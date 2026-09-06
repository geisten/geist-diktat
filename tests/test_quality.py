"""Independent WER oracle checks: edits, Unicode, empty input and aggregation."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'benchmarks'))
from quality import score, words, aggregate

class QualityMetrics(unittest.TestCase):
    def test_german_unicode_normalization(self):
        self.assertEqual(score('GRÜẞE, schöne Welt!', 'grüße scho\u0308ne welt')['wer'],0)
    def test_does_not_hide_dialect_or_number_errors(self):
        self.assertEqual(score('zwei Häuser', '2 Häusle')['substitutions'],2)
    def test_deletion(self):
        s=score('ich gehe heute nach Hause','ich gehe nach Hause')
        self.assertEqual((s['deletions'],s['wer']),(1,.2))
    def test_insertion(self):
        self.assertEqual(score('hallo','hallo du da')['insertions'],2)
        self.assertEqual(score('hallo','hallo du da')['wer'],2)
    def test_substitution(self):
        self.assertEqual(score('das ist gut','das war gut')['substitutions'],1)
    def test_empty_reference_is_not_zero_wer(self):
        self.assertIsNone(score('','halluziniert')['wer'])
        self.assertEqual(score('','halluziniert')['insertions'],1)
    def test_empty_output_counts_all_deletions(self):
        self.assertEqual(score('kein Text verloren','')['wer'],1)
    def test_corpus_wer_is_word_weighted(self):
        rows=[]
        for ref,hyp in [('eins','falsch'),('eins zwei drei vier','eins zwei drei vier')]:
            rows.append(dict(score(ref,hyp),group='g',audio_s=1,wall_s=2,exit_code=0))
        self.assertEqual(aggregate(rows)['g']['wer'],.2)
    def test_repeated_words_alignment(self):
        s=score('ja ja nein ja','ja nein ja ja')
        self.assertEqual(s['errors'],2)
        self.assertEqual(s['errors'],sum(s[k] for k in ('substitutions','deletions','insertions')))
    def test_hyphens_and_apostrophes_documented(self):
        self.assertEqual(words("E-Mail d'Chind"),['e','mail','d','chind'])

if __name__=='__main__':unittest.main(verbosity=2)
