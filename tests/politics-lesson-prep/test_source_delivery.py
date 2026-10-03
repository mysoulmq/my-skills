import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts'))
from check_source_delivery import validate

class DeliveryTests(unittest.TestCase):
    def fixture(self):
        r={'id':'a','material':'材料','prompt':'说明理由','sourceLabel':'（某地模拟）','referenceAnswer':'答案'}
        s={**r,'id':'b'}
        q={**r,'id':'q','sourceRecords':['a','b']}
        return [r,s],[q],[{'questionId':'q','page':1}],['（某地模拟）材料说明理由答案']
    def test_duplicate_sources_merge_without_losing_coverage(self):
        result=validate(*self.fixture());self.assertTrue(result['pass']);self.assertEqual(result['uniqueCount'],1)
    def test_repeated_question_is_rejected(self):
        r,q,p,t=self.fixture();q[0]['sourceRecords']=['a'];q.append({**q[0],'id':'q2','sourceRecords':['b']});p.append({'questionId':'q2','page':1})
        self.assertTrue(any('exact duplicate' in x for x in validate(r,q,p,t)['errors']))
    def test_source_must_be_visible_on_every_page(self):
        r,q,p,t=self.fixture();p.append({'questionId':'q','page':2});t.append('自拟题名材料')
        self.assertTrue(any('P2 missing' in x for x in validate(r,q,p,t)['errors']))
    def test_different_subquestion_not_merged(self):
        r,q,p,t=self.fixture();r[1]['prompt']='如何做'
        self.assertTrue(any('changed source' in x for x in validate(r,q,p,t)['errors']))
    def test_conflicting_answers_not_silently_merged(self):
        r,q,p,t=self.fixture();r[1]['referenceAnswer']='另一答案'
        self.assertTrue(any('variants' in x for x in validate(r,q,p,t)['errors']))
    def test_no_source_does_not_require_invention(self):
        r,q,p,t=self.fixture()
        for x in r:x['sourceLabel']=''
        t[0]='材料说明理由答案';self.assertTrue(validate(r,q,p,t)['pass'])
    def test_unmapped_question_rejected(self):
        r,q,p,t=self.fixture();self.assertFalse(validate(r,q,[],t)['pass'])
    def test_changed_material_rejected(self):
        r,q,p,t=self.fixture();q[0]['material']='自编材料';self.assertFalse(validate(r,q,p,t)['pass'])
