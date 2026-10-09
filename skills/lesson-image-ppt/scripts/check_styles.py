"""Verify semantic headings and planned navigation red in the actual PPTX."""
import argparse
import json
import os
from pathlib import Path
import posixpath
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from template_contract import read
from prepare_marks import compile_marks, norm

A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def check(source, deck, pptx):
    deck, _ = compile_marks(source, deck)
    template = read(os.environ.get('LESSON_TEMPLATE_PPTX', Path(__file__).resolve().parents[1] / 'assets/teaching-template.pptx'))
    style = template['roles']['lesson.subtitle.2']
    units = {u['id']: u for u in source['units']}
    errors, checked = [], []
    ref = lambda o: o if isinstance(o, str) else (o or {}).get('ref')
    with ZipFile(pptx) as z:
        rels = {r.get('Id'): posixpath.normpath(posixpath.join('ppt', r.get('Target'))).lstrip('/') for r in ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))}
        names = [rels[e.get(R+'id')] for e in ET.fromstring(z.read('ppt/presentation.xml')).findall(P+'sldIdLst/'+P+'sldId')]
        if len(names) != len(deck['slides']):
            return {'passed': False, 'errors': ['PPTX and deck slide counts differ']}
        for page, (name, slide) in enumerate(zip(names, deck['slides']), 1):
            shapes = {}
            for sp in ET.fromstring(z.read(name)).iter(P+'sp'):
                nv = sp.find(P+'nvSpPr/'+P+'cNvPr')
                if nv is not None:
                    shapes[nv.get('name')] = sp

            def runs(key):
                sp = shapes.get(key)
                if sp is None:
                    errors.append(f'Page {page}: missing named shape {key}')
                    return []
                result = []
                for par in sp.findall(P+'txBody/'+A+'p'):
                    default = par.find(A+'pPr/'+A+'defRPr')
                    for r in par.findall(A+'r'):
                        rp = r.find(A+'rPr')
                        def attr(k):
                            return rp.get(k, default.get(k) if default is not None else None) if rp is not None else default.get(k) if default is not None else None
                        color = rp.find(A+'solidFill/'+A+'srgbClr') if rp is not None else None
                        if color is None and default is not None:
                            color = default.find(A+'solidFill/'+A+'srgbClr')
                        result.append((norm(r.findtext(A+'t', '')), attr('sz'), attr('b'), color.get('val', '').upper() if color is not None else ''))
                return [r for r in result if r[0]]

            if slide.get('type') == 'knowledge-map':
                for gi, group in enumerate(slide.get('groups', []), 1):
                    targets = [(f'map-frame-{gi}', group['title'])] + [(f'map-topic-{gi}-{ti}', t['title']) for ti, t in enumerate(group.get('topics', []), 1)]
                    for key, obj in targets:
                        for quote in obj.get('contrast', []) if isinstance(obj, dict) else []:
                            rr = runs(key)
                            chars = [(ch, r[3]) for r in rr for ch in r[0]]
                            text = ''.join(c for c, _ in chars); q = norm(quote); start = text.find(q)
                            if start < 0 or any(c != 'FF0000' for _, c in chars[start:start+len(q)]):
                                errors.append(f'Page {page}: navigation red missing {key}: {quote}')
                            checked.append([page, key, 'red'])
                continue
            headings = []
            if slide.get('topic'):
                headings.append(ref(slide['topic']))
            for block in slide.get('blocks', []):
                if block.get('type') == 'paragraphs':
                    headings.extend(ref(o) for o in block['items'] if units.get(ref(o), {}).get('level') in ('point', 'subpoint'))
            for key in headings:
                level = units.get(key, {}).get('level', 'point')
                size = str(round((style['size']-(2 if level == 'subpoint' else 0))*75))
                rr = runs(key)
                if not rr or any(r[1:] != (size, '1', style['color'].lstrip('#').upper()) for r in rr):
                    errors.append(f'Page {page}: inconsistent heading style {key} ({level})')
                checked.append([page, key, level])
    return {'passed': not errors, 'errors': errors, 'checked': checked,
            'scope': 'Native heading font/color and planned red; visual spacing and semantic classification still require review.'}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source'); ap.add_argument('deck'); ap.add_argument('pptx'); ap.add_argument('--report', required=True)
    a = ap.parse_args()
    result = check(json.loads(Path(a.source).read_text()), json.loads(Path(a.deck).read_text()), a.pptx)
    Path(a.report).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result['passed'] else 1)
