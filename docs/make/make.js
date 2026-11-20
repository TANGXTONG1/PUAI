import { readFields, parseReport } from './report-code.mjs?v=35ab1e6bb9';

const form = document.getElementById('form');
const input = document.getElementById('code');
const status = document.getElementById('status');
const result = document.getElementById('result');
const heading = document.getElementById('title');
const image = document.getElementById('preview');
const save = document.getElementById('save');

let templateRequest;
let pending;

async function getTemplate() {
  if (!templateRequest) {
    templateRequest = fetch('./poster-frame.txt?v=6ddd5043d4', { credentials: 'omit', referrerPolicy: 'no-referrer' })
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
    const fields = readFields(value);
    const report = parseReport(fields);
    const { png, alt } = await renderPoster(report, attempt.signal);
    if (attempt.signal.aborted) return;
    image.alt = alt;
    image.src = png;
    if (!fromAddress) {
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
