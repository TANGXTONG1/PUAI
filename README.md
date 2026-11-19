<p align="center">
  <img src="docs/readme-header.svg" width="960" alt="PUAI · 2026 AI 年度报告">
</p>

<p align="center">
  从你和 AI 的聊天里挑出金句，做一张带人格标签的年度报告。<br>
  你是给 AI 上课，给 AI 挂急诊，还是花会员费给 AI 提供情绪价值？
</p>

<p align="center">
  <a href="https://xn--sxrw8m230b.com/PUAI/"><strong>复制口令做同款</strong></a>
  &nbsp; · &nbsp;
  <a href="https://xn--sxrw8m230b.com/PUAI/PUAI-skill.zip?v=87f27a577d">下载 skill</a>
  &nbsp; · &nbsp;
  <a href="https://xn--sxrw8m230b.com/PUAI/themes/">九种报告图鉴</a>
  &nbsp; · &nbsp;
  <a href="https://xn--sxrw8m230b.com/PUAI/palettes/atlas/">48 款配色样刊</a>
  &nbsp; · &nbsp;
  <a href="SKILL.md">Skill 说明</a>
</p>

## 开始使用

扫长图底部的二维码，或打开首页点「复制给 ChatGPT」。把口令粘贴到一段已有聊天里，点它回的「打开我的报告」，就能保存一张带本人原话和人格标签的 PNG。新对话里贴几句自己的原话也可以。[复制生成口令](https://xn--sxrw8m230b.com/PUAI/) · [查看文字口令](https://xn--sxrw8m230b.com/PUAI/go.txt)

如果聊天软件把链接显示成了普通文字，把回复里的备用报告码粘到生成页即可。[粘贴报告码](https://xn--sxrw8m230b.com/PUAI/make/)

<details>
<summary>用完整版 skill 生成发言日历和用量统计</summary>

把下面这句发给能访问仓库、运行代码的 Agent：

```text
用 PUAI 把我和 AI 的聊天做成一张年度报告长图。 https://github.com/TANGXTONG1/PUAI
```

也可以运行 `npx skills add TANGXTONG1/PUAI` 安装。用量和日历按你授权提供的聊天及日志生成。

</details>

## 你的年度人机关系

先看你反复怎么用 AI，再挑最能体现这种人格的原话。PUAI 看你怎样给 AI 施压，「AI 的教育」看你怎样举例让它学会，「AI 特全体」看你怎样让几个模型互评。

[![九种 A 版长图的标题与金句](docs/themes/overview.png?v=ffef27aa57)](https://xn--sxrw8m230b.com/PUAI/themes/)

[打开图鉴，查看并保存九张完整长图](https://xn--sxrw8m230b.com/PUAI/themes/) · [九种人机关系的亮底轻赛博色样](https://xn--sxrw8m230b.com/PUAI/palettes/neon/nine/)

[轻赛博配色 · 8 张高对比报告](https://xn--sxrw8m230b.com/PUAI/palettes/neon/) · [艺术配色样刊 · 同一张报告的 16 种印色](https://xn--sxrw8m230b.com/PUAI/palettes/art/)

## 不愿透露姓名的唐某的 PUAI 报告

<p align="center">
  <a href="https://xn--sxrw8m230b.com/PUAI/persona-report.png?v=b57d3efa3e">
    <img src="docs/persona-report.png?v=b57d3efa3e" width="520" alt="不愿透露姓名的唐某的 2026 PUAI 报告：用户人格、开喷比例、发言日历、原话和标签">
  </a>
</p>

<p align="center">
  <a href="https://xn--sxrw8m230b.com/PUAI/sample.html">查看完整报告</a>
</p>

原话只精选，不改写；没有记录不编数字；私人工作背景不上图。每个人的金句和标签都取自自己的记录。

<details>
<summary>给 Agent：运行环境与生成流程</summary>

读取 [SKILL.md](SKILL.md)，按其中流程整理用户授权的记录，再运行：

```bash
python3 scripts/build_report.py --input /path/to/report.json --style comic --output /path/to/share.html
node scripts/export_png.mjs --input /path/to/share.html --output /path/to/share.png
```

Python 3.9+、Node.js 20+、Playwright 和 Chromium；缺少依赖时见 [PNG 导出说明](references/png-export.md)。输入格式见 [report-schema.md](references/report-schema.md)，无需用户手填。

字体得意黑 Smiley Sans 随包保留 [OFL 许可](assets/SmileySans-OFL.txt)。独立创意项目。

</details>
