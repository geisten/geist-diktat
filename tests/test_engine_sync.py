"""Regression coverage for the engine sync migration added during the audit."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless((ROOT/'scripts/sync-engine.sh').exists(),'sync script absent in pre-migration snapshot')
class EngineSync(unittest.TestCase):
    def test_existing_git_directory_needs_no_clone(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); engine=root/'engine'; (engine/'.git').mkdir(parents=True)
            binary=root/'bin'; binary.mkdir()
            git=binary/'git'
            git.write_text('#!/bin/sh\ncase "$*" in *rev-parse*) echo pinned;; *) exit 99;; esac\n')
            git.chmod(0o755)
            p=subprocess.run(['sh',str(ROOT/'scripts/sync-engine.sh')],env=dict(os.environ,
                PATH=str(binary)+os.pathsep+os.environ['PATH'],GEIST_REPO='unused',GEIST_REF='pinned',
                GEISTLIB=str(engine)),capture_output=True,timeout=5)
            self.assertEqual(p.returncode,0,p.stderr.decode())

    def test_gitfile_checkout_survives_failed_clone(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); engine=root/'engine'; engine.mkdir()
            (engine/'.git').write_text('gitdir: /old/submodule/metadata\n')
            sentinel=engine/'local-model.gguf'; sentinel.write_bytes(b'local data must survive')
            binary=root/'bin'; binary.mkdir()
            git=binary/'git'; git.write_text('#!/bin/sh\nexit 128\n'); git.chmod(0o755)
            p=subprocess.run(['sh',str(ROOT/'scripts/sync-engine.sh')],env=dict(os.environ,
                PATH=str(binary)+os.pathsep+os.environ['PATH'],GEIST_REPO='offline',GEIST_REF='pinned',
                GEISTLIB=str(engine)),capture_output=True,timeout=5)
            self.assertNotEqual(p.returncode,0)
            self.assertTrue(sentinel.exists(),'migration deletes local models before clone succeeds')

if __name__=='__main__': unittest.main(verbosity=2)
