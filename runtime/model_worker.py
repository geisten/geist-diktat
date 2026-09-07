#!/usr/bin/env python3
"""Private, single-model Unix worker. No network listener or audio files.

Only completed sessions and cancellation outside a decode keep the model warm.
A decode-time cancel kills the worker. Idle expiry releases the whole service.
The framed transport is internal; the client preserves the public UTF-8 lines.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import socket
import stat
import struct
import subprocess
import sys
import time
import uuid

MAX_PACKET=640
MAX_QUEUE=50*(MAX_PACKET+4)
MAX_OUTPUT=262144
START=struct.pack('!I',0xffffffff)
END=bytes(4)

def configure_socket(sock):
    # Keep kernel transport queues small as well as the explicit audio queue.
    # Linux may double these requested sizes for accounting overhead.
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,4096)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,4096)
    return sock

def encoded(value):return (json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n').encode()

def location():
    base=Path(os.environ.get('XDG_RUNTIME_DIR',os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache'))))
    return base/'geist-diktat'/'w.sock'

def private_directory(path):
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    info=path.parent.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
        raise ValueError('worker directory must be owned by this user, private (0700), and not a symlink')
    if len(os.fsencode(path))>100:raise ValueError('worker socket path too long; use a shorter XDG_RUNTIME_DIR')

def identity(a):
    files=[]
    for path in (a.core,a.model):
        p=path.resolve(strict=True);s=p.stat();files.append([str(p),s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns])
    return hashlib.sha256(encoded(dict(files=files,rms=float(a.rms),threads=os.getenv('OMP_NUM_THREADS','4'),
        beam=os.getenv('GEIST_WHISPER_BEAM_SIZE','5'),audio_context=os.getenv('GEIST_WHISPER_AUDIO_CONTEXT','full'),wait=os.getenv('OMP_WAIT_POLICY',''),trace=os.getenv('GEIST_DIKTAT_TRACE','')))).hexdigest()

class Service:
    def __init__(self,a):
        self.a=a;self.key=identity(a);self.selector=selectors.DefaultSelector()
        self.clients={};self.active=None;self.worker=None;self.pending=bytearray();self.output=bytearray()
        self.ready=False;self.sequence=0;self.phase='idle';self.ended=False;self.cancel_deadline=None
        self.last_idle=time.monotonic();self.load_started=0;self.loads=0;self.exit=False
    def watch(self,file,events,data):
        try:self.selector.get_key(file)
        except KeyError:
            if events:self.selector.register(file,events,data)
        else:
            if events:self.selector.modify(file,events,data)
            else:self.selector.unregister(file)
    def unwatch(self,file):
        try:self.selector.unregister(file)
        except (KeyError,ValueError):pass
    def kill_worker(self):
        if self.worker is not None:
            self.unwatch(self.worker.stdout);self.unwatch(self.worker.stdin)
            self.worker.stdin.close()
            if self.worker.poll() is None and self.ready and self.phase=='idle':
                try:self.worker.wait(timeout=.2)
                except subprocess.TimeoutExpired:pass
            if self.worker.poll() is None:self.worker.kill()
            self.worker.wait(timeout=1)
            self.worker.stdout.close()
        self.worker=None;self.ready=False;self.sequence=0;self.pending.clear();self.output.clear()
        self.cancel_deadline=None;self.phase='idle';self.last_idle=time.monotonic()
    def load(self):
        if self.worker is not None:return
        env=dict(os.environ);env.pop('GEIST_DIKTAT_READY_FD',None)
        self.worker=subprocess.Popen([str(self.a.core),'--worker',str(self.a.model),str(self.a.rms)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0,env=env)
        os.set_blocking(self.worker.stdin.fileno(),False);os.set_blocking(self.worker.stdout.fileno(),False)
        self.load_started=time.monotonic();self.loads+=1
        self.watch(self.worker.stdout,selectors.EVENT_READ,'worker-read')
    def send(self,client,value):
        if client not in self.clients:return
        c=self.clients[client];c['out'].extend(encoded(value))
        if len(c['out'])>MAX_OUTPUT:self.drop(client);return
        self.refresh()
    def finish(self,client,value):
        if client not in self.clients:return
        self.clients[client]['phase']='closing';self.send(client,value)
    def drop(self,client):
        self.unwatch(client);self.clients.pop(client,None);client.close()
        if client is self.active:
            self.active=None
            if self.worker is not None:
                if self.phase=='decoding' or not self.ready:self.kill_worker()
                else:
                    # Keep an already partly-written packet intact. Drain queued
                    # frames under cancellation, then delimit the abandoned session.
                    if not self.ended:self.pending.extend(END)
                    os.kill(self.worker.pid,signal.SIGUSR1)
                    self.cancel_deadline=time.monotonic()+.35
            self.last_idle=time.monotonic()
    def refresh(self):
        for client,c in list(self.clients.items()):
            if c['phase']=='audio':
                try:self.audio_packets(c)
                except ValueError:self.drop(client);continue
            events=selectors.EVENT_WRITE if c['out'] else 0
            if c['phase']=='request' or (c['phase']=='audio' and len(self.pending)<=MAX_QUEUE-(MAX_PACKET+4)):
                events|=selectors.EVENT_READ
            elif c['phase']=='waiting':events|=selectors.EVENT_READ
            # Detect disconnect even after END; no further bytes are valid.
            elif c['phase']=='ending':events|=selectors.EVENT_READ
            self.watch(client,events,client)
        if self.worker is not None:self.watch(self.worker.stdin,selectors.EVENT_WRITE if self.pending else 0,'worker-write')
    def begin(self):
        client=self.active
        if client not in self.clients:return
        c=self.clients[client]
        if c.get('command')=='start':
            self.active=None;self.last_idle=time.monotonic()
            self.finish(client,dict(type='ready',pid=self.worker.pid,loads=self.loads));return
        self.sequence+=1;self.phase='listening';self.ended=False;self.pending.extend(START)
        c['phase']='audio';c['session']=uuid.uuid4().hex
        self.send(client,dict(type='ready',pid=self.worker.pid,session=c['session'],warm=self.sequence>1))
    def request(self,client,line):
        request=json.loads(line)
        if not isinstance(request,dict):raise ValueError('invalid request')
        cmd=request.get('command')
        if cmd=='status':
            self.finish(client,dict(type='status',loaded=self.ready,busy=self.active is not None or self.cancel_deadline is not None,
                pid=self.worker.pid if self.worker else None,loads=self.loads,idle_seconds=self.a.idle_seconds));return
        if cmd=='stop':
            if self.active is not None:
                active=self.active;self.active=None;self.finish(active,dict(type='error',code=143,message='worker stopped'))
            self.kill_worker();self.finish(client,dict(type='stopped'));self.exit=True;return
        if cmd not in ('run','start') or request.get('key')!=self.key:
            self.finish(client,dict(type='error',code=78,message='worker configuration differs; run geist-diktat worker stop before changing profile or parameters'));return
        if self.active is not None or self.cancel_deadline is not None:
            self.finish(client,dict(type='error',code=73,message='model worker is busy; retry after the active session stops'));return
        self.active=client;self.clients[client].update(phase='waiting',command=cmd)
        self.load()
        if self.ready:self.begin()
    def client_read(self,client):
        c=self.clients[client];data=client.recv(644)
        if not data:self.drop(client);return
        if c['phase'] in ('waiting','ending'):raise ValueError('unexpected data outside audio phase')
        c['in'].extend(data)
        if c['phase']=='request':
            if len(c['in'])>4096:raise ValueError('request too large')
            if b'\n' in c['in']:
                line,extra=c['in'].split(b'\n',1)
                if extra:raise ValueError('audio before ready')
                c['in'].clear();self.request(client,line)
            return
        self.audio_packets(c)
    def audio_packets(self,c):
        while len(c['in'])>=4 and len(self.pending)<=MAX_QUEUE-(MAX_PACKET+4):
            size=struct.unpack('!I',c['in'][:4])[0]
            if size>MAX_PACKET or size%2:raise ValueError('invalid PCM packet')
            if len(c['in'])<4+size:break
            self.pending.extend(c['in'][:4+size]);del c['in'][:4+size]
            if not size:
                if c['in']:raise ValueError('data after end')
                c['phase']='ending';self.ended=True;break
    def worker_read(self):
        data=os.read(self.worker.stdout.fileno(),8192)
        if not data:raise ValueError('model worker exited')
        self.output.extend(data)
        while b'\n' in self.output:
            line,rest=self.output.split(b'\n',1);self.output=bytearray(rest)
            if len(line)>MAX_OUTPUT:raise ValueError('worker event too large')
            event=json.loads(line)
            if not isinstance(event,dict):raise ValueError('invalid worker event object')
            kind=event.get('type')
            if kind=='ready':
                if self.ready:raise ValueError('duplicate model ready')
                self.ready=True;self.begin();continue
            if event.get('session')!=self.sequence:raise ValueError('stale worker session')
            if kind=='state':
                self.phase=event['state']
                if self.cancel_deadline and self.phase=='decoding':self.kill_worker();return
            elif kind=='final':
                if self.active is not None and not self.cancel_deadline:
                    text=event.get('text')
                    if not isinstance(text,str) or '\n' in text or len(text.encode())>65536:raise ValueError('invalid final text')
                    self.send(self.active,dict(type='final',session=self.clients[self.active]['session'],text=text))
            elif kind=='done':
                client=self.active;self.active=None;self.cancel_deadline=None;self.phase='idle';self.last_idle=time.monotonic()
                if client is not None:
                    if self.clients[client]['phase']!='ending' or event.get('cancelled'):raise ValueError('unexpected session end')
                    self.finish(client,dict(type='done',session=self.clients[client]['session'],samples=event.get('samples'),pid=self.worker.pid))
            else:raise ValueError('invalid worker event')
        if len(self.output)>MAX_OUTPUT:raise ValueError('unterminated worker event')
    def serve(self):
        private_directory(self.a.socket)
        fd=os.open(self.a.socket.with_suffix('.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:return 73
            if self.a.socket.exists() or self.a.socket.is_symlink():
                info=self.a.socket.lstat()
                if not stat.S_ISSOCK(info.st_mode) or info.st_uid!=os.getuid():raise ValueError('refusing to replace a non-socket worker path')
                self.a.socket.unlink()
            listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            listener.bind(str(self.a.socket));os.chmod(self.a.socket,0o600);listener.listen(8);listener.setblocking(False)
            self.watch(listener,selectors.EVENT_READ,'listener')
            previous={s:signal.signal(s,lambda *_:setattr(self,'exit',True)) for s in (signal.SIGTERM,signal.SIGINT)}
            try:
                while not self.exit or any(c['out'] for c in self.clients.values()):
                    now=time.monotonic()
                    if self.exit:
                        if not hasattr(self,'exit_deadline'):self.exit_deadline=now+.2
                        if now>=self.exit_deadline:break
                    if self.cancel_deadline and now>=self.cancel_deadline:self.kill_worker()
                    if self.worker and not self.ready and now-self.load_started>self.a.load_timeout:
                        if self.active is not None:
                            client=self.active;self.active=None;self.finish(client,dict(type='error',code=70,message='model startup timed out'))
                        self.kill_worker()
                    if self.active is None and self.cancel_deadline is None and now-self.last_idle>=self.a.idle_seconds:break
                    for client,c in list(self.clients.items()):
                        if c['phase']=='request' and now-c['created']>2:self.drop(client)
                        elif c['phase']=='closing' and not c['out']:self.drop(client)
                    self.refresh()
                    for key,mask in self.selector.select(.02):
                        what=key.data
                        try:
                            if what=='listener':
                                client,_=listener.accept();configure_socket(client);client.setblocking(False)
                                if len(self.clients)>=8:client.close();continue
                                self.clients[client]=dict(phase='request',created=time.monotonic(),**{'in':bytearray(),'out':bytearray()})
                            elif what=='worker-read':
                                if self.worker and key.fileobj is self.worker.stdout:self.worker_read()
                            elif what=='worker-write':
                                if self.worker and self.pending:
                                    n=os.write(self.worker.stdin.fileno(),self.pending);del self.pending[:n]
                            elif what in self.clients:
                                if mask&selectors.EVENT_READ:self.client_read(what)
                                if what in self.clients and mask&selectors.EVENT_WRITE:
                                    c=self.clients[what];n=what.send(c['out']);del c['out'][:n]
                        except BlockingIOError:pass
                        except (OSError,ValueError,KeyError,TypeError) as error:
                            if what in self.clients:self.drop(what)
                            else:
                                if self.active is not None:
                                    client=self.active;self.active=None;self.finish(client,dict(type='error',code=74,message=str(error)))
                                self.kill_worker()
                return 0
            finally:
                for client in list(self.clients):self.drop(client)
                self.kill_worker();listener.close();self.selector.close();self.a.socket.unlink(missing_ok=True)
                for sig,handler in previous.items():signal.signal(sig,handler)

def connect(a,autostart):
    private_directory(a.socket)
    def attempt():
        sock=configure_socket(socket.socket(socket.AF_UNIX,socket.SOCK_STREAM));sock.settimeout(a.load_timeout+2)
        try:sock.connect(str(a.socket));return sock
        except OSError:sock.close();raise
    try:return attempt()
    except (FileNotFoundError,ConnectionRefusedError):
        if not autostart:raise
    env=dict(os.environ);env.pop('GEIST_DIKTAT_READY_FD',None)
    service=subprocess.Popen([sys.executable,__file__,'serve','--socket',str(a.socket),'--core',str(a.core),
        '--model',str(a.model),'--rms',str(a.rms),'--idle-seconds',str(a.idle_seconds),'--load-timeout',str(a.load_timeout)],
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,env=env)
    end=time.monotonic()+5
    while time.monotonic()<end:
        if service.poll() is not None and service.returncode!=73:raise ValueError('model service startup failed; check the private runtime directory')
        try:return attempt()
        except (FileNotFoundError,ConnectionRefusedError):time.sleep(.02)
    raise ValueError('model service did not start')

def receive_line(sock,buffer):
    while b'\n' not in buffer:
        data=sock.recv(8192)
        if not data:raise ValueError('model service disconnected')
        buffer.extend(data)
        if len(buffer)>MAX_OUTPUT:raise ValueError('oversized model event')
    line,rest=buffer.split(b'\n',1);buffer[:]=rest;return json.loads(line)

def client(a):
    try:sock=connect(a,a.command in ('run','start'))
    except (FileNotFoundError,ConnectionRefusedError):
        if a.command=='status':print(json.dumps(dict(type='status',loaded=False,busy=False)));return 0
        if a.command=='stop':return 0
        raise
    with sock:
        sock.sendall(encoded(dict(command=a.command,key=identity(a) if a.command in ('run','start') else None)))
        buffer=bytearray();first=receive_line(sock,buffer)
        if first.get('type')=='error':print('geist-diktat: '+first['message'],file=sys.stderr);return first['code']
        if a.command!='run':print(json.dumps(first));return 0
        if first.get('type')!='ready':raise ValueError('model worker not ready')
        ready=os.getenv('GEIST_DIKTAT_READY_FD')
        if ready is not None:os.write(int(ready),b'1');os.close(int(ready))
        # One bounded producer thread; sendall backpressure reaches the supervisor.
        import threading
        failure=[]
        def feed():
            try:
                while True:
                    data=sys.stdin.buffer.read(MAX_PACKET)
                    if not data:break
                    if len(data)%2:raise ValueError('odd PCM byte')
                    sock.sendall(struct.pack('!I',len(data))+data)
                sock.sendall(END)
            except (OSError,ValueError) as error:
                failure.append(error)
                try:sock.shutdown(socket.SHUT_RDWR)
                except OSError:pass
        sender=threading.Thread(target=feed,daemon=True);sender.start();sock.settimeout(None)
        while True:
            event=receive_line(sock,buffer)
            if event.get('type')=='error':print('geist-diktat: '+event['message'],file=sys.stderr);return event['code']
            if event.get('session')!=first['session']:raise ValueError('stale session output')
            if event.get('type')=='final':
                text=event['text']
                if not isinstance(text,str) or '\n' in text:raise ValueError('invalid final text')
                print(text,flush=True)
            elif event.get('type')=='done':
                sender.join(timeout=.2)
                if failure or sender.is_alive():raise ValueError('incomplete audio sender')
                return 0
            else:raise ValueError('invalid model event')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['serve','run','start','status','stop'])
    p.add_argument('--socket',type=Path,default=location());p.add_argument('--core',type=Path);p.add_argument('--model',type=Path)
    p.add_argument('--rms',type=float,default=300);p.add_argument('--idle-seconds',type=float,default=60);p.add_argument('--load-timeout',type=float,default=120)
    a=p.parse_args()
    if not 1<=a.idle_seconds<=3600 or not 1<=a.load_timeout<=300 or not 0<a.rms<=32768:p.error('invalid worker limits')
    if a.command in ('run','start','serve') and (not a.core or not a.model):p.error('core and model required')
    # Closing the client immediately invalidates its session at the service.
    if a.command=='run':
        for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,lambda n,_:os._exit(128+n))
    try:return Service(a).serve() if a.command=='serve' else client(a)
    except (OSError,ValueError,KeyError,TypeError) as error:print('geist-diktat: '+str(error),file=sys.stderr);return 74
if __name__=='__main__':raise SystemExit(main())
