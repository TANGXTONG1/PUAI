#!/usr/bin/env python3
"""Draw a PUAI chat attachment using only Python and Pillow.

python render_chat_png.py report.txt /mnt/data/PUAI-2026.png [--font /path/font.ttc]
Input is a PUAI year heading followed by the selected public Chinese report fields.
No account, browser, remote font, or rendering service is used.
"""
import argparse
import calendar
from collections import Counter, defaultdict
from datetime import date
from functools import lru_cache
import os
from pathlib import Path
import re
import tempfile

from PIL import Image, ImageDraw, ImageFont


EDITIONS = {
    "puai": ("PUAI", "开喷", "cobalt"), "teach": ("AI的教育", "教学", "cobalt"),
    "einstein": ("AI因斯坦", "追问", "cobalt"), "aicu": ("AICU", "急救", "orange"),
    "edison": ("AI迪生", "新点子", "orange"), "hush": ("AI在心口难开", "代写", "mint"),
    "free": ("AI咋咋地", "放权", "mint"), "all": ("AI特全体", "跨模型", "magenta"),
    "support": ("AI的供养", "应援", "magenta"), "": ("AI 相处", "", "cobalt"),
}
# Paper, ink, marker, marker text, second bubble, second bubble text, tint, calendar.
PALETTES = {
    "cobalt": ("#F3F6F6", "#142238", "#E5EE79", "#142238", "#16399A", "#F3F6F6", "#C7E1F4", "#2552AC"),
    "orange": ("#FCFAF6", "#26242A", "#FF9D53", "#252126", "#CEDCE3", "#212C33", "#FFE3BD", "#90390E"),
    "mint": ("#F1FCF7", "#142F2D", "#FFB4D8", "#292129", "#91E3CD", "#102E2A", "#D3F7E0", "#205955"),
    "magenta": ("#FFF5F9", "#301E30", "#9A2358", "#FFFFFF", "#F5B3D1", "#361829", "#CDDCFF", "#912755"),
}
# Same fixed homepage QR as the browser poster, rows encoded from left to right.
QR_ROWS = (
    0x1fc4527f, 0x1052e241, 0x174b415d, 0x1758df5d, 0x175a5f5d, 0x10433c41,
    0x1fd5557f, 0x1e1400, 0xbdb70da, 0xfaf5b1a, 0x5c0e8ec, 0x17a6d931,
    0x184551c2, 0x1b0aa055, 0xe6ab229, 0x232b11d, 0xd4d4b2b, 0x19a1df10,
    0x1ecaa639, 0x1ab330dc, 0x1e7549f7, 0x17a31e, 0x1fc3ef56, 0x1054bb1a,
    0x17557bf1, 0x175a2c2d, 0x174025b7, 0x105b9455, 0x1fcb9378,
)
FIELDS = "署名 主题 主场景 短评 前情 原话 ai ai收尾 用法 标签 日期账 无日期账 token".split()
UNKNOWN = {"", "?", "无", "未知", "留空", "未提供", "未核准", "未核实", "无法逐条核准", "—", "n/a"}
TOKEN_MAX = 2**53 - 1


def counts(value):
    match = re.fullmatch(r"([0-9]+):([0-9]+|\?)", value.strip())
    if not match:
        raise ValueError("发言账须采用 发言数:命中数，未核准的命中数写 ?")
    n = int(match[1])
    hits = None if match[2] == "?" else int(match[2])
    if not 0 < n <= TOKEN_MAX or hits is not None and hits > n:
        raise ValueError("发言账的总数或命中数无效")
    return n, hits


def day_key(year, value):
    if not re.fullmatch(r"\d\d-\d\d", value):
        raise ValueError("日期格式应为 MM-DD")
    return date.fromisoformat(f"{year}-{value}")


def parse_receipt(text):
    if len(text) > 48000:
        raise ValueError("报告过长")
    title = re.search(r"(?im)^\s*(?:#{1,6}\s+)?(?:\*\*)?PUAI\s+(20\d\d)(?:\*\*)?\s*$", text)
    if not title:
        raise ValueError("报告首行应为 PUAI 2026")
    year = int(title[1])
    values = defaultdict(list)
    lines = []
    for raw in text[title.end():].splitlines():
        line = raw.strip()
        if line.startswith(('```', '~~~')) or line == "报告结束":
            break
        match = re.match(r"^(?:[-*]\s+)?(?:\*\*)?([^:：*]+?)(?:\*\*)?\s*[:：](?:\*\*)?\s*(.+)$", line)
        if not match:
            continue
        field, value = match[1].lower(), match[2].strip()
        if field in FIELDS and value:
            values[field].append(value)
            lines.append((field, value))

    def first(name):
        return next(iter(values[name]), "")

    def stat(name):
        if len(values[name]) > 1:
            raise ValueError(f"重复的{name}")
        val = first(name)
        return "" if val.strip("（）()").lower() in UNKNOWN else val

    theme = first("主题").lower()
    theme = {v[0].lower(): k for k, v in EDITIONS.items()}.get(theme, theme)
    if theme in {"未归类", "无", "ai相处报告"}:
        theme = ""
    if theme not in EDITIONS:
        raise ValueError("未知主题")
    days = {}
    ledger = stat("日期账")
    if ledger:
        for piece in re.split(r"[,，]", ledger):
            dt, _, row = piece.strip().partition(":")
            key = day_key(year, dt)
            if key in days:
                raise ValueError("日期账重叠")
            days[key] = counts(row)
    undated = stat("无日期账")
    rows = list(days.values()) + ([counts(undated)] if undated else [])
    total = sum(n for n, _ in rows)
    if total > TOKEN_MAX:
        raise ValueError("计数超出范围")
    hits = sum(h for _, h in rows) if rows and theme and all(h is not None for _, h in rows) else None
    if not theme and any(h is not None for _, h in rows):
        raise ValueError("未归类时命中数应为 ?")
    tokens = stat("token")
    if tokens and (not re.fullmatch(r"[0-9]+", tokens) or int(tokens) > TOKEN_MAX):
        raise ValueError("Token 须为已核准的整数")
    quotes = []
    reply = None
    for index, (kind, value) in enumerate(lines):
        if kind == "原话" and len(quotes) < 3:
            prefix = re.match(r"^(\d\d-\d\d)~", value)
            stamp = day_key(year, prefix[1]) if prefix else None
            value = value[prefix.end():] if prefix else value
            if not value or len(value) > 80:
                raise ValueError("每条本人原话应为 1–80 字的连续原文")
            quotes.append((stamp, value))
        elif kind == "ai" and reply is None and 0 < len(quotes) < 3 and len(value) <= 80:
            if index > 0 and index+1 < len(lines) and lines[index-1][0] == lines[index+1][0] == "原话":
                reply = (len(quotes), value)
    if rows and (len(quotes) > total or any(day not in days or n > days[day][0]
                                             for day, n in Counter(d for d, _ in quotes if d).items())):
        raise ValueError("引语与发言账不符")
    if reply:
        pos = reply[0]
        if pos >= len(quotes) or quotes[pos-1][0] and quotes[pos][0] and quotes[pos-1][0] > quotes[pos][0]:
            reply = None
    if not reply and quotes:
        # A trailing "AI" is commonly an assistant's unselected extra turn. Only an
        # explicit AI收尾 after the final retained user turn can supply the last beat.
        selected = [(kind, value) for kind, value in lines if kind in {"原话", "ai", "ai收尾"}]
        if (len(values["原话"]) == len(quotes) and selected[-1][0] == "ai收尾"
                and len(selected) >= 2 and selected[-2][0] == "原话" and len(selected[-1][1]) <= 80):
            reply = (len(quotes), selected[-1][1])
    lead = first("主场景")
    if len(lead) > 90:
        raise ValueError("主场景最多 90 字")
    habits = list(dict.fromkeys(values["用法"]))[:3]
    if not (quotes or lead or habits or total):
        raise ValueError("缺少可核对的发言、现场或具体用法")
    tags = [tag.strip() for line in values["标签"] for tag in line.split("、") if tag.strip()]
    return dict(year=year, theme=theme, name=first("署名")[:16] or "我", lead=lead, quotes=quotes,
                reply=reply, setup=first("前情") if len(first("前情")) <= 24 else "", short=first("短评")[:100],
                habits=[h[:120] for h in habits if h != lead], tags=list(dict.fromkeys(tags))[:3],
                days=days, total=total, hits=hits, tokens=int(tokens) if tokens else None)


def load_font(path=None):
    candidates = [path] if path else [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc", "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyh.ttc", Path(__file__).resolve().parents[1]/"assets/SmileySans-Oblique.woff2",
        Path(__file__).with_name("SmileySans-Oblique.woff2"),
    ]
    for filename in candidates:
        try:
            f = ImageFont.truetype(str(filename), 24)
            if len({bytes(f.getmask(ch)) for ch in "中文图"}) == 3:
                return lru_cache(maxsize=32)(lambda size: ImageFont.truetype(str(filename), size))
        except OSError:
            continue
    raise ValueError("找不到可绘制中文的字体。请用 --font 指定 Noto Sans CJK 或包内 SmileySans 字体")


def draw_report(r, font):
    year, theme = r["year"], r["theme"]
    name, theme_label, palette = EDITIONS[theme]
    paper, ink, accent, on_accent, pull, on_pull, tint, calendar_ink = PALETTES[palette]
    commands = []

    def cmd(method, *args, **kwargs):
        commands.append((method, args, kwargs))

    def text(x, y, value, size, color=ink, bold=False, align="lt"):
        cmd("text", (x, y), str(value), font=font(size), fill=color, anchor=align,
            stroke_width=1 if bold else 0, stroke_fill=color)

    def wrap(value, width, size):
        # Keep Latin words intact whenever they fit, breaking an overlong token only when necessary.
        face = font(size)
        def fit(line_width):
            rows, current = [], ""
            for token in re.findall(r"[A-Za-z0-9_]+|.", value):
                for part in ([token] if face.getlength(token) <= line_width else list(token)):
                    if current and face.getlength(current + part) > line_width:
                        rows.append(current)
                        current = ""
                    current += part
            return rows + ([current] if current else [])

        rows = fit(width)
        # Keep short punch lines in one bubble without stranding one character on its own.
        if len(rows) > 1 and face.getlength(rows[-1]) < width * .3:
            for smaller in range(width - size, int(width * .65), -size):
                candidate = fit(smaller)
                if len(candidate) != len(rows):
                    break
                rows = candidate
                if face.getlength(rows[-1]) >= width * .3:
                    break
        return rows

    def paragraph(x, y, rows, size, color=ink, bold=False):
        for row in rows:
            text(x, y, row, size, color, bold)
            y += round(size*1.38)
        return y

    def rect(x, y, w, h, color, outline=None, radius=0):
        cmd("rounded_rectangle", (x, y, x+w, y+h), radius=radius, fill=color, outline=outline,
            width=2 if outline else 1)

    def heading(y, title):
        text(48, y, title, 38, bold=True)
        rect(48, y+42, round(font(38).getlength(title)), 6, accent)
        return y+70

    badge = r["name"]+"的"
    badge_w = min(round(font(34).getlength(badge))+44, 804)
    rect(48, 36, badge_w, 56, accent)
    text(48+badge_w/2, 66, badge, 34, on_accent, True, "mm")
    text(48, 118, f"{year} {name}报告" if not theme else f"{year} {name} 报告", 64, bold=True)
    y = 226
    if r["lead"]:
        y = heading(y, "年度现场")
        rows = wrap(r["lead"], 720, 45)
        height = len(rows)*62+60
        rect(48, y, 804, height, pull)
        rect(48, y, 10, height, accent)
        paragraph(82, y+30, rows, 45, on_pull, True)
        y += height+38

    quotes = r["quotes"]
    if quotes:
        y = heading(y, "对话现场" if r["reply"] else "本人原话")
        if r["setup"]:
            y = paragraph(48, y, wrap(r["setup"], 800, 32), 32)+14
        for i, (dt, quote) in enumerate(quotes):
            rows = wrap(quote, 732, 46)
            header = "本人" + (f"  {dt.month:02}.{dt.day:02}" if dt else "")
            height = 76 + len(rows)*63 + 18
            fill, fg = (pull, on_pull) if i == 1 else (tint if i == 2 else "#FCFCFA", ink)
            rect(48, y, 804, height, fill, ink, 24)
            tail = 716 if i == 1 else 116
            poly = [(tail, y+height-1),(tail+48,y+height-1),(tail+(62 if i==1 else -17),y+height+19)]
            cmd("polygon", poly, fill=fill)
            cmd("line", [poly[0],poly[2],poly[1]], fill=ink, width=2)
            text(82, y+22, header, 29, fg, True)
            paragraph(82, y+70, rows, 46, fg, True)
            y += height+39
            if r["reply"] and r["reply"][0] == i+1:
                rows = wrap(r["reply"][1], 594, 36)
                height = len(rows)*50+40
                rect(92,y,716,height,tint,radius=12)
                text(113,y+21,"AI",34,bold=True)
                cmd("line",(167,y+16,167,y+height-15),fill=ink,width=2)
                paragraph(186,y+20,rows,36)
                y += height+21

    if not quotes and not r["lead"] and r["short"] and not r["habits"]:
        y = paragraph(48,y,wrap(r["short"],800,41),41,bold=True)+28
    if r["total"] or r["tokens"] is not None:
        y = heading(y,"对话用量")
        ratio = None if r["hits"] is None else r["hits"]/r["total"]
        width = 558 if ratio is not None else 804
        lines = []
        if r["tokens"] is not None:
            lines.append(f'至少 {r["tokens"]:,} token')
        if r["total"]:
            lines.append(f'{r["total"]:,} 条指令')
        height = max(130,30+len(lines)*62)
        rect(48,y,width,height,pull)
        for i, val in enumerate(lines):
            size = 48
            while size > 28 and font(size).getlength(val) > width-40:
                size -= 2
            text(70,y+25+i*62,val,size,on_pull,True)
        if ratio is not None:
            cx, cy, rad = 732, y+56, 53
            cmd("ellipse",(cx-rad,cy-rad,cx+rad,cy+rad),outline=tint,width=12)
            if ratio:
                cmd("arc",(cx-rad,cy-rad,cx+rad,cy+rad),-90,-90+ratio*360,fill=calendar_ink,width=12)
            text(cx,cy,f"{ratio*100:.1f}".removesuffix(".0")+"%",28,align="mm")
            text(cx,y+120,theme_label+"占比",27,align="mt")
        y += max(height,160 if ratio is not None else 0)+31

    if r["days"]:
        days = r["days"]
        y = heading(y,"发言日历")
        peak = min(days,key=lambda d:(-days[d][0],d))
        active_label = f"活跃 {len(days)} 天"
        if theme and all(h is not None for _, h in days.values()):
            themed_days = sum(h > 0 for _, h in days.values())
            active_label += f" · {themed_days} 天{theme_label}"
        facts = active_label + f"    单日最高 {peak.month}.{peak.day:02} · {days[peak][0]} 条"
        y = paragraph(48, y, wrap(facts, 804, 33), 33) + 21
        month_counts = Counter(day.month for day in days)
        month_messages = Counter()
        for day, (n, _) in days.items():
            month_messages[day.month] += n
        selected = sorted(sorted(month_counts, key=lambda m: (-month_counts[m], -month_messages[m], -m))[:3])

        card_width = (804-18*(len(selected)-1))//len(selected)
        for i,month in enumerate(selected):
            x = 48+i*(card_width+18)
            rect(x,y,card_width,234,"#FBFBF9",ink,12)
            text(x+20,y+18,f"{month:02} 月",30,bold=True)
            step = min(30,(card_width-35)//7)
            for week,dates in enumerate(calendar.Calendar(0).monthdayscalendar(year,month)):
                for weekday,day in enumerate(dates):
                    if not day:
                        continue
                    record = days.get(date(year,month,day))
                    fill = calendar_ink if record and record[1] else ink if record else None
                    xx, yy = x+18+weekday*step,y+64+week*25
                    cmd("ellipse",(xx,yy,xx+17,yy+17),fill=fill,outline=fill or "#A7B2B4",width=2)
        y += 251
        legend = [("发言", ink), ("缺记录", None)]
        if any(h for _,h in days.values()):
            legend.append((theme_label, calendar_ink))
        for i,(label,fill) in enumerate(legend):
            x = 48+i*172
            cmd("ellipse",(x,y+3,x+16,y+19),fill=fill,outline=fill or "#88939A",width=2)
            text(x+27,y,label,27)

        y += 61
    habits = r["habits"][:2] if r["lead"] or quotes else r["habits"]
    if habits:
        y = heading(y,"日常用法")
        for habit in habits:
            y = paragraph(48,y,wrap(habit,804,38),38)+17
        y += 12
    if r["tags"]:
        zone = y
        rect(0,zone,900,149,tint)
        text(48,zone+19,"人格标签",31,bold=True)
        x = 48
        for tag in r["tags"]:
            tag = tag[:6]
            width = round(font(33).getlength(tag))+34
            rect(x,zone+64,width,55,paper,ink)
            text(x+width/2,zone+92,tag,33,bold=True,align="mm")
            x += width+17
        y += 170
    rect(0,y,900,198,"#FBFBF8")
    text(48,y+35,"扫码复制 → 发到你常聊的 GPT",37,bold=True)
    text(48,y+105,"唐苑容.com/PUAI/go.txt",31)
    rect(690,y+16,164,164,"#FFFFFF")
    for row,bits in enumerate(QR_ROWS):
        for col in range(29):
            if bits & (1 << (28-col)):
                rect(713+4*col,y+40+4*row,3,3,"#101824")
    img = Image.new("RGB",(900,y+198),paper)
    draw = ImageDraw.Draw(img)
    for method,args,kwargs in commands:
        getattr(draw,method)(*args,**kwargs)
    return img


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--font", type=Path)
    args = parser.parse_args()
    if args.report.stat().st_size > 192000:
        parser.error("报告过长")
    report = parse_receipt(args.report.read_text(encoding="utf-8"))
    image = draw_report(report, load_font(args.font))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Leave only complete, verifiable PNGs at the public attachment path.
    with tempfile.NamedTemporaryFile(dir=args.output.parent,suffix=".png",delete=False) as handle:
        temp = Path(handle.name)
    try:
        image.save(temp, format="PNG")
        with Image.open(temp) as check:
            check.verify()
        os.replace(temp,args.output)
    finally:
        temp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
