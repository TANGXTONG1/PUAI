import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const docs = new URL('../docs/', import.meta.url);
const file = path => readFile(new URL(path, docs));
const digest = bytes => createHash('sha256').update(bytes).digest('hex');

test('唐某的官网预览、图鉴首卡和下载都使用定稿的鲜红原图', async () => {
  const approved = '69b56decd89e34d510f75101c29bb5f239f781aa13f593512369270a3b105ce1';
  const expected = 'persona-report.png?v=' + approved.slice(0,10);
  assert.equal(digest(await file('persona-report.png')), approved);
  assert.equal(digest(await file('persona-report-bright.png')), approved);
  const [home,sample,gallery] = await Promise.all(['index.html','sample.html','themes/index.html'].map(async p => (await file(p)).toString()));
  assert.ok(home.includes('src="'+expected+'"'));
  assert.ok(sample.includes('src="'+expected+'"') && sample.includes('href="'+expected+'" download'));
  const flagship = gallery.match(/<figure id="puai"[^>]*>([\s\S]*?)<\/figure>/)[1];
  for (const element of ['class="sheet"','class="save"','<img ']) {
    const tag = flagship.split(element)[1]?.split('>')[0];
    assert.ok(tag?.includes('../'+expected), element);
  }
});

test('九个样刊的预览与保存同源，静态版本号与图片字节一致', async () => {
  const gallery = (await file('themes/index.html')).toString();
  const cards = [...gallery.matchAll(/<figure id="([^"]+)"[^>]*>([\s\S]*?)<\/figure>/g)];
  assert.equal(cards.length,9);
  for (const [_,key,html] of cards) {
    const src = html.match(/<img src="([^"]+)"/)[1];
    const url = new URL(src, new URL('themes/',docs));
    const bytes = await readFile(url);
    assert.equal(url.searchParams.get('v'), digest(bytes).slice(0,10),key);
    assert.ok(html.match(/<a class="save"[^>]*>/)[0].includes('href="'+src+'"'),key);
    assert.ok(html.match(/<a class="sheet"[^>]*>/)[0].includes('href="'+src+'"'),key);
    const height = Number(html.match(/<img[^>]+ height="(\d+)"/)[1]);
    assert.equal(height, bytes.readUInt32BE(20), key);
  }
});
