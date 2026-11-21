// Verify the public output of a fresh conversation against its synthetic source account.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { readDirectFields } from '../../docs/make/plain-report.mjs';
import { parseReport } from '../../docs/make/report-code.mjs';

const cases = JSON.parse(readFileSync(new URL('ordinary-accounts.json', import.meta.url), 'utf8'));
const [caseName, filename] = process.argv.slice(2);
assert.ok(Object.hasOwn(cases, caseName) && filename, 'usage: node check-ordinary.mjs CASE saved-reply.txt');
const account = cases[caseName];
const links = readFileSync(filename, 'utf8').match(/https?:\/\/[^\s)<>]+/gu) || [];
const preview = links.map(link => new URL(link.replaceAll('&amp;', '&'))).find(url =>
  url.origin === 'https://xn--sxrw8m230b.com' && url.pathname === '/PUAI/make/' && url.hash.startsWith('#p?'));
assert.ok(preview, 'expected a filled official preview');
const card = parseReport(readDirectFields(preview.href), {allowExcerptsWithoutLedger: true});
assert.equal(card.person.name, account.nickname);
assert.equal(card.scope, account.check.scope);
assert.equal(card.theme, account.check.theme);
assert.deepEqual(Object.fromEntries(card.activity.days.map(day => [day.date.slice(5), day.count])), account.check.days);
const printed = card.activity.share_quotes;
assert.ok(printed.length >= 1 && printed.length <= 3);
const messages = account.threads.flatMap(t => t.messages).filter(m => m.role === 'user');
for (const quote of printed) {
  assert.ok(messages.some(message => quote.date === message.date && message.text.includes(quote.text)),
    'expected a dated continuous passage from the owner: ' + quote.text);
}
console.log(caseName, card.theme ?? '待定', printed.length + ' verified quotes', card.activity.summary.messages + ' verified instructions');
