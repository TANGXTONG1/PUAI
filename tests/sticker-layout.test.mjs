import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import test from 'node:test';
import { readDirectFields } from '../docs/make/plain-report.mjs';
import { parseReport } from '../docs/make/report-code.mjs';

const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require(process.env.PUAI_PLAYWRIGHT_PACKAGE || 'playwright-core'));
} catch (error) {
  if (error.code !== 'MODULE_NOT_FOUND' || process.env.PUAI_PLAYWRIGHT_PACKAGE) throw error;
}

test('A 版把原话放在短评前，短贴左右对齐，旧链接仍可完整回放', {
  skip: !chromium && 'Install playwright-core to run the browser integration.',
}, async () => {
  const frame = await readFile(new URL('../docs/make/poster-frame.txt', import.meta.url), 'utf8');
  const browser = await chromium.launch({ executablePath: process.env.PUAI_CHROMIUM });
  const page = await browser.newPage({viewport: {width: 390, height: 844}});
  const lines = ['这也算交作业？','红笔借你。','收卷！','请再数一遍。','第三行呢？','终于对了。'];
  const lead = '红笔递了一圈。';
  try {
    await page.addInitScript(() => {
      window.paintedText = [];
      const paint = CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText = function(label, ...args) {
        window.paintedText.push(String(label));
        return paint.call(this, label, ...args);
      };
    });
    for (const count of [1, 2, 3, 6]) {
      const selected = lines.slice(0, count);
      const fields = new URLSearchParams([['theme', 'teach'], ['lead', lead], ...selected.map(q => ['q', q])]);
      const report = parseReport(readDirectFields('#p?' + fields), {allowExcerptsWithoutLedger: true});
      await page.goto('about:blank');
      await page.setContent(frame.replace('__REPORT_JSON__', () => JSON.stringify(report)));
      await page.waitForFunction(() => document.querySelector('#preview')?.naturalWidth === 900);
      const {stickers, transcript, painted} = await page.evaluate(() => ({
        stickers: stickerLayouts, transcript: document.getElementById('preview').alt, painted: window.paintedText,
      }));
      assert.deepEqual(stickers.map(row => row.text), selected);
      assert.ok(painted.indexOf(selected.at(-1)) >= 0);
      assert.ok(painted.indexOf(selected.at(-1)) < painted.indexOf(lead));
      assert.ok(transcript.indexOf(selected.at(-1)) < transcript.indexOf(lead));
      assert.equal(stickers[0].x, 48);
      assert.ok(stickers[0].width < 804);
      assert.ok(stickers.every(s => s.x >= 48 && s.x + s.width <= 852));
      if (count > 1) {
        assert.equal(stickers[1].x + stickers[1].width, 852);
        assert.ok(stickers[1].x > stickers[0].x);
        assert.ok(stickers[0].fontSize > stickers[1].fontSize);
      }
    }
  } finally {
    await browser.close();
  }
});
