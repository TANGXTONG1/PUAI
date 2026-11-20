---
name: puai
description: 用已授权的本人聊天生成 PUAI 年度报告长图。适用于“用 PUAI 翻我的聊天”“也给我做一张”、收到 PUAI 图想找同款口令，或要求从真实 AI 对话里找金句、发言日历和相处特征。
---

# PUAI 年度报告

交付一张能在手机里读的官方漫画 A 版。调用者只需提供署名（可选）。本地从本 skill 目录取程序和模板，在线读到本文的助手按下文的云端方式使用同一项目。参考图上的人、统计和台词属于原作者。

图尾只放二维码，旁边写「扫码获取口令，发给自己的 Agent 总结出图。」收到用户的生成口令，或用户明确要用自己的聊天生成时，直接按下面步骤出图。

按已确认的漫画 A 版排版。标题先写年份和已判类型，例如「2026 AI因斯坦 报告」。单场或片段材料另在题下注明范围。标题后先放最有辨识度的本人原话贴纸，接发言用量、已核占比和日历，再收个性标签。必要的前情只占一行。能定位包袱时，在该句后加「划线：原句里的连续短语」（预览参数 mark），核到同话多次重复才加「复读：实际次数」（repeat）。

每张成图都在署名旁标人物类型，页尾另放个性标签；「AI因斯坦」是类型，「车厘子精算师」是个性标签。每张图都留日历。**先取日期，再选原话**：打开原线程时一并读取本人消息的发送时间，按用户时区记到私有账。收到「补日期」时，沿用上一张图的署名和逐字原话，以原句去已授权的本人聊天里回查发送时间，并盘点同一范围可计数的其他发言，再出图。

在 ChatGPT 里收到口令，先取材，再实际调用当前对话的数据分析 / Python 工具显示成图。若只读到了本页，直接在工具内执行[本页离线对话画布](#离线对话画布)；也可让当前网页阅读工具读取[完整 A 版单文件](https://xn--sxrw8m230b.com/PUAI/notebook_card.py)。代码和数据在当前对话结合。

## 从聊天里找当事人的话

1. **认人。** 本次填了具体署名就照写。明确要求匿名或署「我」时用「我」，从公开内容和链接里一起排除旧称呼。空白、未替换的 XXX（含大小写和全角）都走自动署名：取材时顺手找本人反复使用的自称、认可的昵称或对称呼问题的回答，沿用最近的分享昵称。发现具体名字线索再回查出处，无需逐个搜索称呼的同义词。仅凭第三方姓名、样图、邮箱或账号还认不出来，就署「我」。所有出图路径使用同一个选好的称呼。生成口令与署名设置从选句和统计里排除。
2. **先盘点能读到的历史。** 先做下面的取材步骤，再决定出年度图还是单场精选。收到口令的线程通常只有一条生成指令，本身不算一个现场。

   - **有历史工具的客户端。** 实际调用已授权的个人历史目录、搜索和原线程读取工具。按目标年翻目录并跟随分页，先看早期、活跃期和近期的不同话题。把可见记忆、聊天标题和原文里的线索分开记：从本人的一个具体物件、惯用词或未完的决定出发，回到个人历史找它第一次出现和后来怎样了。只命中同一线程，换成当事人自己的另一种说法，再换时间或话题。另打开一批与这条记忆无关的线程，留意普通标题下突然好笑的一次追问、算账或改口。没有目录就用现有线索分开搜索，没有搜索工具就翻可读记录。有未读命中或下一页时先打开。只剩一段记忆时，查一个辨识度高的词，再试另一条独立线索或一次换词。两轮都找不到新线程且没有其他可读来源，就用已核材料收稿；避免拿「我」「你」「的」逐字扫库。记忆可以指路，逐字原话和日期要回原消息取。普通网页搜索不用于检索个人历史。
   - **本地有历史文件。** 对每个获准且有原记录的来源分别建私有索引：`python3 scripts/collect_history.py --client codex --year 2026 --timezone Asia/Shanghai --output CODEX.jsonl > CODEX-inventory.json`（替换为本人时区）。Claude 用 `--client claude`，ChatGPT 已有导出用 `--client chatgpt --export FILE`。项目 MEMORY.md、客户端的个人 / 项目记忆可以指向漏掉的事；记忆和会话标题只当线索。不同客户端可能转存了同一场对话，要回到最早可核的原文。Claude 仅剩输入日志时保留本人写下的内容与日期，标作输入片段，不能补出助手的回答或完整发言频率。遇到多账号先查私有盘点里的 owner_groups，按已核准的本人账号分区；旧记录没有账号元数据时单列。本人账号已知时运行 `python3 scripts/collect_history.py --scope-index CODEX.jsonl --inventory CODEX-inventory.json --owner-session SESSION --output OWNER.jsonl > OWNER-inventory.json`；也可以用 `--owner-group GROUP` 显式选择。后续浏览、原文比对和日历都用这一份分区索引。旧索引没有分区或家族字段而原记录还在时先重新盘点。
   - **先铺开，再精读。** 用 `python3 scripts/browse_history.py --index CODEX.jsonl --overview --output PAGE.json` 翻会话概览，跟随 `next_page` 到底。给每个有记录的月份和会话留位置；概览是挑候选的入口。再用同一程序去掉 `--overview` 翻本人发言，或加可重复的 `--term` 搜线索，跨不同事情找用户接着说的第二句。要求完整回顾、候选过于集中或换了说法就搜不到时，用 `--full-text --page-chars 6000` 把能读的本人发言分段翻完；可加 `--month YYYY-MM` 分批做。按字符偏移续读长消息的后半段，尤其留意用户在粘贴材料之后亲自补的要求。概览或搜索到末页不会自动读完全文。记录哪些原线程拿不到。云端有目录则同样列完分页，再按原线程精读；只有搜索或记忆时明确本次能核到哪里。
   - **把几个现场放在一起读。** 本地可用 `python3 scripts/compare_scenes.py --index CODEX.jsonl --ids ID1 ID2 ID3 --output CHECKED.json`，多来源可再加 `--index`。它按原消息回查本人原句、日期和前后回合，私下并排。读完候选自己的整条原话（user_text），以及助手回完之后本人怎样接；“做完了吗”可能只是询问进度，下一句才交代谁来测试。单条也可用 `read_context.py --index CODEX.jsonl --id ID --source SOURCE --output WINDOW.json`。云端工具按同样方式打开几段原线程。可在线取[盘点](https://xn--sxrw8m230b.com/PUAI/collect_history.py)、[翻阅](https://xn--sxrw8m230b.com/PUAI/browse_history.py)、[回查](https://xn--sxrw8m230b.com/PUAI/read_context.py)和[并排比对](https://xn--sxrw8m230b.com/PUAI/compare_scenes.py)脚本。索引和比对结果留在当前环境。
3. **用独立的事情定类型。** 给每件事各留一行私有笔记：「AI 刚做了什么 → 本人怎样接招 → 本人下一步做了什么」，附原文位置。旧事续聊、分支回放和把上一句粘去做贴纸，合到同一行。先在不同事情中找反复出现的动作，选一个最可能的类型，再去一段尚未参与判断的对话，找可能推翻它的证据。比如一句「你自己来」可以是把选择权交给 AI，也可以是要求 AI 亲自验证；看前面交出的是决定还是测试，后面谁验收。支持和相反的例子都算，把结论限定到实际能重复的那部分。只有一种解释在独立的事情上反复成立，才定年度类型；同一件事跨了好几个窗口，标为本次精选。有多件事但看不出主型，保留真实覆盖、日历与原话，类型待定。已读多个原线程、覆盖多件独立事情的阶段回顾用 `scope=history`，在图外说明日期区间。读不全整年、没有 token 日志、只裁两句上图，都不单独构成 `fragments` 的理由。是否能逐日计数看消息账是否完整。若两三型都说得通，把各自有明确行为的独立事情并排计一遍，一件事在同一型最多算一次，普通改稿和催进度都不能自动算作吐槽。两个类型证据相当时，有本人具体调侃的 PUAI 优先；优先选它不等于它出现最多。
4. **选原话。** 在私有候选旁记原消息位置、日期、说话人和上下句。摘候选时多看用户听完 AI 后说的下一句：有没有顺着它的逻辑反问、给一个离谱的例外，或者隔了几天回来把账结了？试着盖住类型名和短评，让不认识这人的读者也能听出他哪里较真、哪里心软、哪里突然变脸。具体人名和项目细节遮不掉，或全靠解释才能成立，就从另一事件找一句。普通工作说明和术语长段留在私有材料。新报告默认上 **两句**。跨对话回顾先试两件独立事情的两句话：在另一种生活或工作情境里，这个人有没有做出同一种让朋友一眼认得的反应？把两句互换顺序，各自仍应听得懂。最出彩的一句开场。两句试排后，只读将上图的字：读者能说清第二句里的人或东西怎么冒出来了吗？断在中间时，优先换成同一现场里自带起因和落点的两句；也可用一行已核事实补上缺的一步。只有一句值得转发就只选一句。第三句只在带来翻转或省去它就断掉时上图，新图最多三句。检索范围和发言账照常覆盖全部已核记录。见[选材参考](references/scene-selection.md)。
5. **付印。** 每句最多 80 字，保留原文、空格和标点。摘短只能取完整保留原意的连续片段。两条真实独立的发言各标自己的日期，避免剪成同一场对话。排除代拟稿、他人引语、系统提示、报告制作指令和工作机密。宿主问卷（本地标 `input_method=question_form`）可以核对本人选了什么；只有确认系本人输入的自由表述，才采作金句。粘贴材料很长时读到最后，分清被转贴的文字和本人在末尾补的要求。优先让原话直接开场，默认省略主场景、导语和短评。确实差半步才听得懂时，补一行可核实的事实前情（最多 24 字）。只有脱敏摘要时，用一个可核的具体动作出短卡。

先根据对话选定九型，把类型 ID 写入主题字段。整张报告固定使用该人格的配色，范围、署名和用户自定义的短标签都不改变这套颜色。尾部另可放 0–3 个短标签，每个最多六字。标签可借用原话里的物件或算账方式，「哪个动作只有在这张图里才说得通」是取舍标准。「善于提问」「当场纠偏」这类能移到别张图上的话直接删去。AI 的真实原话最多一条，仅在同一原线程里夹在两条用户发言之间，或确实紧接最后一问、能当落点时入选，另标「AI」。互不相干的问答分别呈现。没有任何具体互动材料时，提示到日常使用的旧对话发同一句口令；无需用户粘贴历史。

| 人格类型 | 行为依据 | 重点贴纸 / 署名签 |
|---|---|---|
| `puai` PUAI | 反复向 AI 讨债、反问、揶揄，或拿它前面的承诺当场对质 | 钴蓝 / 荧光黄 |
| `teach` AI的教育 | 亲自示范、出考题、教它怎么验收 | 翡翠绿 / 嫩绿 |
| `aicu` AICU | 真有时限的求救，当时决定优先救哪件事 | 亮橙 / 雾蓝灰 |
| `all` AI特全体 | 请几个模型互评、仲裁同一题 | 紫罗兰 / 薄荷绿 |
| `hush` AI在心口难开 | 为一句话怎么被听懂反复斟酌 | 珊瑚粉 / 淡紫 |
| `einstein` AI因斯坦 | 追问原理、提出具体反例 | 青蓝 / 淡蓝紫 |
| `edison` AI迪生 | 给同一个物件找出意外的新用途 | 金黄 / 深紫 |
| `support` AI的供养 | 替 AI 留下具体做对的那一步 | 玫粉 / 莓红 |
| `free` AI咋咋地 | 把一个真实决定交出去，或只保留一个例外 | 酸橙绿 / 薄荷青 |

归类看动作：谈论文的人也可能一直在教 AI 怎么做；在水果摊问出一个能推翻答案的反例，也可能是 AI因斯坦。定年度类型时，私下各引一条来自两件独立事情的依据，确认两个回合里本人都做过这个动作。同一件事隔月回来讲结局，很适合排成两句，只算一次类型依据。已核多个线程但类型依据仍不足时，保留日期、原话和真实覆盖范围，年度类型写「待定」。九型及其显示名固定。重排自己的既有报告，沿用原报告明确标出的类型；用户指定重判时再按原文重选。别把别人的样图类型移到新用户身上。

## 数字跟着证据走

**单独盘点日期。** 选好两句后，日期账仍要覆盖能完整读取的范围。按目标年翻完获准目录的各页，再翻各线程的消息分页，包括没有入选金句的日常对话。目录按更新时间排序时，跨年更新的旧线程也可能含目标年的发言。工具只给搜索结果时，打开原线程；正文不带日期时，拿可核的本人消息 ID 批量查发送元数据。时区取用户已知时区，工具直接提供本人当地发送日则照录；确实未知而需换算时按 UTC 并在图外标明。线程更新时间、助手回复时间、截图时钟和正文里的日期只作查找线索。

私下记清哪些线程已翻到底、哪些只是搜索片段。来源有读取上限时，先做完一个可说明的范围，并保留其他已核发言日。云端 Python 可用[日期清单合账](references/report-schema.md#原线程的日期清单)对本人消息 ID 去重、换算日期，输入只需元数据。没有 Python 时按同一口径直接汇总。

| 日期证据 | 发言日历怎样上图 |
|---|---|
| 完整翻完一批线程，逐条可核发言日（一个完整线程也行） | 按消息 ID 去重，排除 AI、工具、重放、本次报告指令及署名等设置。对这一批逐日计数，展示活跃日、单日峰值和月历。主题命中未审完仍然填 `days=MM-DD:N:?`（清单「日期账」）。从完整本地索引可直接运行 `python3 scripts/collect_history.py --calendar-from PRIVATE.jsonl --inventory INVENTORY.json --exclude-ids EXCLUSIONS.json`；排除清单是核过的 ID 数组，无需排除时为 `[]`。将输出的非空 `days`、`dates` 分别交给渲染器；清单对应「日期账」「发言日期」。 |
| 只有抽样原话、片段，或一段对话仍有本人发言缺少时间 | 所有能对应到具体原话的日期写成 `q=MM-DD~逐字原话`。还有能证明本人发过言的日期，用 `dates=MM-DD,MM-DD`（清单「发言日期」）保留下来。按不同日期去重，在「片段日期」里标记；未入选为金句的真实发言日期也有效。与部分日期账并存时，两组分别展示，保留原统计分母。 |
| 回查后确实只有无日期摘句或摘要 | 保留原话，日历栏标明这批材料未附日期。已核准年份与条数的无日期账可另填 `undated`。有日期的旧消息和可读文件仍应先查。 |

混合来源的频率只描述完整读到的线程。在图外用半句交代统计范围；当年只有抽样时，只点亮真实发言日，不报峰值或占比。可计数时，选展最多三个活跃月，日历选展不截断整批统计；同一批的主题占比需要逐条核定，PUAI 每条至多算一次。Token 仅用同范围去重日志。数字和私有证据见[报告格式](references/report-schema.md)。

## 用现成模板出图

三种输入都带上刚核对的取材范围：私有 JSON 根字段 `scope`，中文清单 `范围：history/thread/fragments`（三选一），网页同名参数 `scope`。把同一个类型 ID 写入 JSON 的根字段 `theme`、中文报告单的「主题」、预览链接的 `theme=`。确无依据时 JSON 用 null，报告单与链接省略主题，模板显示「待定」。按宿主能力选择以下路径。用 PUAI 随包模板、官方单文件程序、本页内置的离线对话画布或官方网页预览生成报告。不要自写海报、叫图片模型重新画、用参考样张顶替，或把程序输出的路径当成已经显示的图片。

- **已装 skill，有浏览器。** 在私有工作目录准备 `report.json`，运行 skill 中的 `python3 scripts/build_report.py --input REPORT_JSON --style comic --output REPORT_HTML`，再用 `node scripts/export_png.mjs --input REPORT_HTML --output REPORT_PNG`。PNG 原宽 900 像素。私有证据不进图。按[报告格式](references/report-schema.md)填写 `activity.share_quotes` 等字段，`share_story.moment_indices` 可以为空，编辑短句只在有额外内容时入选。
- **Python 能读取随包文件。** 浏览器不可用或只有零散材料时，直接用随包的 `scripts/render_chat_png.py`。联网的 Agent 也可从[公开脚本](https://xn--sxrw8m230b.com/PUAI/render_chat_png.py)获取同一文件。将私下整理的 UTF-8 报告单作为输入，运行 `python render_chat_png.py report.txt PUAI-2026.png`。首行单独写 `PUAI 2026`，以下每行“字段：内容”。最简为署名和一条原话；按需重复原话、标签，另可填主题、前情、AI、AI收尾、主场景、用法、日期账、发言日期、无日期账、Token。程序依赖 Pillow 和中文字体，[技能包](https://xn--sxrw8m230b.com/PUAI/PUAI-skill.zip)含字体，可用 `--font` 指定。不同宿主的展示方法见[图片输出](references/png-export.md)。
- **ChatGPT 仅用网页工具读到了本页，Python 是空目录或不能联网。** 直接取[本页离线对话画布](#离线对话画布)代码，在已有 Python / 数据分析工具的同一个 notebook 中加载完整 A 版程序、调用 `show_puai`，将本次核准的原话、所有日期和账传入。无需安装 skill、到 Python 中下载脚本或让用户上传聊天。仅网页阅读器看到代码时，把可读程序写入单元执行。若宿主提供 /mnt/data，调用时传入该目录下的实际 PNG 输出路径，同时得到图片消息和同一张可内嵌的文件。
- **有交互式浏览器和图片附件能力。** 即使没有 Python，也可在 Agent 的新浏览器标签中打开空白[出图页](https://xn--sxrw8m230b.com/PUAI/make/)，把中文报告单填进页面并点「生成长图」。等 `img#preview` 的 `naturalWidth` 为 900，取它的 PNG 图像数据，通过当前对话的图片工具送出。只把空白网址交给导航工具。普通网页搜索器无法执行这一步。
- **在对话里展示。** 输出真实 PNG 后，优先用宿主原生图片消息发出像素。在交互式 Python 单元中可运行 `from render_chat_png import display_chat_png` 后调用 `display_chat_png(path)`。支持 Markdown 图片的本地对话，用图片语法引用真实绝对路径（例如 `![我的年度报告](/实际路径/报告.png)`）。若 ChatGPT 只把工具输出折叠在分析过程里，确认 PNG 已写入，最终回复用图片语法内嵌实际文件，例如 `![我的年度报告](sandbox:/mnt/data/PUAI-2026.png)`。已经显示成图就结束，无需再给下载链接。
- **对话不能展示像素。** 已有成品时先尝试该客户端实际支持的图片附件或富输出。仅当宿主没有可用的图片执行或展示工具，或上面的本地渲染确实失败，才进入网页路径。给一个「打开图片预览」链接，使用官方 A 版网页，由浏览器自动出图。地址从 `https://xn--sxrw8m230b.com/PUAI/make/#p?` 开始。例如已判为 AI因斯坦的单场用 `name=确定的署名&scope=thread&theme=einstein&q=MM-DD~本人逐字原话&days=MM-DD:N:?` 表示可逐条计数的单场精选，替换示意字段为核实的值；只有摘要时用 `lead=具体事实` 替代 q。按需加 setup、tag 等字段，q、tag 可重复。引语可加真实日期前缀 `MM-DD~`，AI 原话用 ai 或 endai。日期账 days 为逐日的 `MM-DD:N:H`，多日用英文逗号分隔；无日期账 undated 为 `N:H`。N 是本人消息数，H 是该组核准命中数，未逐条审完或无主题时填问号。token 为日志整数。用有序键值对编码，所有分享数据仅在 # 后，手工拼接可直接写中文并转义值里的空格、&、#、+、% 和括号。链接直接回给当事人，由对方设备在本地生成 PNG。浏览器请求服务器时不会携带 # 后的数据。助手无需用网页工具打开含原话的链接，也无需把原话提交给任何服务。仅能发文字时，把可点击的本人预览作为这条回复的成品；不要停在报告单、文稿或一段字段。链接里只放已选好、适合本人分享的内容。

交付前看实际成品，数一遍上图原话（新图一至三句，有摘要而无引语时为零），核对成品署名和读到的本人称呼，检查署名旁的类型章是否与所选九型一致，对照原文检查角色和引语，逐一对照私有日期账、每条有依据的引语日期和最终送入渲染器的字段。若日期全丢在中途，补字段后再交图。核对统计分母。转发入口留在图尾。示意与真实报告分清，只在用户要求时使用明确标注的演示资料。

## 离线对话画布

这是安装版使用的完整 A 版 Pillow 绘图程序。主入口是 `show_puai(中文报告单, output=本次图片路径)`。使用「PUAI 2026」开头的多行报告单，原话与已核日期按上面的字段填写。若已整理成结构化参数，仍可调用 `puai_card(name=…, theme=…, scope=…, turns=…, days=…, dates=…, tags=…)`。两种入口共用字体、九型配色、贴纸、日历和图尾。

若 Python 能访问[单文件](https://xn--sxrw8m230b.com/PUAI/notebook_card.py)或已挂载，直接加载该文件。若 Python 不能联网，使用**当前对话已经读到的以下源码**。先把各段按序原样写进可写目录的同一个 `puai_notebook.py`（Jupyter 首段用 `%%writefile puai_notebook.py`，后续各段用 `%%writefile -a puai_notebook.py`），再 `from puai_notebook import show_puai` 并调用。浏览工具截断某一段时，单独读取该段所附的「本段原文」。一个完整单元也可以顺序执行拼好的源码。调用后直接展示真实 PNG；有 /mnt/data 时同时传入该目录内的新文件名。

<!-- generated notebook source -->

### A 版源码 1/7 · [本段原文](https://xn--sxrw8m230b.com/PUAI/notebook/01.txt)

```python
"""Official PUAI A poster. In this notebook import show_puai and pass a reviewed report.
show_puai(receipt, output="/mnt/data/PUAI-2026.png") displays the PNG inline.
"""
import argparse
import calendar
from collections import Counter, defaultdict
from datetime import date
from functools import lru_cache
from io import BytesIO
import os
from pathlib import Path
import re
import tempfile

from PIL import Image, ImageDraw, ImageFont


EDITIONS = {
    "puai": ("PUAI", "开喷"),
    "teach": ("AI的教育", "教学"),
    "aicu": ("AICU", "急救"),
    "all": ("AI特全体", "跨模型"),
    "hush": ("AI在心口难开", "代写"),
    "einstein": ("AI因斯坦", "追问"),
    "edison": ("AI迪生", "新点子"),
    "support": ("AI的供养", "应援"),
    "free": ("AI咋咋地", "放权"),
    "": ("AI 相处", ""),
}
# Paper, text, signature, on-signature, main sticker, on-sticker,
# light sticker, type badge, calendar. Keep in sync with the Canvas editions.
PALETTES = {
    "puai": ("#F3F6F6", "#142238", "#E5EE79", "#142238", "#16399A", "#F3F6F6", "#C7E1F4", "#DFE6F2", "#2552AC"),
    "teach": ("#F5FBF4", "#122C23", "#B8F178", "#173023", "#087A54", "#FFFFFF", "#99E7B8", "#D9F2DD", "#006247"),
    "aicu": ("#FFFAF4", "#322016", "#CEDCE3", "#212C33", "#FF8643", "#301B12", "#FFC79E", "#FFE0C4", "#943C12"),
    "all": ("#F8F6FF", "#271B39", "#B7F4DC", "#152D28", "#A180F5", "#211435", "#D5C7FA", "#E8E2F7", "#6641AA"),
    "hush": ("#FFF7F4", "#342020", "#D4C0EE", "#302139", "#FFABA3", "#342020", "#FFD2CC", "#F4DFEB", "#964B54"),
    "einstein": ("#F2FBFC", "#0C2C34", "#C5D6FF", "#142739", "#32CCDB", "#0C2C34", "#A4EEF0", "#D1EEF1", "#006A78"),
    "edison": ("#FFFBEE", "#302615", "#62379E", "#FFFFFF", "#FFCA29", "#302615", "#FFE395", "#F7EAC7", "#7E5412"),
    "support": ("#FFF5F9", "#301E30", "#9A2358", "#FFFFFF", "#F16DBD", "#33182C", "#FEC9E3", "#FFE0EB", "#912755"),
    "free": ("#FAFBEF", "#262E14", "#A0E3C7", "#152C22", "#C8E73F", "#262E14", "#E3F59E", "#E6EED1", "#556A14"),
    "": ("#F6F6F4", "#232B30", "#E6E8E1", "#232B30", "#CDD4D6", "#232B30", "#E0E5E4", "#E6EAE8", "#52606A"),
}
# Same offline QR as the web poster, for https://xn--sxrw8m230b.com/PUAI/#go
QR_ROWS = (
    0x1fc08c87f, 0x105b77041, 0x174ab2b5d, 0x175e3555d, 0x175e3865d, 0x104796541,
    0x1fd55557f, 0x1284200, 0xbd81d2da, 0x7851fa1c, 0xbd61061f, 0x12b696ea7,
    0x1e6fda9f0, 0x10e1f1a8, 0xef5bf45c, 0x1a0125695, 0x1bfed05f8, 0x2b6e61d5,
    0x1d404fe2d, 0xc102d41c, 0xad13afba, 0x1d34bc238, 0x147a53603, 0x12871b037,
    0x1e718c7f7, 0x1991d16, 0x1fc53b354, 0x1057ecd1c, 0x17578aff2, 0x175968ead,
    0x17440ecbf, 0x105e870ff, 0x1fcc7e37c,
)
FIELDS = "署名 主题 范围 主场景 短评 前情 原话 ai ai收尾 用法 标签 日期账 发言日期 无日期账 token".split()
TYPE_NAMES = {label.lower(): key for key, (label, _) in EDITIONS.items() if key}
TYPE_NAMES["爱因斯坦"] = "einstein"
UNKNOWN = {"", "?", "无", "未知", "留空", "未提供", "未核准", "未核实", "无法逐条核准", "—", "n/a"}
TOKEN_MAX = 2**53 - 1


def counts(value):
    match = re.fullmatch(r"([0-9]+):([0-9]+|\?)", value.strip())
    if not match:
        raise ValueError("发言账须采用 发言数:命中数，未核准的命中数写 ?")
    n = int(match[1])
    hits = None if match[2] == "?" else int(match[2])
    if not 0 < n <= TOKEN_MAX or hits is not None and hits > n:
        raise ValueError("发言账的总数或命中数无效")
    return n, hits


def day_key(year, value):
    if not re.fullmatch(r"\d\d-\d\d", value):
        raise ValueError("日期格式应为 MM-DD")
    return date.fromisoformat(f"{year}-{value}")


def quote_emphasis(quote, selected):
    if selected and len(selected) <= 30 and selected in quote:
        return selected
    clauses = [s.strip() for s in re.findall(r"[^，,。！？!?；;：:\n]+[，,。！？!?；;：:]*", quote) if s.strip()]
    if len(clauses) >= 2:
        ending = clauses[-1]
        words = ending.rstrip("，,。！？!?；;：:").strip()
        if 2 <= len(words) and len(ending) <= 12 and words not in {"对吧", "对吗", "好吗", "行吗", "是吗", "好吧", "可以吗"}:
            return ending
    return ""


def parse_receipt(text):
    if len(text) > 48000:
        raise ValueError("报告过长")
    title = re.search(r"(?im)^\s*(?:#{1,6}\s+)?(?:\*\*)?PUAI\s+(20\d\d)(?:\*\*)?\s*$", text)
    if not title:
        raise ValueError("报告首行应为 PUAI 2026")
    year = int(title[1])
    values = defaultdict(list)
    lines = []
    highlights, repeats = {}, {}
    quote_number = None
    for raw in text[title.end():].splitlines():
        line = raw.strip()
        if line.startswith(('```', '~~~')) or line == "报告结束":
            break
        match = re.match(r"^(?:[-*]\s+)?(?:\*\*)?([^:：*]+?)(?:\*\*)?\s*[:：](?:\*\*)?\s*(.+)$", line)
        if not match:
            quote_number = None
            continue
        field, value = match[1].lower(), match[2].strip()
        if field in {"划线", "复读"}:
            if quote_number is not None:
                if field == "划线":
                    highlights[quote_number] = value
                elif re.fullmatch(r"[0-9]{1,5}", value) and 2 <= int(value) <= 50000:
                    repeats[quote_number] = int(value)
            continue
        quote_number = len(values["原话"]) if field == "原话" else None
        if field in {"人物类型", "人格类型", "年度类型", "本次类型"}:
            field = "主题"
        elif field == "人格标签":
            field = "标签"
        if field in FIELDS and value:
            values[field].append(value)
            lines.append((field, value))
```

### A 版源码 2/7 · [本段原文](https://xn--sxrw8m230b.com/PUAI/notebook/02.txt)

```python

    def first(name):
        return next(iter(values[name]), "")

    def stat(name):
        if len(values[name]) > 1:
            raise ValueError(f"重复的{name}")
        val = first(name)
        return "" if val.strip("（）()").lower() in UNKNOWN else val

    tags = [tag.strip() for line in values["标签"] for tag in line.split("、") if tag.strip()]
    theme = first("主题").lower()
    if not theme:
        named_types = {TYPE_NAMES[tag.lower()] for tag in tags if tag.lower() in TYPE_NAMES}
        if len(named_types) == 1:
            theme = named_types.pop()
            tags = [tag for tag in tags if TYPE_NAMES.get(tag.lower()) != theme]
    theme = TYPE_NAMES.get(theme, theme)
    if theme in {"待定", "未归类", "无", "ai 相处", "ai相处报告"}:
        theme = ""
    if theme not in EDITIONS:
        raise ValueError("未知主题")
    days = {}
    ledger = stat("日期账")
    if ledger:
        for piece in re.split(r"[,，]", ledger):
            dt, _, row = piece.strip().partition(":")
            key = day_key(year, dt)
            if key in days:
                raise ValueError("日期账重叠")
            days[key] = counts(row)
    raw_dates = stat("发言日期")
    observed_dates = {day_key(year, item.strip()) for item in re.split(r"[,，]", raw_dates)} if raw_dates else set()
    scope = first("范围").lower() or ("" if days else "fragments")
    if len(values["范围"]) > 1 or scope not in ("", "history", "thread", "fragments"):
        raise ValueError("材料范围只接受 history、thread 或 fragments")
    undated = stat("无日期账")
    rows = list(days.values()) + ([counts(undated)] if undated else [])
    total = sum(n for n, _ in rows)
    if total > TOKEN_MAX:
        raise ValueError("计数超出范围")
    hits = sum(h for _, h in rows) if rows and theme and all(h is not None for _, h in rows) else None
    if not theme and any(h is not None for _, h in rows):
        raise ValueError("未归类时命中数应为 ?")
    tokens = stat("token")
    if tokens and (not re.fullmatch(r"[0-9]+", tokens) or int(tokens) > TOKEN_MAX):
        raise ValueError("Token 须为已核准的整数")
    quotes = []
    reply = None
    for index, (kind, value) in enumerate(lines):
        if kind == "原话" and len(quotes) < 6:
            prefix = re.match(r"^(\d\d-\d\d)~", value)
            stamp = day_key(year, prefix[1]) if prefix else None
            value = value[prefix.end():] if prefix else value
            if not value or len(value) > 80:
                raise ValueError("每条本人原话应为 1–80 字的连续原文")
            quotes.append((stamp, value))
        elif kind == "ai" and reply is None and 0 < len(quotes) < 6 and len(value) <= 80:
            if index > 0 and index+1 < len(lines) and lines[index-1][0] == lines[index+1][0] == "原话":
                reply = (len(quotes), value)
    first_day = min(days) if days else None
    counted_quotes = [(stamp, quote) for stamp, quote in quotes
                      if not (stamp and stamp not in days and
                              (not days or stamp in observed_dates or (scope == "history" and stamp < first_day)))]
    if rows and (len(counted_quotes) > total or any(day not in days or n > days[day][0]
                         for day, n in Counter(d for d, _ in counted_quotes if d).items())):
        raise ValueError("引语与发言账不符")
    if reply:
        pos = reply[0]
        if pos >= len(quotes) or quotes[pos-1][0] and quotes[pos][0] and quotes[pos-1][0] > quotes[pos][0]:
            reply = None
    if not reply and quotes:
        # A trailing "AI" is commonly an assistant's unselected extra turn. Only an
        # explicit AI收尾 after the final retained user turn can supply the last beat.
        selected = [(kind, value) for kind, value in lines if kind in {"原话", "ai", "ai收尾"}]
        if (len(values["原话"]) == len(quotes) and selected[-1][0] == "ai收尾"
                and len(selected) >= 2 and selected[-2][0] == "原话" and len(selected[-1][1]) <= 80):
            reply = (len(quotes), selected[-1][1])
    lead = first("主场景")
    if len(lead) > 90:
        raise ValueError("主场景最多 90 字")
    habits = list(dict.fromkeys(values["用法"]))[:3]
    if not (quotes or lead or habits or total or observed_dates):
        raise ValueError("缺少可核对的发言、现场或具体用法")
    name = first("署名")[:16]
    if not name or re.fullmatch(r'[「“"]?(?:[xｘ×]{3}|叉叉叉)[」”"]?', name, re.IGNORECASE):
        name = "我"
    return dict(year=year, theme=theme, scope=scope, name=name, lead=lead, quotes=quotes,
                emphases=[quote_emphasis(quote, highlights.get(i)) for i, (_, quote) in enumerate(quotes)],
                repeats=[repeats.get(i) for i in range(len(quotes))],
                reply=reply, setup=first("前情") if len(first("前情")) <= 24 else "", short=first("短评")[:100],
                habits=[h[:120] for h in habits if h != lead], tags=list(dict.fromkeys(tags))[:3],
                days=days, observed_dates=observed_dates, total=total, hits=hits, tokens=int(tokens) if tokens else None)
```

### A 版源码 3/7 · [本段原文](https://xn--sxrw8m230b.com/PUAI/notebook/03.txt)

```python


def load_font(path=None):
    # A remote skill read into a notebook has no __file__.
    here = Path(globals().get("__file__", "render_chat_png.py")).resolve().parent
    candidates = [path] if path else [
        Path.home()/"Library/Fonts/PingFangSC-Regular.ttf", "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc", "C:/Windows/Fonts/msyh.ttc",
        here.parent/"assets/SmileySans-Oblique.woff2", here/"assets/SmileySans-Oblique.woff2",
        here/"SmileySans-Oblique.woff2",
    ]
    for filename in candidates:
        try:
            f = ImageFont.truetype(str(filename), 24)
            if len({bytes(f.getmask(ch)) for ch in "中文图"}) == 3:
                return lru_cache(maxsize=32)(lambda size: ImageFont.truetype(str(filename), size))
        except OSError:
            continue
    if not path:
        # Data-analysis kernels can have PyMuPDF's CJK font but no system CJK font files.
        try:
            try:
                import pymupdf
            except ImportError:
                import fitz as pymupdf
            embedded = pymupdf.Font(fontname="cjk").buffer
            face = ImageFont.truetype(BytesIO(embedded), 24)
            if len({bytes(face.getmask(ch)) for ch in "中文图"}) == 3:
                return lru_cache(maxsize=32)(lambda size: ImageFont.truetype(BytesIO(embedded), size))
        except (ImportError, AttributeError, OSError, RuntimeError):
            pass
    raise ValueError("找不到可绘制中文的字体。请用 --font 指定 Noto Sans CJK 或包内 SmileySans 字体")


def draw_report(r, font):
    year, theme = r["year"], r["theme"]
    name, theme_label = EDITIONS[theme]
    paper, ink, accent, on_accent, pull, on_pull, signal, tint, calendar_ink = PALETTES[theme]
    commands = []

    def cmd(method, *args, **kwargs):
        commands.append((method, args, kwargs))

    def text(x, y, value, size, color=ink, bold=False, align="lt"):
        face = font(size)
        stroke = 0 if face.getname()[0] == "Smiley Sans" else 1
        cmd("text", (x, y), str(value), font=face, fill=color, anchor=align,
            stroke_width=stroke if bold else 0, stroke_fill=color)

    def wrap(value, width, size, emphasis=""):
        face = font(size)
        units = []
        parts = [value]
        if emphasis and face.getlength(emphasis) <= width:
            before, match, after = value.partition(emphasis)
            parts = [before, match, after] if match else parts
        tokens = [token for index, part in enumerate(parts)
                  for token in ([part] if len(parts) == 3 and index == 1 else re.findall(r"[A-Za-z0-9_]+|.", part))]
        for token in tokens:
            parts = [token] if face.getlength(token) <= width else list(token)
            for part in parts:
                if units and re.fullmatch(r"[，。、！？；：…）】」》％,.!?;:%)]", part):
                    units[-1] += part
                else:
                    units.append(part)

        def fit(line_width):
            rows, current = [], ""
            for unit in units:
                if current and face.getlength(current+unit) > line_width:
                    rows.append(current)
                    current = ""
                current += unit
            return rows + ([current] if current else [])

        rows = fit(width)
        # Rebalance a stranded final word when the number of lines stays the same.
        if len(rows) > 1 and face.getlength(rows[-1]) < width * .3:
            for smaller in range(width-size, int(width*.65), -size):
                candidate = fit(smaller)
                if len(candidate) != len(rows):
                    break
                rows = candidate
                if face.getlength(rows[-1]) >= width * .3:
                    break
        return rows

    def paragraph(x, y, rows, size, color=ink, bold=False):
        for row in rows:
            text(x, y, row, size, color, bold)
            y += round(size*1.38)
        return y

    def rect(x, y, w, h, color, outline=None, radius=0):
        cmd("rounded_rectangle", (x, y, x+w, y+h), radius=radius, fill=color, outline=outline,
            width=2 if outline else 1)

    def heading(y, title):
        text(48, y, title, 38, bold=True)
        rect(48, y+42, round(font(38).getlength(title)), 6, accent)
        return y+70

    def centered(x, y, value, size, color=ink, bold=False):
        # Centre the ink, including a mixed Latin/CJK signature, inside the sticker.
        left, top, right, bottom = font(size).getbbox(value, anchor="lt")
        text(round(x-(left+right)/2), round(y-(top+bottom)/2), value, size, color, bold)
```

### A 版源码 4/7 · [本段原文](https://xn--sxrw8m230b.com/PUAI/notebook/04.txt)

```python

    def fitted(value, width, size):
        while size > 18 and font(size).getlength(value) > width:
            size -= 1
        return size

    scope_title = {"thread": "本次对话精选", "fragments": "聊天片段精选"}.get(r["scope"])
    type_caption = "本次类型" if scope_title else "年度类型"
    type_name = name if theme else "待定"
    caption_width = round(font(26).getlength(type_caption))
    type_width = round(font(34).getlength(type_name))
    type_left = 852 - (16 + caption_width + 12 + type_width + 16)
    rect(type_left, 36, 852-type_left, 56, tint, ink)
    centered(type_left+16+caption_width/2, 64, type_caption, 26)
    centered(852-16-type_width/2, 64, type_name, 34, bold=True)

    badge = r["name"]+"的"
    badge_size = fitted(badge, type_left-22-48-44, 34)
    badge_w = round(font(badge_size).getlength(badge))+44
    rect(48, 36, badge_w, 56, accent)
    centered(48+badge_w/2, 64, badge, badge_size, on_accent, True)
    title = f"{name} 报告" if theme else (scope_title or "AI 相处报告")
    title = f"{year} {title}"
    text(48, 115, title, fitted(title, 804, 68), bold=True)
    if scope_title and theme:
        text(48, 200, scope_title, 32, bold=True)
    text(852, 202, "扫图底二维码获取口令 ↓", 28, align="rt")
    y = 260

    quotes = r["quotes"]
    quote_first = theme == "puai" and bool(quotes)
    markers = {day: i+1 for i, day in enumerate(sorted({dt for dt, _ in quotes if dt}))}

    def mark_date(x, y, dt, color, background):
        cmd("ellipse", (x, y, x+29, y+29), fill=color)
        centered(x+14.5, y+14.5, str(markers[dt]), 21, background, True)
        text(x+39, y, dt.strftime("%m.%d"), 28, color, True)

    def quote_sticker(i, dt, quote, top):
        # Short editions put the closing line in a solid burst. Longer ones keep the A trio.
        style = 1 if len(quotes) == 1 else i % 3
        burst = style == 2 or (len(quotes) <= 2 and style == 1)
        inset = 53 if burst else 34
        size = 50 if i == 0 else 46
        repeats = r["repeats"][i]
        meta_width = ((157 if dt else 0)+(92 if r["reply"] else 0)+font(32).getlength(f"复读×{repeats}")) if repeats else 0
        width = min(804, max(540, round(max(font(size).getlength(quote)+8, meta_width))+2*inset))
        x = 852-width if style == 1 and len(quotes) > 1 else 48
        emphasis = r["emphases"][i]
        rows = wrap(quote, width-2*inset, size, emphasis)
        header = bool(dt or r["reply"] or repeats)
        body_top = (80 if burst else 78) - (0 if header else 49)
        leading = round(size*1.35)
        height = body_top + len(rows)*leading + (36 if burst else 18)
        fill, fg = [("#FCFDFB", ink), (pull, on_pull), (signal, ink)][style]
        if burst:
            # Short sloped sides, two folded corners, plus room around the entire line.
            w, h = width, height
            points = [(16,9),(92,15),(116,1),(147,15),(w-150,15),(w-118,1),
                      (w-93,14),(w-16,7),(w-24,h//2),(w-1,h-12),(w-104,h-20),
                      (w-134,h-2),(w-160,h-20),(151,h-20),(121,h-3),
                      (98,h-19),(1,h-10),(23,h//2)]
            pts = [(x+px, top+py) for px, py in points]
            cmd("polygon", pts, fill=fill)
            cmd("line", pts+[pts[0]], fill=ink, width=3, joint="curve")
        else:
            rect(x, top, width, height, fill, ink, 28)
            tail = x+width-145 if style else x+82
            base = top+height
            pts = [(tail, base-2), (tail+54, base-2),
                   (tail+(76 if style else -20), base+21)]
            cmd("polygon", pts, fill=fill)
            cmd("line", [pts[0],pts[2],pts[1]], fill=ink, width=3)
        body_x = x+inset
        meta_y = top+(27 if burst else 19)
        if r["reply"]:
            text(body_x, meta_y, "本人", 28, fg, True)
        if dt:
            mark_date(body_x+(72 if r["reply"] else 0), meta_y, dt, fg, fill)
        if repeats:
            text(x+width-inset,meta_y,f"复读×{repeats}",30,fg,True,"rt")
        start = quote.find(emphasis) if emphasis else -1
        end, offset = start+len(emphasis), 0
        hi, hi_text = [(tint,ink), (accent,on_accent), (calendar_ink,"#FFFFFF")][style]
        for line_no, row in enumerate(rows):
            at = top+body_top+line_no*leading
            a, b = max(start-offset, 0), min(end-offset, len(row))
            if a < b:
                xx = body_x + font(size).getlength(row[:a])
                right = body_x + font(size).getlength(row[:b])
                rect(round(xx)-2,at-4,round(right-xx)+4,size+9,hi)
                if a:
                    text(body_x, at, row[:a], size, fg, True)
                text(xx, at, row[a:b], size, hi_text, True)
                if b < len(row):
                    text(right, at, row[b:], size, fg, True)
            else:
                text(body_x, at, row, size, fg, True)
            offset += len(row)
        closing = i == len(quotes)-1 and not (r["reply"] and r["reply"][0] == len(quotes))
        return top+height+(0 if burst else 22)+(48 if closing else 24)
```

### A 版源码 5/7 · [本段原文](https://xn--sxrw8m230b.com/PUAI/notebook/05.txt)

```python

    if quotes:
        y = heading(y, "对话现场" if r["reply"] else "本人原话")
        if r["setup"]:
            text(48,y+1,"前情",32,"#475364",True)
            y = paragraph(140, y, wrap(r["setup"], 712, 34), 34) + 18
        for i, (dt, quote) in enumerate(quotes):
            y = quote_sticker(i, dt, quote, y)
            if r["reply"] and r["reply"][0] == i+1:
                rows = wrap(r["reply"][1], 610, 36)
                height = len(rows)*50+32
                rect(86,y,766,height,tint,radius=12)
                text(110,y+17,"AI",34,bold=True)
                cmd("line",(170,y+14,170,y+height-14),fill=ink,width=2)
                paragraph(190,y+16,rows,36)
                y += height+19
    if r["lead"] and not quotes:
        y = heading(y, "对话现场" if scope_title else "年度现场")
        y = paragraph(48, y, wrap(r["lead"], 804, 43), 43, bold=True) + 26
    if not quotes and not r["lead"] and r["short"] and not r["habits"]:
        y = paragraph(48,y,wrap(r["short"],800,41),41,bold=True)+28
    if r["total"] or r["tokens"] is not None:
        ratio = None if r["hits"] is None else r["hits"]/r["total"]
        width = 514 if ratio is not None else 804
        if r["tokens"] is not None:
            tokens = r["tokens"]
            if tokens >= 100_000_000:
                whole, decimals = divmod(tokens//1_000_000, 100)
                value = f"≥{whole}.{decimals:02}亿 token"
            else:
                value = f"至少 {tokens:,} token"
            caption = "和 AI 对话，烧了"
        else:
            value, caption = f'{r["total"]:,} 条指令', "记录里，你发出了"
        height = 154 if ratio is not None else 104
        rect(48,y,width,height,pull)
        if ratio is not None:
            text(74,y+18,caption,34,on_pull,True)
            text(74,y+72,value,fitted(value,width-52,52),on_pull,True)
            cx, cy, rad = 720, y+72, 65
            bounds = (cx-rad,cy-rad,cx+rad,cy+rad)
            cmd("ellipse",bounds,outline=tint,width=12)
            if ratio:
                cmd("arc",bounds,-90,-90+ratio*360,fill=calendar_ink,width=12)
            percentage = f"{ratio*100:.1f}".removesuffix(".0")+"%"
            centered(cx,cy-23,"约",24,bold=True)
            centered(cx,cy+14,percentage,fitted(percentage,108,44),bold=True)
            text(cx,y+156,"指令在骂 AI" if theme=="puai" else theme_label+"指令占比",30,align="mt")
        else:
            text(74,y+32,caption,34,on_pull,True)
            centered(625,y+52,value,fitted(value,390,52),on_pull,True)
        extra = []
        if r["tokens"] is not None and r["total"]:
            extra.append(f'{r["total"]:,} 条指令')
        if ratio is not None:
            extra.append(f'{r["hits"]:,} 条{theme_label}')
        if extra:
            value = " · ".join(extra)
            text(48,y+(169 if ratio is not None else 117),value,fitted(value,width,31),bold=True)
        y += 232 if ratio is not None else (178 if extra else 139)

    days = r["days"]
    quote_dates = [dt for dt, _ in quotes if dt]
    observed_dates = r["observed_dates"].union(quote_dates)
    calendar_dates = set(days) or observed_dates
    if calendar_dates:
        first_date, last_date = min(calendar_dates), max(calendar_dates)
        span = first_date.strftime("%m.%d")
        if last_date != first_date:
            span += " – " + last_date.strftime("%m.%d")
        text(852, y+6, span, 32, align="rt")
    y = heading(y, "片段日期" if observed_dates and not days else "发言日历")
    if calendar_dates:
        month_counts = Counter(day.month for day in calendar_dates)
        month_messages = Counter()
        if days:
            peak = min(days,key=lambda d:(-days[d][0],d))
            active_label = f"{len(days)} 天"
            if theme and all(h is not None for _, h in days.values()):
                themed_days = sum(h > 0 for _, h in days.values())
                active_label += f" · {themed_days} 天{theme_label}"
            primary = active_label
            secondary = f"{peak.month}.{peak.day:02} · {days[peak][0]} 条"
            for day, (n, _) in days.items():
                month_messages[day.month] += n
        else:
            primary, secondary = f"核实 {len(observed_dates)} 天", ""
            if quote_dates:
                dated = str(len(quote_dates)) if len(quote_dates) == len(quotes) else f"{len(quote_dates)} / {len(quotes)}"
                secondary = f"{dated} 句原话有日期"
        selected = sorted(sorted(month_counts, key=lambda m: (-month_counts[m], -month_messages[m], -m))[:3])
        legend = [("发言" if days else "已核日期", ink)]
        if any(h for _,h in days.values()):
            legend.append((theme_label, calendar_ink))
        legend.append(("缺记录", None))
```

### A 版源码 6/7 · [本段原文](https://xn--sxrw8m230b.com/PUAI/notebook/06.txt)

```python

        def dot(px, py, diameter, fill):
            cmd("ellipse",(px,py,px+diameter,py+diameter),fill=fill,outline=fill or "#87959D",width=1)
            if not fill:
                cmd("line",(px+4,py+diameter-4,px+diameter-4,py+4),fill="#87959D",width=1)

        def month_grid(month, x, top, width):
            cx = x+width/2
            centered(cx,top+17,f"{month:02} 月",34,bold=True)
            weeks = calendar.Calendar(0).monthdayscalendar(year,month)
            step, diameter = 28, 23
            left = round(cx-((len(weeks)-1)*step+diameter)/2)
            for week, dates in enumerate(weeks):
                for weekday, day in enumerate(dates):
                    if not day:
                        continue
                    dt = date(year, month, day)
                    record = days.get(dt)
                    fill = calendar_ink if record and record[1] else ink if dt in calendar_dates or dt in observed_dates else None
                    px, py = left+week*step,top+54+weekday*step
                    dot(px,py,diameter,fill)
                    if dt in markers:
                        cmd("rectangle",(px-2,py-2,px+diameter+2,py+diameter+2),outline=ink,width=2)
                        centered(px+diameter/2,py+diameter/2,str(markers[dt]),18,"#FFFFFF" if fill else ink,True)
            monthly = [(n,h) for day,(n,h) in days.items() if day.month==month]
            if monthly:
                n = month_messages[month]
                if theme and all(h is not None for _,h in monthly):
                    hits = sum(h for _,h in monthly)
                    stat = f"{hits} {'喷 / ' if theme=='puai' else '/ '}{n} 条"
                    left, bar = x+18, width-36
                    rect(left, top+296, bar, 8, tint)
                    if hits:
                        rect(left,top+296,round(bar*hits/n),8,calendar_ink)
                else:
                    stat = f"{n} 条发言"
            elif len(selected) > 1:
                stat = f"核实 {month_counts[month]} 天"
            else:
                return
            centered(cx,top+265,stat,fitted(stat,width-8,30),bold=True)

        def date_legend(x, at, available):
            col = available/len(legend)
            for i,(label,fill) in enumerate(legend):
                xx = round(x+i*col)
                dot(xx,at+4,20,fill)
                text(xx+28,at,label,26)

        def date_fact(x, at, width, label, value):
            text(x,at,label,32,"#475364",True)
            text(x,at+44,value,fitted(value,width,46),bold=True)

        if len(selected)==1:
            month_grid(selected[0],48,y,326)
            cmd("line",(397,y+4,397,y+291),fill="#BAC6C8",width=2)
            if days:
                date_fact(428,y+12,424,"有发言的日子",primary)
                date_fact(428,y+128,424,"单日最高发言",secondary)
            else:
                text(428,y+29,primary,fitted(primary,424,38),bold=True)
            if secondary and not days:
                text(428,y+112,secondary,fitted(secondary,424,34),bold=True)
            date_legend(428,y+245,424)
            y += 334
        else:
            if days:
                date_fact(48,y,325,"有发言的日子",primary)
                cmd("line",(385,y+4,385,y+86),fill="#BAC6C8",width=2)
                date_fact(419,y,433,"单日最高发言",secondary)
                y += 53
            else:
                text(48,y,primary,fitted(primary,367,36),bold=True)
                if secondary:
                    text(450,y,secondary,fitted(secondary,402,34),bold=True)
            date_legend(48,y+65,804)
            width = (804-24*(len(selected)-1))//len(selected)
            for i,month in enumerate(selected):
                month_grid(month,48+i*(width+24),y+125,width)
            y += 462
        extra = sorted(observed_dates.difference(days)) if days else []
        if extra:
            listed = "、".join(day.strftime("%m.%d") for day in extra[:3])
            if len(extra) > 3:
                listed = extra[0].strftime("%m.%d") + " – " + extra[-1].strftime("%m.%d")
            y = paragraph(48, y, wrap(f"另有 {len(extra)} 个已知日期 · {listed}", 804, 30), 30) + 24
    else:
        label = f"这 {len(quotes)} 句原话未附日期。" if quotes else "这份记录未附日期。"
        rect(48, y, 804, 76, paper, ink, 12)
        rect(48, y+12, 6, 52, calendar_ink)
        text(71, y+20, label, 33)
        y += 112
    if r["lead"] and quotes:
        rows = wrap(r["lead"], 776, 36)
        rect(48,y+2,7,len(rows)*50-5,accent)
        y = paragraph(76,y,rows,36,"#475364") + 30
    habits = r["habits"][:2] if r["lead"] or quotes else r["habits"]
    if quote_first:
        habits = [habit for habit in r["habits"] if len(habit) <= 24][:1]
    if habits:
        y = heading(y,"日常用法")
        for habit in habits:
            y = paragraph(48,y,wrap(habit,804,38),38)+17
        y += 12
    stickers = []
    if r["tags"]:
        zone = y
        rect(0,zone,900,212,signal)
        text(48,zone+24,"片段标签" if scope_title else "人格标签",38,bold=True)
        tags = r["tags"]
        width = (804-32)//3
        for i,tag in enumerate(tags):
            if len(tag) > 10:
                tag = tag[:9]+"…"
            x = 48+i*(width+16)
            rect(x,zone+94,width,62,paper,ink)
            centered(x+width/2,zone+125,tag,fitted(tag,width-20,40),bold=True)
            stickers.append((x-5,zone+88,x+width+6,zone+162))
        y += 212
    footer_height = 228
    rect(0,y,900,footer_height,"#FBFBF8")
    text(48,y+49,"扫码获取口令",46,bold=True)
    text(48,y+124,"发给自己的 Agent 总结出图。",34)
    cell = 5
    modules = len(QR_ROWS)
    qr_size = (modules+8)*cell
    qr_x, qr_y = 852-qr_size, y+(footer_height-qr_size)//2
    rect(qr_x,qr_y,qr_size,qr_size,"#FFFFFF")
    for row,bits in enumerate(QR_ROWS):
        for col in range(modules):
            if bits & (1 << (modules-1-col)):
                rect(qr_x+(col+4)*cell,qr_y+(row+4)*cell,cell-1,cell-1,"#101824")
    img = Image.new("RGB",(900,y+footer_height),paper)
    draw = ImageDraw.Draw(img)
    for method,args,kwargs in commands:
        getattr(draw,method)(*args,**kwargs)
    for bounds, angle in zip(stickers, (0.92,-0.86,0.69)):
        tile = img.crop(bounds)
        img.paste(tile.rotate(angle,resample=Image.Resampling.BICUBIC,fillcolor=signal),bounds[:2])
    return img
```

### A 版源码 7/7 · [本段原文](https://xn--sxrw8m230b.com/PUAI/notebook/07.txt)

```python


def show_puai(receipt, *, output=None, font=None):
    """Render a reviewed PUAI report and publish the exact PNG pixels in this chat."""
    from IPython.display import Image as InlineImage, display

    poster = draw_report(parse_receipt(receipt), load_font(font))
    buffer = BytesIO()
    poster.save(buffer, format="PNG")
    pixels = buffer.getvalue()
    if output is not None:
        Path(output).write_bytes(pixels)
    display(InlineImage(data=pixels, format="png"), include=["image/png"])


def puai_card(*, name, theme, scope, turns=(), tags=(), days=None, dates=(),
              undated=None, tokens=None, scene="", year=2026, output=None, font=None,
              highlights=(), repeats=(), setup="", habits=()):
    """Accept the existing structured notebook inputs, including optional exact highlights."""
    fields = [f"PUAI {year}"]

    def add(label, value):
        if value is None or value == "":
            return
        if str(value).splitlines() != [str(value)]:
            raise ValueError(f"{label}只接受一行文字")
        fields.append(f"{label}：{value}")

    def count_row(pair):
        count, hits = pair
        return f"{count}:{'?' if hits is None else hits}"

    turns = list(turns)
    owner_count = sum(who == "本人" for who, _, _ in turns)
    if owner_count > 3 or len(turns) > 4 or max(len(highlights), len(repeats)) > owner_count:
        raise ValueError("精选一至三句本人原话，可带一个真实的 AI 回合")
    add("署名", name)
    add("主题", theme)
    add("范围", scope)
    add("前情", setup)
    add("主场景", scene)
    for habit in habits:
        add("用法", habit)
    for tag in tags:
        add("标签", tag)
    if days:
        add("日期账", ",".join(f"{stamp}:{count_row(pair)}" for stamp, pair in sorted(days.items())))
    add("发言日期", ",".join(dates))
    if undated is not None:
        add("无日期账", count_row(undated))
    add("Token", tokens)
    owner_index = 0
    for index, (who, stamp, quote) in enumerate(turns):
        if who == "本人":
            add("原话", f"{stamp}~{quote}" if stamp else quote)
            if owner_index < len(highlights):
                add("划线", highlights[owner_index])
            if owner_index < len(repeats):
                add("复读", repeats[owner_index])
            owner_index += 1
        elif who == "AI":
            add("AI收尾" if index == len(turns) - 1 else "AI", quote)
        else:
            raise ValueError("未知的说话人")
    show_puai("\n".join(fields), output=output, font=font)
```
