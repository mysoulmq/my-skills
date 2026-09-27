import json,sys,subprocess,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
SKILL=Path(__file__).resolve().parents[2]/'skills/worksheet-dual-doc'
sys.path.insert(0,str(SKILL/'scripts'))
from configuration import resolve,check_resolution,require_names
from generate import title_for

class ConfirmedDefaultsTests(unittest.TestCase):
 def test_fresh_process_uses_confirmed_names(self):
  with tempfile.TemporaryDirectory() as cwd:
   p=subprocess.run([sys.executable,str(SKILL/'scripts/worksheet.py'),'config'],cwd=cwd,capture_output=True,text=True,check=True)
  cfg=json.loads(p.stdout)
  self.assertEqual((cfg['compiler'],cfg['proofreader']),('罗典','朴台子'))
 def test_explicit_override_is_temporary_and_verified(self):
  before=(SKILL/'assets/defaults.json').read_bytes()
  cfg,origin=resolve({'compiler':'测试编制'})
  self.assertEqual(cfg['proofreader'],'朴台子')
  self.assertEqual(check_resolution({'config':cfg,'config_resolution':origin}),[])
  self.assertEqual(before,(SKILL/'assets/defaults.json').read_bytes())
 def test_manifest_cannot_silently_replace_defaults(self):
  cfg,origin=resolve();cfg['compiler']='张老师'
  self.assertTrue(check_resolution({'config':cfg,'config_resolution':origin}))
 def test_missing_names_stop_conversion(self):
  cfg,_=resolve({'compiler':''})
  with self.assertRaises(ValueError):require_names(cfg)
 def test_lesson28_and_unknown_topic(self):
  self.assertEqual(title_for('高效作业28 发展中国特色社会主义文化(见学生用书P55)',{}),'第9课  发展中国特色社会主义文化')
  with self.assertRaises(ValueError):title_for('高效作业99 未知主题',{})
  self.assertEqual(title_for('高效作业99 未知主题',{'title':'第2课 自定主题'}),'第2课 自定主题')
if __name__=='__main__':unittest.main()
