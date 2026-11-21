"""Verify the attachment path used by a chat sandbox with Python and Pillow only."""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/render_chat_png.py"
spec = importlib.util.spec_from_file_location("puai_chat_png", SCRIPT)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)

RECEIPT = """PUAI 2026
署名：试读者
主题：all
主场景：两位裁判互相批作业。
原话：11-04~我把名字盖住，你先挑一份。
AI：左边第二行说得更清楚。
原话：11-04~左边就是你昨天写的。
用法：评完才揭晓作者。
标签：匿名评卷、交叉阅卷
日期账：09-03:2:1,11-04:3:2
无日期账：2:?
Token：13000
"""


class ChatPngTest(unittest.TestCase):
    def test_grouped_highlights_keep_their_matching_quote(self):
        receipt = ("PUAI 2026\n原话：02-04~买五单能靠花钱养活自己？\n原话：07-16~塑料袋也能切盘端上桌。"
                   "\n划线：花钱养活自己\n划线：切盘端上桌\n划线：编出来的")
        self.assertEqual(renderer.parse_receipt(receipt)["emphases"], ["花钱养活自己", "切盘端上桌"])
        unclear = "PUAI 2026\n原话：昨天买五单。\n原话：今天买五单。\n原话：那我走了。\n划线：买五单"
        self.assertEqual(renderer.parse_receipt(unclear)["emphases"], ["", "", ""])

    def test_signature_placeholder_is_never_painted_as_the_name(self):
        for incoming, expected in [("", "我"), ("XXX", "我"), ("「xXx」", "我"), ("ＸＸＸ", "我"),
                                   ("叉叉叉", "我"), ("不愿透露姓名的唐某", "不愿透露姓名的唐某"), ("XXX号", "XXX号")]:
            with self.subTest(incoming=incoming):
                self.assertEqual(renderer.parse_receipt(RECEIPT.replace("试读者", incoming))["name"], expected)

    def test_partial_ledger_and_real_conversation_order(self):
        r = renderer.parse_receipt(RECEIPT)
        self.assertEqual(r["reply"], (1, "左边第二行说得更清楚。"))
        self.assertEqual((r["total"], len(r["days"]), r["hits"]), (7, 2, None))
        reviewed = renderer.parse_receipt(RECEIPT.replace("2:?", "2:1"))
        self.assertEqual(reviewed["hits"], 4)
        with self.assertRaises(ValueError):
            renderer.parse_receipt(RECEIPT.replace("11-04:3:2", "11-04:3:7"))

    def test_type_is_visible_on_the_header_separate_from_signature_and_traits(self):
        font = renderer.load_font(ROOT / "assets/SmileySans-Oblique.woff2")
        draw_text = ImageDraw.ImageDraw.text
        nickname = "很长的一串昵称"*2+"唐某"
        themes = {"puai": "PUAI", "einstein": "AI因斯坦", "teach": "AI的教育",
                  "aicu": "AICU", "edison": "AI迪生", "free": "AI咋咋地",
                  "hush": "AI在心口难开", "all": "AI特全体", "support": "AI的供养", "": "待定"}
        for key, value in themes.items():
            for scope, caption in [("history", "年度类型"), ("thread", "本次类型"), ("fragments", "本次类型")]:
                with self.subTest(key=key, scope=scope):
                    receipt = f"PUAI 2026\n范围：{scope}\n署名：{nickname}\n标签：小算盘\n原话：算盘得响。"
                    if key:
                        receipt += "\n主题："+key
                    bounds = {}
                    def observe(draw, xy, label, *args, **kwargs):
                        bounds[label] = draw.textbbox(xy, label, font=kwargs["font"], anchor=kwargs["anchor"])
                        return draw_text(draw, xy, label, *args, **kwargs)
                    with patch.object(ImageDraw.ImageDraw, "text", observe):
                        img = renderer.draw_report(renderer.parse_receipt(receipt), font)
                    self.assertEqual(img.width, 900)
                    self.assertLessEqual(bounds[nickname+"的"][2], bounds[caption][0]-12)
                    self.assertLess(bounds[caption][2], bounds[value][0])
                    self.assertLess(bounds[value][1], 95)
                    self.assertLessEqual(bounds[value][2], 852)
                    self.assertGreater(bounds["小算盘"][1], bounds[value][3])
                    self.assertGreater(len(img.crop(bounds[value]).getcolors(90000)), 2)

    def test_receipt_accepts_explicit_persona_type_labels(self):
        for field in ("人物类型", "人格类型", "年度类型", "本次类型", "主题"):
            for spelling, key in (("AI因斯坦", "einstein"), ("爱因斯坦", "einstein"),
                                  ("PUAI", "puai"), ("待定", "")):
                with self.subTest(field=field, spelling=spelling):
                    receipt = f"PUAI 2026\n{field}：{spelling}\n原话：这是真的吗？"
                    self.assertEqual(renderer.parse_receipt(receipt)["theme"], key)
        self.assertEqual(renderer.parse_receipt("PUAI 2026\n标签：AI因斯坦\n原话：这是真的吗？")["theme"], "einstein")

    def test_unledgered_quote_lead_and_explicit_ai_ending(self):
        r = renderer.parse_receipt("PUAI 2026\n原话：11-06~又丢了？\nAI收尾：你刚才已经给我了。")
        self.assertEqual(r["total"], 0)
        self.assertIsNone(r["hits"])
        self.assertFalse(r["days"])
        self.assertEqual(r["reply"], (1, "你刚才已经给我了。"))
        extra = renderer.parse_receipt("PUAI 2026\n原话：再试一次。\nAI：这是额外的回复。")
        self.assertIsNone(extra["reply"])
        lead = renderer.parse_receipt("PUAI 2026\n主场景：截图一到，空文件有了内容。")
        self.assertFalse(lead["quotes"])
        self.assertFalse(lead["days"])

    def test_scope_and_six_quotes_reach_the_painted_poster(self):
        lines = ["PUAI 2026", "主题：teach", *("原话：" + q for q in "甲乙丙丁戊己"), "AI收尾：六句。"]
        font = renderer.load_font(ROOT / "assets/SmileySans-Oblique.woff2")
        for scope, expected in [("", "聊天片段精选"), ("thread", "本次对话精选"), ("history", None)]:
            parsed = renderer.parse_receipt("\n".join(lines + (["范围：" + scope] if scope else [])))
            self.assertEqual(len(parsed["quotes"]), 6)
            self.assertEqual(parsed["reply"], (6, "六句。"))
            with patch.object(ImageDraw.ImageDraw, "text") as draw:
                renderer.draw_report(parsed, font)
                painted = [call.args[1] for call in draw.call_args_list]
            self.assertIn("2026 AI的教育 报告", painted)
            if expected:
                self.assertIn(expected, painted)
            self.assertTrue(all(q in painted for q in "甲乙丙丁戊己"))
        with self.assertRaises(ValueError):
            renderer.parse_receipt("\n".join(lines + ["范围：other"]))

    def test_calendar_is_painted_for_quotes_observed_days_and_missing_dates(self):
        from io import BytesIO
        font = renderer.load_font(ROOT / "assets/SmileySans-Oblique.woff2")
        draw_text = ImageDraw.ImageDraw.text
        cases = [
            ("原话：甲。\n原话：乙。\n原话：丙。\n原话：丁。",
             ("发言日历", "这 4 句原话未附日期"), ("活跃", "单日最高")),
            ("发言日期：07-02,11-08,11-08", ("片段日期", "核实 2 天", "07 月", "11 月"), ("条指令", "单日最高")),
            ("原话：07-02~甲。\n无日期账：2:?", ("片段日期", "核实 1 天", "2 条指令"), ("单日最高",)),
            ("主场景：落了一行。", ("发言日历", "这份记录未附日期"), ("单日最高",)),
            ("原话：02-03~甲。\n原话：02-03~乙。\n原话：丙。\n发言日期：02-03,04-05,04-05",
             ("片段日期", "核实 2 天", "2 / 3 句原话有日期", "02 月", "04 月"), ("单日最高", "条指令")),
            ("原话：02-03~甲。", ("片段日期", "核实 1 天", "1 句原话有日期"), ("单日最高", "条指令")),
            ("原话：04-05~甲。\n发言日期：04-05,09-10\n日期账：09-10:5:?",
             ("发言日历", "有发言的日子", "1 天", "单日最高发言", "9.10 · 5 条", "另有 1 个已知日期", "04.05"), ("2 天开喷",)),
        ]
        for body, expected, forbidden in cases:
            report = renderer.parse_receipt("PUAI 2026\n" + body)
            painted = {}
            def observe(draw, xy, label, *args, **kwargs):
                painted[label] = xy
                return draw_text(draw, xy, label, *args, **kwargs)
            with self.subTest(body=body), patch.object(ImageDraw.ImageDraw, "text", observe):
                img = renderer.draw_report(report, font)
                payload = BytesIO()
                img.save(payload, "PNG")
                with Image.open(payload) as png:
                    self.assertEqual(png.width, 900)
                    at = painted[expected[0]][1]
                    self.assertGreater(len(png.crop((48, at, 820, at+43)).getcolors(400*1000)), 3)
                words = "\n".join(painted)
                for label in expected:
                    self.assertIn(label, words)
                for label in forbidden:
                    self.assertNotIn(label, words)
        with self.assertRaises(ValueError):
            renderer.parse_receipt("PUAI 2026\n原话：甲。\n发言日期：02-30")

    def test_observed_day_in_a_counted_month_is_also_inked(self):
        source = "PUAI 2026\n主题：puai\n日期账：09-10:5:?\n发言日期：09-12"
        report = renderer.parse_receipt(source)
        font = renderer.load_font(ROOT / "assets/SmileySans-Oblique.woff2")
        with patch.object(ImageDraw.ImageDraw, "ellipse") as dots:
            renderer.draw_report(report, font)
        # The month grid uses 23px dots; ignore legends and the decorative graphics.
        painted = [call for call in dots.call_args_list if call.args[0][2]-call.args[0][0] == 23
                   and call.kwargs.get("fill") == renderer.PALETTES["puai"][1]]
        self.assertEqual(len(painted), 2)
        self.assertEqual((len(report["days"]), report["total"]), (1, 5))

    def test_turn_selection_and_invalid_empty_source(self):
        self.assertIsNone(renderer.parse_receipt(
            "PUAI 2026\n原话：11-06~后来的问题。\nAI：不在其间。\n原话：11-01~早来的问题。")["reply"])
        with self.assertRaises(ValueError):
            renderer.parse_receipt("PUAI 2026\n署名：我\n标签：教学")

    def test_all_themes_lead_with_the_verified_exchange_before_the_caption_and_stats(self):
        receipt = """PUAI 2026
主题：puai
主场景：自带红笔。
前情：表里少一行。
原话：11-04~你再数数。
AI：四行。
原话：11-04~三行半吗？
日期账：11-04:2:2
"""
        font = renderer.load_font(ROOT / "assets/SmileySans-Oblique.woff2")
        draw_text = ImageDraw.ImageDraw.text

        def positions(source):
            ys = {}

            def record(draw, xy, text, *args, **kwargs):
                ys[text] = xy[1]
                return draw_text(draw, xy, text, *args, **kwargs)

            with patch.object(ImageDraw.ImageDraw, "text", record):
                renderer.draw_report(renderer.parse_receipt(source), font)
            return ys

        for theme in ["puai", "teach"]:
            order = ["对话现场", "表里少一行。", "你再数数。", "四行。", "三行半吗？", "记录里，你发出了", "发言日历", "自带红笔。"]
            with self.subTest(theme=theme):
                ys = positions(receipt.replace("主题：puai", f"主题：{theme}"))
                actual = [ys[text] for text in order]
                self.assertEqual(actual, sorted(set(actual)))
        lead_only = positions("PUAI 2026\n主题：puai\n主场景：自带红笔。")
        self.assertLess(lead_only["对话现场"], lead_only["自带红笔。"])
        self.assertNotIn("本人原话", lead_only)

    def test_comic_layout_centers_the_signature_and_alternates_quotes(self):
        source = "PUAI 2026\n署名：不愿透露姓名的唐某\n主题：puai\n原话：你再数数。\n原话：四行半。\n原话：退款！"
        font = renderer.load_font(ROOT / "assets/SmileySans-Oblique.woff2")
        positions = {}
        draw_text = ImageDraw.ImageDraw.text

        def observe(draw, xy, label, *args, **kwargs):
            positions[label] = (xy, kwargs)
            return draw_text(draw,xy,label,*args,**kwargs)

        with patch.object(ImageDraw.ImageDraw,"text",observe):
            img = renderer.draw_report(renderer.parse_receipt(source),font)
        badge = "不愿透露姓名的唐某的"
        xy, kwargs = positions[badge]
        bounds = kwargs["font"].getbbox(badge,anchor=kwargs["anchor"])
        actual_cx = xy[0]+(bounds[0]+bounds[2])/2
        width = round(kwargs["font"].getlength(badge))+44
        self.assertAlmostEqual(actual_cx,48+width/2,delta=1)
        self.assertAlmostEqual(xy[1]+(bounds[1]+bounds[3])/2,64,delta=1)
        first, second, third = [positions[q][0] for q in ("你再数数。","四行半。","退款！")]
        self.assertLess(first[0],second[0])
        self.assertLess(third[0],second[0])
        for (x,y),color in zip([first,second,third],["#FCFDFB","#16399A","#C7E1F4"]):
            self.assertEqual(img.getpixel((x-6,y+5)),tuple(bytes.fromhex(color[1:])))

    def test_sticker_outlines_include_the_burst_in_short_and_archived_editions(self):
        face = renderer.load_font(ROOT / "assets/SmileySans-Oblique.woff2")
        polygon = ImageDraw.ImageDraw.polygon
        quotes = ["你再数数。", "难道果核也按果肉算钱？", "退款！", "再来。", "还有？", "收卷。"]
        for count in range(1, 7):
            source = "PUAI 2026\n主题：puai\n" + "\n".join("原话："+q for q in quotes[:count])
            outlines = []

            def observe(draw, vertices, *args, **kwargs):
                # A dialogue sticker contributes one triangular tail; the burst is a closed polygon.
                outlines.append(len(vertices) > 3)
                return polygon(draw, vertices, *args, **kwargs)

            with self.subTest(count=count), patch.object(ImageDraw.ImageDraw, "polygon", observe):
                renderer.draw_report(renderer.parse_receipt(source), face)
                expected = [i == count-1 if count <= 2 else i % 3 == 2 for i in range(count)]
                self.assertEqual(outlines, expected)

    def test_standalone_png_without_node_browser_templates_or_network(self):
        with tempfile.TemporaryDirectory() as folder:
            wd = Path(folder)
            shutil.copyfile(SCRIPT, wd/"render_chat_png.py")
            # Ship the freely licensed font, as the public skill ZIP does.
            font = wd/"SmileySans-Oblique.woff2"
            shutil.copyfile(ROOT/"assets"/font.name, font)
            (wd/"report.txt").write_text(RECEIPT, encoding="utf-8")
            probe = """import runpy, socket, sys
def deny_network(*args, **kwargs): raise AssertionError('network used during render')
socket.socket = deny_network
sys.argv=['render_chat_png.py','report.txt','report.png','--font','SmileySans-Oblique.woff2']
runpy.run_path(sys.argv[0],run_name='__main__')
"""
            subprocess.run([sys.executable, "-I", "-c", probe], cwd=wd,
                           env={"PATH": "", "HOME": str(wd)}, check=True)
            with Image.open(wd/"report.png") as img:
                self.assertEqual((img.format, img.width), ("PNG", 900))
                self.assertGreater(img.height, 1300)
                self.assertGreater(len(img.resize((40, 80)).getcolors(3200)), 20)
                prev = img.copy()
            # Two different original answers must generate different actual pixels.
            (wd/"report.txt").write_text(RECEIPT.replace("左边第二行说得更清楚。","右边的理由更充分。"),encoding="utf-8")
            subprocess.run([sys.executable,"-I","-c",probe],cwd=wd,
                           env={"PATH":"","HOME":str(wd)},check=True)
            with Image.open(wd/"report.png") as img:
                self.assertIsNotNone(ImageChops.difference(prev,img).getbbox())
                try:
                    import zxingcpp
                except ImportError:
                    return
                self.assertEqual(zxingcpp.read_barcode(img).text, "https://xn--sxrw8m230b.com/PUAI/#go")


if __name__ == "__main__":
    unittest.main()
