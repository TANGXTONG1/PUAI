const themes = new Set(['puai', 'teach', 'aicu', 'all', 'hush', 'einstein', 'edison', 'support', 'free']);

export function readFields(value) {
  let line = value.trim();
  if (line.length > 48000) throw new Error('报告码太长了，请只粘贴 GPT 给出的那一行。');
  // Also accept a copied Markdown link or a fenced fallback line.
  line = line.replace(/^```[^\n]*\n([\s\S]*?)\n```$/, '$1').trim();
  const markdown = line.match(/^\[[^\]\n]*\]\(<?(https?:\/\/[^\n]+?)>?\)$/i);
  if (markdown) line = markdown[1];
  if (/^<https?:\/\//i.test(line) && line.endsWith('>')) line = line.slice(1, -1);
  const isUrl = /^https?:\/\//i.test(line);
  const isFragment = line.startsWith('#') || isUrl;
  if (isFragment) {
    const hash = line.indexOf('#');
    if (hash < 0) throw new Error('这个链接缺少报告码，请复制 GPT 给出的完整链接或代码块。');
    line = line.slice(hash + 1);
  }
  const fullWidth = /^v[12](?:｜|%ef%bd%9c)/i.test(line);
  const ascii = /^v[12](?:\||%7c)/i.test(line);
  if (!fullWidth && !ascii) throw new Error('请粘贴从 v2 或 v1 开始的报告码，或完整的成图链接。');
  let fields;
  if (fullWidth) {
    fields = line.split(isFragment ? /｜|%ef%bd%9c/i : '｜');
  } else {
    fields = line.split(isFragment && /^v[12]%7c/i.test(line) ? /%7c/i : '|');
  }
  fields[0] = fields[0].toLowerCase();
  const expected = fields[0] === 'v2' ? 16 : 8;
  if (fields.length !== expected) throw new Error('这版报告码需要 ' + expected + ' 个位置，请复制完整一行，包含留空的分隔符。');
  if (!isFragment) return fields;
  return fields.map(field => field.replace(/(?:%[0-9a-f]{2})+/gi, bytes => {
    try { return decodeURIComponent(bytes); }
    catch { throw new Error('链接中的部分文字没有解码成功，请粘贴 GPT 附的原始报告码。'); }
  }));
}

function checkText(value, name, limit, optional = false) {
  if (!value.trim()) {
    if (optional) return '';
    throw new Error('报告码缺少' + name + '，请补上后再生成。');
  }
  if (Array.from(value).length > limit || /[\u0000-\u001f\u007f]/u.test(value)) {
    throw new Error(name + '最多 ' + limit + ' 个字符，请使用一行文字。');
  }
  return value;
}

function wholeNumber(value, field) {
  if (!/^\d+$/.test(value) || !Number.isSafeInteger(Number(value))) {
    throw new Error(field + '需要填写可核对的非负整数。');
  }
  return Number(value);
}

// A missing review is distinct from a checked count of zero, at every level.
function readCounts(value) {
  const parts = value.split(':');
  if (parts.length !== 2) throw new Error('发言计数应写作「发言数:命中数」，未核对命中数可填 ?。');
  const count = wholeNumber(parts[0], '发言数');
  const hits = parts[1] === '?' ? null : wholeNumber(parts[1], '命中数');
  if (count === 0 || hits > count) throw new Error('有记录的发言数须大于零，命中数不能超过发言数。');
  return { count, hits };
}

function summarizeRows(rows) {
  const count = rows.reduce((total, row) => total + row.count, 0);
  if (!Number.isSafeInteger(count)) throw new Error('发言数超出报告码可用的整数范围。');
  const hits = rows.every(row => row.hits !== null) ? rows.reduce((total, row) => total + row.hits, 0) : null;
  return { count, hits };
}

function readDays(value) {
  if (!value.trim()) return [];
  const dates = new Set();
  return value.trim().split(/[,，]/).map(entry => {
    const match = /^(\d{2}-\d{2}):(.+)$/.exec(entry.trim());
    if (!match) throw new Error('逐日记录请写成 MM-DD:发言数:命中数，多天用逗号隔开。');
    const date = '2026-' + match[1];
    const time = Date.parse(date + 'T00:00:00Z');
    if (!Number.isFinite(time) || new Date(time).toISOString().slice(0, 10) !== date) {
      throw new Error('逐日记录含有无效的 2026 年日期。');
    }
    if (dates.has(date)) throw new Error('逐日记录中同一日期出现两次，请每个日期只统计一次。');
    dates.add(date);
    return { date, ...readCounts(match[2]) };
  }).sort((a, b) => a.date.localeCompare(b.date));
}

function readQuote(value, days) {
  const header = days && /^(\d{2}-\d{2})~/.exec(value);
  if (!header) return { text: checkText(value, '原话', 80) };
  const date = '2026-' + header[1];
  if (!days.some(day => day.date === date)) throw new Error('原话前标注的日期须出现在逐日记录里。');
  return { date, text: checkText(value.slice(header[0].length), '原话', 80) };
}

function richActivity(fields, theme) {
  const days = readDays(fields[4]);
  const undated = fields[5].trim() ? readCounts(fields[5].trim()) : null;
  const habits = fields.slice(7, 10).map(habit => checkText(habit.trim(), '日常习惯', 24, true)).filter(Boolean);
  const peak = days.reduce((best, day) => !best || day.count > best.count ? day : best, null);
  const totals = summarizeRows(undated ? [...days, undated] : days);
  const activity = {
    coverage: 'partial',
    daily_profile: {
      habits: [...new Set(habits)],
      active_days: days.length,
      dated_messages: totals.count - (undated?.count || 0),
      peak: peak ? { date: peak.date, count: peak.count } : null,
      undated_messages: undated?.count || 0
    },
    share_quotes: fields.slice(10, 13).filter(value => value.trim()).map(value => readQuote(value, days))
  };
  if (!totals.count && !habits.length) {
    throw new Error('请让 GPT 从可读的聊天或记忆里补上一条具体使用习惯；能核对发言时，也请填入计数。');
  }
  if (activity.share_quotes.length > totals.count) {
    throw new Error('每条原话要来自一条不同的已统计发言，请让 GPT 补全逐日或无日期计数。');
  }
  for (const { date, count } of days) {
    if (activity.share_quotes.filter(quote => quote.date === date).length > count) {
      throw new Error('同一天的原话超过该日发言数，请让 GPT 核对引语的日期和来源。');
    }
  }
  if (fields[6].trim()) {
    activity.token_usage = { total_tokens: wholeNumber(fields[6].trim(), 'token 用量'), coverage: 'partial', scope: '本次可核验的用量日志' };
  }
  if (!totals.count) return activity;

  const isRoast = theme === 'puai';
  const themeStats = { days: {}, months: {} };
  activity.summary = { messages: totals.count, active_days: days.length };
  if (totals.hits !== null) {
    if (isRoast) activity.summary.roast_messages = totals.hits;
    else themeStats.messages = totals.hits;
  }
  if (!isRoast) activity.theme_stats = themeStats;
  if (!days.length) return activity;
  if (days.every(day => day.hits !== null)) {
    activity.daily_profile.theme_days = days.filter(day => day.hits > 0).length;
  }

  const monthRows = new Map();
  activity.days = days.map(({ date, count, hits }) => {
    const month = date.slice(0, 7);
    if (!monthRows.has(month)) monthRows.set(month, []);
    monthRows.get(month).push({ count, hits });
    const day = { date, count };
    if (hits !== null) {
      if (isRoast) day.roast_count = hits;
      else themeStats.days[date] = hits;
    }
    return day;
  });
  const months = Array.from(monthRows, ([month, rows]) => {
    const { count, hits } = summarizeRows(rows);
    const row = { month, messages: count, active_days: rows.length };
    if (hits !== null) {
      if (isRoast) row.roast_messages = hits;
      else themeStats.months[month] = hits;
    }
    return row;
  });
  const first = days[0].date;
  const last = days[days.length - 1].date;
  activity.rhythm = { first_seen: first, last_seen: last, analysis_start: first, analysis_end: last, analysis_months: [...monthRows.keys()] };
  // Ranking affects only which three calendars fit on the poster.
  activity.months = months.sort((a, b) =>
    b.active_days - a.active_days || b.messages - a.messages || b.month.localeCompare(a.month)
  ).slice(0, 3).sort((a, b) => a.month.localeCompare(b.month));
  return activity;
}

export function parseReport(fields) {
  const [version, rawTheme, rawName, persona] = fields;
  const theme = rawTheme.trim().toLowerCase();
  if (!themes.has(theme)) throw new Error('报告码的主题 ID 无法识别，请使用 PUAI 的九种主题之一。');
  const name = checkText(rawName.trim(), '署名', 16, true) || '我';
  const isRich = version === 'v2';
  const keywords = fields.slice(isRich ? 13 : 6).map((tag, index) =>
    checkText(tag.trim(), '标签', 6, isRich || index > 0)
  ).filter(Boolean);
  if (!keywords.length) throw new Error('报告码中至少需要一个标签。');
  const activity = isRich ? richActivity(fields, theme) : {
    share_quotes: fields.slice(4, 6).filter(value => value.trim()).map(value => readQuote(value))
  };
  return {
    // Both URL formats belong to this edition, including when reopened later.
    year: 2026,
    mode: 'excerpt',
    theme,
    person: { name },
    story: { persona: checkText(persona.trim(), '人格短评', 60), scenes: [] },
    keywords,
    activity
  };
}
