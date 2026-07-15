"""Load the skill-specific private config without printing secrets."""

from __future__ import annotations

import os
from pathlib import Path


SKILL_NAME = "soia-pkm-baidupan"
DEFAULT_CONFIG = (
    Path.home()
    / ".config"
    / "soia-skills"
    / "soia-open-skills"
    / "soia-pkm"
    / SKILL_NAME
    / "config.yml"
)
OVERRIDE_CONFIG_NAME = "SOIA_PKM_BAIDUPAN_CONFIG_FILE"
OVERRIDE_ENV_NAME = "SOIA_PKM_BAIDUPAN_ENV_FILE"
ALLOWED_ENV_KEYS = frozenset(
    {
        "BAIDUPAN_APP_KEY",
        "BAIDUPAN_APP_SECRET",
        "BAIDUPAN_APP_NAME",
        "BAIDUPAN_CRYPTO_PASSPHRASE",
    }
)
ALLOWED_BINARIES = frozenset({"bdpan", "baidupan-cli"})


def private_config_file() -> Path:
    configured = os.environ.get(OVERRIDE_CONFIG_NAME) or os.environ.get(OVERRIDE_ENV_NAME)
    return Path(configured).expanduser() if configured else DEFAULT_CONFIG


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_config(text: str) -> dict[str, object]:
    config: dict[str, object] = {"env": {}}
    section: str | None = None
    env: dict[str, str] = {}
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if indent == 0:
            section = stripped[:-1] if stripped.endswith(":") else None
            if ":" in stripped and not stripped.endswith(":"):
                key, value = stripped.split(":", 1)
                if key.strip() in {"provider", "binary"}:
                    config[key.strip()] = _strip_quotes(value.split(" #", 1)[0])
            continue
        if section != "env" or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        if key in ALLOWED_ENV_KEYS:
            value = value.split(" #", 1)[0].strip()
            if value not in {"", "null", "Null", "NULL", "~"}:
                env[key] = _strip_quotes(value)
    config["env"] = env
    return config


def load_private_config(required: bool = False) -> dict[str, object]:
    path = private_config_file()
    if not path.exists():
        if required:
            raise SystemExit(
                f"Missing private config file: {path}\n"
                "Copy config.example.yml there and fill the selected provider values."
            )
        return {"env": {}}
    try:
        return _parse_config(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Could not read private config file {path}: {exc}") from exc


def load_private_env(required: bool = False) -> Path | None:
    path = private_config_file()
    config = load_private_config(required=required)
    for key, value in dict(config.get("env", {})).items():
        os.environ.setdefault(key, value)
    return path if path.exists() else None


def configured_binary() -> str:
    config = load_private_config(required=False)
    binary = str(config.get("binary") or "").strip()
    provider = str(config.get("provider") or "official").strip().lower()
    if not binary:
        binary = "baidupan-cli" if provider == "community" else "bdpan"
    if binary not in ALLOWED_BINARIES:
        raise SystemExit("config binary must be 'bdpan' or 'baidupan-cli'")
    if provider not in {"official", "community"}:
        raise SystemExit("config provider must be 'official' or 'community'")
    return binary


if __name__ == "__main__":
    # Intentionally silent: never turn private config into shell exports.
    load_private_env(required=False)
