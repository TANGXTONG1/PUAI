// Shared by the public site and the offline report's copy button.
function puaiPortablePrompt(nickname = '') {
  const name = Array.from(String(nickname).trim().replace(/\s+/g, ' ')).slice(0, 16).join('');
  const placeholder = /^[「“"]?(?:[xｘ×]{3}|叉叉叉)[」”"]?$/iu.test(name);
  const signature = name && !placeholder ? '署名「' + name + '」' : '署名沿用我在聊天里用过的称呼';
  return '读下方 $puai，整理我的 2026 聊天，' + signature +
    '。只用官方模板直接在对话里显示 PNG，跑不了给我的预览链接，读不到请直说，别用 AI 绘图。\nhttps://raw.githubusercontent.com/TANGXTONG1/PUAI/main/SKILL.md?v=16';
}

function bindPuaiPromptCopy(button, fallback, status, nickname) {
  function clearFeedback() {
    status.textContent = '';
    fallback.hidden = true;
  }
  if (nickname) nickname.addEventListener('input', clearFeedback);
  button.addEventListener('click', async () => {
    const prompt = puaiPortablePrompt(nickname ? nickname.value : '');
    try {
      await navigator.clipboard.writeText(prompt);
      fallback.hidden = true;
      status.textContent = '已复制，粘贴到你的 Agent 并发送。';
    } catch {
      fallback.value = prompt;
      fallback.hidden = false;
      fallback.focus();
      fallback.select();
      fallback.setSelectionRange(0, prompt.length);
      status.textContent = '口令已选中，长按复制后发给你的 Agent。';
    }
  });
}
