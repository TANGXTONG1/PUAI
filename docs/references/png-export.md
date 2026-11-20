# PNG 导出

`scripts/export_png.mjs` 将报告的 `#poster` 完整画布导出为 900 px 宽 PNG；不是截取网页可见区域，高度随内容变化。支持 A 版及其他紧凑模板，不适用于旧多页模板。

先生成 HTML，再导出：

```bash
python3 scripts/build_report.py --input /path/report.json --style comic --output /path/report.html
node scripts/export_png.mjs --input /path/report.html --output /path/report.png --mobile-preview /path/report-mobile.png
```

需要 Node.js 20+、`playwright` 或 `playwright-core`，以及 Chrome、Edge 或 Chromium。导出器先尝试 Playwright 自带浏览器，再找常见系统安装位置；不会安装依赖或修改日常浏览器配置。

已有依赖在其他目录时传 `--module-root /path/to/node_modules`。没有依赖时，可在临时工作目录安装 `playwright-core`，不改全局配置：

```bash
npm install --prefix /path/to/temporary-dependencies playwright-core
node scripts/export_png.mjs --input /path/report.html --output /path/report.png --module-root /path/to/temporary-dependencies/node_modules
```

自动发现不了浏览器时加 `--browser /path/to/chrome-or-edge`。Windows 路径有空格时加引号。Linux 需有可用中文系统字体，例如 Noto Sans CJK；嵌入的展示字体不能替代全部正文字体。

脚本等待字体和图像生成，阻止外网请求，检查 JavaScript 错误、画布尺寸及 390 px 手机横向溢出。它不判断文案是否真实或视觉是否好看；交付前打开 PNG 与可选手机预览，检查字形、署名居中、贴纸内原句是否完整、字体大小和间距。输出文件权限按私人材料设置，不会上传。

没有可用 Node/Playwright 时，可用宿主浏览器打开 HTML，等待生成后点击「保存长图」。不要以网页截图代替最终原始 PNG，也不要声称未实际导出的图片已经生成。

## 在对话里显示图片

用网页工具读取远程 skill 的 ChatGPT 也可能有可执行 Python 的数据分析工具。先实际调用它。若内核没有随包文件，将 SKILL.md 末尾的「离线对话画布」各段顺序写入同一个 Python 文件，导入 `show_puai`，把中文报告单传给它。与命令行共用同一个 A 版绘图函数。消息、日期和图片留在内核内，Python 无需联网。程序使用本机可读中文字体，也支持从已装 PyMuPDF 读取内置 CJK 字体。输出为 MIME 类型 `image/png` 的像素。ChatGPT 有 /mnt/data 时同时传 `output="/mnt/data/PUAI-2026.png"`（同名文件已存在时换新文件名），令回复正文也能内嵌同一张图。安装版的入口在 `scripts/notebook_card.py`；在线另有[完整可执行单文件](https://xn--sxrw8m230b.com/PUAI/notebook_card.py)。

有原生图片输出工具时，直接发送成品 PNG 的图像数据。交互式 Python 宿主可在生成报告的同一个 notebook 单元或后续单元运行以下代码。将脚本所在目录加入导入路径，文件名使用实际成品。

```python
from render_chat_png import display_chat_png

display_chat_png("/mnt/data/PUAI-2026.png")
```

这是 notebook 的图片输出步骤，在独立 shell 子进程里运行不会生成对话预览。脚本不可导入时，用 IPython 的 `display(Image(filename=path))` 显示相同的 PNG。宿主需要在回复正文引用文件时，把真实成品写成 `![我的年度报告](sandbox:/mnt/data/PUAI-2026.png)`。已展示的图片无需再配一个文件下载链接。

只有文件下载或文字能力时，用含本人数据的网页直达链接「打开图片预览」。网页载入即显示整张图，读者可以选择保存。
