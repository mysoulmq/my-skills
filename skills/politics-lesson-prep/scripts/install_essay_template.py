"""Install selected native reference slides privately, preserving their XML/timing.

Selection is explicit, never inferred from the source's file names.
"""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from pptx_views import compose, ordered_slides, NS


def install(source, workspace, analysis, answer):
    source = Path(source).resolve()
    target = Path(workspace).resolve() / '.politics-lesson-prep'
    target.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    slides = [{'id': f'{role}-{i}', 'deck': 'reference', 'sourceSlide': number,
               'role': role} for role, numbers in [('analysis', analysis), ('answer', answer)]
              for i, number in enumerate(numbers, 1)]
    deck = target / f'essay-template-{digest[:12]}.pptx'
    if deck.exists():
        raise ValueError(f'Template exists; inspect existing contract before replacing: {deck}')
    compose({'decks': {'reference': str(source)}, 'slides': slides}, deck)
    inventory = []
    with ZipFile(source) as z:
        files = {n: z.read(n) for n in z.namelist()}
        order = ordered_slides(files)
        for page, item in enumerate(slides, 1):
            payload = files[order[item['sourceSlide'] - 1]]
            root = ET.fromstring(payload)
            shapes = []
            for shape in root.find('p:cSld/p:spTree', NS):
                prop = shape.find('.//p:cNvPr', NS)
                if prop is not None:
                    shapes.append({'id': prop.get('id'), 'name': prop.get('name'),
                                   'kind': shape.tag.split('}')[-1]})
            inventory.append({**item, 'templatePage': page,
                              'sourceXmlSha256': hashlib.sha256(payload).hexdigest(),
                              'shapes': shapes})
    contract = {'mode': 'native-reference', 'template': str(deck),
                'sourceSha256': digest, 'source': str(source), 'pages': inventory,
                'status': 'installed-reference-not-generated-output'}
    config = target / 'essay-template.json'
    config.write_text(json.dumps(contract, ensure_ascii=False, indent=2))
    return config


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source'); p.add_argument('workspace')
    p.add_argument('--analysis', type=int, nargs='+', required=True)
    p.add_argument('--answer', type=int, nargs='+', required=True)
    a = p.parse_args()
    print(install(a.source, a.workspace, a.analysis, a.answer))
