#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { loadPrivateConfigEnv } from './soia-config.mjs';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
loadPrivateConfigEnv();

const suffixToType = new Map([
  ['.architecture.json', 'architecture'],
  ['.workflow.json', 'workflow'],
  ['.sequence.json', 'sequence'],
  ['.dataflow.json', 'dataflow'],
  ['.lifecycle.json', 'lifecycle'],
]);

function usage() {
  return `Usage:
  render-archify-diagrams.mjs --dir <diagram-dir> [--archify-root <path>] [--png-only] [--theme light|dark] [--width 1400] [--height 1000] [--scale 2] [--dry-run]
  render-archify-diagrams.mjs --file <diagram.json> [--archify-root <path>] [--png-only] [--theme light|dark] [--width 1400] [--height 1000] [--scale 2] [--dry-run]

Environment:
  ARCHIFY_ROOT=/path/to/archify/archify
  ARCHIFY_BIN=/path/to/archify.mjs
`;
}

function fail(message, code = 2) {
  console.error(message);
  process.exit(code);
}

function parseArgs(argv) {
  const args = { dryRun: false, pngOnly: false, theme: 'light', width: 1400, height: 1000, scale: 2 };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--dir') args.dir = argv[++i];
    else if (arg === '--file') args.file = argv[++i];
    else if (arg === '--archify-root') args.archifyRoot = argv[++i];
    else if (arg === '--png-only') args.pngOnly = true;
    else if (arg === '--theme') args.theme = argv[++i];
    else if (arg === '--width') args.width = Number(argv[++i]);
    else if (arg === '--height') args.height = Number(argv[++i]);
    else if (arg === '--scale') args.scale = Number(argv[++i]);
    else if (arg === '--dry-run') args.dryRun = true;
    else if (arg === '-h' || arg === '--help') {
      console.log(usage());
      process.exit(0);
    } else {
      fail(`Unknown argument: ${arg}\n\n${usage()}`);
    }
  }
  if ((args.dir && args.file) || (!args.dir && !args.file)) {
    fail(usage());
  }
  if (!['light', 'dark'].includes(args.theme)) fail('--theme must be light or dark');
  if (!Number.isFinite(args.width) || args.width < 320) fail('--width must be >= 320');
  if (!Number.isFinite(args.height) || args.height < 240) fail('--height must be >= 240');
  if (!Number.isFinite(args.scale) || args.scale < 1) fail('--scale must be >= 1');
  return args;
}

function pathExists(p) {
  try {
    fs.accessSync(p);
    return true;
  } catch {
    return false;
  }
}

function findArchifyBin(args) {
  if (process.env.ARCHIFY_BIN && pathExists(process.env.ARCHIFY_BIN)) {
    return process.env.ARCHIFY_BIN;
  }

  const roots = [
    args.archifyRoot,
    process.env.ARCHIFY_ROOT,
    path.join(os.homedir(), '.agents/skills/archify'),
    path.join(os.homedir(), '.codex/skills/archify'),
    path.join(os.homedir(), '.claude/skills/archify'),
  ].filter(Boolean);

  for (const root of roots) {
    const candidate = path.join(root, 'bin/archify.mjs');
    if (pathExists(candidate)) return candidate;
  }

  fail('Cannot find Archify. Set ARCHIFY_ROOT or ARCHIFY_BIN.');
}

function inferType(file) {
  for (const [suffix, type] of suffixToType.entries()) {
    if (file.endsWith(suffix)) return { suffix, type };
  }
  return null;
}

function outputFor(file, suffix) {
  return file.slice(0, -suffix.length) + '.html';
}

function collectFiles(args) {
  if (args.file) {
    const abs = path.resolve(args.file);
    const inferred = inferType(abs);
    if (!inferred) fail(`Unsupported diagram file suffix: ${args.file}`);
    return [abs];
  }

  const dir = path.resolve(args.dir);
  if (!pathExists(dir)) fail(`Directory does not exist: ${dir}`);
  return fs.readdirSync(dir)
    .map((name) => path.join(dir, name))
    .filter((file) => fs.statSync(file).isFile() && inferType(file))
    .sort();
}

function run(cmd, args, dryRun) {
  console.log(`$ ${[cmd, ...args].join(' ')}`);
  if (dryRun) return;
  const result = spawnSync(cmd, args, { stdio: 'inherit', encoding: 'utf8' });
  if (result.error) fail(result.error.message, 1);
  if (result.status !== 0) process.exit(result.status ?? 1);
}

const args = parseArgs(process.argv.slice(2));
const archifyBin = findArchifyBin(args);
const files = collectFiles(args);

if (files.length === 0) {
  fail('No Archify JSON files found.');
}

console.log(`Archify: ${archifyBin}`);
console.log(`Files: ${files.length}`);

for (const file of files) {
  const inferred = inferType(file);
  const output = outputFor(file, inferred.suffix);
  run(process.execPath, [archifyBin, 'validate', inferred.type, file, '--json'], args.dryRun);
  run(process.execPath, [archifyBin, 'render', inferred.type, file, output], args.dryRun);
  run(process.execPath, [archifyBin, 'check', output], args.dryRun);
}

if (args.pngOnly) {
  const exporter = path.join(scriptDir, 'export-archify-previews.mjs');
  if (args.file) {
    const inferred = inferType(path.resolve(args.file));
    const output = outputFor(path.resolve(args.file), inferred.suffix);
    run(process.execPath, [
      exporter,
      '--file',
      output,
      '--theme',
      args.theme,
      '--width',
      String(args.width),
      '--height',
      String(args.height),
      '--scale',
      String(args.scale),
    ], args.dryRun);
    if (!args.dryRun) fs.unlinkSync(output);
  } else {
    run(process.execPath, [
      exporter,
      '--dir',
      path.resolve(args.dir),
      '--theme',
      args.theme,
      '--width',
      String(args.width),
      '--height',
      String(args.height),
      '--scale',
      String(args.scale),
    ], args.dryRun);
    if (!args.dryRun) {
      for (const file of files) {
        const inferred = inferType(file);
        fs.unlinkSync(outputFor(file, inferred.suffix));
      }
    }
  }
}
