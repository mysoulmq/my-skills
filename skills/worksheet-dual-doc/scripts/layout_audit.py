"""Check visible glyph positions in the PDF rendered directly from the saved DOC.

This module deliberately does not import the generator's indentation constants.
The number-to-stem gap and continuation alignment are relational measurements.
"""
import re

def compact(s):return re.sub(r'\s+','',s)

def audit_question_layout(pdf,model,manifest):
    lines=[]
    for page_no,page in enumerate(pdf.pages,1):
        for line in page.extract_text_lines():
            chars=[c for c in line['chars'] if c['text'].strip()]
            if not chars:continue
            lines.append({'text':''.join(c['text'] for c in chars),'chars':chars,'page':page_no})
    questions={q['number']:q for q in model['questions'] if q['type']=='choice'}
    records=[];errors=[];seen=[]
    stems={b['qid']:b['text'] for b in manifest if b['role']=='stem' and b['choice']}
    for i,line in enumerate(lines):
        m=re.match(r'^\(\)(\d+)\.',line['text'])
        if not m:continue
        n=int(m[1]);seen.append(n)
        if n not in questions:errors.append(f'/第{n}题出现额外题号');continue
        chars=line['chars'];prefix_len=len(m[0]);rec={'number':n,'page':line['page']}
        if len(chars)<=prefix_len:
            errors.append(f'/第{n}题题号单独占行');continue
        gap=chars[prefix_len]['x0']-chars[prefix_len-1]['x1'];stem_x=chars[prefix_len]['x0']
        rec.update(gap_pt=round(gap,2),stem_x=round(stem_x,2),continuations_checked=0)
        # Opening CJK punctuation can optically hang left; positive gaps may not
        # be excused as punctuation. Reference number directly touches the stem.
        if gap>1.0 or gap < -3.6:errors.append(f'/第{n}题题号后间隔异常:{gap:.2f}pt')
        dot_end=chars[prefix_len-1]['x1']
        full=compact(stems[questions[n]['id']]);consumed=len(line['text'])
        if not full.startswith(line['text']):
            errors.append(f'/第{n}题无法将可见题干与原文逐行对应');records.append(rec);continue
        remaining=full[consumed:]
        for following in lines[i+1:]:
            if not remaining:break
            # Page headers and footers are not part of the question paragraph.
            if following['page']!=line['page'] and all(abs(c['size']-10.5)>0.2 for c in following['chars']):continue
            if not remaining.startswith(following['text']):
                errors.append(f'/第{n}题续行无法对应原文，需定位复核');break
            x=following['chars'][0]['x0'];delta=x-dot_end
            # First-character CJK opening punctuation may hang by ~3.2pt.
            tolerance=3.6 if following['text'][0] in '（“《「『【' else 1.0
            if abs(delta)>tolerance:errors.append(f'/第{n}题续行与题干起点偏移:{delta:.2f}pt')
            rec['continuations_checked']+=1;remaining=remaining[len(following['text']):]
        records.append(rec)
    if sorted(seen)!=sorted(questions):errors.append('/可见选择题题号缺失或重复')
    return {'errors':sorted(set(errors)),'questions':records}
