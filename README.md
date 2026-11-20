<p align="center">
  <a href="https://xn--sxrw8m230b.com/PUAI/"><img src="docs/readme/cover.png" width="1080" alt="2026 你和 AI 的年度相处报告。AICU、AI的供养与唐某的 PUAI 三份报告样张。"></a>
</p>

<p align="center">
  <a href="https://xn--sxrw8m230b.com/PUAI/"><img src="docs/readme/start.png" width="220" height="44" alt="做我的年度报告"></a>
</p>

把口令发给 ChatGPT，它会从可用的历史、记忆或项目里找出你和 AI 的相处习惯。点回复里的链接，保存自己的长图。只有行为摘要也能生成；金句只用能核对的本人原话。[粘贴备用报告码](https://xn--sxrw8m230b.com/PUAI/make/) · [查看文字口令](https://xn--sxrw8m230b.com/PUAI/go.txt)

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

装好后说「用 PUAI 生成我的年度报告」。有可靠的时间戳和 token 日志时，完整版还能画出发言日历和用量统计。[下载 skill](https://xn--sxrw8m230b.com/PUAI/PUAI-skill.zip?v=ca468f9bf1) · [阅读 SKILL.md](SKILL.md)

<details>
<summary>生成命令与运行环境</summary>

```sh
python3 scripts/build_report.py --input /path/to/report.json --style comic --output /path/to/share.html
node scripts/export_png.mjs --input /path/to/share.html --output /path/to/share.png
```

需要 Python 3.9+、Node.js 20+、Playwright 和 Chromium。[输入格式](references/report-schema.md) · [PNG 导出](references/png-export.md)

</details>

<details>
<summary>样刊、配色与字体</summary>

[九份完整报告](https://xn--sxrw8m230b.com/PUAI/themes/) · [九型色样](https://xn--sxrw8m230b.com/PUAI/palettes/neon/nine/) · [亮底霓虹](https://xn--sxrw8m230b.com/PUAI/palettes/neon/) · [艺术印色](https://xn--sxrw8m230b.com/PUAI/palettes/art/) · [48 款配色](https://xn--sxrw8m230b.com/PUAI/palettes/atlas/)

报告标题使用得意黑 Smiley Sans。[字体许可](assets/SmileySans-OFL.txt)

</details>
