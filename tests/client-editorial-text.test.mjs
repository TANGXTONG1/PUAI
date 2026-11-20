import assert from 'node:assert/strict';
import test from 'node:test';
import { parseReport, readFields } from '../docs/make/report-code.mjs';

const fields = ['v2', 'einstein', '我', '把答案送回去重测。',
  '11-15:1:1,11-20:1:1', '', '', '先问 stopwatch 的零点，再问 countdown 归零以后做什么。',
  '', '', '11-15~闹钟响了才算结束吗？', '', '', '计时员', '', ''];

test('mixed-script habits exceeding the editorial target survive mobile deep links and pastes', () => {
  const pasted = fields.join('｜');
  const link = 'https://example.com/make/?utm_source=chatgpt.com#' + encodeURIComponent(pasted);
  for (const source of [pasted, link]) {
    const { activity } = parseReport(readFields(source));
    assert.deepEqual(activity.daily_profile.habits, [fields[7]]);
    assert.equal(activity.summary.messages, 2);
    assert.equal(activity.share_quotes[0].text, '闹钟响了才算结束吗？');
  }
});

test('a runaway editorial aside cannot block the report or modify its quoted evidence', () => {
  const variant = [...fields];
  variant[7] = '很长的补充说明'.repeat(80);
  const { activity } = parseReport(readFields(variant.join('｜')));
  assert.ok(activity.daily_profile.habits[0].endsWith('…'));
  assert.equal(activity.share_quotes[0].text, '闹钟响了才算结束吗？');
  variant[4] = '11-15:1:2';
  assert.throws(() => parseReport(readFields(variant.join('｜'))), /命中数/);
});

test('v2 can deliver facts without a personality verdict', () => {
  const direct = [...fields];
  direct[3] = '';
  direct.fill('', 13, 16);
  assert.equal(parseReport(readFields(direct.join('｜'))).activity.share_quotes[0].text, '闹钟响了才算结束吗？');
  direct.fill('', 4, 13);
  direct[7] = '请助手安排谁来洗碗';
  const memory = parseReport(readFields(direct.join('｜')));
  assert.equal(memory.story.persona, '');
  assert.deepEqual(memory.keywords, []);
  assert.equal(memory.activity.summary, undefined);
  direct[7] = '';
  assert.throws(() => parseReport(readFields(direct.join('｜'))), /具体使用习惯/);
});
