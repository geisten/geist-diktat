#!/usr/bin/env python3
"""Sequential screening, not a statistically conclusive optimization claim.

Two fixed German clips per setting, paced input. Run on an otherwise idle Pi.
Selected candidates need repeated tests and long-conversation validation.
GEIST_AUDIO_STREAM changes early vs lazy worker creation here: audio_begin
always starts streaming. These values are NOT streaming off/on.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','binary','model','tower','mel','output_dir'):
        ap.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    a=ap.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
    for stream,threads,wait in [(0,1,'PASSIVE'),(1,1,'PASSIVE'),(0,2,'PASSIVE'),(1,2,'PASSIVE'),(0,4,'PASSIVE'),(1,4,'PASSIVE'),(0,4,'ACTIVE')]:
        cmd=[sys.executable,str(Path(__file__).with_name('quality.py'))]
        for name in ('manifest','binary','model','tower','mel'):cmd+=['--'+name,str(getattr(a,name))]
        cmd+=['--output',str(a.output_dir/f'stream{stream}-threads{threads}-{wait.lower()}.json'),
              '--threads',str(threads),'--groups','de-read-clean','--limit','2','--paced','--timeout','180']
        print(f'CONFIG stream={stream} threads={threads} wait={wait}',flush=True)
        subprocess.run(cmd,env=dict(os.environ,GEIST_AUDIO_STREAM=str(stream),OMP_WAIT_POLICY=wait),check=True)

if __name__=='__main__':main()
