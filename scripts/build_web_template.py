#!/usr/bin/env python3
"""Publish the skill's self-contained A poster template for the static /make/ page."""

from pathlib import Path
import subprocess

from build_report import embed_template_assets


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


if __name__ == "__main__":
    main()
