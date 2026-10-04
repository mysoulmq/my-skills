"""Native editable recall-node layout inside the teacher's reserved region.

Returns source-linked text boxes; the adapter writes native text/shape objects,
never a bitmap. measure(text, font_pt, bold) uses the actual installed font.
"""
from native_line_breaks import wrap_native_text

def fit_recall(nodes,route,x,y,width,measure,max_height,*,base_font=13.5,min_font=12):
    """Reserve room for analysis before choosing a bounded recall-only profile.

    Sizes are points on a 960x540 canvas; callers scale for other slide sizes.
    Returns fits=False at the readable floor: paginate, never delete source nodes.
    """
    if max_height<=0 or min_font<=0 or base_font<min_font:
        raise ValueError('Invalid recall capacity or font bounds')
    profiles=[(base_font,1.22,4,4)]
    size=base_font
    while size>=min_font:
        profiles.append((size,1.10,2,1));size=round(size-.5,2)
    if profiles[-1][0]!=min_font:profiles.append((min_font,1.10,2,1))
    for size,spacing,gap,padding in profiles:
        result=plan_recall(nodes,route,x,y,width,measure,size,spacing,gap,padding)
        result['profile']={'fontPt':size,'lineSpacing':spacing,'nodeGapPt':gap,'nodePaddingPt':padding}
        result['fits']=result['height']<=max_height
        if result['fits']:return result
    return result

def plan_recall(nodes,route,x,y,width,measure,font=14,line_spacing=1.22,gap=4,node_padding=4):
    if not nodes:raise ValueError('No compiled recall nodes')
    children={n['id']:[] for n in nodes};byid={n['id']:n for n in nodes}
    roots=[]
    for n in nodes:
        if n.get('parentId') is None:roots.append(n['id'])
        else:children[n['parentId']].append(n['id'])
    def box(n,bx,by,bw,bold):
        lines=wrap_native_text(n['text'],bw,lambda s:measure(s,font,bold),safety=4)
        h=len(lines)*font*line_spacing+node_padding
        return {'nodeId':n['id'],'parentId':n.get('parentId'),'text':n['text'],
                'lines':lines,'x':bx,'y':by,'w':bw,'h':h,'fontPt':font,
                'bold':bold,'emphasis':n.get('emphasis',[]),'depth':n['depth'],
                'lineSpacing':line_spacing}
    result=[]
    if route=='handout':
        cy=y
        for n in nodes:
            indent=min(n['depth'],2)*8
            b=box(n,x+indent,cy,width-indent,bool(children[n['id']]))
            result.append(b);cy+=b['h']+gap
        return {'boxes':result,'height':cy-y-gap,'connectors':[]}
    maxdepth=max(n['depth'] for n in nodes)
    if maxdepth>2:raise ValueError('Recall framework exceeds chosen depth; return to scope selection')
    fractions=[.29,.71] if maxdepth==1 else [.18,.29,.53]
    widths=[width*f-12 for f in fractions];starts=[x]
    for f in fractions[:-1]:starts.append(starts[-1]+width*f)
    def subtree(ident,top):
        n=byid[ident];depth=n['depth'];b=box(n,starts[depth],top,widths[depth],True)
        childtop=top;sub=[];links=[]
        for child in children[ident]:
            childboxes,ch,cl=subtree(child,childtop);sub+=childboxes;links+=cl;childtop+=ch+gap
        h=max(b['h'],childtop-top-gap if sub else 0)
        b['y']=top+(h-b['h'])/2
        for child in children[ident]:
            c=next(v for v in sub if v['nodeId']==child)
            links.append({'from':ident,'to':child,'x1':b['x']+b['w']+2,'y1':b['y']+b['h']/2,
                          'x2':c['x']-3,'y2':c['y']+c['h']/2})
        return [b]+sub,h,links
    cy=y;links=[]
    for ident in roots:
        bs,h,ls=subtree(ident,cy);result+=bs;links+=ls;cy+=h+gap
    return {'boxes':result,'height':cy-y-gap,'connectors':links}
