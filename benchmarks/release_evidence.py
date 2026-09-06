#!/usr/bin/env python3
"""Require successful speech evidence for the exact commit before publishing.

Reads GitHub Actions through gh. Does not start jobs or publish a release.
This enforces only the speech prerequisite, not the external usability approval.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile
from check_gates import evaluate, read_json, sha


def select_run(runs, commit):
    if not sha(commit,40) or not isinstance(runs,list) or not runs:
        raise ValueError('no quality-audit run for candidate commit')
    # gh run list returns newest first. Never hide a newer failed/pending run by
    # falling back to an older successful attempt.
    run=runs[0]
    if (run.get('headSha')!=commit or run.get('status')!='completed'
        or run.get('conclusion')!='success' or type(run.get('databaseId')) is not int):
        raise ValueError('latest quality-audit run is incomplete, failed or for another commit')
    return run['databaseId']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',required=True);p.add_argument('--commit',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=dict(passed=False)
    try:
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',a.repo) or not sha(a.commit,40):
            raise ValueError('invalid repository or commit')
        raw=subprocess.check_output(['gh','run','list','--repo',a.repo,'--workflow','quality-audit.yml',
            '--event','workflow_dispatch','--commit',a.commit,'--limit','1',
            '--json','databaseId,headSha,status,conclusion'],text=True,timeout=60)
        run_id=select_run(json.loads(raw),a.commit)
        with tempfile.TemporaryDirectory(prefix='geist-release-evidence-') as temp:
            subprocess.run(['gh','run','download',str(run_id),'--repo',a.repo,'--name',
                'ubuntu-agent-speech-metrics','--dir',temp],check=True,timeout=60)
            report=read_json(Path(temp)/'ubuntu-agent-quality.json')
            policy=read_json(Path(__file__).with_name('release-gates.json'))
            result=evaluate(report,policy,a.commit)
            result.update(run_id=run_id,source_commit=a.commit,repository=a.repo)
    except (OSError,ValueError,subprocess.SubprocessError) as e:
        result=dict(passed=False,error=str(e))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
