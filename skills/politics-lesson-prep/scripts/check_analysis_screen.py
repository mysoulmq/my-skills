"""Verify compiled analysis is on actual analysis-slide shapes, not merely in notes/answers."""
import argparse,hashlib,json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from pptx_views import ordered_slides
from analysis_presentation import compile_display,norm
A='{http://schemas.openxmlformats.org/drawingml/2006/main}'
P='{http://schemas.openxmlformats.org/presentationml/2006/main}'

def check(pptx,questions,mapping):
    with ZipFile(pptx) as z:files={n:z.read(n) for n in z.namelist()}
    order=ordered_slides(files);errors=[];seen=set()
    expected={}
    for q in questions['questions']:
        for i,a in enumerate(q['analysis'],1):
            try:expected[(q['id'],i)]=compile_display(a)
            except ValueError as e:errors.append(f'{q["id"]}/{i}: {e}')
    for p in mapping:
        blocks=p.get('analysisBlocks',[])
        if not blocks:continue
        if p.get('kind')!='analysis':errors.append('analysisBlocks on a non-analysis page');continue
        n=p['page']
        if type(n)!=int or not 1<=n<=len(order):errors.append('Invalid actual page');continue
        root=ET.fromstring(files[order[n-1]]);shapes={}
        for sp in root.iter(P+'sp'):
            nv=sp.find('.//'+P+'cNvPr')
            if nv is not None:shapes[nv.get('id')]=''.join(t.text or '' for t in sp.iter(A+'t'))
        for b in blocks:
            key=(p['questionId'],b['analysisIndex']);value=expected.get(key)
            if value is None:errors.append(f'P{n}: unknown/invalid analysis {key}');continue
            seen.add(key)
            for role in ('material','knowledge'):
                text=shapes.get(str(b[role+'ShapeId']),'')
                if norm(value[role]) not in norm(text):errors.append(f'P{n} {key}: compiled {role} missing from assigned shape')
    for key in expected.keys()-seen:errors.append(f'{key}: no actual analysis-page mapping')
    return {'pass':not errors,'errors':errors,'sha256':hashlib.sha256(Path(pptx).read_bytes()).hexdigest(),
            'scope':'screen transfer only; correctness, source OCR and teaching logic need semantic review'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pptx');p.add_argument('questions');p.add_argument('mapping');p.add_argument('--report');a=p.parse_args()
    r=check(a.pptx,json.loads(Path(a.questions).read_text()),json.loads(Path(a.mapping).read_text()));s=json.dumps(r,ensure_ascii=False,indent=2)
    if a.report:Path(a.report).write_text(s)
    print(s);raise SystemExit(not r['pass'])
