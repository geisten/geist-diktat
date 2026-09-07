"""Model selection and verified setup: no external downloads or microphone."""
import copy
import fcntl
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
import model_profiles as profiles
import launcher

class ProfileSetup(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="profile space ' ");self.root=Path(self.temp.name)
        self.env=patch.dict(os.environ,dict(HOME=str(self.root),XDG_CONFIG_HOME=str(self.root/'config'),XDG_DATA_HOME=str(self.root/'data')),clear=True);self.env.start()
        self.prefix=self.root/'prefix';(self.prefix/'bin').mkdir(parents=True)
        for binary in ('diktat','diktat-whisper'):
            p=self.prefix/'bin'/binary;p.write_text('#!/bin/sh\nexit 0\n');p.chmod(0o755)
        self.content=b'verified model bytes';self.sha=hashlib.sha256(self.content).hexdigest()
        definition=copy.deepcopy(profiles.PROFILES['whisper-small']);definition['files'][0]['sha256']=self.sha
        self.definition=patch.dict(profiles.PROFILES,{'whisper-small':definition});self.definition.start()
        self.config=profiles.resolve(self.prefix,'whisper-small');self.file=self.config['files'][0];self.path=self.file['path']
    def tearDown(self):self.definition.stop();self.env.stop();self.temp.cleanup()
    def writer(self,command,**kw):
        Path(command[command.index('-o')+1]).write_bytes(self.content)
    def test_setup_only_downloads_the_selected_model(self):
        with patch.object(launcher.subprocess,'run',side_effect=self.writer) as run:launcher.setup(self.prefix,self.config)
        self.assertEqual(run.call_count,1);self.assertEqual(self.path.read_bytes(),self.content)
        self.assertFalse((self.path.parent/'audio_tower.safetensors').exists())
    def test_valid_cache_works_without_curl(self):
        self.path.parent.mkdir(parents=True);self.path.write_bytes(self.content)
        with patch.object(launcher.subprocess,'run') as run:launcher.setup(self.prefix,self.config)
        run.assert_not_called()
    def test_failed_checksum_preserves_previous_model(self):
        self.path.parent.mkdir(parents=True);self.path.write_bytes(b'previous')
        def bad(cmd,**kw):Path(cmd[cmd.index('-o')+1]).write_bytes(b'wrong')
        with patch.object(launcher.subprocess,'run',side_effect=bad),self.assertRaisesRegex(ValueError,'SHA mismatch'):launcher.setup(self.prefix,self.config)
        self.assertEqual(self.path.read_bytes(),b'previous');self.assertEqual(list(self.path.parent.glob('*.part')),[])
    def test_interruption_retains_resumable_part_and_old_model(self):
        self.path.parent.mkdir(parents=True);self.path.write_bytes(b'old')
        def interrupted(cmd,**kw):
            Path(cmd[cmd.index('-o')+1]).write_bytes(b'partial');raise subprocess.CalledProcessError(18,cmd)
        with patch.object(launcher.subprocess,'run',side_effect=interrupted),self.assertRaises(subprocess.CalledProcessError):launcher.setup(self.prefix,self.config)
        self.assertEqual(self.path.read_bytes(),b'old');self.assertEqual(len(list(self.path.parent.glob('*.part'))),1)
        with patch.object(launcher.subprocess,'run',side_effect=self.writer) as run:launcher.setup(self.prefix,self.config)
        self.assertIn('-C',run.call_args.args[0]);self.assertEqual(self.path.read_bytes(),self.content)
    def test_concurrent_setup_is_rejected_without_downloading(self):
        profiles.data_path().mkdir(parents=True)
        with (profiles.data_path()/'.setup.lock').open('w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with patch.object(launcher.subprocess,'run') as run,self.assertRaisesRegex(ValueError,'another model setup'):launcher.setup(self.prefix,self.config)
        run.assert_not_called()
    def test_symlink_partial_file_does_not_overwrite_target(self):
        self.path.parent.mkdir(parents=True);target=self.root/'private';target.write_bytes(b'keep')
        part=self.path.with_name('.'+self.path.name+'.'+self.sha[:12]+'.part');part.symlink_to(target)
        with self.assertRaises(OSError):launcher.setup(self.prefix,self.config)
        self.assertEqual(target.read_bytes(),b'keep')
    def test_failed_atomic_selection_keeps_old_profile(self):
        profiles.save(self.prefix,'geist')
        with patch.object(profiles.os,'replace',side_effect=OSError('disk error')),self.assertRaises(OSError):profiles.save(self.prefix,'whisper-small')
        self.assertEqual(profiles.selected(self.prefix)[0],'geist');self.assertEqual(list(profiles.config_path().parent.glob('.profile-*')),[])
    def test_malformed_package_default_is_not_legacy_fallback(self):
        p=self.prefix/'share/geist-diktat';p.mkdir(parents=True);(p/'default-profile').write_text('unknown')
        with self.assertRaises(ValueError):profiles.resolve(self.prefix)
    def test_doctor_detects_changed_packaged_binary(self):
        import json
        import desktop_tools
        self.path.parent.mkdir(parents=True);self.path.write_bytes(self.content)
        share=self.prefix/'share/geist-diktat';share.mkdir(parents=True)
        core=self.prefix/'bin/diktat-whisper'
        (share/'package-profile.json').write_text(json.dumps(dict(profile='whisper-small',binary_sha256=hashlib.sha256(core.read_bytes()).hexdigest())))
        os.environ['GEIST_DIKTAT_CAPTURE']='true'
        before=desktop_tools.doctor(self.prefix,True,'whisper-small');self.assertTrue(before['ready'],before)
        core.write_text('#!/bin/sh\nexit 99\n')
        after=desktop_tools.doctor(self.prefix,True,'whisper-small')
        self.assertFalse(after['ready']);self.assertEqual([c['name'] for c in after['checks'] if not c['ok']],['recognizer-sha256'])
