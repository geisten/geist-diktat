#!/usr/bin/env python3
"""Fetch the measured small Q5_1 candidate with fixed content verification."""
import hashlib
import os
from pathlib import Path
import tempfile
import urllib.request
SHA='ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb'
URL='https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small-q5_1.bin'
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while data:=f.read(1024*1024):h.update(data)
    return h.hexdigest()
def main():
    target=Path('build/ggml-small-q5_1.bin');target.parent.mkdir(exist_ok=True)
    if target.exists():
        if digest(target)!=SHA:raise ValueError('existing model hash mismatch; preserved unchanged')
        return
    with tempfile.NamedTemporaryFile(dir=target.parent,prefix='.whisper-model-',delete=False) as f:
        temp=Path(f.name)
        try:
            with urllib.request.urlopen(URL,timeout=90) as src:
                while data:=src.read(1024*1024):f.write(data)
            f.flush();os.fsync(f.fileno());f.close()
            if digest(temp)!=SHA:raise ValueError('downloaded model hash mismatch')
            # Never replace a concurrently created cache file.
            os.link(temp,target)
        finally:temp.unlink(missing_ok=True)
if __name__=='__main__':main()
