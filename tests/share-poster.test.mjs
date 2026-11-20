import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import test from 'node:test';

const require = createRequire(import.meta.url);
let chromium;
try {
  ({chromium} = require(process.env.PUAI_PLAYWRIGHT_PACKAGE || 'playwright-core'));
} catch (error) {
  if (error.code !== 'MODULE_NOT_FOUND' || process.env.PUAI_PLAYWRIGHT_PACKAGE) throw error;
}

test('转发按钮只在点按时交出当前 PNG，取消或缺少分享能力都能恢复', {
  skip: !chromium && 'Install playwright-core to test the mobile share flow.',
}, async () => {
  const browser = await chromium.launch({executablePath:process.env.PUAI_CHROMIUM});
  try {
    const context = await browser.newContext({viewport:{width:320,height:720}, isMobile:true, hasTouch:true});
    await context.route('https://puai.test/make/**', async route => {
      const name = new URL(route.request().url()).pathname.split('/').pop() || 'index.html';
      assert.ok(['index.html','make.js','poster-frame.txt','plain-report.mjs','report-code.mjs'].includes(name));
      assert.equal(route.request().method(), 'GET');
      await route.fulfill({body:await readFile(new URL('../docs/make/'+name,import.meta.url)), contentType:
        name.endsWith('.html')?'text/html':name.endsWith('.txt')?'text/plain':'text/javascript'});
    });
    const page = await context.newPage();
    await page.addInitScript(() => {
      const mode = new URL(location.href).searchParams.get('mode');
      window.copied = [];
      window.shared = [];
      Object.defineProperty(navigator, 'clipboard', {value:{writeText:async text => {
        if (mode === 'manual') throw new DOMException('Denied','NotAllowedError');
        window.copied.push(text);
      }}});
      Object.defineProperty(navigator, 'canShare', {value:payload =>
        mode !== 'copy' && mode !== 'manual' && payload.files?.length === 1 && Boolean(payload.text)});
      Object.defineProperty(navigator, 'share', {value:async ({files, text}) => {
        const file = files[0];
        window.shared.push({name:file.name, mime:file.type, text, active:navigator.userActivation.isActive});
        if (mode === 'cancel') throw new DOMException('Stopped','AbortError');
        if (mode === 'reject') throw new DOMException('Blocked','NotAllowedError');
        const input = new FileReader();
        const data = new Promise(resolve => {input.onload=()=>resolve(input.result)});
        input.readAsDataURL(file);
        window.sameImage = (await data) === document.getElementById('preview').src;
      }});
    });
    const fields = new URLSearchParams({name:'小橘',theme:'hush',scope:'thread',q:'连果核也算？'});
    const button=page.locator('#share');
    let invite;
    for(const mode of ['native','cancel','copy','reject','manual']){
      await page.goto('https://puai.test/make/?mode='+mode+'#p?'+fields);
      await page.waitForFunction(()=>document.querySelector('#preview').naturalWidth===900);
      assert.equal(await button.isVisible(),true);
      assert.equal(await button.innerText(), ['copy','manual'].includes(mode)?'复制转发语':'转发长图');
      assert.deepEqual(await page.evaluate(()=>[shared.length,copied.length]),[0,0]);
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      await button.click();
      await page.waitForFunction(()=>!document.getElementById('share').disabled);
      const output = await page.evaluate(()=>({shared,copied,sameImage:window.sameImage,
        status:document.getElementById('status').textContent}));
      if(mode==='native'){
        assert.equal(output.shared.length,1);
        const payload=output.shared[0];
        assert.deepEqual([payload.name,payload.mime,payload.active,output.sameImage],['小橘-2026-PUAI.png','image/png',true,true]);
        invite=payload.text;
        assert.equal(invite,'扫码获取口令，复制给你的 Agent。\nhttps://xn--sxrw8m230b.com/PUAI/#go');
        assert.ok(!invite.includes('连果核') && !invite.includes('小橘'));
      } else if(mode==='cancel'){
        assert.deepEqual([output.shared.length,output.copied.length,output.status],[1,0,'']);
        assert.equal(await button.innerText(),'转发长图');
      } else if(mode==='manual'){
        const selected=await page.locator('#share-text').evaluate(t=>({
          shown:!t.hidden,selected:t.value.slice(t.selectionStart,t.selectionEnd),focused:document.activeElement===t}));
        assert.deepEqual(selected,{shown:true,selected:invite,focused:true});
        assert.equal(output.status,'长按复制这段转发语。');
      } else {
        assert.deepEqual(output.copied,[invite]);
        assert.equal(output.status,'已复制转发语。');
        assert.equal(output.shared.length,mode==='reject'?1:0);
        assert.equal(await button.innerText(),'复制转发语');
      }
    }
  } finally { await browser.close(); }
});
