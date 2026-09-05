#!/usr/bin/env python3
"""Publish numeric product-test evidence only, excluding transcript/stderr content."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NAMES=['product-pi-quality','product-mac-quality-contended','product-mac-whisper-validated',
       'product-mac-whisper-dialects','product-pi-whisper','product-pi-whisper-beam1',
       'product-pi-live','product-pi-whisper-live','product-pi-whisper-beam1-live','product-mac-final-smoke','product-pi-final-smoke']
report={'scope':'Development pilot; no physical microphone certification or representative DACH claim.',
        'whisper_source_commit':'52a939a2a762224e255d366c1182b2af4dd1a032',
        'mac_timing_warning':'Unrelated engine stress tests ran concurrently; Mac timings cannot establish idle-speed superiority.',
        'excluded':'Initial Whisper adapter experiments with incorrect stdout flags are instrumentation failures, not ASR accuracy results.',
        'tests':{'macos_unittest':77,'ubuntu_arm64_unittest':77,'nvim_toggle_cycles':100,'ibus_toggle_cycles':100,'vim_toggle_cycles':100,
                 'core_line_coverage_percent':98.08,'core_branch_coverage_percent':73.27,
                 'coverage_scope':'src/diktat.c with controlled fake engine, ASan and UBSan; not model/driver/UI coverage'},'results':{}}
for name in NAMES:
    p=ROOT/'build'/(name+'.json')
    if not p.exists():continue
    d=json.loads(p.read_text())
    for row in [d,*d.get('runs',[])]:
        row.pop('transcript',None);row.pop('stderr',None)
    if 'runs' in d:
        refs=[r['dialect_score'] for r in d['runs'] if 'dialect_score' in r]
        if refs:d['dialect_orthography_wer']=sum(x['errors'] for x in refs)/sum(x['reference_words'] for x in refs)
    report['results'][name]=d
out=ROOT/'benchmarks/reports/product-2026-09-06.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(out)
