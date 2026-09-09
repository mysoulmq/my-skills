"""Exercise first-run font preparation without changing the real user font folder."""
import unittest,tempfile,sys
from pathlib import Path
from unittest.mock import patch
SKILL=Path(__file__).resolve().parents[2]/'skills/worksheet-dual-doc'
sys.path.insert(0,str(SKILL/'scripts'))
from fonts import font_record,resolve_fonts

class NativeFontTests(unittest.TestCase):
 def test_register_private_font_without_overwriting(self):
  source=Path(resolve_fonts()['font_file'])
  with tempfile.TemporaryDirectory() as td:
   home=Path(td)
   with patch('fonts.Path.home',return_value=home),patch('fonts.native_families',side_effect=[set(),{'SimSun'}]):
    result=font_record(source)
   target=Path(result['native_font_file']);self.assertEqual(target.read_bytes(),source.read_bytes());self.assertTrue(result['native_registered'])
   with patch('fonts.Path.home',return_value=home),patch('fonts.native_families',return_value={'SimSun'}):
    again=font_record(source)
   self.assertTrue(again['native_registered']);self.assertEqual(len(list((home/'Library/Fonts').iterdir())),1)
   target.write_bytes(b'unrelated font')
   with patch('fonts.Path.home',return_value=home),patch('fonts.native_families',return_value=set()):
    with self.assertRaisesRegex(RuntimeError,'未覆盖'):font_record(source)
   self.assertEqual(target.read_bytes(),b'unrelated font')

if __name__=='__main__':unittest.main()
