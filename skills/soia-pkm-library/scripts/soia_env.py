from __future__ import annotations

import os
import re
import shlex
import sys
from pathlib import Path

OVERRIDE_CONFIG_NAME = "SOIA_PKM_LIBRARY_CONFIG_FILE"
OVERRIDE_ENV_NAME = "SOIA_PKM_LIBRARY_ENV_FILE"
DEFAULT_CONFIG_FILE = "~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-library/config.yml"
WEREAD_SKILL_URL = "https://weread.qq.com/r/weread-skills"
WEREAD_SKILL_INSTALL = "npx skills add Tencent/WeChatReading -g"

KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PATH_LIKE_KEYS = {
    "OBSIDIAN_VAULT",
    "OBSIDIAN_ARTICLES",
}


def _candidate_paths() -> list[Path]:
    paths: list[Path] = []
    configured_config = os.environ.get(OVERRIDE_CONFIG_NAME)
    if configured_config:
        paths.append(Path(configured_config).expanduser())
    configured = os.environ.get(OVERRIDE_ENV_NAME)
    if configured:
        paths.append(Path(configured).expanduser())
    paths.append(Path(DEFAULT_CONFIG_FILE).expanduser())
    return paths


def _parse_scalar(value: str) -> str:
    value = value.strip()
    if not value or value in {"null", "~"}:
        return ""
    if value[0] in {"'", '"'} and value[-1:] == value[0]:
        try:
            return value[1:-1] if value[0] == "'" else bytes(value[1:-1], "utf-8").decode("unicode_escape")
        except UnicodeDecodeError:
            return value[1:-1]
    return value.split(" #", 1)[0].strip()


def _load_config_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    in_env = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent == 0:
            in_env = stripped == "env:"
            continue
        if not in_env or indent < 2 or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        if not KEY_RE.match(key):
            continue
        parsed = _parse_scalar(value)
        if key in PATH_LIKE_KEYS:
            parsed = os.path.expandvars(os.path.expanduser(parsed))
        env[key] = parsed
    return env


def load_private_env(required: bool = False) -> Path | None:
    """Load private config env values without overriding the process environment.

    Secrets must stay outside the vault and outside the open-source skill repo.
    """
    for path in _candidate_paths():
        if not path.is_file():
            continue
        try:
            for key, value in _load_config_env(path).items():
                os.environ.setdefault(key, value)
            return path
        except OSError as exc:
            print(f"⚠️ Could not read private config.yml {path}: {exc}", file=sys.stderr)
    if required:
        checked = ", ".join(str(path) for path in _candidate_paths())
        raise SystemExit(f"Missing private config file. Checked: {checked}")
    return None


def env_source_hint() -> str:
    return f"{OVERRIDE_CONFIG_NAME}, {OVERRIDE_ENV_NAME}, or {DEFAULT_CONFIG_FILE}"


def weread_skills_installed() -> bool:
    home = Path.home()
    return any(
        path.exists()
        for path in (
            home / ".agents/skills/weread-skills",
            home / ".codex/skills/weread-skills",
            home / ".claude/skills/weread-skills",
        )
    )


def weread_dependency_status() -> str:
    return "已安装" if weread_skills_installed() else f"未检测到，请先执行 `{WEREAD_SKILL_INSTALL}`"


def require_weread_skills() -> None:
    if weread_skills_installed():
        return
    raise SystemExit(
        "缺少强依赖 weread-skills：请先安装微信读书官方 Skill："
        f"{WEREAD_SKILL_INSTALL}；官方页面：{WEREAD_SKILL_URL}"
    )


def weread_api_key_hint() -> str:
    return (
        f"请打开 {WEREAD_SKILL_URL} 登录微信读书获取 WEREAD_API_KEY；"
        f"强依赖 weread-skills 状态：{weread_dependency_status()}"
    )


def main() -> int:
    path = next((p for p in _candidate_paths() if p.is_file()), None)
    if not path:
        return 1
    for key, value in _load_config_env(path).items():
        print(f"export {key}={shlex.quote(value)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
