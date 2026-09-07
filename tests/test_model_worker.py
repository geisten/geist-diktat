"""Actual resident C++ frontend + private Unix service, with a controlled ASR API."""
import json
import os
from pathlib import Path
import shlex
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
WORKER=ROOT/'runtime/model_worker.py'
PCM=struct.pack('<h',1000)*8000

class ModelWorker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build=tempfile.TemporaryDirectory(prefix='gw-build-');cls.core=Path(cls.build.name)/'core'
        subprocess.run([os.getenv('CXX','c++'),'-std=c++17','-Wall','-Wextra','-Werror',
            '-fsanitize=address,undefined','-fno-omit-frame-pointer','-g','-pthread',
            '-I'+str(ROOT/'tests/whisper_stub'),str(ROOT/'src/whisper_diktat.cpp'),str(ROOT/'tests/whisper_stub/stub.cpp'),
            '-o',str(cls.core)],check=True,capture_output=True)
    @classmethod
    def tearDownClass(cls):cls.build.cleanup()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='gw-',dir='/tmp');self.root=Path(self.temp.name)
        self.model=self.root/'model';self.model.touch();self.sock=self.root/'w.sock';self.log=self.root/'engine.log'
        self.env=dict(os.environ,STUB_LOG=str(self.log),OMP_NUM_THREADS='4',GEIST_WHISPER_BEAM_SIZE='5')
        for k in ('STUB_BLOCK','STUB_LOAD_FAIL','GEIST_DIKTAT_TRACE','GEIST_DIKTAT_READY_FD'):self.env.pop(k,None)
        self.server=None;self.sockets=[]
    def tearDown(self):
        if self.sock.exists():
            try:self.call('stop',timeout=3)
            except (OSError,subprocess.TimeoutExpired):pass
        for s in self.sockets:s.close()
        if self.server:
            self.server.terminate()
            try:self.server.communicate(timeout=3)
            except subprocess.TimeoutExpired:self.server.kill();self.server.communicate()
        self.temp.cleanup()
    def options(self,idle=10):return ['--socket',str(self.sock),'--core',str(self.core),'--model',str(self.model),'--idle-seconds',str(idle)]
    def start(self,idle=10,**env):
        self.env.update(env)
        self.server=subprocess.Popen([sys.executable,str(WORKER),'serve',*self.options(idle)],env=self.env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        end=time.monotonic()+2
        while not self.sock.exists() and self.server.poll() is None and time.monotonic()<end:time.sleep(.01)
        self.assertTrue(self.sock.exists(),self.server.communicate(timeout=1) if self.server.poll() is not None else 'socket timeout')
    def call(self,command,data=None,timeout=5,extra=()):
        return subprocess.run([sys.executable,str(WORKER),command,*self.options(),*extra],env=self.env,input=data,capture_output=True,timeout=timeout)
    def key(self):
        sys.path.insert(0,str(ROOT/'runtime'))
        from model_worker import identity
        from argparse import Namespace
        old=dict(os.environ)
        try:os.environ.clear();os.environ.update(self.env);return identity(Namespace(core=self.core,model=self.model,rms=300))
        finally:os.environ.clear();os.environ.update(old)
    def open(self,command='run',key=None):
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.settimeout(3);s.connect(str(self.sock));self.sockets.append(s)
        s.sendall((json.dumps(dict(command=command,key=self.key() if key is None else key))+'\n').encode())
        return s,self.read(s)
    def read(self,s):
        # Byte reads avoid consuming a following event in these test clients.
        data=bytearray()
        while not data.endswith(b'\n'):
            b=s.recv(1)
            if not b:raise EOFError()
            data.extend(b)
        return json.loads(data)
    def packet(self,s,data):
        for i in range(0,len(data),640):s.sendall(struct.pack('!I',len(data[i:i+640]))+data[i:i+640])
    def wait_idle(self):
        end=time.monotonic()+2
        while time.monotonic()<end:
            p=self.call('status');d=json.loads(p.stdout)
            if not d['busy']:return d
            time.sleep(.02)
        self.fail('worker did not become idle')
    def test_twenty_sessions_load_once_and_have_unique_ids(self):
        self.start();ids=[];pids=[]
        for _ in range(20):
            s,ready=self.open();self.assertEqual(ready['type'],'ready');ids.append(ready['session']);pids.append(ready['pid'])
            self.packet(s,PCM);s.sendall(bytes(4));final=self.read(s);done=self.read(s)
            self.assertEqual(final['text'],'Hallo Welt Grüße!');self.assertEqual(final['session'],ready['session'])
            self.assertEqual(done['type'],'done');self.assertEqual(done['samples'],8000);s.close()
        self.assertEqual(len(set(ids)),20);self.assertEqual(len(set(pids)),1)
        self.assertEqual(self.log.read_text().splitlines().count('load 0'),1)
    def test_idle_cancel_reuses_model_and_discards_partial_audio(self):
        self.start();s,ready=self.open();self.packet(s,PCM[:4000]);s.close()
        status=self.wait_idle();self.assertTrue(status['loaded']);self.assertEqual(status['pid'],ready['pid'])
        p=self.call('run',PCM);self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout.decode(),'Hallo Welt Grüße!\n')
        self.assertEqual(self.log.read_text().splitlines().count('load 0'),1)
        self.assertEqual(self.log.read_text().splitlines().count('decode 8000'),1)
    def test_cancel_during_decode_kills_model_and_next_session_is_clean(self):
        self.start(STUB_BLOCK='1');s,ready=self.open();self.packet(s,PCM+bytes(25600))
        end=time.monotonic()+2
        while 'decode ' not in self.log.read_text() and time.monotonic()<end:time.sleep(.01)
        self.assertIn('decode ',self.log.read_text());start=time.monotonic();s.close()
        status=self.wait_idle();self.assertLess(time.monotonic()-start,1);self.assertFalse(status['loaded'])
        p=self.call('run',PCM,timeout=5);self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout.decode(),'Hallo Welt Grüße!\n')
        self.assertEqual(self.log.read_text().splitlines().count('load 0'),2)
    def test_cancel_with_full_queue_stops_decode_before_draining_audio(self):
        import threading
        self.start(STUB_BLOCK='1',STUB_LONG_BLOCK='1');s,_=self.open()
        def feed():
            try:self.packet(s,PCM+bytes(25600)+PCM*40)
            except OSError:pass
        sender=threading.Thread(target=feed,daemon=True);sender.start()
        end=time.monotonic()+2
        while time.monotonic()<end:
            status=json.loads(self.call('status').stdout)
            if status['transport_queue_bytes']>=31000:break
            time.sleep(.01)
        self.assertGreaterEqual(status['transport_queue_bytes'],31000)
        started=time.monotonic();s.shutdown(socket.SHUT_RDWR);s.close()
        status=self.wait_idle();self.assertLess(time.monotonic()-started,1)
        self.assertFalse(status['loaded'])
        # macOS can keep the test feeder in socket.select until its 3 s timeout
        # after another thread closes the fd. This cleanup is outside Stop timing.
        sender.join(timeout=3.5);self.assertFalse(sender.is_alive())

    def test_busy_and_mismatched_configuration_fail_without_stealing_session(self):
        self.start();s,ready=self.open()
        p=self.call('run',PCM);self.assertEqual(p.returncode,73,p.stderr)
        other,answer=self.open(key='different');self.assertEqual(answer['code'],78);other.close()
        self.packet(s,PCM);s.sendall(bytes(4));self.assertEqual(self.read(s)['type'],'final');self.assertEqual(self.read(s)['type'],'done')
    def test_idle_expiry_releases_model_and_service(self):
        self.start(idle=1);p=self.call('run',PCM);self.assertEqual(p.returncode,0,p.stderr)
        self.server.communicate(timeout=3);self.assertEqual(self.server.returncode,0);self.assertFalse(self.sock.exists())
    def test_malformed_packet_is_not_success_and_does_not_poison_restart(self):
        self.start();s,_=self.open();s.sendall(struct.pack('!I',641)+bytes(641))
        with self.assertRaises((EOFError,ConnectionResetError)):self.read(s)
        self.wait_idle();p=self.call('run',PCM);self.assertEqual(p.returncode,0,p.stderr)
    def test_regular_file_at_socket_path_is_preserved(self):
        self.sock.write_text('existing user data')
        p=subprocess.run([sys.executable,str(WORKER),'serve',*self.options()],env=self.env,capture_output=True,timeout=3)
        self.assertNotEqual(p.returncode,0);self.assertEqual(self.sock.read_text(),'existing user data')
        self.sock.unlink()

    def test_private_directory_required(self):
        self.root.chmod(0o755)
        p=self.call('start');self.assertNotEqual(p.returncode,0);self.assertIn(b'private',p.stderr)
        self.assertFalse(self.sock.exists());self.root.chmod(0o700)
    def test_model_load_failure_is_reported_before_capture(self):
        self.start(STUB_LOAD_FAIL='1');marker=self.root/'capture-started'
        decoder=[sys.executable,str(WORKER),'run',*self.options()]
        p=subprocess.run([sys.executable,str(ROOT/'runtime/diktat_runtime.py'),'--capture','touch '+shlex.quote(str(marker)),
            '--ready-timeout','3','--',*decoder],env=self.env,capture_output=True,timeout=5)
        self.assertNotEqual(p.returncode,0);self.assertFalse(marker.exists())
    def test_supervisor_overload_cancels_worker_without_hiding_failure(self):
        self.start(STUB_BLOCK='1')
        decoder=[sys.executable,str(WORKER),'run',*self.options()]
        p=subprocess.run([sys.executable,str(ROOT/'runtime/diktat_runtime.py'),'--capture','cat /dev/zero',
            '--buffer-seconds','.1','--ready-timeout','3','--',*decoder],env=self.env,capture_output=True,timeout=6)
        self.assertEqual(p.returncode,75,p.stderr);self.assertIn(b'overload',p.stderr)
        self.assertFalse(self.wait_idle()['busy'])
    def test_explicit_stop_terminates_active_client_and_service(self):
        self.start();s,_=self.open();p=self.call('stop');self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(self.read(s)['code'],143);self.server.communicate(timeout=2);self.assertFalse(self.sock.exists())
    def test_installed_launcher_reuses_worker_and_waits_before_capture(self):
        import shutil
        prefix=self.root/'prefix';binpath=prefix/'bin';share=prefix/'share/geist-diktat'
        binpath.mkdir(parents=True);share.mkdir(parents=True)
        shutil.copyfile(self.core,binpath/'diktat-whisper');(binpath/'diktat-whisper').chmod(0o755)
        shutil.copyfile(ROOT/'packaging/geist-diktat',binpath/'geist-diktat');(binpath/'geist-diktat').chmod(0o755)
        for helper in (ROOT/'runtime').glob('*.py'):shutil.copyfile(helper,share/helper.name)
        (share/'default-profile').write_text('whisper-small')
        code="from pathlib import Path;import sys,struct;assert Path("+repr(str(self.log))+").exists();sys.stdout.buffer.write(struct.pack('<h',1000)*8000)"
        env=dict(self.env,HOME=str(self.root),XDG_CONFIG_HOME=str(self.root/'config'),XDG_RUNTIME_DIR=str(self.root/'r'),
            GEIST_DIKTAT_MODEL=str(self.model),GEIST_DIKTAT_REUSE_MODEL='1',GEIST_DIKTAT_CAPTURE=shlex.join([sys.executable,'-c',code]))
        launcher=str(binpath/'geist-diktat')
        try:
            for _ in range(2):
                p=subprocess.run([launcher,'run'],env=env,capture_output=True,timeout=5)
                self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout.decode(),'Hallo Welt Grüße!\n')
            self.assertEqual(self.log.read_text().splitlines().count('load 0'),1)
        finally:subprocess.run([launcher,'worker','stop'],env=env,capture_output=True,timeout=3)

    def test_autostart_and_status(self):
        # The child service has its own short lifetime and private directory.
        p=self.call('run',PCM,extra=('--idle-seconds','1'));self.assertEqual(p.returncode,0,p.stderr)
        try:self.assertTrue(json.loads(self.call('status').stdout)['loaded'])
        finally:self.call('stop')
