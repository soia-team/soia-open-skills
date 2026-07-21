from __future__ import annotations

import json
import os
import re
import shlex
import sys
import tempfile
from datetime import datetime
from pathlib import Path

OVERRIDE_CONFIG_NAME = "SOIA_PKM_CLIP_X_CONFIG_FILE"
OVERRIDE_ENV_NAME = "SOIA_PKM_CLIP_X_ENV_FILE"

KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PATH_LIKE_KEYS = {
    "OBSIDIAN_VAULT",
    "OBSIDIAN_ARTICLES",
}


def default_config_file() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home() / ".config"
    return base / "soia-skills" / "soia-open-skills" / "soia-pkm" / "soia-pkm-clip-x" / "config.yml"


def _candidate_paths() -> list[Path]:
    paths: list[Path] = []
    configured_config = os.environ.get(OVERRIDE_CONFIG_NAME)
    if configured_config:
        paths.append(Path(configured_config).expanduser())
    configured = os.environ.get(OVERRIDE_ENV_NAME)
    if configured:
        paths.append(Path(configured).expanduser())
    paths.append(default_config_file())
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
    return f"{OVERRIDE_CONFIG_NAME}, {OVERRIDE_ENV_NAME}, or {default_config_file()}"


def write_failure_log(failures: list[dict[str, object]], prefix: str = "telegram_sync_failures") -> Path:
    """Persist a batch-sync failure list to the platform temp dir and return its path.

    Failure lists are use-once-then-discard run reports, not an audit trail, so
    they belong under the platform's temporary directory /soia-pkm-clip-x/ instead of the caller's cwd
    (which may be the vault root, a read-only dir, or anything else at call time).
    Shared by sync_telegram_export.py and sync_telegram_saved.py so both behave
    the same way.
    """
    base_dir = Path(tempfile.gettempdir()) / "soia-pkm-clip-x"
    base_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fail_log = base_dir / f"{prefix}-{timestamp}.json"
    fail_log.write_text(
        json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return fail_log


def main() -> int:
    path = next((p for p in _candidate_paths() if p.is_file()), None)
    if not path:
        return 1
    for key, value in _load_config_env(path).items():
        print(f"export {key}={shlex.quote(value)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
