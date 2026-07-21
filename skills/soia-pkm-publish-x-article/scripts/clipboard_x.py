#!/usr/bin/env python3
"""Put rich HTML or an image on the macOS clipboard for X Articles paste.

Own implementation for soia-pkm-publish-x-article: pure stdlib + osascript, no
pyobjc. The osascript program is written to a temp file and executed from
there, so payload size is never limited by ARG_MAX.

Clipboard flavors:
- html  → «class HTML» (hex-encoded UTF-8) + plain-text fallback; the X editor
  reads the HTML flavor on Cmd+V and keeps headings/bold/links/lists.
- image → PNG via «class PNGf», JPEG via «class JPEG», read directly from the
  file (no hex round-trip). Other formats: convert first (sips -s format png).

Usage:
    python3 clipboard_x.py html --file /path/body.html
    python3 clipboard_x.py image /path/to/img.png
    python3 clipboard_x.py image /path/to/img.jpg --max-bytes 3000000

--max-bytes guards against editor-side upload failures on oversized images: if
the file exceeds the limit the script downsizes a temp copy with sips (ships
with macOS) and copies that instead. The original file is never modified.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

IMAGE_CLASSES = {".png": "«class PNGf»", ".jpg": "«class JPEG»", ".jpeg": "«class JPEG»"}


def _run_applescript(program: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".applescript", delete=False, encoding="utf-8") as f:
        f.write(program)
        script_path = f.name
    try:
        subprocess.run(["osascript", script_path], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"osascript failed: {exc.stderr.strip()}") from exc
    finally:
        os.unlink(script_path)


def copy_html(html: str) -> None:
    hex_html = html.encode("utf-8").hex().upper()
    # Plain-text fallback is intentionally the raw HTML: paste targets without
    # a rich-text flavor should still receive something inspectable.
    escaped = html.replace("\\", "\\\\").replace('"', '\\"')
    _run_applescript(
        f'set the clipboard to {{«class HTML»:«data HTML{hex_html}», string:"{escaped}"}}'
    )


def _downsize(path: Path, max_bytes: int) -> Path:
    out = Path(tempfile.mkdtemp(prefix="clipboard-x-")) / path.name
    subprocess.run(
        ["sips", "--resampleHeightWidthMax", "2000", str(path), "--out", str(out)],
        check=True,
        capture_output=True,
    )
    if out.stat().st_size > max_bytes:
        print(
            f"[clipboard_x] still {out.stat().st_size} bytes after downsize; copying anyway",
            file=sys.stderr,
        )
    return out


def copy_image(path: Path, max_bytes: int | None) -> None:
    ext = path.suffix.lower()
    if ext not in IMAGE_CLASSES:
        raise SystemExit(
            f"unsupported image type '{ext}' — convert first: sips -s format png '{path}'"
        )
    if max_bytes and path.stat().st_size > max_bytes:
        print(
            f"[clipboard_x] {path.stat().st_size} bytes > {max_bytes}, downsizing a temp copy",
            file=sys.stderr,
        )
        path = _downsize(path, max_bytes)
    posix = str(path).replace("\\", "\\\\").replace('"', '\\"')
    _run_applescript(
        f'set the clipboard to (read (POSIX file "{posix}") as {IMAGE_CLASSES[ext]})'
    )


def main() -> int:
    if sys.platform != "darwin":
        print("Error: macOS only (osascript). ", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser(description="Clipboard helper for X Articles upload")
    sub = parser.add_subparsers(dest="mode", required=True)

    html_p = sub.add_parser("html", help="copy rich HTML")
    html_p.add_argument("content", nargs="?", help="inline HTML (or use --file / stdin)")
    html_p.add_argument("--file", "-f", help="read HTML from file")

    img_p = sub.add_parser("image", help="copy an image")
    img_p.add_argument("path", help="png/jpg/jpeg file")
    img_p.add_argument(
        "--max-bytes",
        type=int,
        default=None,
        help="downsize a temp copy if the file is larger than this many bytes",
    )

    args = parser.parse_args()

    if args.mode == "html":
        if args.file:
            html = Path(args.file).read_text(encoding="utf-8")
        elif args.content:
            html = args.content
        else:
            html = sys.stdin.read()
        if not html.strip():
            print("Error: empty HTML", file=sys.stderr)
            return 1
        copy_html(html)
        print(f"HTML on clipboard ({len(html)} chars)")
        return 0

    path = Path(args.path).expanduser()
    if not path.is_file():
        print(f"Error: image not found: {path}", file=sys.stderr)
        return 1
    copy_image(path, args.max_bytes)
    print(f"Image on clipboard: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
