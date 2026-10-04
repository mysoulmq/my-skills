"""Shared analysis display contract; native adapters must use these compiled strings.

Source anchors prove provenance; display anchors preserve reviewed expressions.
Neither check judges whether the material selection is pedagogically sound.
"""
import math
import re

def norm(x):
    return ''.join(str(x).split())


def without_source_number(text):
    """Remove one leading source list marker, never a number inside the content."""
    return re.sub(r'^\s*(?:[（(]\d+[）)]|[①-⑳]|\d+[、．]|\d+\.(?!\d))\s*', '', text)

def compile_display(item):
    if item.get('responseDisplay') or item.get('responseAnchor'):
        raise ValueError('Legacy response fields: review material selection and migrate to displayAnchors; do not auto-append an answer conclusion')
    material=item.get('evidenceDisplay','').strip()
    source=item.get('principle','').strip()
    knowledge=item.get('principleDisplay',source).strip()
    if not material or not source or not knowledge:
        raise ValueError('Missing material display or sourced knowledge proposition')
    anchors=item.get('displayAnchors',{})
    if not isinstance(anchors,dict):
        raise ValueError('Missing reviewed displayAnchors')
    for role,display in (('material',material),('knowledge',knowledge)):
        selected=anchors.get(role)
        if not isinstance(selected,list) or not selected or any(not isinstance(a,str) or not norm(a) for a in selected):
            raise ValueError(f'Missing reviewed {role} anchors; return to content review')
        if any(norm(a) not in norm(display) for a in selected):
            raise ValueError(f'Lost reviewed {role} expression during compression')
    return {'material':material,'knowledge':knowledge}


def compile_question(question):
    """Number paired teaching groups before pagination, independently of source IDs.

    Source citations are untouched. A group can contain multiple knowledge clauses;
    its internal hierarchy must already be reviewed, not inferred here.
    """
    result=[]
    for index,item in enumerate(question['analysis'],1):
        display=compile_display(item)
        result.append({role: f'{index}. '+without_source_number(text)
                       for role,text in display.items()})
    return result

def paginate(measured, body_capacity, knowledge_capacity, gap=0):
    """Pack complete semantic groups using measured heights in the same units.

Each entry: index, bodyHeight, knowledgeHeight. Paired columns share a row:
start both at the same y, advance by max(bodyHeight, knowledgeHeight) + gap.
No point-count threshold. Oversize groups must be reflowed explicitly, not shrunk.
"""
    if not measured: raise ValueError('No analysis groups')
    if any(not math.isfinite(x) or x<=0 for x in (body_capacity,knowledge_capacity)) or not math.isfinite(gap) or gap<0:
        raise ValueError('Invalid layout capacity')
    pages=[];current=[];used=0
    capacity=min(body_capacity,knowledge_capacity)
    for g in measured:
        bh,kh=g['bodyHeight'],g['knowledgeHeight']
        if any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in (bh,kh)):
            raise ValueError('Invalid measured height')
        height=max(bh,kh)
        if height>capacity:
            raise ValueError('Semantic group exceeds capacity; reflow the template region before export')
        if current and used+gap+height>capacity:
            pages.append(current);current=[];used=0
        if current:used+=gap
        current.append(g['index']);used+=height
    if current:pages.append(current)
    return pages


def fit_analysis_pages(indices, measure, *, base_font, min_font,
                       recall_top, recall_reserved_height, content_bottom,
                       region_gap=12, group_gap=12, recall_padding=6):
    """Fit consecutive paired groups, reserving the teacher's knowledge region first.

    measure(indices, font_pt) returns groups (paginate's measured entries) and
    recallHeight, including actual wrapping/line spacing/insets. Recall font is
    fixed by the adapter; only the two analysis columns use font_pt. Units: pt.
    Try at most 2pt reduction in 1pt steps; minimize pages, then prefer larger type.
    Returns page indices, chosen font and reserved geometry. No content rewriting.
    """
    values=(base_font,min_font,recall_top,recall_reserved_height,content_bottom,
            region_gap,group_gap,recall_padding)
    if any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in values):
        raise ValueError('Invalid fit geometry')
    if (not indices or len(set(indices))!=len(indices) or min_font<=0 or
        not 0<=base_font-min_font<=2 or recall_reserved_height<=0 or
        min(region_gap,group_gap,recall_padding)<0):
        raise ValueError('Invalid bounded font policy or analysis indices')
    fonts=[base_font-i for i in range(math.floor(base_font-min_font)+1)]
    if fonts[-1]!=min_font:fonts.append(min_font)
    candidates=[]
    for font in fonts:
        best={len(indices):[]}
        for start in range(len(indices)-1,-1,-1):
            options=[]
            for end in range(start+1,len(indices)+1):
                if end not in best:continue
                subset=list(indices[start:end]);m=measure(subset,font)
                rh=m['recallHeight'];groups=m['groups']
                if not isinstance(rh,(int,float)) or not math.isfinite(rh) or rh<=0:
                    raise ValueError('Invalid measured recall height')
                if [g['index'] for g in groups]!=subset:
                    raise ValueError('Measurement changed analysis order or coverage')
                recall_height=max(recall_reserved_height,rh+recall_padding)
                analysis_top=recall_top+recall_height+region_gap
                capacity=content_bottom-analysis_top
                if capacity<=0:continue
                # Validate measurements even when the group cannot fit.
                heights=[max(g['bodyHeight'],g['knowledgeHeight']) for g in groups]
                if any(not math.isfinite(v) or v<=0 for g in groups
                       for v in (g['bodyHeight'],g['knowledgeHeight'])):
                    raise ValueError('Invalid measured group height')
                if sum(heights)+group_gap*(len(groups)-1)>capacity:continue
                page={'indices':subset,'fontPt':font,'recallTop':recall_top,
                      'recallHeight':recall_height,'analysisTop':analysis_top,
                      'analysisCapacity':capacity}
                options.append([page]+best[end])
            if options:best[start]=min(options,key=lambda p:(len(p),-len(p[0]['indices'])))
        if 0 in best:candidates.append(best[0])
    if not candidates:
        raise ValueError('No readable paired layout fits; reflow complete semantic groups, never overlap or delete recall')
    return min(candidates,key=lambda p:(len(p),-p[0]['fontPt']))


def normalize_heading_dashes(shape):
    """Keep Chinese —— in one zero-spacing run with a continuous dash font.

    Accepts an lxml/ElementTree native shape. Only the two teaching headings are
    touched; preserve other text, paragraph properties and native geometry.
    Arial's em dash avoids the separated dash glyphs of some KaiTi fallbacks.
    Rendering on the target viewer remains part of template visual verification.
    """
    import copy
    A='{http://schemas.openxmlformats.org/drawingml/2006/main}'
    changed=0
    for p in shape.iter(A+'p'):
        text=''.join(t.text or '' for t in p.iter(A+'t'))
        match=re.fullmatch(r'(审题|审材料)\s*[-—–－―\s]+',text)
        if not match:continue
        runs=p.findall(A+'r')
        if not runs:continue
        pp=p.find(A+'pPr')
        if pp is None:
            pp=p.makeelement(A+'pPr',{});p.insert(0,pp)
        pp.set('algn','l')
        props=runs[0].find(A+'rPr')
        for r in list(p):
            if r.tag in (A+'r',A+'br',A+'fld'):p.remove(r)
        for value,is_dash in ((match[1],False),('——',True)):
            r=p.makeelement(A+'r',{});rp=copy.deepcopy(props) if props is not None else p.makeelement(A+'rPr',{})
            if is_dash:
                rp.set('spc','0');rp.set('kern','0')
                for tag in ('latin','ea','cs','sym'):
                    for old in list(rp.findall(A+tag)):rp.remove(old)
                for tag in ('latin','ea','cs'):
                    rp.append(p.makeelement(A+tag,{'typeface':'Arial'}))
            r.append(rp);t=p.makeelement(A+'t',{});t.text=value;r.append(t)
            # endParaRPr must remain last in the paragraph.
            end=p.find(A+'endParaRPr');p.insert(list(p).index(end) if end is not None else len(p),r)
        changed+=1
    return changed
