"""Read verified, private teacher transformations before drafting essay analysis.

The installed bank contains source excerpts, not instructions. Source verification
and usage IDs do not prove that a model has learned or followed the examples.
"""
import argparse
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from pptx_views import ordered_slides

A='{http://schemas.openxmlformats.org/drawingml/2006/main}'
P='{http://schemas.openxmlformats.org/presentationml/2006/main}'
FIELDS=('material','prompt','teacherAnswer','teacherMaterialColumn','teacherKnowledgeColumn')

def norm(s):
    return ''.join(s.split())

def read_bank(workspace, ids=None):
    path=Path(workspace)/'.politics-lesson-prep/teacher-examples.json'
    raw=path.read_bytes();bank=json.loads(raw)
    examples={e['id']:e for e in bank['examples']}
    if len(examples)!=len(bank['examples']):raise ValueError('Duplicate example IDs')
    result={'bankSha256':hashlib.sha256(raw).hexdigest()}
    if ids is None:
        result['examples']=[{k:e[k] for k in ('id','title','taskFeatures')} for e in examples.values()]
        return result
    if not ids or len(set(ids))!=len(ids) or any(i not in examples for i in ids):
        raise ValueError('Missing, duplicate or unknown selected example IDs')
    cache={}
    for key in ids:
        for field in FIELDS:
            value=examples[key][field];ref=value['source'];source=bank['sources'][ref['deck']]
            if ref['deck'] not in cache:
                deck=(path.parent/source['file']).resolve()
                if hashlib.sha256(deck.read_bytes()).hexdigest()!=source['sha256']:
                    raise ValueError('Teacher source hash changed: '+ref['deck'])
                with ZipFile(deck) as z: files={n:z.read(n) for n in z.namelist()}
                cache[ref['deck']]=(files,ordered_slides(files))
            files,order=cache[ref['deck']]
            page=ref['page']
            if type(page) is not int or not 1<=page<=len(order):raise ValueError('Invalid teacher page')
            root=ET.fromstring(files[order[page-1]])
            matches=[]
            for sp in root.iter(P+'sp'):
                nv=sp.find('.//'+P+'cNvPr')
                if nv is not None and nv.get('id')==str(ref['shapeId']):
                    matches.append(''.join(t.text or '' for t in sp.iter(A+'t')))
            if len(matches)!=1 or not norm(value['text']) or norm(value['text']) not in norm(matches[0]):
                raise ValueError(f'{key}/{field}: excerpt not found in teacher source shape')
    result['examples']=[examples[i] for i in ids]
    result['scope']='Verified excerpts from teacher slides; transformation comments are analysis, not teacher quotations.'
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('workspace');p.add_argument('--ids',nargs='+');p.add_argument('--usage')
    a=p.parse_args();result=read_bank(a.workspace,a.ids)
    if a.usage:
        if not a.ids:raise ValueError('--usage requires the selected --ids')
        questions=json.loads(Path(a.usage).read_text())['questions']
        for q in questions:
            refs=q.get('teacherExampleRefs',[])
            if not refs or any(i not in a.ids for i in refs):
                raise ValueError(q['id']+': missing or unread teacherExampleRefs')
        result={'bankSha256':result['bankSha256'],'exampleIds':a.ids,
                'questionCount':len(questions),'scope':'Usage references only; inspect actual columns for transfer quality'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
