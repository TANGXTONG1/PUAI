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

test('A版在 PNG 上绘制日期栏，区分日期线索、完整日账和无日期的原话', {
  skip: !chromium && 'Install playwright-core to run the browser integration.',
}, async () => {
  const frame = await readFile(new URL('../docs/make/poster-frame.txt', import.meta.url), 'utf8');
  const browser = await chromium.launch({ executablePath: process.env.PUAI_CHROMIUM });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  try {
    // The transcript alone does not prove that a date was painted in the PNG.
    await page.addInitScript(() => {
      window.painted = [];
      const original = CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText = function(label, ...rest) {
        window.painted.push(String(label));
        return original.call(this, label, ...rest);
      };
    });
    for (const [query, included, excluded] of [
      ['q=甲&q=乙&q=丙&q=丁', ['发言日历','这 4 句原话未附日期'], ['单日最高发言','有发言的日子']],
      ['q=02-05~甲&q=02-05~乙&q=丙', ['片段日期','核实 1 天','2 / 3 句原话有日期','02 月'], ['单日最高发言','有发言的日子']],
      ['dates=02-05,02-05,07-15', ['片段日期','核实 2 天','02 月','07 月'], ['单日最高发言','有发言的日子']],
      ['dates=02-05,07-15&days=07-15:11:?', ['发言日历','单日最高发言','另有 1 个已知日期','11 条指令'], ['片段日期']],
      ['q=02-01~原话。&dates=02-01,03-01,04-01,05-01', ['片段日期','02 月','04 月','05 月'], ['03 月','条指令']],
      ['dates=07-16&days=07-15:11:?', ['发言日历','另有 1 个已知日期','11 条指令'], ['片段日期']],
    ]) {
      const report = parseReport(readDirectFields('#p?' + query), { allowExcerptsWithoutLedger: true });
      await page.goto('about:blank');
      await page.setContent(frame.replace('__REPORT_JSON__', () => JSON.stringify(report)));
      await page.waitForFunction(() => document.querySelector('#preview')?.naturalWidth === 900);
      const labels = await page.evaluate(() => window.painted);
      for (const label of included) assert.ok(labels.includes(label), JSON.stringify({ label, labels }));
      for (const label of excluded) assert.ok(!labels.includes(label), label);
      assert.match(await page.locator('#preview').getAttribute('alt'), new RegExp(included[0]));
      if (query.startsWith('dates=07-16')) {
        const colors = await page.evaluate(() => ['15','16','17'].map(day => {
          comicCell(1,1,23,dayState('2026-07-'+day));
          return Array.from(ctx.getImageData(9,11,1,1).data);
        }));
        assert.deepEqual(colors[1], colors[0], 'a verified date with unknown volume gets a speaking-day dot');
        assert.notDeepEqual(colors[1], colors[2], 'the surrounding unknown date stays unmarked');
        assert.equal(report.activity.daily_profile.dated_messages, 11);
      }
    }
  } finally {
    await browser.close();
  }
});
