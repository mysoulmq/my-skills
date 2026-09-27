"""Recognize standalone written-question requests, not quoted material or answers."""
import re

def is_written_prompt(value):
    value=re.sub(r'^\s*(?:[（(]\d+[)）]|\d+[.．、])\s*','',value).strip()
    return bool(re.match(r'^(?:结合|运用|请运用|根据|请结合).*(?:分析|说明|阐述|评析|评价|谈谈|谈一谈|回答|解释|论证|如何|为什么)',value))

def audit_paragraphs(doc, blocks, model, effective):
    """Check saved DOC properties against source semantics, not generator flags."""
    from docx.oxml.ns import qn
    from common import text,norm
    qmap={q['id']:q for q in model['questions']}
    prompts={norm(b['text']) for b in model['blocks'] if b['role']=='body'
             and qmap.get(b['qid'],{}).get('type')=='written'
             and b.get('kind')=='p' and is_written_prompt(b['text'])}
    errors=[];found=set()
    for e in blocks:
        if e.tag!=qn('w:p'):continue
        value=text(e);label=value[:30]
        if norm(value) in prompts:
            found.add(norm(value))
            if any(effective(r,e,doc,'b') not in ('1','true','on') for r in e.xpath('./w:r') if text(r).strip()):
                errors.append('综合题设问未全部加粗：'+label)
        if re.match(r'^\(\s*\)\d+\.',value) and value!=value.rstrip():
            errors.append('选择题题干末尾残留空白或制表符：'+label)
        if value.strip() and not e.xpath('.//w:drawing'):
            spacing=e.find('w:pPr/w:spacing',e.nsmap)
            if spacing is None or spacing.get(qn('w:lineRule'))!='exact' or spacing.get(qn('w:line'))!='320':
                errors.append('正文行距未固定为16pt：'+label)
    if found!=prompts:errors.append('综合题设问未能在最终文件中完整定位')
    return errors
