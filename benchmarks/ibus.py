#!/usr/bin/env python3
"""Private daemon startup + stub Unicode commit + teardown (not ASR)."""
import argparse
import json
from pathlib import Path
import platform
import statistics
import subprocess
import time

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output',type=Path,required=True)
ap.add_argument('--repeats',type=int,default=5)
args=ap.parse_args()
if args.repeats<1: ap.error('repeats must be positive')
root=Path(__file__).resolve().parents[1]
rows=[]
for i in range(args.repeats):
    start=time.monotonic()
    p=subprocess.run(['sh','tests/ibus_isolated.sh'],cwd=root,capture_output=True,timeout=30)
    rows.append({'wall_ms':1000*(time.monotonic()-start),'exit_code':p.returncode,
                 'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')})
    if p.returncode: break
result={'platform':platform.platform(),'scope':__doc__,'runs':rows,
        'median_ms':statistics.median(r['wall_ms'] for r in rows)}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(result,ensure_ascii=False))
raise SystemExit(int(any(r['exit_code'] for r in rows)))
