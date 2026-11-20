import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import test from 'node:test';

const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require(process.env.PUAI_PLAYWRIGHT_PACKAGE || 'playwright-core'));
} catch (error) {
  if (error.code !== 'MODULE_NOT_FOUND' || process.env.PUAI_PLAYWRIGHT_PACKAGE) throw error;
}

// Run with playwright-core installed and either bundled Chromium or PUAI_CHROMIUM.
test('report links open the PNG; manual recovery requires a tap', {
  skip: !chromium && 'Install playwright-core to run the browser integration.',
}, async () => {
  const browser = await chromium.launch({ executablePath: process.env.PUAI_CHROMIUM });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const base = 'https://reports.test/make/';
    const raw = ['v2', 'edison', '样例', '把杯子翻过来当鼓。', '11-05:1:1', '', '',
      '给每个杯子配个盖子，然后请助手依次比较哪个敲起来比较像小鼓。', '', '',
      '11-05~原来这套杯子还自带打击乐。', '', '', '敲杯成乐', '', ''].join('｜');
    const fragment = '#'+encodeURIComponent(raw);
    const form = page.locator('#form');
    const recovery = page.locator('#recover');
    const preview = page.locator('#preview');
    const ready = async () => {
      await page.waitForFunction(() => document.getElementById('preview').naturalWidth === 900);
      assert.equal(await form.isVisible(), false);
      assert.equal(await page.locator('#save').isVisible(), true);
    };
    let failFrame = false;
    let inspectLoading = false;
    const requested = [];
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      requested.push(url.pathname + url.search);
      const name = url.pathname.split('/').pop() || 'index.html';
      if (url.origin !== new URL(base).origin ||
          !['index.html', 'report-code.mjs', 'plain-report.mjs', 'make.js', 'poster-frame.txt'].includes(name)) {
        return route.abort();
      }
      if (name === 'make.js' || name === 'poster-frame.txt') {
        if (inspectLoading) assert.equal(await form.isVisible(), false);
        if (name === 'poster-frame.txt' && failFrame) {
          failFrame = false;
          return route.fulfill({ status: 503 });
        }
      }
      const body = await readFile(new URL('../docs/make/'+name, import.meta.url));
      const contentType = name.endsWith('.html') ? 'text/html' : name.endsWith('.txt') ? 'text/plain' : 'text/javascript';
      await route.fulfill({ body, contentType });
    });
    inspectLoading = true;
    await page.goto(base+'?utm_source=chatgpt.com'+fragment);
    await ready();
    const alt = await preview.getAttribute('alt');
    assert.ok(alt.includes('原来这套杯子还自带打击乐。'));
    inspectLoading = false;

    // A regular chat can put just the visible fields in a fragment. Opening
    // it in a fresh tab needs no clipboard, server record or previous visit.
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'clipboard', { value: {
        readText: () => { window.__readClipboard = true; throw new Error('clipboard is off'); }
      } });
    });
    const named = new URLSearchParams([['q','是盖子高了？'],['ai','是杯子矮了。'],
      ['q','这两件事在茶几上有区别吗？'],['theme','einstein'],['tag','量杯师']]);
    const directURL = base + '?utm_source=chatgpt.com#p?' + named;
    await page.goto(directURL);
    await ready();
    const turns = await preview.getAttribute('alt');
    const positions = ['是盖子高了？','是杯子矮了。','这两件事在茶几上有区别吗？'].map(q => turns.indexOf(q));
    assert.ok(positions.every((position, i) => position >= 0 && (!i || position > positions[i - 1])));
    assert.equal(await page.evaluate(() => window.__readClipboard), undefined);
    assert.ok(requested.every(url => !decodeURIComponent(url).includes('杯子矮')));
    await page.reload();
    await ready();
    assert.equal(await preview.getAttribute('alt'), turns);

    await page.goto(base+'#v2%EF%BD%9C');
    await page.locator('#status.error').waitFor();
    assert.equal(await form.isVisible(), false);
    assert.equal(await page.locator('#code').inputValue(), '');
    await recovery.click();
    await page.locator('#code').fill(raw);
    await page.locator('button[type="submit"]').click();
    await ready();
    assert.equal(await preview.getAttribute('alt'), alt);

    // A real template failure can be retried without copying anything.
    failFrame = true;
    await page.goto(base+'?retry=1'+fragment);
    await page.locator('#retry').waitFor();
    assert.equal(await form.isVisible(), false);
    await page.locator('#retry').click();
    await ready();

    await page.goto(base);
    await form.waitFor();
    const old = 'v1｜puai｜样例｜先约法三章｜今天可以只改错字吗｜｜错字巡逻｜';
    await page.locator('#code').fill(old);
    await page.locator('button[type="submit"]').click();
    await ready();
    await page.reload();
    await ready();
    assert.ok((await preview.getAttribute('alt')).includes('今天可以只改错字吗'));
  } finally {
    await browser.close();
  }
});
