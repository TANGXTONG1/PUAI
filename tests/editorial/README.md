# 选材与文案回归

`synthetic-contexts.json` 含 12 位虚拟用户的合成材料，其中 9 份覆盖九种主题，另 3 份测试只有摘要、素材平淡和容易误读的情况。每次只把一个 ID 的上下文和待测口令发给独立会话。把返回的备用码整理成一个 JSON 对象，键为匿名 ID，值为完整单行报告码。

从仓库根目录运行：

```sh
node tests/editorial/audit.mjs /path/to/codes.json
node --test tests/editorial/audit.test.mjs
```

`review-key.json` 只给验收者。自动检查复用出图页的解析器，核对主题、每日与总发言数、引语逐字出处及日期。材料未标注逐条命中，因此各日主题命中需要人工复核。

试读时逐份随机交换新旧报告的左右顺序，隐藏版本标记。让评审选想发给朋友的那份，允许平手或两份都不选，并摘出自己记住的那句话。最后用判分依据中的 `actions` 和 `avoid` 对照事实、被引者及跨回合因果。所有对话和人物仅作测试使用。

## 文字客户端到图片

`portable-replies.json` 是独立 Codex 会话对合成材料的实际答复。分别覆盖只有一段可核原话、只有记忆摘要与有完整日期账的双方对话。以下测试将回复原文连同围栏、操作说明和固定网址一起交给出图页，核对原话先后、缺失统计和下载的 PNG。

```sh
python3 -m unittest discover -s tests -p test_portable_images.py -v
```

需要 Python Playwright 及其 Chromium、WebKit、Firefox 浏览器。移动设备配置检查浏览器渲染；ChatGPT 等原生 App 的验收还需在该 App 内实际发送口令、复制回复并保存图片。拒绝剪贴板权限、旧空链接和刷新恢复另见 `tests/clipboard-handoff.test.mjs`。
