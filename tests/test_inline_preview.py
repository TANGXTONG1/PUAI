"""Exercise display of a rendered report in an actual notebook output cell."""
import base64
import importlib.util
from io import BytesIO
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/render_chat_png.py"


def notebook_parts():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    appendix = skill.split("<!-- generated notebook source -->", 1)[1]
    return re.findall(r"```python\n(.*?)^```$", appendix, re.S | re.M)


class InlinePreviewTests(unittest.TestCase):
    def test_public_notebook_loader_checks_exact_source_before_execution(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        section = skill.split("## 联网加载官方模板\n", 1)[1].split("## 离线对话画布", 1)[0]
        cell = re.search(r"```python\n(.*?)^```$", section, re.S | re.M)[1]
        url = "https://raw.githubusercontent.com/TANGXTONG1/PUAI/main/docs/notebook_card.py"
        font_url = "https://raw.githubusercontent.com/TANGXTONG1/PUAI/main/assets/SmileySans-Oblique.woff2"
        source = (ROOT / "docs/notebook_card.py").read_bytes()
        font = (ROOT / "assets/SmileySans-Oblique.woff2").read_bytes()
        with patch("urllib.request.urlopen", return_value=BytesIO(b"raise RuntimeError()")) as get:
            with self.assertRaisesRegex(ValueError, "模板版本"):
                exec(cell, {})
            get.assert_called_once_with(url, timeout=8)

        # Observe the last display call while the font's temporary directory exists.
        # The separate kernel test below exercises the real PNG display.
        self.assertEqual(cell.count('renderer["show_puai"](receipt, output=output)'), 1)
        inspect = cell.replace('renderer["show_puai"](receipt, output=output)',
                               'observed = (callable(renderer["show_puai"]), (path / "SmileySans-Oblique.woff2").exists())')
        for response, available in [(BytesIO(font), True), (BytesIO(b"wrong font"), False), (OSError("offline"), False)]:
            with self.subTest(available=available):
                with patch("urllib.request.urlopen", side_effect=[BytesIO(source), response]) as get:
                    loaded = {}
                    exec(inspect, loaded)
                    self.assertEqual(loaded["observed"], (True, available))
                    self.assertEqual(get.call_args_list[1].args, (font_url,))
                    self.assertFalse(loaded["path"].exists())

    def test_remote_skill_carries_the_complete_print_renderer(self):
        parts = notebook_parts()
        self.assertTrue(parts)
        source = "".join(parts)
        self.assertEqual(source, (ROOT / "docs/notebook_card.py").read_text(encoding="utf-8"))
        official = SCRIPT.read_text(encoding="utf-8").split("\ndef display_chat_png(", 1)[0].rstrip()
        self.assertIn(official[official.index("EDITIONS ="):], source)
        for i, part in enumerate(parts, 1):
            self.assertEqual(part, (ROOT / f"docs/notebook/{i:02}.txt").read_text(encoding="utf-8"))

    @unittest.skipUnless(importlib.util.find_spec("ipykernel") and importlib.util.find_spec("jupyter_client"),
                         "requires Jupyter for rich-output integration")
    def test_offline_notebook_displays_the_full_poster_pixel_for_pixel(self):
        from io import BytesIO
        from jupyter_client.manager import run_kernel
        from PIL import Image

        receipt = ("PUAI 2026\n署名：探班员\n主题：puai\n范围：fragments\n"
                   "原话：08-20~这锅谁来背？\n划线：谁来背？\n复读：2\n"
                   "日期账：11-02:9:?\n发言日期：08-20,10-01\n标签：锅盖批发")
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            with run_kernel(cwd=directory) as client:
                deny_network = ("import socket\ndef offline(*args, **kwargs): raise AssertionError('external network')"
                                "\nsocket.create_connection = offline")
                client.execute_interactive(deny_network, timeout=10)
                for i, part in enumerate(notebook_parts()):
                    magic = "%%writefile " + ("-a " if i else "") + "puai_notebook.py\n"
                    reply = client.execute_interactive(magic + part, output_hook=lambda msg: None, timeout=10)
                    self.assertEqual(reply["content"]["status"], "ok", reply["content"])
                messages = []
                call = f"from puai_notebook import show_puai\nshow_puai({receipt!r}, output='report.png')"
                reply = client.execute_interactive(call, output_hook=messages.append, timeout=45)
                self.assertEqual(reply["content"]["status"], "ok", reply["content"])
                legacy = ("from puai_notebook import puai_card\n"
                          "puai_card(name='探班员', theme='puai', scope='fragments', "
                          "turns=[('本人','08-20','这锅谁来背？')], highlights=['谁来背？'], repeats=[2], "
                          "tags=['锅盖批发'], days={'11-02':(9,None)}, dates=['08-20','10-01'], "
                          "output='structured.png')")
                reply = client.execute_interactive(legacy, output_hook=lambda msg: None, timeout=45)
                self.assertEqual(reply["content"]["status"], "ok", reply["content"])
            file_for_chat = (work / "report.png").read_bytes()
            self.assertEqual(file_for_chat, (work / "structured.png").read_bytes())
            # Run the actual installed CLI with the same locally available fonts.
            (work / "renderer.py").write_bytes(SCRIPT.read_bytes())
            (work / "report.txt").write_text(receipt, encoding="utf-8")
            subprocess.run([sys.executable, work / "renderer.py", work / "report.txt", work / "cli.png"], check=True)
            self.assertEqual(file_for_chat, (work / "cli.png").read_bytes())
        displays = [msg["content"]["data"] for msg in messages if msg["msg_type"] == "display_data"]
        self.assertEqual(len(displays), 1)
        self.assertEqual(set(displays[0]), {"image/png"})
        self.assertEqual(base64.b64decode(displays[0]["image/png"]), file_for_chat)
        with Image.open(BytesIO(file_for_chat)) as image:
            self.assertEqual((image.format, image.width), ("PNG", 900))
            self.assertGreater(image.height, 1100)
            if importlib.util.find_spec("zxingcpp"):
                import zxingcpp
                self.assertEqual(zxingcpp.read_barcode(image).text, "https://xn--sxrw8m230b.com/PUAI/#go")

    @unittest.skipUnless(importlib.util.find_spec("pymupdf"), "requires the embedded CJK font")
    def test_full_renderer_works_without_system_fonts(self):
        from io import BytesIO
        from unittest.mock import patch
        from PIL import ImageFont
        spec = importlib.util.spec_from_file_location("puai_renderer", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        truetype = ImageFont.truetype

        def embedded_only(source, *args, **kwargs):
            if not isinstance(source, BytesIO):
                raise OSError("test kernel has no CJK font files")
            return truetype(source, *args, **kwargs)

        with patch.object(ImageFont, "truetype", embedded_only):
            face = module.load_font()(32)
            self.assertEqual(len({bytes(face.getmask(ch)) for ch in "年月日"}), 3)

    def test_plain_python_reports_no_inline_output(self):
        code = f"""
import sys
sys.path.insert(0, {str(SCRIPT.parent)!r})
from render_chat_png import display_chat_png
try:
    display_chat_png('report.png')
except RuntimeError as exc:
    assert 'kernel' in str(exc), str(exc)
else:
    raise AssertionError('reported a preview in an ordinary terminal')
"""
        result = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    @unittest.skipUnless(importlib.util.find_spec("ipykernel") and importlib.util.find_spec("jupyter_client"),
                         "requires Jupyter for rich-output integration")
    def test_notebook_publishes_the_complete_report_png(self):
        from jupyter_client.manager import run_kernel
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            receipt, png = work / "report.txt", work / "report.png"
            receipt.write_text("PUAI 2026\n署名：试读者\n原话：你又把茶杯算了两遍？", encoding="utf-8")
            subprocess.run([sys.executable, SCRIPT, receipt, png, "--font", ROOT / "assets/SmileySans-Oblique.woff2"],
                           check=True)
            code = (f"import sys\nsys.path.insert(0, {str(SCRIPT.parent)!r})\n"
                    f"from render_chat_png import display_chat_png\ndisplay_chat_png({str(png)!r})")
            outputs = []
            with run_kernel() as client:
                reply = client.execute_interactive(code, output_hook=outputs.append, timeout=30)
            self.assertEqual(reply["content"]["status"], "ok", reply["content"])
            displays = [msg["content"]["data"] for msg in outputs if msg["msg_type"] == "display_data"]
            self.assertEqual(len(displays), 1)
            self.assertEqual(set(displays[0]), {"image/png"})
            self.assertEqual(base64.b64decode(displays[0]["image/png"]), png.read_bytes())
            with Image.open(png) as poster:
                self.assertEqual((poster.format, poster.width), ("PNG", 900))
