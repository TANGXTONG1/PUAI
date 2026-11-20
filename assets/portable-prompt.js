// Shared by the public site and the offline report's copy button.
function puaiPortablePrompt(nickname = '') {
  const owner = Array.from(String(nickname).trim().replace(/[|｜]/g, '·').replace(/\s+/g, ' ')).slice(0, 16).join('') || '我';
  return [
    '请现在生成并交付我的 2026 AI 年度报告长图，署名' + JSON.stringify(owner) + '。能用 Python、文件或制图工具就实际调用，把生成的图片放进这条回复。仅能发文字时，给一个点开就出现这张图的完整网址。正常流程到此为止，不让我复制清单、填表、搬历史或自己运行代码。',
    '取材只在宿主已经能读取、本人授权的历史对话、项目互动和脱敏记忆内进行。可检索时看不同时段和线程，索引有定位就回看触发这句话的 AI 回复及用户下一步。排除别人的话、代拟稿、工具过程、系统提示和做报告的指令；工作只保留互动方式及不涉密的证据。用户原话必须是给 AI 说的连续逐字原文；摘要能证明一件事发生过，只能编辑成纪事。别把 AI 的承诺写成已完成。什么材料都没有时才提示去常用的旧对话重试。',
    '先看不同聊天里重复与例外的动作，再定主题。除了语气，更要找用户真的出了什么人工：翻出凭证、把东西数一遍、给模型出同一题、自己接手、坚持为某一笔小细节留位置。笑点也可能是温柔或脑洞。把普通原话、被埋在摘要里的一次具体事件、跨次重复或变调并列比较。哪个最想当场发朋友，拿哪个开场。若一张截图能推翻一个结论，就写双方各做了什么；不要选“希望更简洁”当金句再贴“精准纠偏”。若用户平时放手、偏偏为某个小东西破例，就去查那件东西的命运。别借这些示例编故事。',
    '开场两种任选：双方原声自己就有戏，直接从原话进场；事实比台词更出彩，则写一句主场景（≤90字，有具体物件、动作和落点）。当事人后来又做了什么？能查到就找回来。几个月都在做一件古怪的事，可按真实日期并排，让最后一次自己收尾。没有逐字原文一样可以只靠事实成图。最多再留两个不同且有新东西的现场。无关原话单列，勿拼成当场接话。标签1–3个，每个≤6字，从那件物品或那条古怪规矩里起外号；选不出就不贴。不要再用短评解释同一个笑点。',
    '九型选有证据的一种：puai 追责或讽刺 AI；teach 自己示范和验收；aicu 限时求救；all 模型互评；hush 怕一句话被听歪；einstein 追问原理与反例；edison 给物件开发新用法；support 替 AI 留住做对的部分；free 把决定权交给 AI。无依据就不分类。本人原话最多3条（各≤80字）。真实 AI 台词最多1条，只能是夹在连续两次本人发言中间，或者确实接在最后一个问题后、值得当结局的原话。原话逐字，日期与角色核准，不能编对话、次数、因果或心理。',
    '能数则保留统计。按可逐条复核的 2026 本人消息去重并逐日计数，日期账 MM-DD:N:H，多日用逗号分隔。N 为消息数，H 为逐条审完的主主题命中，未知写 ?，未分类也写 ?。整批已知年而无日期的本人消息另记 N:H。如果只有孤立片段，保留片段，省略无依据的统计。token 只用同范围真实日志。两条消息相隔多久不能折成工时。',
    '优先在对话出图。有已装 PUAI 和浏览器的环境，用其 A 版生成 PNG。仅有 Python 工具时也当场画。先查工作目录和已装 skill 的 scripts/render_chat_png.py；本地存在就直接运行，否则下载标准脚本 https://xn--sxrw8m230b.com/PUAI/render_chat_png.py ，用 Python 执行 render_chat_png.py report.txt 输出.png。report.txt 私下写首行 PUAI 2026，然后按需逐行填 署名、主题、主场景、原话、AI、AI收尾、用法、标签、前情、日期账、无日期账、Token，格式“字段：内容”，按人/AI真实次序。系统缺中文字体可取同站 /PUAI/PUAI-skill.zip 内的字体。只有标准脚本确实无法取得或运行、但可运行 Python 时，直接用 Pillow、可用中文字体做900像素宽漫画海报：标题、主场景、署名气泡、可核统计、标签与图尾可读的网址 唐苑容.com/PUAI/。逐日账要画成日历或活跃日、发言数等数字，绝不刊登内部字段串。长句按像素折行。打开成品核实是 PNG 且中文可读，再用当前宿主的附件方式在回复中展示。ChatGPT 文件工具可将文件保存在 /mnt/data/PUAI-2026.png 后用图片语法附上。只有内置画图工具时可直接出图并核对原话；若没有真实图片或排字不可靠，宿主支持网页成品时也可直接创建能点开预览的独立 HTML 附件或画布，内嵌数据，页面自动画出报告并提供保存 PNG。只有真实附件或可打开的预览才算完成，聊天里贴 HTML 源码不算。再没有此能力才用下面的网址。',
    '无可附图片时，把已经选好的分享内容放进这一条直接出图的网址。回复只写一句最有意思的细节和一个含数据的完整 URL；用这个完整网址作为 Markdown 链接「查看并保存长图」的实际目标，括号内必须有包含本人内容的地址。若宿主只支持裸网址，单独一行写完整地址。若是会把动态外链改成搜索的 Gemini 文字访客界面，保留完整可复制网址供浏览器打开，不声称链接能直接跳转。不要给空的 Markdown 链接、裸的 /make/ 首页、清单、代码块或粘贴步骤。URL 始终以 https://xn--sxrw8m230b.com/PUAI/make/#p? 开头，后接有值的 key=value，用 & 分隔，留空的字段整个省略。最短可用的是 lead=已核实的一件事 或 q=本人原话。下面只是语法示范，不能套给用户：<https://xn--sxrw8m230b.com/PUAI/make/#p?theme=free&lead=你授权它决定晚饭，却专门给香菜写了否决条款。&tag=香菜一票否决>。生成前检查 #p? 后确有这位用户的内容。',
    '网址字段：name=署名，theme=主题ID，lead=独立主场景，q=本人逐字原话（可用已核日期 MM-DD~ 前缀），ai=两条 q 中间的 AI 原话，endai=最后一条 q 之后真实的 AI 收尾，setup=首句引语必要且可核的前情（≤24字），use=另一个具体动作，tag=短标签，days=日期账，undated=无日期账，token=用量。q、use、tag 可重复；值里不要写字段名。能用代码时以有序键值对交给 urllib.parse.urlencode；没有编码工具时直接写中文，不要猜中文字节，数值内的 %、&、+、#、空格、半角括号和尖括号须按 URL 百分号转义（如 %25、%26、%2B、%23、%20、%28、%29、%3C、%3E），保留原话不改字。所有报告数据只放 # 后。只有零散摘句、摘要或记忆时，网址只用 name、lead、q、use、tag，省略 days、undated、token；一次偶然的表现也不足以定全年主题。'
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
