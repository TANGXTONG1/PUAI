const form = document.getElementById('form');
const input = document.getElementById('code');
const status = document.getElementById('status');
const result = document.getElementById('result');
const heading = document.getElementById('title');
const image = document.getElementById('preview');
const save = document.getElementById('save');

const themes = new Set(['puai', 'teach', 'aicu', 'all', 'hush', 'einstein', 'edison', 'support', 'free']);
let templateRequest;
let pending;

function readFields(value) {
  let line = value.trim();
  if (line.length > 12000) throw new Error('报告码太长了，请只粘贴 GPT 给出的那一行。');
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
  const fullWidth = /^v1(?:｜|%ef%bd%9c)/i.test(line);
  const ascii = /^v1(?:\||%7c)/i.test(line);
  if (!fullWidth && !ascii) throw new Error('请粘贴从 v1 开始的报告码，或含有这段报告码的完整链接。');
  let fields;
  if (fullWidth) {
    fields = line.split(isFragment ? /｜|%ef%bd%9c/i : '｜');
  } else {
    fields = line.split(isFragment && /^v1%7c/i.test(line) ? /%7c/i : '|');
  }
  if (fields.length !== 8) throw new Error('报告码需要八个位置。请重新复制完整的一行，包含留空的分隔符。');
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

function parseReport(value) {
  const [, rawTheme, rawName, persona, firstQuote, secondQuote, firstTag, secondTag] = readFields(value);
  const theme = rawTheme.trim().toLowerCase();
  if (!themes.has(theme)) throw new Error('报告码的主题 ID 无法识别，请使用 PUAI 的九种主题之一。');
  const name = checkText(rawName.trim(), '署名', 16, true) || '我';
  const quotes = [checkText(firstQuote, '第一条原话', 80), checkText(secondQuote, '第二条原话', 80, true)];
  const keywords = [checkText(firstTag.trim(), '第一个标签', 6), checkText(secondTag.trim(), '第二个标签', 6, true)];
  return {
    // v1 links belong to the 2026 edition, including when reopened later.
    year: 2026,
    mode: 'excerpt',
    theme,
    person: { name },
    story: { persona: checkText(persona.trim(), '人格短评', 60), scenes: [] },
    keywords: keywords.filter(Boolean),
    activity: { share_quotes: quotes.filter(Boolean).map(text => ({ text })) }
  };
}

async function getTemplate() {
  if (!templateRequest) {
    templateRequest = fetch('./poster-frame.txt', { credentials: 'omit', referrerPolicy: 'no-referrer' })
      .then(response => {
        if (!response.ok) throw new Error('版式加载失败，请检查连接后重试。');
        return response.text();
      })
      .catch(error => { templateRequest = undefined; throw error; });
  }
  return templateRequest;
}

async function renderPoster(report, signal) {
  const template = await getTemplate();
  if (signal.aborted) throw new DOMException('Aborted', 'AbortError');
  if (!template.includes('__REPORT_JSON__')) throw new Error('版式加载失败，请刷新后重试。');
  // The report is data in a JSON script block, including when a quote contains HTML.
  const payload = JSON.stringify(report).replace(/[<>&\u2028\u2029]/g, char =>
    '\\u' + char.charCodeAt(0).toString(16).padStart(4, '0'));
  const frame = document.createElement('iframe');
  frame.hidden = true;
  frame.setAttribute('aria-hidden', 'true');
  frame.title = 'PUAI 海报画布';
  frame.srcdoc = template.replace('__REPORT_JSON__', () => payload);

  let observer, handleAbort, timeout;
  try {
    return await new Promise((resolve, reject) => {
      handleAbort = () => reject(new DOMException('Aborted', 'AbortError'));
      timeout = window.setTimeout(() => reject(new Error('海报还没有画好，请重试生成。')), 30000);
      signal.addEventListener('abort', handleAbort, { once: true });
      frame.addEventListener('load', () => {
        const preview = frame.contentDocument?.getElementById('preview');
        if (!preview) { reject(new Error('无法打开海报画布，请刷新重试。')); return; }
        function whenReady() {
          const png = preview.getAttribute('src');
          if (png?.startsWith('data:image/png;base64,')) resolve({ png, alt: preview.alt });
        }
        observer = new MutationObserver(whenReady);
        observer.observe(preview, { attributes: true, attributeFilter: ['src'] });
        whenReady();
      }, { once: true });
      document.body.appendChild(frame);
    });
  } finally {
    clearTimeout(timeout);
    observer?.disconnect();
    signal.removeEventListener('abort', handleAbort);
    frame.remove();
  }
}

function clearResult() {
  result.hidden = true;
  save.hidden = true;
  save.removeAttribute('href');
  image.removeAttribute('src');
  heading.textContent = '生成我的年度报告';
  document.title = '生成我的 AI 年度相处报告 · PUAI';
}

async function generate(value, fromAddress = false) {
  pending?.abort();
  const attempt = new AbortController();
  pending = attempt;
  clearResult();
  status.className = '';
  form.hidden = true;
  status.textContent = '正在生成长图…';
  try {
    const report = parseReport(value);
    const { png, alt } = await renderPoster(report, attempt.signal);
    if (attempt.signal.aborted) return;
    image.alt = alt;
    image.src = png;
    if (!fromAddress) {
      const [first, second] = report.activity.share_quotes;
      const fields = ['v1', report.theme, report.person.name, report.story.persona,
        first.text, second?.text || '', report.keywords[0], report.keywords[1] || ''];
      history.replaceState(null, '', '#' + fields.map(encodeURIComponent).join('|'));
    }
    save.download = report.person.name + '-2026-PUAI.png';
    save.href = png;
    save.hidden = false;
    result.hidden = false;
    heading.textContent = '你的年度报告';
    document.title = report.person.name + '的 AI 年度相处报告 · PUAI';
    status.textContent = '';
  } catch (error) {
    if (attempt.signal.aborted) return;
    form.hidden = false;
    if (value.startsWith('#')) input.value = location.href;
    status.className = 'error';
    status.textContent = error.message || '生成失败，请把报告码重新粘贴一次。';
  }
}

function openFragment() {
  if (location.hash.length > 1) {
    generate(location.hash, true);
  } else {
    pending?.abort();
    clearResult();
    status.textContent = '';
    form.hidden = false;
  }
}

form.addEventListener('submit', event => {
  event.preventDefault();
  generate(input.value);
});
window.addEventListener('hashchange', openFragment);
openFragment();
