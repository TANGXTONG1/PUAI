import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { parseReport, readFields } from '../../docs/make/report-code.mjs';

function quoteMatches(turn, quote, borrowedSpans) {
  if (turn.date !== (quote.date ?? null)) return false;
  let ownText = [turn.text];
  for (const borrowed of borrowedSpans[turn.id] ?? []) {
    ownText = ownText.flatMap(part => part.split(borrowed));
  }
  return ownText.some(part => part.includes(quote.text));
}

// Two short excerpts can each match multiple messages. Try all distinct assignments
// before rejecting an otherwise valid set of at most three quote bubbles.
function hasDistinctSources(matches, used = new Set(), index = 0) {
  if (index === matches.length) return true;
  for (const turn of matches[index]) {
    if (used.has(turn.id)) continue;
    used.add(turn.id);
    if (hasDistinctSources(matches, used, index + 1)) return true;
    used.delete(turn.id);
  }
  return false;
}

export function auditReport(context, key, code) {
  const fields = readFields(code);
  assert.equal(fields[0], 'v2', '测试使用 v2 报告码');
  const { activity, theme } = parseReport(fields);
  assert.equal(theme, key.expected_theme, '主题与材料不符');
  assert.equal(activity.token_usage, undefined, '材料没有 token 用量记录');

  const users = new Map();
  for (const session of context.sessions) {
    for (const turn of session.turns) {
      if (turn.role === 'user') users.set(turn.id, turn);
    }
  }
  const turns = [...users.values()];
  assert.equal(activity.summary?.messages ?? 0, turns.length, '本人消息总数不符');
  const dated = {}, actual = {};
  let undated = 0;
  for (const turn of turns) {
    if (turn.date) dated[turn.date] = (dated[turn.date] ?? 0) + 1;
    else undated++;
  }
  for (const day of activity.days ?? []) actual[day.date] = day.count;
  assert.deepEqual(actual, dated, '逐日发言数与来源不符');
  assert.equal(activity.daily_profile.undated_messages, undated, '无日期发言数不符');
  const matches = activity.share_quotes.map(quote =>
    turns.filter(turn => quoteMatches(turn, quote, key.borrowed_spans ?? {})));
  assert.ok(hasDistinctSources(matches), '每条原话须能匹配不同的本人消息、连续原文和对应日期');
}

function readJSON(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

function main(path) {
  if (!path) throw new Error('用法：node tests/editorial/audit.mjs <按匿名 ID 保存的报告码.json>');
  const corpus = readJSON(new URL('./synthetic-contexts.json', import.meta.url));
  const keys = readJSON(new URL('./review-key.json', import.meta.url));
  const codes = readJSON(path);
  assert.deepEqual(Object.keys(codes).sort(), Object.keys(corpus).sort(), '报告码的 ID 必须覆盖全部样本');
  const failures = [];
  for (const [id, context] of Object.entries(corpus)) {
    try {
      auditReport(context, keys[id], codes[id]);
    } catch (error) {
      failures.push(id + ' — ' + error.message);
    }
  }
  if (failures.length) throw new Error(failures.join('\n'));
  console.log(Object.keys(corpus).length + ' 组样本通过主题、计数与引语来源检查。');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    main(process.argv[2]);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
