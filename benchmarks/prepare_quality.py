#!/usr/bin/env python3
"""Prepare locally cached public research fixtures. Never upload the corpus.

FLEURS: CC-BY-4.0. SwissDial: public recorded research samples (not TTS demos).
OOCC: CC-BY-NC-ND-4.0, noncommercial research only; explicit --oocc opt-in.
Requires ffmpeg. All derived WAVs/references remain under ignored build/.
"""
import argparse
import csv
import hashlib
import html
import io
import json
import math
from pathlib import Path
import random
import re
import struct
import subprocess
import tarfile
import urllib.request
import wave
import zipfile

REV='70bb2e84b976b7e960aa89f1c648e09c59f894dd'
HF='https://huggingface.co/datasets/google/fleurs/resolve/'+REV+'/data/de_de/'
SWISS='https://gitlab.inf.ethz.ch/ou-mtc-public/swiss-dial-samples'
OOCC='https://zenodo.org/records/21446419/files/'

def fetch(url,path):
    if not path.exists():
        with urllib.request.urlopen(url,timeout=90) as src, path.with_suffix(path.suffix+'.part').open('wb') as dst:
            while data:=src.read(1024*1024):dst.write(data)
        path.with_suffix(path.suffix+'.part').replace(path)
    return path.read_bytes()

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def convert(source,target):
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-vn','-ar','16000','-ac','1','-c:a','pcm_s16le',str(target)],check=True)

def convert_fleurs(source,target):
    # The pinned FLEURS archive is already 16 kHz mono float32 WAV. Decode
    # exactly this documented format, so CI needs no host-level ffmpeg install.
    data=source.read_bytes(); chunks={};offset=12
    if data[:4]!=b'RIFF' or data[8:12]!=b'WAVE':raise ValueError('not RIFF WAV')
    while offset+8<=len(data):
        name=data[offset:offset+4];size=struct.unpack_from('<I',data,offset+4)[0]
        if offset+8+size>len(data):raise ValueError('truncated WAV chunk')
        chunks[name]=data[offset+8:offset+8+size];offset+=8+size+(size%2)
    fmt=struct.unpack_from('<HHIIHH',chunks[b'fmt '])
    if (fmt[0],fmt[1],fmt[2],fmt[5])!=(3,1,16000,32):raise ValueError('unexpected FLEURS WAV format')
    samples=[max(-32768,min(32767,math.floor(x[0]*32768+0.5))) for x in struct.iter_unpack('<f',chunks[b'data'])]
    save_wav(target,samples)

def save_wav(path,samples):
    with wave.open(str(path),'wb') as w:
        w.setparams((1,2,16000,0,'NONE','not compressed'))
        w.writeframes(struct.pack('<'+'h'*len(samples),*samples))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path('build/speech-corpus'))
    ap.add_argument('--cache',type=Path,default=Path('build/speech-research'))
    ap.add_argument('--oocc',action='store_true',help='include OOCC for noncommercial local research under its terms')
    ap.add_argument('--fleurs-only',action='store_true',help='prepare only FLEURS and noise; no ffmpeg dependency')
    a=ap.parse_args();p=a.root;r=a.cache;p.mkdir(parents=True,exist_ok=True);r.mkdir(parents=True,exist_ok=True)
    rows=list(csv.reader(io.StringIO(fetch(HF+'test.tsv',r/'fleurs_tsv').decode()),delimiter='\t'))
    refs={row[1]:row for row in rows}; manifest=[]
    if len(list(p.glob('source-*.wav')))<12:
        with urllib.request.urlopen(HF+'audio/test.tar.gz',timeout=90) as stream,tarfile.open(fileobj=stream,mode='r|gz') as archive:
            count=0
            for m in archive:
                name=Path(m.name).name
                if m.isfile() and name in refs:
                    (p/('source-'+name)).write_bytes(archive.extractfile(m).read());count+=1
                    if count==12:break
    for raw in sorted(p.glob('source-*.wav'))[:12]:
        name=raw.name.removeprefix('source-');dst=p/('fleurs-'+name);convert_fleurs(raw,dst)
        manifest.append(dict(id=dst.stem,wav=dst.name,reference=refs[name][2],group='de-read-clean',source=HF+'audio/test.tar.gz',source_file=name,revision=REV,license='CC-BY-4.0',source_sha256=sha(raw)))
    page=fetch(SWISS,r/'swiss_page').decode() if not a.fleurs_only else ''
    for sample in (() if a.fleurs_only else (1,2)):
        block=page.split('id="user-content-sample-'+str(sample)+'"')[1].split('<h3')[0]
        plain=html.unescape(re.sub('<[^>]+>',' ',block))
        standard=re.search(r'High German Sentence:\s*(.*?)\s*Thema:',plain,re.S).group(1).strip()
        for dialect,ref,url in re.findall(r'(AG|BE|BS|GR|LU|SG|VS|ZH):</strong>\s*<em[^>]*>(.*?)</em>.*?<audio src="([^"]+)"',block,re.S):
            url='https://gitlab.inf.ethz.ch'+url;raw=r/Path(url).name;fetch(url,raw)
            dst=p/('swiss-'+raw.name);convert(raw,dst)
            manifest.append(dict(id=dst.stem,wav=dst.name,reference=standard,dialect_reference=html.unescape(ref),dialect=dialect,group='ch-dialect',source=url,license='SwissDial public research samples; no corpus redistribution',source_sha256=sha(raw)))
    # Deterministic noise mixture: microphone self-noise proxy, NOT recorded mic
    # noise. Scale to active-speech RMS (20 ms frames over amplitude 300).
    for original in list(manifest[:6]):
        with wave.open(str(p/original['wav'])) as w:raw=w.readframes(w.getnframes())
        samples=struct.unpack('<'+'h'*(len(raw)//2),raw)
        active=[]
        for i in range(0,len(samples),320):
            f=samples[i:i+320]
            if math.sqrt(sum(x*x for x in f)/len(f))>300:active.extend(f)
        signal_rms=math.sqrt(sum(x*x for x in active)/len(active))
        for snr in (20,10,5):
            rng=random.Random(20260905);noise=[rng.gauss(0,1)+0.2*math.sin(2*math.pi*50*i/16000) for i in range(len(samples))]
            scale=signal_rms/(10**(snr/20)*math.sqrt(sum(x*x for x in noise)/len(noise)))
            values=[round(s+scale*n) for s,n in zip(samples,noise)]
            clipping=sum(abs(x)>32767 for x in values)
            dst=p/(original['id']+'-snr'+str(snr)+'.wav');save_wav(dst,[max(-32768,min(32767,x)) for x in values])
            manifest.append(dict(original,id=dst.stem,wav=dst.name,group='de-noise-'+str(snr)+'db',noise=dict(kind='simulated white self-noise plus 50 Hz hum',snr_db=snr,seed=20260905,clipped_samples=clipping)))
    if a.oocc:
        fetch(OOCC+'README.md?download=1',r/'oocc_readme')
        fetch(OOCC+'documentation.zip?download=1',r/'oocc-documentation.zip')
        fetch(OOCC+'10_minute_recordings_transcripts.zip?download=1',r/'oocc_transcripts')
        fetch(OOCC+'10_minute_recordings_audio_video_task1.zip?download=1',r/'oocc-audio.zip')
        with zipfile.ZipFile(r/'oocc-audio.zip') as z:
            name=next(n for n in z.namelist() if Path(n).name=='1_free_conversation.mov')
            raw=r/'oocc-1.mov'
            if not raw.exists():
                with z.open(name) as src,raw.open('wb') as dst:
                    while b:=src.read(1024*1024):dst.write(b)
        with zipfile.ZipFile(r/'oocc_transcripts') as z:
            text=z.read('10_minute_recordings_transcripts/1_free_conversation.csv').decode('utf-8-sig')
        rows=list(csv.DictReader(io.StringIO(text)))
        rows.sort(key=lambda row:sum(float(row[k] or 0)*m for k,m in [('start_minute',60),('start_second',1),('start_ms',.001)]))
        ref=' '.join(row['utterance'].strip() for row in rows if row['utterance'].strip().lower()!='redacted')
        dst=p/'oocc-1-free-conversation.wav';convert(raw,dst)
        manifest.append(dict(id=dst.stem,wav=dst.name,reference=ref,group='de-conversation-long',source='https://doi.org/10.5281/zenodo.21446419',source_file=name,source_sha256=sha(raw),license='CC-BY-NC-ND-4.0; local noncommercial research; do not redistribute',reference_policy='manually corrected official transcript; redacted annotations removed; order by start; overlapping speakers may inflate ordinary WER'))
    for entry in manifest:
        entry['sha256']=sha(p/entry['wav'])
        with wave.open(str(p/entry['wav'])) as w:entry['audio_s']=w.getnframes()/w.getframerate()
    (p/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(fixtures=len(manifest),audio_s=sum(f['audio_s'] for f in manifest),groups=sorted(set(f['group'] for f in manifest)))))

if __name__=='__main__':main()
