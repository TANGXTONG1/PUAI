"""Create gallery sheets and README excerpts from the rendered sample posters."""
import argparse
import json
import sys
from shutil import copyfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from pathlib import Path

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from render_chat_png import EDITIONS, PALETTES, draw_report, load_font, parse_receipt

ORDER = ("puai", "aicu", "teach", "hush", "einstein", "all", "support", "edison", "free")
DISPLAY = ROOT / "assets/SmileySans-Oblique.woff2"
RESAMPLE = Image.Resampling.LANCZOS


def quote_band(image, theme):
    """Find the first solid-colour speech sticker, excluding the title and statistics."""
    ink = ImageColor.getrgb(PALETTES[theme][4])
    background = Image.new("RGB", image.size, image.getpixel((0, 0)))
    bounds = ImageChops.difference(image, background).crop((28, 0, 872, image.height))
    pixels = image.load()
    for y in range(260, image.height - 228):
        if sum(pixels[x, y] == ink for x in range(48, 852, 8)) < 18:
            continue
        top = bottom = y
        while top > 0 and bounds.crop((0, top, bounds.width, top+1)).getbbox():
            top -= 1
        while bottom < image.height and bounds.crop((0, bottom, bounds.width, bottom+1)).getbbox():
            bottom += 1
        return image.crop((28, max(0,top-5), 872, min(bottom+6,image.height)))
    raise ValueError(f"No solid quote sticker found for {theme}")


def overview(pages, title, dest, geometry=None):
    font = lambda size: ImageFont.truetype(str(DISPLAY), size)
    margin, gap, col = 36, 18, 448
    width = 2*margin + 3*col + 2*gap
    tiles = {}
    for key in ORDER:
        if geometry is None:
            tile = quote_band(pages[key], key)
        else:
            sticker = geometry[key]["stickers"][1]
            y = round(sticker["y"])
            tile = pages[key].crop((28, y-6, 872, y+round(sticker["height"])+7))
        tiles[key] = tile.resize((col, round(col*tile.height/tile.width)), RESAMPLE)
    row_heights = [max(tiles[k].height for k in ORDER[i:i+3]) + 93 for i in (0,3,6)]
    footer = pages["puai"].crop((0, pages["puai"].height-228, 900, pages["puai"].height))
    canvas = Image.new("RGB", (width, 151+sum(row_heights)+footer.height), "#FBFAF6")
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 31), title, fill="#142238", font=font(55), anchor="lt")
    draw.text((margin, 101), "PUAI 为唐某本人报告，其他八种为虚构聊天样例。", fill="#414950", font=font(27), anchor="lt")
    top = 150
    for i,key in enumerate(ORDER):
        row = i//3
        x = margin + (i%3)*(col+gap)
        paper = pages[key].getpixel((0,0))
        draw.rectangle((x, top, x+col-1, top+row_heights[row]-gap), fill=paper)
        draw.line((x,top+1,x+col-1,top+1),fill=PALETTES[key][4],width=5)
        draw.text((x+12,top+15),EDITIONS[key][0],font=font(40),fill=PALETTES[key][1],anchor="lt")
        canvas.paste(tiles[key], (x,top+69))
        if i%3 == 2:
            top += row_heights[row]
    canvas.paste(footer, ((width-900)//2, top))
    canvas.save(dest)


def main(source, docs):
    meta = json.loads((source / "meta.json").read_text(encoding="utf-8"))
    pages = {key: Image.open(source / (key+".png")).convert("RGB") for key in ORDER}
    for key in ("aicu", "einstein", "support"):
        first = meta[key]["stickers"][0]
        bottom = round(first["y"] + first["height"] + 12)
        pages[key].crop((0, 0, 900, bottom)).save(docs/"readme"/(key+".png"))
    # The signed cover edition has the same positions as its standard cobalt rendering.
    red = Image.open(docs/"persona-report.png").convert("RGB")
    second, last = meta["puai"]["stickers"][1:]
    red.crop((0, round(second["y"]-8), 900, round(last["y"]+last["height"]+9))).save(docs/"readme/tang-excerpt.png")
    overview(pages, "2026 · 九种 AI 相处方式", docs/"themes/overview.png", meta)
    native_font = load_font(DISPLAY)
    native = {k: draw_report(parse_receipt((source/(k+".txt")).read_text(encoding="utf-8")), native_font) for k in ORDER}
    overview(native, "2026 · 对话里的九型长图", docs/"themes/inline-editions.png")

    # The nine-report collection opens on the same approved red report as the site.
    themes = docs/"themes"
    for key in ORDER:
        copyfile(source/(key+".png"), themes/(key+".png"))
    with ZipFile(themes/"PUAI-samples.zip", "w") as bundle:
        for key in ORDER:
            member = "本人报告/PUAI.png" if key == "puai" else f"演示样刊/{EDITIONS[key][0]}.png"
            image = docs/"persona-report.png" if key == "puai" else themes/(key+".png")
            bundle.writestr(ZipInfo(member), image.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=6)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Sample render directory with PNGs, receipts and meta.json")
    parser.add_argument("--docs", type=Path, default=ROOT/"docs")
    args = parser.parse_args()
    main(args.source, args.docs)
