import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import ImageColor, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_chat_png as poster


class PosterLayout(unittest.TestCase):
    def test_personality_tag_selects_the_palette_only_when_it_names_one_type(self):
        parse = lambda fields: poster.parse_receipt("PUAI 2026\n原话：果核怎么算？\n" + fields)
        for key, (label, _) in poster.EDITIONS.items():
            if key:
                data = parse("人格标签："+label+"、果核精算师")
                self.assertEqual((data["theme"], data["tags"]), (key, ["果核精算师"]))
        self.assertEqual(parse("标签：爱因斯坦")["theme"], "einstein")
        self.assertEqual(parse("标签：爱提问、果核精算师")["theme"], "")
        self.assertEqual(parse("标签：AI因斯坦、AICU")["theme"], "")
        self.assertEqual(parse("主题：待定\n标签：AI因斯坦")["theme"], "")
        self.assertEqual(parse("主题：AICU\n标签：AI因斯坦")["theme"], "aicu")

    def test_annotations_bind_to_their_quote_without_changing_turn_order_or_counts(self):
        raw = ("PUAI 2026\n主题：puai\n范围：thread\n"
               "原话：03-08~多调研点啊，我缺你这点 token 吗？\n复读：4\n划线：这点 token\n"
               "AI：我继续。\n原话：03-08~就一页啊，尾款呢？\n划线：不存在的句子\n复读：50001\n"
               "日期账：03-08:2:1\n标签：尾款追缴")
        data = poster.parse_receipt(raw)
        self.assertEqual(data["repeats"], [4, None])
        self.assertEqual(data["emphases"], ["这点 token", "尾款呢？"])
        self.assertEqual(data["reply"], (1, "我继续。"))
        self.assertEqual((data["hits"], data["total"]), (1, 2))

        positions = {}
        draw_text = ImageDraw.ImageDraw.text
        def trace(draw, xy, label, *args, **kwargs):
            positions[label] = xy
            return draw_text(draw, xy, label, *args, **kwargs)

        face = poster.load_font(ROOT / "assets/SmileySans-Oblique.woff2")
        with patch.object(ImageDraw.ImageDraw, "text", trace):
            image = poster.draw_report(data, face)
        order = ["2026 PUAI 报告", "本次对话精选", "这点 token", "我继续。", "尾款呢？",
                 "记录里，你发出了", "发言日历", "片段标签", "扫码获取口令"]
        self.assertEqual([positions[k][1] for k in order], sorted(positions[k][1] for k in order))
        self.assertIn("复读×4", positions)
        for label, palette_slot in [("这点 token", 7), ("尾款呢？", 2)]:
            x, y = positions[label]
            self.assertEqual(image.getpixel((round(x), round(y)-3)), ImageColor.getrgb(poster.PALETTES["puai"][palette_slot]))

    def test_empty_or_generic_endings_do_not_get_an_invented_highlight(self):
        for line in ["就看看。", "少算了，对吧？", "我问的是，这样真的每次都能百分之百保证永远算对吗？"]:
            self.assertEqual(poster.quote_emphasis(line, None), "")
        data = poster.parse_receipt("PUAI 2026\n原话：不能再等了。\n前情：交稿\n复读：7\n划线：不能再等")
        self.assertEqual(data["emphases"], [""])
        self.assertEqual(data["repeats"], [None])


if __name__ == "__main__":
    unittest.main()
