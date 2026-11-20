import test from 'node:test';
import assert from 'node:assert/strict';
import { parsePlainReport, readDirectFields } from '../docs/make/plain-report.mjs';
import { parseReport } from '../docs/make/report-code.mjs';

function report(link) {
  return parseReport(readDirectFields(link), { allowExcerptsWithoutLedger: true });
}

test('a single named persona among the tags selects its original edition on both web entry points', () => {
  const labels = { PUAI: 'puai', AI的教育: 'teach', AICU: 'aicu', AI特全体: 'all',
    AI在心口难开: 'hush', AI因斯坦: 'einstein', 爱因斯坦: 'einstein', AI迪生: 'edison',
    AI的供养: 'support', AI咋咋地: 'free' };
  for (const [label, theme] of Object.entries(labels)) {
    const plain = parsePlainReport('PUAI 2026\n人格标签：双耳杯、' + label + '\n原话：挑一只耳朵喝。');
    const link = report('#p?' + new URLSearchParams([['tag','双耳杯'],['tag',label],['q','挑一只耳朵喝。']]));
    assert.equal(plain.theme, theme, label);
    assert.deepEqual(plain.keywords, ['双耳杯']);
    assert.deepEqual(link, plain);
  }
  assert.equal(report('#p?q=挑一只。&tag=PUAI&tag=AICU').theme, null);
  assert.equal(report('#p?q=挑一只。&tag=当场纠偏').theme, null);
  assert.equal(report('#p?q=挑一只。&tag=PUAI&theme=待定').theme, null);
  assert.equal(report('#p?q=挑一只。&tag=PUAI&theme=free').theme, 'free');
});

test('原话划线、复读和接话在网页端保持对应', () => {
  const card = report('#p?' + new URLSearchParams([
    ['q','多调研点啊，我缺你这点 token 吗？'], ['repeat','4'], ['mark','我缺你这点 token 吗？'],
    ['ai','我再看看。'], ['q','这次够了。'], ['mark','新编半句'], ['repeat','0'],
  ]));
  assert.deepEqual(card.activity.share_quotes, [
    {text:'多调研点啊，我缺你这点 token 吗？',repeat_count:4,emphasis:'我缺你这点 token 吗？'},
    {text:'这次够了。'},
  ]);
  assert.deepEqual(card.story.assistant_reply, {after_quote:1,text:'我再看看。'});
  assert.equal(card.activity.summary, undefined);
});

test('named links carry a readable scene, preserve speaker turns, and retain the real daily ledger', () => {
  const source = new URLSearchParams([
    ['theme', 'teach'], ['name', '画圈人'], ['lead', '同一只杯子被要求画三次把手。'],
    ['q', '10-08~先画把手。'], ['use', '先把草图翻了个面'], ['ai', '杯子有两个把手。'],
    ['tag', '双耳杯'], ['q', '10-08~那你挑一边喝。'], ['days', '10-08:2:1'], ['token', '100']
  ]);
  const path = 'https://example.org/make/?utm_source=chatgpt.com#p?' + source;
  const card = report(path);
  assert.equal(card.person.name, '画圈人');
  assert.equal(card.story.lead, '同一只杯子被要求画三次把手。');
  assert.deepEqual(card.story.assistant_reply, { after_quote: 1, text: '杯子有两个把手。' });
  assert.deepEqual(card.activity.share_quotes.map(q => q.text), ['先画把手。', '那你挑一边喝。']);
  assert.deepEqual(card.activity.daily_profile.habits, ['先把草图翻了个面']);
  assert.equal(card.activity.summary.messages, 2);
  assert.equal(card.activity.token_usage.total_tokens, 100);
  assert.deepEqual(report('[打开图](<' + path + '>)'), card);
});

test('legacy placeholder signatures do not appear on linked posters', () => {
  assert.equal(report('#p?name=XXX&q=你偷偷换杯子了？').person.name, '我');
  assert.equal(parseReport(['v1','puai','「ＸＸＸ」','偷换杯子','你偷偷换杯子了？','','换杯','']).person.name, '我');
});

test('only the named values are encoded; original special characters survive the URL round-trip', () => {
  const quote = 'C++ &= #1 [100%] (%20) | ｜ 🫖';
  const fragment = '#p?' + new URLSearchParams([['q',quote],['tag','代码茶']]);
  const card = report(fragment);
  assert.equal(card.activity.share_quotes[0].text, quote);
  assert.deepEqual(report(fragment.replace('&tag=', '&amp;tag=')), card);
  assert.equal(report('#p?q=走，去喝茶。').activity.share_quotes[0].text, '走，去喝茶。');
  assert.equal(card.activity.summary, undefined);
});

test('a stand-alone lead or verified excerpt renders without invented activity or duplicated habits', () => {
  const card = report('#p?lead=把杯盖当计时器。&use=把杯盖当计时器。&use=用茶匙拨响。');
  assert.deepEqual(card.story, { persona: '', scenes: [], lead: '把杯盖当计时器。' });
  assert.deepEqual(card.activity.daily_profile.habits, ['用茶匙拨响。']);
  assert.equal(card.activity.summary, undefined);
  assert.equal(card.activity.share_quotes.length, 0);
  assert.equal(report('#p?lead=比较两把茶匙。').story.lead, '比较两把茶匙。');
  assert.equal(report('#p?q=11-04~谁把茶倒给了盖子？').activity.share_quotes[0].date, '2026-11-04');
});

test('private diagnosis, injected fields and unsupported totals cannot become report content', () => {
  assert.equal(readDirectFields('https://example.org/make/?q=无私人片段'), null);
  assert.equal(readDirectFields('#v2｜old'), null);
  assert.throws(() => report('#p?theme=teach'));
  assert.throws(() => report('#p?q=有问题%0A原话：多一句'));
  assert.throws(() => report('#p?theme=teach&q=只有一条&other=不应展示'));
  assert.throws(() => report('#p?days=11-10:1:1&q=真话&theme=teach&q=第二条'));
});

test('an explicitly selected final AI line belongs after the last visible user quote', () => {
  const close = '我没法确认自己的型号。';
  const card = report('#p?q=第三次问了，你是谁？&endai=' + close);
  assert.equal(card.story.final_reply, close);
  assert.equal(card.story.assistant_reply, undefined);
  assert.equal(report('#p?q=谁？&ai=' + close).story.final_reply, undefined);
  assert.equal(report('#p?endai=' + close + '&q=谁？').story.final_reply, undefined);
  const misplaced = report('#p?q=第一句&endai=提前的结尾&q=真正的最后一问');
  assert.equal(misplaced.story.final_reply, undefined);
  const unselected = report('#p?q=一&q=二&q=三&q=四&endai=只答第四问');
  assert.equal(unselected.story.final_reply, '只答第四问');
  const both = report('#p?q=第一句&ai=中间的答复&q=第二句&endai=再答一句');
  assert.equal(both.story.assistant_reply.text, '中间的答复');
  assert.equal(both.story.final_reply, undefined);
});

test('a scoped scene cannot claim an annual theme; broader history can carry six different turns', () => {
  const turns = ['一','二','三','四','五','六'];
  const link = '#p?' + new URLSearchParams([['theme', 'teach'], ...turns.map(q => ['q',q])]);
  assert.equal(report(link).scope, 'fragments');
  assert.equal(report(link + '&scope=thread').scope, 'thread');
  const broad = report(link + '&scope=history&endai=最后的回复');
  assert.equal(broad.scope, 'history');
  assert.deepEqual(broad.activity.share_quotes.map(q => q.text), turns);
  assert.equal(broad.story.final_reply, '最后的回复');
  assert.equal(report(link + '&undated=6:?').scope, 'fragments');
  const early = report('#p?scope=history&q=02-02~二月的原话&q=07-03~暑假的原话&days=07-03:1:?');
  assert.equal(early.activity.share_quotes.length, 2);
  assert.equal(early.activity.summary.messages, 1);
  assert.equal(early.activity.daily_profile.active_days, 1);
  assert.throws(() => report(link+'&scope=invented'));
  assert.equal(report(link + '&days=01-02:6:?').scope, undefined);
});

test('observed owner dates round-trip without inventing a message ledger', () => {
  const partial = report('#p?q=03-08~第二回合&q=第三回合&dates=03-08,03-09,03-08');
  assert.deepEqual(partial.activity.observed_dates, ['2026-03-08','2026-03-09']);
  assert.equal(partial.activity.summary, undefined);
  assert.equal(partial.activity.daily_profile.active_days, undefined);
  const mixed = report('#p?days=03-08:2:?&q=03-09~另一个现场&dates=03-09');
  assert.equal(mixed.activity.summary.messages, 2);
  assert.deepEqual(mixed.activity.share_quotes[0], {date:'2026-03-09', text:'另一个现场'});
  const undated = report('#p?q=03-09~有日期的一句&q=未标记日期的一句&undated=1:?');
  assert.equal(undated.activity.summary.messages, 1);
  assert.equal(undated.activity.share_quotes[0].date, '2026-03-09');
  assert.throws(() => report('#p?q=一个现场&dates=02-29'), /日期/);
});
