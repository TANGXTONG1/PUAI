// Shared by the public site and the offline report's copy button.
function puaiPortablePrompt(nickname = '') {
  const owner = String(nickname).trim() || '我';
  return [
    '请直接用这段聊天做我的 PUAI 年度报告。内容用你当前能看到的我的发言，或我贴出的本人聊天记录。按下面的格式给我成图链接即可，无需联网、安装 skill 或运行代码。',
    '先从实际用法总结一句有梗的人格，再精选 1–2 条我的连续原话，逐字保留；补 1–2 个短标签。排除这条口令、参考图、AI 的回复、转述和私人工作信息。看不到可用原话时，只请我贴几句；有材料就直接做。不要估算天数或 token。',
    '主题 ID 选最贴近的一种：puai 吐槽 AI，teach 教 AI 做事，aicu 紧急求救，all 多模型互评，hush 斟酌措辞，einstein 追问原理，edison 发散点子，support 鼓励 AI，free 放手让 AI 拍板。',
    '署名用' + JSON.stringify(owner) + '。人格≤60字，原话每条≤80字，标签每个≤6字。用以下模板，替换所有占位词；第二条原话、第二个标签可空，但保留分隔符：',
    '[打开我的报告](<https://xn--sxrw8m230b.com/PUAI/make/#v1｜主题ID｜署名｜人格｜原话一｜原话二｜标签一｜标签二>)',
    '链接一行写完。普通中英文直接保留；字段内的半角空格写 %20、% 写 %25、# 写 %23、( 和 ) 写 %28 和 %29、< 和 > 写 %3C 和 %3E。避免选含竖线或换行的片段。最后另给一个代码块，写一行从 v1 开始的备用报告码，字段保留原始文字、空格和标点，不做网址转义。附上[粘贴报告码出图](https://xn--sxrw8m230b.com/PUAI/make/)供链接打不开时使用。'
  ].join('\n');
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
      status.textContent = '已复制。粘贴到你平时聊天的对话里即可。';
    } catch {
      fallback.value = prompt;
      fallback.hidden = false;
      fallback.focus();
      fallback.select();
      fallback.setSelectionRange(0, prompt.length);
      status.textContent = '口令已选中，长按复制后发给 ChatGPT。';
    }
  });
}
