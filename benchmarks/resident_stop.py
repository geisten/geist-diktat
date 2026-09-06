#!/usr/bin/env python3
"""Measure SIGTERM during actual resident model decoding; no GUI/microphone."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
import time
import wave
from dictation import digest

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('binary','model','wav','output'):parser.add_argument('--'+n,type=Path,required=True)
    a=parser.parse_args()
    with wave.open(str(a.wav),'rb') as w:
        if (w.getframerate(),w.getnchannels(),w.getsampwidth())!=(16000,1,2):raise ValueError('invalid PCM fixture')
        pcm=w.readframes(w.getnframes())+bytes(32000)
    with tempfile.TemporaryDirectory(prefix='geist-stop-') as temp:
        temp=Path(temp);trace=temp/'trace.jsonl';started=False
        with (temp/'out').open('wb') as out,(temp/'err').open('wb') as err:
            proc=subprocess.Popen([str(a.binary.resolve()),str(a.model.resolve())],stdin=subprocess.PIPE,
                stdout=out,stderr=err,start_new_session=True,
                env=dict(os.environ,GEIST_DIKTAT_TRACE=str(trace),OMP_NUM_THREADS='4'))
            def feed():
                try:proc.stdin.write(pcm);proc.stdin.flush()
                except (OSError,BrokenPipeError):pass
                finally:
                    try:proc.stdin.close()
                    except (OSError,BrokenPipeError):pass
            feeder=threading.Thread(target=feed,daemon=True);feeder.start();deadline=time.monotonic()+60
            try:
                while proc.poll() is None and time.monotonic()<deadline:
                    lines=trace.read_text().splitlines() if trace.exists() else []
                    try:events=[json.loads(s) for s in lines]
                    except ValueError:continue
                    begins=sum(r['event']=='decode_start' for r in events)
                    ends=sum(r['event']=='decode_end' for r in events)
                    if begins>ends:started=True;break
                    time.sleep(.002)
                before=len((temp/'out').read_bytes());stop=time.monotonic();proc.terminate()
                killed=False
                try:proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    killed=True;os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                elapsed=time.monotonic()-stop
            finally:
                if proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                feeder.join(2)
        after=len((temp/'out').read_bytes())
        result=dict(passed=started and not killed and proc.returncode==143 and after==before and elapsed<1,
            scope='SIGTERM after observed decode_start; real CPU model; excludes loading, GUI and physical capture',
            decode_started=started,forced_kill=killed,stop_s=elapsed,exit_code=proc.returncode,
            output_bytes_after_stop=after-before,files={n:digest(getattr(a,n)) for n in ('binary','model','wav')})
        a.output.parent.mkdir(exist_ok=True,parents=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
