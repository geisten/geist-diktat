"""Adversarial evidence checks and application-observation timing oracle."""
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'benchmarks'))
from check_gates import evaluate
from quality import aggregate
from release_evidence import select_run
from latency import analyze, load_trace


class SpeechEvidence(unittest.TestCase):
    def fixture(self):
        rows=[dict(id='clip',group='g',wav_sha256='a'*64,errors=1,substitutions=1,
                   deletions=0,insertions=0,reference_words=10,wer=.1,audio_s=2,wall_s=1,exit_code=0)]
        return dict(source_commit='b'*40,manifest_sha256='c'*64,files={'binary':'d'*64},
                    platform='Linux',threads=4,runs=rows,groups=aggregate(rows))
    policy=dict(require_run_evidence=True,required_files=['binary'],groups={'g':{'min_clips':1,'min_reference_words':10,'max_wer':.1}})
    def test_complete_boundary_report_and_exact_commit(self):
        self.assertTrue(evaluate(self.fixture(),self.policy,'b'*40)['passed'])
        self.assertFalse(evaluate(self.fixture(),self.policy,'e'*40)['passed'])
    def test_engine_specific_files_and_unknown_engines(self):
        policy=dict(self.policy,engines={'geist':{'required_files':['tower']},'whisper':{'required_report_hashes':['whisper_cli_sha256']}})
        r=self.fixture();r['engine']='geist'
        self.assertFalse(evaluate(r,policy)['passed'])
        r['files']['tower']='a'*64
        self.assertTrue(evaluate(r,policy)['passed'])
        r['engine']='whisper'
        self.assertFalse(evaluate(r,policy)['passed'])
        r['whisper_cli_sha256']='a'*64
        self.assertTrue(evaluate(r,policy)['passed'])
        r['engine']='unknown'
        self.assertFalse(evaluate(r,policy)['passed'])

    def test_aggregates_cannot_hide_word_errors(self):
        r=self.fixture();r['runs'][0]['errors']=5;r['runs'][0]['substitutions']=5;r['runs'][0]['wer']=.5
        self.assertFalse(evaluate(r,self.policy)['passed'])
    def test_forged_wer_in_run_cannot_pass(self):
        r=self.fixture();r['runs'][0]['wer']=0
        self.assertFalse(evaluate(r,self.policy)['passed'])
    def test_negative_nan_infinite_and_boolean_measurements_rejected(self):
        for bad in (-1,float('nan'),float('inf'),True,'0'):
            for field in ('wer','wall_s','reference_words'):
                with self.subTest(bad=bad,field=field):
                    r=self.fixture();r['runs'][0][field]=bad
                    self.assertFalse(evaluate(r,self.policy)['passed'])
    def test_missing_hash_rows_or_duplicate_clips_rejected(self):
        for mutation in ('files','runs','manifest_sha256'):
            r=self.fixture();del r[mutation]
            self.assertFalse(evaluate(r,self.policy)['passed'])
        r=self.fixture();r['runs']*=2;r['groups']=aggregate(r['runs'])
        self.assertFalse(evaluate(r,self.policy)['passed'])
    def test_timeout_and_process_failure_not_hidden_by_zero_wer(self):
        for key,value in [('timeout',True),('exit_code',17)]:
            r=self.fixture();r['runs'][0][key]=value;r['groups']=aggregate(r['runs'])
            self.assertFalse(evaluate(r,self.policy)['passed'])
    def test_malformed_policy_fails_closed(self):
        for policy in ({},{'groups':{}},{'groups':{'g':None}},{'groups':{'g':{'min_clips':-1,'max_wer':.1}}}):
            self.assertFalse(evaluate(self.fixture(),policy)['passed'])
    def test_missing_and_nonfinite_json_cli_are_failures_with_report(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'input.json';out=Path(d)/'out.json'
            for text in (None,'{"groups":NaN}', '{'):
                if text is not None:path.write_text(text)
                p=subprocess.run([sys.executable,str(ROOT/'benchmarks/check_gates.py'),str(path),'--output',str(out)],capture_output=True)
                self.assertNotEqual(p.returncode,0);self.assertFalse(json.loads(out.read_text())['passed'])
    def test_latest_failed_run_never_falls_back_to_old_success(self):
        run=dict(databaseId=1,headSha='b'*40,status='completed',conclusion='success')
        self.assertEqual(select_run([run],'b'*40),1)
        for altered in ({'headSha':'c'*40},{'status':'in_progress'},{'conclusion':'failure'}):
            with self.assertRaises(ValueError):select_run([dict(run,**altered),run],'b'*40)
        with self.assertRaises(ValueError):select_run([],'b'*40)


class PacedSource(unittest.TestCase):
    def test_complete_frame_is_delivered_at_its_end(self):
        import os
        import wave
        with tempfile.TemporaryDirectory() as d:
            wav=Path(d)/'frame.wav';trace=Path(d)/'trace.jsonl'
            with wave.open(str(wav),'wb') as w:
                w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes(bytes(640))
            p=subprocess.run([sys.executable,str(ROOT/'benchmarks/trace_capture.py'),str(wav)],
                env=dict(os.environ,GEIST_DIKTAT_TRACE=str(trace)),capture_output=True,timeout=3)
            self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout,bytes(640))
            events=[json.loads(line) for line in trace.read_text().splitlines()]
            self.assertGreaterEqual(events[-1]['monotonic_ns']-events[0]['origin_ns'],20_000_000)


class InsertionLatency(unittest.TestCase):
    def fixture(self):
        def e(component,event,t,**v):return dict(schema=1,component=component,event=event,monotonic_ns=t,**v)
        return [e('capture','audio_origin',0,origin_ns=0),
                e('capture','source_summary',2_000_000_000,sent_bytes=64000,failed=False),
                e('core','output_ready',2_000_000_000,output_seq=1),
                e('core','output_emitted',2_000_000_001,output_seq=1),
                e('ibus','commit_requested',2_100_000_000,output_seq=1),
                e('gtk','app_observed',3_000_000_000,output_seq=1),
                e('core','input_summary',3_100_000_000,audio_end_sample=32000),
                e('runtime','input_summary',3_200_000_000,received_bytes=64000,delivered_bytes=64000,failed=False)]
    annotations=[dict(output_seq=1,end_sample=16000)]
    def test_waits_for_terminal_accounting_without_treating_window_exit_as_end(self):
        import threading
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'trace.jsonl';path.write_text('')
            timer=threading.Timer(.05,lambda:path.write_text(''.join(json.dumps(e)+'\n' for e in self.fixture())))
            timer.start()
            try:self.assertEqual(analyze(load_trace(path,1),self.annotations)['p95_insertion_s'],2)
            finally:timer.join()
            path.write_text('')
            with self.assertRaises(ValueError):load_trace(path,.02)

    def test_insertion_is_app_observation_not_stdout_or_ibus_request(self):
        r=analyze(self.fixture(),self.annotations)
        self.assertEqual(r['p95_insertion_s'],2)
        self.assertEqual(r['measurements'][0]['output_ready_to_insertion_s'],1)
        self.assertFalse(r['full_product_approval'])
    def test_no_widget_receipt_no_latency_pass(self):
        e=[r for r in self.fixture() if r['event']!='app_observed']
        with self.assertRaises(ValueError):analyze(e,self.annotations)
    def test_missing_annotation_cannot_be_replaced_by_rms(self):
        with self.assertRaises(ValueError):analyze(self.fixture(),[])
    def test_overload_incomplete_delivery_and_duplicate_session_rejected(self):
        for key,value in [('failed',True),('delivered_bytes',63998),('received_bytes',None)]:
            e=self.fixture();e[-1][key]=value
            with self.assertRaises(ValueError):analyze(e,self.annotations)
        e=self.fixture();e.append(e[0])
        with self.assertRaises(ValueError):analyze(e,self.annotations)
    def test_duplicate_or_noncausal_observation_rejected(self):
        e=self.fixture();e.append(e[5])
        with self.assertRaises(ValueError):analyze(e,self.annotations)
        e=self.fixture();e[5]['monotonic_ns']=1
        with self.assertRaises(ValueError):analyze(e,self.annotations)
    def test_float_and_out_of_audio_annotations_rejected(self):
        for sample in (float('nan'),0,32001,True):
            with self.assertRaises(ValueError):analyze(self.fixture(),[dict(output_seq=1,end_sample=sample)])
    def test_post_flush_log_may_follow_widget_callback(self):
        # Scheduling after fflush can delay the emitted diagnostic; readiness
        # is timestamped before write and actual insertion in the widget itself.
        e=self.fixture();e[3]['monotonic_ns']=3_000_000_001
        self.assertEqual(analyze(e,self.annotations)['p95_insertion_s'],2)

if __name__=='__main__':unittest.main(verbosity=2)
