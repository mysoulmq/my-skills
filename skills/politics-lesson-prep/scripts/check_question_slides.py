"""Verify required visible question text; notes never count as screen coverage."""
import argparse
import json
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from pptx_views import ordered_slides
from check_teaching import norm

A='{http://schemas.openxmlformats.org/drawingml/2006/main}'


def check(pptx,questions,mapping):
    with ZipFile(pptx) as z:files={n:z.read(n) for n in z.namelist()}
    order=ordered_slides(files);errors=[]
    for q in questions['questions']:
        grouped={};material_parts=[]
        for page in mapping:
            if page.get('questionId')!=q['id']:continue
            number=page['page'] if 'page' in page else page['sourceSlide']
            root=ET.fromstring(files[order[number-1]])
            text=''.join(t.text or '' for t in root.iter(A+'t'))
            grouped.setdefault(page['kind'],[]).append(norm(text))
            if q.get('totalScore') is not None and not any(float(v)==q['totalScore'] for v in re.findall(r'[（(]\s*(\d+(?:\.\d+)?)\s*分(?:[，,]\s*预测)?\s*[）)]',text)):
                errors.append(f'{q["id"]}: page {number} missing question total score')
            if page['kind']=='material':
                for shape in root.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}sp'):
                    props=shape.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr')
                    if props is not None and props.get('name','').startswith(q['id']+'-material-') and not props.get('name','').endswith('-title'):
                        material_parts.append(norm(''.join(t.text or '' for t in shape.iter(A+'t'))))
        if q.get('scoreStatus')=='predicted' and any('预测' not in t for texts in grouped.values() for t in texts):
            errors.append(f'{q["id"]}: predicted total lacks visible prediction label')
        all_text=''.join(t for texts in grouped.values() for t in texts)
        for field in ('material','prompt'):
            pool=''.join(material_parts) if field=='material' and material_parts else all_text
            if norm(q[field]) not in pool:errors.append(f'{q["id"]}: missing visible {field}')
        answers=''.join(grouped.get('answer',[]))
        for i,item in enumerate(q['answer']):
            for field in ('principle','application'):
                if norm(item[field]) not in answers:errors.append(f'{q["id"]}: answer {i+1} missing {field}')
        analysis=''.join(grouped.get('analysis',[]))
        if norm(q['task']) not in analysis:errors.append(f'{q["id"]}: missing task')
        for i,item in enumerate(q['analysis']):
            for field in ('evidence','principle'):
                if norm(item[field]) not in analysis:errors.append(f'{q["id"]}: analysis {i+1} missing {field}')
    return {'pass':not errors,'errors':errors}


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['pptx','questions','mapping']:p.add_argument(name)
    p.add_argument('--report');a=p.parse_args()
    result=check(a.pptx,json.loads(Path(a.questions).read_text()),json.loads(Path(a.mapping).read_text()))
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if a.report:Path(a.report).write_text(text)
    print(text);raise SystemExit(0 if result['pass'] else 1)
