"""Load skill-specific private config.yml into os.environ.

Expected file:
  ~/.config/soia-skills/soia-open-skills/soia-pkm/soia-pkm-alipan-drive-ops/config.yml

Only a small YAML subset is needed here: a top-level `env:` mapping with scalar
KEY: value pairs.
"""

from __future__ import annotations

import os
from pathlib import Path


SKILL_NAME = "soia-pkm-alipan-drive-ops"
DEFAULT_CONFIG = Path.home() / ".config" / "soia-skills" / "soia-open-skills" / "soia-pkm" / SKILL_NAME / "config.yml"
OVERRIDE_CONFIG_NAME = "SOIA_PKM_ALIPAN_DRIVE_OPS_CONFIG_FILE"
OVERRIDE_ENV_NAME = "SOIA_PKM_ALIPAN_ENV_FILE"


def private_config_file() -> Path:
    configured_config = os.environ.get(OVERRIDE_CONFIG_NAME)
    if configured_config:
        return Path(configured_config).expanduser()
    configured = os.environ.get(OVERRIDE_ENV_NAME)
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_CONFIG


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_env_mapping(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    in_env = False
    env_indent: int | None = None

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue

        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()

        if not in_env:
            if stripped == "env:":
                in_env = True
                env_indent = None
            continue

        if env_indent is None:
            if indent == 0:
                in_env = False
                continue
            env_indent = indent

        if indent < env_indent:
            in_env = False
            continue
        if indent != env_indent or ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        if not key or not key.replace("_", "").isalnum():
            continue
        value = value.split(" #", 1)[0].strip()
        if value in {"", "null", "Null", "NULL", "~"}:
            continue
        values[key] = _strip_quotes(value)

    return values


def load_private_env(required: bool = False) -> Path | None:
    path = private_config_file()
    if not path.exists():
        if required:
            raise SystemExit(
                f"Missing private config file: {path}\n"
                f"Copy config.example.yml there and fill required values."
            )
        return None

    try:
        values = _parse_env_mapping(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Could not read private config file {path}: {exc}") from exc

    for key, value in values.items():
        os.environ.setdefault(key, value)
    return path


if __name__ == "__main__":
    # This module is intentionally silent when run directly.  Its former
    # ``export KEY=value`` output could disclose credentials from config.yml.
    # Consumers should import ``load_private_env`` instead.
    load_private_env(required=False)
