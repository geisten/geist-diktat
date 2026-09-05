#!/usr/bin/env python3
"""Evaluate explicit pilot gates, failing closed for missing/failed groups."""
import argparse
import json
from pathlib import Path

def evaluate(report,policy):
    results=[]
    for name,rule in policy['groups'].items():
        group=report.get('groups',{}).get(name,{})
        ok=(group.get('clips',0)>=rule['min_clips'] and group.get('failed',1)==0
            and group.get('wer') is not None and group['wer']<=rule['max_wer'])
        results.append(dict(group=name,passed=ok,observed=group,required=rule))
    return dict(passed=bool(results) and all(r['passed'] for r in results),checks=results)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('report',type=Path)
    p.add_argument('--policy',type=Path,default=Path(__file__).with_name('release-gates.json'))
    a=p.parse_args();result=evaluate(json.loads(a.report.read_text()),json.loads(a.policy.read_text()))
    print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
