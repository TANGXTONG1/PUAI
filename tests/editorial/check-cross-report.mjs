/** Check one real text-only agent response against a synthetic multi-thread account. */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { readDirectFields } from '../../docs/make/plain-report.mjs';
import { parseReport } from '../../docs/make/report-code.mjs';

const cases = JSON.parse(readFileSync(new URL('cross-thread-fixtures.json', import.meta.url), 'utf8'));
const expected = {
  jury: {theme: 'all', eligible: ['v','w','x']},
  handover: {theme: 'free', eligible: ['f','g','h']},
  loud: {theme: 'einstein', eligible: ['s1','s2','s3','s4']},
  one_event: {theme: 'puai', eligible: ['k0','k1','k2','k3','o']},
};
const [id, responsePath] = process.argv.slice(2);
assert.ok(Object.hasOwn(expected, id) && responsePath, 'use: node check-cross-report.mjs CASE saved-response.md');
const response = readFileSync(responsePath, 'utf8');
const link = response.match(/https:\/\/[^\s)<>]*#p\?[^\s)<>]+/u)?.[0];
assert.ok(link, 'the response must include a real filled preview link');
const report = parseReport(readDirectFields(link), { allowExcerptsWithoutLedger: true });
const quotes = report.activity.share_quotes;
assert.equal(report.theme, expected[id].theme);
assert.ok(id === 'one_event' ? ['thread','fragments'].includes(report.scope) : report.scope === 'history');
assert.ok(quotes.length >= 2 && quotes.length <= 3);
const sources = new Set();
for (const quote of quotes) {
  const matches = expected[id].eligible.filter(key => {
    const [day, , turns] = cases[id].threads[key];
    return quote.date === '2026-' + day && turns.some(turn => turn.startsWith('u:') && turn.slice(2).includes(quote.text));
  });
  assert.equal(matches.length, 1, 'the quote must be an exact passage from the owner on this date in an eligible scene');
  sources.add(matches[0]);
}
if (id !== 'one_event') assert.ok(sources.size >= 2, 'cross-history evidence must represent two independent events here');
console.log(id, report.theme, report.scope, quotes.length + ' verified owner quotes');
