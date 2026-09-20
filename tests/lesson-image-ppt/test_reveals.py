"""Native Appear animation tests using real, temporary PPTX ZIP/XML fixtures."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/lesson-image-ppt/scripts/add_reveals.py"
SPEC = importlib.util.spec_from_file_location("add_reveals", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
P = MODULE.P
R = MODULE.R
NS = MODULE.NS
A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def slide_xml(names=("source-a", "source-b", "source-c"), timing=False, extension=True):
    shapes = []
    for index, name in enumerate(names, 2):
        shapes.append(f'''<p:sp><p:nvSpPr><p:cNvPr id="{index}" name="{name}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{index * 100}" y="450"/><a:ext cx="900" cy="200"/></a:xfrm></p:spPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>原文{index}：实践。</a:t></a:r></a:p></p:txBody></p:sp>''')
    tail = '<p:timing><p:tnLst/></p:timing>' if timing else ''
    if extension:
        tail += '<p:extLst><p:ext uri="fixture"><f:keep xmlns:f="urn:fixture" value="untouched"/></p:ext></p:extLst>'
    return (f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>{''.join(shapes)}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>{tail}</p:sld>''').encode()


def write_pptx(path, first=None, second=None, reverse=False):
    first = first if first is not None else slide_xml()
    second = second if second is not None else slide_xml(("other-page",), extension=False)
    rel_ids = ["rId2", "rId1"] if reverse else ["rId1", "rId2"]
    presentation = f'<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst>' + ''.join(
        f'<p:sldId id="{256 + i}" r:id="{rid}"/>' for i, rid in enumerate(rel_ids)) + '</p:sldIdLst></p:presentation>'
    rels = f'<Relationships xmlns="{MODULE.PKG_R}"><Relationship Id="rId1" Type="{R}/slide" Target="slides/slide1.xml"/><Relationship Id="rId2" Type="{R}/slide" Target="slides/slide2.xml"/></Relationships>'
    types = '''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/><Override PartName="/ppt/slides/slide2.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/></Types>'''
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.comment = b"fixture archive comment"
        archive.writestr("[Content_Types].xml", types)
        archive.writestr("_rels/.rels", f'<Relationships xmlns="{MODULE.PKG_R}"><Relationship Id="rId1" Type="{R}/officeDocument" Target="ppt/presentation.xml"/></Relationships>')
        archive.writestr("ppt/presentation.xml", presentation)
        archive.writestr("ppt/_rels/presentation.xml.rels", rels)
        archive.writestr("ppt/slides/slide1.xml", first)
        archive.writestr("ppt/slides/slide2.xml", second)
        archive.writestr("ppt/media/untouched.bin", b"\x00\xffsample payload\x10")


class RevealsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lesson-reveals-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.input = self.folder / "input.pptx"
        self.output = self.folder / "output.pptx"
        self.report = self.folder / "report.json"
        write_pptx(self.input)

    def run_plan(self, steps=None, slide=1, plan=None):
        plan = plan or {"slides": [{"slide": slide, "steps": steps or [["source-a"], ["source-b", "source-c"]]}]}
        return MODULE.add_reveals(self.input, plan, self.output, self.report)

    def test_click_groups_target_names_and_valid_shape_ids(self):
        report = self.run_plan()
        self.assertEqual(report["clickSteps"], 2)
        self.assertEqual(report["shapes"], 3)
        self.assertEqual(report["slides"][0]["steps"][1]["shapes"][1]["id"], "4")
        with ZipFile(self.output) as archive:
            root = ET.fromstring(archive.read("ppt/slides/slide1.xml"))
        timing = root.find("p:timing", NS)
        clocks = timing.findall(".//p:cTn", NS)
        self.assertEqual(len({clock.get("id") for clock in clocks}), len(clocks))
        effects = [clock for clock in clocks if clock.get("presetID") == "1"]
        self.assertEqual([effect.get("nodeType") for effect in effects], ["clickEffect", "clickEffect", "withEffect"])
        self.assertTrue(all(effect.get("presetClass") == "entr" for effect in effects))
        self.assertEqual([target.get("spid") for target in timing.findall(".//p:spTgt", NS)], ["2", "3", "4"])
        shape_ids = {shape.get("id") for shape in root.findall(".//p:cNvPr", NS)}
        self.assertTrue(all(target.get("spid") in shape_ids for target in timing.findall(".//p:spTgt", NS)))
        main = next(clock for clock in clocks if clock.get("nodeType") == "mainSeq")
        click_groups = main.findall("p:childTnLst/p:par/p:cTn", NS)
        self.assertEqual(len(click_groups), 2)
        self.assertTrue(all(group.find("p:stCondLst/p:cond", NS).get("delay") == "indefinite" for group in click_groups))
        self.assertEqual(len(click_groups[1].findall(".//p:set", NS)), 2)
        self.assertTrue(all(action.get("dur") == "1" for action in timing.findall(".//p:cBhvr/p:cTn", NS)))
        self.assertTrue(all(value.get("val") == "visible" for value in timing.findall(".//p:set/p:to/p:strVal", NS)))
        self.assertTrue(all(attr.text == "style.visibility" for attr in timing.findall(".//p:attrName", NS)))

    def test_nonanimation_entry_payloads_and_slide_content_bytes_preserved(self):
        original_input = self.input.read_bytes()
        report = self.run_plan()
        record = report["slides"][0]
        with ZipFile(self.input) as original, ZipFile(self.output) as output:
            self.assertEqual(original.namelist(), output.namelist())
            self.assertEqual(original.comment, output.comment)
            for name in original.namelist():
                if name == record["part"]:
                    changed = output.read(name)
                    position, count = record["insertionByteOffset"], record["insertedBytes"]
                    self.assertEqual(changed[:position] + changed[position + count:], original.read(name))
                else:
                    self.assertEqual(original.read(name), output.read(name), name)
                self.assertEqual(original.getinfo(name).compress_type, output.getinfo(name).compress_type)
            root = ET.fromstring(output.read(record["part"]))
            tags = [element.tag for element in root]
            self.assertLess(tags.index(f"{{{P}}}timing"), tags.index(f"{{{P}}}extLst"))
        self.assertEqual(self.input.read_bytes(), original_input)

    def test_presentation_order_not_filename_order(self):
        write_pptx(self.input, reverse=True)
        report = self.run_plan([["other-page"]])
        self.assertEqual(report["slides"][0]["part"], "ppt/slides/slide2.xml")

    def test_rejects_missing_duplicate_and_repeated_targets(self):
        for steps, message in [([["missing"]], "missing shape"),
                               ([["source-a", "source-a"]], "repeated reveal"),
                               ([["source-a"], ["source-a"]], "repeated reveal")]:
            with self.subTest(steps=steps), self.assertRaisesRegex(ValueError, message):
                self.run_plan(steps)
            self.assertFalse(self.output.exists())
        write_pptx(self.input, first=slide_xml(("same", "same")))
        with self.assertRaisesRegex(ValueError, "Duplicate shape name"):
            self.run_plan([["same"]])

    def test_rejects_existing_timing_on_target(self):
        write_pptx(self.input, first=slide_xml(timing=True))
        with self.assertRaisesRegex(ValueError, "already has timing"):
            self.run_plan()
        self.assertFalse(self.output.exists())

    def test_non_utf8_declaration_without_bom_is_rejected(self):
        # Numeric references keep this a valid ISO-8859-1 XML document, rather
        # than relying on a malformed UTF-8 payload to trigger a parse error.
        declared_latin1 = slide_xml().decode("utf-8").replace(
            'encoding="UTF-8"', 'encoding="ISO-8859-1"')
        declared_latin1 = declared_latin1.encode("ascii", errors="xmlcharrefreplace")
        ET.fromstring(declared_latin1)
        write_pptx(self.input, first=declared_latin1)
        original = self.input.read_bytes()
        with self.assertRaisesRegex(ValueError, "Only UTF-8 slide XML is supported"):
            self.run_plan()
        self.assertFalse(self.output.exists())
        self.assertFalse(self.report.exists())
        self.assertEqual(self.input.read_bytes(), original)

    def test_preserves_existing_timing_on_unselected_slide(self):
        write_pptx(self.input, second=slide_xml(("other-page",), timing=True))
        self.run_plan()
        with ZipFile(self.input) as original, ZipFile(self.output) as output:
            self.assertEqual(original.read("ppt/slides/slide2.xml"), output.read("ppt/slides/slide2.xml"))

    def test_refuses_overwrite_input_output_and_report(self):
        plan = {"slides": [{"slide": 1, "steps": [["source-a"]]}]}
        original = self.input.read_bytes()
        with self.assertRaisesRegex(ValueError, "refusing overwrite"):
            MODULE.add_reveals(self.input, plan, self.input, self.report)
        self.assertEqual(self.input.read_bytes(), original)
        self.output.write_bytes(b"KEEP")
        with self.assertRaises(FileExistsError):
            self.run_plan()
        self.assertEqual(self.output.read_bytes(), b"KEEP")
        self.output.unlink()
        self.report.write_text("KEEP", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.run_plan()
        self.assertEqual(self.report.read_text(), "KEEP")
        self.assertFalse(self.output.exists())

    def test_invalid_plan_is_rejected_before_any_write(self):
        plans = [{"slides": []}, {"slides": [{"slide": True, "steps": [["source-a"]]}]},
                 {"slides": [{"slide": 3, "steps": [["source-a"]]}]},
                 {"slides": [{"slide": 1, "steps": [[]]}]},
                 {"slides": [{"slide": 1, "steps": [["source-a"]]}, {"slide": 1, "steps": [["source-b"]]}]}]
        for plan in plans:
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                self.run_plan(plan=plan)
            self.assertFalse(self.output.exists())
            self.assertFalse(self.report.exists())

    def test_cli_produces_report_and_non_destructive_failure(self):
        plan = self.folder / "plan.json"
        plan.write_text(json.dumps({"slides": [{"slide": 1, "steps": [["source-a"]]}]}), encoding="utf-8")
        command = [sys.executable, str(SCRIPT), str(self.input), str(plan), str(self.output), "--report", str(self.report)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.report.read_text())["clickSteps"], 1)
        original_output = self.output.read_bytes()
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(original_output, self.output.read_bytes())


if __name__ == "__main__":
    unittest.main()
