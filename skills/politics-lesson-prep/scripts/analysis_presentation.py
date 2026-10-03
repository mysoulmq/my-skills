"""Shared analysis display contract; native adapters must use these compiled strings.

Source anchors prove provenance; display anchors preserve reviewed expressions.
Neither check judges whether the material selection is pedagogically sound.
"""
import math

def norm(x):
    return ''.join(str(x).split())

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
