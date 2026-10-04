import sys,unittest,tempfile,json
from pathlib import Path
from xml.etree import ElementTree as E
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts'))
from native_text import write_text,write_role_paragraphs,normalize_native_dashes,A,P
from native_line_breaks import wrap_native_text,line_errors
from check_recall_delivery import styled_text,check
class NativeTextTests(unittest.TestCase):
 def shape(self):
  s=E.Element('{'+P+'}sp');n=E.SubElement(s,'{'+P+'}nvSpPr');E.SubElement(n,'{'+P+'}cNvPr',id='1');return s
 def test_role_boundary_and_no_default_yellow(self):
  s=self.shape();parts=[{'text':'原理来自社会实践。','bold':True},{'text':'材料中运用5G与AI改善生产。','color':'00B0F0'}]
  out=write_role_paragraphs(s,parts,12,lambda t,sz,b:len(t)*(1.1 if b else 1),size=10)
  self.assertEqual(''.join(out['sectionLines'][0]),parts[0]['text'])
  self.assertEqual(''.join(out['sectionLines'][1]),parts[1]['text'])
  self.assertTrue(any('5G' in line for line in out['sectionLines'][1]))
  self.assertEqual(list(s.iter('{'+A+'}highlight')),[])
  self.assertEqual(styled_text(s)[0],''.join(p['text'] for p in parts))
 def test_bold_is_measured_and_color_retained(self):
  s=self.shape();out=write_role_paragraphs(s,[{'text':'甲乙丙丁','color':'00B0F0','emphasis':['乙丙']}],5,lambda t,sz,b:len(t)*(2 if b else 1),safety=0)
  self.assertEqual(out['sectionLines'],[['甲乙丙','丁']]);self.assertIn('乙丙',styled_text(s)[2])
  self.assertTrue(all(r.find('{'+A+'}rPr/{'+A+'}solidFill/{'+A+'}srgbClr').get('val')=='00B0F0' for r in s.iter('{'+A+'}r')))
 def test_global_double_dash_across_runs(self):
  s=self.shape();write_text(s,['含义——具体内容'],focus=['含义—'])
  self.assertEqual(styled_text(s)[0],'含义——具体内容')
  dashruns=[r for r in s.iter('{'+A+'}r') if '—' in r.find('{'+A+'}t').text]
  self.assertEqual(''.join(r.find('{'+A+'}t').text for r in dashruns),'——')
  for r in dashruns:
   rp=r.find('{'+A+'}rPr');self.assertEqual(rp.get('spc'),'0');self.assertEqual(rp.find('{'+A+'}ea').get('typeface'),'Arial')
 def test_alphanumeric_and_closing_punctuation(self):
  lines=wrap_native_text('技术采用5G、AI及12项措施。',7,len)
  self.assertTrue(any('5G' in s for s in lines));self.assertTrue(any('12项' in s for s in lines));self.assertFalse(line_errors(lines))
 def test_actual_file_checks_role_boundary_and_no_yellow(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'a.pptx';s=self.shape();write_text(s,['原理。材料。'],focus=['材料'])
   root=E.Element('{'+P+'}sld');root.append(s)
   with ZipFile(path,'w') as z:
    z.writestr('ppt/presentation.xml','<p:presentation xmlns:p="'+P+'" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId id="256" r:id="r1"/></p:sldIdLst></p:presentation>')
    z.writestr('ppt/_rels/presentation.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="slides/s.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"/></Relationships>')
    z.writestr('ppt/slides/s.xml',E.tostring(root))
   report=check(path,[],{},[{'page':1,'emphasisShapes':[{'shapeId':1,'noHighlight':True,'sectionTexts':['原理。','材料。']}]}])
   self.assertFalse(report['pass']);self.assertEqual(len(report['errors']),2)
