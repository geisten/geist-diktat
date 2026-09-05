import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'runtime/diktat_runtime.py'

class Runtime(unittest.TestCase):
    def command(self,capture,decoder,buffer=6):
        return [sys.executable,str(RUNTIME),'--capture',capture,'--buffer-seconds',str(buffer),'--',sys.executable,'-c',decoder]
    def run_pipeline(self,capture,decoder,buffer=6):
        return subprocess.run(self.command(capture,decoder,buffer),capture_output=True,timeout=6)
    def test_finite_pcm_is_delivered_exactly(self):
        p=self.run_pipeline("printf 'abcdefgh'","import sys; print(repr(sys.stdin.buffer.read()))")
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout,b"b'abcdefgh'\n")
    def test_capture_error(self):
        p=self.run_pipeline('exit 17','import sys; sys.stdin.buffer.read()')
        self.assertEqual(p.returncode,17,p.stderr)
    def test_capture_failure_after_stdout_eof_is_not_success(self):
        p=self.run_pipeline('exec 1>&-; sleep 0.1; exit 17','import sys;sys.stdin.buffer.read()')
        self.assertEqual(p.returncode,17,p.stderr)
    def test_decoder_error(self):
        p=self.run_pipeline('sleep 10','raise SystemExit(19)')
        self.assertEqual(p.returncode,19,p.stderr)
    def test_early_decoder_success_is_failure(self):
        p=self.run_pipeline('sleep 10','pass')
        self.assertEqual(p.returncode,70,p.stderr)
    def test_bounded_overload_stops_instead_of_blocking(self):
        p=self.run_pipeline('cat /dev/zero','import time;time.sleep(60)',.1)
        self.assertEqual(p.returncode,75,p.stderr);self.assertIn(b'overload:',p.stderr)
    def test_invalid_buffer(self):
        for value in ('nan','inf','0','61'):
            p=self.run_pipeline('true','pass',value)
            self.assertEqual(p.returncode,2);self.assertNotIn(b'Traceback',p.stderr)
    def test_term_stops_descendants(self):
        with tempfile.TemporaryDirectory() as d:
            pidfile=Path(d)/'pid'
            command="sleep 60 & echo $! > '"+str(pidfile)+"'; wait"
            p=subprocess.Popen(self.command(command,'import sys;sys.stdin.buffer.read()'),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                end=time.monotonic()+3
                while not pidfile.exists() and time.monotonic()<end:time.sleep(.01)
                self.assertTrue(pidfile.exists());child=int(pidfile.read_text())
                p.terminate();out,err=p.communicate(timeout=3)
                self.assertEqual(p.returncode,143,err)
                # A Linux container's PID 1 may retain a dead orphan zombie;
                # /proc state Z is stopped, not a surviving audio process.
                state=Path('/proc')/str(child)/'stat'
                if state.exists():self.assertEqual(state.read_text().split()[2],'Z')
                else:
                    with self.assertRaises(ProcessLookupError):os.kill(child,0)
            finally:
                if p.poll() is None:p.kill();p.wait()

class LineSink(unittest.TestCase):
    def test_streaming_literal_arguments(self):
        cmd=[sys.executable,str(ROOT/'runtime/line_sink.py'),'--',sys.executable,'-c','import json,sys;print(json.dumps(sys.argv[1:]))']
        text='Grüße $(touch /tmp/never-execute); :q!\nzweite Zeile\n'
        p=subprocess.run(cmd,input=text,text=True,capture_output=True,timeout=5)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual([json.loads(x) for x in p.stdout.splitlines()],[[x] for x in text.splitlines()])
    def test_sink_failure_and_bad_utf8(self):
        for data,script in [(b'text\n','raise SystemExit(7)'),(b'\xff\n','pass')]:
            p=subprocess.run([sys.executable,str(ROOT/'runtime/line_sink.py'),'--',sys.executable,'-c',script],input=data,capture_output=True)
            self.assertNotEqual(p.returncode,0)
    def test_oversize_line_rejected(self):
        p=subprocess.run([sys.executable,str(ROOT/'runtime/line_sink.py'),'--','cat'],input=b'x'*65537,capture_output=True)
        self.assertNotEqual(p.returncode,0)
