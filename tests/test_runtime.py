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
    def test_trace_accounts_for_all_delivered_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'trace.jsonl'
            p=subprocess.run(self.command("printf 'abcdefgh'","import sys;sys.stdin.buffer.read()"),
                env=dict(os.environ,GEIST_DIKTAT_TRACE=str(path)),capture_output=True,timeout=6)
            self.assertEqual(p.returncode,0,p.stderr)
            events=[json.loads(line) for line in path.read_text().splitlines()]
            summary=events[-1]
            self.assertEqual((summary['received_bytes'],summary['delivered_bytes'],summary['unconfirmed_bytes']),(8,8,0))
            self.assertFalse(summary['failed']);self.assertNotIn('abcdefgh',path.read_text())

    def test_trace_exposes_overload_and_unconfirmed_audio(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'trace.jsonl'
            p=subprocess.run(self.command('cat /dev/zero','import time;time.sleep(60)',.1),
                env=dict(os.environ,GEIST_DIKTAT_TRACE=str(path)),capture_output=True,timeout=6)
            self.assertEqual(p.returncode,75,p.stderr)
            summary=json.loads(path.read_text().splitlines()[-1])
            self.assertTrue(summary['failed']);self.assertGreater(summary['unconfirmed_bytes'],0)
            self.assertLessEqual(summary['peak_queue_bytes'],3200)

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
    def test_descendant_ignoring_term_is_killed_after_leader_exits(self):
        import shlex
        with tempfile.TemporaryDirectory() as d:
            pidfile=Path(d)/'pid'
            code="import os,signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);open("+repr(str(pidfile))+",'w').write(str(os.getpid()));time.sleep(60)"
            capture=shlex.quote(sys.executable)+' -c '+shlex.quote(code)+' & wait'
            p=subprocess.Popen(self.command(capture,'import sys;sys.stdin.buffer.read()'),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                end=time.monotonic()+3
                while not pidfile.exists() and time.monotonic()<end:time.sleep(.01)
                self.assertTrue(pidfile.exists());child=int(pidfile.read_text())
                p.terminate();p.communicate(timeout=3)
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

class CommandRunner(unittest.TestCase):
    def test_success_and_error_status(self):
        for code in (0,17):
            p=subprocess.run([sys.executable,str(ROOT/'runtime/command_runner.py'),'--',sys.executable,'-c','raise SystemExit('+str(code)+')'],capture_output=True,timeout=3)
            self.assertEqual(p.returncode,code,p.stderr)
    def test_term_bounds_a_stubborn_command(self):
        p=subprocess.Popen([sys.executable,str(ROOT/'runtime/command_runner.py'),'--',sys.executable,'-c','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);print("ready",flush=True);time.sleep(60)'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            self.assertEqual(p.stdout.readline(),b'ready\n');p.terminate();p.communicate(timeout=4)
            self.assertEqual(p.returncode,143)
        finally:
            if p.poll() is None:p.kill();p.wait()
