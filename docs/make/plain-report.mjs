import { parseReport } from './report-code.mjs?v=dd2ced4faa';

const themeNames = new Map([
  ['ai的教育','teach'], ['ai特全体','all'], ['ai在心口难开','hush'],
  ['ai因斯坦','einstein'], ['ai迪生','edison'], ['ai的供养','support'],
  ['ai咋咋地','free'], ['未归类',''], ['无',''], ['ai相处报告','']
]);
const fieldPattern = /^(署名|主题|短评|用法|原话|AI|前情|标签|日期账|无日期账|Token)\s*[:：]\s*(.*)$/iu;
const repeated = new Set(['用法', '原话', '标签']);
const title = /^(?:#{1,6}\s+)?(?:\*\*|__|`)?PUAI\s*2026(?:\*\*|__|`)?$/iu;
const unknownStat = /^[（(]?(?:[-—–]+|N\/A|无|不详|未知|留空|未提供|无记录|暂无|未核[实准]?|未核[验对]|未统计|无法(?:逐条)?核[实准验对]|缺少数据)[）)]?$/iu;

function reportLine(line) {
  // Strip Markdown applied to the field label only. Keep the quote itself literal.
  const unlisted = line.replace(/^(?:[-*+]\s+|\d+[.)]\s+)/u, '');
  const unstyled = unlisted
    .replace(/^(\*\*|__|`)([^:：]+?)\1\s*([:：])/u, '$2$3')
    .replace(/^(\*\*|__|`)([^:：]+?[:：])\1/u, '$2');
  return fieldPattern.exec(unstyled);
}

function collectFields(lines, start) {
  const values = new Map();
  let reply = '';
  const body = lines.slice(start + 1).filter(Boolean);
  for (const [index, line] of body.entries()) {
    if (/^(?:```|~~~)|^(?:报告结束|结束|END|END PUAI)$/iu.test(line) || title.test(line)) break;
    const match = reportLine(line);
    if (!match || !match[2]) continue;
    const name = match[1].toLowerCase();
    if (['日期账','无日期账','token'].includes(name) && unknownStat.test(match[2].trim())) continue;
    if (name === 'ai') {
      const position = values.get('原话')?.length ?? 0;
      if (!reply && (position === 1 || position === 2) && publishableLine(match[2], 80)) {
        const before = reportLine(body[index - 1] ?? '');
        const after = reportLine(body[index + 1] ?? '');
        if (before?.[1] === '原话' && before[2] && after?.[1] === '原话' && after[2]) {
          const dateBefore = /^(\d\d-\d\d)~/u.exec(before[2])?.[1];
          const dateAfter = /^(\d\d-\d\d)~/u.exec(after[2])?.[1];
          if (!dateBefore || !dateAfter || dateBefore <= dateAfter) reply = position + '~' + match[2];
        }
      }
      continue;
    }
    const entries = values.get(name) ?? [];
    const parts = name === '标签' ? match[2].split('、').map(tag => tag.trim()).filter(Boolean) : [match[2]];
    entries.push(...parts);
    if (!repeated.has(name) && entries.length > 1) throw new Error('「' + match[1] + '」最多填写 1 项。');
    values.set(name, entries);
  }
  return { values, reply };
}

function publishableLine(value, limit) {
  return value && Array.from(value).length <= limit && !/[\u0000-\u001f\u007f]/u.test(value);
}

// Parse only a marked report block. A model's prose mentioning a quote is not a source.
export function readPlainFields(value) {
  const lines = value.split(/\r\n?|\n/u).map(line => line.trim().replace(/^(?:>\s*)+/u, ''));
  const start = lines.findIndex(line => title.test(line));
  if (start < 0) return null;
  if (value.length > 48000) throw new Error('报告文字太长，请只复制 PUAI 2026 这份报告。');
  const { values, reply } = collectFields(lines, start);
  const first = name => values.get(name)?.[0] ?? '';
  const three = name => Array.from({ length: 3 }, (_, index) => values.get(name)?.[index] ?? '');
  const themeText = first('主题').replace(/\s+/gu, '').toLowerCase();
  const theme = themeNames.get(themeText) ?? themeText;
  const setup = first('前情');
  const fields = ['v2', theme, first('署名'), first('短评'), first('日期账'), first('无日期账'), first('token'),
    ...three('用法'), ...three('原话'), ...three('标签'), first('原话') && publishableLine(setup, 24) ? setup : ''];
  if (reply) fields.push(reply);
  return fields;
}

export function parsePlainReport(value) {
  const fields = readPlainFields(value);
  return fields && parseReport(fields, { allowExcerptsWithoutLedger: true });
}
