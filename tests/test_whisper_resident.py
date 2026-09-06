"""Exercise the actual resident frontend with a controlled public engine API.

Real-model quality is measured separately; these tests cannot establish WER.
"""
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]

def audio(samples,value=1000):
    return struct.pack('<h',value)*samples

class ResidentWhisper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.binary=Path(cls.temp.name)/'resident'
        subprocess.run([os.environ.get('CXX','c++'),'-std=c++17','-Wall','-Wextra','-Werror',
            '-fsanitize=address,undefined','-fno-omit-frame-pointer','-g','-pthread',
            '-I'+str(ROOT/'tests/whisper_stub'),str(ROOT/'src/whisper_diktat.cpp'),
            str(ROOT/'tests/whisper_stub/stub.cpp'),'-o',str(cls.binary)],check=True,capture_output=True)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def run_audio(self,data,args=(),**env):
        with tempfile.TemporaryDirectory() as d:
            log=Path(d)/'engine.log';trace=Path(d)/'trace.jsonl'
            p=subprocess.run([str(self.binary),'model.bin',*args],input=data,capture_output=True,timeout=8,
                env=dict(os.environ,STUB_LOG=str(log),GEIST_DIKTAT_TRACE=str(trace),**env))
            return p,log.read_text().splitlines() if log.exists() else [],[json.loads(s) for s in trace.read_text().splitlines()] if trace.exists() else []
    def test_model_loaded_once_for_many_segments_and_freed_once(self):
        p,log,trace=self.run_audio((audio(8000)+bytes(25600))*20)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(log.count('load 0'),1);self.assertIn('free 20',log)
        self.assertEqual(p.stdout.decode().splitlines(),['Hallo Welt Grüße!']*20)
        peaks=[r['audio_end_sample'] for r in trace if r['event']=='peak_queue_samples']
        self.assertTrue(peaks and max(peaks)<=16000)
        self.assertEqual([r['output_seq'] for r in trace if r['event']=='output_emitted'],list(range(1,21)))
    def test_eof_keeps_complete_partial_frame_and_negative_samples(self):
        p,log,_=self.run_audio(audio(8001,-32768));self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('decode 8001',log);self.assertIn('first_sample -32768',log)
    def test_odd_byte_is_failure(self):
        p,_,_=self.run_audio(audio(4000)+b'x');self.assertEqual(p.returncode,74)
    def test_silence_never_calls_engine(self):
        p,log,_=self.run_audio(bytes(32000*5));self.assertEqual(p.returncode,0);self.assertEqual(p.stdout,b'')
        self.assertIn('free 0',log)
    def test_short_utterance_is_not_decoded(self):
        p,log,_=self.run_audio(audio(7999));self.assertEqual(p.returncode,0);self.assertIn('free 0',log)
    def test_long_utterance_has_bounded_windows_and_preserves_samples(self):
        p,log,trace=self.run_audio(audio(29*16000));self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual([s for s in log if s.startswith('decode ')],['decode 448000','decode 16000'])
        self.assertEqual([r['audio_end_sample'] for r in trace if r['event']=='input_summary'],[464000])
    def test_invalid_configuration_fails_before_loading(self):
        for args,env in [(('nan',),{}),(('0',),{}),(('300x',),{}),((),{'GEIST_WHISPER_BEAM_SIZE':'0'}),((),{'OMP_NUM_THREADS':'-1'})]:
            with self.subTest(args=args,env=env):
                p,log,_=self.run_audio(b'',args,**env);self.assertNotEqual(p.returncode,0);self.assertEqual(log,[])
    def test_beam_configuration_reaches_decoder(self):
        p,log,_=self.run_audio(audio(8000),GEIST_WHISPER_BEAM_SIZE='1');self.assertEqual(p.returncode,0);self.assertIn('beam 1',log)
    def test_load_failure_never_announces_ready(self):
        p,_,_=self.run_audio(b'',STUB_LOAD_FAIL='1');self.assertNotEqual(p.returncode,0);self.assertNotIn(b'listening',p.stderr)
    def test_decode_failure_is_nonzero_without_text(self):
        p,log,_=self.run_audio(audio(8000),STUB_DECODE_FAIL='1');self.assertNotEqual(p.returncode,0);self.assertEqual(p.stdout,b'');self.assertIn('free 1',log)
    def test_empty_recognition_does_not_emit_blank_line(self):
        p,_,_=self.run_audio(audio(8000),STUB_EMPTY='1');self.assertEqual(p.returncode,0);self.assertEqual(p.stdout,b'')
    def test_oversized_transcript_fails_without_partial_line(self):
        p,_,_=self.run_audio(audio(8000),STUB_LARGE='1');self.assertNotEqual(p.returncode,0);self.assertEqual(p.stdout,b'')
    def test_fragmented_stdin_reassembles_samples(self):
        p=subprocess.Popen([str(self.binary),'model.bin'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            data=audio(8001)
            for offset in range(0,len(data),113):p.stdin.write(data[offset:offset+113]);p.stdin.flush()
            p.stdin.close();p.stdin=None
            out,err=p.communicate(timeout=5);self.assertEqual(p.returncode,0,err);self.assertEqual(out.decode(),'Hallo Welt Grüße!\n')
        finally:
            if p.poll() is None:p.kill();p.wait()
    def test_stop_during_idle_and_active_decode(self):
        for decoding in [False,True]:
            with self.subTest(decoding=decoding):
                p=subprocess.Popen([str(self.binary),'model.bin'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    env=dict(os.environ,STUB_BLOCK='1'))
                try:
                    self.assertIn(b'listening',p.stderr.readline())
                    if decoding:
                        p.stdin.write(audio(8000)+bytes(25600));p.stdin.flush()
                        self.assertIn(b'stub: decoding',p.stderr.readline())
                    start=time.monotonic();p.send_signal(signal.SIGTERM)
                    out,err=p.communicate(timeout=1)
                    self.assertLess(time.monotonic()-start,1);self.assertEqual(p.returncode,143,err);self.assertEqual(out,b'')
                finally:
                    if p.poll() is None:p.kill();p.wait()
    def test_broken_output_pipe_is_failure(self):
        read_fd,write_fd=os.pipe();os.close(read_fd)
        try:
            p=subprocess.run([str(self.binary),'model.bin'],input=audio(8000),stdout=write_fd,stderr=subprocess.PIPE,timeout=5)
            self.assertEqual(p.returncode,1,p.stderr);self.assertIn(b'stdout write failed',p.stderr)
        finally:os.close(write_fd)
    def test_input_read_error_is_failure(self):
        fd=os.open(ROOT,os.O_RDONLY)
        try:
            p=subprocess.run([str(self.binary),'model.bin'],stdin=fd,capture_output=True,timeout=5)
            self.assertEqual(p.returncode,74,p.stderr);self.assertEqual(p.stdout,b'')
        finally:os.close(fd)
