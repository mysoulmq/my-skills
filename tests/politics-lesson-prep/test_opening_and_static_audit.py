import sys,tempfile,unittest
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as E
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts'))
from check_opening_outline import check as opening_check
from check_analysis_screen import check as analysis_check
from check_recall_delivery import check as recall_check
from native_text import write_text,A,P
from analysis_presentation import compile_question
from native_recall_background import add_recall_background,check_recall_background

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

def recall_slide(*contents):
 root=E.Element('{'+P+'}sld');cs=E.SubElement(root,'{'+P+'}cSld');tree=E.SubElement(cs,'{'+P+'}spTree');boxes=[]
 for i,s in enumerate(contents):
  pr=E.SubElement(s,'{'+P+'}spPr');xf=E.SubElement(pr,'{'+A+'}xfrm')
  E.SubElement(xf,'{'+A+'}off',x='127000',y=str((10+i*30)*12700));E.SubElement(xf,'{'+A+'}ext',cx='2540000',cy='254000')
  boxes.append({'x':10,'y':10+i*30,'w':200,'h':20});tree.append(s)
 add_recall_background(root,boxes)
 return root

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
   # A knowledge-only continuation still has an audit area; the lack of
   # paired analysis blocks must not exempt it from the animation rule.
   mapping[1]['analysisBlocks']=[]
   self.assertTrue(any('initially visible' in s for s in analysis_check(p,q,mapping)['errors']))
   roots[1].remove(timing);write_deck(p,roots);mapping[0].pop('auditShapeIds')
   self.assertFalse(analysis_check(p,q,mapping)['pass'])

 def test_recall_continuations_cover_full_record_without_false_missing_nodes(self):
  record={'id':'r','route':'handout','scopeReason':'原理回看','sourceScope':'讲义','nodes':[
   {'id':key,'parentId':None,'text':word,'source':{'kind':'handout','unitId':key,'quote':word}}
   for key,word in [('a','完整第一分支'),('b','完整第二分支')]]}
  catalog={'unit:'+n['id']:n['text'] for n in record['nodes']}
  roots=[];mapping=[]
  for i,n in enumerate(record['nodes'],1):
   root=recall_slide(shape(1,n['text']));roots.append(root)
   mapping.append({'page':i,'recallId':'r','nodeShapes':{n['id']:1},'backgroundShapeId':3900})
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'recall.pptx';write_deck(p,roots)
   self.assertTrue(recall_check(p,[record],catalog,mapping)['pass'])
   result=recall_check(p,[record],catalog,mapping[:1])
   self.assertTrue(any('no actual recall delivery b' in e for e in result['errors']))
   mapping[1]['nodeShapes']={'invented':1}
   self.assertTrue(any('unknown recall nodes' in e for e in recall_check(p,[record],catalog,mapping)['errors']))

 def test_recall_heading_display_omits_ordinal_without_changing_source(self):
  record={'id':'r','route':'handout','scopeReason':'独立知识回看','sourceScope':'讲义','nodes':[
   {'id':'h','parentId':None,'text':'2、个人与社会','source':{'kind':'handout','unitId':'h','quote':'2、个人与社会'},'display':{'omitSourceNumber':True}},
   {'id':'p','parentId':'h','text':'①客观条件是前提。','source':{'kind':'handout','unitId':'p','quote':'①客观条件是前提。'},'emphasis':['客观条件']}]}
  catalog={'unit:h':'2、个人与社会','unit:p':'①客观条件是前提。'}
  mapping=[{'page':1,'recallId':'r','nodeShapes':{'h':1,'p':2},'backgroundShapeId':3900}]
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'heading.pptx';root=recall_slide(shape(1,'个人与社会'),shape(2,'①客观条件是前提。',['客观条件']))
   write_deck(p,[root]);self.assertTrue(recall_check(p,[record],catalog,mapping)['pass'])
   root=recall_slide(shape(1,'2、个人与社会'),shape(2,'①客观条件是前提。',['客观条件']));write_deck(p,[root])
   self.assertTrue(any('recall text changed h' in e for e in recall_check(p,[record],catalog,mapping)['errors']))

 def test_background_is_real_pale_shape_behind_and_around_all_nodes(self):
  root=recall_slide(shape(1,'标题'),shape(2,'原理'))
  self.assertEqual(check_recall_background(root,[1,2],3900),[])
  self.assertTrue(check_recall_background(root,[1,2],None))
  tree=root.find('.//{'+P+'}spTree');panel=tree[0]
  tree.remove(panel);tree.append(panel)
  self.assertTrue(any('behind' in e for e in check_recall_background(root,[1,2],3900)))
  tree.remove(panel);tree.insert(0,panel)
  ext=panel.find('{'+P+'}spPr/{'+A+'}xfrm/{'+A+'}ext');ext.set('cy','12700')
  self.assertTrue(any('enclose' in e for e in check_recall_background(root,[1,2],3900)))
  root=recall_slide(shape(1,'标题'));panel=root.find('.//{'+P+'}spTree')[0]
  panel.find('{'+P+'}spPr/{'+A+'}solidFill/{'+A+'}srgbClr').set('val','FFFFFF')
  self.assertTrue(any('pale' in e for e in check_recall_background(root,[1],3900)))
