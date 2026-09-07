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
    # Full legacy-engine control matrix. Whisper does not implement these
    # Geist-specific subsampling/worker-start settings.
    settings=[(0,t,w,inc) for t in (1,2,4) for w in ('PASSIVE','ACTIVE') for inc in (0,1)]
    settings += [(1,4,'PASSIVE',inc) for inc in (0,1)]
    for stream,threads,wait,incremental in settings:
        cmd=[sys.executable,str(Path(__file__).with_name('quality.py'))]
        for name in ('manifest','binary','model','tower','mel'):cmd+=['--'+name,str(getattr(a,name))]
        cmd+=['--output',str(a.output_dir/f'stream{stream}-threads{threads}-{wait.lower()}-subsample{incremental}.json'),
              '--threads',str(threads),'--groups','de-read-clean','--limit','2','--paced','--timeout','180']
        print(f'CONFIG stream={stream} threads={threads} wait={wait} subsample_incremental={incremental}',flush=True)
        subprocess.run(cmd,env=dict(os.environ,GEIST_AUDIO_STREAM=str(stream),OMP_WAIT_POLICY=wait,GEIST_AUDIO_SUBSAMPLE_INC=str(incremental)),check=True)

if __name__=='__main__':main()
