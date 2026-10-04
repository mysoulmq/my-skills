import sys,tempfile,unittest
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as E
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts'))
from check_opening_outline import check as opening_check
from check_analysis_screen import check as analysis_check
from native_text import write_text,A,P
from analysis_presentation import compile_question

def shape(ident,text,focus=()):
 s=E.Element('{'+P+'}sp');n=E.SubElement(s,'{'+P+'}nvSpPr');E.SubElement(n,'{'+P+'}cNvPr',id=str(ident))
 write_text(s,[text],focus=focus);return s

def write_deck(path,roots):
 R='http://schemas.openxmlformats.org/officeDocument/2006/relationships';Q='http://schemas.openxmlformats.org/package/2006/relationships'
 pres=E.Element('{'+P+'}presentation');ids=E.SubElement(pres,'{'+P+'}sldIdLst');rels=E.Element('{'+Q+'}Relationships')
 with ZipFile(path,'w') as z:
  for i,r in enumerate(roots,1):
   E.SubElement(ids,'{'+P+'}sldId',id=str(255+i),attrib={'{'+R+'}id':'r'+str(i)})
   E.SubElement(rels,'{'+Q+'}Relationship',Id='r'+str(i),Target=f'slides/slide{i}.xml',Type=R+'/slide')
   z.writestr(f'ppt/slides/slide{i}.xml',E.tostring(r))
  z.writestr('ppt/presentation.xml',E.tostring(pres));z.writestr('ppt/_rels/presentation.xml.rels',E.tostring(rels))

class OpeningAuditTests(unittest.TestCase):
 def test_marks_must_be_on_first_slide_and_star_must_keep_source(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'test.pptx';root=E.Element('{'+P+'}sld');root.append(shape(1,'关键知识★',['关键知识']))
   source={'units':[{'id':'s','text':'关键知识★'}]};plan={'nodes':[{'shapeId':1,'text':'关键知识★','focus':['关键知识'],'starRefs':['s']}]}
   write_deck(p,[root]);self.assertTrue(opening_check(p,source,plan)['pass'])
   blank=E.Element('{'+P+'}sld');blank.append(shape(1,'关键知识'))
   write_deck(p,[blank,root]);r=opening_check(p,source,plan)
   self.assertFalse(r['pass']);self.assertTrue(any('star lost' in s for s in r['errors']))
   write_deck(p,[root]);plan['nodes'][0]['starRefs']=['invented']
   self.assertFalse(opening_check(p,source,plan)['pass'])
 def test_red_or_yellow_is_sufficient_but_not_both(self):
  source={'units':[{'id':'s','text':'关键知识★'}]}
  plan={'nodes':[{'shapeId':1,'text':'关键知识★','focus':['关键知识'],'starRefs':['s']}]}
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'test.pptx'
   for ink,bg,expected in [('FF0000',False,True),('C00000',False,True),('000000',True,True),('000000',False,False),('FF0000',True,False),('00B0F0',False,False)]:
    root=E.Element('{'+P+'}sld');s=shape(1,'关键知识★',['关键知识'] if bg else [])
    for rp in s.iter('{'+A+'}rPr'):
     fill=rp.find('{'+A+'}solidFill')
     if fill is None:fill=E.SubElement(rp,'{'+A+'}solidFill')
     for child in list(fill):fill.remove(child)
     E.SubElement(fill,'{'+A+'}srgbClr',val=ink)
    root.append(s);write_deck(path,[root])
    self.assertEqual(opening_check(path,source,plan)['pass'],expected,(ink,bg))
 def test_multiple_analysis_pages_require_static_audit_including_group_target(self):
  item={'evidenceDisplay':'材料变化','principle':'认识变化','principleDisplay':'认识变化','displayAnchors':{'material':['材料变化'],'knowledge':['认识变化']}}
  q={'questions':[{'id':'q','analysis':[item]}]};row=compile_question(q['questions'][0])[0]
  roots=[];mapping=[]
  for i in (1,2):
   root=E.Element('{'+P+'}sld');root.extend([shape(1,row['material']),shape(2,row['knowledge'])])
   group=E.SubElement(root,'{'+P+'}grpSp');nv=E.SubElement(group,'{'+P+'}nvGrpSpPr');E.SubElement(nv,'{'+P+'}cNvPr',id='5');group.append(shape(3,'审题——'))
   roots.append(root);mapping.append({'questionId':'q','kind':'analysis','page':i,'auditShapeIds':[3],'analysisBlocks':[{'analysisIndex':1,'materialShapeId':1,'knowledgeShapeId':2}]})
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.pptx';write_deck(p,roots);self.assertTrue(analysis_check(p,q,mapping)['pass'])
   timing=E.SubElement(roots[1],'{'+P+'}timing');E.SubElement(timing,'{'+P+'}spTgt',spid='5');write_deck(p,roots)
   self.assertTrue(any('initially visible' in s for s in analysis_check(p,q,mapping)['errors']))
   roots[1].remove(timing);write_deck(p,roots);mapping[0].pop('auditShapeIds')
   self.assertFalse(analysis_check(p,q,mapping)['pass'])
