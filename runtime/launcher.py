#!/usr/bin/env python3
"""Installed profile-aware launcher. Selection persists without changing editors."""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from model_profiles import PROFILES,resolve,save,data_path

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while data:=f.read(1024*1024):h.update(data)
    return h.hexdigest()

def fetch_file(prefix,file):
    path=file['path'];sha=file.get('sha256')
    if file.get('bundled'):
        if not path.is_file() or not path.stat().st_size:raise ValueError('bundled data missing; reinstall package: '+str(path))
        return
    if path.is_file() and digest(path)==sha:
        print('verified: '+str(path));return
    path.parent.mkdir(parents=True,exist_ok=True)
    part=path.with_name('.'+path.name+'.'+sha[:12]+'.part')
    fd=os.open(part,os.O_CREAT|os.O_WRONLY|os.O_NOFOLLOW,0o600);os.close(fd)
    print('downloading '+file['name']+' for selected profile ...',flush=True)
    if file.get('fetcher'):
        command=[sys.executable,str(prefix/'share/geist-diktat'/file['fetcher']),'-o',str(part),'--sha256',sha]
    else:
        command=['curl','-fL','--retry','3','--retry-delay','2','-C','-','-o',str(part),file['url']]
    subprocess.run(command,check=True)
    if digest(part)!=sha:
        part.unlink();raise ValueError('SHA mismatch; existing model preserved: '+str(path))
    os.replace(part,path)

def setup(prefix,profile):
    if not profile['core'].is_file() or not os.access(profile['core'],os.X_OK):raise ValueError('selected profile decoder missing; install its package first')
    data_path().mkdir(parents=True,exist_ok=True)
    fd=os.open(data_path()/'.setup.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('another model setup is running; retry after it completes')
        for file in profile['files']:fetch_file(prefix,file)
    print('setup complete: '+profile['name']+'; geist-diktat doctor --verify checks files.')
    print('Microphone access and text insertion still need a test dictation.')

def capture_command():
    if os.environ.get('GEIST_DIKTAT_CAPTURE'):return os.environ['GEIST_DIKTAT_CAPTURE']
    if platform.system()=='Darwin':
        if shutil.which('sox'):return 'exec sox -q -d -t raw -r 16000 -e signed -b 16 -c 1 -'
        if shutil.which('ffmpeg'):return 'exec ffmpeg -loglevel error -f avfoundation -i :default -ar 16000 -ac 1 -f s16le -'
        raise ValueError('no capture tool — brew install sox')
    if not shutil.which('arecord'):raise ValueError('arecord missing — install alsa-utils')
    return 'exec arecord -q -f S16_LE -r 16000 -c 1 -t raw'

def main():
    p=argparse.ArgumentParser(prog='geist-diktat')
    p.add_argument('--prefix',type=Path,required=True);p.add_argument('--profile',choices=list(PROFILES))
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('setup')
    run=sub.add_parser('run');run.add_argument('rms',nargs='?')
    doctor=sub.add_parser('doctor');doctor.add_argument('--json',action='store_true');doctor.add_argument('--verify',action='store_true')
    editor=sub.add_parser('editor-install');editor.add_argument('editor',choices=['vim','nvim','all'])
    sink=sub.add_parser('type');sink.add_argument('sink',nargs=argparse.REMAINDER)
    profile=sub.add_parser('profile');profile.add_argument('action',choices=['list','show','use'],nargs='?',default='show');profile.add_argument('name',nargs='?')
    a=p.parse_args();share=a.prefix/'share/geist-diktat'
    try:
        if a.command=='profile' and a.action=='use':
            if not a.name:p.error('profile use requires a profile name')
            dest=save(a.prefix,a.name);print('saved '+a.name+': '+str(dest));return 0
        if a.command=='profile' and a.action=='list':
            for name,profile in PROFILES.items():
                core=a.prefix/'bin'/profile['binary'];print(name+'\t'+profile['label']+'\t'+('installed' if core.is_file() and os.access(core,os.X_OK) else 'decoder not installed'))
            return 0
        if a.command in ('editor-install','type'):
            script='desktop_tools.py' if a.command=='editor-install' else 'line_sink.py'
            args=['--prefix',str(a.prefix),'editor-install',a.editor] if a.command=='editor-install' else ['--',*a.sink]
            os.execv(sys.executable,[sys.executable,str(share/script),*args])
        config=resolve(a.prefix,a.profile)
        if a.command=='profile':
            print(json.dumps(config,default=str,ensure_ascii=False,indent=2));return 0
        if a.command=='setup':setup(a.prefix,config);return 0
        if a.command=='doctor':
            from desktop_tools import doctor
            report=doctor(a.prefix,a.verify,a.profile)
            if a.json:print(json.dumps(report,ensure_ascii=False))
            else:
                print('Profile: '+report['profile']['name'])
                for check in report['checks']:print(('OK   ' if check['ok'] else 'FAIL ')+check['name']+(': '+check['help'] if check['help'] else ''))
                print('Device permissions and app insertion: interactive test required.')
            return 0 if report['ready'] else 1
        core=config['core'];model=next(f['path'] for f in config['files'] if f['name']=='model')
        if not core.is_file() or not os.access(core,os.X_OK):raise ValueError('recognizer missing for '+config['name']+'; install its package')
        if not model.is_file():raise ValueError('model missing — run: geist-diktat setup')
        if a.rms is not None and (not math.isfinite(float(a.rms)) or not 0<float(a.rms)<=32768):raise ValueError('invalid RMS')
        capture=capture_command()
        os.environ['OMP_NUM_THREADS']=str(config['parameters']['threads'])
        if 'beam_size' in config['parameters']:os.environ['GEIST_WHISPER_BEAM_SIZE']=str(config['parameters']['beam_size'])
        for file in config['files']:
            if file['name']!='model':os.environ[file['env']]=str(file['path'])
        args=[sys.executable,str(share/'diktat_runtime.py'),'--capture',capture,'--buffer-seconds',os.environ.get('GEIST_DIKTAT_BUFFER_SECONDS','6'),'--',str(core),str(model)]
        if a.rms is not None:args.append(a.rms)
        os.execv(sys.executable,args)
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        print('geist-diktat: '+str(error),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
