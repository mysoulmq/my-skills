from pathlib import Path
from docx import Document
from common import text, norm, image_hashes, digest
import re

STEM=re.compile(r'^\s*(\d+)[.．、]')
ANSWER=re.compile(r'[（(]\s*([A-DＡ-Ｄ](?:\s*[,，、]?\s*[A-DＡ-Ｄ])*)\s*[)）]\s*$')

def inspect(path):
    path=Path(path);d=Document(path);issues=[];warnings=[]
    # Unsupported rich structures must not be flattened silently.
    for tag in ['object','pict','txbxContent','altChunk','ins','del','sdt','footnoteReference','endnoteReference','sym']:
        if d._element.xpath(f'//w:{tag}'):issues.append(f'不支持的结构 w:{tag}，需要先人工规范化输入')
    if d._element.xpath('//m:oMath | //m:oMathPara | //w:fldSimple | //w:fldChar | //w:instrText'):issues.append('输入含公式或动态域，当前保存链路未验证，不能静默转换')
    if any(n.get('uri')!='http://schemas.openxmlformats.org/drawingml/2006/picture' for n in d._element.xpath('//a:graphicData')):issues.append('输入含未验证的图表或绘图对象，不能静默转换')
    if d._element.xpath('//a:blip[@r:link]'):issues.append('输入含外链图片，需先嵌入原件副本')
    if d._element.xpath('//wp:anchor'):issues.append('输入含浮动图片，需先规范为行内图片以保证图题关系')
    for r in d._element.xpath('//w:rPr/w:vanish'):
        if r.get('{'+r.nsmap['w']+'}val') not in ['0','false']:issues.append('输入含隐藏文字，需确认后处理');break
    body=[e for e in d._element.body if e.tag.rsplit('}',1)[-1] in ['p','tbl']]
    title=text(body[0]).strip() if body else ''
    if not title:issues.append('缺少可识别标题')
    qs=[];blocks=[];current=None;section='choice';in_answer=False
    for idx,e in enumerate(body[1:],1):
        t=text(e);clean=t.strip();kind=e.tag.rsplit('}',1)[-1]
        if re.match(r'^[一二三四五六七八九十]+[、．.]',clean) and ('题' in clean):
            section='choice' if '选择' in clean else 'written';current=None;in_answer=False
            blocks.append({'index':idx,'role':'section','text':t,'qid':None});continue
        m=STEM.match(t) if kind=='p' else None
        if m:
            number=int(m.group(1));current={'id':f'q{len(qs)+1:03d}','number':number,'type':section,'stem_index':idx,'answer':None,'indices':[]};qs.append(current);in_answer=False
            if section=='choice':
                am=ANSWER.search(t)
                if am:current['answer']=am.group(1).translate(str.maketrans('ＡＢＣＤ','ABCD')).replace(' ','')
            role='stem'
        elif current and current['type']=='choice' and ANSWER.fullmatch(clean):
            current['answer']=ANSWER.fullmatch(clean).group(1);role='answer_slot'
        elif clean.startswith(('【解析】','【答案】')):role='answer';in_answer=True
        elif in_answer:role='answer'
        else:role='body'
        if not current:
            if clean or image_hashes(e,d.part):issues.append(f'块{idx}无法归属题目: {clean[:35]}')
            continue
        if not clean and not image_hashes(e,d.part) and kind=='p':continue
        current['indices'].append(idx)
        blocks.append({'index':idx,'role':role,'text':t,'qid':current['id'],'kind':kind,'images':image_hashes(e,d.part)})
    # Some publisher files place the next question's cartoon before its question number.
    # Reattach only when the following stem explicitly references an image; otherwise block.
    for b in list(blocks):
        if b.get('images') and b['role']=='answer' and not b['text'].strip():
            pos=blocks.index(b)
            nxt=blocks[pos+1] if pos+1<len(blocks) else None
            if nxt and nxt['role']=='stem' and re.search('漫画|下图|图示|图中|绘画作品',nxt['text']):
                old=next(q for q in qs if q['id']==b['qid']);new=next(q for q in qs if q['id']==nxt['qid'])
                old['indices'].remove(b['index']);new['indices'].append(b['index'])
                b['qid']=new['id'];b['role']='body';b['attachment_reason']='图片独立段位于上一题解析后、下一题明确引用漫画；归属下一题并置于其题干后'
                blocks.pop(pos);blocks.insert(pos+1,b)
            else:issues.append(f"图片块{b['index']}位于解析边界，无法确定题目归属")
    if not qs:issues.append('没有识别出题目')
    numbers=[q['number'] for q in qs]
    if len(set(numbers))!=len(numbers):issues.append('题号重复，不能自动生成')
    if numbers!=list(range(1,len(numbers)+1)):issues.append('题号不连续，需要先确认编号')
    for q in qs:
        ab=[b for b in blocks if b['qid']==q['id'] and b['role']=='answer']
        if not ab:issues.append(f"第{q['number']}题缺少答案或解析")
        if q['type']=='choice':
            if not q['answer']:issues.append(f"第{q['number']}题缺少明确答案括号")
            optiontext='\n'.join(b['text'] for b in blocks if b['qid']==q['id'] and b['role']=='body')
            letters=re.findall(r'(?:^|\s)([A-D])[.．、]',optiontext)
            if letters!=['A','B','C','D']:issues.append(f"第{q['number']}题选项识别异常: {letters}")
            conclusion=re.findall(r'(?:故选|故答案选|故答案为)\s*([A-D])',''.join(b['text'] for b in ab))
            if conclusion and any(c not in (q['answer'] or '') for c in conclusion):
                warnings.append(f"第{q['number']}题括号答案{q['answer']}与解析结论{conclusion}不一致，需教研确认")
    return {'source':str(path.resolve()),'source_sha256':digest(path),'title':title,'questions':qs,'blocks':blocks,'errors':issues,'review_issues':warnings,'question_count':len(qs),'image_count':sum(len(b.get('images',[])) for b in blocks),'table_count':sum(b.get('kind')=='tbl' for b in blocks)}
