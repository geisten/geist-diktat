#!/usr/bin/env python3
"""Timed real-ASR worker/supervisor soak using repeated licensed local fixtures.

No microphone, no desktop, no corpus redistribution. A 60-minute run includes a
30-minute checkpoint; that checkpoint is not a separately completed 30-minute run.
Only a full run receives WER. All model memory is released on exit.
"""
import argparse
import json
import math
import os
import platform
from pathlib import Path
import shlex
import statistics
import subprocess
import sys
import tempfile
import time
import wave
from dictation import digest
from quality import score
from worker_bench import Resources,process_ids
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('binary','model','manifest','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--group',choices=['de-read-clean','de-conversation-long'],default='de-conversation-long')
    p.add_argument('--minutes',type=float,default=60);p.add_argument('--threads',type=int,default=4);p.add_argument('--beam',type=int,default=5)
    a=p.parse_args()
    if not .01<=a.minutes<=120 or a.threads not in (1,2,4) or a.beam not in (1,5):p.error('invalid soak parameters')
    if digest(a.model)!='ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb':p.error('model SHA mismatch')
    rows=[r for r in json.loads(a.manifest.read_text()) if r['group']==a.group]
    if not rows:p.error('no fixtures')
    provenance=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        working_tree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)),
        implementation_sha256={name:digest(ROOT/name) for name in ('src/whisper_diktat.cpp','runtime/model_worker.py','runtime/diktat_runtime.py','benchmarks/worker_soak.py')},
        files={name:digest(getattr(a,name)) for name in ('binary','model','manifest')},platform=platform.platform(),machine=platform.machine())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gs-',dir='/tmp') as temp:
        d=Path(temp);wav=d/'input.wav';trace=d/'trace.jsonl';sock=d/'w.sock';references=[];samples=0;occurrences=[]
        with wave.open(str(wav),'wb') as out:
            out.setparams((1,2,16000,0,'NONE','not compressed'))
            while samples<math.ceil(a.minutes*60*16000):
                for row in rows:
                    source=a.manifest.parent/row['wav']
                    if digest(source)!=row['sha256']:raise ValueError('fixture hash mismatch')
                    with wave.open(str(source)) as w:
                        if (w.getframerate(),w.getnchannels(),w.getsampwidth())!=(16000,1,2):raise ValueError('invalid source PCM')
                        while data:=w.readframes(16000):out.writeframes(data);samples+=len(data)//2
                    out.writeframes(bytes(32000));samples+=16000
                    references.append(row['reference']);occurrences.append(dict(id=row['id'],sha256=row['sha256'],end_sample=samples))
                    if samples>=math.ceil(a.minutes*60*16000):break
        env=dict(os.environ,GEIST_DIKTAT_TRACE=str(trace),OMP_NUM_THREADS=str(a.threads),GEIST_WHISPER_BEAM_SIZE=str(a.beam),OMP_WAIT_POLICY='PASSIVE')
        opts=['--socket',str(sock),'--core',str(a.binary.resolve()),'--model',str(a.model.resolve()),'--idle-seconds','60']
        server=subprocess.Popen([sys.executable,str(ROOT/'runtime/model_worker.py'),'serve',*opts],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        probe=None;proc=None;checkpoints=[];timeout=False
        started=time.monotonic()
        try:
            deadline=time.monotonic()+5
            while not sock.exists() and server.poll() is None and time.monotonic()<deadline:time.sleep(.02)
            start=subprocess.run([sys.executable,str(ROOT/'runtime/model_worker.py'),'start',*opts],env=env,capture_output=True,text=True,timeout=125)
            if start.returncode:raise ValueError(start.stderr)
            model_startup_s=time.monotonic()-started
            capture=shlex.join([sys.executable,str(ROOT/'benchmarks/trace_capture.py'),str(wav)])
            command=[sys.executable,str(ROOT/'runtime/diktat_runtime.py'),'--capture',capture,'--ready-timeout','125','--',
                sys.executable,str(ROOT/'runtime/model_worker.py'),'run',*opts]
            with (d/'text').open('wb') as text,(d/'errors').open('wb') as errors:
                started=time.monotonic();proc=subprocess.Popen(command,env=env,stdout=text,stderr=errors)
                probe=Resources(lambda:process_ids([server.pid,proc.pid]));probe.start();next_checkpoint=60
                while proc.poll() is None:
                    elapsed=time.monotonic()-started
                    if elapsed>samples/16000+180:
                        timeout=True;proc.terminate();break
                    if elapsed>=next_checkpoint:
                        latest=probe.samples[-1] if probe.samples else {}
                        checkpoint=dict(elapsed_s=elapsed,output_bytes=(d/'text').stat().st_size,**latest)
                        checkpoints.append(checkpoint);a.output.with_suffix('.progress.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
                        print(json.dumps(dict(elapsed_s=elapsed,rss_mib=latest.get('rss_mib'),temperature_c=latest.get('temperature_c'))),flush=True)
                        next_checkpoint+=60
                    time.sleep(.25)
                proc.wait(timeout=3)
            wall_s=time.monotonic()-started
            resource_samples=probe.finish();probe=None
            events=[json.loads(line) for line in trace.read_text().splitlines()]
            def one(component,event):
                found=[r for r in events if r['component']==component and r['event']==event]
                return found[0] if len(found)==1 else {}
            runtime=one('runtime','input_summary');core=one('core','input_summary');capture_summary=one('capture','source_summary')
            complete=(not timeout and proc.returncode==0 and not runtime.get('failed',True) and not capture_summary.get('failed',True)
                and runtime.get('received_bytes')==runtime.get('delivered_bytes')==capture_summary.get('sent_bytes')==samples*2
                and core.get('audio_end_sample')==samples)
            loads=sum(e['event']=='model_load_start' for e in events)
            rss=[s for s in resource_samples if s['rss_mib'] is not None]
            first=[s['rss_mib'] for s in rss if 60<=s['monotonic_s']-started<660]
            last=[s['rss_mib'] for s in rss if s['monotonic_s']-started>max(660,wall_s-600)]
            growth=statistics.median(last)-statistics.median(first) if first and last else None
            transport_pass=complete and loads==1
            peak_rss=max((s['rss_mib'] for s in resource_samples if s['rss_mib'] is not None),default=None)
            peak_swap=max((s['process_swap_mib'] for s in resource_samples if s['process_swap_mib'] is not None),default=None)
            throttled=any(s['throttled'] is not None and s['throttled']&0xf for s in resource_samples)
            memory_pass=(growth is not None and growth<=64 and peak_rss is not None and peak_rss<=1536 and peak_swap==0)
            soak_pass=transport_pass and (a.minutes<30 or (memory_pass and not throttled))
            result=dict(scope=__doc__,passed=soak_pass,transport_passed=transport_pass,transport_complete=complete,full_product_approval=False,
                **provenance,input_sha256=digest(wav),source_occurrences=occurrences,
                requested_minutes=a.minutes,audio_s=samples/16000,wall_s=wall_s,model_startup_s=model_startup_s,model_loads=loads,
                audio_context=os.getenv('GEIST_WHISPER_AUDIO_CONTEXT','full'),threads=a.threads,beam_size=a.beam,wait_policy='PASSIVE',exit_code=proc.returncode,timeout=timeout,
                runtime=runtime,core=core,capture=capture_summary,decode_events=[e for e in events if e['component']=='core'],buffer_observations=[e for e in events if e['event']=='buffer_state'],
                resources=resource_samples,checkpoints=checkpoints,rss_median_growth_mib=growth,
                memory_plateau_passed=memory_pass,peak_tree_rss_mib=peak_rss,peak_process_swap_mib=peak_swap,
                temperature_peak_c=max((s['temperature_c'] for s in resource_samples if s['temperature_c'] is not None),default=None),
                active_throttling_observed=throttled,
                physical_microphone=False,application_insertion=False)
            result['source_files_unchanged']=all(digest(ROOT/name)==sha for name,sha in provenance['implementation_sha256'].items())
            result['passed']=result['passed'] and result['source_files_unchanged']
            if complete:
                analysis_start=time.monotonic();result['quality']=score(' '.join(references),' '.join((d/'text').read_text().splitlines()));result['wer_analysis_s']=time.monotonic()-analysis_start
            a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('passed','audio_s','wall_s','model_loads','rss_median_growth_mib','active_throttling_observed')}),flush=True)
            return 0 if result['passed'] else 1
        finally:
            if probe:probe.finish()
            if proc and proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=3)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
            server.terminate()
            try:server.wait(timeout=3)
            except subprocess.TimeoutExpired:server.kill();server.wait()
if __name__=='__main__':raise SystemExit(main())
