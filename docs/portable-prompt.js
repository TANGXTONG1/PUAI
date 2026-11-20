// Shared by the public site and the offline report's copy button.
function puaiPortablePrompt(nickname = '') {
  const name = Array.from(String(nickname).trim().replace(/\s+/g, ' ')).slice(0, 16).join('');
  const placeholder = /^[「“"]?(?:[xｘ×]{3}|叉叉叉)[」”"]?$/iu.test(name);
  const signature = name && !placeholder ? '署名「' + name + '」' : '署名沿用我在聊天里用过的称呼';
  return '调用 $puai，用我的聊天原话生成 2026 年度长图，直接在对话里显示，' + signature +
    '。未安装先读 skill，读不到就告诉我。\nhttps://raw.githubusercontent.com/TANGXTONG1/PUAI/refs/heads/main/SKILL.md?v=13';
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
