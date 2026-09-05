import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class Editors(unittest.TestCase):
    @unittest.skipUnless(shutil.which('nvim'), 'Neovim not installed')
    def test_nvim_callback_contracts(self):
        p=subprocess.run(['nvim','--headless','-u','NONE','--cmd','set rtp+='+str(ROOT),
            '-c',"lua dofile('tests/nvim_contract.lua')"],cwd=ROOT,capture_output=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))

    @unittest.skipUnless(shutil.which('nvim'), 'Neovim not installed')
    def test_nvim_real_fragmented_process(self):
        lua="""
vim.cmd('enew!')
vim.notify=function() end
local m=require('geist-diktat')
m.setup({cmd="printf hel; sleep 0.15; printf 'lo\\n'"})
m.start()
vim.wait(3000,function() return not m.is_active() end)
vim.wait(50,function() return false end)
local text=table.concat(vim.api.nvim_buf_get_lines(0,0,-1,false),'')
if text~='hello ' then print('Actual: '..vim.inspect(text)); vim.cmd('cquit') else vim.cmd('qa!') end
"""
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.lua'; path.write_text(lua)
            p=subprocess.run(['nvim','--headless','-u','NONE','--cmd','set rtp+='+str(ROOT),
                '-c','lua dofile('+json.dumps(str(path))+')'],capture_output=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stdout.decode()+p.stderr.decode())

    @unittest.skipUnless(shutil.which('vim'), 'Vim not installed')
    def test_vim_finite_stdout_import(self):
        binary=os.getenv('VIM_BINARY','vim')
        version=subprocess.check_output([binary,'--version'],text=True)
        if not version.startswith('VIM -'):
            self.skipTest('vim resolves to Neovim; real Vim is absent')
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'check.vim'; out=Path(d)/'result.txt'
            path.write_text("set encoding=utf-8\nread !printf 'Grüße Welt\\n'\ncall writefile(getline(1,'$'), "
                + "'"+str(out).replace("'","''")+"')\nqa!\n")
            p=subprocess.run([binary,'-Nu','NONE','-n','-es','-S',str(path)],capture_output=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr.decode())
            self.assertIn('Grüße Welt',out.read_text())

if __name__=='__main__': unittest.main(verbosity=2)

class VimAsync(unittest.TestCase):
    def test_real_terminal_fragmented_unicode_and_literal_commands(self):
        import pty
        import select
        import time
        binary=os.getenv('VIM_BINARY',shutil.which('vim') or '')
        if not binary or not subprocess.check_output([binary,'--version']).startswith(b'VIM -'):self.skipTest('real Vim unavailable')
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'async.vim';out=Path(d)/'out'
            path.write_text("set encoding=utf-8\nset rtp+="+str(ROOT)+"\nruntime plugin/geist-diktat.vim\n"
                +"let g:geist_diktat_command=['sh','-c',\"printf 'Gr'; sleep 0.1; printf 'üße :q! $(false)\\\\n'\"]\n"
                +"call geist_diktat#start()\nfunction! Finish(timer)\ncall writefile([getline(1)],'"+str(out)+"')\nqa!\nendfunction\ncall timer_start(700,'Finish')\n")
            master,slave=pty.openpty()
            p=subprocess.Popen([binary,'-Nu','NONE','-n','-i','NONE','-S',str(path)],stdin=slave,stdout=slave,stderr=slave,env=dict(os.environ,TERM='xterm'))
            os.close(slave)
            try:
                deadline=time.monotonic()+5
                while p.poll() is None and time.monotonic()<deadline:
                    if select.select([master],[],[],.1)[0]:
                        try:os.read(master,65536)
                        except OSError:break
                self.assertEqual(p.wait(timeout=1),0)
                self.assertEqual(out.read_text(),'Grüße :q! $(false) \n')
            finally:
                if p.poll() is None:p.kill();p.wait()
                os.close(master)
