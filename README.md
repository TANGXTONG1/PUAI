<p align="center">
  <a href="https://xn--sxrw8m230b.com/PUAI/">
    <img src="docs/readme-header.svg?v=5a0709019b" width="1000" alt="PUAI · 2026 你和 AI 的年度相处报告">
  </a>
</p>

有人拿到答案先找反例，有人付了会员费还要哄模型开心。PUAI 从你和 AI 的聊天里找出反复出现的习惯，用你的原话和人格标签做成一张年度长图。

**[复制给 ChatGPT，生成我的报告 →](https://xn--sxrw8m230b.com/PUAI/)**

把口令粘进平时聊天的那段对话，点它回复的「打开我的报告」即可保存 PNG。新对话里也可以贴几句自己的原话。如果链接打不开，把回复里的备用码粘到生成页。[粘贴报告码](https://xn--sxrw8m230b.com/PUAI/make/) · [查看文字口令](https://xn--sxrw8m230b.com/PUAI/go.txt)

## 九种年度相处方式

| 主题样张 | 聊天里常见的动作 |
| --- | --- |
| [AI因斯坦](https://xn--sxrw8m230b.com/PUAI/themes/#einstein) | 问完出处问反例，一个回答得过两轮答辩。 |
| [AI迪生](https://xn--sxrw8m230b.com/PUAI/themes/#edison) | 第一个点子还没取名，第三个已经通电。 |
| [AI的教育](https://xn--sxrw8m230b.com/PUAI/themes/#teach) | AI 答错一道题，你补一页教案。 |
| [AI特全体](https://xn--sxrw8m230b.com/PUAI/themes/#all) | 一道题发给三家，顺手让它们互相批改。 |
| [AICU](https://xn--sxrw8m230b.com/PUAI/themes/#aicu) | 截止时间按分钟倒数，轮到 AI 值急诊。 |
| [AI在心口难开](https://xn--sxrw8m230b.com/PUAI/themes/#hush) | 心里有八百字，发出去得像随口一说。 |
| [AI的供养](https://xn--sxrw8m230b.com/PUAI/themes/#support) | 会员费你付，情绪价值也你给。 |
| [AI咋咋地](https://xn--sxrw8m230b.com/PUAI/themes/#free) | 连「要不要问我」这件事，也交给 AI 拍板。 |
| [PUAI](https://xn--sxrw8m230b.com/PUAI/themes/#puai) | 愿意给 AI 花 token，也随时准备找它退款。 |

唐某这份用了本人原话，其余八份是场景样例。做你的报告时，金句取自你自己的聊天，按原文上图。[打开九份报告图鉴](https://xn--sxrw8m230b.com/PUAI/themes/)

<details>
<summary>看唐某的完整长图</summary>

<p>
  <a href="https://xn--sxrw8m230b.com/PUAI/sample.html">
    <img src="docs/persona-report.png?v=b57d3efa3e" width="440" alt="不愿透露姓名的唐某的 2026 PUAI 报告，含发言日历、本人原话和人格标签">
  </a>
</p>

[查看与下载原图](https://xn--sxrw8m230b.com/PUAI/sample.html)

</details>

## 用完整版 skill 加上日历和用量

能读取聊天记录并运行代码的 Agent，可从你授权的记录生成发言日历。有可靠的用量日志时，报告还会显示 token 用量。[下载 PUAI skill](https://xn--sxrw8m230b.com/PUAI/PUAI-skill.zip?v=87f27a577d)

```sh
npx skills add TANGXTONG1/PUAI
```

装好后说一句「用 PUAI，把我和 AI 的聊天做成年度报告」。能读取仓库链接的 Agent 也可以直接使用 [SKILL.md](SKILL.md)。

<details>
<summary>生成命令与运行环境</summary>

```sh
python3 scripts/build_report.py --input /path/to/report.json --style comic --output /path/to/share.html
node scripts/export_png.mjs --input /path/to/share.html --output /path/to/share.png
```

需要 Python 3.9+、Node.js 20+、Playwright 和 Chromium。Agent 按说明整理输入，自行生成长图。[输入格式](references/report-schema.md) · [PNG 导出](references/png-export.md)

</details>

<details>
<summary>配色与字体</summary>

[九种主题色样](https://xn--sxrw8m230b.com/PUAI/palettes/neon/nine/) · [亮底霓虹](https://xn--sxrw8m230b.com/PUAI/palettes/neon/) · [艺术印色](https://xn--sxrw8m230b.com/PUAI/palettes/art/) · [48 款配色样刊](https://xn--sxrw8m230b.com/PUAI/palettes/atlas/)

标题使用得意黑 Smiley Sans。[字体许可](assets/SmileySans-OFL.txt)

</details>
