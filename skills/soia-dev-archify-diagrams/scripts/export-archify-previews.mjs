#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { loadPrivateConfigEnv } from './soia-config.mjs';

loadPrivateConfigEnv();

function usage() {
  return `Usage:
  export-archify-previews.mjs --dir <diagram-dir> [--theme light|dark] [--width 1400] [--height 1000] [--scale 2] [--chrome <path>]
  export-archify-previews.mjs --file <diagram.html> [--theme light|dark] [--width 1400] [--height 1000] [--scale 2] [--chrome <path>]

Writes one PNG next to each HTML file.
`;
}

function fail(message, code = 2) {
  console.error(message);
  process.exit(code);
}

function parseArgs(argv) {
  const args = {
    theme: 'light',
    width: 1400,
    height: 1000,
    scale: 2,
    chrome: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--dir') args.dir = argv[++i];
    else if (arg === '--file') args.file = argv[++i];
    else if (arg === '--theme') args.theme = argv[++i];
    else if (arg === '--width') args.width = Number(argv[++i]);
    else if (arg === '--height') args.height = Number(argv[++i]);
    else if (arg === '--scale') args.scale = Number(argv[++i]);
    else if (arg === '--chrome') args.chrome = argv[++i];
    else if (arg === '-h' || arg === '--help') {
      console.log(usage());
      process.exit(0);
    } else {
      fail(`Unknown argument: ${arg}\n\n${usage()}`);
    }
  }
  if ((args.dir && args.file) || (!args.dir && !args.file)) fail(usage());
  if (!['light', 'dark'].includes(args.theme)) fail('--theme must be light or dark');
  if (!Number.isFinite(args.width) || args.width < 320) fail('--width must be >= 320');
  if (!Number.isFinite(args.height) || args.height < 240) fail('--height must be >= 240');
  if (!Number.isFinite(args.scale) || args.scale < 1) fail('--scale must be >= 1');
  return args;
}

function collectFiles(args) {
  if (args.file) {
    const file = path.resolve(args.file);
    if (!file.endsWith('.html')) fail(`Expected .html file: ${file}`);
    return [file];
  }
  const dir = path.resolve(args.dir);
  if (!fs.existsSync(dir)) fail(`Directory does not exist: ${dir}`);
  return fs.readdirSync(dir)
    .filter((name) => name.endsWith('.html'))
    .map((name) => path.join(dir, name))
    .sort();
}

function outputFor(file) {
  return file.slice(0, -'.html'.length) + '.png';
}

async function loadPlaywright() {
  try {
    return await import('playwright');
  } catch (error) {
    return null;
  }
}

const args = parseArgs(process.argv.slice(2));
const files = collectFiles(args);
if (files.length === 0) fail('No HTML files found.');

const playwright = await loadPlaywright();

if (playwright) {
  const { chromium } = playwright;
  const launchOptions = { headless: true };
  if (args.chrome && fs.existsSync(args.chrome)) {
    launchOptions.executablePath = args.chrome;
  }

  const browser = await chromium.launch(launchOptions);
  try {
    const page = await browser.newPage({
      viewport: { width: args.width, height: args.height },
      deviceScaleFactor: args.scale,
    });

    for (const file of files) {
      const output = outputFor(file);
      console.log(`${file} -> ${output}`);
      await page.goto(`file://${file}`, { waitUntil: 'networkidle' });
      await page.evaluate((theme) => {
        document.documentElement.setAttribute('data-theme', theme);
      }, args.theme);
      await page.screenshot({ path: output, fullPage: true, type: 'png' });
    }
  } finally {
    await browser.close();
  }
} else {
  if (!args.chrome || !fs.existsSync(args.chrome)) {
    fail('Cannot import playwright and cannot find system Chrome. Install playwright or pass --chrome <path>.', 1);
  }

  for (const file of files) {
    const output = outputFor(file);
    const url = `file://${file}?theme=${encodeURIComponent(args.theme)}`;
    console.log(`${file} -> ${output}`);
    const result = spawnSync(args.chrome, [
      '--headless=new',
      '--disable-gpu',
      '--hide-scrollbars',
      `--force-device-scale-factor=${args.scale}`,
      `--window-size=${args.width},${args.height}`,
      `--screenshot=${output}`,
      url,
    ], { encoding: 'utf8' });
    if (result.error) fail(result.error.message, 1);
    if (result.status !== 0) {
      if (result.stdout) process.stdout.write(result.stdout);
      if (result.stderr) process.stderr.write(result.stderr);
      process.exit(result.status ?? 1);
    }
  }
}
