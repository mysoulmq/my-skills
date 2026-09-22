"""Structural checks complement, but do not replace, a teacher's semantic review."""
import argparse
import json
import re
from pathlib import Path

TEACHING = ('ask', 'expected', 'misconception', 'followup', 'explanation', 'check', 'transition')


def norm(text):
    return re.sub(r'\s+', '', str(text))


def check(questions, plan):
    errors = []
    for field in ('lesson','designRationale','preparation','goals','difficulties'):
        if not plan.get(field):errors.append(f'Plan missing {field}')
    ids = set()
    for q in questions['questions']:
        qid = q['id']
        if 'totalScore' in q:
            score=q['totalScore']
            if isinstance(score,bool) or not isinstance(score,(int,float)) or score<=0 or not q.get('totalScoreSource'):
                errors.append(f'{qid}: invalid totalScore or missing source')
            given=re.search(r'[（(]\s*(\d+(?:\.\d+)?)\s*分\s*[）)]',q.get('prompt',''))
            if given and float(given.group(1))!=score:errors.append(f'{qid}: conflicting total score')
        if qid in ids:
            errors.append(f'Duplicate question: {qid}')
        ids.add(qid)
        for field in ('material', 'prompt', 'referenceAnswer', 'scope', 'task', 'scoreBasis'):
            if not str(q.get(field, '')).strip():
                errors.append(f'{qid}: missing {field}')
        if not q.get('analysis') or not q.get('answer') or not q.get('knowledge'):
            errors.append(f'{qid}: incomplete reasoning or answer')
        for item in q.get('analysis', []):
            if not norm(item.get('evidence', '')) or norm(item['evidence']) not in norm(q['material']):
                errors.append(f'{qid}: evidence is not a contiguous material quote: {item.get("evidence")}')
            for field in ('principle', 'reason'):
                if not item.get(field): errors.append(f'{qid}: empty analysis {field}')
        for item in q.get('answer', []):
            if not item.get('principle') or not item.get('application'):
                errors.append(f'{qid}: incomplete answer point')
            if 'score' in item and (not isinstance(item['score'], (int, float)) or item['score'] <= 0):
                errors.append(f'{qid}: invalid score')
        for field in TEACHING:
            if not q.get('teaching', {}).get(field): errors.append(f'{qid}: missing teaching.{field}')
    covered = set()
    activities = set()
    for period in plan['periods']:
        for field in ('mainline','mustExplain','timeChoice'):
            if not period.get('quickCard',{}).get(field):errors.append(f'{period["title"]}: missing quickCard.{field}')
        if sum(a['minutes'] for a in period['activities']) != 40:
            errors.append(f'{period["title"]}: duration must total 40')
        for a in period['activities']:
            if a['id'] in activities: errors.append(f'Duplicate activity: {a["id"]}')
            activities.add(a['id'])
            if a['minutes'] <= 0: errors.append(f'{a["id"]}: nonpositive duration')
            for qid in a.get('questionIds', []):
                if qid not in ids: errors.append(f'{a["id"]}: unknown question {qid}')
                covered.add(qid)
            for field in TEACHING:
                if not a.get('teaching', {}).get(field): errors.append(f'{a["id"]}: missing teaching.{field}')
            for field in ('ask','explain','pitfall','followup','check','transition'):
                if not a.get('cue',{}).get(field):errors.append(f'{a["id"]}: missing cue.{field}')
    if ids - covered: errors.append(f'Questions absent from plan: {sorted(ids-covered)}')
    return {'pass': not errors, 'errors': errors}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('questions'); p.add_argument('plan'); p.add_argument('--report')
    a = p.parse_args()
    result = check(json.loads(Path(a.questions).read_text()), json.loads(Path(a.plan).read_text()))
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if a.report: Path(a.report).write_text(encoded)
    print(encoded)
    raise SystemExit(0 if result['pass'] else 1)
