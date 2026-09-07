"""Pinned model profiles shared by setup, launch, doctor and packaging."""
import json
import os
from pathlib import Path
import tempfile

PROFILES={
 'geist':dict(label='Geist / Gemma 4',binary='diktat',engine='geist',threads=4,files=[
  dict(name='model',filename='gemma4-e2b-Q4_K_M.gguf',env='GEIST_DIKTAT_MODEL',sha256='740185b21d22ceb83a11c3aa62ad5842ef32c70f6096d756bbee85a1e4ec34b8',url='https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-Q4_K_M.gguf'),
  dict(name='tower',filename='audio_tower.safetensors',env='GEIST_AUDIO_MODEL_PATH',sha256='d6c45a6c276212dc3a793e66dfc588d89c12d1ac92c0e4b85494390ca848cd77',fetcher='fetch_audio_tower.py'),
  dict(name='mel',filename='mel_constants.bin',env='GEIST_MEL_CONSTANTS_PATH',bundled=True)]),
 'whisper-small':dict(label='Whisper small Q5_1 · Beam 5',binary='diktat-whisper',engine='whisper-resident',threads=4,beam_size=5,files=[
  dict(name='model',filename='ggml-small-q5_1.bin',env='GEIST_DIKTAT_MODEL',sha256='ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb',url='https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small-q5_1.bin')])}

def config_path():return Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'geist-diktat/profile.json'
def data_path():return Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'geist-diktat'
def validate(name):
    if not isinstance(name,str) or name not in PROFILES:raise ValueError('unknown profile: '+str(name))
    return name

def selected(prefix,explicit=None):
    if explicit is not None:return validate(explicit),'command'
    if 'GEIST_DIKTAT_PROFILE' in os.environ:return validate(os.environ['GEIST_DIKTAT_PROFILE']),'environment'
    config=config_path()
    if config.exists():
        value=json.loads(config.read_text())
        if not isinstance(value,dict) or type(value.get('version')) is not int or value['version']!=1:raise ValueError('invalid profile configuration: '+str(config))
        return validate(value.get('profile')),'user'
    default=prefix/'share/geist-diktat/default-profile'
    return (validate(default.read_text().strip()),'package') if default.exists() else ('geist','legacy default')

def resolve(prefix,explicit=None):
    name,source=selected(prefix,explicit);p=PROFILES[name]
    core=Path(os.environ.get('GEIST_DIKTAT_CORE',str(prefix/'bin'/p['binary'])))
    files=[]
    for definition in p['files']:
        root=prefix/'share/geist-diktat' if definition.get('bundled') else data_path()
        files.append(dict(definition,path=Path(os.environ.get(definition['env'],str(root/definition['filename'])))))
    def integer(key,default,maximum):
        raw=os.environ.get(key,str(default))
        if not raw.isascii() or not raw.isdecimal() or not 1<=int(raw)<=maximum:raise ValueError('invalid '+key)
        return int(raw)
    parameters=dict(threads=integer('OMP_NUM_THREADS',p['threads'],256))
    if 'beam_size' in p:parameters['beam_size']=integer('GEIST_WHISPER_BEAM_SIZE',p['beam_size'],8)
    return dict(name=name,source=source,label=p['label'],engine=p['engine'],core=core,files=files,parameters=parameters)

def save(prefix,name):
    name=validate(name);core=prefix/'bin'/PROFILES[name]['binary']
    if not core.is_file() or not os.access(core,os.X_OK):raise ValueError('profile decoder is not installed: '+str(core))
    dest=config_path();dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=dest.parent,prefix='.profile-',delete=False) as f:
        temp=Path(f.name)
        try:
            json.dump(dict(version=1,profile=name),f);f.write('\n');f.flush();os.fsync(f.fileno());f.close();os.replace(temp,dest)
        finally:temp.unlink(missing_ok=True)
    return dest
