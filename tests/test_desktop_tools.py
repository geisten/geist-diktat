import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('desktop',ROOT/'runtime/desktop_tools.py')
desktop=importlib.util.module_from_spec(spec);spec.loader.exec_module(desktop)
class DesktopTools(unittest.TestCase):
    def test_doctor_missing_files_and_no_microphone_claim(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'HOME':d,'XDG_DATA_HOME':d},clear=True):
            r=desktop.doctor(Path(d));self.assertFalse(r['ready']);self.assertTrue(r['limitations'])
    def test_install_editors_empty_home_and_preserve_update(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'HOME':d,'XDG_DATA_HOME':d+'/data'}):
            prefix=Path(d)/'prefix';source=prefix/'share/geist-diktat/editor';source.mkdir(parents=True)
            for n in ('lua','plugin','autoload'):shutil.copytree(ROOT/n,source/n)
            for editor in ('vim','nvim'):
                a=desktop.install_editor(prefix,editor);dest=Path(a['installed']);self.assertTrue((dest/'autoload/geist_diktat.vim').exists())
                (dest/'user-note').write_text('preserve me')
                b=desktop.install_editor(prefix,editor);self.assertEqual((Path(b['backup'])/'user-note').read_text(),'preserve me')
            self.assertFalse((Path(d)/'.vimrc').exists())
    def test_incomplete_package_preserves_existing(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'HOME':d}):
            dest=Path(d)/'.vim/pack/geist/start/geist-diktat';dest.mkdir(parents=True);(dest/'note').write_text('old')
            with self.assertRaises(ValueError):desktop.install_editor(Path(d),'vim')
            self.assertEqual((dest/'note').read_text(),'old')
