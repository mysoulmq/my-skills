"""Verify compiled analysis is on actual analysis-slide shapes, not merely in notes/answers."""
import argparse,hashlib,json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from pptx_views import ordered_slides
from analysis_presentation import compile_question,norm
from native_line_breaks import line_errors
A='{http://schemas.openxmlformats.org/drawingml/2006/main}'
P='{http://schemas.openxmlformats.org/presentationml/2006/main}'

def check(pptx,questions,mapping):
    with ZipFile(pptx) as z:files={n:z.read(n) for n in z.namelist()}
    order=ordered_slides(files);errors=[];seen=set()
    expected={};analysis_pages={}
    for page in mapping:
        if page.get('kind')=='analysis':
            analysis_pages.setdefault(page.get('questionId'),set()).add(page['page'])
    for q in questions['questions']:
        try:
            for i,a in enumerate(compile_question(q),1):expected[(q['id'],i)]=a
        except ValueError as e:errors.append(f'{q["id"]}: {e}')
    for p in mapping:
        blocks=p.get('analysisBlocks',[])
        if p.get('kind')!='analysis':
            if blocks:errors.append('analysisBlocks on a non-analysis page')
            continue
        n=p['page']
        if type(n)!=int or not 1<=n<=len(order):errors.append('Invalid actual page');continue
        root=ET.fromstring(files[order[n-1]]);shapes={};shape_lines={};highlighted=set()
        if len(analysis_pages.get(p.get('questionId'),()))>1:
            audit={str(s) for s in p.get('auditShapeIds',[])}
            actual={nv.get('id') for nv in root.iter(P+'cNvPr')}
            if not audit or not audit<=actual:
                errors.append(f'P{n}: declare actual auditShapeIds for multi-page analysis')
            targeted={t.get('spid') for t in root.iter(P+'spTgt')}
            # A group entrance also animates audit objects nested inside it.
            for group in root.iter(P+'grpSp'):
                nv=group.find(P+'nvGrpSpPr/'+P+'cNvPr')
                if nv is not None and nv.get('id') in targeted:
                    targeted.update(n.get('id') for n in group.iter(P+'cNvPr'))
            if audit & targeted:
                errors.append(f'P{n}: audit area must be initially visible without animation')
        if not blocks:continue
        for sp in root.iter(P+'sp'):
            nv=sp.find('.//'+P+'cNvPr')
            if nv is not None:
                shapes[nv.get('id')]=''.join(t.text or '' for t in sp.iter(A+'t'))
                lines=[]
                for para in sp.iter(A+'p'):
                    line=''
                    for node in para.iter():
                        if node.tag==A+'t':line+=node.text or ''
                        elif node.tag==A+'br':lines.append(line);line=''
                    lines.append(line)
                shape_lines[nv.get('id')]=lines
                if any(True for _ in sp.iter(A+'highlight')):highlighted.add(nv.get('id'))
        for b in blocks:
            key=(p['questionId'],b['analysisIndex']);value=expected.get(key)
            if value is None:errors.append(f'P{n}: unknown/invalid analysis {key}');continue
            seen.add(key)
            for role in ('material','knowledge'):
                sid=str(b[role+'ShapeId']);text=shapes.get(sid,'')
                if role=='material' and sid in highlighted:
                    errors.append(f'P{n} {key}: material synopsis must not be highlighted')
                for issue in line_errors(shape_lines.get(sid,[])):
                    errors.append(f'P{n} {key} {role}: {issue}')
                if norm(value[role]) not in norm(text):errors.append(f'P{n} {key}: compiled {role} missing from assigned shape')
    for key in expected.keys()-seen:errors.append(f'{key}: no actual analysis-page mapping')
    return {'pass':not errors,'errors':errors,'sha256':hashlib.sha256(Path(pptx).read_bytes()).hexdigest(),
            'scope':'screen transfer only; correctness, source OCR and teaching logic need semantic review'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pptx');p.add_argument('questions');p.add_argument('mapping');p.add_argument('--report');a=p.parse_args()
    r=check(a.pptx,json.loads(Path(a.questions).read_text()),json.loads(Path(a.mapping).read_text()));s=json.dumps(r,ensure_ascii=False,indent=2)
    if a.report:Path(a.report).write_text(s)
    print(s);raise SystemExit(not r['pass'])
