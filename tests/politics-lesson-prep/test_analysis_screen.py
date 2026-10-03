import sys,unittest,tempfile
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts'))
from analysis_presentation import compile_display,paginate
from check_analysis_screen import check

class ScreenTests(unittest.TestCase):
    def item(self):
        return {'evidenceDisplay':'治理理念从末端处置转向源头预防',
                'principle':'实践的发展推动认识的发展，并提供认识工具。',
                'principleDisplay':'实践的发展推动认识的发展。',
                'displayAnchors':{'material':['末端处置','转向源头预防'],
                                  'knowledge':['实践的发展推动认识的发展']}}
    def test_reviewed_short_proposition_is_preserved(self):
        a=self.item();self.assertEqual(compile_display(a)['knowledge'],a['principleDisplay'])
        self.assertEqual(compile_display(a)['material'],a['evidenceDisplay'])
    def test_source_is_default_without_display_override(self):
        a=self.item();a.pop('principleDisplay')
        self.assertEqual(compile_display(a)['knowledge'],a['principle'])
    def test_legacy_answer_append_requires_content_migration(self):
        for field in ('responseDisplay','responseAnchor'):
            a=self.item();a[field]='我们应该遵循规律。'
            with self.assertRaisesRegex(ValueError,'Legacy'):compile_display(a)
    def test_private_reason_cannot_restore_lost_focus(self):
        a=self.item();a['reason']=a['evidenceDisplay'];a['evidenceDisplay']='购置设备，改进治理'
        with self.assertRaisesRegex(ValueError,'material expression'):compile_display(a)
    def test_lost_before_or_after_is_detected(self):
        for display in ('理念转向源头预防','原来采用末端处置'):
            a=self.item();a['evidenceDisplay']=display
            with self.assertRaisesRegex(ValueError,'material expression'):compile_display(a)
    def test_label_cannot_replace_reviewed_relation(self):
        a=self.item();a['principleDisplay']='实践'
        with self.assertRaisesRegex(ValueError,'knowledge expression'):compile_display(a)
    def test_missing_anchors_return_to_content_review(self):
        for anchors in (None,{}, {'material':[],'knowledge':['实践']}, {'material':'末端处置','knowledge':['实践']}):
            a=self.item();a['displayAnchors']=anchors
            with self.assertRaises(ValueError):compile_display(a)
    def test_three_groups_fit_without_mechanical_split(self):
        g=[{'index':i,'bodyHeight':40,'knowledgeHeight':30} for i in range(3)]
        self.assertEqual(paginate(g,150,150,5),[[0,1,2]])
        self.assertEqual(paginate(g,90,120,5),[[0,1],[2]])
    def test_asymmetric_pairs_use_shared_row_height(self):
        g=[{'index':0,'bodyHeight':70,'knowledgeHeight':20},
           {'index':1,'bodyHeight':20,'knowledgeHeight':70}]
        self.assertEqual(paginate(g,100,100,5),[[0],[1]])
    def test_overflow_not_silently_shrunk(self):
        with self.assertRaises(ValueError):paginate([{'index':1,'bodyHeight':151,'knowledgeHeight':30}],150,120)
    def test_nonfinite_gap_rejected(self):
        with self.assertRaises(ValueError):paginate([{'index':1,'bodyHeight':20,'knowledgeHeight':30}],150,120,float('nan'))
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
