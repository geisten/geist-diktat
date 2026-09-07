#!/usr/bin/env python3
"""Stage one explicitly selected backend with its matching runtime metadata."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from model_profiles import PROFILES,validate

def stage(prefix,profile):
    profile=validate(profile);definition=PROFILES[profile]
    source=ROOT/'diktat' if profile=='geist' else ROOT/'build/whisper-resident/diktat-whisper'
    if not source.is_file() or not os.access(source,os.X_OK):raise ValueError('build the selected decoder first: '+str(source))
    share=prefix/'share/geist-diktat';binpath=prefix/'bin'
    share.mkdir(parents=True,exist_ok=True);binpath.mkdir(exist_ok=True)
    for path in (ROOT/'runtime').glob('*.py'):shutil.copy2(path,share/path.name)
    shutil.copy2(ROOT/'packaging/geist-diktat',binpath/'geist-diktat');(binpath/'geist-diktat').chmod(0o755)
    shutil.copy2(source,binpath/definition['binary'])
    for name in ('lua','plugin','autoload'):shutil.copytree(ROOT/name,share/'editor'/name)
    if profile=='geist':
        shutil.copy2(ROOT/'geistlib/audio_test_data/mel_constants.bin',share/'mel_constants.bin')
        shutil.copy2(ROOT/'geistlib/tools/fetch_audio_tower.py',share/'fetch_audio_tower.py')
    else:
        # The current binary is optimized for the build host. This profile is
        # deliberately a development package until distribution builds pass.
        licenses=prefix/'share/doc/geist-diktat/whisper';licenses.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/'build/whisper.cpp/LICENSE',licenses/'LICENSE')
    (share/'default-profile').write_text(profile+'\n')
    (share/'package-profile.json').write_text(json.dumps(dict(profile=profile,engine=definition['engine'],
        binary=definition['binary'],model_files=[dict(name=f['name'],filename=f['filename'],sha256=f.get('sha256')) for f in definition['files']],
        cpu_compatibility='build-host native; development profile, not a portable release' if profile=='whisper-small' else 'existing release build policy',
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()),indent=2)+'\n')

def finalize(prefix):
    path=prefix/'share/geist-diktat/package-profile.json';metadata=json.loads(path.read_text())
    binary=prefix/'bin'/PROFILES[validate(metadata['profile'])]['binary']
    metadata['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
    path.write_text(json.dumps(metadata,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prefix',type=Path);p.add_argument('--profile',choices=list(PROFILES),default='geist');p.add_argument('--finalize',action='store_true');a=p.parse_args()
    if a.finalize:finalize(a.prefix)
    else:stage(a.prefix,a.profile)
