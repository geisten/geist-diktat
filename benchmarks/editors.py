#!/usr/bin/env python3
"""Fresh editor process + fake transcript insertion, NOT ASR latency."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output',type=Path,required=True)
ap.add_argument('--repeats',type=int,default=10)
args=ap.parse_args()
if args.repeats<1: ap.error('repeats must be positive')
results={'platform':platform.platform(),'scope':'fresh editor process and stub transcript insertion; no ASR, microphone, or GUI','editors':{}}
with tempfile.TemporaryDirectory() as d:
    tmp=Path(d)
    sample=tmp/'transcript.txt'; sample.write_text('Grüße Welt\n')
    for name in ('vim','nvim'):
        binary=shutil.which(os.getenv('VIM_BINARY','vim') if name=='vim' else name)
        if not binary:
            results['editors'][name]={'skip':'not installed'}; continue
        version=subprocess.check_output([binary,'--version'],text=True).splitlines()[0]
        if name=='vim' and not version.startswith('VIM -'):
            results['editors'][name]={'skip':'vim resolves to another editor','version':version}; continue
        if name=='nvim':
            script=tmp/'bench.lua'
            script.write_text("""
vim.cmd('enew!')
vim.notify=function() end
local m=require('geist-diktat')
m.setup({cmd='cat '..vim.fn.shellescape(%s)})
m.start()
local ok=vim.wait(3000,function()
  return table.concat(vim.api.nvim_buf_get_lines(0,0,-1,false),'')=='Grüße Welt '
end)
m.stop()
vim.cmd(ok and 'qa!' or 'cquit')
""" % json.dumps(str(sample)))
            cmd=[binary,'--headless','-u','NONE','--cmd','set rtp+='+str(ROOT),'-c','lua dofile('+json.dumps(str(script))+')']
        else:
            script=tmp/'bench.vim'
            script.write_text("set encoding=utf-8\nread !cat "+str(sample)+"\nif getline('$') !=# 'Grüße Welt'\ncquit\nendif\nqa!\n")
            cmd=[binary,'-Nu','NONE','-n','-es','-S',str(script)]
        rows=[]
        for _ in range(args.repeats):
            start=time.monotonic()
            p=subprocess.run(cmd,capture_output=True,timeout=10)
            rows.append({'wall_ms':1000*(time.monotonic()-start),'exit_code':p.returncode,
                         'stderr':p.stderr.decode(errors='replace') if p.returncode else ''})
        results['editors'][name]={'version':version,'runs':rows,
            'median_ms':statistics.median(r['wall_ms'] for r in rows),
            'min_ms':min(r['wall_ms'] for r in rows),'max_ms':max(r['wall_ms'] for r in rows)}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(results,ensure_ascii=False))
raise SystemExit(int(any(r['exit_code'] for e in results['editors'].values() for r in e.get('runs',[]))))
