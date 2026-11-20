import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import test from 'node:test';

const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require(process.env.PUAI_PLAYWRIGHT_PACKAGE || 'playwright-core'));
} catch (error) {
  if (error.code !== 'MODULE_NOT_FOUND' || process.env.PUAI_PLAYWRIGHT_PACKAGE) throw error;
}

const plain = '仅供助手核对的历史背景。\nPUAI 2026\n主题：teach\n原话：把那只小鼓翻回来。\n标签：嗒嗒嗒嗒嗒嗒省略尾文\n\n保存地址 https://example.org/make/';
const old = 'v1｜puai｜我｜开庭了｜把那只小鼓翻回来。｜｜敲小鼓｜';

test('mobile copy/paste delivers a PNG, including stripped-link and denied-clipboard recovery', {
  skip: !chromium && 'Install playwright-core to run the browser integration.',
}, async () => {
  const assets = new Set(['index.html', 'make.js', 'report-code.mjs', 'plain-report.mjs', 'poster-frame.txt']);
  const requests = [];
  const server = createServer(async (req, res) => {
    requests.push(req.method + ' ' + req.url);
    const url = new URL(req.url, 'http://localhost');
    const name = url.pathname.split('/').pop() || 'index.html';
    if (!assets.has(name)) { res.writeHead(404); res.end(); return; }
    try {
      const data = await readFile(new URL('../docs/make/' + name, import.meta.url));
      res.setHeader('content-type', name.endsWith('.html') ? 'text/html; charset=utf-8'
        : name.endsWith('.txt') ? 'text/plain; charset=utf-8' : 'text/javascript; charset=utf-8');
      res.end(data);
    } catch { res.writeHead(500); res.end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    const base = 'http://127.0.0.1:' + server.address().port + '/make/';
    browser = await chromium.launch({ executablePath: process.env.PUAI_CHROMIUM });
    const context = await browser.newContext({ viewport: { width: 390, height: 844 },
      permissions: ['clipboard-read', 'clipboard-write'] });
    const page = await context.newPage();
    const input = page.locator('#code');
    const ready = async () => {
      await page.waitForFunction(() => document.querySelector('#preview').naturalWidth === 900);
      assert.equal(await page.locator('#save').isVisible(), true);
      assert.equal(await page.locator('#form').isVisible(), false);
      return page.locator('#preview').getAttribute('alt');
    };
    await page.goto('about:blank');
    await page.goto(base);
    await page.evaluate(text => navigator.clipboard.writeText(text), plain);
    await page.locator('#paste').click();
    assert.match(await ready(), /把那只小鼓翻回来。/);
    assert.equal(new URL(page.url()).hash, '');
    const state = await page.evaluate(() => JSON.stringify(history.state));
    assert.ok(state.includes('把那只小鼓翻回来。'));
    assert.ok(!state.includes('仅供助手核对') && !state.includes('省略尾文') && !state.includes('保存地址'));
    await page.reload();
    assert.match(await ready(), /把那只小鼓翻回来。/);

    await page.goto('about:blank');
    await page.goBack();
    assert.match(await ready(), /把那只小鼓翻回来。/);
    const blank = await context.newPage();
    await blank.goto(base);
    await blank.locator('#form').waitFor();
    assert.equal(await blank.locator('#preview').isVisible(), false);
    await blank.close();

    // An explicit hash always wins over an existing entry's saved receipt.
    await page.evaluate(() => history.replaceState(history.state, '', '#v1|puai|我|先打分|先换个鼓再看。||评鼓|'));
    await page.reload();
    assert.match(await ready(), /先换个鼓再看。/);
    await page.evaluate(() => history.replaceState({ puaiReceipt: ['v2'] }, '', location.pathname));
    await page.reload();
    await page.locator('#form').waitFor();
    assert.equal(await page.locator('#preview').isVisible(), false);


    await page.goto('about:blank');
    await page.goto(base);
    await page.evaluate(() => {
      Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
        readText: async () => { throw new DOMException('Permission denied', 'NotAllowedError'); },
      }});
    });
    await page.locator('#paste').click();
    assert.equal(await input.evaluate(el => document.activeElement === el), true);
    assert.match(await page.locator('#status').innerText(), /长按/);
    // Exercise OS paste via its real keyboard event with Chromium's clipboard.
    await page.evaluate(() => { delete navigator.clipboard; });
    await input.press(process.platform === 'darwin' ? 'Meta+V' : 'Control+V');
    assert.match(await ready(), /把那只小鼓翻回来。/);

    // A legacy assistant narrative can carry a recoverable habit, never an attributed quote.
    await page.goto('about:blank');
    await page.goto(base);
    await input.fill('从 2026 年片段里选了你追问“纸杯洗完还会响吗？”的现场。\n[查看并保存长图]()');
    await page.locator('button[type=submit]').click();
    assert.equal(await page.locator('#partial-text').innerText(), '追问纸杯洗完还会响吗？');
    assert.equal(await page.locator('#preview').isVisible(), false);
    await page.locator('#use-partial').click();
    const habitAlt = await ready();
    assert.match(habitAlt, /追问纸杯洗完还会响吗？/);
    assert.doesNotMatch(habitAlt, /发言日历|对话现场/);

    // Generic prose and an empty link give a same-chat repair, without inventing a report.
    await page.goto('about:blank');
    await page.goto(base);
    await input.fill('回顾结束。\n[查看并保存长图]()');
    await page.locator('button[type=submit]').click();
    assert.equal(await page.locator('#preview').isVisible(), false);
    assert.equal(await page.locator('#partial').isVisible(), false);
    await page.locator('#repair-copy').click();
    assert.match(await page.evaluate(() => navigator.clipboard.readText()), /PUAI 2026/);

    // A full legacy response with an actual link wins over the surrounding old prose.
    await page.goto('about:blank');
    await page.goto(base);
    await input.fill('从 2026 年片段里选了你追问“纸杯会响吗？”的现场。\n[查看并保存长图](<' + base + '#' + encodeURIComponent(old) + '>)');
    await page.locator('button[type=submit]').click();
    assert.match(await ready(), /把那只小鼓翻回来。/);
    await page.reload();
    assert.match(await ready(), /把那只小鼓翻回来。/);
    assert.ok(requests.every(req => req.startsWith('GET ') && !/小鼓|纸杯|%e5%b0%8f/i.test(req)));
  } finally {
    await browser?.close();
    await new Promise(resolve => server.close(resolve));
  }
});
