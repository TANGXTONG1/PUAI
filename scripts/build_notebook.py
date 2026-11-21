"""Publish the same readable A-edition Pillow source inside the remote skill."""
import argparse
import ast
from hashlib import sha256
from pathlib import Path
import re


def build_notebook(root, docs=None):
    root = Path(root)
    renderer = (root / "scripts/render_chat_png.py").read_text(encoding="utf-8")
    adapter = (root / "scripts/notebook_card.py").read_text(encoding="utf-8")
    # CLI-only file I/O and piped input are unnecessary in a notebook. The parser,
    # fonts, nine editions and complete layout are the same functions as the CLI.
    renderer, _, rest = renderer.partition("\ndef display_chat_png(")
    adapter_header, separator, adapter = adapter.partition("def show_puai(")
    if not rest or not separator or "from render_chat_png import" not in adapter_header:
        raise ValueError("Could not locate both halves of the official notebook renderer")
    doc_end = ast.parse(renderer).body[0].end_lineno
    notebook_doc = '"""Official PUAI A poster. In this notebook import show_puai and pass a reviewed report.\n' \
                   'show_puai(receipt, output="/mnt/data/PUAI-2026.png") displays the PNG inline.\n"""\n'
    source = notebook_doc + "".join(renderer.splitlines(keepends=True)[doc_end:]).rstrip() + "\n\n\n" + separator + adapter
    # Browsing tools may return only a few thousand characters from raw assets.
    # Each numbered resource is a literal, contiguous slice of the complete file.
    parts, lines, size = [], [], 0
    for line in source.splitlines(keepends=True):
        if size >= 4700 and not line.strip():
            parts.append("".join(lines))
            lines, size = [], 0
        lines.append(line)
        size += len(line.encode("utf-8"))
    if lines:
        parts.append("".join(lines))

    generated = []
    if docs:
        docs = Path(docs)
        (docs / "notebook").mkdir(exist_ok=True)
        (docs / "notebook_card.py").write_text(source, encoding="utf-8")
        for old_part in (docs / "notebook").glob("[0-9][0-9].txt"):
            if int(old_part.stem) > len(parts):
                old_part.unlink()
    for number, part in enumerate(parts, start=1):
        filename = f"{number:02}.txt"
        url = "https://raw.githubusercontent.com/TANGXTONG1/PUAI/main/docs/notebook/" + filename
        generated.append(f"### A 版源码 {number}/{len(parts)} · [本段原文]({url})\n\n```python\n{part}```\n")
        if docs:
            (docs / "notebook" / filename).write_text(part, encoding="utf-8")
    marker = "<!-- generated notebook source -->"
    path = root / "SKILL.md"
    instructions, boundary, _ = path.read_text(encoding="utf-8").partition(marker)
    if not boundary:
        raise ValueError("Missing notebook source marker in SKILL.md")
    digest = sha256(source.encode("utf-8")).hexdigest()
    instructions, count = re.subn(r'^expected_sha256 = "[0-9a-f]{64}"$',
                                  f'expected_sha256 = "{digest}"', instructions, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("Expected a single digest for the downloadable official notebook")
    path.write_text(instructions + marker + "\n\n" + "\n".join(generated), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--docs", type=Path)
    args = parser.parse_args()
    build_notebook(args.root, args.docs)
