#!/usr/bin/env python3
"""Build a standard Windows/browser .ico from the canonical Grow Central PNG.

No optional Pillow/ImageMagick dependency: ICO supports PNG-compressed frames.
The input is the 192 × 192 Grow Central app icon; one deterministic ICO entry.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def favicon_bytes(png: bytes) -> bytes:
    if not png.startswith(PNG_SIGNATURE) or len(png) < 33 or png[12:16] != b"IHDR":
        raise ValueError("Expected a valid PNG header")
    width, height = struct.unpack_from(">II", png, 16)
    if (width, height) != (192, 192):
        raise ValueError("Expected the canonical 192x192 Grow Central icon")
    # 6-byte ICO header, 16-byte ICONDIRENTRY, then intact PNG.
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 192, 192, 0, 0, 1, 32, len(png), 22)
    return header + entry + png


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.write_bytes(favicon_bytes(args.source.read_bytes()))


if __name__ == "__main__":
    main()
