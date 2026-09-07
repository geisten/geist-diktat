#!/usr/bin/env python3
"""Check the installed launcher/profile/setup/doctor with a real German fixture.

Only numeric evidence is exported. Uses an isolated HOME and cached model; no
microphone, network setup, desktop changes or user profile changes.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
from dictation import digest
from quality import score
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('prefix','model','manifest','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prefix=a.prefix.resolve();launcher=prefix/'bin/geist-diktat'
    manifest=json.loads(a.manifest.read_text());fixture=next(f for f in manifest if f['group']=='de-read-clean')
    wav=a.manifest.parent/fixture['wav']
    if digest(wav)!=fixture['sha256']:raise ValueError('fixture hash mismatch')
    with tempfile.TemporaryDirectory(prefix='geist-installed-') as d:
        d=Path(d);data=d/'data/geist-diktat';data.mkdir(parents=True)
        (data/'ggml-small-q5_1.bin').symlink_to(a.model.resolve())
        env=dict(os.environ,HOME=str(d),XDG_DATA_HOME=str(d/'data'),XDG_CONFIG_HOME=str(d/'config'),XDG_RUNTIME_DIR=str(d/'r'),GEIST_DIKTAT_CAPTURE='true')
        for key in ('GEIST_DIKTAT_PROFILE','GEIST_DIKTAT_CORE','GEIST_DIKTAT_MODEL','GEIST_WHISPER_BEAM_SIZE','OMP_NUM_THREADS'):env.pop(key,None)
        def call(*args):return subprocess.run([str(launcher),*args],env=env,capture_output=True,text=True,timeout=120)
        chosen=call('profile','show');assert chosen.returncode==0,chosen.stderr
        assert json.loads(chosen.stdout)['name']=='whisper-small'
        saved=call('profile','use','whisper-small');assert saved.returncode==0,saved.stderr
        setup=call('setup');assert setup.returncode==0,setup.stderr
        checked=call('doctor','--verify','--json');assert checked.returncode==0,checked.stderr
        doctor=json.loads(checked.stdout);assert doctor['profile']['parameters']==dict(threads=4,beam_size=5)
        env['GEIST_DIKTAT_CAPTURE']=shlex.join([sys.executable,str(ROOT/'benchmarks/trace_capture.py'),str(wav.resolve())])
        env['GEIST_DIKTAT_TRACE']=str(d/'trace.jsonl')
        start=time.monotonic()
        try:recognition=call('run');elapsed=time.monotonic()-start
        finally:call('worker','stop')
        measured=score(fixture['reference'],' '.join(recognition.stdout.splitlines()))
        result=dict(source_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
            passed=recognition.returncode==0 and measured['wer']==0,scope='one paced known clean German clip through installed profile/setup/doctor/run; no general WER or desktop acceptance',
            profile='whisper-small',parameters=doctor['profile']['parameters'],package_profile=doctor['package_profile'],
            setup_exit=setup.returncode,doctor_exit=checked.returncode,run_exit=recognition.returncode,
            wall_s=elapsed,score=measured,fixture_sha256=fixture['sha256'],model_sha256=digest(a.model),
            installed_binary_sha256=digest(prefix/'bin/diktat-whisper'),physical_microphone=False)
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
