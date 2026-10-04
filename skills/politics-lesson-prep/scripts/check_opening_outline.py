"""Verify planned opening-outline emphasis and source stars in the actual PPT.

This checks transfer, not pedagogical selection. Run after the existing source-
based mark compiler and independent review; do not infer importance from words.
"""
import argparse,hashlib,json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as E
from pptx_views import ordered_slides
from check_recall_delivery import styled_text,P,A
from knowledge_recall import norm

def emphasis_text(shape):
    """Native explicit red ink or yellow background; keep the two masks separate.

    Adapters must resolve theme colors to explicit sRGB before this transfer
    check. A general text color or any arbitrary background is not emphasis.
    """
    red='';yellow='';double=False
    for p in shape.iter(A+'p'):
        for r in p.findall(A+'r'):
            value=''.join(t.text or '' for t in r.iter(A+'t'))
            rp=r.find(A+'rPr')
            ink=rp.find(A+'solidFill/'+A+'srgbClr') if rp is not None else None
            bg=rp.find(A+'highlight/'+A+'srgbClr') if rp is not None else None
            is_red=ink is not None and ink.get('val','').upper() in ('FF0000','C00000')
            is_yellow=bg is not None and bg.get('val','').upper()=='FFFF00'
            red+=value if is_red else '\0'*len(value)
            yellow+=value if is_yellow else '\0'*len(value)
            double=double or (is_red and is_yellow and bool(value.strip()))
    return norm(red),norm(yellow),double

def check(pptx,source,plan):
    errors=[];units={u['id']:u['text'] for u in source['units']}
    expected_stars={key for key,text in units.items() if '★' in text}
    with ZipFile(pptx) as z:files={n:z.read(n) for n in z.namelist()}
    order=ordered_slides(files)
    if not order:raise ValueError('Empty presentation')
    root=E.fromstring(files[order[0]]);shapes={}
    for shape in root.iter(P+'sp'):
        nv=shape.find('.//'+P+'cNvPr')
        if nv is not None:shapes[nv.get('id')]=shape
    seen=set();marked=0
    nodes=plan.get('nodes',[])
    if not nodes:errors.append('Missing opening-outline object mapping')
    for node in nodes:
        shape=shapes.get(str(node['shapeId']))
        if shape is None:errors.append('Opening node missing: '+str(node['shapeId']));continue
        text,_,_=styled_text(shape)
        red,yellow,double=emphasis_text(shape)
        if double:errors.append('Opening keyword uses both red and yellow: '+str(node['shapeId']))
        if text!=norm(node['text']):errors.append('Opening node text differs: '+str(node['shapeId']))
        for word in node.get('focus',[]):
            if not norm(word) or not (norm(word) in red or norm(word) in yellow):errors.append('Opening emphasis lost (red or yellow): '+str(word))
            else:marked+=1
        refs=set(node.get('starRefs',[]))
        if refs-expected_stars:errors.append('Opening star lacks original source: '+str(sorted(refs-expected_stars)))
        if refs and '★' not in text:errors.append('Opening source star lost: '+str(node['shapeId']))
        if '★' in text and not refs:errors.append('Opening star missing provenance: '+str(node['shapeId']))
        if refs and '★' in text:seen.update(refs)
    if not marked:errors.append('Opening outline has no verified keyword emphasis (red or yellow)')
    if expected_stars-seen:errors.append('Source-star points not mapped to opening outline: '+str(sorted(expected_stars-seen)))
    return {'pass':not errors,'errors':errors,'sha256':hashlib.sha256(Path(pptx).read_bytes()).hexdigest(),
            'scope':'first-slide native marks and source-star transfer; visual/pedagogical quality requires review'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pptx');p.add_argument('source');p.add_argument('plan');p.add_argument('--report',required=True);a=p.parse_args()
    out=check(a.pptx,json.loads(Path(a.source).read_text()),json.loads(Path(a.plan).read_text()))
    Path(a.report).write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False));raise SystemExit(not out['pass'])
