"""Small routing contract for existing agent tools; does not call or switch models.

Record accepted executor arguments and returned identity, not agent self-reports.
"""
import argparse
import json
from pathlib import Path
POLICY=Path(__file__).resolve().parents[1]/'assets/model-routing.json'


def configuration(stage):
    return json.loads(POLICY.read_text())['stages'][stage].copy()


def request(stage, task_name, message):
    return dict(task_name=task_name,message=message,fork_turns='none',**configuration(stage))


def check(records):
    errors=[]
    if not records:errors.append("No executor records supplied")
    for r in records:
        if r.get('stage') not in json.loads(POLICY.read_text())['stages']:
            errors.append(f"Unknown routing stage: {r.get('stage')} (record repair as an operation on its original stage)")
            continue
        expected=configuration(r['stage'])
        accepted=r.get('acceptedRequest',{})
        for k,v in expected.items():
            if accepted.get(k)!=v:errors.append(f"{r['stage']}: executor {k} differs from policy")
        if accepted.get('fork_turns')!='none':errors.append(f"{r['stage']}: use explicit isolated dispatch")
        if not (r.get('executorResult',{}).get('agent_id') or r.get('executorResult',{}).get('task_name')):errors.append(f"{r['stage']}: missing executor-returned identity")
        if not r.get('evidencePath'):errors.append(f"{r['stage']}: missing dispatch evidence location")
        reported=r.get('reportedRuntime')
        if reported:
            for k,v in expected.items():
                if reported.get(k)!=v:errors.append(f"{r['stage']}: reported runtime {k} mismatch")
    return {'pass':not errors,'errors':errors,'scope':'Executor configuration consistency only; absent runtime metadata is not inferred'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage');p.add_argument('--task-name');p.add_argument('--message-file');p.add_argument('--check')
    a=p.parse_args()
    if a.check:
        result=check(json.loads(Path(a.check).read_text()));print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['pass'] else 1)
    if not all((a.stage,a.task_name,a.message_file)):p.error('request needs --stage, --task-name and --message-file')
    print(json.dumps(request(a.stage,a.task_name,Path(a.message_file).read_text()),ensure_ascii=False,indent=2))
