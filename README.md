<p align="center">
  <img src="docs/readme-header.svg" width="960" alt="PUAI · 2026 AI 年度报告">
</p>

<p align="center">
  从你和 AI 的聊天里挑出年度人格，用你的原话做成长图。<br>
  你是给 AI 上课，给 AI 挂急诊，还是花会员费给 AI 提供情绪价值？
</p>

<p align="center">
  <a href="https://xn--sxrw8m230b.com/PUAI/"><strong>在线入口</strong></a>
  &nbsp; · &nbsp;
  <a href="https://xn--sxrw8m230b.com/PUAI/PUAI-skill.zip?v=84205cab92">下载 skill</a>
  &nbsp; · &nbsp;
  <a href="https://xn--sxrw8m230b.com/PUAI/themes/">九种报告图鉴</a>
  &nbsp; · &nbsp;
  <a href="SKILL.md">Skill 说明</a>
</p>

## 开始使用

把 `XXX` 换成你的昵称，复制给能读取链接、运行代码的 Agent：

```text
叫我「XXX」，生成我调教 AI 的年度报告长图。
参考该 skill：https://github.com/TANGXTONG1/PUAI
```

<details>
<summary>通过命令行安装</summary>

```bash
npx skills add TANGXTONG1/PUAI
```

已安装时：`叫我「XXX」，用 PUAI 生成我的年度报告长图。`

</details>

Agent 无法访问你的历史时，上传聊天导出文件即可。生成在你的 Agent 环境中完成。

## 你的年度人机关系

从反复出现的相处方式里挑一个主题，再用你的原话做成报告。PUAI 看你怎样给 AI 施压，「AI 的教育」看你怎样举例让它学会，「AI 特全体」看你怎样让几个模型互评。

[![九种 A 版长图的标题与金句](docs/themes/overview.png?v=ffef27aa57)](https://xn--sxrw8m230b.com/PUAI/themes/)

[打开图鉴，查看并保存九张完整长图](https://xn--sxrw8m230b.com/PUAI/themes/)

## 不愿透露姓名的唐某的 PUAI 报告

<p align="center">
  <a href="https://xn--sxrw8m230b.com/PUAI/preview.png">
    <img src="docs/preview.png" width="520" alt="不愿透露姓名的唐某的 2026 PUAI 报告：token 用量、开喷比例、发言日历、原话金句和用户人格">
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
