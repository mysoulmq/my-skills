"""Compile source-backed teaching marks into editable presentation styles."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import sys

ROLES = {"topic-key", "knowledge-anchor", "analysis-axis", "definition-core",
         "logical-boundary", "mechanism", "conclusion", "methodology", "source-star"}
STYLE_KEYS = ("focus", "emphasis", "contrast")


def norm(text):
    return re.sub(r"\s", "", str(text))


def compile_marks(source, deck):
    units = {u["id"]: u["text"] for u in source["units"]}
    if len(units) != len(source["units"]):
        raise ValueError("Duplicate source IDs")
    result = deepcopy(deck)
    report = {"marks": [], "legacyUnexplained": [], "axisGroups": {},
              "scope": "Evidence and style checks only; independently review teaching reasons and logic."}

    def visible(obj):
        refs = set()
        if "segments" in obj:
            parts = ([obj["label"]] if obj.get("label") else []) + obj["segments"]
            words = []
            for part in parts:
                ref, quote = part.get("ref"), part.get("quote", "")
                if ref not in units or not norm(quote) or norm(quote) not in norm(units[ref]):
                    raise ValueError(f"Unsupported map excerpt: {ref}: {quote}")
                refs.add(ref)
                words.append(quote)
            # Separators are layout, not selectable teaching content.
            return "；".join(words), refs
        if obj.get("ref"):
            ref = obj["ref"]
            if ref not in units:
                raise ValueError(f"Unknown ref {ref}")
            text = obj.get("text", units[ref])
            if norm(text) != norm(units[ref]):
                raise ValueError(f"Text override changes source {ref}")
            return text, {ref}
        return obj.get("text", ""), refs

    def walk(obj, slide, page_type, path, region):
        if isinstance(obj, list):
            for i, value in enumerate(obj):
                walk(value, slide, page_type, f"{path}[{i}]", region)
            return
        if not isinstance(obj, dict):
            return
        marks = obj.get("marks", [])
        if not isinstance(marks, list):
            raise ValueError(f"{path}: marks must be an array")
        if marks or any(k in obj for k in STYLE_KEYS):
            target, allowed_refs = visible(obj)
            planned = {key: [] for key in STYLE_KEYS}
            for mark in marks:
                quote, role, reason = mark.get("quote"), mark.get("role"), mark.get("reason")
                if not isinstance(quote, str) or not norm(quote) or norm(quote) not in norm(target):
                    raise ValueError(f"{path}: mark must occur in visible text: {quote}")
                ref = mark.get("evidenceRef", obj.get("ref"))
                if ref not in units or (allowed_refs and ref not in allowed_refs) or norm(quote) not in norm(units[ref]):
                    raise ValueError(f"{path}: invalid source evidence for {quote}")
                if role not in ROLES:
                    raise ValueError(f"{path}: unknown teaching role {role}")
                if not isinstance(reason, str) or not reason.strip() or reason.strip(" 。.!！") in {"重要", "重点", "高亮", "强调", "便于记忆", "背诵重点"}:
                    raise ValueError(f"{path}: supply a concrete teaching reason")
                if role == "topic-key" and not (page_type == "knowledge-map" and region == "hierarchy"):
                    raise ValueError(f"{path}: topic-key is only for map hierarchy titles")
                if role == "source-star" and quote != "★":
                    raise ValueError(f"{path}: source-star can only select an original ★")
                if role == "analysis-axis":
                    group = mark.get("group")
                    if not isinstance(group, str) or not group.strip():
                        raise ValueError(f"{path}: analysis-axis needs its comparison group")
                    report["axisGroups"].setdefault(f"{slide}:{group}", []).append(quote)
                if role == "topic-key":
                    style = "contrast"
                elif role == "analysis-axis" or page_type == "knowledge-map":
                    style = "focus"
                elif role == "source-star":
                    style = "preserve"
                else:
                    style = "emphasis"
                if style != "preserve":
                    # Manual semantic line breaks must not silently defeat a mark.
                    pattern = r"\s*".join(re.escape(char) for char in norm(quote))
                    for match in re.finditer(pattern, target):
                        if match.group() not in planned[style]:
                            planned[style].append(match.group())
                report["marks"].append({"slide": slide, "path": path, "ref": ref,
                                        "quote": quote, "role": role, "style": style,
                                        "reason": reason, "group": mark.get("group")})
            for style in STYLE_KEYS:
                old = obj.get(style, [])
                if not isinstance(old, list) or any(not isinstance(q, str) or not norm(q) or norm(q) not in norm(target) for q in old):
                    raise ValueError(f"{path}: invalid legacy style phrases")
                for quote in old:
                    if quote not in planned[style]:
                        report["legacyUnexplained"].append({"slide": slide, "path": path,
                                                           "quote": quote, "style": style})
                values = list(dict.fromkeys(old + planned[style]))
                if values:
                    obj[style] = values
            # Detect overlapping ranges even if the two phrases differ in length.
            assigned = {}
            clean = norm(target)
            for style in STYLE_KEYS:
                for quote in obj.get(style, []):
                    q, start = norm(quote), 0
                    while True:
                        start = clean.find(q, start)
                        if start < 0:
                            break
                        for index in range(start, start + len(q)):
                            if index in assigned and assigned[index] != style:
                                raise ValueError(f"{path}: overlapping conflicting styles near {quote}")
                            assigned[index] = style
                        start += len(q)
        for key, value in list(obj.items()):
            if key in {"marks", *STYLE_KEYS, "_highlightPlan"}:
                continue
            child_region = region
            if page_type == "knowledge-map":
                if key == "leaves":
                    child_region = "leaf"
                elif key in {"root", "title"}:
                    child_region = "hierarchy"
            walk(value, slide, page_type, f"{path}.{key}", child_region)

    for index, slide in enumerate(result["slides"], 1):
        walk(slide, index, slide.get("type", "content"), f"slides[{index}]", "body")
    result["_highlightPlan"] = {"version": 1, "marks": len(report["marks"]),
                                 "legacyUnexplained": len(report["legacyUnexplained"])}
    report["semanticReviewRequired"] = True
    report["evidenceAndStylesPassed"] = True
    return result, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("deck")
    parser.add_argument("output")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    paths = [Path(p).resolve() for p in (args.source, args.deck, args.output, args.report)]
    created = []
    try:
        if len(set(paths)) != 4:
            raise ValueError("Source, deck, output, report must be different paths")
        if any(p.exists() or p.is_symlink() for p in paths[2:]):
            raise FileExistsError("Output or report exists; refusing overwrite")
        deck, report = compile_marks(json.loads(paths[0].read_text()), json.loads(paths[1].read_text()))
        for output, data in [(paths[2], deck), (paths[3], report)]:
            with output.open("x", encoding="utf-8") as stream:
                created.append(output)
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        for path in created:
            path.unlink(missing_ok=True)
        print(f"prepare_marks: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(deck["_highlightPlan"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
