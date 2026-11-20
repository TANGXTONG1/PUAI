// Shared by the public site and the offline report's copy button.
function puaiPortablePrompt(nickname = '') {
  const owner = Array.from(String(nickname).trim().replace(/[|｜]/g, '·').replace(/\s+/g, ' ')).slice(0, 16).join('') || '我';
  return [
    '生成我的 2026 AI 年度报告，署名' + JSON.stringify(owner) + '。我授权你在已有访问范围内主动查找本人历史聊天、项目互动、记忆和脱敏工作摘要。新对话也先检索；跨月份回看较早、中段、近期和发言密集的对话，别只搜吐槽或只用最近一条。有消息原文就打开；工作内容只提炼我怎么用 AI。排除这条口令、示例、他人发言、AI 回复、工具事件与历史重放。',
    '先定人格和主题：puai 吐槽 AI、teach 教 AI 做事、aicu 紧急求救、all 多模型互评、hush 斟酌措辞、einstein 追问原理、edison 发散点子、support 鼓励 AI、free 让 AI 拍板。普通修改要求不能算骂。给一句带动作的人格短评（≤60字），挑出不同场合下 2–3 个有依据的日常用法（各≤24字）、2–3 句能独立成立的本人原话（各≤80字）及 1–3 个标签（各≤6字）。习惯写我具体干了什么；单次表现别写成“总是”。原话逐字保留连续片段，不能改写或从摘要复原。删去涉及人名、公司、项目、路径和业务的整句。',
    '必须先数后写。以实际能逐条核对的 2026 本人消息为范围，每条只计一次，同一原消息在多个来源出现只计一次。按同一时区把消息逐日合并，日期账格式 MM-DD:N:H，多日用英文逗号连接（格式示意 03-08:4:1,03-09:2:?，不用这组示意数）。N 是当天全部可核对的本人发言数，H 是其中符合主主题的条数；整组逐条复核后才写 H（可以为 0），未核全写 ?。可确定属于当年但无具体日期的其余原消息单列为 N:H。记忆和摘要只支撑习惯；不把片段、标签、选句数量当作发言数。token 仅填同范围真实用量日志核准的整数，没有就留空。',
    '先在对话里交付一小段能直接读的报告：写人格；写本次可数的发言总数（含无日期项）；有日期就写活跃日、峰值日和峰值条数；逐日都核完时加上其中有几天命中主题；整批都核完主题时写命中条数/发言总数及百分比；有 token 就写。再写日常用法、金句和标签。金句优先挑说法反转、态度最鲜明的。有依据的项目必须同时进入下方报告码。每句引语选自一条已入账的不同消息。有原文无日期也照数；只有行为摘要则写有依据的日常，数字和引语留空。至少有可数的发言或一个具体用法；所有来源都无具体行为才提示去常聊的旧对话或有历史的项目再发同一口令。无需用户粘贴、上传聊天或填问卷。',
    '按顺序填写以下 16 格；空字段保留分隔符，不写占位词。引语有可核日期且在日期账里时，以 MM-DD~ 开头，再接原文。实际输出一行可点击链接：',
    '[打开我的报告](<https://xn--sxrw8m230b.com/PUAI/make/#v2｜主题ID｜署名｜人格｜日期账｜无日期账｜token｜习惯一｜习惯二｜习惯三｜引语一｜引语二｜引语三｜标签一｜标签二｜标签三>)',
    '普通中英文直接保留；链接字段内半角空格、%、#、(、)、<、> 分别写 %20、%25、%23、%28、%29、%3C、%3E。字段避开竖线和换行。最后给一个代码块，附同内容从 v2 开始的单行备用报告码，保留原文空格和标点，不做网址转义。再附[粘贴报告码出图](https://xn--sxrw8m230b.com/PUAI/make/)。'
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
      status.textContent = '已复制。发给 ChatGPT，它会先找可用的历史和记忆。';
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
