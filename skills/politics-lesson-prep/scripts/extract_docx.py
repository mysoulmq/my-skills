"""Extract ordered DOCX paragraphs and table cells without model transcription."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def paragraph_text(node):
    result = []
    for n in node.iter():
        if n.tag == W + 't':
            result.append(n.text or '')
        elif n.tag == W + 'tab':
            result.append('\t')
        elif n.tag in (W + 'br', W + 'cr'):
            result.append('\n')
    return ''.join(result)


def extract(filename):
    with ZipFile(filename) as z:
        root = ET.fromstring(z.read('word/document.xml'))
    blocks = []
    def walk(parent):
        for n in parent:
            if n.tag == W + 'p':
                text = paragraph_text(n)
                if text.strip():
                    blocks.append({'id': f'b{len(blocks)+1}', 'kind': 'paragraph', 'text': text})
            elif n.tag == W + 'tbl':
                rows = []
                for row in n.findall(W+'tr'):
                    cells = []
                    for cell in row.findall(W+'tc'):
                        cells.append('\n'.join(paragraph_text(p) for p in cell.iter(W+'p')))
                    rows.append(cells)
                blocks.append({'id': f'b{len(blocks)+1}', 'kind': 'table', 'rows': rows})
            elif n.tag in (W+'sdt', W+'sdtContent'):
                walk(n)
    walk(root.find(W+'body'))
    return {'source': Path(filename).name, 'blocks': blocks}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('input'); p.add_argument('output')
    args = p.parse_args()
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(extract(args.input), ensure_ascii=False, indent=2), encoding='utf-8')
