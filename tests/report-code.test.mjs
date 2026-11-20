import assert from 'node:assert/strict';
import test from 'node:test';
import { parseReport, readFields } from '../docs/make/report-code.mjs';

function report(source) {
  return parseReport(readFields(source));
}

const fields = ['v2', 'einstein', '小明', '总要多问一个反例。',
  '01-02:2:1,04-18:3:1,06-02:2:1,08-01:4:1,08-02:2:1', '2:1', '',
  '先问结论的分母', '要一个反例', '', '01-02~分母呢？', '讲讲这 50% (怎么算的)。', '给我一个反例。',
  '分母呢', '反例呢', ''];

test('链接、原始备用码和刷新都保留整份账，选展三个月不缩小分母', () => {
  const raw = fields.join('｜');
  const markdown = '[打开](<https://example.org/#' + fields.map(encodeURIComponent).join('｜') + '>)';
  const refreshed = '#' + readFields(raw).map(encodeURIComponent).join('|');
  const expected = report(raw);
  assert.deepEqual(report(markdown), expected);
  assert.deepEqual(report(refreshed), expected);
  const { activity } = expected;
  assert.equal(activity.summary.messages, 15);
  assert.equal(activity.theme_stats.messages, 6);
  assert.equal(activity.daily_profile.active_days, 5);
  assert.equal(activity.daily_profile.theme_days, 5);
  assert.deepEqual(activity.daily_profile.peak, { date: '2026-08-01', count: 4 });
  assert.equal(activity.months.length, 3);
  assert.equal(activity.rhythm.analysis_months.length, 4);
  assert.equal(activity.share_quotes[0].date, '2026-01-02');
  assert.equal(activity.share_quotes[1].text, fields[11]);
  assert.equal(activity.daily_profile.habits.length, 2);
});

test('缺少主题核验时保留发言、活跃日和已知月份的零命中', () => {
  const mixed = [...fields];
  mixed[1] = 'puai';
  mixed[4] = '01-02:2:0,02-10:5:?';
  const { activity } = report(mixed.join('｜'));
  assert.equal(activity.summary.messages, 9);
  assert.equal(activity.daily_profile.active_days, 2);
  assert.equal(activity.daily_profile.theme_days, undefined);
  assert.equal(activity.summary.roast_messages, undefined);
  assert.equal(activity.months[0].roast_messages, 0);
  assert.equal(activity.months[1].roast_messages, undefined);
  assert.equal(activity.token_usage, undefined);
});

test('只有摘要时留下具体用法，空画像和没有消息支撑的引语不可出图', () => {
  const memory = [...fields];
  memory.fill('', 4, 13);
  assert.throws(() => report(memory.join('｜')));
  memory[7] = '斟酌措辞时让助手读出声';
  const { activity } = report(memory.join('｜'));
  assert.deepEqual(activity.daily_profile.habits, [memory[7]]);
  assert.equal(activity.summary, undefined);
  assert.equal(activity.months, undefined);
  memory[10] = '分母呢？';
  assert.throws(() => report(memory.join('｜')));
  memory[5] = '4:0';
  const undated = report(memory.join('｜')).activity;
  assert.equal(undated.summary.messages, 4);
  assert.equal(undated.theme_stats.messages, 0);
  assert.equal(undated.months, undefined);
});

test('数字和日期相互校验，已分享的 v1 照常打开', () => {
  for (const invalid of ['02-29:5:1', '01-02:1:2', '01-02:2:1,01-02:2:1']) {
    const draft = [...fields];
    draft[4] = invalid;
    assert.throws(() => report(draft.join('｜')));
  }
  const legacy = report('v1｜puai｜我｜先夸后骂｜好一个 50%。｜｜仅退款｜');
  assert.equal(legacy.activity.share_quotes[0].text, '好一个 50%。');
  assert.deepEqual(legacy.keywords, ['仅退款']);
});
