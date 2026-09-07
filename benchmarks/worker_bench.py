#!/usr/bin/env python3
"""Pi worker screening with matched audio, WER, warm latency and Linux telemetry.

Numeric output only. This is a development pilot, no physical microphone or
held-out quality certification. Fixture-end latency is not an annotated speech
endpoint or app insertion latency. Configuration order is explicit, not randomized.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import statistics
import struct
import subprocess
import sys
import tempfile
import threading
import time
import wave
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from model_worker import identity,encoded,receive_line
from quality import score,aggregate
from dictation import digest

def process_ids(roots):
    result=set(roots);parents={}
    for p in Path('/proc').glob('[0-9]*/stat'):
        try:parents[int(p.parent.name)]=int(p.read_text().rpartition(') ')[2].split()[1])
        except (OSError,ValueError,IndexError):continue
    while True:
        added={pid for pid,parent in parents.items() if parent in result}-result
        if not added:break
        result.update(added)
    return result

class Resources:
    def __init__(self,pids):self.pids=pids;self.samples=[];self.stop=threading.Event();self.thread=threading.Thread(target=self.loop,daemon=True)
    def start(self):self.thread.start()
    def loop(self):
        while not self.stop.is_set():
            row=dict(monotonic_s=time.monotonic(),rss_mib=0,process_swap_mib=0,system_swap_mib=None,temperature_c=None,throttled=None)
            valid=False
            for pid in (self.pids() if callable(self.pids) else self.pids):
                try:status=Path('/proc',str(pid),'status').read_text()
                except OSError:continue
                valid=True
                for line in status.splitlines():
                    if line.startswith('VmRSS:'):row['rss_mib']+=int(line.split()[1])/1024
                    if line.startswith('VmSwap:'):row['process_swap_mib']+=int(line.split()[1])/1024
            if not valid:row['rss_mib']=row['process_swap_mib']=None
            try:
                mem={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
                row['system_swap_mib']=(mem['SwapTotal']-mem['SwapFree'])/1024
            except (OSError,ValueError,KeyError):pass
            try:row['temperature_c']=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000
            except (OSError,ValueError):pass
            try:
                row['throttled']=int(subprocess.check_output(['vcgencmd','get_throttled'],timeout=.8,text=True).strip().split('=')[1],16)
            except (OSError,ValueError,subprocess.SubprocessError):pass
            self.samples.append(row);self.stop.wait(1)
    def finish(self):self.stop.set();self.thread.join(timeout=2);return self.samples

def quantile(values,q):
    if not values:return None
    values=sorted(values);return values[max(0,__import__('math').ceil(q*len(values))-1)]

def session(a,path,pcm,reference,env,paced=False):
    from argparse import Namespace
    config=Namespace(core=a.binary,model=a.model,rms=300)
    old={k:os.environ.get(k) for k in env}
    try:
        os.environ.update(env);key=identity(config)
    finally:
        for k,v in old.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v
    start=time.monotonic();sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);sock.settimeout(a.timeout);sock.connect(str(path))
    received=[];times=[];source=dict(sent_bytes=0,max_feed_lateness_s=0);buffer=bytearray()
    with sock:
        sock.sendall(encoded(dict(command='run',key=key)));ready=receive_line(sock,buffer)
        if ready.get('type')!='ready':raise ValueError(str(ready))
        ready_s=time.monotonic()-start;origin=time.monotonic()
        def feed():
            try:
                for offset in range(0,len(pcm),640):
                    data=pcm[offset:offset+640]
                    if paced:time.sleep(max(0,origin+(offset+len(data))/32000-time.monotonic()))
                    sock.sendall(struct.pack('!I',len(data))+data);source['sent_bytes']+=len(data)
                    if paced:source['max_feed_lateness_s']=max(source['max_feed_lateness_s'],time.monotonic()-origin-(offset+len(data))/32000)
                sock.sendall(bytes(4))
            except OSError:source['failed']=True
        thread=threading.Thread(target=feed,daemon=True);thread.start()
        done=None
        try:
            while True:
                event=receive_line(sock,buffer)
                if event.get('session')!=ready['session']:raise ValueError('unexpected/stale session')
                if event['type']=='final':received.append(event['text']);times.append(time.monotonic()-origin)
                elif event['type']=='done':done=event;break
                else:raise ValueError(str(event))
        finally:
            sock.shutdown(socket.SHUT_RDWR);thread.join(timeout=2)
        complete=not thread.is_alive() and not source.get('failed') and source['sent_bytes']==len(pcm)==done['samples']*2
    elapsed=time.monotonic()-start
    return dict(passed=complete,exit_code=0 if complete else 74,wall_s=elapsed,ready_s=ready_s,warm=ready['warm'],worker_pid=ready['pid'],
        supplied_audio_s=len(pcm)/32000,source=source,core_samples=done['samples'],output_lines=len(received),
        last_output_after_fixture_end_s=(times[-1]-(len(pcm)/32000-1)) if paced and times else None,
        **score(reference,' '.join(received)))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('binary','model','manifest','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--threads',default='4');p.add_argument('--beams',default='1,5');p.add_argument('--waits',default='PASSIVE')
    p.add_argument('--per-group',type=int,default=1);p.add_argument('--groups',default='de-read-clean,de-noise-10db')
    p.add_argument('--paced',action='store_true');p.add_argument('--timeout',type=float,default=180)
    a=p.parse_args();a.binary=a.binary.resolve();a.model=a.model.resolve()
    expected='ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb'
    if digest(a.model)!=expected:p.error('pinned small Q5_1 SHA mismatch')
    fixtures=json.loads(a.manifest.read_text());chosen=[]
    for group in a.groups.split(','):
        rows=[f for f in fixtures if f['group']==group];chosen+=rows[:a.per_group] if a.per_group else rows
    if not chosen:p.error('no fixtures')
    report=dict(scope=__doc__,date_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),platform=platform.platform(),machine=platform.machine(),
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        working_tree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)),
        files={name:digest(getattr(a,name)) for name in ('binary','model','manifest')},
        implementation_sha256={name:digest(ROOT/name) for name in ('src/whisper_diktat.cpp','runtime/model_worker.py','benchmarks/worker_bench.py')},
        paced=a.paced,configs=[])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    for threads in map(int,a.threads.split(',')):
      for beam in map(int,a.beams.split(',')):
       for wait in a.waits.split(','):
        if threads not in (1,2,4) or beam not in (1,5) or wait not in ('PASSIVE','ACTIVE'):p.error('invalid sweep values')
        env=dict(OMP_NUM_THREADS=str(threads),GEIST_WHISPER_BEAM_SIZE=str(beam),OMP_WAIT_POLICY=wait)
        with tempfile.TemporaryDirectory(prefix='gp-',dir='/tmp') as d:
            path=Path(d)/'w.sock';opts=['--socket',str(path),'--core',str(a.binary),'--model',str(a.model),'--idle-seconds','60']
            server=subprocess.Popen([sys.executable,str(ROOT/'runtime/model_worker.py'),'serve',*opts],env=dict(os.environ,**env),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            resources=None;config=dict(threads=threads,beam_size=beam,wait_policy=wait,runs=[])
            try:
                end=time.monotonic()+5
                while not path.exists() and server.poll() is None and time.monotonic()<end:time.sleep(.02)
                start=time.monotonic()
                warm=subprocess.run([sys.executable,str(ROOT/'runtime/model_worker.py'),'start',*opts],env=dict(os.environ,**env),capture_output=True,text=True,timeout=a.timeout)
                if warm.returncode:raise ValueError(warm.stderr)
                config['model_startup_s']=time.monotonic()-start;pid=json.loads(warm.stdout)['pid'];resources=Resources([server.pid,pid]);resources.start()
                for fixture in chosen:
                    file=a.manifest.parent/fixture['wav']
                    if digest(file)!=fixture['sha256']:raise ValueError('fixture hash mismatch')
                    with wave.open(str(file)) as w:
                        if (w.getframerate(),w.getnchannels(),w.getsampwidth())!=(16000,1,2):raise ValueError('invalid PCM')
                        pcm=w.readframes(w.getnframes())
                    run=session(a,path,pcm+bytes(32000),fixture['reference'],env,a.paced)
                    run.update(id=fixture['id'],group=fixture['group'],audio_s=len(pcm)/32000,wav_sha256=fixture['sha256'])
                    config['runs'].append(run);config['groups']=aggregate(config['runs'])
                    print(json.dumps(dict(threads=threads,beam=beam,wait=wait,id=run['id'],wer=run['wer'],wall_s=run['wall_s'],passed=run['passed'])),flush=True)
            finally:
                if resources:config['resources']=resources.finish()
                server.terminate()
                try:server.communicate(timeout=3)
                except subprocess.TimeoutExpired:server.kill();server.communicate()
            latency=[r['last_output_after_fixture_end_s'] for r in config['runs'] if r['last_output_after_fixture_end_s'] is not None]
            config['fixture_end_latency_s']=dict(count=len(latency),p50=quantile(latency,.5),p95=quantile(latency,.95))
            config['all_audio_accounted']=all(r['passed'] for r in config['runs'])
            report['configs'].append(config);a.output.write_text(json.dumps(report,indent=2)+'\n')
    return 0
if __name__=='__main__':raise SystemExit(main())
