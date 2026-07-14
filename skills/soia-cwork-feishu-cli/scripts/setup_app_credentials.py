#!/usr/bin/env python3
"""Create or update a lark-cli profile from a private YAML config.

The App Secret is sent through stdin to lark-cli and is never printed or put
in the child process argv. This script intentionally does not perform OAuth
user login; it configures application credentials for bot identity calls.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO = "soia-open-skills"
SKILL_TYPE = "cwork"
SKILL_NAME = "soia-cwork-feishu-cli"
CONFIG_ENV = "SOIA_CWORK_FEISHU_CONFIG_FILE"


def config_candidates() -> list[Path]:
    candidates: list[Path] = []
    explicit = os.environ.get(CONFIG_ENV)
    if explicit:
        candidates.append(Path(explicit).expanduser())
    candidates.append(
        Path("~/.config/soia-skills").expanduser()
        / REPO
        / SKILL_TYPE
        / SKILL_NAME
        / "config.yml"
    )
    return candidates


def load_config(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise SystemExit("Missing PyYAML. Install it with: python3 -m pip install pyyaml") from exc

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        candidates = "\n".join(f"- {item}" for item in config_candidates())
        raise SystemExit(f"Config not found. Create one of:\n{candidates}") from exc
    except yaml.YAMLError as exc:
        raise SystemExit(f"Invalid YAML config: {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit("Config root must be a YAML mapping")
    return data


def resolve_env(data: dict, key: str, default: str | None = None) -> str | None:
    values = data.get("env")
    if not isinstance(values, dict):
        values = {}
    value = values.get(key)
    if value in (None, "", f"<YOUR_{key.removeprefix('LARK_')}>"):
        value = os.environ.get(key, default)
    if value is None:
        return None
    return str(value).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure lark-cli with Feishu App ID and App Secret.")
    parser.add_argument("--config", type=Path, help=f"Override {CONFIG_ENV} config path.")
    parser.add_argument("--use", action="store_true", help="Switch to the configured profile after adding it.")
    args = parser.parse_args()

    if args.config:
        os.environ[CONFIG_ENV] = str(args.config.expanduser())

    path = next((candidate for candidate in config_candidates() if candidate.is_file()), None)
    if path is None:
        load_config(Path("__missing_config__"))
        return 2

    data = load_config(path)
    app_id = resolve_env(data, "LARK_APP_ID")
    app_secret = resolve_env(data, "LARK_APP_SECRET")
    defaults = data.get("defaults") if isinstance(data.get("defaults"), dict) else {}
    profile = resolve_env(data, "LARK_PROFILE", str(defaults.get("profile", "feishu-reader")))
    brand = resolve_env(data, "LARK_BRAND", str(defaults.get("brand", "feishu")))

    if not app_id or app_id.startswith("<"):
        raise SystemExit("Missing LARK_APP_ID in the private config or process environment")
    if not app_secret or app_secret.startswith("<"):
        raise SystemExit("Missing LARK_APP_SECRET in the private config or process environment")
    if brand not in {"feishu", "lark"}:
        raise SystemExit("LARK_BRAND must be feishu or lark")
    if not profile or profile.startswith("<"):
        raise SystemExit("LARK_PROFILE must be a non-empty profile name")

    if shutil.which("lark-cli"):
        argv = ["lark-cli"]
    else:
        argv = ["npx", "--yes", "@larksuite/cli@latest"]
    argv += ["profile", "add", "--name", profile, "--app-id", app_id, "--app-secret-stdin", "--brand", brand]
    if args.use:
        argv.append("--use")

    result = subprocess.run(
        argv,
        input=(app_secret + "\n").encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.stdout:
        sys.stdout.buffer.write(result.stdout)
    if result.returncode != 0:
        # Do not echo stderr because provider errors may accidentally include
        # sensitive request context. Surface a bounded, redacted status only.
        print(f"lark-cli profile setup failed with exit code {result.returncode}", file=sys.stderr)
        return result.returncode
    print(f"Configured lark-cli profile: {profile} (brand={brand}, use={args.use})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
