#!/usr/bin/env python3
"""Finalize ProcessOn browser downloads with safe paths and audit manifests."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


REPO = "soia-open-skills"
SKILL_TYPE = "cwork"
SKILL_NAME = "soia-cwork-processon-diagrams"
CONFIG_ENV = "SOIA_CWORK_PROCESSON_DIAGRAMS_CONFIG_FILE"
TEMP_ENV = "SOIA_CWORK_PROCESSON_DIAGRAMS_TEMP_DIR"
OUTPUT_ENV = "SOIA_CWORK_PROCESSON_DIAGRAMS_OUTPUT_DIR"
MANIFEST_ENV = "SOIA_CWORK_PROCESSON_DIAGRAMS_MANIFEST_DIR"
RETENTION_ENV = "SOIA_CWORK_PROCESSON_DIAGRAMS_RETENTION_DAYS"
MANAGED_MARKER = ".soia-cwork-processon-diagrams-managed"
MARKER_CONTENT = f"{SKILL_NAME}\n"


class DownloadError(RuntimeError):
    """A user-actionable download finalization error."""


@dataclass(frozen=True)
class Settings:
    temp_dir: Path
    output_dir: Path
    manifest_dir: Path
    retention_days: int
    config_file: Path | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "temp_dir": str(self.temp_dir),
            "output_dir": str(self.output_dir),
            "manifest_dir": str(self.manifest_dir),
            "retention_days": self.retention_days,
            "config_file": str(self.config_file) if self.config_file else None,
        }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp_token(value: datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y%m%dT%H%M%S%fZ")


def expand_path(value: str | os.PathLike[str]) -> Path:
    return Path(os.path.expandvars(str(value))).expanduser().resolve()


def config_root(home: Path, environ: Mapping[str, str]) -> Path:
    if os.name == "nt":
        return expand_path(environ.get("APPDATA", home / "AppData" / "Roaming"))
    return expand_path(environ.get("XDG_CONFIG_HOME", home / ".config"))


def state_root(home: Path, environ: Mapping[str, str]) -> Path:
    if os.name == "nt":
        return expand_path(environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    return expand_path(environ.get("XDG_STATE_HOME", home / ".local" / "state"))


def default_config_file(home: Path, environ: Mapping[str, str]) -> Path:
    return (
        config_root(home, environ)
        / "soia-skills"
        / REPO
        / SKILL_TYPE
        / SKILL_NAME
        / "config.yml"
    )


def is_placeholder(value: Any) -> bool:
    text = str(value).strip()
    return not text or (text.startswith("<") and text.endswith(">"))


def load_config_env(path: Path) -> dict[str, str]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise DownloadError(
            "PyYAML is required when using config.yml; install it with: "
            "python3 -m pip install pyyaml"
        ) from exc

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise DownloadError(f"Config file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise DownloadError(f"Invalid YAML config: {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise DownloadError("Config root must be a YAML mapping")
    values = payload.get("env") or {}
    if not isinstance(values, dict):
        raise DownloadError("Config env must be a YAML mapping")
    return {
        str(key): str(value).strip()
        for key, value in values.items()
        if value is not None and not is_placeholder(value)
    }


def resolve_config_file(
    cli_value: str | os.PathLike[str] | None,
    environ: Mapping[str, str],
    home: Path,
) -> Path | None:
    if cli_value:
        path = expand_path(cli_value)
        if not path.is_file():
            raise DownloadError(f"Config file not found: {path}")
        return path
    if environ.get(CONFIG_ENV):
        path = expand_path(environ[CONFIG_ENV])
        if not path.is_file():
            raise DownloadError(f"{CONFIG_ENV} points to a missing file: {path}")
        return path
    path = default_config_file(home, environ)
    return path if path.is_file() else None


def resolved_value(
    cli_value: str | os.PathLike[str] | None,
    env_name: str,
    environ: Mapping[str, str],
    config_env: Mapping[str, str],
    default: str | os.PathLike[str],
) -> str | os.PathLike[str]:
    if cli_value is not None and not is_placeholder(cli_value):
        return cli_value
    if environ.get(env_name) and not is_placeholder(environ[env_name]):
        return environ[env_name]
    if config_env.get(env_name) and not is_placeholder(config_env[env_name]):
        return config_env[env_name]
    return default


def resolve_retention_days(
    cli_value: int | None,
    environ: Mapping[str, str],
    config_env: Mapping[str, str],
) -> int:
    raw: Any = cli_value
    if raw is None:
        raw = environ.get(RETENTION_ENV)
    if raw is None:
        raw = config_env.get(RETENTION_ENV)
    if raw is None:
        raw = 7
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise DownloadError(f"{RETENTION_ENV} must be an integer") from exc
    if value < 0:
        raise DownloadError("retention days must be zero or greater")
    return value


def load_settings(
    *,
    config: str | os.PathLike[str] | None = None,
    temp_dir: str | os.PathLike[str] | None = None,
    output_dir: str | os.PathLike[str] | None = None,
    manifest_dir: str | os.PathLike[str] | None = None,
    retention_days: int | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    system_temp: Path | None = None,
) -> Settings:
    environment = dict(os.environ if environ is None else environ)
    resolved_home = (home or Path.home()).expanduser().resolve()
    resolved_system_temp = (system_temp or Path(tempfile.gettempdir())).resolve()
    config_file = resolve_config_file(config, environment, resolved_home)
    config_env = load_config_env(config_file) if config_file else {}

    default_temp = resolved_system_temp / SKILL_NAME
    default_output = resolved_home / "Downloads" / SKILL_NAME
    default_manifest = state_root(resolved_home, environment) / SKILL_NAME / "manifests"
    settings = Settings(
        temp_dir=expand_path(
            resolved_value(temp_dir, TEMP_ENV, environment, config_env, default_temp)
        ),
        output_dir=expand_path(
            resolved_value(output_dir, OUTPUT_ENV, environment, config_env, default_output)
        ),
        manifest_dir=expand_path(
            resolved_value(
                manifest_dir, MANIFEST_ENV, environment, config_env, default_manifest
            )
        ),
        retention_days=resolve_retention_days(
            retention_days, environment, config_env
        ),
        config_file=config_file,
    )
    validate_settings(settings)
    return settings


def validate_settings(settings: Settings) -> None:
    temp_dir = settings.temp_dir.resolve()
    for label, destination in (
        ("output", settings.output_dir),
        ("manifest", settings.manifest_dir),
    ):
        resolved = destination.resolve()
        if resolved == temp_dir or path_is_within(resolved, temp_dir):
            raise DownloadError(
                f"{label} directory must not equal or sit inside managed temp dir: "
                f"{resolved}"
            )


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def reserve_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.touch(exist_ok=False)
    except OSError as exc:
        raise DownloadError(f"Cannot reserve audit manifest: {path}: {exc}") from exc


def remove_empty_reservation(path: Path) -> None:
    try:
        if path.is_file() and path.stat().st_size == 0:
            path.unlink()
    except OSError:
        pass


def marker_path(temp_dir: Path) -> Path:
    return temp_dir / MANAGED_MARKER


def require_managed_temp(temp_dir: Path) -> None:
    marker = marker_path(temp_dir)
    try:
        content = marker.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise DownloadError(
            f"Refusing destructive temp operation: managed marker missing in {temp_dir}. "
            "Run the paths command with --ensure first."
        ) from exc
    if content != MARKER_CONTENT:
        raise DownloadError(f"Managed marker content is invalid: {marker}")


def ensure_paths(settings: Settings) -> dict[str, Any]:
    validate_settings(settings)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.manifest_dir.mkdir(parents=True, exist_ok=True)

    marker = marker_path(settings.temp_dir)
    if settings.temp_dir.exists() and not marker.exists():
        existing = list(settings.temp_dir.iterdir())
        if existing:
            raise DownloadError(
                f"Refusing to adopt non-empty temp directory without marker: "
                f"{settings.temp_dir}"
            )
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    if marker.exists():
        require_managed_temp(settings.temp_dir)
    else:
        marker.write_text(MARKER_CONTENT, encoding="utf-8")
    return {
        "status": "ready",
        "settings": settings.as_dict(),
        "managed_marker": str(marker),
    }


def load_inspector() -> Any:
    script = Path(__file__).with_name("inspect_processon_export.py")
    spec = importlib.util.spec_from_file_location(
        "soia_processon_export_inspector", script
    )
    if not spec or not spec.loader:
        raise DownloadError(f"Cannot load export inspector: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect_source(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise DownloadError(f"Downloaded file not found: {path}")
    if path.is_symlink():
        raise DownloadError("Downloaded file must not be a symbolic link")
    if path.stat().st_size <= 0:
        raise DownloadError("Downloaded file is empty")
    try:
        return load_inspector().inspect_file(path, 500)
    except Exception as exc:
        raise DownloadError(
            f"Downloaded file inspection failed: {type(exc).__name__}: {exc}"
        ) from exc


def next_available_destination(output_dir: Path, name: str) -> Path:
    candidate = output_dir / name
    if not candidate.exists():
        return candidate
    source_name = Path(name)
    for index in range(1, 10_000):
        candidate = output_dir / f"{source_name.stem} ({index}){source_name.suffix}"
        if not candidate.exists():
            return candidate
    raise DownloadError(f"Cannot find an available destination name for: {name}")


def select_destination(
    output_dir: Path,
    source_name: str,
    collision: str,
    allow_overwrite: bool,
) -> Path:
    candidate = output_dir / Path(source_name).name
    if not candidate.exists():
        return candidate
    if collision == "rename":
        return next_available_destination(output_dir, source_name)
    if collision == "fail":
        raise DownloadError(f"Destination already exists: {candidate}")
    if collision == "overwrite" and not allow_overwrite:
        raise DownloadError(
            "--collision overwrite requires --allow-overwrite and explicit user approval"
        )
    return candidate


def path_is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def copy_atomically(source: Path, destination: Path, overwrite: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    reserved = False
    temporary = destination.parent / f".{destination.name}.{uuid.uuid4().hex}.part"
    try:
        if not overwrite:
            destination.touch(exist_ok=False)
            reserved = True
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
        reserved = False
    except FileExistsError as exc:
        raise DownloadError(f"Destination appeared concurrently: {destination}") from exc
    finally:
        if temporary.exists():
            temporary.unlink()
        if reserved and destination.exists() and destination.stat().st_size == 0:
            destination.unlink()


def finalize_download(
    source: Path,
    settings: Settings,
    *,
    collision: str = "rename",
    allow_overwrite: bool = False,
    move: bool = False,
    dry_run: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    validate_settings(settings)
    source = source.expanduser().resolve()
    inspection = inspect_source(source)
    destination = select_destination(
        settings.output_dir, source.name, collision, allow_overwrite
    )
    if source == destination.resolve():
        raise DownloadError("Source and destination must be different paths")

    operation = "move" if move else "copy"
    if move:
        require_managed_temp(settings.temp_dir)
        if source.name == MANAGED_MARKER:
            raise DownloadError("Managed temp marker cannot be finalized or removed")
        if not path_is_within(source, settings.temp_dir):
            raise DownloadError(
                f"--move is allowed only for files inside managed temp dir: "
                f"{settings.temp_dir}"
            )

    finalized_at = now or utc_now()
    manifest_name = (
        f"{destination.stem}.{timestamp_token(finalized_at)}."
        f"{uuid.uuid4().hex[:8]}.manifest.json"
    )
    manifest_path = settings.manifest_dir / manifest_name
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "dry-run" if dry_run else "completed",
        "operation": operation,
        "collision_policy": collision,
        "source": str(source),
        "destination": str(destination),
        "manifest": str(manifest_path),
        "finalized_at": finalized_at.isoformat(),
        "inspection": inspection,
        "settings": settings.as_dict(),
    }
    if dry_run:
        return result

    overwrite = collision == "overwrite" and allow_overwrite
    destination_existed = destination.exists()
    reserve_manifest(manifest_path)
    try:
        copy_atomically(source, destination, overwrite)
        finalized_inspection = inspect_source(destination)
        if finalized_inspection.get("sha256") != inspection.get("sha256"):
            raise DownloadError("SHA-256 mismatch after finalizing download")
        result["inspection"] = finalized_inspection
        atomic_write_json(manifest_path, result)
        if move:
            source.unlink()
    except Exception:
        remove_empty_reservation(manifest_path)
        if not destination_existed:
            destination.unlink(missing_ok=True)
        raise
    return result


def cleanup_temp(
    settings: Settings,
    *,
    retention_days: int | None = None,
    dry_run: bool = False,
    now_timestamp: float | None = None,
) -> dict[str, Any]:
    validate_settings(settings)
    require_managed_temp(settings.temp_dir)
    keep_days = settings.retention_days if retention_days is None else retention_days
    if keep_days < 0:
        raise DownloadError("retention days must be zero or greater")
    current = time.time() if now_timestamp is None else now_timestamp
    cutoff = current - keep_days * 24 * 60 * 60
    candidates = [
        path
        for path in settings.temp_dir.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and path.name != MANAGED_MARKER
        and path.stat().st_mtime < cutoff
    ]
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "dry-run" if dry_run else "completed",
        "temp_dir": str(settings.temp_dir),
        "retention_days": keep_days,
        "candidate_count": len(candidates),
        "deleted": [],
        "failures": [],
        "completed_at": utc_now().isoformat(),
    }
    if dry_run:
        result["candidates"] = [str(path) for path in candidates]
        return result

    manifest_path = (
        settings.manifest_dir
        / f"cleanup.{timestamp_token()}.{uuid.uuid4().hex[:8]}.manifest.json"
    )
    result["manifest"] = str(manifest_path)
    reserve_manifest(manifest_path)
    try:
        for path in candidates:
            try:
                path.unlink()
                result["deleted"].append(str(path))
            except OSError as exc:
                result["failures"].append(
                    {"path": str(path), "error": f"{type(exc).__name__}: {exc}"}
                )
        for directory in sorted(
            (path for path in settings.temp_dir.rglob("*") if path.is_dir()),
            key=lambda item: len(item.parts),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                pass
        atomic_write_json(manifest_path, result)
    except Exception:
        remove_empty_reservation(manifest_path)
        raise
    return result


def add_config_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", help=f"Override {CONFIG_ENV}.")


def add_path_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_retention: bool = True,
) -> None:
    parser.add_argument("--temp-dir", help=f"Override {TEMP_ENV}.")
    parser.add_argument("--output-dir", help=f"Override {OUTPUT_ENV}.")
    parser.add_argument("--manifest-dir", help=f"Override {MANIFEST_ENV}.")
    if include_retention:
        parser.add_argument(
            "--retention-days",
            type=int,
            help=f"Override {RETENTION_ENV}.",
        )


def settings_from_args(args: argparse.Namespace) -> Settings:
    return load_settings(
        config=args.config,
        temp_dir=getattr(args, "temp_dir", None),
        output_dir=getattr(args, "output_dir", None),
        manifest_dir=getattr(args, "manifest_dir", None),
        retention_days=getattr(args, "retention_days", None),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve, finalize, and clean ProcessOn browser downloads."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    paths_parser = subparsers.add_parser(
        "paths", help="Resolve configured temp, output, and manifest paths."
    )
    add_config_argument(paths_parser)
    add_path_arguments(paths_parser)
    paths_parser.add_argument(
        "--ensure",
        action="store_true",
        help="Create directories and mark the temp directory as skill-managed.",
    )

    finalize_parser = subparsers.add_parser(
        "finalize", help="Validate and copy or move one downloaded file."
    )
    finalize_parser.add_argument("source", help="Browser-reported downloaded file.")
    add_config_argument(finalize_parser)
    add_path_arguments(finalize_parser)
    finalize_parser.add_argument(
        "--collision",
        choices=("rename", "fail", "overwrite"),
        default="rename",
        help="Destination collision policy; default: rename.",
    )
    finalize_parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="Required with --collision overwrite after explicit user approval.",
    )
    finalize_parser.add_argument(
        "--move",
        action="store_true",
        help="Remove source only after success; allowed only inside managed temp.",
    )
    finalize_parser.add_argument(
        "--dry-run", action="store_true", help="Print the plan without writing."
    )

    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Delete expired files only from the managed temp directory."
    )
    add_config_argument(cleanup_parser)
    add_path_arguments(cleanup_parser)
    cleanup_parser.add_argument(
        "--dry-run", action="store_true", help="List candidates without deleting."
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        settings = settings_from_args(args)
        if args.command == "paths":
            result = ensure_paths(settings) if args.ensure else {
                "status": "resolved",
                "settings": settings.as_dict(),
            }
        elif args.command == "finalize":
            result = finalize_download(
                Path(args.source),
                settings,
                collision=args.collision,
                allow_overwrite=args.allow_overwrite,
                move=args.move,
                dry_run=args.dry_run,
            )
        else:
            result = cleanup_temp(
                settings,
                retention_days=args.retention_days,
                dry_run=args.dry_run,
            )
    except (DownloadError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.command == "cleanup" and result.get("failures"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
