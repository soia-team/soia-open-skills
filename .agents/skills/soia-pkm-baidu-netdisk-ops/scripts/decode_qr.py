#!/usr/bin/env python3
"""Decode a QR image path or HTTPS image URL and print its payload.

OpenCV is optional at skill-install time. Install ``opencv-python`` in the
runtime that executes this helper when QR decoding is needed.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.request import Request, urlopen


class QRDecodeError(RuntimeError):
    """Raised when the source cannot be decoded as a QR code."""


def _read_source(source: str) -> bytes:
    if source.startswith("http://"):
        raise QRDecodeError("remote QR sources must use HTTPS")
    if source.startswith("https://"):
        request = Request(source, headers={"User-Agent": "soia-baidu-netdisk-ops/1"})
        with urlopen(request, timeout=15) as response:  # noqa: S310 - source is explicitly user-provided
            return response.read()
    return Path(source).read_bytes()


def decode_image_bytes(data: bytes) -> str:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise QRDecodeError("QR decoding requires optional opencv-python (and its numpy dependency)") from exc

    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise QRDecodeError("could not read the image")
    value, _points, _straight = cv2.QRCodeDetector().detectAndDecode(image)
    if not value:
        raise QRDecodeError("no decodable QR code was found")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Decode a QR image path or HTTPS image URL")
    parser.add_argument("source", help="local image path or image URL")
    args = parser.parse_args(argv)
    try:
        print(decode_image_bytes(_read_source(args.source)))
    except (OSError, QRDecodeError, TimeoutError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
