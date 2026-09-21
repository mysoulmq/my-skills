"""Reorder native slides with their relationship graph, preserving timing XML.

Input manifest: {decks: {key: path}, slides:[{id, deck, sourceSlide, ...}]}.
All references are resolved from package relationships, never filename order.
"""
import argparse
import copy
import json
import posixpath as pp
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as ET

P='http://schemas.openxmlformats.org/presentationml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
NS={'p':P,'r':R}
for prefix,uri in [('p',P),('r',R)]: ET.register_namespace(prefix,uri)


def xml(node):
    # OPC content-type and relationship roots use their default namespace.
    namespace=node.tag.split('}')[0].lstrip('{')
    if namespace in (CT,PKG):ET.register_namespace('',namespace)
    return ET.tostring(node,encoding='utf-8',xml_declaration=True)


def relpath(part): return pp.join(pp.dirname(part),'_rels',pp.basename(part)+'.rels')


def resolve(part,target): return pp.normpath(pp.join(pp.dirname(part),target.lstrip('/') if not target.startswith('/') else '/'+target.lstrip('/'))).lstrip('/')


def ordered_slides(files):
    pres=ET.fromstring(files['ppt/presentation.xml'])
    rels={r.get('Id'):r for r in ET.fromstring(files['ppt/_rels/presentation.xml.rels'])}
    return [resolve('ppt/presentation.xml',rels[n.get('{'+R+'}id')].get('Target')) for n in pres.findall('p:sldIdLst/p:sldId',NS)]


def click_texts(slide_xml):
    """Read actual native click groups and their displayed text, not planned counts."""
    root=ET.fromstring(slide_xml);texts={}
    for shape in root.findall('.//p:spTree/*',NS):
        props=shape.find('.//p:cNvPr',NS)
        if props is not None:
            texts[props.get('id')]=''.join(
                t.text or '' for t in shape.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t'))
    groups=[]
    for node in root.findall('.//p:timing//p:cTn',NS):
        kind=node.get('nodeType')
        if kind not in ('clickEffect','withEffect'):continue
        if kind=='clickEffect':groups.append([])
        if not groups:continue
        for target in node.findall('.//p:spTgt',NS):
            value=texts.get(target.get('spid'),'').strip()
            if value and value not in groups[-1]:groups[-1].append(value)
    return groups


def compose(manifest, output):
    output=Path(output)
    if output.exists(): raise ValueError('Refusing to overwrite output')
    if not manifest['slides']: raise ValueError('No slides selected')
    decks={}
    for key,filename in manifest['decks'].items():
        with ZipFile(filename) as z: decks[key]={n:z.read(n) for n in z.namelist()}
    orders={k:ordered_slides(v) for k,v in decks.items()}
    mappings={k:{} for k in decks}
    selected=[]; ids=set()
    for i,item in enumerate(manifest['slides'],1):
        if item['id'] in ids: raise ValueError('Duplicate page ID')
        ids.add(item['id'])
        key=item['deck']; index=item['sourceSlide']
        if not isinstance(index,int) or index<1 or index>len(orders[key]): raise ValueError('Invalid source slide')
        old=orders[key][index-1]
        if old in mappings[key]: raise ValueError('Duplicate source slide; render separate instances instead')
        new=f'ppt/slides/slide{i}.xml';mappings[key][old]=new;selected.append((key,old,new))
    base_key=selected[0][0];base=decks[base_key]
    output_files={};ct=ET.Element('{'+CT+'}Types')
    defaults={};overrides={}
    for key,files in decks.items():
        types=ET.fromstring(files['[Content_Types].xml'])
        defaults[key]={e.get('Extension'):e.get('ContentType') for e in types if e.tag.endswith('Default')}
        overrides[key]={e.get('PartName').lstrip('/'):e.get('ContentType') for e in types if e.tag.endswith('Override')}
    ET.SubElement(ct,'{'+CT+'}Default',Extension='rels',ContentType='application/vnd.openxmlformats-package.relationships+xml')
    visited=set();master_parts=[];notes_parts=[]
    def clone(key,old):
        files=decks[key]
        if old not in files: raise ValueError(f'Broken relationship: {key}:{old}')
        mapping=mappings[key]
        if old not in mapping:
            mapping[old]=f'ppt/imports/d{list(decks).index(key)+1}/{old}'
        new=mapping[old]
        if (key,old) in visited:return new
        visited.add((key,old));output_files[new]=files[old]
        content_type=overrides[key].get(old,defaults[key].get(pp.splitext(old)[1][1:]))
        if not content_type:raise ValueError(f'Unknown content type: {old}')
        ET.SubElement(ct,'{'+CT+'}Override',PartName='/'+new,ContentType=content_type)
        if content_type.endswith('slideMaster+xml'):master_parts.append(new)
        if content_type.endswith('notesMaster+xml'):notes_parts.append(new)
        rp=relpath(old)
        if rp in files:
            relationships=ET.fromstring(files[rp])
            for relationship in relationships:
                if relationship.get('TargetMode')=='External':continue
                target=resolve(old,relationship.get('Target'))
                target_new=clone(key,target)
                relationship.set('Target',pp.relpath(target_new,pp.dirname(new)))
            output_files[relpath(new)]=xml(relationships)
        return new
    for key,old,new in selected:clone(key,old)
    pres=copy.deepcopy(ET.fromstring(base['ppt/presentation.xml']))
    # Root features referencing old relationship IDs must not survive remapping.
    allowed={'sldSz','notesSz','defaultTextStyle'}
    for child in list(pres):
        if child.tag.split('}')[-1] not in allowed:pres.remove(child)
    rootrels=ET.Element('{'+PKG+'}Relationships')
    def rel(target,kind):
        rid=f'rId{len(rootrels)+1}'
        ET.SubElement(rootrels,'{'+PKG+'}Relationship',Id=rid,Type=R+'/'+kind,Target=pp.relpath(target,'ppt'))
        return rid
    masters=ET.Element('{'+P+'}sldMasterIdLst')
    for i,part in enumerate(dict.fromkeys(master_parts)):
        ET.SubElement(masters,'{'+P+'}sldMasterId',id=str(2147483648+i),attrib={'{'+R+'}id':rel(part,'slideMaster')})
    pres.insert(0,masters)
    if notes_parts:
        notes=ET.Element('{'+P+'}notesMasterIdLst')
        for part in dict.fromkeys(notes_parts):ET.SubElement(notes,'{'+P+'}notesMasterId',{'{'+R+'}id':rel(part,'notesMaster')})
        pres.insert(1,notes)
    slides=ET.Element('{'+P+'}sldIdLst')
    for i,(_,_,new) in enumerate(selected):ET.SubElement(slides,'{'+P+'}sldId',id=str(256+i),attrib={'{'+R+'}id':rel(new,'slide')})
    pres.insert(2 if notes_parts else 1,slides)
    output_files['ppt/presentation.xml']=xml(pres)
    output_files['ppt/_rels/presentation.xml.rels']=xml(rootrels)
    ET.SubElement(ct,'{'+CT+'}Override',PartName='/ppt/presentation.xml',ContentType='application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml')
    package_rels=ET.Element('{'+PKG+'}Relationships')
    ET.SubElement(package_rels,'{'+PKG+'}Relationship',Id='rId1',Type=R+'/officeDocument',Target='ppt/presentation.xml')
    output_files['_rels/.rels']=xml(package_rels)
    output_files['[Content_Types].xml']=xml(ct)
    # Every internal relationship must resolve, and copied slide XML (incl timing) stays byte-identical.
    for key,old,new in selected:
        assert output_files[new]==decks[key][old]
    output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,'w',ZIP_DEFLATED) as z:
        for name,payload in output_files.items():z.writestr(name,payload)
    return [{**item,'page':i,'clickTexts':click_texts(output_files[f'ppt/slides/slide{i}.xml'])}
            for i,item in enumerate(manifest['slides'],1)]


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('output');p.add_argument('--mapping',required=True)
    a=p.parse_args();m=json.loads(Path(a.manifest).read_text())
    Path(a.mapping).write_text(json.dumps(compose(m,a.output),ensure_ascii=False,indent=2))
