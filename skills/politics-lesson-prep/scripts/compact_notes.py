"""Validate page-specific glanceable cues and replace only native notes bodies."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as ET
from pptx_views import P, R, relpath, resolve, ordered_slides, xml

A='http://schemas.openxmlformats.org/drawingml/2006/main'

def cue_text(plan, page_id):
    lines=plan.get('notesByPage',{}).get(page_id)
    if isinstance(lines,list):
        lines=list(lines)
        score_note=plan.get('scoreNotesByPage',{}).get(page_id)
        if score_note and score_note not in lines:lines.append(score_note)
    if not isinstance(lines,list) or not 1<=len(lines)<=3:
        raise ValueError(f'{page_id}: supply 1–3 page-specific notesByPage cues')
    if any(not isinstance(s,str) or not s.strip() or len(s)>35 or '\n' in s for s in lines):
        raise ValueError(f'{page_id}: each cue must be one line, at most 35 characters; rewrite, never truncate')
    if sum(map(len,lines))>90:raise ValueError(f'{page_id}: notes exceed 90 characters')
    return '\n'.join(lines)

def rewrite(input_path, mapping, plan, output_path):
    with ZipFile(input_path) as z:files={n:z.read(n) for n in z.namelist()}
    slides=ordered_slides(files)
    if len(slides)!=len(mapping):raise ValueError('Page mapping mismatch')
    for slide,page in zip(slides,mapping):
        text=cue_text(plan,page['id'])
        rels=ET.fromstring(files[relpath(slide)])
        rel=next(r for r in rels if r.get('Type')==R+'/notesSlide')
        note=resolve(slide,rel.get('Target'));root=ET.fromstring(files[note])
        body=None
        for shape in root.findall('.//{'+P+'}sp'):
            ph=shape.find('.//{'+P+'}ph')
            if ph is not None and ph.get('type')=='body':body=shape.find('{'+P+'}txBody');break
        if body is None:raise ValueError(f'{page["id"]}: no native notes body')
        for p in list(body):
            if p.tag=='{'+A+'}p':body.remove(p)
        for line in text.split('\n'):
            par=ET.SubElement(body,'{'+A+'}p');run=ET.SubElement(par,'{'+A+'}r')
            ET.SubElement(run,'{'+A+'}t').text=line
        files[note]=xml(root)
    target=Path(output_path);temp=target.with_suffix('.notes-tmp.pptx')
    with ZipFile(temp,'w',ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(name,data)
    temp.replace(target)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('input','mapping','plan','output'):p.add_argument(key)
    args=p.parse_args();load=lambda f:json.loads(Path(f).read_text())
    rewrite(args.input,load(args.mapping),load(args.plan),args.output)
