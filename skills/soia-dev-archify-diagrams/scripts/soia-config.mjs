import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const overrideConfigName = 'SOIA_DEV_ARCHIFY_DIAGRAMS_CONFIG_FILE';
const overrideEnvName = 'SOIA_DEV_ARCHIFY_DIAGRAMS_ENV_FILE';
const defaultConfigFile = '~/.config/soia-skills/soia-open-skills/soia-dev/soia-dev-archify-diagrams/config.yml';
const keyPattern = /^[A-Za-z_][A-Za-z0-9_]*$/;
const pathLikeKeys = new Set(['ARCHIFY_BIN', 'ARCHIFY_ROOT', 'CHROME_PATH']);

function expandHome(value) {
  if (!value) return value;
  let result = value.replace(/\$HOME/g, os.homedir());
  if (result === '~') return os.homedir();
  if (result.startsWith('~/')) return path.join(os.homedir(), result.slice(2));
  return result;
}

function parseScalar(value) {
  const trimmed = value.trim();
  if (!trimmed || trimmed === 'null' || trimmed === '~') return '';
  if ((trimmed.startsWith('"') && trimmed.endsWith('"')) || (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
    return trimmed.slice(1, -1);
  }
  return trimmed.split(' #', 1)[0].trim();
}

function parseEnvConfig(file) {
  const env = new Map();
  let inEnv = false;
  const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/);
  for (const line of lines) {
    const stripped = line.trim();
    if (!stripped || stripped.startsWith('#')) continue;
    const indent = line.length - line.trimStart().length;
    if (indent === 0) {
      inEnv = stripped === 'env:';
      continue;
    }
    if (!inEnv || indent < 2 || !stripped.includes(':')) continue;
    const index = stripped.indexOf(':');
    const key = stripped.slice(0, index).trim();
    if (!keyPattern.test(key)) continue;
    let value = parseScalar(stripped.slice(index + 1));
    if (pathLikeKeys.has(key)) value = expandHome(value);
    env.set(key, value);
  }
  return env;
}

function candidatePaths() {
  return [
    process.env[overrideConfigName],
    process.env[overrideEnvName],
    defaultConfigFile,
  ].filter(Boolean).map(expandHome);
}

export function loadPrivateConfigEnv() {
  const found = candidatePaths().find((file) => fs.existsSync(file) && fs.statSync(file).isFile());
  if (!found) return null;
  for (const [key, value] of parseEnvConfig(found)) {
    if (process.env[key] === undefined) process.env[key] = value;
  }
  return found;
}
