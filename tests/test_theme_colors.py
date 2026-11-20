import itertools
import json
import subprocess
import sys
import unittest
from pathlib import Path

from PIL import ImageColor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_chat_png


def luminance(rgb):
    values = [n / 255 for n in ImageColor.getrgb(rgb)]
    linear = [n / 12.92 if n <= 0.04045 else ((n + 0.055) / 1.055) ** 2.4 for n in values]
    return sum(x * y for x, y in zip(linear, (0.2126, 0.7152, 0.0722)))


class ThemeColors(unittest.TestCase):
    def test_the_nine_editions_have_distinct_main_inks_in_both_renderers(self):
        # Ask the Canvas template for its effective colours with and without a
        # story, the two report shapes used by the live generator and the gallery.
        program = """
        const fs = require('node:fs');
        const vm = require('node:vm');
        const html = fs.readFileSync('assets/comic-template.html', 'utf8');
        const definitions = html.slice(html.indexOf('const editions ='), html.indexOf('const fontFamily='));
        const ids = JSON.parse(process.argv[1]);
        const roles = ['base','ink','accent','onAccent','pull','onPull','signal','tint','calendar'];
        const palettes = ids.map(theme => [undefined, {}].map(story =>
          vm.runInNewContext(definitions + '\\nroles.map(key => colors[key]);', {report: {theme, story}, roles})));
        console.log(JSON.stringify(palettes));
        """
        ids = list(render_chat_png.PALETTES)
        self.assertEqual(len(ids), 10)  # nine named editions plus unclassified
        web = subprocess.check_output(
            ["node", "-e", program, json.dumps([key or None for key in ids])], cwd=ROOT, text=True)
        font = render_chat_png.load_font(ROOT / "assets/SmileySans-Oblique.woff2")
        main_inks = []
        for theme, variants in zip(ids, json.loads(web)):
            with self.subTest(theme=theme):
                palette = render_chat_png.PALETTES[theme]
                self.assertEqual(variants, [list(palette), list(palette)])
                base, ink, accent, on_accent, pull, on_pull, signal, tint, calendar = palette
                for foreground, background in ((ink, base), (on_accent, accent), (on_pull, pull),
                                               (ink, signal), (ink, tint), ("#FFFFFF", calendar)):
                    low, high = sorted((luminance(foreground), luminance(background)))
                    self.assertGreaterEqual((high + 0.05) / (low + 0.05), 4.5)
                receipt = f"PUAI 2026\n主题：{theme or '待定'}\n原话：一颗够吗？\n原话：你把果核也算进去了？"
                image = render_chat_png.draw_report(render_chat_png.parse_receipt(receipt), font)
                areas = {color: count for count, color in image.getcolors(image.width * image.height)}
                self.assertGreater(areas.get(ImageColor.getrgb(pull), 0), 7000)
                if theme:
                    main_inks.append(ImageColor.getrgb(pull))
        for a, b in itertools.combinations(main_inks, 2):
            self.assertGreater(sum((x-y)**2 for x, y in zip(a, b)), 60**2)
