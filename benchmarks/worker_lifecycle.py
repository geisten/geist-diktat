#!/usr/bin/env python3
"""Real-model warm reuse, idle/decode cancellation and expiry; no microphone/GUI.

Uses the production worker CLI for cancellation. The saturated input is a stress
fixture, not a paced recording. Exported reports contain no audio or transcripts.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import wave
from worker_bench import session,encoded,receive_line
from dictation import digest
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('binary','model','manifest','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--beam',type=int,choices=[1,3,5],default=5)
    a=p.parse_args();a.binary=a.binary.resolve();a.model=a.model.resolve();a.timeout=120
    if digest(a.model)!='ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb':p.error('model SHA mismatch')
    fixture=next(r for r in json.loads(a.manifest.read_text()) if r['group']=='de-read-clean')
    wav=a.manifest.parent/fixture['wav']
    if digest(wav)!=fixture['sha256']:raise ValueError('fixture SHA mismatch')
    with wave.open(str(wav)) as w:
        if (w.getframerate(),w.getnchannels(),w.getsampwidth())!=(16000,1,2):raise ValueError('invalid PCM')
        pcm=w.readframes(w.getnframes())+bytes(32000)
    result=dict(scope=__doc__,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        working_tree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)),
        implementation_sha256={name:digest(ROOT/name) for name in ('src/whisper_diktat.cpp','runtime/model_worker.py','runtime/pipe_limits.py','benchmarks/worker_lifecycle.py','benchmarks/worker_bench.py')},
        files={name:digest(getattr(a,name)) for name in ('binary','model','manifest')},fixture_sha256=fixture['sha256'],
        temperature_fallback=os.getenv('GEIST_WHISPER_TEMPERATURE_FALLBACK','1')=='1',audio_context=os.getenv('GEIST_WHISPER_AUDIO_CONTEXT','full'),chunk_seconds=int(os.getenv('GEIST_WHISPER_CHUNK_SECONDS','28')),
        threads=4,beam_size=a.beam,wait_policy='PASSIVE',physical_microphone=False,application_insertion=False)
    with tempfile.TemporaryDirectory(prefix='gl-',dir='/tmp') as tmp:
        d=Path(tmp);sock=d/'w.sock';trace=d/'trace.jsonl'
        env=dict(os.environ,GEIST_DIKTAT_TRACE=str(trace),OMP_NUM_THREADS='4',GEIST_WHISPER_BEAM_SIZE=str(a.beam),OMP_WAIT_POLICY='PASSIVE')
        opts=['--socket',str(sock),'--core',str(a.binary),'--model',str(a.model),'--idle-seconds','3']
        server=subprocess.Popen([sys.executable,str(ROOT/'runtime/model_worker.py'),'serve',*opts],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        client=None;feeder=None
        def status():
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
                s.settimeout(2);s.connect(str(sock));s.sendall(encoded(dict(command='status')))
                return receive_line(s,bytearray())
        def until(predicate,timeout):
            end=time.monotonic()+timeout
            while time.monotonic()<end:
                value=status()
                if predicate(value):return value
                time.sleep(.005)
            raise TimeoutError('worker condition not reached')
        try:
            deadline=time.monotonic()+5
            while not sock.exists() and server.poll() is None and time.monotonic()<deadline:time.sleep(.01)
            first=session(a,sock,pcm,fixture['reference'],env)
            second=session(a,sock,pcm,fixture['reference'],env)
            result['warm_sessions']=[first,second]
            # A client waiting for more speech must discard its session and reuse
            # its existing model. No synthetic text should leak to the next run.
            client=subprocess.Popen([sys.executable,str(ROOT/'runtime/model_worker.py'),'run',*opts],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
            until(lambda s:s['busy'] and s['loaded'],3)
            before=time.monotonic();client.terminate();out,err=client.communicate(timeout=1)
            idle=until(lambda s:not s['busy'],1)
            result['idle_cancel']=dict(stop_s=time.monotonic()-before,exit_code=client.returncode,output_bytes=len(out),loaded=idle['loaded'],pid=idle['pid'])
            client=None
            # Fill bounded transport while a real decode is observed. Stop must
            # invalidate the client even while PCM remains unread in the socket.
            output=d/'cancel-output'
            baseline=sum(json.loads(line)['event']=='decode_start' for line in trace.read_text().splitlines())
            with output.open('wb') as out:
                client=subprocess.Popen([sys.executable,str(ROOT/'runtime/model_worker.py'),'run',*opts],stdin=subprocess.PIPE,stdout=out,stderr=subprocess.DEVNULL,env=env)
                def feed():
                    try:
                        for _ in range(30):client.stdin.write(pcm);client.stdin.flush()
                    except (BrokenPipeError,OSError):pass
                feeder=threading.Thread(target=feed,daemon=True);feeder.start()
                deadline=time.monotonic()+120;saturated=False
                while time.monotonic()<deadline and client.poll() is None:
                    try:events=[json.loads(line) for line in trace.read_text().splitlines()]
                    except ValueError:continue
                    starts=sum(e['event']=='decode_start' for e in events);ends=sum(e['event']=='decode_end' for e in events)
                    st=status()
                    if starts>baseline and starts>ends and st['transport_queue_bytes']>=31000:saturated=True;break
                    time.sleep(.005)
                before_bytes=output.stat().st_size;before=time.monotonic();client.terminate();client.wait(timeout=1)
                stopped=until(lambda s:not s['busy'],1)
                result['decode_cancel']=dict(stop_s=time.monotonic()-before,exit_code=client.returncode,observed_saturated_decode=saturated,
                    output_bytes_after_stop=output.stat().st_size-before_bytes,loaded=stopped['loaded'])
                feeder.join(timeout=2);client.stdin.close();client=None
            third=session(a,sock,pcm,fixture['reference'],env);result['restart']=third
            before=time.monotonic();server.wait(timeout=5)
            result['idle_expiry']=dict(elapsed_s=time.monotonic()-before,exit_code=server.returncode,socket_removed=not sock.exists())
            result['model_loads']=sum(json.loads(line)['event']=='model_load_start' for line in trace.read_text().splitlines())
            stop=result['decode_cancel'];idle=result['idle_cancel']
            result['passed']=(all(r['passed'] for r in (first,second,third)) and first['worker_pid']==second['worker_pid']==idle['pid']
                and third['worker_pid']!=first['worker_pid'] and result['model_loads']==2
                and all(r['errors']==first['errors'] for r in (second,third))
                and idle['loaded'] and idle['exit_code']==143 and idle['output_bytes']==0 and idle['stop_s']<1
                and stop['observed_saturated_decode'] and stop['exit_code']==143 and not stop['loaded'] and stop['stop_s']<1 and stop['output_bytes_after_stop']==0
                and result['idle_expiry']['exit_code']==0 and result['idle_expiry']['socket_removed'])
        finally:
            if client and client.poll() is None:client.kill();client.wait()
            if feeder:feeder.join(timeout=2)
            if server.poll() is None:
                server.terminate()
                try:server.wait(timeout=3)
                except subprocess.TimeoutExpired:server.kill();server.wait()
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('passed','idle_cancel','decode_cancel','model_loads')}));return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
