#!/usr/bin/env python3
"""Fail-closed speech-quality prerequisite; this is not full product approval."""
import argparse
import json
import math
from pathlib import Path
import re
from quality import aggregate


def number(value, minimum=0):
    return type(value) in (int, float) and math.isfinite(value) and value >= minimum


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def sha(value, length=64):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{'+str(length)+'}', value) is not None


def evaluate(report, policy, expected_commit=None):
    checks=[]
    def check(name, passed, reason):
        checks.append(dict(check=name, passed=bool(passed), reason=reason))
    if not isinstance(report, dict) or not isinstance(policy, dict):
        return dict(passed=False, checks=[dict(check='schema', passed=False, reason='JSON objects required')])
    rules=policy.get('groups')
    if not isinstance(rules, dict) or not rules:
        return dict(passed=False, checks=[dict(check='policy', passed=False, reason='nonempty groups required')])
    groups=report.get('groups', {})
    if not isinstance(groups, dict):groups={}
    if expected_commit is not None:
        check('commit', sha(expected_commit,40) and report.get('source_commit')==expected_commit,
              'evidence must match the exact candidate commit')
    if policy.get('require_run_evidence'):
        files=report.get('files', {})
        check('provenance', isinstance(files,dict) and all(sha(files.get(k)) for k in policy.get('required_files',[]))
              and sha(report.get('manifest_sha256')) and sha(report.get('source_commit'),40)
              and bool(report.get('platform')) and integer(report.get('threads'),1),
              'binary/model/corpus hashes, source commit, platform and thread count required')
        if policy.get('engines'):
            engines=policy['engines']
            engine=report.get('engine')
            rule=engines.get(engine) if isinstance(engines,dict) and isinstance(engine,str) else None
            check('engine',isinstance(rule,dict) and isinstance(files,dict)
                  and all(sha(files.get(k)) for k in rule.get('required_files',[]))
                  and all(sha(report.get(k)) for k in rule.get('required_report_hashes',[])),
                  'known engine and all engine-specific artifact hashes required')
        rows=report.get('runs')
        valid=isinstance(rows,list) and bool(rows)
        ids=set()
        if valid:
            for row in rows:
                if not isinstance(row,dict):valid=False;break
                ident=row.get('id')
                if (not isinstance(ident,str) or not ident or ident in ids
                    or not isinstance(row.get('group'),str) or not sha(row.get('wav_sha256'))
                    or not integer(row.get('reference_words'),1)
                    or not all(integer(row.get(k)) for k in ('errors','substitutions','deletions','insertions'))
                    or row['errors']!=sum(row[k] for k in ('substitutions','deletions','insertions'))
                    or not number(row.get('audio_s')) or row['audio_s']==0
                    or not number(row.get('wall_s')) or type(row.get('exit_code')) is not int
                    or type(row.get('timeout',False)) is not bool
                    or not number(row.get('wer'))
                    or not math.isclose(row['wer'],row['errors']/row['reference_words'],rel_tol=1e-9,abs_tol=1e-12)):
                    valid=False;break
                ids.add(ident)
        check('runs',valid,'unique complete per-clip evidence with consistent edit counts required')
        if valid:
            recalculated=aggregate(rows)
            for name in rules:
                observed=groups.get(name,{})
                actual=recalculated.get(name,{})
                same=isinstance(observed,dict) and bool(actual)
                if same:
                    for key,value in actual.items():
                        candidate=observed.get(key)
                        if not number(candidate) or not math.isclose(candidate,value,rel_tol=1e-9,abs_tol=1e-12):
                            same=False;break
                check('aggregate:'+name,same,'reported totals must match per-clip evidence')
    for name,rule in rules.items():
        valid=(isinstance(rule,dict) and integer(rule.get('min_clips'),1)
               and number(rule.get('max_wer')) and integer(rule.get('min_reference_words',1),1))
        check('policy:'+name,valid,'positive sample minima and finite nonnegative WER limit required')
        g=groups.get(name,{})
        ok=(valid and isinstance(g,dict) and integer(g.get('clips'),rule['min_clips'])
            and type(g.get('failed')) is int and g['failed']==0
            and number(g.get('wer')) and g['wer']<=rule['max_wer'])
        if isinstance(rule,dict) and (policy.get('require_run_evidence') or 'min_reference_words' in rule):
            ok=ok and integer(g.get('reference_words'),rule.get('min_reference_words',1))
        check('quality:'+name,ok,'complete successful corpus group within its WER limit')
    return dict(passed=all(c['passed'] for c in checks),scope='speech-quality prerequisite, not full beta approval',checks=checks)


def read_json(path):
    def reject(value):raise ValueError('non-finite JSON number: '+value)
    return json.loads(path.read_text(),parse_constant=reject)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('report',type=Path)
    p.add_argument('--policy',type=Path,default=Path(__file__).with_name('release-gates.json'))
    p.add_argument('--expected-commit');p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:result=evaluate(read_json(a.report),read_json(a.policy),a.expected_commit)
    except (OSError,ValueError,TypeError) as e:
        result=dict(passed=False,checks=[dict(check='input',passed=False,reason=str(e))])
    payload=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(payload)
    print(payload,end='');return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
