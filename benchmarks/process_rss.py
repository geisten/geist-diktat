#!/usr/bin/env python3
"""Read-only ps RSS probe for one owned process tree; no swap/thermal claims.

Starts when invoked, not at model startup. Guards against PID reuse by checking
process start time and uid. Shared resident pages may be counted more than once.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import time


def output(args):
    return subprocess.run(['ps',*args],capture_output=True,text=True,check=False).stdout.strip()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pid',type=int,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-minutes',type=float,default=40);p.add_argument('--interval',type=float,default=5)
    a=p.parse_args()
    if a.pid<=0 or not 0<a.max_minutes<=120 or not 1<=a.interval<=60:p.error('invalid limits')
    identity=output(['-p',str(a.pid),'-o','uid=,lstart='])
    if not identity or int(identity.split()[0])!=os.getuid():p.error('root process must exist and belong to this user')
    started=time.monotonic();rows=[];errors=0
    while time.monotonic()-started<a.max_minutes*60:
        if output(['-p',str(a.pid),'-o','uid=,lstart='])!=identity:break
        entries={}
        for line in output(['-ax','-o','pid=,ppid=,rss=']).splitlines():
            fields=line.split()
            if len(fields)==3:
                try:pid,parent,rss=map(int,fields);entries[pid]=(parent,rss)
                except ValueError:errors+=1
        if a.pid not in entries:break
        selected={a.pid}
        while True:
            extra={pid for pid,(parent,_) in entries.items() if parent in selected}-selected
            if not extra:break
            selected.update(extra)
        rows.append(dict(elapsed_s=time.monotonic()-started,rss_mib=sum(entries[pid][1] for pid in selected)/1024,pids=sorted(selected)))
        time.sleep(a.interval)
    elapsed=time.monotonic()-started
    first=[r['rss_mib'] for r in rows if r['elapsed_s']<300]
    last=[r['rss_mib'] for r in rows if r['elapsed_s']>=max(300,elapsed-300)]
    result=dict(scope=__doc__,platform=platform.platform(),root_pid=a.pid,root_identity=identity,
        started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time()-elapsed)),elapsed_s=elapsed,
        root_exited=output(['-p',str(a.pid),'-o','uid=,lstart='])!=identity,interval_s=a.interval,
        sample_count=len(rows),parse_errors=errors,peak_rss_mib=max((r['rss_mib'] for r in rows),default=None),
        rss_median_growth_mib=statistics.median(last)-statistics.median(first) if first and last else None,
        samples=rows,full_model_lifetime=False,process_swap_measured=False,temperature_measured=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('root_exited','sample_count','peak_rss_mib','rss_median_growth_mib')}))
    return 0 if rows and not errors else 1

if __name__=='__main__':raise SystemExit(main())
