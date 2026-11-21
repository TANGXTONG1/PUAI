"""Official PUAI A poster. In this notebook import show_puai and pass a reviewed report.
show_puai(receipt, output="/mnt/data/PUAI-2026.png") displays the PNG inline.
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
TYPE_NAMES = {label.lower(): key for key, (label, _) in EDITIONS.items() if key}
TYPE_NAMES["爱因斯坦"] = "einstein"
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


def quote_emphasis(quote, selected):
    if selected and len(selected) <= 30 and selected in quote:
        return selected
    clauses = [s.strip() for s in re.findall(r"[^，,。！？!?；;：:\n]+[，,。！？!?；;：:]*", quote) if s.strip()]
    if len(clauses) >= 2:
        ending = clauses[-1]
        words = ending.rstrip("，,。！？!?；;：:").strip()
        if 2 <= len(words) and len(ending) <= 12 and words not in {"对吧", "对吗", "好吗", "行吗", "是吗", "好吧", "可以吗"}:
            return ending
    return ""


def parse_receipt(text):
    if len(text) > 48000:
        raise ValueError("报告过长")
    title = re.search(r"(?im)^\s*(?:#{1,6}\s+)?(?:\*\*)?PUAI\s+(20\d\d)(?:\*\*)?\s*$", text)
    if not title:
        raise ValueError("报告首行应为 PUAI 2026")
    year = int(title[1])
    values = defaultdict(list)
    lines = []
    highlights, repeats = {}, {}
    quote_number = None
    for raw in text[title.end():].splitlines():
        line = raw.strip()
        if line.startswith(('```', '~~~')) or line == "报告结束":
            break
        match = re.match(r"^(?:[-*]\s+)?(?:\*\*)?([^:：*]+?)(?:\*\*)?\s*[:：](?:\*\*)?\s*(.+)$", line)
        if not match:
            quote_number = None
            continue
        field, value = match[1].lower(), match[2].strip()
        if field in {"划线", "复读"}:
            if quote_number is not None and quote_number < 6:
                if field == "划线":
                    # Some clients group all q fields, followed by all marks.
                    originals = [re.sub(r"^\d\d-\d\d~", "", q) for q in values["原话"][:6]]
                    matches = [i for i, q in enumerate(originals) if value in q]
                    if len(value) <= 30:
                        if quote_number in matches:
                            highlights[quote_number] = value
                        elif len(matches) == 1:
                            highlights[matches[0]] = value
                elif re.fullmatch(r"[0-9]{1,5}", value) and 2 <= int(value) <= 50000:
                    repeats[quote_number] = int(value)
            continue
        quote_number = len(values["原话"]) if field == "原话" else None
        if field in {"人物类型", "人格类型", "年度类型", "本次类型"}:
            field = "主题"
        elif field == "人格标签":
            field = "标签"
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

    tags = [tag.strip() for line in values["标签"] for tag in line.split("、") if tag.strip()]
    theme = first("主题").lower()
    if not theme:
        named_types = {TYPE_NAMES[tag.lower()] for tag in tags if tag.lower() in TYPE_NAMES}
        if len(named_types) == 1:
            theme = named_types.pop()
            tags = [tag for tag in tags if TYPE_NAMES.get(tag.lower()) != theme]
    theme = TYPE_NAMES.get(theme, theme)
    if theme in {"待定", "未归类", "无", "ai 相处", "ai相处报告"}:
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
    name = first("署名")[:16]
    if not name or re.fullmatch(r'[「“"]?(?:[xｘ×]{3}|叉叉叉)[」”"]?', name, re.IGNORECASE):
        name = "我"
    return dict(year=year, theme=theme, scope=scope, name=name, lead=lead, quotes=quotes,
                emphases=[quote_emphasis(quote, highlights.get(i)) for i, (_, quote) in enumerate(quotes)],
                repeats=[repeats.get(i) for i in range(len(quotes))],
                reply=reply, setup=first("前情") if len(first("前情")) <= 24 else "", short=first("短评")[:100],
                habits=[h[:120] for h in habits if h != lead], tags=list(dict.fromkeys(tags))[:3],
                days=days, observed_dates=observed_dates, total=total, hits=hits, tokens=int(tokens) if tokens else None)


def load_font(path=None):
    # A remote skill read into a notebook has no __file__.
    here = Path(globals().get("__file__", "render_chat_png.py")).resolve().parent
    candidates = [path] if path else [
        Path.home()/"Library/Fonts/PingFangSC-Regular.ttf", "/System/Library/Fonts/PingFang.ttc",
        here.parent/"assets/SmileySans-Oblique.woff2", here/"assets/SmileySans-Oblique.woff2",
        here/"SmileySans-Oblique.woff2",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc", "C:/Windows/Fonts/msyh.ttc",
    ]
    for filename in candidates:
        try:
            f = ImageFont.truetype(str(filename), 24)
            if len({bytes(f.getmask(ch)) for ch in "中文图"}) == 3:
                return lru_cache(maxsize=32)(lambda size: ImageFont.truetype(str(filename), size))
        except OSError:
            continue
    if not path:
        # Data-analysis kernels can have PyMuPDF's CJK font but no system CJK font files.
        try:
            try:
                import pymupdf
            except ImportError:
                import fitz as pymupdf
            embedded = pymupdf.Font(fontname="cjk").buffer
            face = ImageFont.truetype(BytesIO(embedded), 24)
            if len({bytes(face.getmask(ch)) for ch in "中文图"}) == 3:
                return lru_cache(maxsize=32)(lambda size: ImageFont.truetype(BytesIO(embedded), size))
        except (ImportError, AttributeError, OSError, RuntimeError):
            pass
    raise ValueError("找不到可绘制中文的字体。请用 --font 指定 Noto Sans CJK 或包内 SmileySans 字体")


def draw_report(r, font):
    year, theme = r["year"], r["theme"]
    name, theme_label = EDITIONS[theme]
    paper, ink, accent, on_accent, pull, on_pull, signal, tint, calendar_ink = PALETTES[theme]
    commands = []

    def cmd(method, *args, **kwargs):
        commands.append((method, args, kwargs))

    def text(x, y, value, size, color=ink, bold=False, align="lt"):
        face = font(size)
        stroke = 0 if face.getname()[0] == "Smiley Sans" else 1
        cmd("text", (x, y), str(value), font=face, fill=color, anchor=align,
            stroke_width=stroke if bold else 0, stroke_fill=color)

    def wrap(value, width, size, emphasis="", spoken=False):
        face = font(size)
        units = []
        parts = [value]
        if emphasis and face.getlength(emphasis) <= width:
            before, match, after = value.partition(emphasis)
            parts = [before, match, after] if match else parts
        tokens = [token for index, part in enumerate(parts)
                  for token in ([part] if len(parts) == 3 and index == 1 else re.findall(r"[A-Za-z0-9_]+|.", part))]
        for token in tokens:
            parts = [token] if face.getlength(token) <= width else list(token)
            for part in parts:
                if units and re.fullmatch(r"[，。、！？；：…）】」』”’》％,.!?;:%)]", part):
                    units[-1] += part
                else:
                    units.append(part)

        def fit(line_width, pieces=units):
            rows, current = [], ""
            for unit in pieces:
                if current and face.getlength(current+unit) > line_width:
                    rows.append(current)
                    current = ""
                current += unit
            return rows + ([current] if current else [])

        rows = fit(width)
        if spoken and len(rows) > 1:
            # Prefer whole spoken clauses when they fit, preserving marked runs and punctuation.
            clauses, current = [], []
            for unit in units:
                current.append(unit)
                if re.search(r"[，。！？；!?;][”’」』）】]*$", unit):
                    clauses.append(current)
                    current = []
            if current:
                clauses.append(current)
            pieces = []
            for clause in clauses:
                phrase = "".join(clause)
                turn = re.search(r"就是|结果|但是|可是|偏偏|反倒|还得|才是", phrase[3:]) if face.getlength(phrase) > width else None
                if turn:
                    cut = turn.start()+3
                    left, right = phrase[:cut], phrase[cut:]
                    marked = phrase.find(emphasis) if emphasis else -1
                    if (not (marked >= 0 and marked < cut < marked+len(emphasis))
                        and all(width*.26 <= face.getlength(p) <= width for p in (left, right))):
                        pieces.extend((left, right))
                        continue
                pieces.append(phrase)
            if len(pieces) > 1 and all(face.getlength(piece) <= width for piece in pieces):
                spoken_rows = fit(width, pieces)
                if len(spoken_rows) <= len(rows) + 1:
                    return spoken_rows
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
    title = f"{name} 报告" if theme else (scope_title or "AI 相处报告")
    title = f"{year} {title}"
    text(48, 115, title, fitted(title, 804, 68), bold=True)
    if scope_title and theme:
        text(48, 200, scope_title, 32, bold=True)
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
        inset = 53 if burst else 34
        size = 50 if i == 0 else 46
        repeats = r["repeats"][i]
        meta_width = ((157 if dt else 0)+(92 if r["reply"] else 0)+font(32).getlength(f"复读×{repeats}")) if repeats else 0
        width = min(804, max(540, round(max(font(size).getlength(quote)+8, meta_width))+2*inset))
        x = 852-width if style == 1 and len(quotes) > 1 else 48
        emphasis = r["emphases"][i]
        rows = wrap(quote, width-2*inset, size, emphasis, spoken=True)
        header = bool(dt or r["reply"] or repeats)
        body_top = (80 if burst else 78) - (0 if header else 49)
        leading = round(size*1.35)
        height = body_top + len(rows)*leading + (36 if burst else 18)
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
        if repeats:
            text(x+width-inset,meta_y,f"复读×{repeats}",30,fg,True,"rt")
        start = quote.find(emphasis) if emphasis else -1
        end, offset = start+len(emphasis), 0
        hi, hi_text = [(tint,ink), (accent,on_accent), (calendar_ink,"#FFFFFF")][style]
        for line_no, row in enumerate(rows):
            at = top+body_top+line_no*leading
            a, b = max(start-offset, 0), min(end-offset, len(row))
            if a < b:
                xx = body_x + font(size).getlength(row[:a])
                right = body_x + font(size).getlength(row[:b])
                rect(round(xx)-2,at-4,round(right-xx)+4,size+9,hi)
                if a:
                    text(body_x, at, row[:a], size, fg, True)
                text(xx, at, row[a:b], size, hi_text, True)
                if b < len(row):
                    text(right, at, row[b:], size, fg, True)
            else:
                text(body_x, at, row, size, fg, True)
            offset += len(row)
        closing = i == len(quotes)-1 and not (r["reply"] and r["reply"][0] == len(quotes))
        return top+height+(0 if burst else 22)+(48 if closing else 24)

    if quotes:
        y = heading(y, "对话现场" if r["reply"] else "本人原话")
        if r["setup"]:
            text(48,y+1,"前情",32,"#475364",True)
            y = paragraph(140, y, wrap(r["setup"], 712, 34), 34) + 18
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
    if r["lead"] and not quotes:
        y = heading(y, "对话现场" if scope_title else "年度现场")
        y = paragraph(48, y, wrap(r["lead"], 804, 43), 43, bold=True) + 26
    if not quotes and not r["lead"] and r["short"] and not r["habits"]:
        y = paragraph(48,y,wrap(r["short"],800,41),41,bold=True)+28
    if r["total"] or r["tokens"] is not None:
        ratio = None if r["hits"] is None else r["hits"]/r["total"]
        width = 514 if ratio is not None else 804
        if r["tokens"] is not None:
            tokens = r["tokens"]
            if tokens >= 100_000_000:
                whole, decimals = divmod(tokens//1_000_000, 100)
                value = f"≥{whole}.{decimals:02}亿 token"
            else:
                value = f"至少 {tokens:,} token"
            caption = "和 AI 对话，烧了"
        else:
            value, caption = f'{r["total"]:,} 条指令', "记录里，你发出了"
        height = 154 if ratio is not None else 104
        rect(48,y,width,height,pull)
        if ratio is not None:
            text(74,y+18,caption,34,on_pull,True)
            text(74,y+72,value,fitted(value,width-52,52),on_pull,True)
            cx, cy, rad = 720, y+72, 65
            bounds = (cx-rad,cy-rad,cx+rad,cy+rad)
            cmd("ellipse",bounds,outline=tint,width=12)
            if ratio:
                cmd("arc",bounds,-90,-90+ratio*360,fill=calendar_ink,width=12)
            percentage = f"{ratio*100:.1f}".removesuffix(".0")+"%"
            centered(cx,cy-23,"约",24,bold=True)
            centered(cx,cy+14,percentage,fitted(percentage,108,44),bold=True)
            text(cx,y+156,"指令在骂 AI" if theme=="puai" else theme_label+"指令占比",30,align="mt")
        else:
            text(74,y+32,caption,34,on_pull,True)
            centered(625,y+52,value,fitted(value,390,52),on_pull,True)
        extra = []
        if r["tokens"] is not None and r["total"]:
            extra.append(f'{r["total"]:,} 条指令')
        if ratio is not None:
            extra.append(f'{r["hits"]:,} 条{theme_label}')
        if extra:
            value = " · ".join(extra)
            text(48,y+(169 if ratio is not None else 117),value,fitted(value,width,31),bold=True)
        y += 232 if ratio is not None else (178 if extra else 139)

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
            active_label = f"{len(days)} 天"
            if theme and all(h is not None for _, h in days.values()):
                themed_days = sum(h > 0 for _, h in days.values())
                active_label += f" · {themed_days} 天{theme_label}"
            primary = active_label
            secondary = f"{peak.month}.{peak.day:02} · {days[peak][0]} 条"
            for day, (n, _) in days.items():
                month_messages[day.month] += n
        else:
            primary, secondary = f"核实 {len(observed_dates)} 天", ""
            if quote_dates:
                dated = str(len(quote_dates)) if len(quote_dates) == len(quotes) else f"{len(quote_dates)} / {len(quotes)}"
                secondary = f"{dated} 句原话有日期"
        quoted_months = {dt.month for dt in quote_dates}
        selected = sorted(sorted(month_counts, key=lambda m: (
            month_counts[m], month_messages[m], m in quoted_months, m), reverse=True)[:3])
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
                    fill = calendar_ink if record and record[1] else ink if dt in calendar_dates or dt in observed_dates else None
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

        def date_fact(x, at, width, label, value):
            text(x,at,label,32,"#475364",True)
            text(x,at+44,value,fitted(value,width,46),bold=True)

        if len(selected)==1:
            month_grid(selected[0],48,y,326)
            cmd("line",(397,y+4,397,y+291),fill="#BAC6C8",width=2)
            if days:
                date_fact(428,y+12,424,"有发言的日子",primary)
                date_fact(428,y+128,424,"单日最高发言",secondary)
            else:
                text(428,y+29,primary,fitted(primary,424,38),bold=True)
            if secondary and not days:
                text(428,y+112,secondary,fitted(secondary,424,34),bold=True)
            date_legend(428,y+245,424)
            y += 334
        else:
            if days:
                date_fact(48,y,325,"有发言的日子",primary)
                cmd("line",(385,y+4,385,y+86),fill="#BAC6C8",width=2)
                date_fact(419,y,433,"单日最高发言",secondary)
                y += 53
            else:
                text(48,y,primary,fitted(primary,367,36),bold=True)
                if secondary:
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
    if r["lead"] and quotes:
        rows = wrap(r["lead"], 776, 36)
        rect(48,y+2,7,len(rows)*50-5,accent)
        y = paragraph(76,y,rows,36,"#475364") + 30
    habits = r["habits"][:2] if r["lead"] or quotes else r["habits"]
    if quote_first:
        habits = [habit for habit in r["habits"] if len(habit) <= 24][:1]
    if habits:
        heading(y,"日常用法")
        for index, habit in enumerate(habits):
            if index:
                cmd("line", (264,y,852,y), fill="#BAC6C8", width=2)
                y += 14
            y = paragraph(264,y,wrap(habit,588,37),37,bold=True)+15
        y += 24
    stickers = []
    if r["tags"]:
        zone = y
        tags = r["tags"]
        compact = len(tags) <= 2
        height = 144 if compact else 212
        chip_y = zone + (37 if compact else 94)
        rect(0,zone,900,height,signal)
        text(48,zone+(47 if compact else 24),"片段标签" if scope_title else "人格标签",38,bold=True)
        width = (588-16)//2 if compact else (804-32)//3
        for i,tag in enumerate(tags):
            if len(tag) > 10:
                tag = tag[:9]+"…"
            x = (264 if compact else 48)+i*(width+16)
            rect(x,chip_y,width,62,paper,ink)
            centered(x+width/2,chip_y+31,tag,fitted(tag,width-20,40),bold=True)
            stickers.append((x-5,chip_y-6,x+width+6,chip_y+68))
        y += height
    footer_height = 228
    rect(0,y,900,footer_height,"#FBFBF8")
    text(48,y+49,"扫码获取口令",46,bold=True)
    text(48,y+124,"发给自己的 Agent 总结出图。",34)
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
    for bounds, angle in zip(stickers, (0.92,-0.86,0.69)):
        tile = img.crop(bounds)
        img.paste(tile.rotate(angle,resample=Image.Resampling.BICUBIC,fillcolor=signal),bounds[:2])
    return img


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
