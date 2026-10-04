import json,sys,tempfile,unittest
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts'))
from check_choice_reveals import check,_timing,P,A

class ChoiceRevealsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.deck=Path(self.temp.name)/'choice.pptx'
        self.q={'id':'q1','answer':'B','options':[{'key':k,'text':'原选项'+k,'verdict':'false' if i==0 else 'supported'} for i,k in enumerate('ABCD')]}
    def write(self,mode='valid'):
        root=ET.Element(P+'sld');spTree=ET.SubElement(root,P+'spTree')
        rows=[('q1-choice-1-answer','答案 B'),('q1-choice-1-annotation-0','概念混用')]+[(f'q1-choice-1-option-{i}',o['key']+' '+o['text']) for i,o in enumerate(self.q['options'])]
        for i,(name,text) in enumerate(rows,1):
            sp=ET.SubElement(spTree,P+'sp');nv=ET.SubElement(sp,P+'nvSpPr');ET.SubElement(nv,P+'cNvPr',id=str(i),name=name)
            if mode=='leak' and name.endswith('option-0'):text+=' 概念混用'
            ET.SubElement(sp,A+'t').text=text
        steps=[[{'id':'1','type':'sp'}],[{'id':'2','type':'sp'}]]
        timing=ET.fromstring(_timing(steps))
        if mode=='automatic':
            for c in timing.iter(P+'cond'):
                if c.get('delay')=='indefinite':c.set('delay','0')
        if mode!='missing':root.append(timing)
        with ZipFile(self.deck,'w') as z:
            z.writestr('ppt/presentation.xml','<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId id="256" r:id="r1"/></p:sldIdLst></p:presentation>')
            z.writestr('ppt/_rels/presentation.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="slides/slide7.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"/></Relationships>')
            z.writestr('ppt/slides/slide7.xml',ET.tostring(root))
    def test_click_template_passes(self):
        self.write();self.assertTrue(check(self.deck,{'questions':[self.q]})['pass'])
    def test_unanimated_candidate_rejected(self):
        self.write('missing');self.assertFalse(check(self.deck)['pass'])
    def test_automatic_entrance_rejected(self):
        self.write('automatic');self.assertFalse(check(self.deck)['pass'])
    def test_explanation_in_visible_option_rejected(self):
        self.write('leak');self.assertFalse(check(self.deck,{'questions':[self.q]})['pass'])
    def test_missing_choice_rejected(self):
        self.write();q={**self.q,'id':'q2'}
        self.assertFalse(check(self.deck,{'questions':[self.q,q]})['pass'])
if __name__=='__main__':unittest.main()
