import sys,unittest,tempfile
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts'))
from analysis_presentation import compile_display,paginate
from check_analysis_screen import check

class ScreenTests(unittest.TestCase):
    def item(self):return {'evidenceDisplay':'需求变化','principle':'价值选择应符合实际条件。','responseDisplay':'该方案适应当前需求。','responseAnchor':'适应当前需求'}
    def test_private_reason_does_not_count(self):
        a=self.item();a.pop('responseDisplay');a['reason']='该方案适应当前需求。'
        with self.assertRaises(ValueError):compile_display(a)
    def test_proposition_not_replaced_by_label(self):
        a=self.item();a['principleDisplay']='条件';self.assertEqual(compile_display(a)['knowledge'],a['principle'])
    def test_link_can_already_be_in_material(self):
        a=self.item();a['evidenceDisplay']+='，该方案适应当前需求。';a.pop('responseDisplay');self.assertIn(a['responseAnchor'],compile_display(a)['material'])
    def test_three_groups_fit_without_mechanical_split(self):
        g=[{'index':i,'bodyHeight':40,'knowledgeHeight':30} for i in range(3)]
        self.assertEqual(paginate(g,150,120,5),[[0,1,2]])
        self.assertEqual(paginate(g,90,120,5),[[0,1],[2]])
    def test_overflow_not_silently_shrunk(self):
        with self.assertRaises(ValueError):paginate([{'index':1,'bodyHeight':151,'knowledgeHeight':30}],150,120)
    def test_actual_screen_not_notes_or_answer(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'sample.pptx';a=self.item();compiled=compile_display(a)
            def write(material):
                with ZipFile(f,'w') as z:
                    z.writestr('ppt/presentation.xml','<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId id="256" r:id="r1"/></p:sldIdLst></p:presentation>')
                    z.writestr('ppt/_rels/presentation.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="slides/slide9.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"/></Relationships>')
                    z.writestr('ppt/slides/slide9.xml',f'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:sp><p:nvSpPr><p:cNvPr id="1"/></p:nvSpPr><a:t>{material}</a:t></p:sp><p:sp><p:nvSpPr><p:cNvPr id="2"/></p:nvSpPr><a:t>{compiled["knowledge"]}</a:t></p:sp></p:sld>')
            q={'questions':[{'id':'q','analysis':[a]}]};m=[{'questionId':'q','page':1,'kind':'analysis','analysisBlocks':[{'analysisIndex':1,'materialShapeId':1,'knowledgeShapeId':2}]}]
            write(compiled['material']);self.assertTrue(check(f,q,m)['pass'])
            write('需求变化');self.assertFalse(check(f,q,m)['pass'])
            write(compiled['material']);m[0]['kind']='answer';self.assertFalse(check(f,q,m)['pass'])
