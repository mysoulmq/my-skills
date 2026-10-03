"""Check source anchors for essay analysis; does not prove semantic entailment.

knowledge JSON: {units:[{id,text,page|locator,...}]}, reused from handout OCR.
Each analysis item supplies knowledgeRefs:[{unitId,quote}] and answerRefs:[1,...].
principle must quote those source units; material interpretation belongs in reason.
"""
import argparse
import json
import re
from pathlib import Path


def norm(value):
    return re.sub(r'\s+', '', str(value))


def check(data, source):
    errors = []
    units = {u['id']: u for u in source['units']}
    if len(units) != len(source['units']):
        errors.append('Duplicate knowledge unit IDs')
    if not data.get('questions'):
        errors.append('No questions supplied for source-backed analysis review')
    for q in data.get('questions', []):
        if not q.get('analysis') or not q.get('answer'):
            errors.append(q['id'] + ': missing analysis or answer points')
            continue
        if not norm(q.get('referenceAnswer', '')):
            errors.append(q['id'] + ': no reference answer; requires authored-answer review, not fabricated backtrace')
        covered = set()
        for i, item in enumerate(q.get('analysis', []), 1):
            label = f'{q["id"]}:analysis[{i}]'
            trace = item.get('referenceTrace', {})
            answer_quote = norm(trace.get('answerQuote', ''))
            if not answer_quote or answer_quote not in norm(q.get('referenceAnswer', '')):
                errors.append(label + ': missing/non-source reference answer quote')
            explanation = norm(q.get('referenceExplanation', ''))
            explanation_quote = norm(trace.get('explanationQuote', ''))
            if explanation:
                if trace.get('mode') != 'explanation-led' or not explanation_quote or explanation_quote not in explanation:
                    errors.append(label + ': trace must use the provided reference explanation')
            elif trace.get('mode') != 'answer-only' or explanation_quote:
                errors.append(label + ': absent explanation requires honest answer-only trace')
            quotes = item.get('evidenceQuotes') or [item.get('evidence', '')]
            if not quotes or any(not norm(v) or norm(v) not in norm(q['material']) for v in quotes):
                errors.append(label + ': evidence must quote original material')
            if not item.get('evidenceDisplay'):
                errors.append(label + ': missing classroom material excerpt')
            refs = item.get('knowledgeRefs', [])
            if not refs:
                errors.append(label + ': missing handout/textbook knowledge references')
            for ref in refs:
                unit = units.get(ref.get('unitId'))
                quote = norm(ref.get('quote', ''))
                if not unit or not quote or quote not in norm(unit['text']):
                    errors.append(label + ': knowledge quote does not match source unit')
                elif not (unit.get('page') or unit.get('locator')):
                    errors.append(label + ': source unit has no locator')
            # A classroom application cannot masquerade as the knowledge column.
            expected = ''.join(norm(r.get('quote', '')) for r in refs)
            if norm(item.get('principle', '')) != expected:
                errors.append(label + ': principle must preserve cited knowledge wording/order; put application in reason')
            links = item.get('answerRefs', [])
            if not links or any(type(v) is not int or not 1 <= v <= len(q['answer']) for v in links):
                errors.append(label + ': missing/invalid answer point references')
            else:
                covered.update(links)
        if covered != set(range(1, len(q['answer']) + 1)):
            errors.append(q['id'] + ': analysis does not cover every answer point')
    return errors


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('questions'); p.add_argument('knowledge'); p.add_argument('--report', required=True)
    a = p.parse_args()
    errors = check(json.loads(Path(a.questions).read_text()), json.loads(Path(a.knowledge).read_text()))
    Path(a.report).write_text(json.dumps({'passed': not errors, 'errors': errors,
        'scope': 'source anchors only; material selection, paraphrase fidelity and entailment require semantic review'}, ensure_ascii=False, indent=2))
    print('\n'.join(errors) if errors else 'Source anchors passed; semantic review still required')
    raise SystemExit(bool(errors))
