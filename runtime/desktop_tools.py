#!/usr/bin/env python3
"""Read-only diagnostics and explicit editor installation; never edit vimrc."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import time
from model_profiles import resolve


def doctor(prefix, verify=False, profile=None):
    data=Path(os.getenv('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'geist-diktat'
    checks=[]
    def check(name, ok, hint):checks.append(dict(name=name,ok=bool(ok),help='' if ok else hint))
    check('python3',shutil.which('python3'),'Install Python 3')
    config=resolve(prefix,profile)
    core=config['core']
    check('recognizer',core.is_file() and os.access(core,os.X_OK),'Install the selected profile package; decoder missing: '+str(core))
    for file in config['files']:
        name,path,sha=file['name'],file['path'],file.get('sha256')
        ok=path.is_file() and path.stat().st_size>0
        if ok and verify and sha:
            h=hashlib.sha256()
            with path.open('rb') as f:
                for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
            ok=h.hexdigest()==sha
        check(name,ok,'Run geist-diktat setup; missing, empty or invalid file: '+str(path))
    metadata_path=prefix/'share/geist-diktat/package-profile.json'
    metadata=json.loads(metadata_path.read_text()) if metadata_path.exists() else None
    if metadata is not None:
        valid=isinstance(metadata,dict) and metadata.get('profile')==config['name']
        check('package-profile',valid,'Selected profile differs from the installed package; install the matching profile package')
        if valid and verify:
            h=hashlib.sha256()
            if core.is_file():
                with core.open('rb') as f:
                    for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
            check('recognizer-sha256',core.is_file() and h.hexdigest()==metadata.get('binary_sha256'),'Reinstall package; recognizer differs from the packaged binary')
    capture=bool(os.getenv('GEIST_DIKTAT_CAPTURE')) or any(shutil.which(c) for c in (('sox','ffmpeg') if platform.system()=='Darwin' else ('arecord',)))
    check('capture-command',capture,'macOS: brew install sox; Ubuntu: sudo apt install alsa-utils')
    return dict(package_profile=metadata,profile=dict(name=config['name'],source=config['source'],engine=config['engine'],core=str(core),parameters=config['parameters']),platform=platform.platform(),ready=all(c['ok'] for c in checks),checks=checks,
                verification='sha256' if verify else 'file presence only',
                limitations=['Device access, microphone permission and focused-app insertion require an interactive test.'],
                editors={c:shutil.which(c) for c in ('vim','nvim')})


def install_editor(prefix, editor):
    base=(Path.home()/'.vim' if editor=='vim' else Path(os.getenv('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'nvim/site')
    parent=base/'pack/geist/start';parent.mkdir(parents=True,exist_ok=True)
    dest=parent/'geist-diktat'
    source=prefix/'share/geist-diktat/editor'
    if not all((source/n).is_dir() for n in ('lua','plugin','autoload')):raise ValueError('incomplete editor package; reinstall geist-diktat')
    stage=Path(tempfile.mkdtemp(prefix='.geist-stage-',dir=parent));backup=None
    try:
        for name in ('lua','plugin','autoload'):shutil.copytree(source/name,stage/name)
        if dest.exists() or dest.is_symlink():
            backup_root=parent.parent/'backups';backup_root.mkdir(exist_ok=True)
            backup=backup_root/('geist-diktat.previous-'+str(time.time_ns()));dest.rename(backup)
        try:stage.rename(dest)
        except OSError:
            if backup is not None:backup.rename(dest)
            raise
    finally:
        if stage.exists():shutil.rmtree(stage)
    return dict(installed=str(dest),backup=str(backup) if backup else None,usage='Restart editor; :DiktatToggle starts/stops. Map <Plug>(DiktatToggle) to your preferred key.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prefix',type=Path,required=True)
    sub=p.add_subparsers(dest='command',required=True)
    d=sub.add_parser('doctor');d.add_argument('--json',action='store_true');d.add_argument('--verify',action='store_true')
    i=sub.add_parser('editor-install');i.add_argument('editor',choices=['vim','nvim','all'])
    a=p.parse_args()
    try:
        if a.command=='doctor':
            report=doctor(a.prefix,a.verify)
            if a.json:print(json.dumps(report,ensure_ascii=False))
            else:
                for c in report['checks']:print(('OK   ' if c['ok'] else 'FAIL ')+c['name']+(': '+c['help'] if c['help'] else ''))
                print('Device permissions and app insertion: interactive test required.')
            return 0 if report['ready'] else 1
        for editor in (['vim','nvim'] if a.editor=='all' else [a.editor]):print(json.dumps(install_editor(a.prefix,editor),ensure_ascii=False))
        return 0
    except (OSError,ValueError) as e:print('geist-diktat: '+str(e),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
