"""Launcher integration with isolated prefix/HOME and fake capture/binary."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class Launcher(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="diktat quote ' ")
        self.root=Path(self.tmp.name)
        self.bin=self.root/'prefix/bin'; self.bin.mkdir(parents=True)
        self.data=self.root/'data/geist-diktat'; self.data.mkdir(parents=True)
        self.wrapper=self.bin/'geist-diktat'; shutil.copy(ROOT/'packaging/geist-diktat',self.wrapper)
        self.wrapper.chmod(0o755)
        share=self.root/'prefix/share/geist-diktat'; share.mkdir(parents=True)
        for helper in (ROOT/'runtime').glob('*.py'):
            shutil.copy(helper,share/helper.name)
        self.stub=self.bin/'diktat'
        self.stub.write_text('#!/bin/sh\ncat\nprintf "MODEL=%s\\nTOWER=%s\\nMEL=%s\\nRMS=%s\\n" "$1" "$GEIST_AUDIO_MODEL_PATH" "$GEIST_MEL_CONSTANTS_PATH" "$2" >&2\n')
        self.stub.chmod(0o755)
        self.env=dict(os.environ,HOME=str(self.root/'home'),XDG_DATA_HOME=str(self.root/'data'),
            GEIST_DIKTAT_CAPTURE="printf 'Hallo Welt\\n'")
        self.env.pop('GEIST_AUDIO_MODEL_PATH',None)
        self.env.pop('GEIST_MEL_CONSTANTS_PATH',None)
        (self.data/'gemma4-e2b-Q4_K_M.gguf').touch()

    def tearDown(self): self.tmp.cleanup()
    def call(self,*args):
        return subprocess.run([str(self.wrapper),*args],env=self.env,capture_output=True,text=True,timeout=10)

    def test_usage(self):
        for args in [(),('wrong',)]:
            p=self.call(*args); self.assertEqual(p.returncode,2); self.assertIn('usage:',p.stderr)

    def test_missing_model(self):
        (self.data/'gemma4-e2b-Q4_K_M.gguf').unlink()
        p=self.call('run'); self.assertEqual(p.returncode,1); self.assertIn('model missing',p.stderr)

    def test_prefix_data_quoting_and_capture(self):
        p=self.call('run','420')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout,'Hallo Welt\n')
        self.assertIn('MODEL='+str(self.data/'gemma4-e2b-Q4_K_M.gguf'),p.stderr)
        self.assertIn('TOWER='+str(self.data/'audio_tower.safetensors'),p.stderr)
        self.assertIn('MEL='+str(self.root/'prefix/share/geist-diktat/mel_constants.bin'),p.stderr)
        self.assertIn('RMS=420',p.stderr)

    def test_environment_overrides(self):
        self.env.update(GEIST_AUDIO_MODEL_PATH='/custom/tower',GEIST_MEL_CONSTANTS_PATH='/custom/mel')
        p=self.call('run'); self.assertIn('TOWER=/custom/tower',p.stderr); self.assertIn('MEL=/custom/mel',p.stderr)

    def test_capture_error_is_not_success(self):
        self.env['GEIST_DIKTAT_CAPTURE']='exit 17'
        p=self.call('run'); self.assertNotEqual(p.returncode,0,'capture failure hidden by pipeline exit status')

    def test_decoder_failure_propagates(self):
        self.stub.write_text('#!/bin/sh\ncat >/dev/null\nexit 19\n')
        self.assertEqual(self.call('run').returncode,19)

if __name__=='__main__': unittest.main(verbosity=2)
