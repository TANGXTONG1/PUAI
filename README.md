# PUAI

[在线入口：填写昵称，复制口令](https://xn--sxrw8m230b.com/PUAI/)

把你的 AI 对话做成一张年度报告：token 用量、开喷比例、发言日历、原话金句和用户人格。默认红白漫画 A 版，导出手机可读的 PNG 长图。

## 分享与使用

把 `XXX` 换成你的分享昵称，发给能读取链接、执行代码并输出文件的 Agent：

```text
https://github.com/TANGXTONG1/PUAI
叫我「XXX」，生成我的 PUAI 年度报告长图。
```

[下载 skill](docs/PUAI-skill.zip) · [打开样例](docs/preview.png) · [完整规则](SKILL.md)

也可以通过 [skills CLI](https://github.com/vercel-labs/skills) 安装：

```bash
npx skills add TANGXTONG1/PUAI
```

已安装时：`叫我「XXX」，用 PUAI 生成我的年度报告长图。`

Agent 无法访问你的历史时，把聊天导出文件交给它。托管页提供口令、skill 和样例，生成在你的 Agent 环境中完成。

原话只精选，不改写；没有记录不编数字；私人工作背景不上图。公开样例是虚拟人物与合成统计，金句摘自不同作者的真实公开发言，出处见 [样例说明](docs/sample.html)。

## 给 Agent 的入口

读取 [SKILL.md](SKILL.md)，按其中流程整理用户授权的记录，再运行：

```bash
python3 scripts/build_report.py --input /path/to/report.json --style comic --output /path/to/share.html
node scripts/export_png.mjs --input /path/to/share.html --output /path/to/share.png
```

Python 3.9+、Node.js 20+、Playwright 和 Chromium；缺少依赖时见 [PNG 导出说明](references/png-export.md)。输入格式见 [report-schema.md](references/report-schema.md)，无需用户手填。

字体得意黑 Smiley Sans 随包保留 [OFL 许可](assets/SmileySans-OFL.txt)。独立创意项目，非网易云音乐官方产品。
