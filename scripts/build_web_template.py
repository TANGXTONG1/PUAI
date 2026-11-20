#!/usr/bin/env python3
"""Publish the skill's self-contained A poster template for the static /make/ page."""

from hashlib import sha256
from pathlib import Path
import re
import shutil
import subprocess

from build_report import embed_template_assets
from build_notebook import build_notebook


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
    build_notebook(root, docs)
    # Keep the attachable skill and its relative references browsable from Pages.
    for relative in ("SKILL.md", "references/scene-selection.md", "references/report-schema.md",
                     "references/png-export.md"):
        target = docs / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, target)
    shutil.copyfile(root / "SKILL.md", docs / "skill.txt")
    for script in ("render_chat_png.py", "collect_history.py", "read_context.py", "browse_history.py", "compare_scenes.py"):
        shutil.copyfile(root / "scripts" / script, docs / script)
    make = docs / "make"
    # The date-recovery button sends the originating chat to the same skill as go.txt.
    page = make / "index.html"
    html, changed = re.subn(r'(id="dates-copy" data-skill=")[^"]*(")',
                            lambda m: m[1] + prompt.strip().splitlines()[-1] + m[2],
                            page.read_text(encoding="utf-8"))
    if changed != 1:
        raise ValueError("Missing date-recovery skill address")
    page.write_text(html, encoding="utf-8")
    for page in ("index.html", "sample.html"):
        update_asset_version(docs / page, docs / "portable-prompt.js")
    update_asset_version(make / "plain-report.mjs", make / "report-code.mjs")
    update_asset_version(make / "make.js", make / "report-code.mjs")
    update_asset_version(make / "make.js", make / "plain-report.mjs")
    update_asset_version(make / "make.js", path)
    update_asset_version(make / "index.html", make / "make.js")


if __name__ == "__main__":
    main()
