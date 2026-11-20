import assert from 'node:assert/strict';
import test from 'node:test';
import { parsePlainReport } from '../docs/make/plain-report.mjs';
import { parseReport } from '../docs/make/report-code.mjs';

const quoted = '格子里有 52% 的蓝色？(真的)  A｜B';
const full = [
  'PUAI 2026', '署名：小陈', '主题：AI因斯坦', '短评：又给标准答案出了一题。',
  '用法：把格子数量和颜色面积分开问', '前情：先看一张转盘。',
  '原话：03-08~格子数还是面积？', 'AI：我数的是格子。', '原话：03-09~' + quoted,
  '日期账：03-08:2:1,03-09:3:2', '无日期账：1:?', 'Token：438',
  '标签：出题人、再问一格',
];
test('共享入口字段映射与已有有账报告的计数、引语、插话完全一致', () => {
  const expected = parseReport(['v2','einstein','小陈','又给标准答案出了一题。',
    '03-08:2:1,03-09:3:2','1:?','438','把格子数量和颜色面积分开问','','',
    '03-08~格子数还是面积？','03-09~'+quoted,'','出题人','再问一格','','先看一张转盘。','1~我数的是格子。']);
  assert.deepEqual(parsePlainReport(full.join('\n')), expected);
});

test('占位符和空署名用「我」兜底，保留用户选定的昵称', () => {
  for (const [input, expected] of [['XXX','我'],['「xXx」','我'],['ＸＸＸ','我'],['×××','我'],['','我'],['Ｘ某','Ｘ某'],['梦XXX','梦XXX']]) {
    assert.equal(parsePlainReport('PUAI 2026\n署名：' + input + '\n原话：谁来付账？').person.name, expected);
  }
});

test('整条聊天复制包含空链接、单独静态网址、加粗标签、围栏和前后说明', () => {
  const reply = ['本次可以查到两段。','[查看并保存长图]()','```text','**PUAI 2026**',
    '- **署名**：小白', '- **原话：** 两次都说「等一下」？','```',
    'https://example.org/make/','署名：这是聊天按钮下面的内容。','给朋友转发。'].join('\r\n');
  const result = parsePlainReport(reply);
  assert.equal(result.person.name,'小白');
  assert.deepEqual(result.activity.share_quotes,[{text:'两次都说「等一下」？'}]);
  assert.equal(result.activity.summary,undefined);
  assert.equal(result.activity.days,undefined);
  assert.equal(parsePlainReport('[查看并保存长图]()'),null);
});

test('日期不齐的已核实片段可以携带真实原话和相邻 AI 回复，无分母也不补计数', () => {
  const result = parsePlainReport(['> ## PUAI 2026','> 原话：03-08~格子数还是面积？','> AI：我数的是格子。',
    '> 原话：'+quoted,'> 标签：出题人','> 标签：补考','报告结束'].join('\n'));
  assert.equal(result.year,2026);
  assert.equal(result.theme,null);
  assert.deepEqual(result.activity.share_quotes,[{date:'2026-03-08',text:'格子数还是面积？'},{text:quoted}]);
  assert.deepEqual(result.story.assistant_reply,{after_quote:1,text:'我数的是格子。'});
  for (const name of ['summary','rhythm','days','months','theme_stats']) assert.equal(result.activity[name],undefined);
  assert.equal(result.activity.daily_profile.dated_messages,undefined);
  assert.equal(result.activity.daily_profile.undated_messages,undefined);
  assert.equal(result.activity.daily_profile.active_days,undefined);
  assert.deepEqual(result.keywords,['出题人','补考']);
});

test('只有具体行为摘要也能出卡；未知散文、声明、单独标题不能冒充消息', () => {
  const report = parsePlainReport('PUAI 2026\n我觉得他很聪明。\n**用法**: 会把两个答案并排找差异。\nhttps://example.org/');
  assert.deepEqual(report.activity.daily_profile.habits,['会把两个答案并排找差异。']);
  assert.deepEqual(report.activity.share_quotes,[]);
  assert.throws(() => parsePlainReport('PUAI 2026\n短评：聪明人\n标签：懂行\n“给个漂亮的总结”'),/习惯|用法|原话/);
  assert.equal(parsePlainReport('这次生成的是 PUAI 2026，我会看情况分享。'),null);
});

test('部分有账的报告不能把漏数的片段塞进已核对样本', () => {
  assert.throws(() => parsePlainReport('PUAI 2026\n原话：01-02~格子数还是面积？\n日期账：01-03:2:?'),/日期/);
  assert.throws(() => parsePlainReport('PUAI 2026\n原话：格子数？\n原话：面积？\n无日期账：1:?'),/原话/);
  assert.throws(() => parsePlainReport('PUAI 2026\n用法：核算格子\n日期账：03-08:1:2'),/命中数/);
  assert.throws(() => parsePlainReport('PUAI 2026\n原话：02-29~格子数还是面积？'),/日期/);
  assert.equal(parsePlainReport('PUAI 2026\n原话：格子数？\nAI：三个。').story.assistant_reply,undefined);
  assert.throws(() => parseReport(['v2','','我','','','','','','','','格子数？','','','','','']),/习惯|发言/);
});

test('单值不互相覆盖，超出支持数量不悄悄拼接', () => {
  assert.throws(() => parsePlainReport('PUAI 2026\n署名：A\n署名：B\n用法：检查格子'),/署名/);
  assert.deepEqual(parsePlainReport('PUAI 2026\n'+['A','B','C','D'].map(x=>'原话：'+x).join('\n')).activity.share_quotes.map(q=>q.text),['A','B','C','D']);
  assert.deepEqual(parsePlainReport('PUAI 2026\n原话：x\nAI：a\n原话：y\nAI：b\n原话：z').story.assistant_reply,{after_quote:1,text:'a'});
});

test('常见的未知统计标记等同缺省，仍严格校验所写的数值', () => {
  const lead = 'PUAI 2026\n原话：只数蓝色的，再换一个分母。';
  const base = parsePlainReport(lead);
  assert.deepEqual(parsePlainReport(lead+'\n日期账：（无法逐条核准）\n无日期账：—\nToken：N/A'),base);
  assert.throws(() => parsePlainReport(lead+'\n无日期账：0:0'),/大于零/);
  assert.throws(() => parsePlainReport(lead+'\nToken：10万左右'),/整数/);
});

test('额外的收尾 AI 不会阻断三条本人发言和两日的发言账', () => {
  const receipt=['PUAI 2026','主题：free','前情：'+'太长了'.repeat(9),'原话：11-04~铃声你定。',
    'AI：海浪还是鸟叫？','原话：11-04~你来选。','原话：11-07~今天也交给你。',
    'AI：鸟叫。','日期账：11-04:2:2,11-07:1:1'].join('\n');
  const {story,activity}=parsePlainReport(receipt);
  assert.deepEqual(story.assistant_reply,{after_quote:1,text:'海浪还是鸟叫？'});
  assert.equal(story.quote_setup,undefined);
  assert.deepEqual(activity.share_quotes.map(q=>q.text),['铃声你定。','你来选。','今天也交给你。']);
  assert.equal(activity.summary.messages,3);
  assert.equal(activity.daily_profile.active_days,2);
});

test('不拼接多条连续 AI，也不把隔着场景标题的答复夹进对话', () => {
  const report = parsePlainReport('PUAI 2026\nAI：开场\n原话：x\nAI：a\nAI：b\n原话：y\nAI：c\n下一次\n原话：z');
  assert.equal(report.story.assistant_reply,undefined);
  assert.equal(parsePlainReport('PUAI 2026\n用法：根据声音挑闹钟。\n前情：先听听。').story.quote_setup,undefined);
});

test('第四条原话与原线程中紧邻的 AI 可以入图，用法和标签仍精选三项', () => {
  const plain = ['PUAI 2026', '原话：第一句','原话：第二句','原话：第三句',
    'AI：答第三句。','原话：第四句', '标签：甲、乙、丙、丁',
    ...['一','二','三','四'].map(s=>'用法：'+s), '日期账：06-10:4:?'].join('\n');
  const {activity,story,keywords}=parsePlainReport(plain);
  assert.deepEqual(activity.share_quotes.map(q=>q.text),['第一句','第二句','第三句','第四句']);
  assert.deepEqual(keywords,['甲','乙','丙']);
  assert.deepEqual(activity.daily_profile.habits,['一','二','三']);
  assert.deepEqual(story.assistant_reply,{after_quote:3,text:'答第三句。'});
  assert.equal(activity.summary.messages,4);
});

test('date-only evidence survives a pasted receipt alongside six quotes', () => {
  const card = parsePlainReport('PUAI 2026\n发言日期：03-01,04-05,03-01\n' +
    ['甲','乙','丙','丁','戊','己'].map(word => '原话：' + word).join('\n'));
  assert.deepEqual(card.activity.observed_dates, ['2026-03-01','2026-04-05']);
  assert.equal(card.activity.share_quotes.length, 6);
  assert.equal(card.activity.summary, undefined);
});

test('中文报告单的人物类型可单独识别，普通标签仍保留原意', () => {
  for (const field of ['年度类型','人物类型','本次类型','人格类型']) {
    const report = parsePlainReport(['PUAI 2026', field+'：爱因斯坦','原话：这两颗果核算谁的？','标签：果核精算师'].join('\n'));
    assert.equal(report.theme, 'einstein');
    assert.deepEqual(report.keywords, ['果核精算师']);
  }
  assert.equal(parsePlainReport('PUAI 2026\n人物类型：待定\n原话：这里也算吗？').theme, null);
  assert.equal(parsePlainReport('PUAI 2026\n标签：PUAI\n原话：这里也算吗？').theme, null);
});
