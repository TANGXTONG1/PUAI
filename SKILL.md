---
name: puai
description: 用已授权的本人聊天生成 PUAI 年度报告长图。适用于“用 PUAI 翻我的聊天”“也给我做一张”、收到 PUAI 图想找同款口令，或要求从真实 AI 对话里找金句、发言日历和相处特征。
---

# PUAI 年度报告

交付一张能在手机里读的官方漫画 A 版。调用者只需提供署名（可选）。本地从本 skill 目录取程序和模板，在线读到本文的助手按下文的云端方式使用同一项目。参考图上的人、统计和台词属于原作者。

图尾只放二维码，旁边写「扫码获取口令，发给自己的 Agent 总结出图。」收到用户的生成口令，或用户明确要用自己的聊天生成时，直接按下面步骤出图。

每张成图都在署名旁标人物类型，页尾另放个性标签；「AI因斯坦」是类型，「车厘子精算师」是个性标签。每张图都留日历。**先取日期，再选原话**：打开原线程时一并读取本人消息的发送时间，按用户时区记到私有账。收到「补日期」时，沿用上一张图的署名和逐字原话，以原句去已授权的本人聊天里回查发送时间，并盘点同一范围可计数的其他发言，再出图。

在 ChatGPT 里收到口令，先取材，再实际调用当前对话的数据分析 / Python 工具显示成图。若只读到了本页，直接在工具内执行[本页离线对话画布](#离线对话画布)；也可让当前网页阅读工具读取[单独的短程序](https://xn--sxrw8m230b.com/PUAI/notebook_card.py)。代码和数据在当前对话结合。

## 从聊天里找当事人的话

1. **认人。** 本次填了具体署名就照写。明确要求匿名或署「我」时用「我」，从公开内容和链接里一起排除旧称呼。空白、未替换的 XXX（含大小写和全角）都走自动署名：取材时顺手找本人反复使用的自称、认可的昵称或对称呼问题的回答，沿用最近的分享昵称。发现具体名字线索再回查出处，无需逐个搜索称呼的同义词。仅凭第三方姓名、样图、邮箱或账号还认不出来，就署「我」。所有出图路径使用同一个选好的称呼。生成口令与署名设置从选句和统计里排除。
2. **先盘点能读到的历史。** 先做下面的取材步骤，再决定出年度图还是单场精选。收到口令的线程通常只有一条生成指令，本身不算一个现场。

   - **有历史工具的客户端。** 实际调用已授权的个人历史目录、搜索和原线程读取工具。按目标年翻目录并跟随分页，先看早期、活跃期和近期的不同话题。把可见记忆、聊天标题和原文里的线索分开记：从本人的一个具体物件、惯用词或未完的决定出发，回到个人历史找它第一次出现和后来怎样了。只命中同一线程，换成当事人自己的另一种说法，再换时间或话题。另打开一批与这条记忆无关的线程，留意普通标题下突然好笑的一次追问、算账或改口。没有目录就用现有线索分开搜索，没有搜索工具就翻可读记录。有未读命中或下一页时先打开。只剩一段记忆时，查一个辨识度高的词，再试另一条独立线索或一次换词。两轮都找不到新线程且没有其他可读来源，就用已核材料收稿；避免拿「我」「你」「的」逐字扫库。记忆可以指路，逐字原话和日期要回原消息取。普通网页搜索不用于检索个人历史。
   - **已安装的本地 Agent。** 有授权的聊天索引就用；缺索引可用随包的 `python3 scripts/collect_history.py --client codex --year 2026 --output PRIVATE.jsonl > INVENTORY.json` 盘点当前客户端；Claude Code 用 `--client claude`。ChatGPT 对话中已有用户提供的导出 JSON/ZIP 时，用 `--client chatgpt --export FILE`。三者均可用 `--timezone Asia/Shanghai`（替换为用户时区）。云端 Python 可取同目录的[盘点](https://xn--sxrw8m230b.com/PUAI/collect_history.py)、[翻阅](https://xn--sxrw8m230b.com/PUAI/browse_history.py)和[原文读取](https://xn--sxrw8m230b.com/PUAI/read_context.py)脚本。运行 `python3 scripts/browse_history.py --index PRIVATE.jsonl --output PAGE.json`，按月份和线程交错读本人发言。加 `--term 物件或口头禅` 搜本人线索（可重复，任一词命中），用 `--page 2` 继续翻页。最后用 `python3 scripts/read_context.py --index PRIVATE.jsonl --id ID --source SOURCE --output PRIVATE_WINDOW` 打开候选前后的原文，读取回查结果的 `target_date`。索引仅作取材，留在当前环境。
   - **私下核对覆盖。** 留下实际打开的线程、日期跨度、可计数范围和还没打开的线索。选句时先核看六个线程、三个有记录的时段；打开六次相似工单仍只得到一种现场。候选全来自最近同一话题、都在交代任务，或全依赖编辑解释才懂时，优先去未看的月份、闲聊或结尾翻第二回合。换入口仍只得到同样的材料，或可读来源已经用尽，就按实际范围付印。确实只读到一个线程就标 `scope=thread`；仅有零散摘句或摘要就标 `scope=fragments`。跨线程核到多个独立现场，足以支持一个阶段的回顾，才标 `scope=history`。在精选图旁用一句话告知本次实际范围；若用户要扩大覆盖，可在有历史工具的 Agent 发同一句口令，或在能读文件的对话选用已有聊天导出，无需手贴记录。图上用标题标材料范围。
3. **先定类型。** 读过原文后，按下表九型选一个最能解释这人怎么用 AI 的类型。年度回顾看在不同现场反复出现的动作；单场或片段看这一回合实际做了什么，一次有辨识度的互动就能定「本次类型」。有多个现场时，拿另外一次发言试一试初判，看它更支持哪个类型。比如频繁纠正答案，有人是在教 AI，有人是在找机会讨债，第二回合往往才能分清。留下最能同时解释动作和原话的类型，再从相符的场景中精选。两类同样有据时，有具体对象的 PUAI 调侃优先。
4. **选原话。** 在私有候选旁记原消息位置、日期、说话人和上下句。摘候选时多看用户听完 AI 后说的下一句：有没有顺着它的逻辑反问、给一个离谱的例外，或者隔了几天回来把账结了？试着盖住类型名和短评，让不认识这人的读者也能听出他哪里较真、哪里心软、哪里突然变脸。具体人名和项目细节遮不掉，或全靠解释才能成立，就从另一事件找一句。普通工作说明和术语长段留在私有材料。新报告默认上 **两句**。最出彩的一句开场，下一句要有新落点，或能和第一句产生回声。两句试排后，只读将上图的字：读者能说清第二句里的人或东西怎么冒出来了吗？断在中间时，优先换成同一现场里自带起因和落点的两句；也可用一行已核事实补上缺的一步。只有一句值得转发就只选一句。第三句只在带来翻转或省去它就断掉时上图，新图最多三句。检索范围和发言账照常覆盖全部已核记录。见[选材参考](references/scene-selection.md)。
5. **付印。** 每句最多 80 字，保留原文、空格和标点。摘短只能取完整保留原意的连续片段。两条真实独立的发言各标自己的日期，避免剪成同一场对话。排除代拟稿、他人引语、系统提示、报告制作指令和工作机密。优先让原话直接开场，默认省略主场景、导语和短评。确实差半步才听得懂时，补一行可核实的事实前情（最多 24 字）。只有脱敏摘要时，用一个可核的具体动作出短卡。

选好的九型用专门的主题字段传给模板。尾部另可放 0–3 个短标签，每个最多六字。标签可借用原话里的物件或算账方式，「哪个动作只有在这张图里才说得通」是取舍标准。「善于提问」「当场纠偏」这类能移到别张图上的话直接删去。AI 的真实原话最多一条，仅在同一原线程里夹在两条用户发言之间，或确实紧接最后一问、能当落点时入选，另标「AI」。互不相干的问答分别呈现。没有任何具体互动材料时，提示到日常使用的旧对话发同一句口令；无需用户粘贴历史。

| 主题 | 行为依据 |
|---|---|
| `puai` PUAI | 反复向 AI 讨债、反问、揶揄，或拿它前面的承诺当场对质 |
| `teach` AI的教育 | 亲自示范、出考题、教它怎么验收 |
| `aicu` AICU | 真有时限的求救，当时决定优先救哪件事 |
| `all` AI特全体 | 请几个模型互评、仲裁同一题 |
| `hush` AI在心口难开 | 为一句话怎么被听懂反复斟酌 |
| `einstein` AI因斯坦 | 追问原理、提出具体反例 |
| `edison` AI迪生 | 给同一个物件找出意外的新用途 |
| `support` AI的供养 | 替 AI 留下具体做对的那一步 |
| `free` AI咋咋地 | 把一个真实决定交出去，或只保留一个例外 |

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
- **ChatGPT 仅用网页工具读到了本页，Python 是空目录或不能联网。** 直接取[本页离线对话画布](#离线对话画布)代码，在已有 Python / 数据分析工具的同一个 notebook 中定义并调用 `puai_card`，将本次核准的原话、所有日期和账传入。无需安装 skill、到 Python 中下载脚本或让用户上传聊天。仅网页阅读器看到代码时，把可读程序写入单元执行。若宿主提供 /mnt/data，调用时传入该目录下的实际 PNG 输出路径，同时得到图片消息和同一张可内嵌的文件。
- **有交互式浏览器和图片附件能力。** 即使没有 Python，也可在 Agent 的新浏览器标签中打开空白[出图页](https://xn--sxrw8m230b.com/PUAI/make/)，把中文报告单填进页面并点「生成长图」。等 `img#preview` 的 `naturalWidth` 为 900，取它的 PNG 图像数据，通过当前对话的图片工具送出。只把空白网址交给导航工具。普通网页搜索器无法执行这一步。
- **在对话里展示。** 输出真实 PNG 后，优先用宿主原生图片消息发出像素。在交互式 Python 单元中可运行 `from render_chat_png import display_chat_png` 后调用 `display_chat_png(path)`。支持 Markdown 图片的本地对话，用图片语法引用真实绝对路径（例如 `![我的年度报告](/实际路径/报告.png)`）。若 ChatGPT 只把工具输出折叠在分析过程里，确认 PNG 已写入，最终回复用图片语法内嵌实际文件，例如 `![我的年度报告](sandbox:/mnt/data/PUAI-2026.png)`。已经显示成图就结束，无需再给下载链接。
- **对话不能展示像素。** 已有成品时先尝试该客户端实际支持的图片附件或富输出。仅当宿主没有可用的图片执行或展示工具，或上面的本地渲染确实失败，才进入网页路径。给一个「打开图片预览」链接，使用官方 A 版网页，由浏览器自动出图。地址从 `https://xn--sxrw8m230b.com/PUAI/make/#p?` 开始。例如已判为 AI因斯坦的单场用 `name=确定的署名&scope=thread&theme=einstein&q=MM-DD~本人逐字原话&days=MM-DD:N:?` 表示可逐条计数的单场精选，替换示意字段为核实的值；只有摘要时用 `lead=具体事实` 替代 q。按需加 setup、tag 等字段，q、tag 可重复。引语可加真实日期前缀 `MM-DD~`，AI 原话用 ai 或 endai。日期账 days 为逐日的 `MM-DD:N:H`，多日用英文逗号分隔；无日期账 undated 为 `N:H`。N 是本人消息数，H 是该组核准命中数，未逐条审完或无主题时填问号。token 为日志整数。用有序键值对编码，所有分享数据仅在 # 后，手工拼接可直接写中文并转义值里的空格、&、#、+、% 和括号。链接直接回给当事人，由对方设备在本地生成 PNG。浏览器请求服务器时不会携带 # 后的数据。助手无需用网页工具打开含原话的链接，也无需把原话提交给任何服务。仅能发文字时，把可点击的本人预览作为这条回复的成品；不要停在报告单、文稿或一段字段。链接里只放已选好、适合本人分享的内容。

交付前看实际成品，数一遍上图原话（新图一至三句，有摘要而无引语时为零），核对成品署名和读到的本人称呼，检查署名旁的类型章是否与所选九型一致，对照原文检查角色和引语，逐一对照私有日期账、每条有依据的引语日期和最终送入渲染器的字段。若日期全丢在中途，补字段后再交图。核对统计分母。转发入口留在图尾。示意与真实报告分清，只在用户要求时使用明确标注的演示资料。

## 离线对话画布

供只有本文和交互式 Python 的宿主。把下面整个函数放进当前数据分析单元，随后在同一内核调用 `puai_card(name=署名, theme=已选类型ID或空串, scope=已核范围, turns=按顺序的原话, days=整批逐日账, dates=另核发言日期, undated=无日期账或None, tokens=核准值或None, tags=标签)`。`turns` 每项是 `(本人或AI, MM-DD或空串, 逐字原文)`。`days` 为日期字符串到 `(当日消息数, 命中数或None)` 的字典。需要旁注可填 `scene`。只有摘要时用核实的现场填 `scene`，留空 `turns`。默认 2026，可传 `year`。文件宿主可同时传真实可写位置 `output` 保留同一成品。函数最后直接发送 `image/png`。若网页工具截断长文件，可单独读[这段代码](https://xn--sxrw8m230b.com/PUAI/notebook_card.py)。

```python
from calendar import monthrange
from collections import Counter
from datetime import date
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import re
from PIL import Image, ImageDraw, ImageFont
from IPython.display import Image as NotebookImage, display

def puai_card(*, name, theme, scope, turns=(), tags=(), days=None, dates=(),
              undated=None, tokens=None, scene="", year=2026, output=None):
    # turns 按现场顺序，每项 (说话人, 当地 MM-DD 或空串, 逐字原话)
    # days 为 {"MM-DD": (当日可数本人消息数, 核准命中数或 None)}
    editions = {
        "puai": ("PUAI", "#16399A", "#F3F6F6", "#C7E1F4"),
        "teach": ("AI的教育", "#087A54", "#FFFFFF", "#99E7B8"),
        "aicu": ("AICU", "#FF8643", "#301B12", "#FFC79E"),
        "all": ("AI特全体", "#A180F5", "#211435", "#D5C7FA"),
        "hush": ("AI在心口难开", "#FFABA3", "#342020", "#FFD2CC"),
        "einstein": ("AI因斯坦", "#32CCDB", "#0C2C34", "#A4EEF0"),
        "edison": ("AI迪生", "#FFCA29", "#302615", "#FFE395"),
        "support": ("AI的供养", "#F16DBD", "#33182C", "#FEC9E3"),
        "free": ("AI咋咋地", "#C8E73F", "#262E14", "#E3F59E"),
        "": ("待定", "#CDD4D6", "#232B30", "#E0E5E4")}
    name = (name or "").strip()
    if not name or re.fullmatch(r'[「“"]?(?:[xｘ×]{3}|叉叉叉)[」”"]?', name, re.I):
        name = "我"
    kind, color, on_color, light = editions[theme or ""]
    ink, paper = "#142238", "#FAFBF7"
    # 本机已装字体或 PyMuPDF 自带的 CJK 字库。全程离线。
    faces = ["NotoSansCJK-Regular.ttc", "wqy-zenhei.ttc", "DroidSansFallbackFull.ttf",
             "/System/Library/Fonts/STHeiti Medium.ttc", "msyh.ttc", "SmileySans-Oblique.woff2"]
    font_file = None
    for path in faces:
        try:
            found = ImageFont.truetype(path, 26)
            if len({bytes(found.getmask(c)) for c in "中文图"}) == 3:
                font_file = found.path
                break
        except OSError:
            pass
    if not font_file:
        try:
            import pymupdf
        except ImportError:
            import fitz as pymupdf
        embedded = pymupdf.Font(fontname="cjk").buffer
    @lru_cache(maxsize=48)
    def font(size):
        return ImageFont.truetype(font_file or BytesIO(embedded), size)
    poster = Image.new("RGB", (900, 5800), paper)
    pen = ImageDraw.Draw(poster)
    def text(x, y, value, size, fill=ink, max_width=804):
        while size > 16 and font(size).getlength(value) > max_width:
            size -= 1
        pen.text((x, y), value, font=font(size), fill=fill, anchor="lt")
    def lines(value, size, width):
        rows, row = [], ""
        for c in value:
            if row and (c == "\n" or font(size).getlength(row+c) > width):
                rows.append(row)
                row = ""
            if c != "\n":
                row += c
        return rows + ([row] if row else [])
    def section(y, value):
        text(48, y, value, 38)
        pen.rectangle((48, y+48, 162, y+54), fill=light)
        return y+74
    def known_day(s):
        return date.fromisoformat(f"{year}-{s}")
    days = {known_day(k): v for k, v in (days or {}).items()}
    observed = {known_day(d) for d in dates} | {known_day(d) for who,d,_ in turns if who == "本人" and d}
    rows = list(days.values()) + ([undated] if undated is not None else [])
    assert all(isinstance(n,int) and n>0 and (h is None or isinstance(h,int) and 0<=h<=n) for n,h in rows)
    assert len(turns) <= 4 and sum(who == "本人" for who,_,_ in turns) <= 3
    assert all(who in ("本人", "AI") and 0 < len(q) <= 80 for who,_,q in turns)
    assert len(scene) <= 90 and len(name) <= 16
    assert tokens is None or isinstance(tokens, int) and tokens >= 0
    pen.rectangle((48, 38, 450, 100), fill=light)
    text(65, 50, name+"的", 38, max_width=367)
    text(478, 52, ("年度类型" if scope=="history" else "本次类型")+" · "+kind, 34, max_width=374)
    title = {"history": kind+" 报告" if kind!="待定" else "AI 相处报告",
             "thread": "单场对话精选", "fragments": "聊天片段精选"}[scope]
    text(48, 134, str(year)+" "+title, 66)
    y = section(245, "对话现场") if turns or scene else 245
    for line in lines(scene, 34, 804):
        text(48, y, line, 34)
        y += 48
    for i, (who, stamp, quote) in enumerate(turns):
        size = 46 if who == "本人" else 34
        x = 48 if who == "本人" else 112
        quote_lines = lines(quote, size, 802-x)
        bottom = y + 76 + (size+15)*len(quote_lines)
        bg, fg = ((color, on_color) if i==0 else (light, ink)) if who=="本人" else (paper, ink)
        if i==2 and who=="本人":
            pen.polygon([(x,y+8),(x+70,y+12),(x+88,y),(x+108,y+12),(820,y+8),
                         (852,y),(844,bottom-18),(852,bottom),(784,bottom-6),(x,bottom)], fill=bg, outline=ink, width=3)
        else:
            pen.rounded_rectangle((x,y,852,bottom), radius=22, fill=bg, outline=ink, width=3)
            pen.polygon([(x+58,bottom-3),(x+42,bottom+14),(x+103,bottom-3)], fill=bg, outline=ink, width=2)
        text(x+26,y+21,who+("  "+stamp.replace("-",".") if stamp else ""),26,fg)
        for j, line in enumerate(quote_lines):
            text(x+26, y+62+j*(size+15), line, size, fg)
        y = bottom+36
    if rows or tokens is not None:
        total = sum(n for n,_ in rows)
        numbers = ([f"{total:,} 条可数指令"] if rows else []) + ([f"{tokens:,} token"] if tokens is not None else [])
        if rows and theme and all(h is not None for _,h in rows):
            metric = "开喷" if theme=="puai" else kind
            numbers.append(f"{metric}约 {sum(h for _,h in rows)/total:.1%}")
        pen.rectangle((48,y,852,y+88),fill=color)
        text(70,y+27," · ".join(numbers),36,on_color,758)
        y += 120
    y = section(y,"发言日历")
    all_dates = sorted(observed | set(days))
    if days:
        peak = max(n for n,_ in days.values())
        label = f"已记账 {len(days)} 天 · 单日最多 {peak} 条"
        if observed-set(days):
            label += f" · 另见 {len(observed-set(days))} 天"
    else:
        label = f"可核实 {len(all_dates)} 个发言日" if all_dates else "这批记录未附发送日期"
    text(48,y,label,32)
    y += 53
    months = Counter(d.month for d in all_dates)
    for slot,m in enumerate(sorted(sorted(months, key=lambda m:(-months[m],m))[:3])):
        left = 48+slot*272
        pen.rounded_rectangle((left,y,left+258,y+208),radius=14,outline=ink,width=2)
        text(left+15,y+15,f"{m:02} 月",31)
        weekday,last = monthrange(year,m)
        for day in range(1,last+1):
            week,col = divmod(weekday+day-1,7)
            d = date(year,m,day)
            cx,cy=left+26+32*col,y+64+24*week
            bounds = (cx-7,cy-7,cx+7,cy+7)
            if d in days:
                pen.ellipse(bounds,outline=ink,fill=ink if days[d][0]>1 else light)
            elif d in observed:
                pen.ellipse(bounds,outline=ink,width=3)
            else:
                pen.ellipse(bounds,outline="#A7AEB3",width=1)
    if months:
        y += 226
        text(48,y,"浅色 1 条 · 深色多条 · 粗圈仅核到日期 · 灰圈缺记录",25)
        y += 45
    if tags:
        y = section(y+15, "人格标签" if scope=="history" else "片段标签")
        for i,tag in enumerate(tags[:3]):
            x=48+i*272
            pen.rectangle((x,y,x+258,y+65),fill=light,outline=ink,width=2)
            text(x+16,y+18,tag,30,max_width=226)
        y += 100
    pen.line((48,y,852,y), fill=ink,width=2)
    text(48,y+50,"扫码获取口令",43,max_width=575)
    text(48,y+106,"发给自己的 Agent 总结出图。",35,max_width=575)
    qr = "1fc08c87f 105b77041 174ab2b5d 175e3555d 175e3865d 104796541 1fd55557f 1284200 bd81d2da 7851fa1c bd61061f 12b696ea7 1e6fda9f0 10e1f1a8 ef5bf45c 1a0125695 1bfed05f8 2b6e61d5 1d404fe2d c102d41c ad13afba 1d34bc238 147a53603 12871b037 1e718c7f7 1991d16 1fc53b354 1057ecd1c 17578aff2 175968ead 17440ecbf 105e870ff 1fcc7e37c"
    pen.rectangle((647,y+16,852,y+221),fill="white")
    for r,bits in enumerate(qr.split()):
        for c in range(33):
            if int(bits,16) & (1 << (32-c)):
                x, top = 667+c*5, y+36+r*5
                pen.rectangle((x,top,x+4,top+4),fill=ink)
    result = BytesIO()
    poster.crop((0,0,900,y+242)).save(result, format="PNG")
    pixels = result.getvalue()
    if output is not None:
        Path(output).write_bytes(pixels)
    display(NotebookImage(data=pixels,format="png"), include=["image/png"])
```
