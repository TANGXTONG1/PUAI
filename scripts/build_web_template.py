#!/usr/bin/env python3
"""Publish the skill's self-contained A poster template for the static /make/ page."""

from hashlib import sha256
from pathlib import Path
import re
import subprocess

from build_report import embed_template_assets


def update_asset_version(page, asset):
    version = sha256(asset.read_bytes()).hexdigest()[:10]
    expression = re.escape(asset.name) + r"\?v=[0-9a-f]+"
    contents, changes = re.subn(expression, f"{asset.name}?v={version}", page.read_text(encoding="utf-8"))
    if changes != 1:
        raise ValueError(f"Expected one versioned link to {asset.name} in {page.name}")
    page.write_text(contents, encoding="utf-8")


def main():
    root = Path(__file__).resolve().parents[1]
    template = (root / "assets" / "comic-template.html").read_text(encoding="utf-8")
    frame = embed_template_assets(template)
    if frame.count("__REPORT_JSON__") != 1:
        raise ValueError("The static frame needs exactly one report data marker")
    path = root / "docs" / "make" / "poster-frame.txt"
    path.write_text(frame, encoding="utf-8")
    prompt_js = (root / "assets" / "portable-prompt.js").read_text(encoding="utf-8")
    prompt = subprocess.run(
        ["node", "-"], input=prompt_js + "\nconsole.log(puaiPortablePrompt());",
        encoding="utf-8", capture_output=True, check=True,
    ).stdout
    (root / "docs" / "portable-prompt.js").write_text(prompt_js, encoding="utf-8")
    (root / "docs" / "go.txt").write_text(prompt, encoding="utf-8")
    docs = root / "docs"
    make = docs / "make"
    for page in ("index.html", "sample.html"):
        update_asset_version(docs / page, docs / "portable-prompt.js")
    update_asset_version(make / "plain-report.mjs", make / "report-code.mjs")
    update_asset_version(make / "make.js", make / "report-code.mjs")
    update_asset_version(make / "make.js", make / "plain-report.mjs")
    update_asset_version(make / "make.js", path)
    update_asset_version(make / "index.html", make / "make.js")


if __name__ == "__main__":
    main()
