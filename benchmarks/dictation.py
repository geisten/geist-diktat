#!/usr/bin/env python3
"""Measure the real binary with file-fed PCM; no microphone or GUI access.

Each repetition is a fresh process. OS caches are not evicted. Results include
wall time, startup readiness, per-process peak RSS, transcript, WER, timeouts,
and (with --paced) delivery latency relative to the last loud input frame.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import statistics
import subprocess
import threading
import time
import wave

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(8*1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def wer(ref, hyp):
    norm = lambda x: re.sub(r"[^\w' ]+", ' ', x.lower()).split()
    r, h = norm(ref), norm(hyp)
    prev = list(range(len(h)+1))
    for i, w in enumerate(r, 1):
        cur = [i]
        for j, v in enumerate(h, 1):
            cur.append(min(prev[j]+1, cur[j-1]+1, prev[j-1]+(w!=v)))
        prev = cur
    return {'errors':prev[-1], 'reference_words':len(r), 'wer':prev[-1]/len(r) if r else None}

def run(args, pcm, seconds):
    ready = threading.Event()
    stderr, transcript, times, state = [], [], [], {}
    env = dict(os.environ, GEIST_AUDIO_MODEL_PATH=str(args.tower),
               GEIST_MEL_CONSTANTS_PATH=str(args.mel), OMP_NUM_THREADS=str(args.threads))
    start=time.monotonic()
    p=subprocess.Popen([str(args.binary),str(args.model),'300'], stdin=subprocess.PIPE,
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,start_new_session=True)
    def errors():
        for line in iter(p.stderr.readline,b''):
            stderr.append(line.decode(errors='replace'))
            if b'diktat: listening' in line:
                state['ready_s']=time.monotonic()-start
                ready.set()
    def output():
        for line in iter(p.stdout.readline,b''):
            transcript.append(line.decode(errors='replace').rstrip('\n'))
            times.append(time.monotonic()-start)
    def feed():
        if not ready.wait(args.timeout):
            return
        if 'ready_s' not in state:
            return
        state['feed_start_s']=time.monotonic()-start
        base=time.monotonic()
        try:
            for offset in range(0,len(pcm),640):
                if args.paced:
                    time.sleep(max(0,base+offset/32000-time.monotonic()))
                p.stdin.write(pcm[offset:offset+640])
                p.stdin.flush()
            state['feed_finished_s']=time.monotonic()-start
        except (BrokenPipeError, OSError):
            state['broken_pipe']=True
        finally:
            try: p.stdin.close()
            except BrokenPipeError: pass
    def expire():
        state['timeout']=True
        try: os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError: pass
    readers=[threading.Thread(target=f,daemon=True) for f in (errors,output,feed)]
    for t in readers: t.start()
    timer=threading.Timer(args.timeout,expire)
    timer.start()
    _, status, usage=os.wait4(p.pid,0)
    p.returncode=os.waitstatus_to_exitcode(status)
    elapsed=time.monotonic()-start
    timer.cancel()
    ready.set()
    for t in readers: t.join(3)
    rss=usage.ru_maxrss/(1024*1024 if platform.system()=='Darwin' else 1024)
    result=dict(state,exit_code=p.returncode,wall_s=elapsed,peak_rss_mib=rss,
        cpu_s=usage.ru_utime+usage.ru_stime,audio_s=seconds,
        wall_rtf=elapsed/seconds if seconds else None,
        processing_s=elapsed-state['ready_s'] if 'ready_s' in state else None,
        transcript=transcript,output_times_s=times,stderr=''.join(stderr))
    if args.paced and times and 'feed_start_s' in state:
        # Relative to the END of the supplied speech fixture (which may itself
        # contain trailing silence); the appended VAD silence is excluded.
        result['first_output_after_fixture_end_s']=times[0]-state['feed_start_s']-seconds
    if args.reference:
        result.update(wer(args.reference.read_text(),' '.join(transcript)))
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--binary',type=Path,default=ROOT/'diktat')
    ap.add_argument('--model',type=Path,required=True)
    ap.add_argument('--tower',type=Path,required=True)
    ap.add_argument('--mel',type=Path,default=ROOT/'geistlib/audio_test_data/mel_constants.bin')
    ap.add_argument('--wav',type=Path,default=ROOT/'tests/fixtures/librispeech-1089-134691-0016.wav')
    ap.add_argument('--reference',type=Path,default=ROOT/'tests/fixtures/librispeech-1089-134691-0016.txt')
    ap.add_argument('--repeats',type=int,default=3)
    ap.add_argument('--threads',type=int,default=4)
    ap.add_argument('--timeout',type=float,default=300)
    ap.add_argument('--silence',type=float,default=1)
    ap.add_argument('--paced',action='store_true')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    if args.repeats<1 or args.threads<1 or args.timeout<=0 or args.silence<0:
        ap.error('repeats/threads/timeout must be positive and silence nonnegative')
    for name in ('binary','model','tower','mel','wav'):
        setattr(args,name,getattr(args,name).resolve(strict=True))
    # Never mistake an incomplete copy or an old local model for this release.
    for name, expected in [('model','740185b21d22ceb83a11c3aa62ad5842ef32c70f6096d756bbee85a1e4ec34b8'),
                           ('tower','d6c45a6c276212dc3a793e66dfc588d89c12d1ac92c0e4b85494390ca848cd77')]:
        if digest(getattr(args,name)) != expected:
            ap.error(name+' does not match the pinned release SHA-256')
    with wave.open(str(args.wav)) as w:
        if (w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getcomptype()) != (16000,1,2,'NONE'):
            ap.error('WAV must be 16 kHz mono PCM16')
        pcm=w.readframes(w.getnframes())
    seconds=len(pcm)/32000
    pcm+=bytes(round(args.silence*32000))
    meta={'platform':platform.platform(),'machine':platform.machine(),'python':platform.python_version(),
          'date_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
          'threads':args.threads,'paced':args.paced,'appended_silence_s':args.silence,
          'cache_policy':'fresh process; OS caches NOT flushed; hashes read before runs',
          'files':{name:{'path':str(getattr(args,name)),'sha256':digest(getattr(args,name))}
                   for name in ('binary','model','tower','mel','wav')}, 'runs':[]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for i in range(args.repeats):
        result=run(args,pcm,seconds)
        meta['runs'].append(result)
        meta['median_wall_s']=statistics.median(r['wall_s'] for r in meta['runs'])
        args.output.write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps({'run':i+1,**{k:result.get(k) for k in ('exit_code','wall_s','ready_s','peak_rss_mib','wer','transcript','timeout')}},ensure_ascii=False),flush=True)
        if result.get('timeout') or result['exit_code']:
            break
    return int(any(r['exit_code'] or r.get('timeout') or not r['transcript'] for r in meta['runs']))

if __name__=='__main__':
    raise SystemExit(main())
