#!/usr/bin/env python3
"""Paced PCM file source for a controlled trace; never opens a microphone."""
import argparse
from pathlib import Path
import sys
import time
import wave
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from trace_metrics import emit


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('wav',type=Path)
    a=p.parse_args()
    with wave.open(str(a.wav)) as w:
        if (w.getframerate(),w.getnchannels(),w.getsampwidth())!=(16000,1,2):
            p.error('PCM16 mono 16kHz required')
        # Timestamp the ideal audio timeline separately from delayed pipe writes.
        origin=time.monotonic_ns();emit('capture','audio_origin',origin_ns=origin)
        sent=0;max_lateness=0
        try:
            while data:=w.readframes(320):
                target=origin+sent*1_000_000_000//32000
                time.sleep(max(0,(target-time.monotonic_ns())/1e9))
                sys.stdout.buffer.write(data);sys.stdout.buffer.flush()
                max_lateness=max(max_lateness,time.monotonic_ns()-target)
                sent+=len(data)
        except BrokenPipeError:
            # Do not turn an overload-induced source interruption into success.
            emit('capture','source_summary',sent_bytes=sent,max_lateness_ns=max_lateness,failed=True)
            return 1
        emit('capture','source_summary',sent_bytes=sent,max_lateness_ns=max_lateness,failed=False)
    return 0

if __name__=='__main__':raise SystemExit(main())
