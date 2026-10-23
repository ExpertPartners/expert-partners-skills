#!/usr/bin/env python3
"""inspect_image.py -- deterministic technical facts about one image file.

Part of the visual-clearance skill. Reports what the bytes prove and nothing
more: format, stored dimensions, display dimensions after EXIF orientation,
SHA-256 of the exact file, and the EXIF fields that matter for provenance
(capture date, GPS, camera, artist, copyright). Standard library only, so it
runs on any surface without Pillow.

An EXIF GPS fix or caption is ONE evidence item for location grading, never a
verification by itself, and stripped EXIF proves nothing either way.

Usage:
  inspect_image.py FILE [FILE ...]      JSON array on stdout
Exit status: 0 when every file was read, 1 when any file could not be parsed.
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

ORIENTATION_SWAPS = {5, 6, 7, 8}

IFD0_TAGS = {
    0x010F: "make",
    0x0110: "model",
    0x0112: "orientation",
    0x0132: "datetime",
    0x013B: "artist",
    0x8298: "copyright",
}
EXIF_TAGS = {0x9003: "datetime_original"}
GPS_TAGS = {1: "lat_ref", 2: "lat", 3: "lon_ref", 4: "lon"}
TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8}


class ParseError(Exception):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_value(tiff: bytes, endian: str, typ: int, count: int, raw: bytes):
    size = TYPE_SIZES.get(typ)
    if size is None:
        return None
    total = size * count
    if total > 4:
        (offset,) = struct.unpack(endian + "I", raw)
        if offset + total > len(tiff):
            return None
        data = tiff[offset : offset + total]
    else:
        data = raw[:total]
    if typ == 2:
        return data.split(b"\x00", 1)[0].decode("utf-8", "replace").strip()
    if typ == 3:
        values = struct.unpack(endian + "H" * count, data)
    elif typ in (4, 9):
        code = "I" if typ == 4 else "i"
        values = struct.unpack(endian + code * count, data)
    elif typ in (5, 10):
        code = "I" if typ == 5 else "i"
        pairs = struct.unpack(endian + code * (2 * count), data)
        values = tuple(
            (pairs[i] / pairs[i + 1]) if pairs[i + 1] else None
            for i in range(0, len(pairs), 2)
        )
    else:
        values = tuple(data)
    return values[0] if count == 1 else list(values)


def _read_ifd(tiff: bytes, endian: str, offset: int, wanted: dict) -> tuple[dict, dict]:
    found: dict = {}
    pointers: dict = {}
    if offset + 2 > len(tiff):
        return found, pointers
    (entries,) = struct.unpack(endian + "H", tiff[offset : offset + 2])
    for index in range(entries):
        start = offset + 2 + index * 12
        if start + 12 > len(tiff):
            break
        tag, typ, count = struct.unpack(endian + "HHI", tiff[start : start + 8])
        raw = tiff[start + 8 : start + 12]
        if tag in (0x8769, 0x8825):
            (pointers[tag],) = struct.unpack(endian + "I", raw)
        elif tag in wanted:
            found[wanted[tag]] = _read_value(tiff, endian, typ, count, raw)
    return found, pointers


def _dms_to_decimal(dms, ref) -> float | None:
    if not isinstance(dms, list) or len(dms) != 3 or any(v is None for v in dms):
        return None
    value = dms[0] + dms[1] / 60 + dms[2] / 3600
    if ref in ("S", "W"):
        value = -value
    return round(value, 7)


def parse_exif(tiff: bytes) -> dict:
    """Parse a TIFF-structured EXIF block (the bytes after 'Exif\\0\\0')."""
    if len(tiff) < 8 or tiff[:2] not in (b"II", b"MM"):
        return {}
    endian = "<" if tiff[:2] == b"II" else ">"
    (ifd0,) = struct.unpack(endian + "I", tiff[4:8])
    exif, pointers = _read_ifd(tiff, endian, ifd0, IFD0_TAGS)
    if 0x8769 in pointers:
        sub, _ = _read_ifd(tiff, endian, pointers[0x8769], EXIF_TAGS)
        exif.update(sub)
    if 0x8825 in pointers:
        gps, _ = _read_ifd(tiff, endian, pointers[0x8825], GPS_TAGS)
        lat = _dms_to_decimal(gps.get("lat"), gps.get("lat_ref"))
        lon = _dms_to_decimal(gps.get("lon"), gps.get("lon_ref"))
        if lat is not None and lon is not None:
            exif["gps"] = {"lat": lat, "lon": lon}
    return exif


def _jpeg(data: bytes) -> tuple[int, int, dict]:
    pos, width, height, exif = 2, None, None, {}
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            raise ParseError("corrupt JPEG marker stream")
        marker = data[pos + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        (length,) = struct.unpack(">H", data[pos + 2 : pos + 4])
        segment = data[pos + 4 : pos + 2 + length]
        if marker == 0xE1 and segment.startswith(b"Exif\x00\x00") and not exif:
            exif = parse_exif(segment[6:])
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            height, width = struct.unpack(">HH", segment[1:5])
            break
        if marker == 0xDA:
            break
        pos += 2 + length
    if width is None:
        raise ParseError("no JPEG frame header found")
    return width, height, exif


def _png(data: bytes) -> tuple[int, int, dict]:
    width, height = struct.unpack(">II", data[16:24])
    exif, pos = {}, 8
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        if kind == b"eXIf":
            exif = parse_exif(data[pos + 8 : pos + 8 + length])
        if kind == b"IEND":
            break
        pos += 12 + length
    return width, height, exif


def _webp(data: bytes) -> tuple[int, int, dict]:
    width = height = None
    exif, pos = {}, 12
    while pos + 8 <= len(data):
        kind = data[pos : pos + 4]
        (length,) = struct.unpack("<I", data[pos + 4 : pos + 8])
        body = data[pos + 8 : pos + 8 + length]
        if kind == b"VP8X" and width is None:
            width = 1 + int.from_bytes(body[4:7], "little")
            height = 1 + int.from_bytes(body[7:10], "little")
        elif kind == b"VP8 " and width is None:
            w, h = struct.unpack("<HH", body[6:10])
            width, height = w & 0x3FFF, h & 0x3FFF
        elif kind == b"VP8L" and width is None:
            bits = int.from_bytes(body[1:5], "little")
            width, height = (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        elif kind == b"EXIF":
            exif = parse_exif(body[6:] if body.startswith(b"Exif\x00\x00") else body)
        pos += 8 + length + (length & 1)
    if width is None:
        raise ParseError("no WebP image header found")
    return width, height, exif


def inspect(path: Path) -> dict:
    data = path.read_bytes()
    if data[:2] == b"\xff\xd8":
        fmt, (width, height, exif) = "jpeg", _jpeg(data)
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        fmt, (width, height, exif) = "png", _png(data)
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        fmt, (width, height, exif) = "webp", _webp(data)
    elif data[:6] in (b"GIF87a", b"GIF89a"):
        fmt, exif = "gif", {}
        width, height = struct.unpack("<HH", data[6:10])
    else:
        raise ParseError("unsupported or unrecognized image format")
    orientation = exif.get("orientation") if isinstance(exif.get("orientation"), int) else 1
    display = (height, width) if orientation in ORIENTATION_SWAPS else (width, height)
    return {
        "file": str(path),
        "original_filename": path.name,
        "format": fmt,
        "bytes": len(data),
        "sha256": sha256_file(path),
        "stored_dimensions": {"w": width, "h": height},
        "dimensions": {"w": display[0], "h": display[1]},
        "exif_orientation": orientation,
        "exif": exif,
        "exif_present": bool(exif),
    }


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    results, failed = [], False
    for name in argv:
        try:
            results.append(inspect(Path(name)))
        except (OSError, ParseError, struct.error) as exc:
            failed = True
            results.append({"file": name, "error": str(exc)})
    print(json.dumps(results, indent=2, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
