<p align="center">
  <a href="https://xn--sxrw8m230b.com/PUAI/"><img src="docs/readme/cover.png" width="1080" alt="2026 你和 AI 的年度相处报告。AICU、AI的供养与唐某的 PUAI 三份报告样张。"></a>
</p>

<p align="center">
  <a href="https://xn--sxrw8m230b.com/PUAI/"><img src="docs/readme/start.png" width="220" height="44" alt="做我的年度报告"></a>
</p>

扫码获取口令，发给自己的 Agent 总结出图。想换署名就在复制前填昵称，留空会沿用你在聊天里认可的称呼。[领取生成口令](https://xn--sxrw8m230b.com/PUAI/#go)

九种人格各有一套固定配色。**PUAI** 用钴蓝和荧光黄，**AI因斯坦** 用青蓝和淡蓝紫。报告从类型标题和本人原话开场，接发言统计、日历和人格标签。单场精选会在标题下注明范围。[看九型对话出图色样](https://xn--sxrw8m230b.com/PUAI/themes/inline-editions.png)

把口令发进常用对话。能运行官方模板、也支持图片展示时，可以在对话里直接看到 PNG。只有绘图或文字工具时，口令会要求返回专属预览链接，点开就能看到同一套版式。

选原话时会把不同聊天里的几件事放在一起，回原文看你接下来怎么说。续聊和分支里重放的老话只算同一件事。同机有多个账号时按本人账号取材。

日历按原消息的发送时间统计。有历史工具时会跨月翻原对话，截图和附件也算一次发言。只找到零散片段时，日历标出已核实的日期。有现成的 ChatGPT 聊天导出（JSON 或 ZIP），也可在支持文件的对话中用它核对整个导出范围。

如果助手打不开技能链接，可把[技能说明文件](https://xn--sxrw8m230b.com/PUAI/skill.txt)作为附件发给它，再发同一句口令。

## 翻三张场景样刊

<p align="center">
  <a href="https://xn--sxrw8m230b.com/PUAI/themes/#aicu"><img src="docs/readme/aicu.png" width="248" alt="AICU 场景样刊，最后一分钟还要换字体。查看完整长图。"></a>
  <a href="https://xn--sxrw8m230b.com/PUAI/themes/#einstein"><img src="docs/readme/einstein.png" width="248" alt="AI因斯坦场景样刊，一个新名词引出一场追问。查看完整长图。"></a>
  <a href="https://xn--sxrw8m230b.com/PUAI/themes/#support"><img src="docs/readme/support.png" width="248" alt="AI的供养场景样刊，付了会员费还得安慰模型。查看完整长图。"></a>
</p>

还有六种相处方式可以翻。点主题看完整报告。

[AI迪生 · 脑洞接力](https://xn--sxrw8m230b.com/PUAI/themes/#edison)　[AI特全体 · 模型互评](https://xn--sxrw8m230b.com/PUAI/themes/#all)　[AI的教育 · 给它补课](https://xn--sxrw8m230b.com/PUAI/themes/#teach)<br>
[AI在心口难开 · 措辞代练](https://xn--sxrw8m230b.com/PUAI/themes/#hush)　[AI咋咋地 · 你来拍板](https://xn--sxrw8m230b.com/PUAI/themes/#free)　[PUAI · 在线追责](https://xn--sxrw8m230b.com/PUAI/themes/#puai)

## 唐某的两笔 token 账

<p>
  <a href="https://xn--sxrw8m230b.com/PUAI/sample.html"><img src="docs/readme/tang-excerpt.png" width="540" alt="不愿透露姓名的唐某的两条本人原话。11 月 7 日：多调研点啊，我缺你这点 token 吗？做一小会就停下是几个意思？11 月 10 日：浪费我的 token， 赔钱！"></a>
</p>

[看不愿透露姓名的唐某的完整报告 ↗](https://xn--sxrw8m230b.com/PUAI/sample.html)

## 用自己的 Agent 生成

```sh
npx skills add TANGXTONG1/PUAI
```

装好后直接唤起，也可以把「小栗」换成自己的昵称。

> 用 $puai 整理我的 2026 聊天，署名「小栗」。运行官方模板在对话里显示 PNG，跑不了就给我的预览链接。

Agent 可以在本地核对获准读取的记录并导出 PNG。有日期就能画发言日历，有用量日志还能查那段时间烧了多少 token。[下载 skill](https://xn--sxrw8m230b.com/PUAI/PUAI-skill.zip?v=fb8f45e7be) · [阅读 SKILL.md](SKILL.md)

<details>
<summary>生成命令与运行环境</summary>

```sh
python3 scripts/build_report.py --input /path/to/report.json --style comic --output /path/to/share.html
node scripts/export_png.mjs --input /path/to/share.html --output /path/to/share.png
```

以上命令使用 Python、Node.js、Playwright 与 Chromium。有 Python、Pillow 和中文字体的文件环境还可以独立运行 `python scripts/render_chat_png.py report.txt PUAI-2026.png`。[输入格式](references/report-schema.md) · [PNG 导出](references/png-export.md)

</details>

<details>
<summary>样刊、配色与字体</summary>

[九份完整报告](https://xn--sxrw8m230b.com/PUAI/themes/) · [九型配色总览](https://xn--sxrw8m230b.com/PUAI/themes/overview.png?v=116bfc4e0a) · [历次试色](https://xn--sxrw8m230b.com/PUAI/palettes/neon/nine/) · [亮底霓虹](https://xn--sxrw8m230b.com/PUAI/palettes/neon/) · [艺术印色](https://xn--sxrw8m230b.com/PUAI/palettes/art/) · [48 款配色](https://xn--sxrw8m230b.com/PUAI/palettes/atlas/)

报告标题使用得意黑 Smiley Sans。[字体许可](assets/SmileySans-OFL.txt)

</details>

<details>
<summary>查看按钮点击人数</summary>

在主站的 [Google Analytics](https://analytics.google.com/) 打开「事件」报告，按事件名称搜索 `puai_`。看「总用户数」了解所选日期内点过该按钮的去重人数，「事件数」是总点击次数。想知道多少人领过口令，看 `puai_copy_prompt`。

| 按钮 | 事件 |
| --- | --- |
| 复制生成口令 | `puai_copy_prompt` |
| 下载 skill | `puai_download_skill` |
| 手动生成长图 | `puai_generate_report` |
| 保存长图 | `puai_save_report` |
| 转发长图或复制转发语 | `puai_share_report` |

统计覆盖同意统计的网页访客。同一人换浏览器或设备可能分别计数，同一人点多个按钮也会出现在多行。Agent 内直接出图、长按存图均在网页统计范围外。

</details>
