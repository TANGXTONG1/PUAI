import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import test from 'node:test';
import { runInNewContext } from 'node:vm';

const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require(process.env.PUAI_PLAYWRIGHT_PACKAGE || 'playwright-core'));
} catch (error) {
  if (error.code !== 'MODULE_NOT_FOUND' || process.env.PUAI_PLAYWRIGHT_PACKAGE) throw error;
}

test('the shared launcher includes an editable signature and the official skill address', async () => {
  const source = await readFile(new URL('../assets/portable-prompt.js', import.meta.url), 'utf8');
  const prompt = runInNewContext(source + '\npuaiPortablePrompt');
  const auto = prompt();
  for (const marker of ['  ', 'XXX', '「xXx」', 'ＸＸＸ', '×××', '叉叉叉']) {
    assert.equal(prompt(marker), auto);
  }
  assert.ok(auto.includes('署名沿用我在聊天里用过的称呼'));
  assert.ok(!auto.includes('XXX'));
  assert.match(auto, /\$puai\b/);
  assert.ok(auto.includes('https://raw.githubusercontent.com/TANGXTONG1/PUAI/'));
  assert.equal(new URL(auto.split('\n').at(-1)).pathname, '/TANGXTONG1/PUAI/main/SKILL.md');
  assert.ok(auto.includes('直接在对话里显示'));
  assert.equal(new URL(auto.split('\n').at(-1)).searchParams.get('v'), '16');
  assert.match(auto, /官方模板/);
  assert.match(auto, /预览链接/);
  assert.match(auto, /别用 AI 绘图/);
  assert.ok(auto.length < 160);
  assert.equal((await readFile(new URL('../docs/go.txt', import.meta.url), 'utf8')).trim(), auto);
  for (const name of ['不愿透露姓名的唐某', '我', 'XXX号', 'Ｘ某']) {
    assert.equal(prompt(name), auto.replace('署名沿用我在聊天里用过的称呼', '署名「' + name + '」'));
  }
  const canonical = await readFile(new URL('../SKILL.md', import.meta.url), 'utf8');
  const firstPage = canonical.slice(0, 1850);
  assert.ok(firstPage.includes('https://xn--sxrw8m230b.com/PUAI/make/#p?'));
  assert.ok(firstPage.includes('MM-DD~') && firstPage.includes('show_puai'));
  for (const mirror of ['../docs/skill.txt', '../docs/SKILL.md']) {
    assert.equal(await readFile(new URL(mirror, import.meta.url), 'utf8'), canonical);
  }
});

test('mobile visitors can sign before copying on the home page and sample', {
  skip: !chromium && 'Install playwright-core to run the browser integration.',
}, async () => {
  const browser = await chromium.launch({ executablePath: process.env.PUAI_CHROMIUM });
  try {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 },
      permissions: ['clipboard-read', 'clipboard-write'] });
    const page = await context.newPage();
    for (const file of ['index.html', 'sample.html']) {
      const url = new URL('../docs/' + file, import.meta.url);
      if (file === 'index.html') url.hash = 'go';
      await page.goto(url.href);
      const copy = page.getByRole('button', { name: '复制生成口令' });
      const bounds = await copy.boundingBox();
      assert.ok(bounds && bounds.y >= 0 && bounds.y + bounds.height <= 844);
      const nickname = page.getByLabel(/署名/);
      assert.ok(await nickname.isVisible());
      await nickname.fill('山楂');
      await copy.click();
      await page.waitForFunction(() => document.querySelector('#status').textContent.includes('已复制'));
      assert.match(await page.evaluate(() => navigator.clipboard.readText()), /署名「山楂」/);
    }
  } finally {
    await browser.close();
  }
});

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
    const downloads = [];
    page.on('download', file => downloads.push(file));
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
    assert.equal(await page.locator('#dates-copy').isVisible(), false);
    const alt = await preview.getAttribute('alt');
    assert.ok(alt.includes('原来这套杯子还自带打击乐。'));
    inspectLoading = false;

    // A regular chat can put just the visible fields in a fragment. Opening
    // it in a fresh tab needs no clipboard, server record or previous visit.
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
        readText: () => { window.__readClipboard = true; throw new Error('clipboard is off'); }
      } });
    });
    const named = new URLSearchParams([['q','是盖子高了？'],['ai','是杯子矮了。'],
      ['q','这两件事在茶几上有区别吗？'],['theme','einstein'],['tag','量杯师']]);
    const directURL = base + '?utm_source=chatgpt.com#p?' + named;
    await page.goto(directURL);
    await ready();
    assert.equal(downloads.length, 0);
    const datesButton = page.getByRole('button', { name: '复制补日期口令' });
    assert.equal(await datesButton.isVisible(), true);
    await page.evaluate(() => {
      Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
        writeText: async () => { throw new Error('clipboard unavailable'); }
      }});
    });
    await datesButton.click();
    const followup = await page.locator('#dates-text').inputValue();
    assert.equal(await page.locator('#dates-text').isVisible(), true);
    assert.ok(followup.includes('$puai') && followup.includes('保留原话'));
    const shared = (await readFile(new URL('../docs/go.txt', import.meta.url), 'utf8')).trim();
    assert.equal(followup.split('\n').at(-1), shared.split('\n').at(-1));
    const claim = page.getByRole('link', { name: '领取同款生成口令' });
    assert.equal(await claim.getAttribute('href'), '../#go');
    const footer = await claim.boundingBox();
    const imageBounds = await preview.boundingBox();
    assert.ok(footer.width > 0 && footer.height >= 44);
    assert.ok(Math.abs(footer.y + footer.height - imageBounds.y - imageBounds.height) < 3);
    const description = await preview.getAttribute('alt');
    assert.ok(description.endsWith('扫码获取口令，发给自己的 Agent 总结出图。'));
    assert.doesNotMatch(description, /唐苑容\.com|xn--sxrw8m230b|#go/u);
    assert.doesNotMatch(description, /随图问|图里说怎么做/u);
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
    // A browser-capable agent can return these bytes as a chat image without Python.
    await page.locator('#code').fill('PUAI 2026\n署名：试映员\n原话：灯泡还能领年终奖？\n日期账：07-15:3:?');
    await page.locator('button[type="submit"]').click();
    await ready();
    const src = await preview.getAttribute('src');
    assert.match(src, /^data:image\/png;base64,/);
    const pixels = Buffer.from(src.split(',')[1], 'base64');
    assert.equal(pixels.subarray(1,4).toString(), 'PNG');
    assert.equal(pixels.readUInt32BE(16), 900);
    assert.ok((await preview.getAttribute('alt')).includes('3 条'));
    assert.ok(requested.every(url => !decodeURIComponent(url).includes('年终奖')));

    await page.goto('about:blank');
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
