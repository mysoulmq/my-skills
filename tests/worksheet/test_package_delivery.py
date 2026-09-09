import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'skills/worksheet-dual-doc/scripts'))
from package_delivery import package


class PackageTests(unittest.TestCase):
    def test_grouping_and_integrity_gates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            runs = []
            for n in range(2):
                run = root / str(n)
                dest = run / 'deliverables'
                dest.mkdir(parents=True)
                source = run / '同名原件.docx'
                source.write_bytes(b'original' + bytes([n]))
                sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
                model = {'source': str(source), 'source_sha256': sha(source), 'removed_questions': [1] if n == 0 else []}
                result = {'status': 'passed', 'errors': [], 'deliverables': {}, 'files': {}}
                for v in ('题目版', '答案版'):
                    name = v + '完整标题.doc'
                    (dest / name).write_bytes(v.encode())
                    result['deliverables'][v] = name
                    result['files'][v] = {'sha256': sha(dest / name)}
                if n == 0:
                    (dest / '记录.pdf').write_bytes(b'report')
                    result['deletion_report'] = {'filename': '记录.pdf', 'sha256': sha(dest / '记录.pdf')}
                (run / 'input.json').write_text(json.dumps(model))
                (run / 'verification.json').write_text(json.dumps(result))
                runs.append(run)
            out = package(runs, root / 'delivery.zip')
            with zipfile.ZipFile(out) as z:
                self.assertEqual(len(z.namelist()), 7)
                self.assertEqual({p.split('/')[0] for p in z.namelist()}, {'同名原件', '同名原件（2）'})
                self.assertEqual(z.read('同名原件/同名原件.docx'), b'original\x00')
                self.assertIn('同名原件/浙江选考题删除记录汇总.pdf', z.namelist())
            source.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, '发生变化'):
                package(runs, root / 'bad.zip')
            self.assertFalse((root / 'bad.zip').exists())
            result['status'] = 'failed'
            (runs[1] / 'verification.json').write_text(json.dumps(result))
            with self.assertRaisesRegex(ValueError, '验收通过'):
                package([runs[1]], root / 'failed.zip')
