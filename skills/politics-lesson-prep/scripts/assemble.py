"""Create three native PPTX views and a linked teacher plan from one sequence.

No semantic ordering is guessed: sequence is part of the reviewed teaching plan.
"""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile
from pptx_views import compose, ordered_slides
from check_teaching import check
from write_plan import write
from compact_notes import rewrite


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


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['knowledge_pptx','question_pptx','question_pages','questions','plan','sequence','output']:p.add_argument(name)
    a=p.parse_args();load=lambda f:json.loads(Path(f).read_text())
    plan=load(a.plan);result=check(load(a.questions),plan)
    if not result['pass']:raise ValueError(result['errors'])
    out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
    mappings={}
    for name,manifest in manifests(a.knowledge_pptx,a.question_pptx,load(a.question_pages),load(a.sequence),plan).items():
        mappings[name]=compose(manifest,out/(name+'.pptx'))
        rewrite(out/(name+'.pptx'),mappings[name],plan,out/(name+'.pptx'))
    # Keep build metadata private; finalization copies only the four artifacts.
    (out/'page-mapping.json').write_text(json.dumps(mappings,ensure_ascii=False,indent=2))
    write(plan,mappings['完整授课'],out/'授课方案.docx')
