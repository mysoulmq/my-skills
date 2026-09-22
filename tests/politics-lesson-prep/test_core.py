import importlib.util
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts'
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
extract=module('extract_docx');views=module('pptx_views');checks=module('check_teaching')


class CoreTests(unittest.TestCase):
    def test_docx_order_and_table(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'source.docx'
            with ZipFile(f,'w') as z:z.writestr('word/document.xml',f'<w:document xmlns:w="{extract.W[1:-1]}"><w:body><w:p><w:r><w:t>前</w:t><w:br/><w:t>续</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>表格</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:p><w:r><w:t>后</w:t></w:r></w:p></w:body></w:document>')
            result=extract.extract(f)['blocks']
            self.assertEqual([b['kind'] for b in result],['paragraph','table','paragraph'])
            self.assertEqual(result[0]['text'],'前\n续');self.assertEqual(result[1]['rows'],[['表格']])

    def test_relationship_resolution(self):
        self.assertEqual(views.resolve('ppt/slides/slide1.xml','../media/image1.png'),'ppt/media/image1.png')
        self.assertEqual(views.resolve('ppt/slides/slide1.xml','/ppt/media/image1.png'),'ppt/media/image1.png')

    def test_actual_order_and_animation_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'in.pptx';out=Path(d)/'out.pptx'
            pres=f'<p:presentation xmlns:p="{views.P}" xmlns:r="{views.R}"><p:sldIdLst><p:sldId id="256" r:id="b"/><p:sldId id="257" r:id="a"/></p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/></p:presentation>'
            rel=f'<Relationships xmlns="{views.PKG}"><Relationship Id="a" Target="slides/slide1.xml" Type="{views.R}/slide"/><Relationship Id="b" Target="slides/slide2.xml" Type="{views.R}/slide"/></Relationships>'
            ct=f'<Types xmlns="{views.CT}"><Default Extension="xml" ContentType="application/xml"/><Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/><Override PartName="/ppt/slides/slide2.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/></Types>'
            s1=f'<p:sld xmlns:p="{views.P}"><p:cSld name="one"/><p:timing/></p:sld>'.encode()
            s2=f'<p:sld xmlns:p="{views.P}"><p:cSld name="two"/></p:sld>'.encode()
            with ZipFile(f,'w') as z:
                for n,b in {'ppt/presentation.xml':pres,'ppt/_rels/presentation.xml.rels':rel,'[Content_Types].xml':ct,'ppt/slides/slide1.xml':s1,'ppt/slides/slide2.xml':s2}.items():z.writestr(n,b)
            mapping=views.compose({'decks':{'k':str(f)},'slides':[{'id':'chosen','deck':'k','sourceSlide':2}]},out)
            with ZipFile(out) as z:self.assertEqual(z.read('ppt/slides/slide1.xml'),s1)
            self.assertEqual(mapping[0]['page'],1)
            with self.assertRaises(ValueError):views.compose({'decks':{'k':str(f)},'slides':[{'id':'a','deck':'k','sourceSlide':2}]},out)

    def test_bad_evidence_is_rejected(self):
        q={'questions':[{'id':'q','material':'原材料','analysis':[{'evidence':'编造材料','principle':'原理','reason':'关系'}]}]}
        result=checks.check(q,{'periods':[]})
        self.assertFalse(result['pass']);self.assertTrue(any('quote' in e for e in result['errors']))

    def test_known_question_score_requires_source_and_matches_prompt(self):
        q={'questions':[{'id':'q','prompt':'说明理由。（6分）','totalScore':8,
             'material':'资料','analysis':[],'answer':[]}]}
        result=checks.check(q,{'periods':[]})
        self.assertTrue(any('missing source' in e for e in result['errors']))
        self.assertTrue(any('conflicting total score' in e for e in result['errors']))
        q['questions'][0].update(totalScore=6,totalScoreSource='supplied reference')
        result=checks.check(q,{'periods':[]})
        self.assertFalse(any('totalScore' in e or 'total score' in e for e in result['errors']))

    def test_resource_and_notes_relationship_graph(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'in.pptx';out=Path(d)/'out.pptx'
            def relations(entries):
                r=ET.Element('{'+views.PKG+'}Relationships')
                for i,(target,kind) in enumerate(entries):ET.SubElement(r,'{'+views.PKG+'}Relationship',Id=f'rId{i+1}',Type=views.R+'/'+kind,Target=target)
                return views.xml(r)
            pres=f'<p:presentation xmlns:p="{views.P}" xmlns:r="{views.R}"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/></p:presentation>'
            ct=f'<Types xmlns="{views.CT}"><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/></Types>'
            files={'ppt/presentation.xml':pres,'ppt/_rels/presentation.xml.rels':relations([('slides/slide1.xml','slide')]),'[Content_Types].xml':ct,'ppt/slides/slide1.xml':f'<p:sld xmlns:p="{views.P}"><p:timing/></p:sld>','ppt/slides/_rels/slide1.xml.rels':relations([('../media/image1.png','image'),('../notesSlides/notesSlide1.xml','notesSlide')]),'ppt/media/image1.png':b'unchanged-image-bytes','ppt/notesSlides/notesSlide1.xml':f'<p:notes xmlns:p="{views.P}"/>','ppt/notesSlides/_rels/notesSlide1.xml.rels':relations([('../slides/slide1.xml','slide')])}
            with ZipFile(f,'w') as z:
                for n,b in files.items():z.writestr(n,b)
            views.compose({'decks':{'k':str(f)},'slides':[{'id':'k','deck':'k','sourceSlide':1}]},out)
            with ZipFile(out) as z:
                slide='ppt/slides/slide1.xml';rels=ET.fromstring(z.read(views.relpath(slide)))
                targets=[views.resolve(slide,r.get('Target')) for r in rels]
                self.assertEqual(z.read(targets[0]),b'unchanged-image-bytes')
                back=ET.fromstring(z.read(views.relpath(targets[1])))[0]
                self.assertEqual(views.resolve(targets[1],back.get('Target')),slide)


class ClickTests(unittest.TestCase):
    def test_actual_click_group_text(self):
        a='http://schemas.openxmlformats.org/drawingml/2006/main'
        x=f'''<p:sld xmlns:p="{views.P}" xmlns:a="{a}"><p:cSld><p:spTree>
        <p:sp><p:nvSpPr><p:cNvPr id="2"/></p:nvSpPr><a:t>证据</a:t></p:sp>
        <p:sp><p:nvSpPr><p:cNvPr id="3"/></p:nvSpPr><a:t>原理</a:t></p:sp>
        </p:spTree></p:cSld><p:timing><p:cTn nodeType="clickEffect"><p:spTgt spid="2"/></p:cTn>
        <p:cTn nodeType="withEffect"><p:spTgt spid="3"/></p:cTn></p:timing></p:sld>'''
        self.assertEqual(views.click_texts(x),[['证据','原理']])


if __name__=='__main__':unittest.main()
