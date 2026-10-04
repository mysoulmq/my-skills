"""Write reviewed highlights to editable native PPT text, preserving line breaks."""
from knowledge_recall import emphasis_spans
from native_line_breaks import wrap_native_text
A='http://schemas.openxmlformats.org/drawingml/2006/main'
P='http://schemas.openxmlformats.org/presentationml/2006/main'

def write_role_paragraphs(shape, sections, width, measure, *, size=22,
                          font='Microsoft YaHei', line_spacing=1.22,
                          paragraph_gap=6, safety=2):
    """Write semantic blocks separately; soft wraps never merge principle/application.

    Each section has text, color, bold, focus (yellow) and emphasis (bold).
    measure(text, size, bold) must measure the actual font. Existing score runs
    belong with their owning section; do not infer section boundaries by color.
    Returns measured height and the exact lines written. All sections are placed
    in one native text box with paragraph breaks and native paragraph spacing.
    """
    import copy
    if not sections:raise ValueError('No semantic answer sections')
    paragraphs=[];height=0;all_lines=[]
    for index,section in enumerate(sections):
        text=section['text']
        if '\n' in text:raise ValueError('Pass semantic sections, not previous layout breaks')
        bold=bool(section.get('bold',False));flags=[]
        for span in emphasis_spans(text,section.get('focus',()),section.get('emphasis',())):
            flags.extend([bold or span['bold']]*len(span['text']))
        def measured_slice(value,start,end):
            total=0;pos=start
            while pos<end:
                stop=pos+1
                while stop<end and flags[stop]==flags[pos]:stop+=1
                total+=measure(value[pos:stop],size,flags[pos]);pos=stop
            return total
        lines=wrap_native_text(text,width,lambda s:measure(s,size,bold),safety,measured_slice)
        # Use the same measured lines, weight and font at export; no viewer wrap.
        temp=copy.deepcopy(shape)
        write_text(temp,lines,size,font,bold,section.get('color','000000'),
                   section.get('focus',()),section.get('emphasis',()),line_spacing)
        ps=list(temp.find('{'+P+'}txBody').findall('{'+A+'}p'))
        if index:
            pp=ps[0].find('{'+A+'}pPr')
            gap=pp.makeelement('{'+A+'}spcBef',{})
            gap.append(pp.makeelement('{'+A+'}spcPts',{'val':str(round(paragraph_gap*100))}));pp.append(gap)
            height+=paragraph_gap
        paragraphs.extend(ps);all_lines.append(lines);height+=len(lines)*size*line_spacing
    body=shape.find('{'+P+'}txBody')
    if body is None:
        body=shape.makeelement('{'+P+'}txBody',{});shape.append(body)
    for child in list(body):body.remove(child)
    bp=body.makeelement('{'+A+'}bodyPr',{'wrap':'none','lIns':'0','rIns':'0','tIns':'0','bIns':'0','anchor':'t'})
    bp.append(body.makeelement('{'+A+'}noAutofit',{}));body.append(bp)
    body.append(body.makeelement('{'+A+'}lstStyle',{}));body.extend(paragraphs)
    return {'height':height,'sectionLines':all_lines}

def write_text(shape,lines,size=16,font='Microsoft YaHei',bold=False,color='000000',focus=(),emphasis=(),line_spacing=1.22):
    def sub(parent,ns,name,**attrs):
        e=parent.makeelement('{'+ns+'}'+name,{k:str(v) for k,v in attrs.items()});parent.append(e);return e
    body=shape.find('{'+P+'}txBody')
    if body is None:body=sub(shape,P,'txBody')
    for c in list(body):body.remove(c)
    bp=sub(body,A,'bodyPr',wrap='none',lIns=0,rIns=0,tIns=0,bIns=0,anchor='t');sub(bp,A,'noAutofit');sub(body,A,'lstStyle')
    full=''.join(lines);chars=[]
    for span in emphasis_spans(full,focus,emphasis):
        chars.extend((c,span['highlight'],span['bold']) for c in span['text'])
    offset=0
    for line in lines:
        p=sub(body,A,'p');pp=sub(p,A,'pPr',algn='l',marL=0,indent=0)
        sub(sub(pp,A,'lnSpc'),A,'spcPts',val=round(size*line_spacing*100))
        runs=[]
        for c,hi,heavy in chars[offset:offset+len(line)]:
            if runs and runs[-1][1:]==[hi,heavy]:runs[-1][0]+=c
            else:runs.append([c,hi,heavy])
        offset+=len(line)
        for value,hi,heavy in runs:
            r=sub(p,A,'r');rp=sub(r,A,'rPr',sz=round(size*100),b=int(bold or heavy),lang='zh-CN')
            sub(sub(rp,A,'solidFill'),A,'srgbClr',val=color)
            if hi:sub(sub(rp,A,'highlight'),A,'srgbClr',val='FFFF00')
            for tag in ('latin','ea','cs'):sub(rp,A,tag,typeface=font)
            sub(r,A,'t').text=value
    normalize_native_dashes(shape)


def apply_reviewed_emphasis(shape,focus=(),emphasis=()):
    """Apply marks across existing native run/line boundaries; keep fonts/colors.

    Use on answer shapes with black principle/cyan application/green score runs.
    This does not reflow or change geometry; adding bold requires remeasurement.
    """
    import copy
    runs=[(p,r) for p in shape.iter('{'+A+'}p') for r in p.findall('{'+A+'}r')]
    full=''.join(''.join(t.text or '' for t in r.iter('{'+A+'}t')) for _,r in runs)
    flags=[]
    for span in emphasis_spans(full,focus,emphasis):
        flags.extend((span['highlight'],span['bold']) for _ in span['text'])
    offset=0
    for p,r in runs:
        value=''.join(t.text or '' for t in r.iter('{'+A+'}t'));segments=[]
        for c,(hi,heavy) in zip(value,flags[offset:offset+len(value)]):
            if segments and segments[-1][1:]==[hi,heavy]:segments[-1][0]+=c
            else:segments.append([c,hi,heavy])
        offset+=len(value);index=list(p).index(r);p.remove(r)
        for j,(text,hi,heavy) in enumerate(segments):
            nr=copy.deepcopy(r);rp=nr.find('{'+A+'}rPr')
            if rp is None:rp=nr.makeelement('{'+A+'}rPr',{});nr.insert(0,rp)
            if hi:
                for old in list(rp.findall('{'+A+'}highlight')):rp.remove(old)
                h=rp.makeelement('{'+A+'}highlight',{});h.append(rp.makeelement('{'+A+'}srgbClr',{'val':'FFFF00'}))
                # highlight precedes font children in CT_TextCharacterProperties.
                before=next((k for k,c in enumerate(rp) if c.tag in ('{'+A+'}latin','{'+A+'}ea','{'+A+'}cs','{'+A+'}sym')),len(rp));rp.insert(before,h)
            if heavy:rp.set('b','1')
            for old in list(nr.findall('{'+A+'}t')):nr.remove(old)
            t=nr.makeelement('{'+A+'}t',{});t.text=text;nr.append(t);p.insert(index+j,nr)
    normalize_native_dashes(shape)


def normalize_native_dashes(shape):
    """Apply continuous glyph styling to every Chinese double em dash, not labels only.

    Preserve source Unicode, color, bold and highlights. Does not change hyphenated
    words/numeric ranges. Handles the pair even across existing rich-text runs.
    """
    import copy,re
    changed=0
    for p in shape.iter('{'+A+'}p'):
        runs=p.findall('{'+A+'}r');values=[''.join(t.text or '' for t in r.iter('{'+A+'}t')) for r in runs]
        full=''.join(values);positions=set()
        for m in re.finditer('——',full):positions.update(range(m.start(),m.end()))
        offset=0
        for r,value in zip(runs,values):
            pieces=[]
            for i,c in enumerate(value):
                dash=offset+i in positions
                if pieces and pieces[-1][1]==dash:pieces[-1][0]+=c
                else:pieces.append([c,dash])
            offset+=len(value)
            if not any(d for _,d in pieces):continue
            index=list(p).index(r);p.remove(r)
            for j,(text,dash) in enumerate(pieces):
                nr=copy.deepcopy(r);rp=nr.find('{'+A+'}rPr')
                if rp is None:rp=nr.makeelement('{'+A+'}rPr',{});nr.insert(0,rp)
                if dash:
                    rp.set('spc','0');rp.set('kern','0')
                    for tag in ('latin','ea','cs','sym'):
                        for old in list(rp.findall('{'+A+'}'+tag)):rp.remove(old)
                    for tag in ('latin','ea','cs'):rp.append(rp.makeelement('{'+A+'}'+tag,{'typeface':'Arial'}))
                    changed+=1
                for old in list(nr.findall('{'+A+'}t')):nr.remove(old)
                t=nr.makeelement('{'+A+'}t',{});t.text=text;nr.append(t);p.insert(index+j,nr)
    return changed
