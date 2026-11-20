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

    def test_name_projection_for_native_templates(self):
        report = json.loads((MODULE.parents[1] / "assets/demo-report.json").read_text())
        report.pop("share_story")
        for person, expected in [({}, "我"), ({"name": " "}, "我"), ({"name": "ＸＸＸ"}, "我"),
                                 ({"name": "「xXx」"}, "我"), ({"name": "普通唐某"}, "普通唐某")]:
            report["person"] = person
            builder.validate_report(report)
            for compact in [False, True]:
                with self.subTest(person=person, compact=compact):
                    self.assertEqual(builder.public_report(report, compact=compact)["person"]["name"], expected)
            self.assertEqual(report["person"], person)

    def test_projection_keeps_only_the_exact_turn_and_position(self):
        r = builder.validate_report(self.report)
        public = builder.public_report(r, compact=True)
        self.assertEqual(public["story"]["assistant_reply"], {"after_quote": 1, "text": "第二张。"})
        self.assertEqual(public["activity"]["summary"]["messages"], 2)

    def test_missing_theme_can_use_one_official_badge_without_changing_input(self):
        r = self.report
        del r["theme"]
        for theme, label in [*builder.THEMES.items(), ("einstein", "爱因斯坦")]:
            r["keywords"] = [label, "当场拆台"]
            public = builder.public_report(builder.validate_report(r), compact=True)
            self.assertEqual((public["theme"], public["keywords"]), (theme, ["当场拆台"]))
            self.assertNotIn("theme", r)
            self.assertEqual(r["keywords"], [label, "当场拆台"])
        r["theme"] = "all"
        r["keywords"] = ["AICU"]
        self.assertEqual(builder.public_report(builder.validate_report(r), compact=True)["theme"], "all")
        r["theme"] = None
        self.assertIsNone(builder.public_report(builder.validate_report(r), compact=True)["theme"])

    def test_legacy_mixed_badges_keep_their_previous_valid_scope(self):
        # This built-in legacy material already carries a verified roast ledger.
        r = json.loads((MODULE.parents[1] / "assets/demo-report.json").read_text())
        r["keywords"] = ["AI在心口难开", "AICU", "找零"]
        for has_story in (True, False):
            if not has_story:
                del r["share_story"]
            public = builder.public_report(builder.validate_report(r), compact=True)
            self.assertIsNone(public["theme"])
            self.assertEqual(public["keywords"], r["keywords"])
        self.assertEqual(builder.public_report(r)["keywords"], r["keywords"])
        r["keywords"] = ["这个标签有七个字"]
        with self.assertRaisesRegex(builder.ReportError, "keywords"):
            builder.validate_report(r)
        r["keywords"] = ["AICU", "一个", "两个", "三个"]
        with self.assertRaisesRegex(builder.ReportError, "keywords"):
            builder.validate_report(r)

    def test_default_and_explicit_old_styles_accept_untyped_legacy_sources(self):
        r = json.loads((MODULE.parents[1] / "assets/demo-report.json").read_text())
        del r["share_story"]
        r["keywords"] = ["AI因斯坦", "找零"]
        r["activity"]["share_quotes"][0]["rewrite"] = {"text": "一条标注过的旧改写"}
        with tempfile.TemporaryDirectory() as directory:
            src, out = Path(directory) / "report.json", Path(directory) / "report.html"
            src.write_text(json.dumps(r, ensure_ascii=False))
            args = ["--input", str(src), "--output", str(out)]
            self.assertEqual(builder.main(args), 0)
            html = out.read_text()
            self.assertIn('"theme":"einstein"', html)
            self.assertIn('"kind":"rewrite"', html)
            self.assertEqual(builder.main(args + ["--style", "ticket"]), 0)
            r["keywords"] = ["AICU", "PUAI"]
            src.write_text(json.dumps(r))
            self.assertEqual(builder.main(args), 0)
            self.assertIn('"schema_version":1', out.read_text())
        r["theme"] = "einstein"
        with self.assertRaisesRegex(builder.ReportError, "rewrite"):
            builder.validate_report(r)

    def test_partial_date_evidence_is_projected_without_creating_messages(self):
        r = self.report
        activity = r["activity"]
        activity["observed_dates"] = [{"date": "2026-01-02", "evidence_ids": ["day"]}]
        r["evidence"].append({"id": "day", "type": "provided", "source": "private",
                              "excerpt": "2026-01-02 · 本人发言。"})
        public = builder.public_report(builder.validate_report(r), compact=True)["activity"]
        self.assertEqual(public["observed_dates"], ["2026-01-02"])
        self.assertEqual(public["summary"]["messages"], 2)
        self.assertEqual(public["summary"]["active_days"], 1)
        self.assertNotIn('"day"', json.dumps(public))
        for bad in ["2026-01-01", "2026-01-03"]:
            activity["observed_dates"][0]["date"] = bad
            with self.assertRaisesRegex(builder.ReportError, "observed_dates"):
                builder.validate_report(r)
        activity["observed_dates"][0]["date"] = "2026-01-02"
        r["evidence"][-1]["type"] = "self_report"
        with self.assertRaisesRegex(builder.ReportError, "observed_dates"):
            builder.validate_report(r)

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
                    i = labels.index("日常用法")
                    self.assertEqual(labels[i+1], "给清单补漏")
                    self.assertEqual(alt.count("给清单补漏"), 1)
                    self.assertNotIn("人格", alt)
                else:
                    self.assertIn(short_habit, alt)
                    self.assertEqual(long_habit in alt, data["theme"] != "puai")
                    for painted in (labels, alt):
                        self.assertLess(painted.index("挑个顺眼的。"), painted.index("这次评委也参赛。"))
            browser.close()


if __name__ == "__main__":
    unittest.main()
