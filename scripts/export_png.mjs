#!/usr/bin/env node
/** Export the complete PUAI canvas, with no image or rendering service uploads. */
import { access, mkdir, rename, rm, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { createRequire } from 'node:module';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const help = `Export a PUAI report HTML to its original 900 px PNG canvas.

Usage:
  node scripts/export_png.mjs --input report.html --output report.png

Options:
  --browser PATH          Chrome, Edge or Chromium executable
  --module-root PATH      Directory containing installed Playwright packages
                          (usually a node_modules directory)
  --mobile-preview PATH   Also save a 390 px wide page preview PNG
  --help                  Show this help

Requires Node.js 20+ and playwright or playwright-core. Uses an existing browser;
does not install dependencies, change browser profiles, or upload anything.`;

function parseArgs(argv) {
  const options = {};
  const allowed = new Set(['input', 'output', 'browser', 'module-root', 'mobile-preview']);
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--help' || argv[i] === '-h') return { help: true };
    const key = argv[i].replace(/^--/, '');
    if (!argv[i].startsWith('--') || !allowed.has(key)) throw new Error(`Unknown option: ${argv[i]}`);
    if (options[key]) throw new Error(`Repeated option: --${key}`);
    const value = argv[++i];
    if (!value || value.startsWith('--')) throw new Error(`Missing value for --${key}`);
    options[key] = path.resolve(value);
  }
  if (!options.input || !options.output) throw new Error('--input and --output are required. Use --help for examples.');
  if (path.extname(options.output).toLowerCase() !== '.png') throw new Error('--output must end in .png');
  if (options['mobile-preview'] && path.extname(options['mobile-preview']).toLowerCase() !== '.png') {
    throw new Error('--mobile-preview must end in .png');
  }
  const paths = [options.input, options.output, options['mobile-preview']].filter(Boolean);
  const comparable = process.platform === 'win32' ? paths.map(p => p.toLowerCase()) : paths;
  if (new Set(comparable).size !== comparable.length) throw new Error('Input, output and mobile preview must be different files.');
  return options;
}

async function exists(file, mode = constants.F_OK) {
  try { await access(file, mode); return true; } catch { return false; }
}

function loadPlaywright(moduleRoot) {
  const loaders = moduleRoot
    ? [createRequire(path.join(moduleRoot, '__puai_loader__.cjs'))]
    : [createRequire(path.join(process.cwd(), '__puai_loader__.cjs')), createRequire(import.meta.url)];
  for (const loader of loaders) {
    for (const name of ['playwright', 'playwright-core']) {
      try {
        const api = loader(name);
        if (api.chromium?.launch) return api;
      } catch { /* Try the other supported package or module location. */ }
    }
  }
  throw new Error('Playwright was not found. Install playwright-core in a local dependency directory, then pass --module-root /path/to/node_modules. See references/png-export.md.');
}

async function findBrowser(chromium, explicit) {
  if (explicit) {
    if (!await exists(explicit, constants.X_OK)) throw new Error(`Browser executable is unavailable: ${explicit}`);
    return explicit;
  }
  const candidates = [chromium.executablePath()];
  if (process.platform === 'darwin') {
    for (const prefix of ['/Applications', path.join(os.homedir(), 'Applications')]) {
      candidates.push(path.join(prefix, 'Google Chrome.app/Contents/MacOS/Google Chrome'));
      candidates.push(path.join(prefix, 'Microsoft Edge.app/Contents/MacOS/Microsoft Edge'));
      candidates.push(path.join(prefix, 'Chromium.app/Contents/MacOS/Chromium'));
    }
  } else if (process.platform === 'win32') {
    for (const prefix of [process.env.PROGRAMFILES, process.env['PROGRAMFILES(X86)'], process.env.LOCALAPPDATA].filter(Boolean)) {
      candidates.push(path.join(prefix, 'Google/Chrome/Application/chrome.exe'));
      candidates.push(path.join(prefix, 'Microsoft/Edge/Application/msedge.exe'));
    }
  } else {
    candidates.push('/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/microsoft-edge', '/snap/bin/chromium');
  }
  for (const prefix of (process.env.PATH || '').split(path.delimiter).filter(Boolean)) {
    for (const name of process.platform === 'win32' ? ['chrome.exe', 'msedge.exe', 'chromium.exe'] : ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'microsoft-edge']) {
      candidates.push(path.join(prefix, name));
    }
  }
  for (const file of new Set(candidates.filter(Boolean))) {
    if (await exists(file, constants.X_OK)) return file;
  }
  throw new Error('No Chromium browser was found. Install Chrome/Edge or a Playwright Chromium browser, or pass --browser /path/to/browser.');
}

async function saveAtomic(file, buffer) {
  await mkdir(path.dirname(file), { recursive: true, mode: 0o700 });
  const temporary = `${file}.${process.pid}.${Date.now()}.tmp`;
  try {
    await writeFile(temporary, buffer, { flag: 'wx', mode: 0o600 });
    await rename(temporary, file);
  } finally {
    await rm(temporary, { force: true });
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) { console.log(help); return; }
  await access(options.input, constants.R_OK);
  const { chromium } = loadPlaywright(options['module-root']);
  const executablePath = await findBrowser(chromium, options.browser);
  let browser;
  try {
    browser = await chromium.launch({ executablePath, headless: true, args: ['--disable-gpu'] });
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, offline: true, serviceWorkers: 'block' });
    const network = new Set(), errors = [];
    const permitted = url => /^(file:|data:|blob:|about:)/i.test(url);
    // Offline context plus a request route prevents remote font/image/script fetches.
    await context.route('**/*', async route => {
      if (!permitted(route.request().url())) {
        network.add(route.request().url());
        await route.abort();
      } else await route.continue();
    });
    context.on('request', request => { if (!permitted(request.url())) network.add(request.url()); });
    const page = await context.newPage();
    page.setDefaultTimeout(30_000);
    page.on('pageerror', error => errors.push(error.message));
    page.on('websocket', socket => network.add(socket.url()));
    await page.goto(pathToFileURL(options.input).href, { waitUntil: 'load', timeout: 30_000 });
    await page.waitForFunction(() => {
      const image = document.querySelector('#preview');
      return document.fonts.status === 'loaded' && image?.complete && image.naturalWidth > 0 && image.getAttribute('src')?.startsWith('data:image/png');
    });
    const result = await page.evaluate(() => {
      const canvas = document.querySelector('#poster');
      if (!(canvas instanceof HTMLCanvasElement)) throw new Error('Expected the report canvas #poster. Generate a compact report with --style comic first.');
      const fonts = [...document.fonts].filter(face => face.status === 'error').map(face => face.family);
      if (fonts.length) throw new Error('Failed to load embedded fonts: ' + fonts.join(', '));
      return { width: canvas.width, height: canvas.height,
        mobileOverflow: document.documentElement.scrollWidth > innerWidth,
        image: canvas.toDataURL('image/png').split(',')[1] };
    });
    if (network.size) throw new Error(`Blocked ${network.size} external network request(s). Use a self-contained report with embedded fonts and assets.`);
    if (errors.length) throw new Error('Report JavaScript failed: ' + errors.join('; '));
    if (result.width !== 900 || !Number.isInteger(result.height) || result.height < 1) {
      throw new Error(`Expected a 900 px wide complete canvas, got ${result.width} × ${result.height}.`);
    }
    if (result.mobileOverflow) throw new Error('The report page overflows a 390 px mobile viewport. Review the HTML before sharing.');
    const png = Buffer.from(result.image, 'base64');
    if (png.length < 24 || !png.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) || png.readUInt32BE(16) !== 900 || png.readUInt32BE(20) !== result.height) {
      throw new Error('Canvas export did not produce a valid full-size PNG.');
    }
    const mobile = options['mobile-preview'] ? await page.screenshot({ fullPage: true, type: 'png' }) : null;
    // Recheck after the optional screenshot, before writing any successful output.
    if (network.size || errors.length) throw new Error('The page attempted a network request or raised a JavaScript error during export.');
    await saveAtomic(options.output, png);
    if (mobile) await saveAtomic(options['mobile-preview'], mobile);
    console.log(`Exported ${options.output} (${result.width} × ${result.height} px)`);
    if (mobile) console.log(`Mobile preview: ${options['mobile-preview']}`);
  } finally {
    if (browser) await browser.close();
  }
}

main().catch(error => {
  console.error('Could not export PNG: ' + error.message);
  process.exitCode = 1;
});
