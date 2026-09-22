import importlib.util
import sys
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[2] / "skills/lesson-image-ppt/scripts/prepare_marks.py"
spec = importlib.util.spec_from_file_location("prepare_marks", path)
module = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(path.parent))
spec.loader.exec_module(module)


class HighlightTests(unittest.TestCase):
    def setUp(self):
        self.source = {"units": [{"id": "a", "text": "实践是认识的唯一来源。"},
                                  {"id": "b", "text": "作为认识主体的人类是世代延续的；"}]}

    def mark(self, q="唯一来源", role="knowledge-anchor", **extras):
        return {"quote": q, "role": role, "reason": "区分认识的来源与获取认识的途径。", **extras}

    def test_page_type_changes_style_without_changing_text(self):
        leaf = {"label": {"ref": "a", "quote": "实践"}, "segments": [{"ref": "a", "quote": "唯一来源"}],
                "marks": [self.mark(evidenceRef="a")]}
        deck = {"slides": [{"type": "content", "items": [{"ref": "a", "marks": [self.mark()]}]},
                           {"type": "knowledge-map", "groups": [{"topics": [{"leaves": [leaf]}]}]}]}
        result, report = module.compile_marks(self.source, deck)
        self.assertEqual(result["slides"][0]["items"][0]["emphasis"], ["唯一来源"])
        self.assertEqual(result["slides"][1]["groups"][0]["topics"][0]["leaves"][0]["focus"], ["唯一来源"])
        self.assertEqual(leaf["segments"], result["slides"][1]["groups"][0]["topics"][0]["leaves"][0]["segments"])
        self.assertNotIn("emphasis", deck["slides"][0]["items"][0])
        self.assertTrue(report["semanticReviewRequired"])

    def test_unrelated_source_and_invisible_quote_rejected(self):
        for mark in [self.mark(evidenceRef="b"), self.mark(q="认识工具")]:
            with self.assertRaises(ValueError):
                module.compile_marks(self.source, {"slides": [{"items": [{"ref": "a", "marks": [mark]}]}]})

    def test_map_requires_specific_excerpt_evidence(self):
        leaf = {"label": {"ref": "a", "quote": "实践"}, "segments": [{"ref": "a", "quote": "唯一来源"}],
                "marks": [self.mark()]}
        with self.assertRaises(ValueError):
            module.compile_marks(self.source, {"slides": [{"type": "knowledge-map", "leaves": [leaf]}]})

    def test_red_topic_only_in_map_hierarchy(self):
        item = {"ref": "a", "marks": [self.mark("实践", "topic-key")]}
        with self.assertRaises(ValueError):
            module.compile_marks(self.source, {"slides": [{"items": [item]}]})
        out, _ = module.compile_marks(self.source, {"slides": [{"type": "knowledge-map", "root": item}]})
        self.assertEqual(out["slides"][0]["root"]["contrast"], ["实践"])

    def test_axis_requires_group_and_stays_yellow(self):
        mark = self.mark("主体", "analysis-axis")
        item = {"ref": "b", "marks": [mark]}
        with self.assertRaises(ValueError):
            module.compile_marks(self.source, {"slides": [{"items": [item]}]})
        mark["group"] = "无限性的三条依据"
        out, report = module.compile_marks(self.source, {"slides": [{"items": [item]}]})
        self.assertEqual(out["slides"][0]["items"][0]["focus"], ["主体"])
        self.assertEqual(report["axisGroups"]["1:无限性的三条依据"], ["主体"])

    def test_generic_reason_and_conflicting_overlap_rejected(self):
        mark = self.mark()
        mark["reason"] = "重要"
        with self.assertRaises(ValueError):
            module.compile_marks(self.source, {"slides": [{"items": [{"ref": "a", "marks": [mark]}]}]})
        with self.assertRaises(ValueError):
            module.compile_marks(self.source, {"slides": [{"items": [{"ref": "a", "focus": ["来源"], "marks": [self.mark()]}]}]})

    def test_legacy_styles_reported_not_silently_approved(self):
        out, report = module.compile_marks(self.source, {"slides": [{"items": [{"ref": "a", "emphasis": ["来源"]}]}]})
        self.assertEqual(out["_highlightPlan"]["legacyUnexplained"], 1)
        self.assertEqual(report["legacyUnexplained"][0]["quote"], "来源")

    def test_manual_linebreak_does_not_lose_highlight(self):
        out, _ = module.compile_marks(self.source, {"slides": [{"items": [{"ref": "a", "text": "实践是认识的唯一\n来源。", "marks": [self.mark()]}]}]})
        self.assertEqual(out["slides"][0]["items"][0]["emphasis"], ["唯一\n来源"])


if __name__ == "__main__":
    unittest.main()
