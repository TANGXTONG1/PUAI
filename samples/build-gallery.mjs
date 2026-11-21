// Run with node samples/build-gallery.mjs /path/to/output. Each HTML renders its own shareable PNG.
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { parsePlainReport } from '../docs/make/plain-report.mjs';

const out = process.argv[2];
if (!out) throw new Error('请指定样刊输出目录，例如 node samples/build-gallery.mjs /tmp/puai-gallery');
const output = resolve(out);
await mkdir(output, { recursive: true });
const here = new URL('./', import.meta.url);
const source = JSON.parse(await readFile(new URL('gallery.json', here), 'utf8'));
const frame = await readFile(new URL('../docs/make/poster-frame.txt', here), 'utf8');

function receiptFor(theme, demo) {
  const { nickname, messages, quotes, tags } = demo;
  const totals = new Map();
  for (const row of Object.values(messages)) {
    const counts = totals.get(row.date) || { count: 0, hits: 0 };
    counts.count++;
    if (row.matchesTheme) counts.hits++;
    totals.set(row.date, counts);
  }
  const lines = [`PUAI ${source.year}`, '署名：' + nickname, '主题：' + theme, '范围：history'];
  for (const { message, excerpt, highlight } of quotes) {
    const row = messages[message];
    const quote = excerpt ?? row.text;
    if (!row.text.includes(quote) || !quote.includes(highlight)) {
      throw new Error(`${theme}/${message} 的引语或强调与原文不符`);
    }
    lines.push(`原话：${row.date}~${quote}`, '划线：' + highlight);
  }
  const ledger = [...totals].sort(([a], [b]) => a.localeCompare(b))
    .map(([date, { count, hits }]) => `${date}:${count}:${hits}`);
  lines.push('标签：' + tags.join('、'), '日期账：' + ledger.join(','));
  return lines.join('\n') + '\n';
}

async function publish(theme, receipt, mode) {
  const report = parsePlainReport(receipt);
  if (report?.theme !== theme) throw new Error('类型与报告单不符：' + theme);
  report.mode = mode;
  const json = JSON.stringify(report).replaceAll('<', '\\u003c');
  const html = frame.replace('__REPORT_JSON__', () => json);
  await Promise.all([
    writeFile(join(output, theme + '.txt'), receipt),
    writeFile(join(output, theme + '.json'), JSON.stringify(report, null, 2) + '\n'),
    writeFile(join(output, theme + '.html'), html),
  ]);
}
for (const [theme, demo] of Object.entries(source.editions)) {
  await publish(theme, receiptFor(theme, demo), 'demo');
}
const personal = await readFile(new URL('tang.txt', here), 'utf8');
await publish('puai', personal, 'excerpt');
