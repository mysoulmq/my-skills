import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts'))
from check_source_delivery import validate
from assemble import require_source_inventory

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

    def test_source_label_alone_does_not_count_as_question(self):
        r,q,p,t=self.fixture();t[0]='（某地模拟）另一道题'
        result=validate(r,q,p,t)
        self.assertFalse(result['pass']);self.assertEqual(result['missingQuestionIds'],['q'])
        self.assertEqual(result['deliveredCount'],0)

    def test_choice_option_must_reach_actual_slide(self):
        r,q,p,t=self.fixture()
        for x in r+q:x['options']=['选项甲','选项乙']
        t[0]+='选项甲'
        self.assertTrue(any('option 2' in e for e in validate(r,q,p,t)['errors']))
        t[0]+='选项乙';self.assertTrue(validate(r,q,p,t)['pass'])

    def test_upstream_omission_is_not_excused_by_optional(self):
        r,q,p,t=self.fixture();r.append({**r[0],'id':'c','prompt':'另一小问'})
        result=validate(r,q,p,t)
        self.assertFalse(result['pass']);self.assertEqual(result['unassignedSourceIds'],['c'])
        registry={'sourceRecords':r,'questions':q+[{'id':'q2','optional':True}]}
        with self.assertRaisesRegex(ValueError,'missing=.*q2'):
            require_source_inventory(registry,p)

    def test_only_diagnostic_page_does_not_replace_teaching(self):
        r,q,p,t=self.fixture();p[0]['stage']='diagnosis'
        with self.assertRaisesRegex(ValueError,'missing'):
            require_source_inventory({'sourceRecords':r,'questions':q},p)

    def test_question_assembly_requires_independent_inventory(self):
        with self.assertRaisesRegex(ValueError,'source-registry'):
            require_source_inventory(None,[{'questionId':'q'}])
        require_source_inventory(None,[])
        r,q,p,t=self.fixture()
        require_source_inventory({'sourceRecords':r,'questions':q},p)

    def test_empty_processed_set_cannot_erase_original_questions(self):
        r,q,p,t=self.fixture()
        with self.assertRaisesRegex(ValueError,'Every original'):
            require_source_inventory({'sourceRecords':r,'questions':[]},[])

    def test_original_record_assignment_is_checked_before_writing(self):
        r,q,p,t=self.fixture();q[0]['sourceRecords']=['a']
        with self.assertRaisesRegex(ValueError,'Every original'):
            require_source_inventory({'sourceRecords':r,'questions':q},p)
        q[0]['sourceRecords']=['a','a','b']
        with self.assertRaisesRegex(ValueError,'Every original'):
            require_source_inventory({'sourceRecords':r,'questions':q},p)
