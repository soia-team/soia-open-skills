#!/usr/bin/env python3
"""Load the optional private config for soia-dev-open-design-ops.

Only a top-level ``env:`` mapping is supported. Values are loaded into the
current process without printing them, and only this skill's documented keys
are accepted.
"""

from __future__ import annotations

import os
from pathlib import Path


SKILL_NAME = "soia-dev-open-design-ops"
OVERRIDE_CONFIG_NAME = "SOIA_DEV_OPEN_DESIGN_OPS_CONFIG_FILE"
ALLOWED_ENV_KEYS = frozenset(
    {
        "OPEN_DESIGN_HOME",
        "OPEN_DESIGN_DAEMON_PORT",
        "OPEN_DESIGN_WEB_PORT",
        "OPEN_DESIGN_DAEMON_URL",
        "OPEN_DESIGN_STATE_DIR",
        "OPEN_DESIGN_PROJECT_DESIGN_MD",
    }
)


def default_config_file() -> Path:
    if os.name == "nt" and os.environ.get("APPDATA"):
        config_root = Path(os.environ["APPDATA"]) / "soia-skills"
    else:
        config_root = Path.home() / ".config" / "soia-skills"
    return config_root / "soia-open-skills" / "soia-dev" / SKILL_NAME / "config.yml"


def private_config_file() -> Path:
    configured = os.environ.get(OVERRIDE_CONFIG_NAME)
    return Path(configured).expanduser() if configured else default_config_file()


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_env_mapping(text: str) -> dict[str, str]:
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
        if key not in ALLOWED_ENV_KEYS:
            continue
        value = value.split(" #", 1)[0].strip()
        if value in {"", "null", "Null", "NULL", "~"}:
            continue
        values[key] = _strip_quotes(value)

    return values


def load_private_env(required: bool = False) -> Path | None:
    path = private_config_file()
    if not path.is_file():
        if required:
            raise SystemExit(
                "Missing private config. Copy config.example.yml to the documented "
                "skill config directory or set SOIA_DEV_OPEN_DESIGN_OPS_CONFIG_FILE."
            )
        return None

    try:
        values = parse_env_mapping(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit("Could not read the private Open Design config.") from exc

    for key, value in values.items():
        os.environ.setdefault(key, value)
    return path


if __name__ == "__main__":
    load_private_env(required=False)
