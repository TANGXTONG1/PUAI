#!/usr/bin/env python3
"""Draw a PUAI chat attachment using only Python and Pillow.

python render_chat_png.py report.txt /mnt/data/PUAI-2026.png [--font /path/font.ttc]
In a notebook cell, call display_chat_png(output_path) to publish the PNG inline.
Input is a PUAI year heading followed by the selected public Chinese report fields.
No account, browser, remote font, or rendering service is used.
"""
import argparse
import calendar
from collections import Counter, defaultdict
from datetime import date
from functools import lru_cache
from io import BytesIO
import os
from pathlib import Path
import re
import tempfile

from PIL import Image, ImageDraw, ImageFont


EDITIONS = {
    "puai": ("PUAI", "开喷"),
    "teach": ("AI的教育", "教学"),
    "aicu": ("AICU", "急救"),
    "all": ("AI特全体", "跨模型"),
    "hush": ("AI在心口难开", "代写"),
    "einstein": ("AI因斯坦", "追问"),
    "edison": ("AI迪生", "新点子"),
    "support": ("AI的供养", "应援"),
    "free": ("AI咋咋地", "放权"),
    "": ("AI 相处", ""),
}
# Paper, text, signature, on-signature, main sticker, on-sticker,
# light sticker, type badge, calendar. Keep in sync with the Canvas editions.
PALETTES = {
    "puai": ("#F3F6F6", "#142238", "#E5EE79", "#142238", "#16399A", "#F3F6F6", "#C7E1F4", "#DFE6F2", "#2552AC"),
    "teach": ("#F5FBF4", "#122C23", "#B8F178", "#173023", "#087A54", "#FFFFFF", "#99E7B8", "#D9F2DD", "#006247"),
    "aicu": ("#FFFAF4", "#322016", "#CEDCE3", "#212C33", "#FF8643", "#301B12", "#FFC79E", "#FFE0C4", "#943C12"),
    "all": ("#F8F6FF", "#271B39", "#B7F4DC", "#152D28", "#A180F5", "#211435", "#D5C7FA", "#E8E2F7", "#6641AA"),
    "hush": ("#FFF7F4", "#342020", "#D4C0EE", "#302139", "#FFABA3", "#342020", "#FFD2CC", "#F4DFEB", "#964B54"),
    "einstein": ("#F2FBFC", "#0C2C34", "#C5D6FF", "#142739", "#32CCDB", "#0C2C34", "#A4EEF0", "#D1EEF1", "#006A78"),
    "edison": ("#FFFBEE", "#302615", "#62379E", "#FFFFFF", "#FFCA29", "#302615", "#FFE395", "#F7EAC7", "#7E5412"),
    "support": ("#FFF5F9", "#301E30", "#9A2358", "#FFFFFF", "#F16DBD", "#33182C", "#FEC9E3", "#FFE0EB", "#912755"),
    "free": ("#FAFBEF", "#262E14", "#A0E3C7", "#152C22", "#C8E73F", "#262E14", "#E3F59E", "#E6EED1", "#556A14"),
    "": ("#F6F6F4", "#232B30", "#E6E8E1", "#232B30", "#CDD4D6", "#232B30", "#E0E5E4", "#E6EAE8", "#52606A"),
}
# Same offline QR as the web poster, for https://xn--sxrw8m230b.com/PUAI/#go
QR_ROWS = (
    0x1fc08c87f, 0x105b77041, 0x174ab2b5d, 0x175e3555d, 0x175e3865d, 0x104796541,
    0x1fd55557f, 0x1284200, 0xbd81d2da, 0x7851fa1c, 0xbd61061f, 0x12b696ea7,
    0x1e6fda9f0, 0x10e1f1a8, 0xef5bf45c, 0x1a0125695, 0x1bfed05f8, 0x2b6e61d5,
    0x1d404fe2d, 0xc102d41c, 0xad13afba, 0x1d34bc238, 0x147a53603, 0x12871b037,
    0x1e718c7f7, 0x1991d16, 0x1fc53b354, 0x1057ecd1c, 0x17578aff2, 0x175968ead,
    0x17440ecbf, 0x105e870ff, 0x1fcc7e37c,
)
FIELDS = "署名 主题 范围 主场景 短评 前情 原话 ai ai收尾 用法 标签 日期账 发言日期 无日期账 token".split()
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
        if field in {"人物类型", "人格类型", "年度类型", "本次类型"}:
            field = "主题"
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
    if theme == "爱因斯坦":
        theme = "einstein"
    elif theme in {"待定", "未归类", "无", "ai相处报告"}:
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
    raw_dates = stat("发言日期")
    observed_dates = {day_key(year, item.strip()) for item in re.split(r"[,，]", raw_dates)} if raw_dates else set()
    scope = first("范围").lower() or ("" if days else "fragments")
    if len(values["范围"]) > 1 or scope not in ("", "history", "thread", "fragments"):
        raise ValueError("材料范围只接受 history、thread 或 fragments")
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
        if kind == "原话" and len(quotes) < 6:
            prefix = re.match(r"^(\d\d-\d\d)~", value)
            stamp = day_key(year, prefix[1]) if prefix else None
            value = value[prefix.end():] if prefix else value
            if not value or len(value) > 80:
                raise ValueError("每条本人原话应为 1–80 字的连续原文")
            quotes.append((stamp, value))
        elif kind == "ai" and reply is None and 0 < len(quotes) < 6 and len(value) <= 80:
            if index > 0 and index+1 < len(lines) and lines[index-1][0] == lines[index+1][0] == "原话":
                reply = (len(quotes), value)
    first_day = min(days) if days else None
    counted_quotes = [(stamp, quote) for stamp, quote in quotes
                      if not (stamp and stamp not in days and
                              (not days or stamp in observed_dates or (scope == "history" and stamp < first_day)))]
    if rows and (len(counted_quotes) > total or any(day not in days or n > days[day][0]
                         for day, n in Counter(d for d, _ in counted_quotes if d).items())):
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
    if not (quotes or lead or habits or total or observed_dates):
        raise ValueError("缺少可核对的发言、现场或具体用法")
    tags = [tag.strip() for line in values["标签"] for tag in line.split("、") if tag.strip()]
    name = first("署名")[:16]
    if not name or re.fullmatch(r'[「“"]?(?:[xｘ×]{3}|叉叉叉)[」”"]?', name, re.IGNORECASE):
        name = "我"
    return dict(year=year, theme=theme, scope=scope, name=name, lead=lead, quotes=quotes,
                reply=reply, setup=first("前情") if len(first("前情")) <= 24 else "", short=first("短评")[:100],
                habits=[h[:120] for h in habits if h != lead], tags=list(dict.fromkeys(tags))[:3],
                days=days, observed_dates=observed_dates, total=total, hits=hits, tokens=int(tokens) if tokens else None)


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
    name, theme_label = EDITIONS[theme]
    paper, ink, accent, on_accent, pull, on_pull, signal, tint, calendar_ink = PALETTES[theme]
    commands = []

    def cmd(method, *args, **kwargs):
        commands.append((method, args, kwargs))

    def text(x, y, value, size, color=ink, bold=False, align="lt"):
        cmd("text", (x, y), str(value), font=font(size), fill=color, anchor=align,
            stroke_width=1 if bold else 0, stroke_fill=color)

    def wrap(value, width, size):
        face = font(size)
        # Keep Latin words whole and bind closing punctuation to the previous unit.
        units = []
        for token in re.findall(r"[A-Za-z0-9_]+|.", value):
            parts = [token] if face.getlength(token) <= width else list(token)
            for part in parts:
                if units and re.fullmatch(r"[，。、！？；：…）】」》％,.!?;:%)]", part):
                    units[-1] += part
                else:
                    units.append(part)

        def fit(line_width):
            rows, current = [], ""
            for unit in units:
                if current and face.getlength(current+unit) > line_width:
                    rows.append(current)
                    current = ""
                current += unit
            return rows + ([current] if current else [])

        rows = fit(width)
        # Rebalance a stranded final word when the number of lines stays the same.
        if len(rows) > 1 and face.getlength(rows[-1]) < width * .3:
            for smaller in range(width-size, int(width*.65), -size):
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

    def centered(x, y, value, size, color=ink, bold=False):
        # Centre the ink, including a mixed Latin/CJK signature, inside the sticker.
        left, top, right, bottom = font(size).getbbox(value, anchor="lt")
        text(round(x-(left+right)/2), round(y-(top+bottom)/2), value, size, color, bold)

    def fitted(value, width, size):
        while size > 18 and font(size).getlength(value) > width:
            size -= 1
        return size

    scope_title = {"thread": "本次对话精选", "fragments": "聊天片段精选"}.get(r["scope"])
    type_caption = "本次类型" if scope_title else "年度类型"
    type_name = name if theme else "待定"
    caption_width = round(font(26).getlength(type_caption))
    type_width = round(font(34).getlength(type_name))
    type_left = 852 - (16 + caption_width + 12 + type_width + 16)
    rect(type_left, 36, 852-type_left, 56, tint, ink)
    centered(type_left+16+caption_width/2, 64, type_caption, 26)
    centered(852-16-type_width/2, 64, type_name, 34, bold=True)

    badge = r["name"]+"的"
    badge_size = fitted(badge, type_left-22-48-44, 34)
    badge_w = round(font(badge_size).getlength(badge))+44
    rect(48, 36, badge_w, 56, accent)
    centered(48+badge_w/2, 64, badge, badge_size, on_accent, True)
    title = scope_title or (f"{name} 报告" if theme else f"{name}报告")
    title = f"{year} {title}"
    text(48, 115, title, fitted(title, 804, 68), bold=True)
    text(852, 202, "扫图底二维码获取口令 ↓", 28, align="rt")
    y = 260

    quotes = r["quotes"]
    quote_first = theme == "puai" and bool(quotes)
    markers = {day: i+1 for i, day in enumerate(sorted({dt for dt, _ in quotes if dt}))}

    def mark_date(x, y, dt, color, background):
        cmd("ellipse", (x, y, x+29, y+29), fill=color)
        centered(x+14.5, y+14.5, str(markers[dt]), 21, background, True)
        text(x+39, y, dt.strftime("%m.%d"), 28, color, True)

    def quote_sticker(i, dt, quote, top):
        # Short editions put the closing line in a solid burst. Longer ones keep the A trio.
        style = 1 if len(quotes) == 1 else i % 3
        burst = style == 2 or (len(quotes) <= 2 and style == 1)
        inset = 52 if burst else 32
        size = 50 if i == 0 and len(quote) <= 22 else 46
        width = min(804, max(506, round(font(size).getlength(quote)) + 2*inset + 12))
        x = 852-width if style == 1 and len(quotes) > 1 else 48
        rows = wrap(quote, width-2*inset, size)
        header = bool(dt or r["reply"])
        body_top = (64 if header else 28) + (13 if burst else 0)
        leading = round(size*1.34)
        height = body_top+(len(rows)-1)*leading+size+(42 if burst else 27)
        fill, fg = [("#FCFDFB", ink), (pull, on_pull), (signal, ink)][style]
        if burst:
            # Short sloped sides, two folded corners, plus room around the entire line.
            w, h = width, height
            points = [(16,9),(92,15),(116,1),(147,15),(w-150,15),(w-118,1),
                      (w-93,14),(w-16,7),(w-24,h//2),(w-1,h-12),(w-104,h-20),
                      (w-134,h-2),(w-160,h-20),(151,h-20),(121,h-3),
                      (98,h-19),(1,h-10),(23,h//2)]
            pts = [(x+px, top+py) for px, py in points]
            cmd("polygon", pts, fill=fill)
            cmd("line", pts+[pts[0]], fill=ink, width=3, joint="curve")
        else:
            rect(x, top, width, height, fill, ink, 28)
            tail = x+width-145 if style else x+82
            base = top+height
            pts = [(tail, base-2), (tail+54, base-2),
                   (tail+(76 if style else -20), base+21)]
            cmd("polygon", pts, fill=fill)
            cmd("line", [pts[0],pts[2],pts[1]], fill=ink, width=3)
        body_x = x+inset
        meta_y = top+(27 if burst else 19)
        if r["reply"]:
            text(body_x, meta_y, "本人", 28, fg, True)
        if dt:
            mark_date(body_x+(72 if r["reply"] else 0), meta_y, dt, fg, fill)

        # Plain receipts contain verified quotes, without editorial emphasis spans.
        for line_no, row in enumerate(rows):
            text(body_x, top+body_top+line_no*leading, row, size, fg, True)
        return top+height+(23 if burst else 40)

    if quotes:
        y = heading(y, "对话现场" if r["reply"] else "本人原话")
        if r["setup"]:
            y = paragraph(48, y, wrap(r["setup"], 804, 34), 34) + 14
        for i, (dt, quote) in enumerate(quotes):
            y = quote_sticker(i, dt, quote, y)
            if r["reply"] and r["reply"][0] == i+1:
                rows = wrap(r["reply"][1], 610, 36)
                height = len(rows)*50+32
                rect(86,y,766,height,tint,radius=12)
                text(110,y+17,"AI",34,bold=True)
                cmd("line",(170,y+14,170,y+height-14),fill=ink,width=2)
                paragraph(190,y+16,rows,36)
                y += height+19
    if r["lead"]:
        if quotes:
            text(48, y, "现场旁注", 31, bold=True)
            cmd("line", (204,y+3,204,y+38), fill=calendar_ink, width=3)
            y = paragraph(226, y+4, wrap(r["lead"], 622, 36), 36) + 28
        else:
            y = heading(y, "对话现场" if scope_title else "年度现场")
            y = paragraph(48, y, wrap(r["lead"], 804, 43), 43, bold=True) + 26
    if not quotes and not r["lead"] and r["short"] and not r["habits"]:
        y = paragraph(48,y,wrap(r["short"],800,41),41,bold=True)+28
    if r["total"] or r["tokens"] is not None:
        y = heading(y,"对话用量")
        ratio = None if r["hits"] is None else r["hits"]/r["total"]
        width = 536 if ratio is not None else 804
        if r["tokens"] is not None:
            tokens = r["tokens"]
            if tokens >= 100_000_000:
                whole, decimals = divmod(tokens//1_000_000, 100)
                value = f"≥{whole}.{decimals:02}亿 token"
            else:
                value = f"至少 {tokens:,} token"
            caption = "和 AI 对话，烧了"
        else:
            value, caption = f'{r["total"]:,} 条指令', "你向 AI 发出了"
        rect(48,y,width,152,pull)
        text(72,y+18,caption,32,on_pull)
        text(72,y+72,value,fitted(value,width-48,54),on_pull,True)
        if ratio is not None:
            cx, cy, rad = 724, y+62, 62
            bounds = (cx-rad,cy-rad,cx+rad,cy+rad)
            cmd("ellipse",bounds,outline=tint,width=12)
            if ratio:
                cmd("arc",bounds,-90,-90+ratio*360,fill=calendar_ink,width=12)
            percentage = f"{ratio*100:.1f}".removesuffix(".0")+"%"
            centered(cx,cy,percentage,fitted(percentage,95,39),bold=True)
            text(cx,y+138,"指令在骂 AI" if theme=="puai" else theme_label+"占比",30,align="mt")
        extra = []
        if r["tokens"] is not None and r["total"]:
            extra.append(f'{r["total"]:,} 条指令')
        if ratio is not None:
            extra.append(f'{r["hits"]:,} 条{theme_label}')
        if extra:
            value = " · ".join(extra)
            text(48,y+169,value,fitted(value,width,31),bold=True)
        y += (231 if extra else 200 if ratio is not None else 186)

    days = r["days"]
    quote_dates = [dt for dt, _ in quotes if dt]
    observed_dates = r["observed_dates"].union(quote_dates)
    calendar_dates = set(days) or observed_dates
    if calendar_dates:
        first_date, last_date = min(calendar_dates), max(calendar_dates)
        span = first_date.strftime("%m.%d")
        if last_date != first_date:
            span += " – " + last_date.strftime("%m.%d")
        text(852, y+6, span, 32, align="rt")
    y = heading(y, "片段日期" if observed_dates and not days else "发言日历")
    if calendar_dates:
        month_counts = Counter(day.month for day in calendar_dates)
        month_messages = Counter()
        if days:
            peak = min(days,key=lambda d:(-days[d][0],d))
            active_label = f"活跃 {len(days)} 天"
            if theme and all(h is not None for _, h in days.values()):
                themed_days = sum(h > 0 for _, h in days.values())
                active_label += f" · {themed_days} 天{theme_label}"
            primary = active_label
            secondary = f"单日最高 {peak.month}.{peak.day:02} · {days[peak][0]} 条"
            for day, (n, _) in days.items():
                month_messages[day.month] += n
        else:
            primary, secondary = f"核实 {len(observed_dates)} 天", ""
            if quote_dates:
                dated = str(len(quote_dates)) if len(quote_dates) == len(quotes) else f"{len(quote_dates)} / {len(quotes)}"
                secondary = f"{dated} 句原话有日期"
        selected = sorted(sorted(month_counts, key=lambda m: (-month_counts[m], -month_messages[m], -m))[:3])
        legend = [("发言" if days else "已核日期", ink)]
        if any(h for _,h in days.values()):
            legend.append((theme_label, calendar_ink))
        legend.append(("缺记录", None))

        def dot(px, py, diameter, fill):
            cmd("ellipse",(px,py,px+diameter,py+diameter),fill=fill,outline=fill or "#87959D",width=1)
            if not fill:
                cmd("line",(px+4,py+diameter-4,px+diameter-4,py+4),fill="#87959D",width=1)

        def month_grid(month, x, top, width):
            cx = x+width/2
            centered(cx,top+17,f"{month:02} 月",34,bold=True)
            weeks = calendar.Calendar(0).monthdayscalendar(year,month)
            step, diameter = 28, 23
            left = round(cx-((len(weeks)-1)*step+diameter)/2)
            for week, dates in enumerate(weeks):
                for weekday, day in enumerate(dates):
                    if not day:
                        continue
                    dt = date(year, month, day)
                    record = days.get(dt)
                    fill = calendar_ink if record and record[1] else ink if dt in calendar_dates else None
                    px, py = left+week*step,top+54+weekday*step
                    dot(px,py,diameter,fill)
                    if dt in markers:
                        cmd("rectangle",(px-2,py-2,px+diameter+2,py+diameter+2),outline=ink,width=2)
                        centered(px+diameter/2,py+diameter/2,str(markers[dt]),18,"#FFFFFF" if fill else ink,True)
            monthly = [(n,h) for day,(n,h) in days.items() if day.month==month]
            if monthly:
                n = month_messages[month]
                if theme and all(h is not None for _,h in monthly):
                    hits = sum(h for _,h in monthly)
                    stat = f"{hits} {'喷 / ' if theme=='puai' else '/ '}{n} 条"
                    left, bar = x+18, width-36
                    rect(left, top+296, bar, 8, tint)
                    if hits:
                        rect(left,top+296,round(bar*hits/n),8,calendar_ink)
                else:
                    stat = f"{n} 条发言"
            elif len(selected) > 1:
                stat = f"核实 {month_counts[month]} 天"
            else:
                return
            centered(cx,top+265,stat,fitted(stat,width-8,30),bold=True)

        def date_legend(x, at, available):
            col = available/len(legend)
            for i,(label,fill) in enumerate(legend):
                xx = round(x+i*col)
                dot(xx,at+4,20,fill)
                text(xx+28,at,label,26)

        if len(selected)==1:
            month_grid(selected[0],48,y,326)
            cmd("line",(397,y+4,397,y+291),fill="#BAC6C8",width=2)
            text(428,y+29,primary,fitted(primary,424,38),bold=True)
            if secondary:
                text(428,y+112,secondary,fitted(secondary,424,34),bold=True)
            date_legend(428,y+219,424)
            y += 334
        else:
            text(48,y,primary,fitted(primary,367,36),bold=True)
            if secondary:
                cmd("line",(425,y,425,y+38),fill="#BAC6C8",width=2)
                text(450,y,secondary,fitted(secondary,402,34),bold=True)
            date_legend(48,y+65,804)
            width = (804-24*(len(selected)-1))//len(selected)
            for i,month in enumerate(selected):
                month_grid(month,48+i*(width+24),y+125,width)
            y += 462
        extra = sorted(observed_dates.difference(days)) if days else []
        if extra:
            listed = "、".join(day.strftime("%m.%d") for day in extra[:3])
            if len(extra) > 3:
                listed = extra[0].strftime("%m.%d") + " – " + extra[-1].strftime("%m.%d")
            y = paragraph(48, y, wrap(f"另有 {len(extra)} 个已知日期 · {listed}", 804, 30), 30) + 24
    else:
        label = f"这 {len(quotes)} 句原话未附日期。" if quotes else "这份记录未附日期。"
        rect(48, y, 804, 76, paper, ink, 12)
        rect(48, y+12, 6, 52, calendar_ink)
        text(71, y+20, label, 33)
        y += 112
    habits = r["habits"][:2] if r["lead"] or quotes else r["habits"]
    if quote_first:
        habits = [habit for habit in r["habits"] if len(habit) <= 24][:1]
    if habits:
        y = heading(y,"日常用法")
        for habit in habits:
            y = paragraph(48,y,wrap(habit,804,38),38)+17
        y += 12
    if r["tags"]:
        zone = y
        rect(0,zone,900,165,signal)
        text(48,zone+18,"片段标签" if scope_title else "人格标签",34,bold=True)
        tags = r["tags"]
        max_width = (804 - 16*(len(tags)-1))//len(tags)
        x = 48
        for tag in tags:
            if len(tag) > 10:
                tag = tag[:9]+"…"
            size = fitted(tag,max_width-24,35)
            width = min(max_width, round(font(size).getlength(tag))+40)
            rect(x,zone+74,width,58,paper,ink)
            centered(x+width/2,zone+103,tag,size,bold=True)
            x += width+16
        y += 170
    footer_height = 228
    rect(0,y,900,footer_height,"#FBFBF8")
    text(48,y+31,"扫码获取口令",46,bold=True)
    text(48,y+98,"复制给你的 Agent。",34)
    text(48,y+160,"唐苑容.com/PUAI/#go",30)
    cell = 5
    modules = len(QR_ROWS)
    qr_size = (modules+8)*cell
    qr_x, qr_y = 852-qr_size, y+(footer_height-qr_size)//2
    rect(qr_x,qr_y,qr_size,qr_size,"#FFFFFF")
    for row,bits in enumerate(QR_ROWS):
        for col in range(modules):
            if bits & (1 << (modules-1-col)):
                rect(qr_x+(col+4)*cell,qr_y+(row+4)*cell,cell-1,cell-1,"#101824")
    img = Image.new("RGB",(900,y+footer_height),paper)
    draw = ImageDraw.Draw(img)
    for method,args,kwargs in commands:
        getattr(draw,method)(*args,**kwargs)
    return img


def display_chat_png(path):
    """Publish the finished PNG as rich output from the host's active notebook cell."""
    try:
        from IPython import get_ipython
        from IPython.display import Image as InlineImage, display
    except ImportError as exc:
        raise RuntimeError("Inline PNG preview requires a notebook kernel.") from exc
    if getattr(get_ipython(), "kernel", None) is None:
        raise RuntimeError("Run display_chat_png in the host's active notebook kernel.")
    png = Path(path).read_bytes()
    with Image.open(BytesIO(png)) as poster:
        if poster.format != "PNG":
            raise ValueError("Inline report must be a PNG.")
        poster.verify()
    display(InlineImage(data=png, format="png"), include=["image/png"])


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
