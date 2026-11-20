"""Check the private source and the public projection of one three-turn scene."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts/build_report.py"
spec = importlib.util.spec_from_file_location("build_report", MODULE)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class AssistantReplyTests(unittest.TestCase):
    def setUp(self):
        first, answer, last = "挑个顺眼的。", "第二张。", "那是你刚做的。"
        self.report = {
            "schema_version": 1, "year": 2026, "mode": "excerpt", "theme": "all",
            "period": {"start": "2026-01-01", "end": "2026-01-02"}, "person": {"name": "试读"},
            "identity": {"title": "互评", "subtitle": "轮流当评委。"},
            "share_story": {"persona_evidence_ids": ["thread"], "moment_indices": [],
                            "assistant_reply": {"after_quote": 1, "text": answer, "evidence_ids": ["thread"]}},
            "evidence": [{"id": "thread", "type": "provided", "source": "私下核对的逐角色对话",
                          "excerpt": f"用户：{first}\nAI：{answer}\n用户：{last}"}],
            "keywords": ["互评"], "metrics": [], "moments": [],
            "closing": {"text": "评完了。", "evidence_ids": ["thread"]},
            "phrase": {"kind": "quote", "note": "本人发言", "text": first, "evidence_ids": ["thread"]},
            "activity": {"timezone": "UTC", "coverage": "partial", "messages": [
                {"id": "one", "timestamp": "2026-01-01T12:00:00Z", "evidence_ids": ["thread"]},
                {"id": "two", "timestamp": "2026-01-01T12:02:00Z", "evidence_ids": ["thread"]}],
                "highlights": [], "share_quotes": [
                    {"message_id": "one", "text": first}, {"message_id": "two", "text": last}]}}

    def test_projection_keeps_only_the_exact_turn_and_position(self):
        r = builder.validate_report(self.report)
        public = builder.public_report(r, compact=True)
        self.assertEqual(public["story"]["assistant_reply"], {"after_quote": 1, "text": "第二张。"})
        self.assertEqual(public["activity"]["summary"]["messages"], 2)

    def test_source_must_situate_reply_in_the_selected_exchange(self):
        evidence = self.report["evidence"][0]
        for evidence_text in [
            "用户：挑个顺眼的。\n用户：第二张。\n用户：那是你刚做的。",
            "用户：那是你刚做的。\nAI：第二张。\n用户：挑个顺眼的。",
            "用户：挑个顺眼的。\nAI：第三张。\n用户：那是你刚做的。"]:
            with self.subTest(evidence_text=evidence_text):
                evidence["excerpt"] = evidence_text
                with self.assertRaisesRegex(builder.ReportError, "assistant_reply"):
                    builder.validate_report(self.report)

    def test_reply_requires_two_visible_ordered_turns(self):
        reply = self.report["share_story"]["assistant_reply"]
        reply["after_quote"] = 2
        with self.assertRaisesRegex(builder.ReportError, "assistant_reply"):
            builder.validate_report(self.report)
        reply["after_quote"] = 1
        self.report["activity"]["messages"][1]["timestamp"] = "2026-01-01T11:59:00Z"
        with self.assertRaisesRegex(builder.ReportError, "assistant_reply"):
            builder.validate_report(self.report)

    @unittest.skipUnless(importlib.util.find_spec("playwright"), "requires Playwright and Chrome")
    def test_poster_paints_the_scene_before_statistics_and_skips_empty_persona(self):
        from playwright.sync_api import Error, sync_playwright
        template = (MODULE.parents[1] / "assets/comic-template.html").read_text()
        html = builder.embed_template_assets(template)
        scene = builder.public_report(self.report, compact=True)
        thin = {"year": 2026, "mode": "excerpt", "theme": None, "person": {"name": "试读"}, "keywords": [],
                "story": {"persona": "", "scenes": []}, "activity": {"daily_profile": {"habits": ["给清单补漏"]}}}
        with sync_playwright() as engine, tempfile.TemporaryDirectory() as tmp:
            try:
                browser = engine.chromium.launch(channel="chrome")
            except Error as exc:
                self.skipTest(f"local Chrome unavailable: {exc}")
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.add_init_script("""{
              const original = CanvasRenderingContext2D.prototype.fillText;
              window.labels = [];
              CanvasRenderingContext2D.prototype.fillText = function(label, ...args) {
                window.labels.push(label);
                return original.call(this, label, ...args);
              };
            }""")
            for index, data in enumerate([scene, thin]):
                path = Path(tmp) / f"poster-{index}.html"
                path.write_text(html.replace("__REPORT_JSON__", json.dumps(data, ensure_ascii=False)))
                page.goto(path.as_uri())
                page.wait_for_function("document.getElementById('preview').naturalWidth === 900")
                labels = page.evaluate("window.labels")
                alt = page.locator("#preview").get_attribute("alt")
                self.assertNotIn("用户人格", labels)
                if index == 0:
                    turns = [labels.index(s) for s in ["挑个顺眼的。", "第二张。", "那是你刚做的。", "发言日历"]]
                    self.assertEqual(turns, sorted(turns))
                    self.assertLess(alt.index("AI：第二张。"), alt.index("那是你刚做的。"))
                else:
                    self.assertEqual(labels[2:4], ["日常用法", "给清单补漏"])
                    self.assertEqual(alt.count("给清单补漏"), 1)
                    self.assertNotIn("人格", alt)
            browser.close()


if __name__ == "__main__":
    unittest.main()
