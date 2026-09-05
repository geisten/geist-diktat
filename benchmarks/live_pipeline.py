#!/usr/bin/env python3
"""Paced file-fed capture through the shipping supervisor; no physical microphone.

Reports overload/stop and process-tree RSS samples on Linux, not an accuracy WER.
Audio and transcripts remain local. TERM/KILL are limited to owned test processes.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import threading
import time
import wave
ROOT=Path(__file__).resolve().parents[1]

def capture(wav,limit=None):
    with wave.open(str(wav)) as f:
        if (f.getframerate(),f.getnchannels(),f.getsampwidth())!=(16000,1,2):raise ValueError('16kHz mono PCM16 required')
        start=time.monotonic();n=0
        while True:
            if limit is not None and n>=limit*32000:break
            data=f.readframes(320)
            if not data:break
            time.sleep(max(0,start+n/32000-time.monotonic()))
            sys.stdout.buffer.write(data);sys.stdout.buffer.flush();n+=len(data)

def process_tree_rss(parent):
    table={}
    for stat in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields=stat.read_text().rsplit(')',1)[1].split()
            table[int(stat.parent.name)]=(int(fields[1]),int(fields[21])*os.sysconf('SC_PAGE_SIZE'))
        except (OSError,ValueError,IndexError):continue
    ids={parent};changed=True
    while changed:
        more={pid for pid,(ppid,_) in table.items() if ppid in ids};changed=bool(more-ids);ids|=more
    return sum(table.get(pid,(0,0))[1] for pid in ids)/1048576

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--capture',type=Path)
    for n in ('wav','binary','model','tower','mel','output'):a.add_argument('--'+n,type=Path)
    a.add_argument('--max-audio-seconds',type=float);a.add_argument('--timeout',type=float,default=180);a.add_argument('--buffer-seconds',type=float,default=6)
    args=a.parse_args()
    if args.capture:capture(args.capture,args.max_audio_seconds);return 0
    if any(getattr(args,n) is None for n in ('wav','binary','model','tower','mel','output')):a.error('all paths required')
    command=shlex.join([sys.executable,str(Path(__file__).resolve()),'--capture',str(args.wav.resolve())])
    if args.max_audio_seconds is not None:command+=' --max-audio-seconds '+str(args.max_audio_seconds)
    env=dict(os.environ,OMP_NUM_THREADS='4',GEIST_AUDIO_MODEL_PATH=str(args.tower.resolve()),GEIST_MEL_CONSTANTS_PATH=str(args.mel.resolve()))
    p=subprocess.Popen([sys.executable,str(ROOT/'runtime/diktat_runtime.py'),'--capture',command,'--buffer-seconds',str(args.buffer_seconds),'--',str(args.binary.resolve()),str(args.model.resolve())],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    lines=[];errors=[];samples=[];start=time.monotonic()
    def read(pipe,target):
        for line in iter(pipe.readline,b''):target.append((time.monotonic()-start,line.decode(errors='replace').rstrip()))
    ts=[threading.Thread(target=read,args=(p.stdout,lines)),threading.Thread(target=read,args=(p.stderr,errors))]
    for t in ts:t.start()
    timed_out=False
    try:
        while p.poll() is None:
            samples.append(dict(t=time.monotonic()-start,tree_rss_mib=process_tree_rss(p.pid)))
            if time.monotonic()-start>args.timeout:timed_out=True;p.terminate();break
            time.sleep(.25)
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:p.kill();p.wait()
    finally:
        for t in ts:t.join(2)
    report=dict(exit_code=p.returncode,wall_s=time.monotonic()-start,timeout=timed_out,buffer_seconds=args.buffer_seconds,
                physical_microphone=False,max_audio_seconds=args.max_audio_seconds,transcript=lines,stderr=errors,samples=samples,
                peak_sampled_tree_rss_mib=max((s['tree_rss_mib'] for s in samples),default=0),
                interpretation='Exit 75 is controlled overload, not successful continuous dictation. No WER on incomplete audio.')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('transcript','stderr','samples')}))
    return 0 if p.returncode in (0,75) and not timed_out else 1
if __name__=='__main__':raise SystemExit(main())
