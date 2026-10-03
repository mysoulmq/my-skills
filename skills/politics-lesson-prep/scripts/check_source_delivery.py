"""Source identity and provenance gate for the actual final PPTX (native or generated)."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from pptx_views import ordered_slides

A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
def norm(value):
    return re.sub(r'\s+', '', str(value or ''))

def identity(record):
    # No fuzzy deduplication: different task wording or options must remain separate.
    return (norm(record['material']), norm(record['prompt']),
            tuple(norm(x) for x in record.get('options', [])))

def validate(records, questions, pages, texts):
    errors=[]; raw={}; groups={}; owners={}; seen=set()
    if not records or not questions: errors.append("empty source registry or question set")
    for r in records:
        if r['id'] in raw: errors.append('duplicate source record: '+r['id'])
        raw[r['id']]=r; groups.setdefault(identity(r), []).append(r['id'])
    qids=set()
    for q in questions:
        qid=q['id']
        if qid in qids: errors.append('duplicate canonical id: '+qid)
        qids.add(qid)
        refs=q.get('sourceRecords', [])
        if not refs: errors.append(qid+': missing sourceRecords')
        labels=set()
        for rid in refs:
            if rid not in raw: errors.append(qid+': unknown source '+rid); continue
            if rid in seen: errors.append(rid+': assigned more than once')
            seen.add(rid); key=identity(raw[rid])
            if key in owners and owners[key]!=qid: errors.append(qid+': exact duplicate of '+owners[key])
            owners[key]=qid
            if key!=identity(q): errors.append(qid+': changed source material/task/options')
            label=raw[rid].get('sourceLabel','')
            if label: labels.add(norm(label))
        if refs and all(r in raw for r in refs):
            for field in ('referenceAnswer','referenceExplanation'):
                versions={norm(raw[r].get(field)) for r in refs}
                if len(versions)>1: errors.append(qid+': source variants require reconciliation: '+field)
        selected=[p for p in pages if p.get('questionId')==qid]
        if not selected: errors.append(qid+': absent from final deck')
        for p in selected:
            n=p['page']
            if not isinstance(n,int) or n<1 or n>len(texts): errors.append(qid+': invalid page'); continue
            for label in labels:
                if label not in norm(texts[n-1]): errors.append(f'{qid}: P{n} missing original source label')
    for p in pages:
        if p.get('questionId') and p['questionId'] not in qids:
            errors.append('unknown mapped question: '+p['questionId'])
    if seen!=set(raw): errors.append('unassigned source records: '+','.join(sorted(set(raw)-seen)))
    return {'pass':not errors,'errors':errors,'rawCount':len(records),'uniqueCount':len(groups)}

def check(pptx, registry, mapping):
    data=Path(pptx).read_bytes()
    with ZipFile(pptx) as z: files={n:z.read(n) for n in z.namelist()}
    order=ordered_slides(files)
    texts=[''.join(t.text or '' for t in ET.fromstring(files[n]).iter(A+'t')) for n in order]
    result=validate(registry['sourceRecords'],registry['questions'],mapping,texts)
    result.update(sha256=hashlib.sha256(data).hexdigest(),slideCount=len(order),pptx=str(Path(pptx).resolve()))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pptx');p.add_argument('registry');p.add_argument('mapping');p.add_argument('--report');a=p.parse_args()
    result=check(a.pptx,json.loads(Path(a.registry).read_text()),json.loads(Path(a.mapping).read_text()))
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if a.report: Path(a.report).write_text(text)
    print(text);raise SystemExit(0 if result['pass'] else 1)
