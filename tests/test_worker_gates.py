"""Reject false green worker reports without invoking a model or microphone."""
import copy
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'benchmarks'))
from check_worker_gates import evaluate,MODEL_SHA
from quality import aggregate


class WorkerGates(unittest.TestCase):
    def setUp(self):
        rows=[]
        for group,words in [('de-read-clean',[24]*11+[30]),('de-noise-10db',[21]*5+[25])]:
            for i,n in enumerate(words):
                rows.append(dict(id=group+str(i),group=group,passed=True,exit_code=0,worker_pid=42,
                    wav_sha256='a'*64,core_samples=32000,source=dict(sent_bytes=64000),audio_s=1,supplied_audio_s=2,wall_s=.2,
                    errors=0,substitutions=0,deletions=0,insertions=0,reference_words=n,wer=0))
        self.report=dict(source_commit='a'*40,working_tree_dirty=False,files=dict(model=MODEL_SHA,binary='b'*64,manifest='c'*64),paced=False,
            implementation_sha256={name:'d'*64 for name in ('src/whisper_diktat.cpp','runtime/model_worker.py','runtime/pipe_limits.py','benchmarks/worker_bench.py')},
            audio_context='full',chunk_seconds=28,temperature_fallback=True,configs=[dict(threads=4,beam_size=5,wait_policy='PASSIVE',
            all_audio_accounted=True,runs=rows,groups=aggregate(rows))])
    def checked(self):return evaluate(self.report,'a'*40)
    def test_complete_selected_worker_report_passes(self):self.assertTrue(self.checked()['passed'])
    def test_source_model_or_parameters_cannot_be_substituted(self):
        original=copy.deepcopy(self.report)
        for key,value in [('source_commit','b'*40),('working_tree_dirty',True),('paced',True),('audio_context','adaptive'),('chunk_seconds',12),('temperature_fallback',False)]:
            self.report=copy.deepcopy(original);self.report[key]=value;self.assertFalse(self.checked()['passed'])
        self.report=copy.deepcopy(original);self.report['files']['model']='b'*64;self.assertFalse(self.checked()['passed'])
        self.report=copy.deepcopy(original);self.report['configs'][0]['beam_size']=3;self.assertFalse(self.checked()['passed'])
    def test_missing_or_duplicate_fixture_fails(self):
        rows=self.report['configs'][0]['runs'];rows[1]['id']=rows[0]['id'];self.assertFalse(self.checked()['passed'])
        rows.pop();self.assertFalse(self.checked()['passed'])
    def test_unaccounted_audio_cannot_pass(self):
        row=self.report['configs'][0]['runs'][0]
        row['core_samples']-=1;self.assertFalse(self.checked()['passed'])
        row['core_samples']+=1;row['source']['failed']=True;self.assertFalse(self.checked()['passed'])
    def test_reloaded_worker_is_not_reuse(self):
        self.report['configs'][0]['runs'][1]['worker_pid']=43;self.assertFalse(self.checked()['passed'])
    def test_nan_or_false_aggregate_cannot_pass(self):
        group=self.report['configs'][0]['groups']['de-read-clean']
        group['wall_s']=float('nan');self.assertFalse(self.checked()['passed'])
        group['wall_s']=2.4;group['errors']=9;self.assertFalse(self.checked()['passed'])
    def test_wer_failure_is_not_hidden_by_successful_exit(self):
        config=self.report['configs'][0];row=config['runs'][0]
        row.update(errors=30,insertions=30,wer=30/row['reference_words']);config['groups']=aggregate(config['runs'])
        result=self.checked();self.assertFalse(result['passed']);self.assertIn('de-read-clean exceeds WER limit',result['failures'])
    def test_missing_provenance_fails(self):
        original=copy.deepcopy(self.report)
        self.report['files'].pop('binary');self.assertFalse(self.checked()['passed'])
        self.report=copy.deepcopy(original);self.report['implementation_sha256']={};self.assertFalse(self.checked()['passed'])
    def test_noise_threshold_is_not_relaxed_for_one_word(self):
        config=self.report['configs'][0];row=config['runs'][12]
        for errors,passed in ((32,True),(33,False)):
            row.update(errors=errors,insertions=errors,wer=errors/row['reference_words'])
            config['groups']=aggregate(config['runs']);self.assertEqual(self.checked()['passed'],passed)

    def test_malformed_evidence_fails_closed(self):
        for value in (None,[],{},dict(configs=[])):
            self.assertFalse(evaluate(value,'a'*40)['passed'])

if __name__=='__main__':unittest.main()
