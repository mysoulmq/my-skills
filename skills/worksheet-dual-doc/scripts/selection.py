"""Source labels and explicitly authorized Zhejiang exam filtering."""
from copy import deepcopy
import re
from inspect_input import STEM

# Restrict to a source prefix. A date in prose (e.g. 2026年是...) is not a source.
EXAM=r'(?:高考|选考|联考|模拟|[一二三四五六七八九十]模|阶段检测|期中考试|期末考试)'
LABEL=re.compile(r'^\s*[（(]?\s*((?:\d{4}|\d{2}[-－]\d{2})\s*[·•]\s*[^。，“”！？?\n（）()]{1,32}?'+EXAM+r')\s*[）)]?')

def source_label(stem):
    n=STEM.match(stem)
    if not n:return None
    m=LABEL.match(stem[n.end():])
    if m:return {'text':m[1].strip(),'start':n.end()+m.start(),'end':n.end()+m.end()}
    if re.match(r'\s*[（(]?\s*\d{4}\s*[·•]',stem[n.end():]):
        raise ValueError('无法可靠划分题源与正文:'+stem[:65])
    return None

def is_zhejiang(label):
    return bool(re.search(r'浙江\s*(?:[·•]\s*)?(?:\d{1,2}\s*月\s*)?选考',label or ''))

def select(raw):
    model=deepcopy(raw);removed=[];deleted_ids=set();choice_deleted=0
    for q in model['questions']:
        stem=next(b['text'] for b in model['blocks'] if b['qid']==q['id'] and b['role']=='stem')
        label=source_label(stem);q['source_number']=q['number'];q['source_label']=label
        if label and is_zhejiang(label['text']):
            removed.append({'qid':q['id'],'source_number':q['number'],'type':q['type'],'source_label':label['text'],'stem_excerpt':stem[:180],'indices':q['indices'],'action':'删除并前移编号' if q['type']=='choice' else '保留原题号空位','output_number':None if q['type']=='choice' else q['number']})
            if q['type']=='choice':deleted_ids.add(q['id']);choice_deleted+=1
            else:q['placeholder']=True
        elif q['type']=='choice' or not q.get('placeholder'):
            q['number']-=choice_deleted
    model['questions']=[q for q in model['questions'] if q['id'] not in deleted_ids]
    placeholder_ids={q['id'] for q in model['questions'] if q.get('placeholder')}
    kept=[]
    for b in model['blocks']:
        if b['qid'] in deleted_ids:continue
        if b['qid'] in placeholder_ids:
            if b['role']!='stem':continue
            b['role']='placeholder';b['images']=[];b['kind']='p'
        kept.append(b)
    # Recalculate section labels from explicit per-question scores only.
    for i,b in enumerate(kept):
        if b['role']!='section':continue
        stop=next((j for j in range(i+1,len(kept)) if kept[j]['role']=='section'),len(kept))
        ids={x['qid'] for x in kept[i+1:stop] if x['qid']}
        qs=[q for q in model['questions'] if q['id'] in ids]
        if not qs:b['drop_empty_section']=True;continue
        if all(q.get('placeholder') for q in qs):
            b['display_text']=re.sub(r'[（(].*?[)）]','',b['text']).strip();b['reserve_page']=True
        elif all(q['type']=='choice' for q in qs):
            t=re.sub(r'本大题共\s*\d+\s*小题',f'本大题共{len(qs)}小题',b['text'])
            per=re.search(r'每小题\s*(\d+(?:\.\d+)?)\s*分',t)
            if per:t=re.sub(r'共\s*\d+(?:\.\d+)?\s*分',f'共{len(qs)*float(per[1]):g}分',t)
            b['display_text']=t
    kept=[b for b in kept if not b.get('drop_empty_section')]
    model['blocks']=kept;model['removed_questions']=removed;model['source_question_count']=raw['question_count']
    model['question_count']=len(model['questions']);model['image_count']=sum(len(b.get('images',[])) for b in kept);model['table_count']=sum(b.get('kind')=='tbl' for b in kept)
    model['number_mapping']=[{'source_number':q['source_number'],'output_number':q['number'],'placeholder':q.get('placeholder',False)} for q in model['questions']]
    return model
