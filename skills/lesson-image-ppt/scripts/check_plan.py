"""Check declared teaching groups against content-page placements before rendering."""
import argparse
import json
from pathlib import Path
from prepare_marks import navigation_reviews


def check(source, deck):
    units = {u['id']: u for u in source['units']}
    errors, placements = [], {}
    try:
        navigation_reviews(deck)
    except ValueError as exc:
        errors.append(str(exc))
    def walk(obj, slide, path, indentation=0):
        if isinstance(obj, str):
            if obj in units:
                placements.setdefault(obj, []).append((slide, path, indentation))
        elif isinstance(obj, list):
            for i, child in enumerate(obj):
                walk(child, slide, path + f'[{i}]')
        elif isinstance(obj, dict):
            if obj.get('ref'):
                walk(obj['ref'], slide, path, 64 if obj.get('bullet') else obj.get('indent', 0))
            else:
                for key in ('title', 'topic', 'root', 'items', 'rows'):
                    if key in obj:
                        walk(obj[key], slide, path + '.' + key)
    for i, slide in enumerate(deck['slides'], 1):
        if slide.get('type') != 'content':
            continue
        for key in ('title', 'topic'):
            if key in slide: walk(slide[key], i, key)
        for j, block in enumerate(slide.get('blocks', [])):
            walk(block, i, f'blocks[{j}]')
            if block.get('type') == 'paragraphs':
                for item in block.get('items', []):
                    ref = item if isinstance(item, str) else item.get('ref')
                    unit = units.get(ref, {})
                    if unit.get('kind') == 'heading' and unit.get('level') not in ('lesson', 'frame', 'topic', 'point', 'subpoint', 'document'):
                        errors.append(f'Page {i}: heading {ref} needs explicit semantic level; body placement must not demote headings')
    # Heading text appearing in the image does not establish its curriculum level.
    maps = [(i, slide) for i, slide in enumerate(deck['slides'], 1)
            if slide.get('type') in ('knowledge-map', 'overview')]
    if maps:
        outline = source.get('curriculumOutline', [])
        approved = {}
        for entry in outline:
            evidence = entry.get('evidence', {})
            frame, topics = entry.get('frameRef'), entry.get('topicRefs', [])
            if (entry.get('verified') is not True or not evidence.get('image')
                    or not evidence.get('region') or frame not in units
                    or frame in approved or not topics or len(topics) != len(set(topics))
                    or any(t not in units for t in topics)):
                errors.append('Invalid curriculumOutline: verified image evidence and unique frame/topic refs required')
                continue
            approved[frame] = topics
        if not approved:
            errors.append('Navigation requires image-verified curriculumOutline; handout headings are not automatically textbook topic titles')
        def full_ref(value):
            if isinstance(value, str):
                return value if value in units else None
            if isinstance(value, dict) and value.get('ref') in units:
                ref = value['ref']
                # Styling is allowed; replacing/truncating a curriculum title is not.
                norm = lambda t: ''.join(t.split())
                for field in ('text', 'quote'):
                    if field in value and norm(value[field]) != norm(units[ref]['text']):
                        return None
                return ref
            return None
        for page, slide in maps:
            if slide.get('type') == 'overview':
                errors.append(f'Page {page}: legacy overview must migrate to curriculum-verified knowledge-map')
                continue
            frames = []
            for group in slide.get('groups', []):
                frame = full_ref(group.get('title')); frames.append(frame)
                topics = [full_ref(t.get('title')) for t in group.get('topics', [])]
                if frame not in approved or topics != approved.get(frame):
                    errors.append(f'Page {page}: frame {frame} topic titles/order differ from verified curriculumOutline')
            if frames != list(approved):
                errors.append(f'Page {page}: frame titles/order differ from verified curriculumOutline')

    groups = source.get('knowledgeGroups', [])
    if not groups:
        errors.append('Declare source.knowledgeGroups before planning slides')
    owned = set()
    seen = set()
    for group in groups:
        gid = group.get('id')
        refs = group.get('members', [])
        if not gid or gid in seen or not refs or len(refs) != len(set(refs)) or any(r not in units for r in refs):
            errors.append(f'Invalid knowledge group: {gid}')
            continue
        if refs != sorted(refs, key=lambda r: list(units).index(r)):
            errors.append(f"{gid}: members not in source order")
        seen.add(gid); owned.update(refs)
        pages = {p for r in refs for p, _, _ in placements.get(r, [])}
        missing = [r for r in refs if not placements.get(r)]
        if missing: errors.append(f'{gid}: missing content placements {missing}')
        split = group.get("split", {})
        split_ok = (isinstance(split, dict) and isinstance(split.get("reason"), str) and bool(split["reason"].strip())
                    and isinstance(split.get("measuredHeight"), (int, float))
                    and isinstance(split.get("availableHeight"), (int, float))
                    and 0 < split["availableHeight"] < split["measuredHeight"])
        if len(pages) != 1 and not split_ok:
            errors.append(f'{gid}: knowledge group split across slides {sorted(pages)}; reorganize the complete group')
        heading = group.get('heading')
        if heading:
            if heading not in units:
                errors.append(f'{gid}: unknown heading {heading}')
            hp = {p for p, _, _ in placements.get(heading, [])}
            if not pages.issubset(hp) or hp - pages:
                errors.append(f'{gid}: heading separated from its content (heading {sorted(hp)}, content {sorted(pages)})')
        for siblings in group.get('parallelSets', []):
            if len(siblings) < 2 or any(r not in refs for r in siblings):
                errors.append(f'{gid}: invalid parallel set')
                continue
            styles = {indented for r in siblings for _, _, indented in placements.get(r, [])}
            if len(styles) > 1:
                errors.append(f'{gid}: parallel items mix parent and subordinate indentation: {siblings}')
    ungrouped = [u['id'] for u in source['units'] if u.get('kind', 'body') == 'body' and u['id'] not in owned]
    if ungrouped: errors.append(f'Body units missing knowledge groups: {ungrouped}')
    return {'passed': not errors, 'errors': errors, 'groups': len(groups),
            'scope': 'Checks declared semantic groups, not their correctness; review grouping against image before running.'}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('source'); ap.add_argument('deck'); ap.add_argument('--report', required=True)
    args = ap.parse_args()
    result = check(json.loads(Path(args.source).read_text()), json.loads(Path(args.deck).read_text()))
    Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result['passed'] else 1)
