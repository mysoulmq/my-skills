"""Attach page-specific short teaching cues to native slides."""
import argparse
import json
import posixpath as pp
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as ET
from pptx_views import P,R,PKG,CT,NS,xml,relpath,resolve,ordered_slides
from compact_notes import cue_text

A='http://schemas.openxmlformats.org/drawingml/2006/main'
ET.register_namespace('a',A)


def note_xml(text):
    n=ET.Element('{'+P+'}notes')
    tree=ET.SubElement(ET.SubElement(n,'{'+P+'}cSld'),'{'+P+'}spTree')
    nv=ET.SubElement(tree,'{'+P+'}nvGrpSpPr');ET.SubElement(nv,'{'+P+'}cNvPr',id='1',name='');ET.SubElement(nv,'{'+P+'}cNvGrpSpPr');ET.SubElement(nv,'{'+P+'}nvPr')
    ET.SubElement(tree,'{'+P+'}grpSpPr')
    s=ET.SubElement(tree,'{'+P+'}sp');nv=ET.SubElement(s,'{'+P+'}nvSpPr');ET.SubElement(nv,'{'+P+'}cNvPr',id='2',name='Notes body');ET.SubElement(nv,'{'+P+'}cNvSpPr');ET.SubElement(ET.SubElement(nv,'{'+P+'}nvPr'),'{'+P+'}ph',type='body',idx='1')
    ET.SubElement(s,'{'+P+'}spPr');body=ET.SubElement(s,'{'+P+'}txBody');ET.SubElement(body,'{'+A+'}bodyPr');ET.SubElement(body,'{'+A+'}lstStyle')
    for line in text.split('\n'):
        par=ET.SubElement(body,'{'+A+'}p');run=ET.SubElement(par,'{'+A+'}r');ET.SubElement(run,'{'+A+'}t').text=line
    return xml(n)


def add(input,source,deck,sequence,plan,output):
    if Path(output).exists():raise ValueError('Refusing overwrite')
    with ZipFile(input) as z:files={n:z.read(n) for n in z.namelist()}
    order=ordered_slides(files)
    if len(order)!=len(deck['slides']):raise ValueError('Deck/actual slide count mismatch')
    types=ET.fromstring(files['[Content_Types].xml'])
    for i,part in enumerate(order,1):
        text=cue_text(plan,f'knowledge-{i}')
        rp=relpath(part);relationships=ET.fromstring(files[rp]) if rp in files else ET.Element('{'+PKG+'}Relationships')
        existing=next((r for r in relationships if r.get('Type')==R+'/notesSlide'),None)
        if existing is not None:note=resolve(part,existing.get('Target'))
        else:
            note=f'ppt/notesSlides/prepNotes{i}.xml'
            if note in files:raise ValueError('Notes name collision')
            ids={r.get('Id') for r in relationships};j=1
            while f'rId{j}' in ids:j+=1
            ET.SubElement(relationships,'{'+PKG+'}Relationship',Id=f'rId{j}',Type=R+'/notesSlide',Target=pp.relpath(note,pp.dirname(part)))
            ET.SubElement(types,'{'+CT+'}Override',PartName='/'+note,ContentType='application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml')
        files[note]=note_xml(text)
        nr=ET.Element('{'+PKG+'}Relationships');ET.SubElement(nr,'{'+PKG+'}Relationship',Id='rId1',Type=R+'/slide',Target=pp.relpath(part,pp.dirname(note)))
        files[relpath(note)]=xml(nr);files[rp]=xml(relationships)
    files['[Content_Types].xml']=xml(types)
    with ZipFile(output,'w',ZIP_DEFLATED) as z:
        for n,payload in files.items():z.writestr(n,payload)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['input','source','deck','sequence','plan','output']:p.add_argument(name)
    a=p.parse_args();load=lambda f:json.loads(Path(f).read_text())
    add(a.input,load(a.source),load(a.deck),load(a.sequence),load(a.plan),a.output)
