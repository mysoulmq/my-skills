"""Shared analysis display contract; native adapters must use these compiled strings.

Source anchors prove provenance; this module preserves the selected classroom link.
It does not judge whether the link is pedagogically sound.
"""
import math

def norm(x):
    return ''.join(str(x).split())

def compile_display(item):
    material=item.get('evidenceDisplay','').strip()
    response=item.get('responseDisplay','').strip()
    if response:
        material += '\n' + response
    # The native knowledge column must not silently replace the proposition with a tag.
    knowledge=item.get('principle','').strip()
    anchor=item.get('responseAnchor','').strip()
    if not material or not knowledge:
        raise ValueError('Missing material display or sourced knowledge proposition')
    if not anchor or norm(anchor) not in norm(material):
        raise ValueError('Missing visible material-to-question link; reason in private data is insufficient')
    return {'material':material,'knowledge':knowledge,'responseAnchor':anchor}

def paginate(measured, body_capacity, knowledge_capacity, gap=0):
    """Pack complete semantic groups using measured heights in the same units.

Each entry: index, bodyHeight (includes responseDisplay), knowledgeHeight.
No point-count threshold. Oversize groups must be reflowed explicitly, not shrunk.
"""
    if not measured: raise ValueError('No analysis groups')
    if any(not math.isfinite(x) or x<=0 for x in (body_capacity,knowledge_capacity)) or gap<0:
        raise ValueError('Invalid layout capacity')
    pages=[];current=[];body=knowledge=0
    for g in measured:
        bh,kh=g['bodyHeight'],g['knowledgeHeight']
        if any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in (bh,kh)):
            raise ValueError('Invalid measured height')
        if bh>body_capacity or kh>knowledge_capacity:
            raise ValueError('Semantic group exceeds capacity; reflow the template region before export')
        if current and (body+gap+bh>body_capacity or knowledge+gap+kh>knowledge_capacity):
            pages.append(current);current=[];body=knowledge=0
        if current:body+=gap;knowledge+=gap
        current.append(g['index']);body+=bh;knowledge+=kh
    if current:pages.append(current)
    return pages
