"""Keep circled choice statements intact, using a shared real tab stop per question."""
from copy import deepcopy
from functools import lru_cache
import re
from PIL import ImageFont
from docx.text.paragraph import Paragraph
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from common import text,norm,patch_text

MARKS='①②③④⑤⑥⑦⑧⑨⑩'

def point_ranges(value):
    matches=list(re.finditer('['+MARKS+']',value))
    if not matches or value[:matches[0].start()].strip():return None
    if re.search(r'(?:^|\s)[A-D][.．、]',value):return None
    out=[]
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(value)
        while end>m.start() and value[end-1].isspace():end-=1
        if end<=m.start()+1:return None
        out.append((m.start(),end,value[m.start():end]))
    return out

@lru_cache(maxsize=1)
def font():
    from fonts import resolve_fonts
    return ImageFont.truetype(resolve_fonts()['font_file'],size=1050)

def width(value):
    # Point content tabs are whitespace, not inherited publisher tab positions.
    return font().getlength(re.sub(r'\s',' ',value))/100

def plan_rows(items,available):
    widths=[width(s) for s in items];gap=14.0;safe=available-4
    pairs=[(i,i+1) for i in range(0,len(items)-1,2)]
    intervals=[(widths[a]+gap,safe-widths[b]) for a,b in pairs]
    candidates={safe/2}
    for lo,hi in intervals:
        if lo<=hi:candidates.update((lo,hi))
    column=min(candidates,key=lambda c:(-sum(lo<=c<=hi for lo,hi in intervals),abs(c-safe/2)))
    rows=[]
    for a in range(0,len(items),2):
        if a+1<len(items) and widths[a]+gap<=column<=safe-widths[a+1]:rows.append([a,a+1])
        else:
            rows.append([a])
            if a+1<len(items):rows.append([a+1])
    return rows,column

def format_points(doc,manifest):
    """Merge consecutive circled statement paragraphs, preserving run emphasis."""
    blocks=[e for e in doc._element.body if e.tag in (qn('w:p'),qn('w:tbl'))][2:]
    assert len(blocks)==len(manifest)
    output=[];i=0
    while i<len(manifest):
        m=manifest[i];e=blocks[i]
        eligible=lambda b,x: b['choice'] and b['role']=='body' and x.tag==qn('w:p') and point_ranges(text(x))
        if not eligible(m,e):output.append(m);i+=1;continue
        group=[];j=i
        while j<len(manifest) and manifest[j]['qid']==m['qid'] and eligible(manifest[j],blocks[j]):
            if manifest[j]['images']:raise ValueError('分点中含图片，需先明确分点图文排版')
            group.append(blocks[j]);j+=1
        pieces=[];items=[]
        for p in group:
            value=text(p)
            for start,end,item in point_ranges(value):
                piece=deepcopy(p);patch_text(piece,end,len(value),'');patch_text(piece,0,start,'')
                # Explicit inherited line breaks and tabs inside one point become spaces.
                for node in piece.xpath('.//w:br | .//w:cr | .//w:tab'):
                    if node.getparent().tag==qn('w:r'):
                        t=OxmlElement('w:t');t.text=' ';t.set(qn('xml:space'),'preserve');node.getparent().replace(node,t)
                pieces.append(piece);items.append(re.sub(r'\s',' ',item))
        if [s[0] for s in items]!=list(MARKS[:len(items)]):
            raise ValueError('选择题分点序号不连续或重复，不能猜测重排')
        paragraph=Paragraph(group[0],doc._body);left=paragraph.paragraph_format.left_indent.pt
        sec=doc.sections[0];available=(sec.page_width-sec.left_margin-sec.right_margin)/12700-left
        rows,column=plan_rows(items,available)
        merged=OxmlElement('w:p');pp=group[0].find(qn('w:pPr'))
        if pp is not None:merged.append(deepcopy(pp))
        par=Paragraph(merged,doc._body);pf=par.paragraph_format
        pf.tab_stops.clear_all();pf.tab_stops.add_tab_stop(Pt(left+column))
        pf.keep_with_next=Paragraph(group[-1],doc._body).paragraph_format.keep_with_next
        for ri,row in enumerate(rows):
            if ri:par.add_run().add_break()
            for ci,index in enumerate(row):
                if ci:par.add_run().add_tab()
                for node in pieces[index]:
                    if node.tag!=qn('w:pPr'):merged.append(deepcopy(node))
        group[0].addprevious(merged)
        for p in group:p.getparent().remove(p)
        record=dict(m);record.update(text=norm(text(merged)),point_items=items,point_rows=rows,point_column_pt=column)
        output.append(record);i=j
    return output
