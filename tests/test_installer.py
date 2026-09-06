"""Offline installer tests. No real download, apt, sudo or external writes."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class Installer(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name); self.bin=self.root/'bin'; self.bin.mkdir()
        for name in ['mktemp','rm','mkdir','mv','cat','cut','sed','head','sh','sha256sum','shasum']:
            path=shutil.which(name)
            if path: (self.bin/name).symlink_to(path)
        self.env=dict(os.environ,PATH=str(self.bin),HOME=str(self.root/'home'),
            TMPDIR=str(self.root),TEST_OS='Darwin',TEST_ARCH='arm64',TEST_ROOT=str(self.root))
        self.script('uname','case "$1" in -m) echo "$TEST_ARCH";; -s) echo "$TEST_OS";; esac')
        self.script('curl', '''out=''
while [ "$#" -gt 0 ]; do
  if [ "$1" = -o ]; then shift; out=$1; fi
  url=$1; shift
done
case "$url" in
*/SHA256SUMS) cat "$TEST_ROOT/manifest" > "$out";;
*) cat "$TEST_ROOT/asset" > "$out";;
esac''')
        self.script('tar','printf "tar\\n" >> "$TEST_ROOT/actions"')
        self.script('id','echo 0')
        self.asset('geist-diktat_macos-arm64.tar.gz')

    def script(self,name,text):
        p=self.bin/name; p.write_text('#!/bin/sh\n'+text+'\n'); p.chmod(0o755)
    def asset(self,name,wrong=False):
        data=b'test release asset'; (self.root/'asset').write_bytes(data)
        sha='0'*64 if wrong else hashlib.sha256(data).hexdigest()
        (self.root/'manifest').write_text(sha+'  '+name+'\n')
    def tearDown(self): self.tmp.cleanup()
    def run_install(self):
        return subprocess.run(['sh',str(ROOT/'install.sh')],env=self.env,text=True,capture_output=True,timeout=10)
    def actions(self):
        p=self.root/'actions'; return p.read_text() if p.exists() else ''

    def test_macos_tarball_verified(self):
        p=self.run_install(); self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('checksum ok',p.stdout); self.assertEqual(self.actions(),'tar\n')

    def test_checksum_mismatch_blocks_install(self):
        self.asset('geist-diktat_macos-arm64.tar.gz',wrong=True)
        p=self.run_install(); self.assertNotEqual(p.returncode,0)
        self.assertIn('checksum mismatch',p.stderr); self.assertEqual(self.actions(),'')

    def test_unlisted_asset_blocks_install(self):
        self.asset('another-asset')
        p=self.run_install(); self.assertNotEqual(p.returncode,0); self.assertEqual(self.actions(),'')

    def test_unsupported_architecture(self):
        self.env['TEST_ARCH']='riscv64'
        p=self.run_install(); self.assertNotEqual(p.returncode,0); self.assertEqual(self.actions(),'')

    def test_intel_macos_rejected(self):
        self.env['TEST_ARCH']='x86_64'
        p=self.run_install(); self.assertNotEqual(p.returncode,0); self.assertIn('Apple Silicon',p.stderr)

    def test_linux_deb_architectures(self):
        self.script('apt-get','printf "apt %s\\n" "$*" >> "$TEST_ROOT/actions"')
        self.env['TEST_OS']='Linux'
        for arch,deb in [('aarch64','arm64'),('x86_64','amd64')]:
            with self.subTest(arch=arch):
                self.env['TEST_ARCH']=arch; self.asset('geist-diktat_'+deb+'.deb')
                p=self.run_install(); self.assertEqual(p.returncode,0,p.stderr)
                self.assertIn('geist-diktat_'+deb+'.deb',self.actions())

    def test_extraction_failure_preserves_previous_install(self):
        previous=self.root/'home/.local/geist-diktat'; previous.mkdir(parents=True)
        (previous/'working').write_text('old working installation')
        self.script('tar','exit 2')
        p=self.run_install(); self.assertNotEqual(p.returncode,0)
        self.assertTrue((previous/'working').exists(),'old installation deleted before extraction succeeds')

if __name__=='__main__': unittest.main(verbosity=2)
