"""Locate the real dependency and record its existing version without editing it."""
import argparse
import hashlib
import json
from pathlib import Path

REQUIRED=('SKILL.md','scripts/graphics.mjs','scripts/render.mjs','scripts/check_plan.py','scripts/prepare_marks.py','scripts/add_reveals.py','scripts/check_pptx.py','scripts/finalize.mjs')


def resolve_dependency(explicit=None,workspace=None):
    candidates=[]
    if explicit:candidates.append(Path(explicit))
    if workspace:candidates.append(Path(workspace)/'.agents/skills/lesson-image-ppt')
    candidates.append(Path(__file__).resolve().parents[2]/'lesson-image-ppt')
    for candidate in candidates:
        if all((candidate/name).is_file() for name in REQUIRED):return candidate.resolve()
    raise FileNotFoundError('lesson-image-ppt with knowledge-group validation is required; install/update it before running')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dependency');p.add_argument('--workspace');p.add_argument('--record')
    a=p.parse_args();root=resolve_dependency(a.dependency,a.workspace)
    record={'dependency':str(root),'sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in REQUIRED}}
    if a.record:Path(a.record).write_text(json.dumps(record,ensure_ascii=False,indent=2))
    print(root)
