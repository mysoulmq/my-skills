import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts'))
from read_teacher_examples import read_bank,FIELDS

class TeacherExamplesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.workspace=Path(self.temp.name);self.base=self.workspace/'.politics-lesson-prep';self.base.mkdir()
        self.deck=self.base/'example.pptx'
        with ZipFile(self.deck,'w') as z:
            z.writestr('ppt/presentation.xml','<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId id="256" r:id="r1"/></p:sldIdLst></p:presentation>')
            z.writestr('ppt/_rels/presentation.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="slides/slide7.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"/></Relationships>')
            z.writestr('ppt/slides/slide7.xml','<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:sp><p:nvSpPr><p:cNvPr id="9"/></p:nvSpPr><a:t>合成来源原句</a:t></p:sp></p:sld>')
        example={'id':'e1','title':'合成例','taskFeatures':['对应']}
        example.update({key:{'text':'合成来源原句','source':{'deck':'d','page':1,'shapeId':'9'}} for key in FIELDS})
        self.bank={'sources':{'d':{'file':'example.pptx','sha256':hashlib.sha256(self.deck.read_bytes()).hexdigest()}},'examples':[example]}
        self.save()
    def save(self):
        (self.base/'teacher-examples.json').write_text(json.dumps(self.bank,ensure_ascii=False))
    def test_index_does_not_pretend_to_read_full_examples(self):
        self.assertNotIn('teacherAnswer',read_bank(self.workspace)['examples'][0])
    def test_full_original_transformation_loaded(self):
        self.assertEqual(read_bank(self.workspace,['e1'])['examples'][0]['teacherMaterialColumn']['text'],'合成来源原句')
    def test_task_routing_and_verified_input_output(self):
        e=self.bank['examples'][0];e['uses']=['outline']
        e['excerpts']=[{'role':role,**e['material']} for role in ('input','output')];self.save()
        self.assertEqual(read_bank(self.workspace,task='outline')['examples'][0]['id'],'e1')
        self.assertEqual(read_bank(self.workspace,task='choice-explanation')['examples'],[])
        self.assertEqual(len(read_bank(self.workspace,['e1'],'outline')['examples']),1)
        with self.assertRaises(ValueError):read_bank(self.workspace,['e1'],'essay-analysis')
    def test_output_only_is_not_a_transformation(self):
        e=self.bank['examples'][0];e['excerpts']=[{'role':'output',**e['material']}];self.save()
        with self.assertRaises(ValueError):read_bank(self.workspace,['e1'])
    def test_unknown_selection_rejected(self):
        with self.assertRaises(ValueError):read_bank(self.workspace,['not-existing'])
    def test_model_text_cannot_masquerade_as_teacher_quote(self):
        self.bank['examples'][0]['teacherKnowledgeColumn']['text']='模型自行改写';self.save()
        with self.assertRaisesRegex(ValueError,'not found'):read_bank(self.workspace,['e1'])
    def test_wrong_shape_rejected(self):
        self.bank['examples'][0]['teacherAnswer']['source']['shapeId']='22';self.save()
        with self.assertRaises(ValueError):read_bank(self.workspace,['e1'])
    def test_source_revision_requires_revalidation(self):
        self.deck.write_bytes(self.deck.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'hash changed'):read_bank(self.workspace,['e1'])

if __name__=='__main__':unittest.main()
