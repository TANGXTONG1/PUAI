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
      window.stickerPaths = [];
      const stroke = CanvasRenderingContext2D.prototype.stroke;
      CanvasRenderingContext2D.prototype.stroke = function(...args) {
        const {e:x, f:y} = this.getTransform();
        if (x >= 48 && y > 0 && this.isPointInPath(x + 64, y + 33)) {
          window.stickerPaths.push({x, y, burst: !this.isPointInPath(x + 64, y + 2), fill:this.fillStyle});
        }
        return stroke.apply(this, args);
      };
      const paint = CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText = function(label, ...args) {
        window.paintedText.push(String(label));
        return paint.call(this, label, ...args);
      };
    });
    for (const count of [1, 2, 3, 4, 5, 6]) {
      const selected = lines.slice(0, count);
      const fields = new URLSearchParams([['theme', 'teach'], ['lead', lead], ['days','10-08:10:3'], ...selected.map(q => ['q', q])]);
      const report = parseReport(readDirectFields('#p?' + fields), {allowExcerptsWithoutLedger: true});
      await page.goto('about:blank');
      await page.setContent(frame.replace('__REPORT_JSON__', () => JSON.stringify(report)));
      await page.waitForFunction(() => document.querySelector('#preview')?.naturalWidth === 900);
      const {stickers, transcript, painted, frames, pull} = await page.evaluate(() => ({
        stickers: stickerLayouts, transcript: document.getElementById('preview').alt, painted: window.paintedText, frames:window.stickerPaths, pull:colors.pull.toLowerCase(),
      }));
      const outlines = stickers.map(s => frames.find(f => f.x === s.x && f.y === s.y));
      assert.deepEqual(outlines.map(frame => frame.burst),
        selected.map((_, i) => count <= 2 ? i === count - 1 : i % 3 === 2));
      if (count <= 2) assert.equal(outlines.at(-1).fill.toLowerCase(), pull);
      assert.deepEqual(stickers.map(row => row.text), selected);
      assert.ok(painted.indexOf(selected.at(-1)) >= 0);
      assert.ok(painted.indexOf(selected.at(-1)) < painted.indexOf(lead));
      assert.ok(painted.indexOf(selected.at(-1)) < painted.indexOf('发言日历'));
      assert.ok(painted.indexOf('发言日历') < painted.indexOf(lead));
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

test('九型独立署在图上，精选保留范围标题，兼容旧 JSON', {
  skip: !chromium && 'Install playwright-core to run the browser integration.',
}, async () => {
  const frame = await readFile(new URL('../docs/make/poster-frame.txt', import.meta.url), 'utf8');
  const themes = {puai:'PUAI', teach:'AI的教育', aicu:'AICU', all:'AI特全体', hush:'AI在心口难开',
    einstein:'AI因斯坦', edison:'AI迪生', support:'AI的供养', free:'AI咋咋地'};
  const browser = await chromium.launch({executablePath: process.env.PUAI_CHROMIUM});
  const owner = '画了一整个下午还在琢磨吃什么的人';
  try {
    const page = await browser.newPage({viewport:{width:390, height:844}});
    await page.addInitScript(() => {
      window.ink = [];
      const paint = CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText = function(value, x, y, ...extra) {
        const m = this.measureText(value), point = new DOMPoint(x, y).matrixTransform(this.getTransform());
        window.ink.push({value, x:point.x-m.actualBoundingBoxLeft, end:point.x+m.actualBoundingBoxRight, y:point.y});
        return paint.call(this, value, x, y, ...extra);
      };
    });
    const cases = Object.entries(themes).map(([theme, value], i) => ({
      theme, value, scope:['fragments','thread','history'][i%3],
    }));
    cases.push({theme:null,value:'待定',scope:'fragments'}, {theme:'hush',value:themes.hush,mode:'demo'},
      {theme:'einstein',value:themes.einstein,mode:'self_report'}, {});
    for (const {theme, value, scope, mode} of cases) {
      const report = parseReport(readDirectFields('#p?' + new URLSearchParams({name:owner, q:'真的吗？', tag:'装盘高手'})),
        {allowExcerptsWithoutLedger:true});
      if (theme === undefined) delete report.theme;
      else report.theme = theme;
      if (scope) report.scope = scope;
      else delete report.scope;
      if (mode) report.mode = mode;
      await page.goto('about:blank');
      await page.setContent(frame.replace('__REPORT_JSON__', () => JSON.stringify(report)));
      await page.waitForFunction(() => document.querySelector('#preview')?.naturalWidth === 900);
      const [ink,alt] = await Promise.all([
        page.evaluate(() => window.ink),
        page.locator('#preview').getAttribute('alt'),
      ]);
      if (!value) {
        assert.ok(alt.includes('2026 PUAI 报告'));
        assert.ok(!ink.some(t => t.value === '年度类型'));
        continue;
      }
      const isPartial = scope === 'fragments' || scope === 'thread';
      const label = isPartial ? '本次类型' : '年度类型';
      const scopeStamp = {thread:'本次对话精选',fragments:'聊天片段精选'}[scope] || '年度报告';
      const nick = ink.find(t => t.value === owner);
      const year = ink.find(t => t.value === '2026');
      const caption = ink.find(t => t.value === scopeStamp);
      const visibleType = theme ? value : '类型待定';
      const type = ink.find(t => t.value === visibleType);
      assert.ok(nick && year && caption && type, [theme, scope, label, value].join(' / '));
      assert.ok(nick.end + 20 <= year.x && year.end < caption.x && caption.end <= 852);
      assert.ok(caption.y <= 92 && type.y > 92 && type.end <= 852);
      assert.ok(!ink.some(t => t.value.includes('扫图底')));
      assert.ok(alt.includes(label+'：'+value));
      assert.ok(ink.some(t => t.value === '装盘高手'));
      if (theme) assert.ok(alt.includes('2026 '+value+' 报告'));
      if (isPartial) {
        const caption = scope === 'thread' ? '本次对话精选' : '聊天片段精选';
        assert.ok(alt.includes(caption));
      }
      if (mode) {
        const source = ink.find(t => t.value === (mode === 'demo' ? '虚拟人物样例' : '自述'));
        assert.ok(source && source.y > 92);
      }
    }
  } finally {
    await browser.close();
  }
});

test('原话换行保留铺垫和转折，也保留原标点与划线', {
  skip: !chromium && 'Install playwright-core to run the browser integration.',
}, async () => {
  const frame = await readFile(new URL('../docs/make/poster-frame.txt', import.meta.url), 'utf8');
  const browser = await chromium.launch({executablePath: process.env.PUAI_CHROMIUM});
  try {
    const page = await browser.newPage({viewport:{width:390,height:844}});
    const q = '我是想省十分钟，结果你让我提前半小时出门。';
    const fields = new URLSearchParams({theme:'einstein', q, mark:'提前半小时出门。'});
    const report = parseReport(readDirectFields('#p?'+fields), {allowExcerptsWithoutLedger:true});
    await page.setContent(frame.replace('__REPORT_JSON__', () => JSON.stringify(report)));
    await page.waitForFunction(() => document.querySelector('#preview')?.naturalWidth === 900);
    assert.deepEqual(await page.evaluate(() => stickerLayouts[0].rows),
      ['我是想省十分钟，','结果你让我提前半小时出门。']);
  } finally {
    await browser.close();
  }
});
