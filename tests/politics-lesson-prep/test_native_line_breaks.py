import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts'))
from native_line_breaks import wrap_native_text,line_errors

class WrapTests(unittest.TestCase):
    def wrap(self,text,width):return wrap_native_text(text,width,len)
    def test_period_moves_with_preceding_content_without_loss(self):
        text='要自觉遵循社会发展的客观规律。'
        rows=self.wrap(text,len(text)-1)
        self.assertEqual(rows[-1],'律。')
        self.assertEqual(''.join(rows),text)
        self.assertFalse(line_errors(rows))
    def test_punctuation_clusters_and_parentheses(self):
        text='某观点（在实践中形成），要遵循规律。'
        rows=self.wrap(text,7)
        self.assertFalse(line_errors(rows));self.assertEqual(''.join(rows),text)
    def test_numbers_units_and_enumeration_stay_together(self):
        for token in ('2026年','3.5%','40分钟','1. 甲','①甲','——'):
            rows=self.wrap('前文'+token+'后文',max(len(token),4))
            self.assertTrue(any(token in row for row in rows),(token,rows))
    def test_too_narrow_fails_without_overflow_or_deletion(self):
        with self.assertRaisesRegex(ValueError,'Unbreakable'):
            self.wrap('2026年',3)
    def test_real_width_and_safety_used(self):
        rows=wrap_native_text('甲乙丙丁。',8,lambda s:len(s)*2,safety=2)
        self.assertTrue(all(len(row)*2<=6 for row in rows))
    def test_explicit_bad_break_not_silently_kept(self):
        with self.assertRaises(ValueError):self.wrap('客观规律\n。',10)
    def test_styled_width_changes_rows(self):
        normal=wrap_native_text('甲乙丙丁戊。',6,len)
        bold=wrap_native_text('甲乙丙丁戊。',6,lambda s:len(s)*1.2)
        self.assertGreater(len(bold),len(normal));self.assertFalse(line_errors(bold))
