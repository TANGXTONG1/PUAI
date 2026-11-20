"""Verify the attachment path used by a chat sandbox with Python and Pillow only."""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops

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
    def test_partial_ledger_and_real_conversation_order(self):
        r = renderer.parse_receipt(RECEIPT)
        self.assertEqual(r["reply"], (1, "左边第二行说得更清楚。"))
        self.assertEqual((r["total"], len(r["days"]), r["hits"]), (7, 2, None))
        reviewed = renderer.parse_receipt(RECEIPT.replace("2:?", "2:1"))
        self.assertEqual(reviewed["hits"], 4)
        with self.assertRaises(ValueError):
            renderer.parse_receipt(RECEIPT.replace("11-04:3:2", "11-04:3:7"))

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

    def test_turn_selection_and_invalid_empty_source(self):
        self.assertIsNone(renderer.parse_receipt(
            "PUAI 2026\n原话：11-06~后来的问题。\nAI：不在其间。\n原话：11-01~早来的问题。")["reply"])
        with self.assertRaises(ValueError):
            renderer.parse_receipt("PUAI 2026\n署名：我\n标签：教学")

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
                self.assertEqual(zxingcpp.read_barcode(img).text, "https://xn--sxrw8m230b.com/PUAI/")


if __name__ == "__main__":
    unittest.main()
