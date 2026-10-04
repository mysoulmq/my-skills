"""Check source-selected recall and reviewed emphasis in actual native PPT shapes."""
import argparse,json,hashlib
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as E
from pptx_views import ordered_slides
from knowledge_recall import compile_recall,norm
from native_recall_background import check_recall_background
A='{http://schemas.openxmlformats.org/drawingml/2006/main}';P='{http://schemas.openxmlformats.org/presentationml/2006/main}'

def styled_text(shape):
    text='';high='';heavy=''
    for p in shape.iter(A+'p'):
        for r in p.findall(A+'r'):
            value=''.join(t.text or '' for t in r.iter(A+'t'));rp=r.find(A+'rPr')
            text+=value
            hi=rp.find(A+'highlight') if rp is not None else None
            high+=value if hi is not None else '\0'*len(value)
            heavy+=value if rp is not None and rp.get('b')=='1' else '\0'*len(value)
    return norm(text),norm(high),norm(heavy)

def check(pptx,records,catalog,mapping):
    errors=[];expected={}
    for record in records:
        if record['id'] in expected:errors.append('Duplicate recall ID: '+record['id'])
        expected[record['id']]=compile_recall(record,catalog)
    with ZipFile(pptx) as z:files={n:z.read(n) for n in z.namelist()}
    order=ordered_slides(files);seen=set()
    for page in mapping:
        n=page['page'];rid=page.get('recallId');nodes=expected.get(rid,[]) if rid is None else expected.get(rid)
        if nodes is None or type(n)!=int or not 1<=n<=len(order):errors.append('Invalid recall/page mapping');continue
        root=E.fromstring(files[order[n-1]]);shapes={}
        for s in root.iter(P+'sp'):
            nv=s.find('.//'+P+'cNvPr')
            if nv is not None:shapes[nv.get('id')]=s
        node_shapes=page.get('nodeShapes',{})
        known_nodes={node['id']:node for node in nodes}
        if set(node_shapes)-known_nodes.keys():errors.append(f'P{n}: unknown recall nodes')
        if rid is not None and not node_shapes:errors.append(f'P{n}: empty recall node mapping')
        if rid is not None:
            errors.extend(f'P{n}: {issue}' for issue in check_recall_background(root,node_shapes.values(),page.get('backgroundShapeId')))
        # Continuations may carry a subset; the union must still cover the
        # complete source-backed record. Never truncate records to fit pages.
        for node_id,sid in node_shapes.items():
            node=known_nodes.get(node_id)
            if node is None:continue
            shape=shapes.get(str(sid))
            if shape is None:errors.append(f'P{n}: missing editable recall {node["id"]}');continue
            text,hi,heavy=styled_text(shape)
            if text!=norm(node['text']):errors.append(f'P{n}: recall text changed {node["id"]}')
            for word in node['emphasis']:
                if norm(word) not in hi:errors.append(f'P{n}: recall highlight lost {word}')
            seen.add((rid,node['id']))
        for mark in page.get('emphasisShapes',[]):
            shape=shapes.get(str(mark['shapeId']))
            if shape is None:errors.append(f'P{n}: missing analysis/answer shape');continue
            text,hi,heavy=styled_text(shape)
            if (mark.get('noHighlight') or mark.get('role')=='analysis-material') and any(True for _ in shape.iter(A+'highlight')):
                errors.append(f'P{n}: forbidden highlight in {mark.get("role","answer")}')
            if mark.get('sectionTexts'):
                paragraphs=[''.join(t.text or '' for t in p.iter(A+'t')) for p in shape.iter(A+'p')]
                starts=set();offset=0
                for value in paragraphs:starts.add(offset);offset+=len(norm(value))
                expected_text=''.join(norm(s) for s in mark['sectionTexts'])
                if text!=expected_text:errors.append(f'P{n}: answer text changed')
                offset=0
                for section in mark['sectionTexts']:
                    if offset not in starts:errors.append(f'P{n}: answer role lacks paragraph boundary')
                    offset+=len(norm(section))
            for word in mark.get('focus',[]):
                if norm(word) not in hi:errors.append(f'P{n}: analysis/answer highlight lost {word}')
            for word in mark.get('emphasis',[]):
                if norm(word) not in heavy:errors.append(f'P{n}: analysis/answer bold lost {word}')
        for sid in page.get('unmarkedShapeIds',[]):
            if str(sid) in shapes and any(r.find(A+'rPr/'+A+'highlight') is not None for r in shapes[str(sid)].iter(A+'r')):
                errors.append(f'P{n}: forbidden source/prompt highlight')
    for rid,nodes in expected.items():
        for node in nodes:
            if (rid,node['id']) not in seen:errors.append(f'{rid}: no actual recall delivery {node["id"]}')
    return {'pass':not errors,'errors':errors,'sha256':hashlib.sha256(Path(pptx).read_bytes()).hexdigest(),
            'scope':'native text/source/emphasis transfer; selection, hierarchy geometry, soft wraps and pedagogy require review'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pptx');p.add_argument('records');p.add_argument('catalog');p.add_argument('mapping');p.add_argument('--report',required=True);a=p.parse_args()
    out=check(a.pptx,json.loads(Path(a.records).read_text())['records'],json.loads(Path(a.catalog).read_text()),json.loads(Path(a.mapping).read_text()))
    Path(a.report).write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False));raise SystemExit(not out['pass'])
