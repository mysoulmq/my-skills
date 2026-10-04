"""Editable pale background for the complete knowledge-recall area, not text highlighting."""
import math

P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
EMU=12700
FILL='EAF2F8'

def panel_bounds(boxes,padding=4):
    if not boxes or not math.isfinite(padding) or padding<0:
        raise ValueError('Recall background needs boxes and nonnegative padding')
    for box in boxes:
        if any(not math.isfinite(box[k]) for k in ('x','y','w','h')) or min(box['w'],box['h'])<=0:
            raise ValueError('Invalid recall background geometry')
    x=min(b['x'] for b in boxes)-padding;y=min(b['y'] for b in boxes)-padding
    right=max(b['x']+b['w'] for b in boxes)+padding
    bottom=max(b['y']+b['h'] for b in boxes)+padding
    return {'x':x,'y':y,'w':right-x,'h':bottom-y}

def add_recall_background(slide,boxes,shape_id=3900,name='knowledge-recall-background'):
    """Works with ElementTree or lxml; write behind native text and connectors."""
    bounds=panel_bounds(boxes)
    tree=slide.find('.//{'+P+'}spTree')
    if tree is None:raise ValueError('Slide has no native shape tree')
    if any(n.get('id')==str(shape_id) for n in tree.iter('{'+P+'}cNvPr')):
        raise ValueError('Recall background shape ID already exists')
    def sub(parent,namespace,tag,**attrs):
        child=parent.makeelement('{'+namespace+'}'+tag,{k:str(v) for k,v in attrs.items()})
        parent.append(child);return child
    sp=tree.makeelement('{'+P+'}sp',{})
    nv=sub(sp,P,'nvSpPr');sub(nv,P,'cNvPr',id=shape_id,name=name)
    sub(nv,P,'cNvSpPr');sub(nv,P,'nvPr')
    pr=sub(sp,P,'spPr');xf=sub(pr,A,'xfrm')
    sub(xf,A,'off',x=round(bounds['x']*EMU),y=round(bounds['y']*EMU))
    sub(xf,A,'ext',cx=round(bounds['w']*EMU),cy=round(bounds['h']*EMU))
    sub(sub(pr,A,'prstGeom',prst='rect'),A,'avLst')
    sub(sub(pr,A,'solidFill'),A,'srgbClr',val=FILL)
    sub(sub(pr,A,'ln'),A,'noFill')
    index=next((i for i,c in enumerate(tree) if c.tag not in ('{'+P+'}nvGrpSpPr','{'+P+'}grpSpPr')),len(tree))
    tree.insert(index,sp)
    return {'shapeId':shape_id,'fill':FILL,**bounds}

def shape_bounds(shape):
    xf=shape.find('{'+P+'}spPr/{'+A+'}xfrm')
    if xf is None:return None
    off=xf.find('{'+A+'}off');ext=xf.find('{'+A+'}ext')
    if off is None or ext is None:return None
    return tuple(int(e.get(k)) for e,k in ((off,'x'),(off,'y'),(ext,'cx'),(ext,'cy')))

def check_recall_background(root,node_shape_ids,background_id):
    errors=[];shapes={}
    tree=root.find('.//{'+P+'}spTree')
    if tree is None:return ['missing recall background shape tree']
    for i,shape in enumerate(tree):
        nv=shape.find('.//{'+P+'}cNvPr')
        if nv is not None:shapes[nv.get('id')]=(i,shape)
    entry=shapes.get(str(background_id))
    if entry is None:return ['missing complete recall background panel']
    order,panel=entry;bounds=shape_bounds(panel)
    fill=panel.find('{'+P+'}spPr/{'+A+'}solidFill/{'+A+'}srgbClr')
    if fill is None or fill.get('val','').upper()!=FILL or len(fill):
        errors.append('recall background must have the opaque pale native fill '+FILL)
    if bounds is None:return errors+['recall background geometry missing']
    x,y,w,h=bounds
    if min(w,h)<=0:errors.append('recall background has no area')
    for sid in node_shape_ids:
        entry=shapes.get(str(sid))
        if entry is None:continue  # Main recall gate reports the missing text.
        node_order,node=entry;box=shape_bounds(node)
        if node_order<=order:errors.append('recall background must be behind its text')
        if box is None:errors.append('recall node geometry missing');continue
        nx,ny,nw,nh=box
        if nx<x or ny<y or nx+nw>x+w or ny+nh>y+h:
            errors.append('recall background does not enclose all knowledge nodes')
    return errors
