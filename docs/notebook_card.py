from calendar import monthrange
from collections import Counter
from datetime import date
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import re
from PIL import Image, ImageDraw, ImageFont
from IPython.display import Image as NotebookImage, display

def puai_card(*, name, theme, scope, turns=(), tags=(), days=None, dates=(),
              undated=None, tokens=None, scene="", year=2026, output=None):
    # turns 按现场顺序，每项 (说话人, 当地 MM-DD 或空串, 逐字原话)
    # days 为 {"MM-DD": (当日可数本人消息数, 核准命中数或 None)}
    editions = {
        "puai": ("PUAI", "#16399A", "#F3F6F6", "#C7E1F4"),
        "teach": ("AI的教育", "#087A54", "#FFFFFF", "#99E7B8"),
        "aicu": ("AICU", "#FF8643", "#301B12", "#FFC79E"),
        "all": ("AI特全体", "#A180F5", "#211435", "#D5C7FA"),
        "hush": ("AI在心口难开", "#FFABA3", "#342020", "#FFD2CC"),
        "einstein": ("AI因斯坦", "#32CCDB", "#0C2C34", "#A4EEF0"),
        "edison": ("AI迪生", "#FFCA29", "#302615", "#FFE395"),
        "support": ("AI的供养", "#F16DBD", "#33182C", "#FEC9E3"),
        "free": ("AI咋咋地", "#C8E73F", "#262E14", "#E3F59E"),
        "": ("待定", "#CDD4D6", "#232B30", "#E0E5E4")}
    name = (name or "").strip()
    if not name or re.fullmatch(r'[「“"]?(?:[xｘ×]{3}|叉叉叉)[」”"]?', name, re.I):
        name = "我"
    kind, color, on_color, light = editions[theme or ""]
    ink, paper = "#142238", "#FAFBF7"
    # 本机已装字体或 PyMuPDF 自带的 CJK 字库。全程离线。
    faces = ["NotoSansCJK-Regular.ttc", "wqy-zenhei.ttc", "DroidSansFallbackFull.ttf",
             "/System/Library/Fonts/STHeiti Medium.ttc", "msyh.ttc", "SmileySans-Oblique.woff2"]
    font_file = None
    for path in faces:
        try:
            found = ImageFont.truetype(path, 26)
            if len({bytes(found.getmask(c)) for c in "中文图"}) == 3:
                font_file = found.path
                break
        except OSError:
            pass
    if not font_file:
        try:
            import pymupdf
        except ImportError:
            import fitz as pymupdf
        embedded = pymupdf.Font(fontname="cjk").buffer
    @lru_cache(maxsize=48)
    def font(size):
        return ImageFont.truetype(font_file or BytesIO(embedded), size)
    poster = Image.new("RGB", (900, 5800), paper)
    pen = ImageDraw.Draw(poster)
    def text(x, y, value, size, fill=ink, max_width=804):
        while size > 16 and font(size).getlength(value) > max_width:
            size -= 1
        pen.text((x, y), value, font=font(size), fill=fill, anchor="lt")
    def lines(value, size, width):
        rows, row = [], ""
        for c in value:
            if row and (c == "\n" or font(size).getlength(row+c) > width):
                rows.append(row)
                row = ""
            if c != "\n":
                row += c
        return rows + ([row] if row else [])
    def section(y, value):
        text(48, y, value, 38)
        pen.rectangle((48, y+48, 162, y+54), fill=light)
        return y+74
    def known_day(s):
        return date.fromisoformat(f"{year}-{s}")
    days = {known_day(k): v for k, v in (days or {}).items()}
    observed = {known_day(d) for d in dates} | {known_day(d) for who,d,_ in turns if who == "本人" and d}
    rows = list(days.values()) + ([undated] if undated is not None else [])
    assert all(isinstance(n,int) and n>0 and (h is None or isinstance(h,int) and 0<=h<=n) for n,h in rows)
    assert len(turns) <= 4 and sum(who == "本人" for who,_,_ in turns) <= 3
    assert all(who in ("本人", "AI") and 0 < len(q) <= 80 for who,_,q in turns)
    assert len(scene) <= 90 and len(name) <= 16
    assert tokens is None or isinstance(tokens, int) and tokens >= 0
    pen.rectangle((48, 38, 450, 100), fill=light)
    text(65, 50, name+"的", 38, max_width=367)
    text(478, 52, ("年度类型" if scope=="history" else "本次类型")+" · "+kind, 34, max_width=374)
    title = {"history": kind+" 报告" if kind!="待定" else "AI 相处报告",
             "thread": "单场对话精选", "fragments": "聊天片段精选"}[scope]
    text(48, 134, str(year)+" "+title, 66)
    y = section(245, "对话现场") if turns or scene else 245
    for line in lines(scene, 34, 804):
        text(48, y, line, 34)
        y += 48
    for i, (who, stamp, quote) in enumerate(turns):
        size = 46 if who == "本人" else 34
        x = 48 if who == "本人" else 112
        quote_lines = lines(quote, size, 802-x)
        bottom = y + 76 + (size+15)*len(quote_lines)
        bg, fg = ((color, on_color) if i==0 else (light, ink)) if who=="本人" else (paper, ink)
        if i==2 and who=="本人":
            pen.polygon([(x,y+8),(x+70,y+12),(x+88,y),(x+108,y+12),(820,y+8),
                         (852,y),(844,bottom-18),(852,bottom),(784,bottom-6),(x,bottom)], fill=bg, outline=ink, width=3)
        else:
            pen.rounded_rectangle((x,y,852,bottom), radius=22, fill=bg, outline=ink, width=3)
            pen.polygon([(x+58,bottom-3),(x+42,bottom+14),(x+103,bottom-3)], fill=bg, outline=ink, width=2)
        text(x+26,y+21,who+("  "+stamp.replace("-",".") if stamp else ""),26,fg)
        for j, line in enumerate(quote_lines):
            text(x+26, y+62+j*(size+15), line, size, fg)
        y = bottom+36
    if rows or tokens is not None:
        total = sum(n for n,_ in rows)
        numbers = ([f"{total:,} 条可数指令"] if rows else []) + ([f"{tokens:,} token"] if tokens is not None else [])
        if rows and theme and all(h is not None for _,h in rows):
            metric = "开喷" if theme=="puai" else kind
            numbers.append(f"{metric}约 {sum(h for _,h in rows)/total:.1%}")
        pen.rectangle((48,y,852,y+88),fill=color)
        text(70,y+27," · ".join(numbers),36,on_color,758)
        y += 120
    y = section(y,"发言日历")
    all_dates = sorted(observed | set(days))
    if days:
        peak = max(n for n,_ in days.values())
        label = f"已记账 {len(days)} 天 · 单日最多 {peak} 条"
        if observed-set(days):
            label += f" · 另见 {len(observed-set(days))} 天"
    else:
        label = f"可核实 {len(all_dates)} 个发言日" if all_dates else "这批记录未附发送日期"
    text(48,y,label,32)
    y += 53
    months = Counter(d.month for d in all_dates)
    for slot,m in enumerate(sorted(sorted(months, key=lambda m:(-months[m],m))[:3])):
        left = 48+slot*272
        pen.rounded_rectangle((left,y,left+258,y+208),radius=14,outline=ink,width=2)
        text(left+15,y+15,f"{m:02} 月",31)
        weekday,last = monthrange(year,m)
        for day in range(1,last+1):
            week,col = divmod(weekday+day-1,7)
            d = date(year,m,day)
            cx,cy=left+26+32*col,y+64+24*week
            bounds = (cx-7,cy-7,cx+7,cy+7)
            if d in days:
                pen.ellipse(bounds,outline=ink,fill=ink if days[d][0]>1 else light)
            elif d in observed:
                pen.ellipse(bounds,outline=ink,width=3)
            else:
                pen.ellipse(bounds,outline="#A7AEB3",width=1)
    if months:
        y += 226
        text(48,y,"浅色 1 条 · 深色多条 · 粗圈仅核到日期 · 灰圈缺记录",25)
        y += 45
    if tags:
        y = section(y+15, "人格标签" if scope=="history" else "片段标签")
        for i,tag in enumerate(tags[:3]):
            x=48+i*272
            pen.rectangle((x,y,x+258,y+65),fill=light,outline=ink,width=2)
            text(x+16,y+18,tag,30,max_width=226)
        y += 100
    pen.line((48,y,852,y), fill=ink,width=2)
    text(48,y+50,"扫码获取口令",43,max_width=575)
    text(48,y+106,"发给自己的 Agent 总结出图。",35,max_width=575)
    qr = "1fc08c87f 105b77041 174ab2b5d 175e3555d 175e3865d 104796541 1fd55557f 1284200 bd81d2da 7851fa1c bd61061f 12b696ea7 1e6fda9f0 10e1f1a8 ef5bf45c 1a0125695 1bfed05f8 2b6e61d5 1d404fe2d c102d41c ad13afba 1d34bc238 147a53603 12871b037 1e718c7f7 1991d16 1fc53b354 1057ecd1c 17578aff2 175968ead 17440ecbf 105e870ff 1fcc7e37c"
    pen.rectangle((647,y+16,852,y+221),fill="white")
    for r,bits in enumerate(qr.split()):
        for c in range(33):
            if int(bits,16) & (1 << (32-c)):
                x, top = 667+c*5, y+36+r*5
                pen.rectangle((x,top,x+4,top+4),fill=ink)
    result = BytesIO()
    poster.crop((0,0,900,y+242)).save(result, format="PNG")
    pixels = result.getvalue()
    if output is not None:
        Path(output).write_bytes(pixels)
    display(NotebookImage(data=pixels,format="png"), include=["image/png"])
