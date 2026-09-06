#!/usr/bin/env python3
"""Analyze observed application insertion, not just stdout or IBus submission.

A trace belongs to ONE controlled local session. Uses CLOCK_MONOTONIC timestamps.
Speech endpoints must come from independent sample annotations. Current toolkit
probes observe one inserted line; this does not certify GNOME/Firefox/LibreOffice.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def analyze(events,annotations):
    def unique(component,event):
        rows=[r for r in events if r.get('component')==component and r.get('event')==event]
        if len(rows)!=1:raise ValueError('expected one '+component+'/'+event)
        return rows[0]
    if not isinstance(events,list) or not events or not isinstance(annotations,list) or not annotations:
        raise ValueError('nonempty trace and independent annotations required')
    for e in events:
        if not isinstance(e,dict) or e.get('schema')!=1 or type(e.get('monotonic_ns')) is not int or e['monotonic_ns']<0:
            raise ValueError('invalid trace event')
    origin=unique('capture','audio_origin')['origin_ns']
    if type(origin) is not int or origin<0:raise ValueError('invalid audio origin')
    runtime=unique('runtime','input_summary');core=unique('core','input_summary')
    source=unique('capture','source_summary')
    counts=[source.get('sent_bytes'),runtime.get('received_bytes'),runtime.get('delivered_bytes'),core.get('audio_end_sample')]
    if any(type(n) is not int or n<=0 for n in counts):raise ValueError('missing audio accounting')
    if counts[:3]!=[counts[0]]*3 or counts[0]!=counts[3]*2 or runtime.get('failed') is not False or source.get('failed') is not False:
        raise ValueError('incomplete/failed audio delivery; no successful live result')
    outputs={};observed={};endpoints={};emitted_sequences=[]
    for a in annotations:
        if (not isinstance(a,dict) or type(a.get('output_seq')) is not int or a['output_seq']<=0
            or a['output_seq'] in endpoints or type(a.get('end_sample')) is not int
            or not 0<a['end_sample']<=counts[3]):raise ValueError('invalid or duplicate annotation')
        endpoints[a['output_seq']]=a['end_sample']
    for e in events:
        if e.get('component')=='core' and e.get('event')=='output_emitted':emitted_sequences.append(e.get('output_seq'))
        target=outputs if e.get('component')=='core' and e.get('event')=='output_ready' else observed if e.get('event')=='app_observed' else None
        if target is not None:
            seq=e.get('output_seq')
            if type(seq) is not int or seq<=0 or seq in target:raise ValueError('duplicate/invalid output sequence')
            target[seq]=e
    if set(outputs)!=set(endpoints) or set(observed)!=set(endpoints) or sorted(emitted_sequences)!=sorted(endpoints):
        raise ValueError('every annotated output needs a core emission and application observation')
    values=[]
    for seq,sample in sorted(endpoints.items()):
        end=origin+sample*1_000_000_000//16000
        emitted=outputs[seq]['monotonic_ns'];inserted=observed[seq]['monotonic_ns']
        if not end<=emitted<=inserted:raise ValueError('noncausal timestamps or mismatched annotation')
        values.append(dict(output_seq=seq,speech_to_output_ready_s=(emitted-end)/1e9,
                           speech_to_insertion_s=(inserted-end)/1e9,output_ready_to_insertion_s=(inserted-emitted)/1e9))
    latencies=sorted(r['speech_to_insertion_s'] for r in values)
    p95=latencies[math.ceil(.95*len(latencies))-1]
    return dict(complete=True,scope='controlled file playback to observed application; not physical-microphone certification',
                annotation_source='independently supplied sample endpoints',samples=len(values),
                p95_method='nearest rank',p95_insertion_s=p95,measurements=values,runtime=runtime,
                capture=source,full_product_approval=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trace',type=Path,required=True);p.add_argument('--annotations',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--max-p95-seconds',type=float,default=3)
    a=p.parse_args()
    try:
        if not math.isfinite(a.max_p95_seconds) or a.max_p95_seconds<=0:raise ValueError('positive finite latency target required')
        events=[json.loads(line) for line in a.trace.read_text().splitlines()]
        result=analyze(events,json.loads(a.annotations.read_text()))
        result['passed']=result['p95_insertion_s']<=a.max_p95_seconds
        result['trace_sha256']=hashlib.sha256(a.trace.read_bytes()).hexdigest()
        result['annotations_sha256']=hashlib.sha256(a.annotations.read_bytes()).hexdigest()
    except (OSError,ValueError,KeyError,TypeError) as e:result=dict(passed=False,complete=False,error=str(e))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False));return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
