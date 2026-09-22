"""Small real-OOXML fixtures for lesson-image-ppt's source coverage checker."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile


REPO = Path(__file__).resolve().parents[2]
CHECKER_PATH = REPO / "skills/lesson-image-ppt/scripts/check_pptx.py"
SPEC = importlib.util.spec_from_file_location("lesson_pptx_check", CHECKER_PATH)
CHECKER = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(CHECKER_PATH.parent))
SPEC.loader.exec_module(CHECKER)

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_R = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"


def write_pptx(path, slides):
    """Write actual slide XML into a minimal PPTX ZIP; slides maps number to runs."""
    content_types = ET.Element(f"{{{CT}}}Types")
    ET.SubElement(content_types, f"{{{CT}}}Default", Extension="rels",
                  ContentType="application/vnd.openxmlformats-package.relationships+xml")
    ET.SubElement(content_types, f"{{{CT}}}Default", Extension="xml",
                  ContentType="application/xml")
    ET.SubElement(content_types, f"{{{CT}}}Override", PartName="/ppt/presentation.xml",
                  ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml")
    root_rels = ET.Element(f"{{{PKG_R}}}Relationships")
    ET.SubElement(root_rels, f"{{{PKG_R}}}Relationship", Id="rId1",
                  Type=f"{R}/officeDocument", Target="ppt/presentation.xml")
    presentation = ET.Element(f"{{{P}}}presentation")
    slide_ids = ET.SubElement(presentation, f"{{{P}}}sldIdLst")
    pres_rels = ET.Element(f"{{{PKG_R}}}Relationships")
    for index, number in enumerate(sorted(slides), 1):
        ET.SubElement(slide_ids, f"{{{P}}}sldId", id=str(255 + index),
                      attrib={f"{{{R}}}id": f"rId{index}"})
        ET.SubElement(pres_rels, f"{{{PKG_R}}}Relationship", Id=f"rId{index}",
                      Type=f"{R}/slide", Target=f"slides/slide{number}.xml")
        ET.SubElement(content_types, f"{{{CT}}}Override",
                      PartName=f"/ppt/slides/slide{number}.xml",
                      ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml")
    with ZipFile(path, "w") as archive:
        for name, xml in [("[Content_Types].xml", content_types),
                          ("_rels/.rels", root_rels),
                          ("ppt/presentation.xml", presentation),
                          ("ppt/_rels/presentation.xml.rels", pres_rels)]:
            archive.writestr(name, ET.tostring(xml, encoding="utf-8", xml_declaration=True))
        # Intentionally keep caller insertion order to exercise numeric slide sorting.
        for number, runs in slides.items():
            slide = ET.Element(f"{{{P}}}sld")
            c_slide = ET.SubElement(slide, f"{{{P}}}cSld")
            tree = ET.SubElement(c_slide, f"{{{P}}}spTree")
            group_props = ET.SubElement(tree, f"{{{P}}}nvGrpSpPr")
            ET.SubElement(group_props, f"{{{P}}}cNvPr", id="1", name="")
            ET.SubElement(group_props, f"{{{P}}}cNvGrpSpPr")
            ET.SubElement(group_props, f"{{{P}}}nvPr")
            ET.SubElement(tree, f"{{{P}}}grpSpPr")
            shape = ET.SubElement(tree, f"{{{P}}}sp")
            nv = ET.SubElement(shape, f"{{{P}}}nvSpPr")
            ET.SubElement(nv, f"{{{P}}}cNvPr", id="2", name="fixture")
            ET.SubElement(nv, f"{{{P}}}cNvSpPr", txBox="1")
            ET.SubElement(nv, f"{{{P}}}nvPr")
            ET.SubElement(shape, f"{{{P}}}spPr")
            body = ET.SubElement(shape, f"{{{P}}}txBody")
            ET.SubElement(body, f"{{{A}}}bodyPr")
            ET.SubElement(body, f"{{{A}}}lstStyle")
            paragraph = ET.SubElement(body, f"{{{A}}}p")
            for value in runs:
                run = ET.SubElement(paragraph, f"{{{A}}}r")
                ET.SubElement(run, f"{{{A}}}t").text = value
            archive.writestr(f"ppt/slides/slide{number}.xml",
                             ET.tostring(slide, encoding="utf-8", xml_declaration=True))


class ContentCheckTests(unittest.TestCase):
    def setUp(self):
        root = Path("/tmp/lesson-skill-smoke")
        root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="content-check-", dir=root)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.pptx = self.folder / "fixture.pptx"
        self.source = {"units": [
            {"id": "a", "text": "甲组先观察。"},
            {"id": "b", "text": "乙组再记录。"},
        ]}

    def check(self, slides, source=None):
        write_pptx(self.pptx, slides)
        return CHECKER.check(source or self.source, self.pptx)

    def test_authorized_number_omission_preserves_raw_and_checks_remainder(self):
        source = {"units": [{"id": "x", "text": "①认识的对象是无限变化的。"}],
                  "displayOmissions": [{"id": "x", "prefix": "①", "reason": "孤立编号",
                                         "authorization": "用户明确要求"}]}
        report = self.check({1: ["认识的对象是无限变化的。"]}, source)
        self.assertTrue(report["passed"])
        self.assertEqual(source["units"][0]["text"][0], "①")
        self.assertEqual(len(report["displayOmissions"]), 1)
        self.assertFalse(self.check({1: ["认识的对象。"]}, source)["passed"])
        source.pop("displayOmissions")
        self.assertFalse(self.check({1: ["认识的对象是无限变化的。"]}, source)["passed"])

    def test_omission_cannot_delete_content_or_lack_authorization(self):
        for prefix, authorization in [("认识", "用户要求"), ("①", "")]:
            source = {"units": [{"id": "x", "text": prefix + "对象"}],
                      "displayOmissions": [{"id": "x", "prefix": prefix,
                                             "reason": "test", "authorization": authorization}]}
            with self.assertRaises(ValueError):
                self.check({1: ["对象"]}, source)

    def test_complete_ordered_body_passes(self):
        report = self.check({1: ["甲组先观察。"], 2: ["乙组再记录。"]})
        self.assertTrue(report["passed"])
        self.assertEqual(report["missing"], [])
        self.assertEqual(report["outOfOrder"], [])
        self.assertEqual(report["mapping"], [
            {"id": "a", "pages": [1]}, {"id": "b", "pages": [2]}])

    def test_text_split_across_runs_and_whitespace_passes(self):
        report = self.check({1: ["甲组\n", "先观察。", "\t乙组", "再记录。"]})
        self.assertTrue(report["passed"])

    def test_missing_source_unit_fails(self):
        report = self.check({1: ["甲组先观察。"]})
        self.assertFalse(report["passed"])
        self.assertEqual(report["missing"], ["b"])
        self.assertEqual(report["outOfOrder"], ["b"])

    def test_same_slide_reversal_is_out_of_order_not_missing(self):
        report = self.check({1: ["乙组再记录。", "甲组先观察。"]})
        self.assertFalse(report["passed"])
        self.assertEqual(report["missing"], [])
        self.assertEqual(report["outOfOrder"], ["b"])

    def test_across_slide_reversal_is_detected(self):
        report = self.check({1: ["乙组再记录。"], 2: ["甲组先观察。"]})
        self.assertFalse(report["passed"])
        self.assertEqual(report["outOfOrder"], ["b"])

    def test_slide_ten_is_after_slide_two_regardless_of_zip_order(self):
        report = self.check({10: ["乙组再记录。"], 2: ["甲组先观察。"]})
        self.assertTrue(report["passed"])

    def test_heading_is_covered_without_constraining_body_order(self):
        source = {"units": [{"id": "h", "text": "观察活动", "kind": "heading"},
                            *self.source["units"]]}
        report = self.check({1: ["甲组先观察。", "乙组再记录。", "观察活动"]}, source)
        self.assertTrue(report["passed"])

    def test_traditional_jian_fails_even_when_source_is_covered(self):
        report = self.check({1: ["甲组先观察。", "乙组再记录。", "實踐"]})
        self.assertFalse(report["passed"])
        self.assertTrue(report["traditionalJian"])
        self.assertEqual(report["missing"], [])

    def test_cli_writes_failure_report_and_returns_nonzero(self):
        write_pptx(self.pptx, {1: ["甲组先观察。"]})
        source = self.folder / "source.json"
        report = self.folder / "report.json"
        source.write_text(json.dumps(self.source, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run([sys.executable, str(CHECKER_PATH), str(source),
                                 str(self.pptx), "--report", str(report)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["missing"], ["b"])


if __name__ == "__main__":
    unittest.main()
