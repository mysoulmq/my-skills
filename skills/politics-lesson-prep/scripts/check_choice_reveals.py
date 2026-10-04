"""Check the final choice PPT against the shared native click/Appear template.

This is an OOXML contract check, not evidence of playback on a particular device.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from pptx_views import ordered_slides
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'lesson-image-ppt/scripts'))
from add_reveals import _timing, _targets

P='{http://schemas.openxmlformats.org/presentationml/2006/main}'
A='{http://schemas.openxmlformats.org/drawingml/2006/main}'


def tree(node):
    if node is None:return None
    return (node.tag, sorted(node.attrib.items()), (node.text or '').strip(), [tree(c) for c in node])


def check(path, choices=None):
    errors=[];count=0;seen=set()
    supplied={q['id']:q for q in choices['questions']} if choices is not None else None
    with ZipFile(path) as z: files={n:z.read(n) for n in z.namelist()}
    for page,part in enumerate(ordered_slides(files),1):
        root=ET.fromstring(files[part])
        all_names=[e.get('name','') for e in root.iter(P+'cNvPr')]
        prefixes={m.group(1) for n in all_names if (m:=re.match(r'^(.*-choice-\d+)-(?:answer|annotation-\d+|option-\d+|stem)$',n))}
        if not prefixes:continue
        try:names=_targets(root)
        except ValueError as exc:
            errors.append(f'page {page}: {exc}');continue
        for prefix in prefixes:
            count+=1
            answer=prefix+'-answer'
            annotations=sorted((n for n in names if n.startswith(prefix+'-annotation-')),key=lambda n:int(n.rsplit('-',1)[1]))
            if answer not in names:
                errors.append(f'page {page}: missing answer shape');continue
            allowed={prefix+'-'+suffix for suffix in ('stem','heading','combinations','answer')} | {f'{prefix}-option-{i}' for i in range(4)} | set(annotations)
            for sp in root.iter(P+'sp'):
                nv=sp.find('.//'+P+'cNvPr')
                if any((t.text or '').strip() for t in sp.iter(A+'t')) and (nv is None or nv.get('name') not in allowed):
                    errors.append(f'page {page}: unexpected text object outside choice template; inspect for visible explanation')
            steps=[[names[answer]],*[[names[n]] for n in annotations]]
            if tree(root.find(P+'timing'))!=tree(ET.fromstring(_timing(steps))):
                errors.append(f'page {page}: answer/annotations must use the click-only entrance template; unanimated or changed timing')
            qid=prefix.rsplit('-choice-',1)[0];seen.add(qid)
            if supplied is not None:
                q=supplied.get(qid)
                if q is None:
                    errors.append(f'page {page}: unknown choice {qid}');continue
                text={}
                for sp in root.iter(P+'sp'):
                    nv=sp.find('.//'+P+'cNvPr')
                    if nv is not None:text[nv.get('name')]=''.join(t.text or '' for t in sp.iter(A+'t'))
                norm=lambda s:''.join(s.split())
                for i,o in enumerate(q['options']):
                    if norm(text.get(f'{prefix}-option-{i}',''))!=norm(o['key']+' '+o['text']):
                        errors.append(f'page {page}: option {i} changed or contains inline explanation')
                expected={f'{prefix}-annotation-{i}' for i,o in enumerate(q['options']) if o['verdict']!='supported'}
                if expected!=set(annotations):errors.append(f'page {page}: annotation coverage mismatch')
                if norm(text.get(answer,''))!=norm('答案 '+q['answer']):errors.append(f'page {page}: answer mismatch')
    if supplied is not None and seen!=set(supplied):errors.append('Choice coverage differs from supplied questions')
    return {'pass':not errors,'choicePages':count,'errors':errors,'scope':'OOXML click template and optional source-text check; playback not tested'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pptx');p.add_argument('--choices');p.add_argument('--report')
    a=p.parse_args();result=check(a.pptx,json.loads(Path(a.choices).read_text()) if a.choices else None)
    encoded=json.dumps(result,ensure_ascii=False,indent=2)
    if a.report:Path(a.report).write_text(encoded)
    print(encoded);raise SystemExit(0 if result['pass'] else 1)
