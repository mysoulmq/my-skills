import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree as E
from zipfile import ZipFile,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'skills/lesson-image-ppt/scripts'))
from template_contract import read,patch,A,P
ASSET=ROOT/'skills/lesson-image-ppt/assets/teaching-template.pptx'
class TemplateContractTests(unittest.TestCase):
    def test_native_spacing_and_roles(self):
        data=read(ASSET)
        self.assertEqual(data['roles']['lesson.body.2.1']['lineSpacing'],1.3)
        self.assertEqual(data['roles']['question.material.2']['font'],'KaiTi')
        self.assertEqual(data['roles']['question.theory.2.1']['lineSpacing'],1.3)
    def test_template_edit_changes_runtime_preset(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy=Path(tmp)/'template.pptx';shutil.copy2(ASSET,copy)
            patch(copy,{'lesson.body.2.1':1.4})
            with ZipFile(copy) as z:files={n:z.read(n) for n in z.namelist()}
            r=E.fromstring(files['ppt/slides/slide1.xml'])
            for sp in r.iter(P+'sp'):
                if sp.find('.//'+P+'cNvPr').get('name')=='lesson.body.2.2':
                    off=sp.find(P+'spPr/'+A+'xfrm/'+A+'off');off.set('y',str(int(off.get('y'))+10*9525))
            files['ppt/slides/slide1.xml']=E.tostring(r)
            with ZipFile(copy,'w',ZIP_DEFLATED) as z:
                for n,d in files.items():z.writestr(n,d)
            self.assertEqual(read(copy)['roles']['lesson.body.2.1']['lineSpacing'],1.4)
            env={**os.environ,'LESSON_TEMPLATE_PPTX':str(copy)}
            module=(ROOT/'skills/lesson-image-ppt/scripts/template_contract.mjs').as_uri()
            result=subprocess.check_output([os.environ.get('LESSON_NODE','node'),'--input-type=module','-e',f"import {{role,gap}} from '{module}';console.log(JSON.stringify([role('lesson.body.2.1').lineSpacing,gap('lesson.body.2.1','lesson.body.2.2')]));"],env=env,text=True)
            self.assertEqual(json.loads(result),[1.4,54])
