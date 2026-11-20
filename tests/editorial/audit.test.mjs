import assert from 'node:assert/strict';
import test from 'node:test';
import { auditReport } from './audit.mjs';

const turns = [
  { id: 'u1', date: '2026-03-01', role: 'user', text: '换个例子。再试一次。' },
  { id: 'a1', date: '2026-03-01', role: 'assistant', text: '还是旧答案。' },
  { id: 'u2', date: '2026-03-02', role: 'user', text: '朋友说：“凑个热闹。”我想换题。' },
  { id: 'u3', date: '2026-03-02', role: 'user', text: '再试一次。' },
];
const source = { sessions: [{ turns }, { turns: [turns[0]] }] };
const key = { expected_theme: 'teach', borrowed_spans: { u2: ['凑个热闹。'] } };
const fields = ['v2', 'teach', '试读', '再出一道题。', '03-01:1:?,03-02:2:?', '', '',
  '', '', '', '03-01~换个例子。', '03-02~再试一次。', '', '换题', '', ''];

function verify(overrides) {
  const values = Object.assign([...fields], overrides);
  auditReport(source, key, values.join('｜'));
}

test('同一条消息的历史重放只计一次，同句独立发过两次可分别入选', () => {
  verify({});
  verify({ 10: '03-01~再试一次。' });
});

test('拒绝杜撰、助手台词、借来的原话、错误日期和同一消息拆成两句', () => {
  for (const quote of ['03-01~这句没说过。', '03-01~还是旧答案。', '03-02~凑个热闹。', '03-02~换个例子。']) {
    assert.throws(() => verify({ 10: quote }), /原话/);
  }
  // Keep the daily count plausible so that only the evidence-ownership check catches the reuse.
  assert.throws(() => verify({ 10: '03-02~我想', 11: '03-02~想换题。' }), /原话/);
});

test('不能串换日期账、编用量或给未分类材料强加九型', () => {
  assert.throws(() => verify({ 4: '03-01:2:?,03-02:1:?' }), /逐日/);
  assert.throws(() => verify({ 6: '1000' }), /token/);
  assert.throws(() => auditReport(source, { expected_theme: null }, fields.join('｜')), /主题/);
});

test('无日期摘要只作行为依据', () => {
  const memory = { sessions: [{ turns: [{ role: 'summary', id: 's1', date: null, text: '会给它换考题。' }] }] };
  const code = [...fields];
  code.fill('', 4, 13);
  code[7] = '给它换考题';
  auditReport(memory, key, code.join('｜'));
  code[5] = '2:?';
  assert.throws(() => auditReport(memory, key, code.join('｜')), /总数/);
});

test('AI 回复需要在同一会话中找到位置，不能从下文、其他会话或用户转述中借来', () => {
  verify({ 11: '03-02~我想换题。', 16: '', 17: '1~还是旧答案。' });
  for (const text of ['再试一次。', '我想换题。', '下次再说。']) {
    assert.throws(() => verify({ 11: '03-02~我想换题。', 16: '', 17: '1~' + text }), /AI 回复/);
  }
  assert.throws(() => verify({ 16: '', 17: '1~还是旧答案。' }), /AI 回复/);
  const differentThreads = { sessions: [{ turns: [turns[0], turns[1]] }, { turns: [turns[2], turns[3]] }] };
  const draft = [...fields, '', '1~还是旧答案。'];
  draft[11] = '03-02~我想换题。';
  assert.throws(() => auditReport(differentThreads, key, draft.join('｜')), /AI 回复/);
});
