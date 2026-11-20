// Shared by the public site and the offline report's copy button.
function puaiPortablePrompt(nickname = '') {
  const owner = Array.from(String(nickname).trim().replace(/[|｜]/g, '·').replace(/\s+/g, ' ')).slice(0, 16).join('') || '我';
  return [
    '生成我的 2026 AI 年度报告，署名' + JSON.stringify(owner) + '。我授权你在已有访问范围内主动查找本人历史聊天、项目互动、记忆和脱敏工作摘要。新对话也先检索；跨月份回看较早、中段、近期和发言密集的对话，别只搜吐槽或只用最近一条。有消息原文就打开；工作内容只提炼我怎么用 AI。排除这条口令、示例、他人发言、AI 回复、工具事件与历史重放。',
    '先读几段完整互动，看 AI 刚说了什么、我怎么接、后来又怎么做。从不同场合反复出现的动作里提炼 1–3 个基础特征（各≤6字），找反例核对，再定主主题。只有一次就只写这次。标签要能认出这个人，例如看他如何拒绝、如何验货；不要拿一句最狠的话倒推性格。给一句带动作的人格短评（≤60字），另挑有依据的日常用法（最多3条，各≤24字）。',
    '九型各有看点：puai 看我怎么损 AI 或向它追责；teach 看我给它立了什么规矩、如何验收；aicu 看火烧眉毛还坚持什么；all 看我怎么让几个模型互评；hush 看我心里想说什么、嘴上又要求多客气；einstein 看我抓住哪个矛盾一直追；edison 看我把一个念头拐到了哪儿；support 看我具体替 AI 留住了哪一点好；free 看我究竟把什么决定权交给它。普通修改不算骂，普通致谢不算应援。',
    '再拿这些特征回查相关对话，把不同回合的候选放在一起比。每句都要对得上一个特征：回到上下文，确认是本人怎样对 AI 说话，排除转述、代拟台词、广告段子和离题的狠话；再遮住上下文，陌生人单看这句也能看出动作、听出这人的口气，才进金句。首句放最值得截走的一条，可以好笑，也可以温柔得很具体。后一句要多露出一个动作、新的角度或有意思的回扣。普通的同意、催促、同义复述留作统计和画像依据。原话取0–3条（各≤80字），只有一条精彩就只放一条，全都平就留空。逐字保留本人一条消息里的连续原文和标点，留下铺垫和落点；整句涉及私人或工作细节就换，不能拼句或加工。',
    '必须先数后写。以实际能逐条核对的 2026 本人消息为范围，每条只计一次，同一原消息在多个来源出现只计一次。按同一时区把消息逐日合并，日期账格式 MM-DD:N:H，多日用英文逗号连接（格式示意 03-08:4:1,03-09:2:?，不用这组示意数）。N 是当天全部可核对的本人发言数，H 是其中符合主主题的条数；整组逐条复核后才写 H（可以为 0），未核全写 ?。可确定属于当年但无具体日期的其余原消息单列为 N:H。记忆和摘要只支撑习惯；不把片段、标签、选句数量当作发言数。token 仅填同范围真实用量日志核准的整数，没有就留空。',
    '先在对话里交付一小段能直接读的报告：写人格；写本次可数的发言总数（含无日期项）；有日期就写活跃日、峰值日和峰值条数；逐日都核完时加上其中有几天命中主题；整批都核完主题时写命中条数/发言总数及百分比；有 token 就写。再写日常用法、入选金句和标签。有依据的项目必须同时进入下方报告码。每句引语选自一条已入账的不同消息。有原文无日期也照数；只有行为摘要则写有依据的日常，数字和引语留空。至少有可数的发言或一个具体用法；所有来源都无具体行为才提示去常聊的旧对话或有历史的项目再发同一口令。无需用户粘贴、上传聊天或填问卷。',
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
