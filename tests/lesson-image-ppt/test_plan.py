import importlib.util
from copy import deepcopy
from pathlib import Path
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / 'skills/lesson-image-ppt/scripts'
def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod
PLAN = load('check_plan')

class PlanTests(unittest.TestCase):
    def setUp(self):
        self.source = {'units':[{'id':'h','kind':'heading','text':'关系'},
                                {'id':'a','text':'一条依据'}, {'id':'b','text':'另一依据'}],
                       'knowledgeGroups':[{'id':'g','heading':'h','members':['a','b'], 'parallelSets':[['a','b']]}]}
        self.deck = {'slides':[{'type':'content','title':'h','blocks':[{'type':'paragraphs','items':[{'ref':'a'},{'ref':'b'}]}]}]}
    def test_complete_group_passes(self):
        self.assertTrue(PLAN.check(self.source,self.deck)['passed'])
    def test_source_to_slide_coverage_does_not_excuse_split(self):
        self.deck['slides'][0]['blocks'][0]['items'].pop()
        self.deck['slides'].append({'type':'content','title':'h','blocks':[{'type':'paragraphs','items':['b']}]})
        self.assertFalse(PLAN.check(self.source,self.deck)['passed'])
        self.source['knowledgeGroups'][0]['split']={'reason':'实测超出可用正文高度','measuredHeight':500,'availableHeight':420}
        self.assertTrue(PLAN.check(self.source,self.deck)['passed'])
    def test_heading_left_on_previous_page_fails(self):
        self.deck['slides'].insert(0,{'type':'content','title':'h','blocks':[]})
        self.assertFalse(PLAN.check(self.source,self.deck)['passed'])
    def test_parallel_indent_mismatch_fails(self):
        self.deck['slides'][0]['blocks'][0]['items'][1]['bullet']=True
        self.assertFalse(PLAN.check(self.source,self.deck)['passed'])
    def test_missing_groups_or_ungrouped_body_fail(self):
        s=deepcopy(self.source);s.pop('knowledgeGroups')
        self.assertFalse(PLAN.check(s,self.deck)['passed'])
        self.source['units'].append({'id':'c','text':'遗漏的正文'})
        self.assertFalse(PLAN.check(self.source,self.deck)['passed'])
    def test_map_excerpts_cannot_supply_content_placement(self):
        self.deck['slides'][0]['type']='knowledge-map'
        self.assertFalse(PLAN.check(self.source,self.deck)['passed'])

if __name__=='__main__':unittest.main()
