"""Add native, click-triggered Appear effects without rewriting slide content.

Only stdlib is used. Existing ZIP entry payloads remain byte-identical except for
inserting one p:timing fragment in each selected slide. Text, shapes, geometry,
relationships, and existing animations on unselected slides are never rewritten.
"""

import argparse
import hashlib
import json
from pathlib import Path
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
from xml.parsers import expat
from zipfile import ZipFile


P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_R = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"p": P, "r": R}
ET.register_namespace("p", P)


def _element(parent, tag, **attrs):
    return ET.SubElement(parent, f"{{{P}}}{tag}", {k: str(v) for k, v in attrs.items()})


def _condition(parent, delay):
    _element(_element(parent, "stCondLst"), "cond", delay=delay)


def _timing(steps):
    """Match the native WPS/PowerPoint Appear hierarchy, one click per step."""
    root = ET.Element(f"{{{P}}}timing")
    counter = 0

    def clock(parent, **attrs):
        nonlocal counter
        counter += 1
        return _element(parent, "cTn", id=counter, **attrs)

    tree = _element(root, "tnLst")
    master = clock(_element(tree, "par"), dur="indefinite", restart="never", nodeType="tmRoot")
    sequence = _element(_element(master, "childTnLst"), "seq", concurrent="1", nextAc="seek")
    main = clock(sequence, dur="indefinite", nodeType="mainSeq")
    clicks = _element(main, "childTnLst")
    for step in steps:
        click = clock(_element(clicks, "par"), fill="hold")
        _condition(click, "indefinite")
        group = clock(_element(_element(click, "childTnLst"), "par"), fill="hold")
        _condition(group, "0")
        effects = _element(group, "childTnLst")
        for index, target in enumerate(step):
            effect = clock(_element(effects, "par"), presetID="1", presetClass="entr",
                           presetSubtype="0", fill="hold", grpId="0",
                           nodeType="clickEffect" if index == 0 else "withEffect")
            _condition(effect, "0")
            setter = _element(_element(effect, "childTnLst"), "set")
            behavior = _element(setter, "cBhvr")
            action = clock(behavior, dur="1", fill="hold")
            _condition(action, "0")
            _element(_element(behavior, "tgtEl"), "spTgt", spid=target["id"])
            _element(_element(behavior, "attrNameLst"), "attrName").text = "style.visibility"
            _element(_element(setter, "to"), "strVal", val="visible")
    for name, event in [("prevCondLst", "onPrev"), ("nextCondLst", "onNext")]:
        condition = _element(_element(sequence, name), "cond", evt=event, delay="0")
        _element(_element(condition, "tgtEl"), "sldTgt")
    # Text shapes use a paragraph-build declaration, matching native Appear.
    text_targets = [target for step in steps for target in step if target["type"] == "sp"]
    if text_targets:
        builds = _element(root, "bldLst")
        for target in text_targets:
            _element(builds, "bldP", spid=target["id"], grpId="0")
    return ET.tostring(root, encoding="utf-8")


def _insert_timing(original, fragment):
    """Locate a schema-valid insertion position without serializing the slide."""
    if original.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise ValueError("UTF-16 slide XML is unsupported; no input bytes were changed")
    declaration = re.match(br"(?:\xef\xbb\xbf)?<\?xml[^?]*encoding\s*=\s*['\"]([^'\"]+)", original)
    if declaration and declaration.group(1).lower() not in (b"utf-8", b"utf8", b"us-ascii", b"ascii"):
        raise ValueError("Only UTF-8 slide XML is supported")
    parser = expat.ParserCreate(namespace_separator="}")
    depth = 0
    before_extension = None
    root_end = None

    def start(name, attrs):
        nonlocal depth, before_extension
        depth += 1
        if depth == 1 and name != f"{P}}}sld":
            raise ValueError("Expected a PresentationML slide root")
        if depth == 2 and name == f"{P}}}extLst":
            before_extension = parser.CurrentByteIndex

    def end(name):
        nonlocal depth, root_end
        if depth == 1:
            root_end = parser.CurrentByteIndex
        depth -= 1

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.Parse(original, True)
    position = before_extension if before_extension is not None else root_end
    if position is None or (before_extension is None and original[position:position + 2] != b"</"):
        raise ValueError("Cannot safely locate the slide closing tag")
    result = original[:position] + fragment + original[position:]
    ET.fromstring(result)  # Validate the combined namespaces and XML before writing.
    return result, position


def _slide_parts(archive):
    presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
    relationships = ET.fromstring(archive.read("ppt/_rels/presentation.xml.rels"))
    rels = {rel.get("Id"): rel for rel in relationships.findall(f"{{{PKG_R}}}Relationship")}
    parts = []
    for slide in presentation.findall("p:sldIdLst/p:sldId", NS):
        rel = rels.get(slide.get(f"{{{R}}}id"))
        if rel is None or not rel.get("Type", "").endswith("/slide") or rel.get("TargetMode") == "External":
            raise ValueError("Invalid or external slide relationship")
        target = rel.get("Target", "")
        part = posixpath.normpath(target.lstrip("/") if target.startswith("/") else posixpath.join("ppt", target))
        if not part.startswith("ppt/") or part not in archive.namelist():
            raise ValueError(f"Invalid slide part: {part}")
        parts.append(part)
    if len(parts) != len(set(parts)):
        raise ValueError("Presentation contains duplicate slide-part relationships")
    return parts


def _targets(root):
    names = {}
    identifiers = []
    supported = {"sp", "pic", "cxnSp", "graphicFrame", "grpSp"}
    for shape in root.iter():
        kind = shape.tag.removeprefix(f"{{{P}}}")
        if kind not in supported:
            continue
        # Nonvisual properties are direct descendants, not a nested group's child.
        props = next((child.find(f"{{{P}}}cNvPr") for child in shape
                      if child.find(f"{{{P}}}cNvPr") is not None), None)
        if props is None:
            continue
        identifier, name = props.get("id"), props.get("name", "")
        if not identifier or not identifier.isdecimal():
            raise ValueError("A target shape has an invalid cNvPr id")
        identifiers.append(identifier)
        if name:
            if name in names:
                raise ValueError(f"Duplicate shape name: {name}")
            names[name] = {"name": name, "id": identifier, "type": kind}
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate shape IDs on slide")
    return names


def add_reveals(input_path, plan, output_path, report_path):
    input_path, output_path, report_path = map(Path, (input_path, output_path, report_path))
    paths = [input_path.resolve(), output_path.resolve(), report_path.resolve()]
    if len(set(paths)) != 3:
        raise ValueError("Input, output, and report paths must be different; refusing overwrite")
    if output_path.exists() or output_path.is_symlink() or report_path.exists() or report_path.is_symlink():
        raise FileExistsError("Output or report already exists; refusing overwrite")
    if not isinstance(plan, dict) or not isinstance(plan.get("slides"), list) or not plan["slides"]:
        raise ValueError("Plan must contain a nonempty slides list")
    changed = {}
    report = {"input": str(input_path.resolve()), "output": str(output_path.resolve()),
              "slides": [], "effect": "appear", "clickSteps": 0, "shapes": 0,
              "unmodifiedEntryPayloadsIdentical": True,
              "slideContentBytesPreserved": True,
              "scope": "Native animation XML only; verify playback in the target application"}
    with ZipFile(input_path) as archive:
        infos = archive.infolist()
        if len(infos) != len(set(info.filename for info in infos)):
            raise ValueError("Duplicate ZIP entry names")
        parts = _slide_parts(archive)
        seen_slides = set()
        for entry in plan["slides"]:
            if not isinstance(entry, dict):
                raise ValueError("Each slide plan must be an object")
            number = entry.get("slide")
            if type(number) is not int or not 1 <= number <= len(parts):
                raise ValueError(f"Slide number out of range: {number}")
            if number in seen_slides:
                raise ValueError(f"Duplicate slide plan: {number}")
            seen_slides.add(number)
            steps = entry.get("steps")
            if not isinstance(steps, list) or not steps:
                raise ValueError(f"Slide {number}: steps must be a nonempty list")
            part = parts[number - 1]
            original = archive.read(part)
            root = ET.fromstring(original)
            if root.find("p:timing", NS) is not None:
                raise ValueError(f"Slide {number} already has timing; refusing overwrite")
            names = _targets(root)
            selected, targets = set(), []
            for index, step in enumerate(steps, 1):
                if not isinstance(step, list) or not step or not all(isinstance(name, str) and name for name in step):
                    raise ValueError(f"Slide {number}, step {index}: expected nonempty shape-name list")
                group = []
                for name in step:
                    if name not in names:
                        raise ValueError(f"Slide {number}: missing shape name: {name}")
                    if name in selected:
                        raise ValueError(f"Slide {number}: repeated reveal: {name}")
                    selected.add(name)
                    group.append(names[name])
                targets.append(group)
            fragment = _timing(targets)
            modified, position = _insert_timing(original, fragment)
            if modified[:position] + modified[position + len(fragment):] != original:
                raise AssertionError("Nonanimation slide content changed")
            changed[part] = modified
            report["slides"].append({"slide": number, "part": part, "clickSteps": len(targets),
                                     "steps": [{"click": i, "shapes": group} for i, group in enumerate(targets, 1)],
                                     "originalSha256": hashlib.sha256(original).hexdigest(),
                                     "outputSha256": hashlib.sha256(modified).hexdigest(),
                                     "insertionByteOffset": position, "insertedBytes": len(fragment)})
            report["clickSteps"] += len(targets)
            report["shapes"] += len(selected)
        # All validation finishes before either output is opened. Exclusive opens
        # also prevent overwriting files created by another process meanwhile.
        created_output = created_report = False
        try:
            with output_path.open("xb") as stream:
                created_output = True
                with ZipFile(stream, "w") as output:
                    output.comment = archive.comment
                    for info in infos:
                        output.writestr(info, changed.get(info.filename, archive.read(info.filename)))
            with report_path.open("x", encoding="utf-8") as stream:
                created_report = True
                json.dump(report, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        except BaseException:
            if created_report:
                report_path.unlink(missing_ok=True)
            if created_output:
                output_path.unlink(missing_ok=True)
            raise
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("plan")
    parser.add_argument("output")
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    try:
        protected = Path(args.plan).resolve()
        if protected in (Path(args.output).resolve(), Path(args.report).resolve()):
            raise ValueError("Refusing to overwrite the plan file")
        report = add_reveals(args.input, json.loads(Path(args.plan).read_text(encoding="utf-8")),
                             args.output, args.report)
    except (ValueError, OSError, KeyError, ET.ParseError, expat.ExpatError) as exc:
        print(f"add_reveals: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({key: report[key] for key in ("output", "clickSteps", "shapes")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
