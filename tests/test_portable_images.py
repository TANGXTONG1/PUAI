"""Replay whole assistant replies in three browsers against the real static site."""
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import struct
import threading
import unittest

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless(sync_playwright, "Install Python Playwright and its browsers for image tests")
class PortableImages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(QuietHandler, directory=ROOT / "docs")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}/make/"
        cls.runtime = sync_playwright().start()
        cls.addClassCleanup(cls.runtime.stop)
        cls.replies = json.loads((ROOT / "tests/editorial/portable-replies.json").read_text())

    def check_engine(self, engine, device=None):
        browser_type = getattr(self.runtime, engine)
        if not Path(browser_type.executable_path).is_file():
            self.skipTest(f"Install Playwright {engine}")
        browser = browser_type.launch()
        self.addCleanup(browser.close)
        context = browser.new_context(**(self.runtime.devices[device] if device else {}))
        for item in self.replies:
            with self.subTest(case=item["case"]):
                page = context.new_page()
                page.goto(self.base)
                page.locator("#code").fill(item["reply"])
                page.locator('button[type="submit"]').click()
                page.wait_for_function('document.querySelector("#preview").naturalWidth === 900')
                transcript = page.locator("#preview").get_attribute("alt")
                positions = [transcript.index(text) for text in item["in_order"]]
                self.assertEqual(positions, sorted(positions))
                for text in item["absent"]:
                    self.assertNotIn(text, transcript)
                with page.expect_download() as download:
                    page.locator("#save").click()
                with download.value.path().open("rb") as png:
                    header = png.read(24)
                self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(struct.unpack(">I", header[16:20])[0], 900)
                page.close()

    def test_chromium(self):
        self.check_engine("chromium", "Pixel 7")

    def test_webkit(self):
        self.check_engine("webkit", "iPhone 13")

    def test_firefox(self):
        self.check_engine("firefox")
