"""Compile source-selected knowledge recall; answers may guide selection, source nodes supply text."""
import re

def norm(s):return re.sub(r'\s+','',str(s))

def source_key(source):
    if source.get('unitId'):return 'unit:'+source['unitId']
    return f"ppt:{source.get('deck')}:{source.get('page')}:{source.get('shapeId')}"


def recall_display_text(node, route):
    """Drop a reviewed orphan heading ordinal, never edit its source quote."""
    text=norm(node['text'])
    display=node.get('display',{})
    if not isinstance(display,dict) or set(display)-{'omitSourceNumber'}:
        raise ValueError('Unknown recall display transformation')
    omit=display.get('omitSourceNumber',False)
    if type(omit)!=bool:raise ValueError('omitSourceNumber must be boolean')
    if not omit:return text
    if route=='handout':
        if node.get('parentId') is not None:
            raise ValueError('Only a standalone handout heading can omit its source ordinal')
        prefix=r'^(?:[0-9]+[、．]|[0-9]+\.(?![0-9])|[一二三四五六七八九十百]+、|[（(](?:[0-9]+|[一二三四五六七八九十百]+)[）)])'
    elif route in ('outline-branch','outline-overview'):
        # Explicitly reviewed outline labels only; preserve knowledge titles,
        # parent/child structure, internal numbering and the original source.
        prefix=r'^第(?:[0-9]+|[一二三四五六七八九十百]+)(?:单元|课|框)'
    else:
        raise ValueError('Unsupported recall source route')
    result,count=re.subn(prefix,'',text,count=1)
    if not count or not result:raise ValueError('No removable source heading ordinal')
    return result

def compile_recall(record,catalog):
    route=record.get('route')
    if route not in ('handout','outline-branch','outline-overview'):
        raise ValueError('Missing explicit knowledge recall source route')
    if not record.get('scopeReason') or not record.get('sourceScope'):
        raise ValueError('Missing effective task scope and selection reason')
    nodes=record.get('nodes',[]);seen={};result=[]
    if not nodes:raise ValueError('Empty knowledge recall; do not fall back to analysis principles')
    for node in nodes:
        ident=node['id'];parent=node.get('parentId');source=node['source']
        if ident in seen or (parent is not None and parent not in seen):
            raise ValueError('Duplicate node or lost/out-of-order parent')
        kind='handout' if route=='handout' else 'outline'
        if source.get('kind')!=kind:raise ValueError('Source kind does not match recall route')
        actual=catalog.get(source_key(source))
        if actual is None or norm(source.get('quote',''))!=norm(actual):
            raise ValueError('Recall quote is not the complete registered source node')
        if norm(node.get('text',''))!=norm(actual):
            raise ValueError('Recall changed source wording; only whitespace reflow is allowed')
        display_text=recall_display_text(node,route)
        emph=node.get('emphasis',[])
        if not isinstance(emph,list) or any(not norm(s) or norm(s) not in display_text for s in emph):
            raise ValueError('Recall emphasis must be an exact source substring')
        depth=0 if parent is None else seen[parent]+1
        seen[ident]=depth
        result.append({**node,'sourceText':norm(node['text']),'text':display_text,'depth':depth,
                       'emphasis':[norm(s) for s in emph]})
    return result


def emphasis_spans(text,focus=(),bold=()):
    """Preserve every character while marking reviewed exact substrings.

    Consumers must write these styles to native runs and include bold in width
    measurement. An explicit empty list is valid after pedagogical review.
    """
    if any(not isinstance(w,str) or not w or w not in text for w in [*focus,*bold]):
        raise ValueError('Emphasis absent from actual display text')
    marks=[[False,False] for _ in text]
    for col,words in enumerate((focus,bold)):
        for word in words:
            start=0
            while (start:=text.find(word,start))>=0:
                for i in range(start,start+len(word)):marks[i][col]=True
                start+=len(word)
    result=[]
    for ch,(hi,heavy) in zip(text,marks):
        if result and (result[-1]['highlight'],result[-1]['bold'])==(hi,heavy):result[-1]['text']+=ch
        else:result.append({'text':ch,'highlight':hi,'bold':heavy})
    return result


def compile_analysis_emphasis(item):
    fields={'material':('evidenceDisplay','evidenceFocus'),
            'knowledge':('principleDisplay','principleFocus')}
    out={}
    if not item.get('visualReviewReason'):
        raise ValueError('Analysis visual emphasis not reviewed')
    for role,(body,focus) in fields.items():
        if role!='material' and focus not in item:raise ValueError('Missing reviewed '+focus+' (explicit [] allowed)')
        text=item.get(body,item.get('principle',''))
        # Material synopsis is intentionally unmarked, including legacy focus.
        out[role]=emphasis_spans(text,[] if role=='material' else item[focus])
    return out


def compile_answer_sections(answer):
    """Default teacher colors, no invented yellow; bold and yellow are independent."""
    # This helper compiles two prose roles only. Never silently discard original
    # score objects: scored answers need the existing score-aware native adapter.
    score_fields=('principleScore','principleScoreLabel','applicationScore',
                  'applicationScoreLabel','score','scoreLabel')
    if any(answer.get(key) is not None for key in score_fields):
        raise ValueError('Scored answer requires score-aware native adapter; preserve original green score runs')
    principle=answer['principle'];application=answer['application']
    pf=answer.get('principleFocus',[]);af=answer.get('applicationFocus',[])
    heavy=answer.get('applicationEmphasis',[])
    if pf or af:
        basis=answer.get('yellowBasis',{})
        if basis.get('kind') not in ('user-request','teacher-example') or not basis.get('reference'):
            raise ValueError('Answer yellow requires an explicit user or verified teacher example basis')
    if heavy and not answer.get('emphasisReason'):
        raise ValueError('Answer bold needs a concrete teaching reason; do not auto-copy yellow')
    emphasis_spans(principle,pf);emphasis_spans(application,af,heavy)
    return [{'text':principle,'bold':True,'color':'000000','focus':pf},
            {'text':application,'bold':False,'color':'00B0F0','focus':af,'emphasis':heavy}]
