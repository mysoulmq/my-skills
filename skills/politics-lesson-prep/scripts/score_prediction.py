"""Validate model-proposed score estimates; never infer grading from answer count."""
import math
import re

def validate(q):
    errors=[];qid=q.get('id','?')
    if q.get('scoreStatus','provided') not in ('provided','predicted'):
        return [f'{qid}: invalid scoreStatus']
    if q.get('scoreStatus')!='predicted':return errors
    p=q.get('scorePrediction',{})
    if re.search(r'[（(]\s*\d+(?:\.\d+)?\s*分\s*[）)]',q.get('prompt','')):
        errors.append(f'{qid}: source prompt already has a score; preserve it as provided')
    for field in ('basis','referencePattern','note'):
        if not isinstance(p.get(field),str) or not p[field].strip():errors.append(f'{qid}: missing scorePrediction.{field}')
    if len(p.get('note',''))>35 or '\n' in p.get('note',''):errors.append(f'{qid}: prediction note must be a single line <=35 characters')
    if '预测' not in p.get('note',''):errors.append(f'{qid}: prediction note must identify prediction')
    if p.get('confidence') not in ('high','medium','low'):errors.append(f'{qid}: invalid prediction confidence')
    units=p.get('units',[]);seen=set();total=0
    if not units:errors.append(f'{qid}: missing scoring units')
    for u in units:
        if not u.get('label') or not u.get('reason'):errors.append(f'{qid}: scoring unit needs rationale')
        score=u.get('score')
        if isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score) or score<=0:
            errors.append(f'{qid}: invalid predicted unit score');continue
        total+=score
        indices=u.get('answerIndices',[])
        if not indices:errors.append(f'{qid}: scoring unit missing answer links')
        for i in indices:
            if not isinstance(i,int) or isinstance(i,bool) or i<0 or i>=len(q.get('answer',[])):
                errors.append(f'{qid}: invalid answer index in scoring unit')
            elif i in seen:errors.append(f'{qid}: repeated answer credit; merge overlapping units')
            seen.add(i)
    if total!=q.get('totalScore'):errors.append(f'{qid}: predicted units do not sum to totalScore')
    if seen!=set(range(len(q.get('answer',[])))):errors.append(f'{qid}: prediction must account for every answer point, grouping overlaps')
    return errors

def attach_notes(plan,questions,mapping):
    """One short prediction note on the first actual page of each question."""
    notes=plan.setdefault('scoreNotesByPage',{})
    for q in questions['questions']:
        if q.get('scoreStatus')!='predicted':continue
        errors=validate(q)
        if errors:raise ValueError(errors)
        page=next((p for p in mapping if p.get('questionId')==q['id']),None)
        if page:notes[page['id']]=q['scorePrediction']['note']
