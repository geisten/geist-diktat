#!/usr/bin/env python3
"""Validate the selected worker's complete German development pilot.

This is not an independent speech, microphone, latency or product-release gate.
"""
import argparse
import json
import math
import re
from pathlib import Path
from quality import aggregate

MODEL_SHA='ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb'
GROUPS={'de-read-clean':(12,294,.10),'de-noise-10db':(6,130,.25)}


def require(condition,message):
    if not condition:raise ValueError(message)


def number(value):return type(value) in (int,float) and math.isfinite(value)

def close(a,b):return number(a) and number(b) and math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-6)


def evaluate(report,expected_commit):
    result=dict(passed=False,scope=__doc__,expected_commit=expected_commit,failures=[],groups={})
    try:
        require(report['source_commit']==expected_commit,'source commit mismatch')
        require(report['working_tree_dirty'] is False,'working tree is not clean')
        require(report['files']['model']==MODEL_SHA,'wrong model SHA')
        for name in ('binary','manifest'):
            require(type(report['files'][name]) is str and bool(re.fullmatch('[0-9a-f]{64}',report['files'][name])),'missing or invalid '+name+' hash')
        for name in ('src/whisper_diktat.cpp','runtime/model_worker.py','runtime/pipe_limits.py','benchmarks/worker_bench.py'):
            require(type(report['implementation_sha256'][name]) is str and bool(re.fullmatch('[0-9a-f]{64}',report['implementation_sha256'][name])),'missing or invalid implementation hash')
        require(report['paced'] is False,'quality gate requires unpaced throughput pilot')
        require(report['audio_context']=='full' and report['chunk_seconds']==28 and report['temperature_fallback'] is True,'unselected audio context/window/fallback')
        require(len(report['configs'])==1,'expected exactly one selected worker configuration')
        config=report['configs'][0]
        require(config['threads']==4 and config['beam_size']==5 and config['wait_policy']=='PASSIVE','unselected decoder parameters')
        require(config['all_audio_accounted'] is True,'worker reports incomplete audio')
        runs=config['runs'];require(len(runs)==18,'expected all 18 pilot fixtures')
        ids=set();pids=set()
        for row in runs:
            require(type(row['id']) is str and row['id'] and row['id'] not in ids,'missing or duplicate fixture id');ids.add(row['id'])
            require(type(row['wav_sha256']) is str and bool(re.fullmatch('[0-9a-f]{64}',row['wav_sha256'])),'missing or invalid fixture hash')
            require(row['group'] in GROUPS,'unexpected fixture group')
            require(row['passed'] is True and type(row['exit_code']) is int and row['exit_code']==0,'failed fixture')
            require(not row['source'].get('failed',False),'failed audio source')
            require(type(row['core_samples']) is int and row['core_samples']>0,'invalid core sample count')
            require(type(row['source']['sent_bytes']) is int and row['source']['sent_bytes']==2*row['core_samples'],'incomplete source/core byte balance')
            require(number(row['supplied_audio_s']) and close(row['supplied_audio_s']*16000,row['core_samples']),'supplied audio/sample mismatch')
            require(number(row['audio_s']) and row['audio_s']>0 and close(row['supplied_audio_s'],row['audio_s']+1),'invalid fixture duration or padding')
            require(number(row['wall_s']) and row['wall_s']>0,'invalid wall time')
            for key in ('errors','substitutions','deletions','insertions','reference_words'):
                require(type(row[key]) is int and row[key]>=0,'invalid word count')
            require(row['reference_words']>0 and row['errors']==row['substitutions']+row['deletions']+row['insertions'],'inconsistent word error counts')
            require(close(row['wer'],row['errors']/row['reference_words']),'inconsistent fixture WER')
            require(type(row['worker_pid']) is int and row['worker_pid']>0,'invalid model PID');pids.add(row['worker_pid'])
        require(len(pids)==1,'model was not reused across all fixtures')
        computed=aggregate(runs)
        require(set(config['groups'])==set(GROUPS),'missing or unexpected aggregate group')
        for name,(clips,words,limit) in GROUPS.items():
            actual=computed[name];stored=config['groups'][name]
            require(actual['clips']==clips and actual['reference_words']==words,'incorrect pilot coverage for '+name)
            for key in ('clips','errors','reference_words','substitutions','deletions','insertions','failed'):
                require(type(stored[key]) is int and stored[key]==actual[key],'inconsistent aggregate '+name+'/'+key)
            for key in ('audio_s','wall_s','wer','wall_rtf'):
                require(close(stored[key],actual[key]),'inconsistent aggregate '+name+'/'+key)
            result['groups'][name]=dict(wer=actual['wer'],limit=limit,passed=actual['wer']<=limit)
            if actual['wer']>limit:result['failures'].append(name+' exceeds WER limit')
        result['passed']=not result['failures']
    except (KeyError,TypeError,ValueError,OverflowError) as error:
        result['failures'].append('invalid worker evidence: '+str(error))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('report',type=Path)
    p.add_argument('--expected-commit',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:report=json.loads(a.report.read_text());result=evaluate(report,a.expected_commit)
    except (OSError,ValueError) as error:result=dict(passed=False,failures=['cannot read worker evidence: '+str(error)])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result));return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
