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
