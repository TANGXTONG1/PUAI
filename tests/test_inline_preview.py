"""Exercise display of a rendered report in an actual notebook output cell."""
import base64
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/render_chat_png.py"


class InlinePreviewTests(unittest.TestCase):
    def test_remote_skill_contains_the_offline_notebook_program(self):
        import re
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        embedded = re.search(r"## 离线对话画布.*?```python\n(.*?)```", skill, re.S)
        self.assertIsNotNone(embedded, "a link-only skill leaves an offline kernel without a renderer")
        self.assertEqual(embedded.group(1), (SCRIPT.parent / "notebook_card.py").read_text(encoding="utf-8"))

    @unittest.skipUnless(importlib.util.find_spec("ipykernel") and importlib.util.find_spec("jupyter_client"),
                         "requires Jupyter for rich-output integration")
    def test_offline_cell_only_needs_the_skill_text_and_its_own_report(self):
        import re
        from io import BytesIO
        from jupyter_client.manager import run_kernel
        from PIL import Image

        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        program = re.search(r"## 离线对话画布.*?```python\n(.*?)```", skill, re.S).group(1)
        # Run the published text in a fresh directory. No repository imports, HTTP or ZIP download.
        with tempfile.TemporaryDirectory() as directory, run_kernel(cwd=directory) as client:
            initialization = "import socket\ndef offline(*args, **kwargs):\n    raise AssertionError('external network')\nsocket.create_connection = offline\n"
            code = initialization + program + "\npuai_card(name='探班员', theme='puai', scope='fragments', turns=[('本人', '08-20', '这锅谁来背？')], dates=['08-20','10-01'], days={'11-02':(9,None)}, tags=['锅盖批发'], output='report.png')"
            messages = []
            reply = client.execute_interactive(code, output_hook=messages.append, timeout=45)
            file_for_chat = (Path(directory) / "report.png").read_bytes()
        self.assertEqual(reply["content"]["status"], "ok", reply["content"])
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
