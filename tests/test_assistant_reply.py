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

    def test_explicit_history_retains_early_exchange_outside_dense_stats(self):
        r = self.report
        r["scope"] = "history"
        r["period"]["end"] = "2026-02-20"
        for day in range(1, 16):
            r["activity"]["messages"].append({"id": "feb-" + str(day), "timestamp": f"2026-02-{day:02}T12:00:00Z",
                                             "evidence_ids": ["thread"]})
        public = builder.public_report(builder.validate_report(r), compact=True)
        self.assertEqual(public["scope"], "history")
        self.assertEqual(len(public["activity"]["share_quotes"]), 2)
        self.assertEqual(public["activity"]["summary"]["messages"], 15)
        self.assertEqual(public["activity"]["rhythm"]["dense_start_month"], "2026-02")
        r["scope"] = "made-up"
        with self.assertRaisesRegex(builder.ReportError, "scope"):
            builder.validate_report(r)

    def test_lead_and_last_reply_publish_only_selected_text(self):
        story = self.report["share_story"]
        del story["assistant_reply"]
        story["lead"] = {"text": "评委选中了自己的图。", "evidence_ids": ["thread"]}
        story["final_reply"] = {"text": "这就有点尴尬了。", "evidence_ids": ["thread"]}
        self.report["evidence"][0]["excerpt"] += "\nAI：这就有点尴尬了。"
        public = builder.public_report(builder.validate_report(self.report), compact=True)
        self.assertEqual(public["story"]["lead"], "评委选中了自己的图。")
        self.assertEqual(public["story"]["final_reply"], "这就有点尴尬了。")
        self.assertNotIn("evidence_ids", json.dumps(public["story"]))

    def test_last_reply_cannot_borrow_another_turn(self):
        story = self.report["share_story"]
        del story["assistant_reply"]
        story["final_reply"] = {"text": "第二张。", "evidence_ids": ["thread"]}
        with self.assertRaisesRegex(builder.ReportError, "final_reply"):
            builder.validate_report(self.report)

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
        scene_with_lead = dict(scene, story={**scene["story"], "lead": "这次评委也参赛。"})
        long_habit = "还逐个检查了杯子、碟子和每一把勺子上有没有相同的花纹。"
        short_habit = "用茶匙补投一票"
        scene_with_lead["activity"] = dict(scene["activity"], daily_profile={"habits": [long_habit, short_habit]})
        scenes = [scene, thin, dict(scene_with_lead, theme="puai"), dict(scene_with_lead, theme="teach")]
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
            for index, data in enumerate(scenes):
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
                elif index == 1:
                    self.assertEqual(labels[2:4], ["日常用法", "给清单补漏"])
                    self.assertEqual(alt.count("给清单补漏"), 1)
                    self.assertNotIn("人格", alt)
                else:
                    quote_first = data["theme"] == "puai"
                    self.assertIn(short_habit, alt)
                    self.assertEqual(long_habit in alt, not quote_first)
                    for painted in (labels, alt):
                        self.assertEqual(
                            painted.index("挑个顺眼的。") < painted.index("这次评委也参赛。"),
                            quote_first)
            browser.close()


if __name__ == "__main__":
    unittest.main()
