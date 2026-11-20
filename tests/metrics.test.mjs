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

const base = 'https://xn--sxrw8m230b.com/PUAI/';
const docs = new URL('../docs/', import.meta.url);
const nickname = 'PrivNick43';
const quote = 'PrivQuote43';
const secret = 'PrivQuery43';
const protectedText = /Priv(?:Nick|Quote|Query)43/;
const mime = {
  html: 'text/html', css: 'text/css', js: 'text/javascript', mjs: 'text/javascript',
  txt: 'text/plain', png: 'image/png', svg: 'image/svg+xml', woff2: 'font/woff2', zip: 'application/zip',
};
const clickEvent = (action, surface) => ({ type: 'puai-click', action, surface });

async function visitor(browser, t, { choice, dnt = false, failGoogle = false } = {}) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  t.after(() => context.close());
  const google = [];
  const unexpected = [];
  await context.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.hostname === 'www.googletagmanager.com') {
      google.push({ url: url.href, referer: request.headers().referer || '', post: request.postData() || '' });
      if (failGoogle) return route.abort();
      return route.fulfill({ contentType: 'text/javascript', body: 'window.__offlineTagLoaded = true;' });
    }
    if (!url.href.startsWith(base)) {
      unexpected.push(url.href);
      return route.abort();
    }
    const path = url.pathname.slice(new URL(base).pathname.length);
    const file = path.endsWith('/') || !path ? path + 'index.html' : path;
    try {
      const body = await readFile(new URL(file, docs));
      return route.fulfill({ body, contentType: mime[file.split('.').pop()] || 'application/octet-stream' });
    } catch {
      return route.fulfill({ status: 404, body: 'missing fixture asset' });
    }
  });
  t.after(() => assert.deepEqual(unexpected, [], 'no other external requests'));
  await context.addInitScript(({ choice, dnt }) => {
    if (choice) localStorage.setItem('yuanrong.analytics-consent.v1', choice);
    if (dnt) Object.defineProperty(navigator, 'doNotTrack', { get: () => '1' });
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
      writeText: async text => { window.__clipboard = text; },
      readText: async () => window.__clipboard || '',
    } });
    window.__incoming = [];
    window.addEventListener('message', event => {
      if (event.data?.type === 'puai-click') window.__incoming.push(event.data);
    });
  }, { choice, dnt });
  const page = await context.newPage();
  page.setDefaultTimeout(6500);
  function frame() {
    return page.frames().find(f => new URL(f.url() || 'about:blank').pathname.endsWith('/metrics-frame.html'));
  }
  async function deliveries() {
    const f = frame();
    return f ? f.evaluate(() => window.__incoming) : [];
  }
  async function expectEvents(list, previousRequests = 0) {
    await page.waitForFunction(length => {
      const metrics = document.querySelector('iframe[src*="metrics-frame.html"]');
      const commands = metrics?.contentWindow?.dataLayer || [];
      return commands.filter(row => row[0] === 'event').length >= length;
    }, list.length);
    const f = frame();
    assert.ok(f, 'the reporting frame loaded');
    await f.waitForFunction(() => window.__offlineTagLoaded);
    assert.deepEqual(await deliveries(), list, 'only allowlisted message fields cross into the analytics frame');
    const state = await f.evaluate(() => ({
      referrer: document.referrer,
      location: location.href,
      sent: (window.dataLayer || []).map(row => Array.from(row)),
    }));
    const sent = state.sent.filter(row => row[0] === 'event');
    assert.deepEqual(sent.map(row => [row[1], row[2]?.puai_surface]),
      list.map(({ action, surface }) => ['puai_' + action, surface]));
    assert.doesNotMatch(JSON.stringify([state, google]), protectedText);
    assert.ok(state.sent.every(row => !row[2]?.user_id && !row[2]?.client_id));
    assert.equal(google.length - previousRequests, 1, 'load the external script once per document');
  }
  async function expectIdle() {
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    assert.equal(await page.locator('iframe[src*="metrics-frame.html"]').count(), 0);
    assert.equal(frame(), undefined, 'no tracking frame before a qualifying, consented click');
    assert.equal(google.length, 0);
  }
  return { page, expectEvents, expectIdle, google };
}

test('anonymous click metrics are opt-in and independent of report delivery', {
  skip: !chromium && 'Install playwright-core to exercise the analytics boundary.',
}, async t => {
  const browser = await chromium.launch({ executablePath: process.env.PUAI_CHROMIUM });
  t.after(() => browser.close());

  await t.test('first copy works before consent; opting in counts that click exactly once', async t => {
    const { page, expectIdle, expectEvents } = await visitor(browser, t);
    await page.goto(base + '?source=' + secret + '#go');
    await expectIdle();
    await page.locator('#nickname').fill(nickname);
    await page.locator('#copy').click();
    await page.waitForFunction(() => window.__clipboard?.includes('PrivNick43'));
    await expectIdle();
    await page.getByRole('button', { name: '允许统计', exact: true }).click();
    await expectEvents([clickEvent('copy_prompt', 'home')]);
    await page.locator('#copy').click();
    await expectEvents([clickEvent('copy_prompt', 'home'), clickEvent('copy_prompt', 'home')]);
    await page.locator('a[href*="PUAI-skill.zip"]').click();
    await expectEvents([clickEvent('copy_prompt', 'home'), clickEvent('copy_prompt', 'home'),
      clickEvent('download_skill', 'home')]);
  });

  await t.test('denial and DNT suppress the frame, Google requests and subsequent tracking', async t => {
    const first = await visitor(browser, t);
    await first.page.goto(base);
    await first.page.locator('#copy').click();
    await first.page.getByRole('button', { name: '拒绝统计', exact: true }).click();
    await first.page.goto(base + 'sample.html');
    await first.page.locator('#copy').click();
    await first.page.waitForFunction(() => window.__clipboard?.includes('$puai'));
    await first.expectIdle();
    const dnt = await visitor(browser, t, { choice: 'granted', dnt: true });
    await dnt.page.goto(base);
    await dnt.page.locator('#copy').click();
    await dnt.expectIdle();
  });

  await t.test('sample copy and save are separate clicks; withdrawing stops later events', async t => {
    const { page, expectEvents, google } = await visitor(browser, t);
    await page.goto(base + 'sample.html');
    await page.locator('#copy').click();
    await page.getByRole('button', { name: '允许统计', exact: true }).click();
    await page.locator('a.download').click();
    await expectEvents([clickEvent('copy_prompt', 'sample'), clickEvent('save_report', 'sample')]);
    await page.locator('[data-puai-privacy]').click();
    await page.getByRole('button', { name: '撤回同意', exact: true }).click();
    await page.locator('#copy').click();
    assert.equal(await page.locator('iframe[src*="metrics-frame.html"]').count(), 0);
    assert.equal(google.length, 1);
  });

  await t.test('gallery card and modal saves count; opening a poster stays silent', async t => {
    const { page, expectIdle, expectEvents } = await visitor(browser, t, { choice: 'granted' });
    await page.goto(base + 'themes/');
    await expectIdle();
    await page.locator('#puai .save').click();
    await expectEvents([clickEvent('save_report', 'gallery')]);
    await page.locator('#einstein .sheet').click();
    await page.locator('dialog[open] #download').click();
    await expectEvents([clickEvent('save_report', 'gallery'), clickEvent('save_report', 'gallery')]);

    const fresh = await visitor(browser, t);
    await fresh.page.goto(base + 'themes/');
    await fresh.page.locator('#hush .sheet').click();
    await fresh.expectIdle();
    await fresh.page.locator('dialog[open] #download').click();
    await fresh.expectIdle();
    await fresh.page.getByRole('button', { name: '允许统计', exact: true }).click();
    await fresh.expectEvents([clickEvent('save_report', 'gallery')]);
  });

  await t.test('a failed provider and a synthetic click do not interfere with the sample copy', async t => {
    const { page, expectIdle, google } = await visitor(browser, t, { choice: 'granted', failGoogle: true });
    await page.goto(base + 'sample.html?source=' + secret);
    await page.locator('#copy').evaluate(el => el.click());
    await expectIdle();
    await page.locator('#nickname').fill(nickname);
    await page.locator('#copy').click();
    await page.waitForFunction(() => window.__clipboard?.includes('PrivNick43'));
    await page.waitForLoadState('networkidle');
    assert.equal(google.length, 1);
    assert.doesNotMatch(JSON.stringify(google), protectedText);
  });

  await t.test('opening a private poster is silent; save and share carry only action and surface', async t => {
    const { page, expectIdle, expectEvents } = await visitor(browser, t, { choice: 'granted' });
    const fields = new URLSearchParams({ name: nickname, scope: 'thread', theme: 'puai', q: quote });
    await page.goto(base + 'make/?source=' + secret + '#p?' + fields);
    await page.waitForFunction(() => document.querySelector('#preview').naturalWidth === 900);
    await expectIdle();
    await page.locator('#save').click();
    await expectEvents([clickEvent('save_report', 'make')]);
    await page.locator('#share').click();
    await expectEvents([clickEvent('save_report', 'make'), clickEvent('share_report', 'make')]);
  });

  await t.test('keyboard submit, paste and recover-from-excerpt each track a single generate click', async t => {
    const { page, expectIdle, expectEvents, google } = await visitor(browser, t, { choice: 'granted' });
    const receipt = 'PUAI 2026\n署名：' + nickname + '\n原话：' + quote;
    await page.goto(base + 'make/?stage=automatic');
    await expectIdle();
    await page.locator('#code').fill(receipt);
    await page.locator('#form').evaluate(form => form.requestSubmit());
    await page.waitForFunction(() => document.querySelector('#preview').naturalWidth === 900);
    await expectIdle();
    await page.goto(base + 'make/?stage=manual');
    await page.locator('#code').fill(receipt);
    await page.locator('button[type=submit]').press('Enter');
    await expectEvents([clickEvent('generate_report', 'make')]);
    const previousRequests = google.length;
    await page.goto(base + 'make/?stage=paste');
    await page.evaluate(text => { window.__clipboard = text; }, receipt);
    await page.locator('#paste').click();
    await expectEvents([clickEvent('generate_report', 'make')], previousRequests);
    const beforeRecovery = google.length;
    await page.goto(base + 'make/?stage=legacy');
    await page.locator('#code').fill('从 2026 年片段里选了你追问“纸杯洗完还会响吗？”的现场。\n[查看并保存长图]()');
    await page.locator('button[type=submit]').click();
    await page.locator('#use-partial').click();
    await expectEvents([clickEvent('generate_report', 'make'), clickEvent('generate_report', 'make')], beforeRecovery);
  });
});
