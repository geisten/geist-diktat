"""Launcher integration with isolated prefix/HOME and fake capture/binary."""
import os
import json
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
        self.env=dict(os.environ,HOME=str(self.root/'home'),XDG_CONFIG_HOME=str(self.root/'config'),XDG_DATA_HOME=str(self.root/'data'),
            GEIST_DIKTAT_CAPTURE="printf 'Hallo Welt\\n'")
        for key in ('GEIST_DIKTAT_PROFILE','GEIST_DIKTAT_CORE','GEIST_DIKTAT_MODEL','OMP_NUM_THREADS','GEIST_WHISPER_BEAM_SIZE'):self.env.pop(key,None)
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

    def whisper(self):
        core=self.bin/'diktat-whisper'
        core.write_text('#!/bin/sh\ncat\nprintf "WHISPER=%s BEAM=%s THREADS=%s\\n" "$1" "$GEIST_WHISPER_BEAM_SIZE" "$OMP_NUM_THREADS" >&2\n')
        core.chmod(0o755);(self.data/'ggml-small-q5_1.bin').write_bytes(b'model')

    def test_profile_persists_for_next_invocation(self):
        self.whisper();self.assertEqual(self.call('profile','use','whisper-small').returncode,0)
        p=self.call('run');self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('WHISPER='+str(self.data/'ggml-small-q5_1.bin'),p.stderr)
        self.assertIn('BEAM=5 THREADS=4',p.stderr)
        self.assertEqual(json.loads(self.call('profile','show').stdout)['source'],'user')

    def test_explicit_profile_overrides_saved_selection(self):
        self.whisper();self.call('profile','use','whisper-small')
        p=self.call('--profile','geist','run');self.assertEqual(p.returncode,0,p.stderr);self.assertNotIn('WHISPER=',p.stderr)
        self.assertIn('MODEL=',p.stderr)

    def test_whisper_doctor_does_not_require_geist_tower_or_mel(self):
        self.whisper();self.call('profile','use','whisper-small')
        p=self.call('doctor','--json');self.assertEqual(p.returncode,0,p.stderr)
        report=json.loads(p.stdout);names=[c['name'] for c in report['checks']]
        self.assertNotIn('tower',names);self.assertNotIn('mel',names);self.assertEqual(report['profile']['parameters']['beam_size'],5)
        self.assertEqual(self.call('doctor','--verify','--json').returncode,1)

    def test_missing_decoder_does_not_replace_profile(self):
        self.call('profile','use','geist')
        p=self.call('profile','use','whisper-small');self.assertEqual(p.returncode,1)
        self.assertEqual(json.loads(self.call('profile','show').stdout)['name'],'geist')

    def test_invalid_saved_configuration_never_falls_back(self):
        self.call('profile','use','geist');path=self.root/'config/geist-diktat/profile.json'
        for value in ['{broken','{"version": 1, "profile":"typo"}','[]']:
            path.write_text(value);p=self.call('run');self.assertEqual(p.returncode,1);self.assertEqual(p.stdout,'')

    def test_package_profile_is_used_without_user_configuration(self):
        self.whisper();(self.root/'prefix/share/geist-diktat/default-profile').write_text('whisper-small\n')
        p=self.call('run');self.assertEqual(p.returncode,0,p.stderr);self.assertIn('WHISPER=',p.stderr)

    def test_environment_selection_and_parameters_are_visible(self):
        self.whisper();self.env.update(GEIST_DIKTAT_PROFILE='whisper-small',GEIST_WHISPER_BEAM_SIZE='1',OMP_NUM_THREADS='2')
        report=json.loads(self.call('doctor','--json').stdout)
        self.assertEqual(report['profile']['source'],'environment');self.assertEqual(report['profile']['parameters'],{'beam_size':1,'threads':2})
        p=self.call('run');self.assertIn('BEAM=1 THREADS=2',p.stderr)

    def test_bad_rms_and_profile_fail_before_capture(self):
        marker=self.root/'captured';self.env['GEIST_DIKTAT_CAPTURE']='touch "'+str(marker)+'"'
        for rms in ['nan','0','-1','32769','x']:
            self.assertNotEqual(self.call('run',rms).returncode,0);self.assertFalse(marker.exists())
        self.env['GEIST_DIKTAT_PROFILE']='unknown';self.assertEqual(self.call('run').returncode,1);self.assertFalse(marker.exists())

if __name__=='__main__': unittest.main(verbosity=2)
