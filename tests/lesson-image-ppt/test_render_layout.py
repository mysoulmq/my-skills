"""Integration checks for generated native diagrams; requires the lesson runtime env."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
READY = all(os.environ.get(k) for k in ('LESSON_NODE', 'LESSON_NODE_MODULES', 'LESSON_FONT_FILES'))
NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}

@unittest.skipUnless(READY, 'Set LESSON_NODE, LESSON_NODE_MODULES, LESSON_FONT_FILES for render integration')
class RenderLayoutTests(unittest.TestCase):
    def fixture(self, oversized=False):
        units = [{'id': 'lesson', 'kind': 'heading', 'text': '课程结构'}]
        groups, body, knowledge = [], [], []
        index = 0
        for frame, counts in enumerate(([2, 4], [2, 2, 3]), 1):
            fid = f'f{frame}'
            units.append({'id': fid, 'kind': 'heading', 'text': f'第{frame}组 概念关系'})
            topics = []
            for topic, count in enumerate(counts, 1):
                tid = f'{fid}t{topic}'
                units.append({'id': tid, 'kind': 'heading', 'text': f'第{topic}目 判断条件'})
                leaves, items = [], []
                for _ in range(count):
                    index += 1
                    uid, label = f'p{index}', f'知识{index}'
                    clue = ('分析对象的性质与条件；保留判断的适用范围；区分概念之间的联系'
                            if index % 2 else '观察对象；辨认条件；区分概念联系')
                    if oversized and index == 1:
                        clue *= 100
                    units.append({'id': uid, 'text': label + '：' + clue})
                    leaves.append({'label': {'ref': uid, 'quote': label},
                                   'segments': [{'ref': uid, 'quote': clue}]})
                    items.append(uid)
                knowledge.append({'id':tid,'heading':tid,'members':list(items)})
                topics.append({'title': tid, 'leaves': leaves})
                body.append({'type': 'content', 'page': '1', 'frame': fid, 'title': tid,
                             'blocks': [{'type': 'paragraphs', 'size': 26, 'items': items}]})
            groups.append({'title': fid, 'topics': topics})
        units[3]['text'] = '①' + units[3]['text']
        return {'units': units, 'knowledgeGroups':knowledge, 'displayOmissions': [{'id': units[3]['id'], 'prefix': '①',
                'reason': '孤立编号', 'authorization': '测试用户明确要求'}]}, {'lesson': 'lesson', 'slides': [
            {'type': 'knowledge-map', 'page': '1', 'groups': groups, 'mapLayout': {'frameWidth': 250, 'topicWidth': 210}}] + body}

    def run_render(self, directory, oversized=False, invalid_plan=False, map_layout=None):
        source, deck = self.fixture(oversized)
        if map_layout:
            deck["slides"][0]["mapLayout"].update(map_layout)
        if invalid_plan:
            source.pop("knowledgeGroups")
        p = Path(directory)
        for name, data in [('source', source), ('deck', deck)]:
            (p / f'{name}.json').write_text(json.dumps(data, ensure_ascii=False))
        result = subprocess.run([os.environ['LESSON_NODE'], str(ROOT / 'skills/lesson-image-ppt/scripts/render.mjs'),
                                 str(p/'source.json'), str(p/'deck.json'), str(p/'run')],
                                capture_output=True, text=True, timeout=120)
        return p/'run', result

    def test_whole_lesson_map_has_all_nodes_and_no_page_counter(self):
        with tempfile.TemporaryDirectory() as temp:
            out, result = self.run_render(temp)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((out/'layout-review.json').read_text())[0]
            self.assertEqual((report['groups'], report['topics'], report['leaves']), (2, 5, 13))
            self.assertLessEqual(report['total'], report['available'])
            self.assertGreaterEqual(report['size'], 21)
            self.assertEqual(report['leafWidth'], 554)
            self.assertEqual(report['leafX'], 696)
            with ZipFile(out/'candidate.pptx') as z:
                native_spacings = [int(e.get('val')) for n in z.namelist()
                                   if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)
                                   for e in ET.fromstring(z.read(n)).findall('.//a:lnSpc/a:spcPts', NS)]
                self.assertIn(2535, native_spacings, 'Measured body spacing must reach native PPTX')
                first = ET.fromstring(z.read('ppt/slides/slide1.xml'))
                names = [e.get('name', '') for e in first.findall('.//p:cNvPr', NS)]
                self.assertEqual(sum(n.startswith('map-leaf-') for n in names), 13)
                self.assertGreater(len(first.findall('.//p:sp', NS)), 20)
                self.assertFalse(first.findall('.//p:pic', NS), 'Diagram must be native objects')
                braces = [shape for shape in first.findall('.//p:sp', NS)
                          if shape.find('p:nvSpPr/p:cNvPr', NS).get('name', '').startswith('map-brace-')]
                self.assertTrue(braces)
                for shape in braces:
                    color = shape.find('p:spPr/a:ln/a:solidFill/a:srgbClr', NS)
                    self.assertIsNotNone(color)
                    name = shape.find('p:nvSpPr/p:cNvPr', NS).get('name')
                    expected = 'ED7D31' if name == 'map-brace-frames' else '4472C4'
                    self.assertEqual(color.get('val').upper(), expected)
                for name in z.namelist():
                    if re.fullmatch(r'ppt/slides/slide\d+\.xml', name):
                        r = ET.fromstring(z.read(name))
                        for shape in r.findall('.//p:sp', NS):
                            text = ''.join(e.text or '' for e in shape.findall('.//a:t', NS))
                            self.assertFalse(re.fullmatch(r'\s*\d+\s*/\s*\d+\s*', text))
                            self.assertNotIn('①', text)

    def test_map_heading_size_and_line_colors_are_exported(self):
        with tempfile.TemporaryDirectory() as temp:
            out, result = self.run_render(temp, map_layout={
                'headingSize': 22, 'frameLineColor': '#A05020',
                'topicLineColor': '#2050A0', 'leafLineColor': '#208050'})
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((out/'layout-review.json').read_text())[0]
            self.assertEqual(report['headingSize'], 22)
            with ZipFile(out/'candidate.pptx') as z:
                native_spacings = [int(e.get('val')) for n in z.namelist()
                                   if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)
                                   for e in ET.fromstring(z.read(n)).findall('.//a:lnSpc/a:spcPts', NS)]
                self.assertIn(2535, native_spacings, 'Measured body spacing must reach native PPTX')
                first = ET.fromstring(z.read('ppt/slides/slide1.xml'))
                for shape in first.findall('.//p:sp', NS):
                    name = shape.find('p:nvSpPr/p:cNvPr', NS).get('name', '')
                    if name.startswith('map-brace-'):
                        expected = ('A05020' if name == 'map-brace-frames' else
                                    '2050A0' if name.startswith('map-brace-topics-') else '208050')
                        self.assertEqual(shape.find('p:spPr/a:ln/a:solidFill/a:srgbClr', NS).get('val').upper(), expected)
                    if name.startswith('map-topic-'):
                        sizes = [int(e.get('sz')) for e in shape.iter() if e.get('sz')]
                        self.assertTrue(sizes)
                        self.assertTrue(all(size == 1650 for size in sizes), sizes)

    def test_plan_failure_blocks_pptx_export(self):
        with tempfile.TemporaryDirectory() as temp:
            out, result = self.run_render(temp, invalid_plan=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Teaching plan check failed before rendering', result.stderr)
            self.assertFalse(json.loads((out/'plan-check.json').read_text())['passed'])
            self.assertFalse((out/'candidate.pptx').exists())

    def test_unfittable_map_fails_without_silently_splitting_or_dropping_nodes(self):
        with tempfile.TemporaryDirectory() as temp:
            out, result = self.run_render(temp, oversized=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('whole-lesson map needs', result.stderr)
            self.assertFalse((out/'candidate.pptx').exists())
