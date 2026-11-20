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
