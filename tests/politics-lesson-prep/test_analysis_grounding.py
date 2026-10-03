import copy
import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts/check_analysis_grounding.py'
spec=importlib.util.spec_from_file_location('grounding',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class GroundingTest(unittest.TestCase):
    def setUp(self):
        self.source={'units':[{'id':'u1','page':'2','text':'理论命题甲。'},{'id':'u2','page':'2','text':'理论命题乙。'}]}
        self.data={'questions':[{'id':'q1','material':'事实甲，事实乙。','answer':[{},{}],'analysis':[
            {'evidence':'事实甲','evidenceDisplay':'事实甲','principle':'理论命题甲。','knowledgeRefs':[{'unitId':'u1','quote':'理论命题甲。'}],'answerRefs':[1]},
            {'evidence':'事实乙','evidenceDisplay':'事实乙','principle':'理论命题乙。','knowledgeRefs':[{'unitId':'u2','quote':'理论命题乙。'}],'answerRefs':[2]}]}]}
    def test_valid(self):self.assertEqual(m.check(self.data,self.source),[])
    def test_application_cannot_replace_knowledge(self):
        self.data['questions'][0]['analysis'][0]['principle']='现实需要得到满足'
        self.assertTrue(any('preserve cited' in e for e in m.check(self.data,self.source)))
    def test_fabricated_knowledge_quote(self):
        self.data['questions'][0]['analysis'][0]['knowledgeRefs'][0]['quote']='自行发明的命题'
        self.assertTrue(any('does not match' in e for e in m.check(self.data,self.source)))
    def test_missing_answer_coverage(self):
        self.data['questions'][0]['analysis'][1]['answerRefs']=[1]
        self.assertTrue(any('cover every' in e for e in m.check(self.data,self.source)))
    def test_material_added_fact(self):
        self.data['questions'][0]['analysis'][0]['evidence']='题目未写的事实'
        self.assertTrue(any('original material' in e for e in m.check(self.data,self.source)))
if __name__=='__main__':unittest.main()
