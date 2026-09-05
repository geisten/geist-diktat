#!/usr/bin/env python3
"""Export reviewable numeric results; never redistribute corpus transcripts."""
import json
from pathlib import Path
import statistics

root=Path(__file__).resolve().parents[1]
source=root/'build/speech-results'
report={'scope':'German/DACH pilot, not representative product certification','runs':{},'pi_sweep':[]}
for name in ('macos-quality','pi5-quality','macos-conversation','pi5-conversation'):
    path=source/(name+'.json')
    if not path.exists():continue
    d=json.loads(path.read_text())
    for r in d['runs']:
        r.pop('transcript',None);r.pop('stderr',None)
    if name.endswith('quality'):
        clean=[r for r in d['runs'] if r['group']=='de-read-clean'][:6]
        d['clean_noise_control']={'clips':len(clean),'errors':sum(r['errors'] for r in clean),'reference_words':sum(r['reference_words'] for r in clean)}
        c=d['clean_noise_control'];c['wer']=c['errors']/c['reference_words']
        dialect=[r['dialect_score'] for r in d['runs'] if 'dialect_score' in r]
        d['dialect_orthography_wer']=sum(r['errors'] for r in dialect)/sum(r['reference_words'] for r in dialect)
    report['runs'][name]=d
for p in sorted((source/'pi-sweep').glob('*.json')):
    d=json.loads(p.read_text());rows=d['runs']
    report['pi_sweep'].append(dict(configuration=p.stem,clips=len(rows),environment=d['environment'],threads=d['threads'],
        wall_s=sum(r['wall_s'] for r in rows),mean_final_latency_s=statistics.mean(r['last_output_after_audio_end_s'] for r in rows),
        wer=d['groups']['de-read-clean']['wer'],max_rss_mib=max(r['peak_rss_mib'] for r in rows),
        note='GEIST_AUDIO_STREAM is early vs lazy worker creation; session API starts streaming in both cases'))
for folder in ('ubuntu-agent','ubuntu-comparison'):
    for p in sorted((source/folder).glob('*.json')):
        d=json.loads(p.read_text());report['runs'][folder+'/'+p.stem]=d
out=root/'benchmarks/reports/quality-2026-09-05.json';out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(out)
