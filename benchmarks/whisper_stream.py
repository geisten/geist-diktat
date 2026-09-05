#!/usr/bin/env python3
"""Experimental whisper.cpp CPU comparison, PCM16LE stdin -> UTF-8 lines.

Model reloads per segment. This is a benchmark adapter, not the release default.
Audio stays in memory. Uses the same 3/40-frame RMS VAD and 28-second cap.
"""
from array import array
import io
import math
import os
from pathlib import Path
import subprocess
import sys
import wave


def recognize(pcm,model):
    if len(pcm)<16000:return
    wav=io.BytesIO()
    with wave.open(wav,'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(pcm)
    cli=os.environ.get('GEIST_WHISPER_CLI','whisper-cli')
    r=subprocess.run([cli,'-m',model,'-f','-','-l','de','-nt','-np','-ng','-t',os.environ.get('OMP_NUM_THREADS','4')],
                     input=wav.getvalue(),capture_output=True,timeout=180)
    if r.returncode:
        sys.stderr.buffer.write(r.stderr);raise RuntimeError('whisper-cli failed: '+str(r.returncode))
    text=' '.join(r.stdout.decode('utf-8').split())
    if text:print(text,flush=True)


def main():
    if len(sys.argv) not in (2,3):raise ValueError('usage: whisper_stream.py MODEL [RMS]')
    model=sys.argv[1];threshold=float(sys.argv[2]) if len(sys.argv)==3 else 300
    if not math.isfinite(threshold) or not 0<threshold<=32768:raise ValueError('invalid RMS')
    if not Path(model).is_file():raise ValueError('model missing')
    print('diktat: listening (experimental whisper CPU; per-segment model reload)',file=sys.stderr,flush=True)
    pre=[];active=False;pcm=bytearray();quiet=0;trailing=0
    while True:
        frame=sys.stdin.buffer.read(640)
        if not frame:
            if active:recognize(pcm,model)
            return 0
        if len(frame)%2:raise ValueError('incomplete PCM16 sample')
        samples=array('h',frame)
        if sys.byteorder!='little':samples.byteswap()
        loud=math.sqrt(sum(x*x for x in samples)/320)>threshold
        if not active:
            if loud:pre.append(frame)
            else:pre=[]
            if len(pre)<3:continue
            active=True;pcm=bytearray(b''.join(pre));pre=[];quiet=0;trailing=0
        else:pcm.extend(frame)
        if loud:quiet=0;trailing=0
        else:quiet+=1;trailing+=len(frame)
        if quiet>=40 or len(pcm)>=28*32000:
            recognize(pcm,model)
            active=False;pcm=bytearray();quiet=0;trailing=0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as e:
        print('diktat: '+str(e),file=sys.stderr);raise SystemExit(1)
