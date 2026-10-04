import sys, unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts'))
from knowledge_recall import compile_recall,emphasis_spans,compile_analysis_emphasis,compile_answer_sections
class RecallTests(unittest.TestCase):
 def data(self):
  return {'route':'handout','scopeReason':'具体原理','sourceScope':'核定讲义段落','nodes':[
   {'id':'p','parentId':None,'text':'上位标题','source':{'kind':'handout','unitId':'p','quote':'上位标题'}},
   {'id':'c','parentId':'p','text':'具体原理及限定。','source':{'kind':'handout','unitId':'c','quote':'具体原理及限定。'},'emphasis':['限定']}]}
 def catalog(self):return {'unit:p':'上位标题','unit:c':'具体原理及限定。'}
 def test_hierarchy_and_exact_source(self):
  out=compile_recall(self.data(),self.catalog());self.assertEqual([x['depth'] for x in out],[0,1])
 def test_answer_concatenation_cannot_pass(self):
  d=self.data();d['nodes'][1]['text']='具体原理。'
  with self.assertRaises(ValueError):compile_recall(d,self.catalog())
 def test_fabricated_quote_cannot_validate_itself(self):
  d=self.data();d['nodes'][1]['source']['quote']='新原理';d['nodes'][1]['text']='新原理'
  with self.assertRaises(ValueError):compile_recall(d,self.catalog())
 def test_parent_and_source_route_required(self):
  for mutation in ('parent','route'):
   d=self.data()
   if mutation=='parent':d['nodes'].reverse()
   else:d['route']='outline-overview'
   with self.assertRaises(ValueError):compile_recall(d,self.catalog())
 def test_wrap_changes_only_whitespace(self):
  d=self.data();d['nodes'][1]['text']='具体原理\n及限定。'
  self.assertEqual(compile_recall(d,self.catalog())[1]['text'],'具体原理及限定。')
 def test_standalone_heading_ordinal_is_display_only(self):
  d=self.data();d['nodes'][0].update(text='2、上位标题',source={'kind':'handout','unitId':'p','quote':'2、上位标题'},display={'omitSourceNumber':True})
  catalog={**self.catalog(),'unit:p':'2、上位标题'}
  out=compile_recall(d,catalog)
  self.assertEqual(out[0]['text'],'上位标题')
  self.assertEqual(out[0]['sourceText'],'2、上位标题')
  self.assertEqual(out[0]['source']['quote'],'2、上位标题')
  self.assertEqual(d['nodes'][0]['text'],'2、上位标题')
  d['nodes'][1]['display']={'omitSourceNumber':True}
  with self.assertRaisesRegex(ValueError,'standalone'):compile_recall(d,catalog)
 def test_heading_display_cannot_delete_content_or_internal_numbers(self):
  for text in ['①内部论点','2026年发展','5G网络','3.5倍增长','第二课知识','普通标题']:
   d=self.data();d['nodes'][0].update(text=text,source={'kind':'handout','unitId':'p','quote':text},display={'omitSourceNumber':True})
   with self.assertRaisesRegex(ValueError,'No removable'):compile_recall(d,{**self.catalog(),'unit:p':text})
  d=self.data();d['nodes'][0]['display']={'replacementText':'自改标题'}
  with self.assertRaisesRegex(ValueError,'Unknown recall'):compile_recall(d,self.catalog())
 def test_spans_preserve_text_and_overlapping_marks(self):
  spans=emphasis_spans('甲乙丙丁',['甲乙'],['乙丙'])
  self.assertEqual(''.join(x['text'] for x in spans),'甲乙丙丁')
  self.assertTrue(next(x for x in spans if x['text']=='乙')['bold'])
  self.assertTrue(next(x for x in spans if x['text']=='乙')['highlight'])
 def test_missing_highlight_decision_does_not_pass_as_no_highlight(self):
  item={'evidenceDisplay':'材料','principleDisplay':'原理','visualReviewReason':'保留材料主体'}
  with self.assertRaises(ValueError):compile_analysis_emphasis(item)
  item.update(evidenceFocus=[],principleFocus=[])
  self.assertIn('material',compile_analysis_emphasis(item))

 def test_answer_no_yellow_without_sample_basis(self):
  answer={'principle':'具体原理','application':'建设某个项目。','applicationFocus':['建设某个项目']}
  with self.assertRaises(ValueError):compile_answer_sections(answer)
  answer['applicationFocus']=[]
  sections=compile_answer_sections(answer)
  self.assertEqual(sections[1]['focus'],[]);self.assertEqual(sections[1]['emphasis'],[])
  answer.update(applicationEmphasis=['建设'],emphasisReason='对照教师示范突出动作')
  self.assertEqual(compile_answer_sections(answer)[1]['focus'],[])

 def test_recall_fit_preserves_nodes_at_readable_floor(self):
  from native_recall_layout import fit_recall
  nodes=compile_recall(self.data(),self.catalog())
  result=fit_recall(nodes,'handout',0,0,200,lambda t,sz,b:len(t)*sz,100)
  self.assertTrue(result['fits']);self.assertEqual(len(result['boxes']),2)
  constrained=fit_recall(nodes,'handout',0,0,200,lambda t,sz,b:len(t)*sz,1)
  self.assertFalse(constrained['fits']);self.assertEqual(constrained['profile']['fontPt'],12)
  self.assertEqual([n['text'] for n in constrained['boxes']],[n['text'] for n in nodes])
  self.assertTrue(all(b['lineSpacing']==1.10 for b in constrained['boxes']))

 def test_material_column_ignores_legacy_highlight(self):
  item={'evidenceDisplay':'针对现实问题采取行动','principleDisplay':'具体知识','evidenceFocus':['现实问题'],'principleFocus':[],'visualReviewReason':'材料列不加黄底'}
  result=compile_analysis_emphasis(item)
  self.assertEqual(''.join(x['text'] for x in result['material']),item['evidenceDisplay'])
  self.assertTrue(all(not x['highlight'] for x in result['material']))

 def test_answer_score_cannot_be_silently_dropped(self):
  for key in ('principleScore','applicationScore','score','scoreLabel'):
   with self.assertRaisesRegex(ValueError,'score-aware'):
    compile_answer_sections({'principle':'原理','application':'材料',key:1})
