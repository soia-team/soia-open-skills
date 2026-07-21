#!/usr/bin/env python3
"""Discover draw.io Desktop and run safe conversion/export commands."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


EXPORT_FORMATS = {"png", "svg", "pdf", "jpg"}


class DrawioError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binary_candidates(environ: dict[str, str] | None = None) -> list[Path]:
    environ = environ or os.environ
    candidates: list[Path] = []
    if environ.get("DRAWIO_BIN"):
        candidates.append(Path(environ["DRAWIO_BIN"]).expanduser())
    for command in ("drawio", "draw.io"):
        found = shutil.which(command)
        if found:
            candidates.append(Path(found))
    if platform.system() == "Darwin":
        candidates.append(Path("/Applications/draw.io.app/Contents/MacOS/draw.io"))
    elif platform.system() == "Windows":
        for variable in ("ProgramFiles", "LOCALAPPDATA"):
            if environ.get(variable):
                candidates.append(Path(environ[variable]) / "draw.io" / "draw.io.exe")
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def find_drawio(environ: dict[str, str] | None = None) -> tuple[Path, str]:
    errors: list[str] = []
    for candidate in binary_candidates(environ):
        if not candidate.is_file():
            continue
        try:
            result = subprocess.run(
                [str(candidate), "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(f"{candidate}: {exc}")
            continue
        version = (result.stdout or result.stderr).strip().splitlines()[0]
        return candidate.resolve(), version
    detail = f" ({'; '.join(errors)})" if errors else ""
    raise DrawioError("draw.io Desktop CLI not found; set DRAWIO_BIN or install the official desktop app" + detail)


def ensure_new_output(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.exists():
        raise DrawioError(f"refusing to overwrite existing output: {path}")
    if not path.parent.is_dir():
        raise DrawioError(f"output directory does not exist: {path.parent}")
    return path


def run_drawio(binary: Path, arguments: list[str]) -> str:
    try:
        result = subprocess.run(
            [str(binary), *arguments],
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        raise DrawioError("draw.io command timed out after 180 seconds") from exc
    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or exc.stdout or str(exc)).strip()
        raise DrawioError(f"draw.io command failed: {message}") from exc
    return (result.stdout or result.stderr).strip()


def validate_output(path: Path, expected: str) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size == 0:
        raise DrawioError(f"draw.io did not create a non-empty output: {path}")
    head = path.read_bytes()[:16]
    if expected == "drawio":
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            raise DrawioError(f"invalid draw.io XML output: {exc}") from exc
        if root.tag != "mxfile" or not root.findall("diagram"):
            raise DrawioError("draw.io XML output has no <mxfile>/<diagram>")
    elif expected == "png" and not head.startswith(b"\x89PNG\r\n\x1a\n"):
        raise DrawioError("PNG output has an invalid signature")
    elif expected == "pdf" and not head.startswith(b"%PDF-"):
        raise DrawioError("PDF output has an invalid signature")
    elif expected == "jpg" and not head.startswith(b"\xff\xd8\xff"):
        raise DrawioError("JPG output has an invalid signature")
    elif expected == "svg" and b"<svg" not in path.read_bytes()[:4096].lower():
        raise DrawioError("SVG output has no <svg> root")
    return {"path": str(path), "size": path.stat().st_size, "sha256": sha256_file(path)}


def doctor() -> dict[str, Any]:
    binary, version = find_drawio()
    help_text = run_drawio(binary, ["--help"])
    return {
        "status": "ready",
        "binary": str(binary),
        "version": version,
        "vsdx_input_supported": "vsdx" in help_text.lower() and "inputs are also supported" in help_text.lower(),
        "supported_outputs": sorted(EXPORT_FORMATS | {"drawio"}),
        "vsdx_output_supported": False,
    }


def convert(input_path: Path, output_path: Path) -> dict[str, Any]:
    input_path = input_path.expanduser().resolve()
    if not input_path.is_file() or input_path.suffix.lower() != ".vsdx":
        raise DrawioError("convert expects an existing .vsdx input")
    if output_path.suffix.lower() not in {".drawio", ".xml"}:
        raise DrawioError("convert output must end in .drawio or .xml")
    output_path = ensure_new_output(output_path)
    binary, version = find_drawio()
    message = run_drawio(
        binary,
        ["-x", "-f", "xml", "-u", "-o", str(output_path), str(input_path)],
    )
    receipt = validate_output(output_path, "drawio")
    receipt.update(
        {
            "action": "convert",
            "input": str(input_path),
            "input_sha256": sha256_file(input_path),
            "binary": str(binary),
            "version": version,
            "message": message,
        }
    )
    return receipt


def export(
    input_path: Path,
    output_path: Path,
    output_format: str,
    all_pages: bool = False,
) -> dict[str, Any]:
    input_path = input_path.expanduser().resolve()
    if not input_path.is_file():
        raise DrawioError(f"input not found: {input_path}")
    if output_format not in EXPORT_FORMATS:
        raise DrawioError(f"unsupported export format: {output_format}")
    output_path = ensure_new_output(output_path)
    binary, version = find_drawio()
    arguments = ["-x", "-f", output_format, "-o", str(output_path)]
    if all_pages:
        arguments.append("--all-pages")
    arguments.append(str(input_path))
    message = run_drawio(binary, arguments)
    receipt = validate_output(output_path, output_format)
    receipt.update(
        {
            "action": "export",
            "format": output_format,
            "input": str(input_path),
            "input_sha256": sha256_file(input_path),
            "binary": str(binary),
            "version": version,
            "message": message,
        }
    )
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor")
    convert_parser = subparsers.add_parser("convert")
    convert_parser.add_argument("input", type=Path)
    convert_parser.add_argument("--output", type=Path, required=True)
    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("input", type=Path)
    export_parser.add_argument("--format", choices=sorted(EXPORT_FORMATS), required=True)
    export_parser.add_argument("--output", type=Path, required=True)
    export_parser.add_argument("--all-pages", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "doctor":
            receipt = doctor()
        elif args.command == "convert":
            receipt = convert(args.input, args.output)
        else:
            receipt = export(args.input, args.output, args.format, args.all_pages)
    except (DrawioError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
