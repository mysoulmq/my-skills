"""Create three native PPTX views and a linked teacher plan from one sequence.

No semantic ordering is guessed: sequence is part of the reviewed teaching plan.
"""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile
from pptx_views import compose, ordered_slides
from check_teaching import check
from compact_notes import rewrite
from score_prediction import attach_notes
from collections import Counter


def require_source_inventory(registry, question_pages):
    """Compare the pre-selection inventory with rendered teaching pages."""
    rendered={p['questionId'] for p in question_pages if p.get('stage','teaching')=='teaching'}
    if registry is None:
        if question_pages: raise ValueError('Question delivery requires --source-registry from all original inputs')
        return
    expected={q['id'] for q in registry['questions']}
    if len(expected)!=len(registry['questions']):
        raise ValueError('Duplicate canonical question IDs in source inventory')
    if rendered!=expected:
        raise ValueError(f'Source inventory mismatch: missing={sorted(expected-rendered)}, unexpected={sorted(rendered-expected)}')
    originals=[r['id'] for r in registry['sourceRecords']]
    assigned=[rid for q in registry['questions'] for rid in q.get('sourceRecords',[])]
    if not originals or len(set(originals))!=len(originals):
        raise ValueError('Source inventory must contain nonempty, unique original records')
    if Counter(originals)!=Counter(assigned):
        raise ValueError('Every original source record must be assigned exactly once before assembly')


def manifests(knowledge_pptx, question_pptx, question_pages, sequence, plan):
    total=0
    if knowledge_pptx!='-':
        with ZipFile(knowledge_pptx) as z:
            total=len(ordered_slides({n:z.read(n) for n in z.namelist()}))
    if total and (not sequence or sequence[0].get('knowledgePage')!=1):
        raise ValueError('Complete lesson must open with the knowledge overview mind map (knowledgePage 1), before diagnostic questions')
    known={a['id'] for p in plan['periods'] for a in p['activities']}
    pages=[];knowledge=[];selected=set()
    allq={(p['questionId'],p.get('stage','teaching')) for p in question_pages}
    for entry in sequence:
        acts=entry['activityIds']
        if not acts or set(acts)-known:raise ValueError('Missing or unknown activity IDs')
        if 'knowledgePage' in entry:
            number=entry['knowledgePage'];knowledge.append(number)
            pages.append({'id':f'knowledge-{number}','deck':'knowledge','sourceSlide':number,'activityIds':acts,'kind':'knowledge','clicks':entry.get('clicks',[])})
        else:
            qid=entry['questionId']
            stage=entry.get('stage','teaching');key=(qid,stage)
            if key in selected or key not in allq:raise ValueError('Duplicate or unknown question stage')
            selected.add(key)
            pages.extend({**page,'deck':'questions','activityIds':acts} for page in question_pages if page['questionId']==qid and page.get('stage','teaching')==stage)
    if knowledge!=list(range(1,total+1)):raise ValueError('Knowledge pages must be complete and remain in original order')
    if selected!=allq:raise ValueError('Questions missing from teaching sequence')
    covered={a for p in pages for a in p['activityIds']}
    if known-covered:raise ValueError(f'Activities without pages: {known-covered}')
    if not pages:raise ValueError('No teaching pages')
    decks={k:str(Path(v).resolve()) for k,v in [('knowledge',knowledge_pptx),('questions',question_pptx)] if v!='-'}
    result={}
    for name in ['完整授课','讲义部分','大题部分']:
        selected_pages=[p for p in pages if name=='完整授课' or (p['deck']=='knowledge')==(name=='讲义部分')]
        if selected_pages:
            used={p['deck'] for p in selected_pages}
            if used-set(decks):raise ValueError('Required source deck missing')
            result[name]={'decks':{k:v for k,v in decks.items() if k in used},'slides':selected_pages}
    return result


def argument_parser():
    p=argparse.ArgumentParser()
    for name in ['knowledge_pptx','question_pptx','question_pages','questions','plan','sequence','output']:p.add_argument(name)
    p.add_argument('--with-docx',action='store_true',help='Export Word only when explicitly requested')
    p.add_argument('--source-registry',help='Pre-selection sourceRecords and all canonical questions; required when question pages exist')
    return p


if __name__=='__main__':
    a=argument_parser().parse_args();load=lambda f:json.loads(Path(f).read_text())
    from check_choice_reveals import check as check_choices
    from check_source_delivery import check as check_sources
    question_pages=load(a.question_pages)
    registry=load(a.source_registry) if a.source_registry else None
    require_source_inventory(registry,question_pages)
    if a.question_pptx!='-':
        visibility=check_choices(a.question_pptx)
        if not visibility['pass']:raise ValueError(visibility['errors'])
    plan=load(a.plan)
    if a.with_docx and plan.get('mode')=='ppt-support':
        raise ValueError('Explicit Word export requires the full document plan fields; expand the shared plan first')
    result=check(load(a.questions),plan)
    if not result['pass']:raise ValueError(result['errors'])
    out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
    mappings={}
    for name,manifest in manifests(a.knowledge_pptx,a.question_pptx,question_pages,load(a.sequence),plan).items():
        mappings[name]=compose(manifest,out/(name+'.pptx'))
        attach_notes(plan,load(a.questions),mappings[name])
        rewrite(out/(name+'.pptx'),mappings[name],plan,out/(name+'.pptx'))
        visibility=check_choices(out/(name+'.pptx'))
        if not visibility['pass']:raise ValueError(visibility['errors'])
        if registry is not None and any(p.get('questionId') for p in mappings[name]):
            coverage=check_sources(out/(name+'.pptx'),registry,mappings[name])
            (out/(name+'-source-delivery.json')).write_text(json.dumps(coverage,ensure_ascii=False,indent=2))
            if not coverage['pass']:raise ValueError(coverage['errors'])
    # Build metadata is private; default deliverables are the available PPT views.
    (out/'page-mapping.json').write_text(json.dumps(mappings,ensure_ascii=False,indent=2))
    if a.with_docx:
        from write_plan import write
        write(plan,mappings['完整授课'],out/'授课方案.docx')
