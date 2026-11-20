"""Display the official Pillow poster in a live notebook."""

from io import BytesIO
from pathlib import Path

from render_chat_png import draw_report, load_font, parse_receipt


def show_puai(receipt, *, output=None, font=None):
    """Render a reviewed PUAI report and publish the exact PNG pixels in this chat."""
    from IPython.display import Image as InlineImage, display

    poster = draw_report(parse_receipt(receipt), load_font(font))
    buffer = BytesIO()
    poster.save(buffer, format="PNG")
    pixels = buffer.getvalue()
    if output is not None:
        Path(output).write_bytes(pixels)
    display(InlineImage(data=pixels, format="png"), include=["image/png"])


def puai_card(*, name, theme, scope, turns=(), tags=(), days=None, dates=(),
              undated=None, tokens=None, scene="", year=2026, output=None, font=None,
              highlights=(), repeats=(), setup="", habits=()):
    """Accept the existing structured notebook inputs, including optional exact highlights."""
    fields = [f"PUAI {year}"]

    def add(label, value):
        if value is None or value == "":
            return
        if str(value).splitlines() != [str(value)]:
            raise ValueError(f"{label}只接受一行文字")
        fields.append(f"{label}：{value}")

    def count_row(pair):
        count, hits = pair
        return f"{count}:{'?' if hits is None else hits}"

    turns = list(turns)
    owner_count = sum(who == "本人" for who, _, _ in turns)
    if owner_count > 3 or len(turns) > 4 or max(len(highlights), len(repeats)) > owner_count:
        raise ValueError("精选一至三句本人原话，可带一个真实的 AI 回合")
    add("署名", name)
    add("主题", theme)
    add("范围", scope)
    add("前情", setup)
    add("主场景", scene)
    for habit in habits:
        add("用法", habit)
    for tag in tags:
        add("标签", tag)
    if days:
        add("日期账", ",".join(f"{stamp}:{count_row(pair)}" for stamp, pair in sorted(days.items())))
    add("发言日期", ",".join(dates))
    if undated is not None:
        add("无日期账", count_row(undated))
    add("Token", tokens)
    owner_index = 0
    for index, (who, stamp, quote) in enumerate(turns):
        if who == "本人":
            add("原话", f"{stamp}~{quote}" if stamp else quote)
            if owner_index < len(highlights):
                add("划线", highlights[owner_index])
            if owner_index < len(repeats):
                add("复读", repeats[owner_index])
            owner_index += 1
        elif who == "AI":
            add("AI收尾" if index == len(turns) - 1 else "AI", quote)
        else:
            raise ValueError("未知的说话人")
    show_puai("\n".join(fields), output=output, font=font)
