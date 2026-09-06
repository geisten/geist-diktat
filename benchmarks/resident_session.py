#!/usr/bin/env python3
"""One paced, multi-utterance resident ASR session via the real supervisor.

Concatenated human read speech is a transport/load test, not a conversation or
physical microphone. Only numeric results/hashes are written to the report.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import wave
from dictation import digest
from quality import score
from live_pipeline import process_tree_rss
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','binary','model','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--rounds',type=int,default=1);p.add_argument('--timeout',type=float,default=360)
    a=p.parse_args()
    if not 1<=a.rounds<=20 or not 0<a.timeout<=4000:p.error('invalid rounds/timeout')
    manifest=json.loads(a.manifest.read_text());fixtures=[r for r in manifest if r['group']=='de-read-clean']
    if len(fixtures)!=12:p.error('the complete 12-clip clean pilot is required')
    with tempfile.TemporaryDirectory(prefix='geist-resident-session-') as d:
        d=Path(d);wav=d/'session.wav';trace=d/'trace.jsonl';transcript=d/'stdout';errors=d/'stderr'
        # Temporary corpus stays local, outside all exported artifact paths.
        refs=[];sample_count=0
        with wave.open(str(wav),'wb') as out:
            out.setparams((1,2,16000,0,'NONE','not compressed'))
            for _ in range(a.rounds):
                for fixture in fixtures:
                    source=a.manifest.parent/fixture['wav']
                    if digest(source)!=fixture['sha256']:raise ValueError('fixture hash mismatch')
                    with wave.open(str(source),'rb') as f:
                        if (f.getframerate(),f.getnchannels(),f.getsampwidth())!=(16000,1,2):raise ValueError('invalid fixture PCM')
                        audio=f.readframes(f.getnframes())
                    out.writeframes(audio+bytes(32000));sample_count+=len(audio)//2+16000;refs.append(fixture['reference'])
        capture=shlex.join([sys.executable,str(ROOT/'benchmarks/trace_capture.py'),str(wav)])
        env=dict(os.environ,GEIST_DIKTAT_TRACE=str(trace),OMP_NUM_THREADS='4')
        command=[sys.executable,str(ROOT/'runtime/diktat_runtime.py'),'--capture',capture,'--',str(a.binary.resolve()),str(a.model.resolve())]
        rss=[];start=time.monotonic();timed_out=False
        with transcript.open('wb') as stdout,errors.open('wb') as stderr:
            proc=subprocess.Popen(command,stdout=stdout,stderr=stderr,env=env)
            try:
                while proc.poll() is None:
                    if Path('/proc').is_dir():rss.append(process_tree_rss(proc.pid))
                    if time.monotonic()-start>a.timeout:
                        timed_out=True;proc.terminate();break
                    time.sleep(.25)
                proc.wait(timeout=5)
            finally:
                if proc.poll() is None:proc.kill();proc.wait()
        events=[json.loads(s) for s in trace.read_text().splitlines()] if trace.exists() else []
        def one(component,event):
            rows=[r for r in events if r.get('component')==component and r.get('event')==event]
            return rows[0] if len(rows)==1 else {}
        runtime=one('runtime','input_summary');core=one('core','input_summary');source=one('capture','source_summary')
        loads=sum(r.get('event')=='model_load_start' for r in events)
        complete=(proc.returncode==0 and not timed_out and loads==1 and
            runtime.get('failed') is False and source.get('failed') is False and
            runtime.get('received_bytes')==runtime.get('delivered_bytes')==source.get('sent_bytes')==sample_count*2 and
            core.get('audio_end_sample')==sample_count)
        result=dict(source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
            scope='paced concatenated human read-speech, 1s between clips; no physical microphone or natural conversation',
            passed=complete,transport_complete=complete,full_product_approval=False,exit_code=proc.returncode,timeout=timed_out,
            wall_s=time.monotonic()-start,audio_s=sample_count/16000,rounds=a.rounds,model_loads=loads,
            decoder=dict(engine='whisper-resident',threads=4,beam_size=int(env.get('GEIST_WHISPER_BEAM_SIZE','5'))),
            output_lines=len(transcript.read_text().splitlines()),runtime=runtime,core=core,capture=source,
            peak_sampled_tree_rss_mib=max(rss) if rss else None,rss_sample_interval_s=.25,
            files={name:digest(getattr(a,name)) for name in ('binary','model','manifest')},session_wav_sha256=digest(wav))
        if complete:result['quality']=score(' '.join(refs),' '.join(transcript.read_text().splitlines()))
        a.output.parent.mkdir(exist_ok=True,parents=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2));return 0 if complete else 1
if __name__=='__main__':raise SystemExit(main())
