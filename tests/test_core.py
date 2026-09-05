"""Application contract tests; failures describe defects in the audited revision."""
import os
from pathlib import Path
import re
import shlex
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

def pcm(loud=25, quiet=40, amplitude=1000):
    return struct.pack('<h', amplitude) * 320 * loud + bytes(640 * quiet)

class Core(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binary = str(Path(cls.tmp.name) / 'core-stub')
        coverage = os.getenv('GEIST_TEST_COVERAGE_DIR')
        if coverage:
            Path(coverage).mkdir(parents=True, exist_ok=True)
            cls.binary = str(Path(coverage).resolve() / 'core-stub')
        cmd = shlex.split(os.getenv('CC', 'cc')) + ['-std=c2x', '-O1', '-g',
            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
            '-I' + str(ROOT / 'geistlib/include'), str(ROOT / 'tests/core_stub.c'),
            '-lm', '-o', cls.binary]
        if coverage:
            cmd += ['-fprofile-instr-generate', '-fcoverage-mapping']
        subprocess.run(cmd, check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_core(self, data=b'', args=('model.gguf',), fail='', piece=None, timeout=10):
        env = dict(os.environ, STUB_FAIL=fail, ASAN_OPTIONS='detect_leaks=0')
        if piece is not None:
            env['STUB_PIECE'] = piece
        p = subprocess.run([self.binary, *args], input=data, capture_output=True, env=env, timeout=timeout)
        stats = dict((k, int(v)) for k, v in re.findall(r'(\w+)=(\d+)', p.stderr.decode(errors='replace')))
        return p, stats

    def test_usage(self):
        p, s = self.run_core(args=())
        self.assertEqual(p.returncode, 2)
        self.assertIn(b'usage:', p.stderr)
        self.assertEqual(s['loads'], 0)

    def test_initialization_failures_cleanup(self):
        for failure, destroyed in [('backend',0), ('model',1), ('tower',2), ('session',2), ('tokenize',3), ('prefix',3)]:
            with self.subTest(failure=failure):
                p,s=self.run_core(fail=failure)
                self.assertEqual(p.returncode, 1)
                self.assertEqual(s['destroyed'], destroyed)
                self.assertEqual(p.stdout, b'')

    def test_silence(self):
        p,s=self.run_core(bytes(640*100))
        self.assertEqual(p.returncode, 0)
        self.assertEqual(s['begins'],0)
        self.assertEqual(p.stdout,b'')

    def test_x86_host_selects_available_accelerated_backend(self):
        p,s=self.run_core(fail='x86-host')
        self.assertEqual(p.returncode,0)
        self.assertEqual(s['selected_x86'],1,'x86 host falls back to scalar despite available cpu_x86')

    def test_open_requires_three_consecutive_frames(self):
        p,s=self.run_core(pcm(2,1)*10)
        self.assertEqual(s['begins'],0)

    def test_threshold_is_strict(self):
        p,s=self.run_core(pcm(amplitude=300))
        self.assertEqual(s['begins'],0)

    def test_negative_samples_rms(self):
        p,s=self.run_core(pcm(amplitude=-1000))
        self.assertEqual(s['ends'],1)

    def test_first_three_frames_preserved(self):
        p,s=self.run_core(pcm())
        self.assertEqual(s['samples'],65*320)

    def test_short_utterance_dropped(self):
        p,s=self.run_core(pcm(24))
        self.assertEqual(s['ends'],1)
        self.assertEqual(p.stdout,b'')

    def test_minimum_utterance_and_normalization(self):
        p,s=self.run_core(pcm())
        self.assertEqual(p.stdout,'Hallo Welt Grüße!\n'.encode())

    def test_multiple_utterances(self):
        p,s=self.run_core(pcm()*3)
        self.assertEqual(s['ends'],3)
        self.assertEqual(len(p.stdout.splitlines()),3)

    def test_thirty_minutes_use_one_model_and_preserve_all_turns(self):
        # 1400 * 1.3 s = 30 min 20 s of PCM. Unpaced, fake recognition:
        # lifecycle/segmentation stress only, not a real ASR conversation test.
        p,s=self.run_core(pcm()*1400,timeout=60)
        self.assertEqual(p.returncode,0)
        self.assertEqual((s['loads'],s['begins'],s['ends']),(1,1400,1400))
        self.assertEqual(s['samples'],1400*65*320)
        self.assertEqual(len(p.stdout.splitlines()),1400)
        self.assertEqual(s['destroyed'],3)

    def test_full_scale_pcm_does_not_overflow_rms(self):
        for amplitude in (-32768,32767):
            with self.subTest(amplitude=amplitude):
                p,s=self.run_core(pcm(amplitude=amplitude))
                self.assertEqual(p.returncode,0)
                self.assertEqual(s['ends'],1)

    def test_short_pause_keeps_one_utterance(self):
        p,s=self.run_core(pcm(25,39)+pcm())
        self.assertEqual(s['ends'],1)

    def test_maximum_segment(self):
        p,s=self.run_core(pcm(1400,0))
        self.assertEqual(s['samples'],28*16000)
        self.assertEqual(s['ends'],1)

    def test_eof_flushes_speech(self):
        p,s=self.run_core(pcm(25,0))
        self.assertEqual(s['ends'],1, 'EOF loses the final utterance')
        self.assertTrue(p.stdout)

    def test_partial_final_frame_preserved(self):
        p,s=self.run_core(pcm(25,0)+bytes(100))
        self.assertEqual(s['samples'],25*320+50)

    def test_invalid_threshold_rejected(self):
        for threshold in ['abc','nan','inf','-1','0','300junk']:
            with self.subTest(threshold=threshold):
                p,s=self.run_core(args=('model.gguf',threshold))
                self.assertEqual(p.returncode,2)
                self.assertEqual(s['loads'],0)

    def test_stream_errors_propagate(self):
        for failure in ['reset','begin','push','poll','end','prefill','decode']:
            with self.subTest(failure=failure):
                p,s=self.run_core(pcm(),fail=failure)
                self.assertNotEqual(p.returncode,0, 'runtime failure reported as success')

    def test_meta_output_dropped(self):
        p,s=self.run_core(pcm(),fail='meta')
        self.assertEqual(p.stdout,b'')
        self.assertIn(b'meta output',p.stderr)

    def test_repetition_guard(self):
        for failure in ['loop','cycle2']:
            p,s=self.run_core(pcm(),fail=failure)
            self.assertEqual(s['decoded'],8)

    def test_decode_cap(self):
        p,s=self.run_core(pcm(),fail='cap')
        self.assertEqual(s['decoded'],400)

    def test_output_cap(self):
        p,s=self.run_core(pcm(),piece='x'*8000)
        self.assertEqual(len(p.stdout),4096)

    def test_tokens_may_split_unicode(self):
        p,s=self.run_core(pcm(),fail="split-utf8")
        self.assertEqual(p.stdout,"ü\n".encode())

    def test_unicode_boundary_sanitized(self):
        p,s=self.run_core(pcm(),piece='a'*4094+'ü')
        try:
            p.stdout.decode('utf-8')
        except UnicodeDecodeError as error:
            self.fail('reply cap splits a UTF-8 character: '+str(error))

    def test_truncated_piece_memory_safety(self):
        p,s=self.run_core(args=('--append-boundary',))
        self.assertEqual(p.returncode,0,p.stderr.decode(errors='replace'))

if __name__ == '__main__':
    unittest.main(verbosity=2)
