import { readFields, parseReport } from './report-code.mjs?v=dd2ced4faa';

import { readPlainFields } from './plain-report.mjs?v=642b270c46';

const form = document.getElementById('form');
const input = document.getElementById('code');
const status = document.getElementById('status');
const result = document.getElementById('result');
const heading = document.getElementById('title');
const image = document.getElementById('preview');
const save = document.getElementById('save');
const recovery = document.getElementById('recovery');
const recover = document.getElementById('recover');
const retry = document.getElementById('retry');

const paste = document.getElementById('paste');
const partial = document.getElementById('partial');
const partialText = document.getElementById('partial-text');
const repair = document.getElementById('repair');
const repairText = document.getElementById('repair-text');
const repairPrompt = '请把刚才那份 PUAI 报告发成可复制的文字。首行单独写 PUAI 2026，下面把有依据的署名、主题、用法、原话、标签逐项分行写作“字段：内容”。能核准时补日期账或无日期账；仅有摘要就只写具体用法，只有本人逐字片段就写原话。无需我粘贴历史。';
let clipboardAttempt = 0;
let templateRequest;
let pending;
let retryRequest;

async function getTemplate() {
  if (!templateRequest) {
    templateRequest = fetch('./poster-frame.txt?v=2a842b3dbc', { credentials: 'omit', referrerPolicy: 'no-referrer' })
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
  if (!template.includes('__REPORT_JSON__')) {
    templateRequest = undefined;
    throw new Error('版式加载失败，请重试。');
  }
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
  heading.textContent = '我的年度报告';
  document.title = '生成我的 AI 年度相处报告 · PUAI';
}

function hideRecovery() {
  recovery.hidden = true;
  recover.setAttribute('aria-expanded', 'false');
  retryRequest = undefined;
}

// Old replies sometimes included a full link or a standalone backup line inside prose.
function legacySource(value) {
  const code = value.match(/^\s*(v[12][｜|][^\r\n]*)$/im);
  if (code) return code[1].trim();
  const url = value.match(/https?:\/\/[^\s<>()[\]]*#v[12](?:｜|\||%ef%bd%9c|%7c)[^\s<>)\]]*/iu);
  return url ? url[0] : '';
}

// A legacy response with a stripped link can still contain a specific incident.
function oldReplyFact(text) {
  if (!/\b2026\b/u.test(text) || !/查看并保存长图|打开我的报告/u.test(text)) return '';
  const match = /选(?:了|取了)你(质疑|追问|询问|比较|核对)[“「]([^”」\n]{1,80})[”」]的(?:现场|片段)/u.exec(text);
  return match ? match[1] + match[2] : '';
}

function resetPasteOptions() {
  partial.hidden = true;
  partialText.textContent = '';
  repair.hidden = true;
  repairText.hidden = true;
  clipboardAttempt++;
}

// Save only validated, public report fields in this navigation entry. Editorial
// text can be shortened by the renderer; its unpublished tail stays out of history.
function publicReceipt(fields, report) {
  const clean = fields.slice();
  clean[3] = report.story.persona;
  for (let i = 0; i < 3; i++) {
    clean[7 + i] = report.activity.daily_profile.habits[i] ?? '';
    clean[13 + i] = report.keywords[i] ?? '';
  }
  return clean;
}

async function generate(value, fromAddress = false, restored = null) {
  pending?.abort();
  const attempt = new AbortController();
  pending = attempt;
  clearResult();
  hideRecovery();
  resetPasteOptions();
  status.className = '';
  form.hidden = true;
  status.textContent = '正在生成长图…';
  let reportParsed = false;
  try {
    if (value.length > 48000) throw new Error('请只复制助手生成的这一份报告。');
    const receipt = restored || (!fromAddress && readPlainFields(value));
    let fields;
    if (receipt) {
      fields = receipt;
    } else {
      const embedded = fromAddress ? '' : legacySource(value);
      if (!fromAddress && !embedded) {
        const fact = oldReplyFact(value);
        if (fact) {
          partialText.textContent = fact;
          partial.hidden = false;
          repair.hidden = false;
          status.textContent = '旧链接缺少报告内容。可以只保存这一条用法。';
          return;
        }
      }
      fields = readFields(embedded || value);
    }
    const report = parseReport(fields, { allowExcerptsWithoutLedger: Boolean(receipt) });
    reportParsed = true;
    const { png, alt } = await renderPoster(report, attempt.signal);
    if (attempt.signal.aborted) return;
    image.alt = alt;
    image.src = png;
    if (!fromAddress) {
      try {
        if (receipt) {
          history.replaceState({ puaiReceipt: publicReceipt(fields, report) }, '', location.pathname + location.search);
        } else {
          history.replaceState(null, '', '#' + fields.map(encodeURIComponent).join('|'));
        }
      } catch {
        // Some in-app browsers restrict history updates.
      }
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
    if (restored && !reportParsed) {
      status.textContent = '';
      form.hidden = false;
      return;
    }
    if (fromAddress || reportParsed) {
      recovery.hidden = false;
      retry.hidden = !reportParsed;
      if (reportParsed) retryRequest = { value, fromAddress, restored };
    } else {
      form.hidden = false;
      repair.hidden = false;
    }
    status.className = 'error';
    status.textContent = reportParsed
      ? '长图暂时没加载出来，可以重试。'
      : fromAddress ? '这个链接里的报告内容有误或不完整。'
      : /查看并保存长图|打开我的报告/u.test(value) && !value.includes('PUAI 2026')
        ? '这条回复里没有可读取的报告正文。可以回到原聊天补全。' : error.message;
  }
}

function openFragment() {
  resetPasteOptions();
  if (location.hash.length > 1) {
    generate(location.hash, true);
  } else {
    const saved = history.state?.puaiReceipt;
    if (Array.isArray(saved) && [16, 17, 18].includes(saved.length) && saved[0] === 'v2'
        && saved.every(field => typeof field === 'string') && saved.join('').length <= 48000) {
      generate('', false, saved);
      return;
    }
    pending?.abort();
    clearResult();
    hideRecovery();
    status.textContent = '';
    status.className = '';
    form.hidden = false;
    input.value = '';
  }
}

recover.addEventListener('click', () => {
  // The user chose another source; a refreshed recovery form should stay blank.
  try { history.replaceState(null, '', location.pathname + location.search); } catch {}
  recovery.hidden = true;
  recover.setAttribute('aria-expanded', 'true');
  form.hidden = false;
  input.focus();
});
retry.addEventListener('click', () => {
  if (retryRequest) generate(retryRequest.value, retryRequest.fromAddress, retryRequest.restored);
});
paste.addEventListener('click', async () => {
  const attempt = ++clipboardAttempt;
  try {
    const text = await navigator.clipboard.readText();
    if (attempt !== clipboardAttempt) return;
    if (!text.trim()) throw new Error('empty clipboard');
    generate(text);
  } catch {
    if (attempt !== clipboardAttempt) return;
    status.className = '';
    status.textContent = '请长按输入框并选择粘贴，电脑上可直接粘贴。';
    input.focus();
  }
});

// OS paste is sufficient, including when the browser denies programmatic reads.
input.addEventListener('input', event => {
  clipboardAttempt++;
  if (event.inputType === 'insertFromPaste' && input.value.trim()) generate(input.value);
});
document.getElementById('use-partial').addEventListener('click', () => {
  if (partialText.textContent) generate('PUAI 2026\n用法：' + partialText.textContent);
});
document.getElementById('repair-copy').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(repairPrompt);
    status.className = '';
    status.textContent = '已复制。发到刚才生成报告的对话，再把回复粘贴回来。';
  } catch {
    repairText.value = repairPrompt;
    repairText.hidden = false;
    repairText.focus();
    repairText.select();
    status.textContent = '长按复制这段指令，发回刚才的聊天。';
  }
});
form.addEventListener('submit', event => {
  event.preventDefault();
  generate(input.value);
});
window.addEventListener('hashchange', openFragment);
openFragment();
