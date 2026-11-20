import { parseReport } from './report-code.mjs?v=ffbab029bc';

const themeNames = new Map([
  ['ai的教育','teach'], ['ai特全体','all'], ['ai在心口难开','hush'],
  ['ai因斯坦','einstein'], ['爱因斯坦','einstein'], ['ai迪生','edison'], ['ai的供养','support'],
  ['ai咋咋地','free'], ['未归类',''], ['待定',''], ['无',''], ['ai相处报告','']
]);
const fieldPattern = /^(署名|主题|(?:人物|人格|年度|本次)类型|范围|短评|主场景|用法|原话|AI|AI收尾|前情|标签|发言日期|日期账|无日期账|Token)\s*[:：]\s*(.*)$/iu;
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
  let ending;
  const body = lines.slice(start + 1).filter(Boolean);
  for (const [index, line] of body.entries()) {
    if (/^(?:```|~~~)|^(?:报告结束|结束|END|END PUAI)$/iu.test(line) || title.test(line)) break;
    const match = reportLine(line);
    if (!match || !match[2]) continue;
    const name = match[1].endsWith('类型') ? '主题' : match[1].toLowerCase();
    if (['发言日期','日期账','无日期账','token'].includes(name) && unknownStat.test(match[2].trim())) continue;
    if (name === 'ai收尾') {
      const after = values.get('原话')?.length ?? 0;
      if (!ending && after > 0 && after <= 6 && publishableLine(match[2], 80)) {
        ending = { after, text: match[2] };
      }
      continue;
    }
    if (name === 'ai') {
      const position = values.get('原话')?.length ?? 0;
      if (!reply && position > 0 && position < 6 && publishableLine(match[2], 80)) {
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
  const finalReply = !reply && ending && ending.after === values.get('原话').length ? ending.text : '';
  return { values, reply, finalReply };
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
  const { values, reply, finalReply } = collectFields(lines, start);
  const first = name => values.get(name)?.[0] ?? '';
  const three = (name, offset = 0) => Array.from({ length: 3 }, (_, index) => values.get(name)?.[offset + index] ?? '');
  const themeText = first('主题').replace(/\s+/gu, '').toLowerCase();
  const theme = themeNames.get(themeText) ?? themeText;
  const setup = first('前情');
  // Keep the original v2 slot positions for saved receipts. Only named/plain
  // receipts use the optional tail (scope, quotes four to six and verified dates).
  const fields = ['v2', theme, first('署名'), first('短评'), first('日期账'), first('无日期账'), first('token'),
    ...three('用法'), ...three('原话'), ...three('标签'), first('原话') && publishableLine(setup, 24) ? setup : '',
    reply, first('主场景'), finalReply, first('范围'), ...three('原话', 3), first('发言日期')];
  while (fields.length > 17 && !fields.at(-1)) fields.pop();
  return fields;
}

export function parsePlainReport(value) {
  const fields = readPlainFields(value);
  return fields && parseReport(fields, { allowExcerptsWithoutLedger: true });
}

const directNames = new Map([
  ['name', '署名'], ['theme', '主题'], ['scope', '范围'], ['note', '短评'], ['lead', '主场景'], ['setup', '前情'],
  ['q', '原话'], ['ai', 'AI'], ['endai', 'AI收尾'], ['use', '用法'], ['tag', '标签'],
  ['days', '日期账'], ['dates', '发言日期'], ['undated', '无日期账'], ['token', 'Token']
]);

// These parameters live in the fragment, never the request query. Accept the
// browser hash and a copied full link. Ordering matters for the speaker turns.
export function readDirectFields(value) {
  let text = value.trim();
  const markdown = /^\[[^\]\n]*\]\(<?(https?:\/\/[^\n]+?)>?\)$/iu.exec(text);
  if (markdown) text = markdown[1];
  const prefix = /^(?:https?:\/\/[^#\s]+)?#p\?/iu.exec(text);
  if (!prefix) return null;
  if (text.length > 48000) throw new Error('报告链接过长。');
  const query = text.slice(prefix[0].length).replace(/&amp;(?=[a-z]+=)/giu, '&');
  const metadata = ['PUAI 2026'];
  const turns = [];
  for (const [key, content] of new URLSearchParams(query)) {
    const label = directNames.get(key.toLowerCase());
    if (!label || /[\u0000-\u001f\u007f]/u.test(content)) {
      throw new Error('报告链接含无法识别的字段或换行，请重新生成完整链接。');
    }
    const lines = ['原话', 'AI', 'AI收尾'].includes(label) ? turns : metadata;
    lines.push(label + '：' + content);
  }
  return readPlainFields(metadata.concat(turns).join('\n'));
}
