"""Render the nine official sample HTML files to PNG and record their crop coordinates.

From the repository root:
  node samples/build-gallery.mjs /tmp/puai-gallery
  python samples/render-gallery.py /tmp/puai-gallery
  python samples/build-previews.py /tmp/puai-gallery

Install Python Playwright and use installed Chrome (default) or pass --channel chromium
after running playwright install chromium. The final step also uses Pillow.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
READ_POSTER = """() => ({
    title: edition.name, w: canvas.width, h: canvas.height, footer: shareFooterHeight,
    stickers: stickerLayouts, paper, pull: colors.pull, onPull: colors.onPull, accent,
    alt: document.getElementById('preview').alt, src: document.getElementById('preview').src
})"""


def render(source, channel):
    cases = json.loads((ROOT / "samples/gallery.json").read_text(encoding="utf-8"))["editions"]
    metadata = {}
    with TemporaryDirectory(dir=source) as temp, sync_playwright() as playwright:
        staged = Path(temp)
        browser = playwright.chromium.launch(channel=channel)
        page = browser.new_page(viewport={"width": 390, "height": 844}, offline=True)
        for key in ["puai", *cases]:
            report = json.loads((source / f"{key}.json").read_text(encoding="utf-8"))
            page.goto((source / f"{key}.html").as_uri())
            page.wait_for_function("document.getElementById('preview').naturalWidth === 900 "
                                   "&& !document.getElementById('save').disabled")
            entry = page.evaluate(READ_POSTER)
            activity = report["activity"]
            quoted = [q["text"] for q in activity["share_quotes"]]
            if quoted != [sticker["text"] for sticker in entry["stickers"]]:
                raise ValueError(f"The canvas for {key} differs from the selected source quotes.")
            prefix, encoded = entry.pop("src").split(",", 1)
            if prefix != "data:image/png;base64":
                raise ValueError(f"The {key} template did not produce a PNG.")
            png = base64.b64decode(encoded, validate=True)
            (staged / f"{key}.png").write_bytes(png)
            summary = activity["summary"]
            entry.update(version=hashlib.sha256(png).hexdigest()[:10],
                         name=report["person"]["name"], tags=report["keywords"],
                         count=summary["messages"], days=len(activity["days"]),
                         hits=summary.get("roast_messages", activity.get("theme_stats", {}).get("messages")))
            metadata[key] = entry
        browser.close()
        (staged / "meta.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
        for key in metadata:
            (staged / f"{key}.png").replace(source / f"{key}.png")
        (staged / "meta.json").replace(source / "meta.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="Directory populated by build-gallery.mjs")
    parser.add_argument("--channel", default="chrome", help="Playwright browser channel (default chrome)")
    args = parser.parse_args()
    render(args.source.resolve(), args.channel)
