from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ENV_FILE_CANDIDATES = (
    "SOIA_PKM_ENV_FILE",
    "~/.config/soia-pkm/env",
    "~/.soia-pkm.env",
)

KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PATH_LIKE_KEYS = {
    "OBSIDIAN_VAULT",
    "OBSIDIAN_GZH_OUT",
}


def _candidate_paths() -> list[Path]:
    paths: list[Path] = []
    configured = os.environ.get("SOIA_PKM_ENV_FILE")
    if configured:
        paths.append(Path(configured).expanduser())
    for raw in ENV_FILE_CANDIDATES[1:]:
        paths.append(Path(raw).expanduser())
    return paths


def _parse_env_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[len("export "):].lstrip()
    if "=" not in line:
        return None
    key, value = line.split("=", 1)
    key = key.strip()
    if not KEY_RE.match(key):
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    else:
        value = value.split(" #", 1)[0].strip()
    if key in PATH_LIKE_KEYS:
        value = os.path.expandvars(os.path.expanduser(value))
    return key, value


def load_private_env() -> Path | None:
    """Load private env values without overriding the process environment.

    Secrets must stay outside the vault and outside the open-source skill repo.
    Supported private locations:
    - $SOIA_PKM_ENV_FILE
    - ~/.config/soia-pkm/env
    - ~/.soia-pkm.env
    """
    for path in _candidate_paths():
        if not path.is_file():
            continue
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                parsed = _parse_env_line(line)
                if not parsed:
                    continue
                key, value = parsed
                os.environ.setdefault(key, value)
            return path
        except OSError as exc:
            print(f"⚠️ Could not read private env file {path}: {exc}", file=sys.stderr)
    return None


def env_source_hint() -> str:
    return "SOIA_PKM_ENV_FILE, ~/.config/soia-pkm/env, or ~/.soia-pkm.env"
