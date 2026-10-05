#!/usr/bin/env python3
"""Offline conversion of the authored BOR ENDING animation clips."""
from __future__ import annotations

import hashlib
import io
import struct
import sys
from fractions import Fraction
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PAK = ROOT / "Beats of Rage Original [v.3.0 Build 4086].pak"
CLIPS = ("FALLA", "FALLB", "CONSP", "CREDS", "THANKS")
CLIP_IDS = {name: index + 2 for index, name in enumerate(CLIPS)}
CLIP_IDS["SEWER"] = 7
WIDTH, HEIGHT = 256, 192
TILEMAP_BYTES, MAX_TILES, BYTES_PER_TILE = 1536, 384, 32
BORVID_FLAG_PER_FRAME_MS = 1

sys.path.insert(0, str(ROOT / "tools" / "bor_converter"))
from pak_extract import extract  # noqa: E402
sys.path.insert(0, str(ROOT / "tools" / "scene_video"))
from convert_rugal import convert_frame, shared_palettes  # noqa: E402


def read_clip(pak_path: str | Path, name: str):
    path = rf"DATA\SCENES\{name}.GIF"
    raw = extract(str(pak_path), path)
    image = Image.open(io.BytesIO(raw))
    frames, durations, disposals, transparency = [], [], [], []
    index = 0
    while True:
        try:
            image.seek(index)
        except EOFError:
            break
        frames.append(image.convert("RGB").copy())
        durations.append(image.info.get("duration"))
        disposals.append(getattr(image, "disposal_method", image.info.get("disposal")))
        transparency.append(image.info.get("transparency"))
        index += 1
    if not frames:
        raise ValueError(f"{name}: empty GIF")
    return raw, image.size, frames, durations, disposals, transparency


def audit_clip(pak_path: str | Path, name: str) -> dict:
    raw, size, frames, durations, disposals, transparency = read_clip(pak_path, name)
    return {
        "clip_id": CLIP_IDS[name], "name": name,
        "source_path": rf"DATA\SCENES\{name}.GIF",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_size_bytes": len(raw), "source_width": size[0],
        "source_height": size[1], "source_frame_count": len(frames),
        "durations_ms": durations, "total_duration_ms": sum(d or 0 for d in durations),
        "disposals": disposals, "transparency": transparency,
        "uniform_timing": len(set(durations)) == 1,
        "frames_are_composited": True,
    }


def build_clip(pak_path: str | Path, name: str):
    raw, size, originals, durations, disposals, transparency = read_clip(pak_path, name)
    if size != (320, 240):
        raise ValueError(f"{name}: source geometry {size} is not supported")
    if any(value is None or value <= 0 for value in durations):
        raise ValueError(f"{name}: missing/invalid GIF timing")
    scaled = [frame.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
              for frame in originals]
    palettes = shared_palettes(scaled)
    converted = [convert_frame(frame, palettes) for frame in scaled]
    records = []
    for frame_id, (tiles, tilemap, palette, before, after, reduced) in enumerate(converted):
        if len(tilemap) != TILEMAP_BYTES or len(tiles) > MAX_TILES * BYTES_PER_TILE:
            raise ValueError(f"{name}: frame {frame_id} exceeds 384-tile bound")
        length_header = ((len(tilemap) // 2) & 0x7FF
                         | (((len(tiles) // BYTES_PER_TILE) & 0x7FF) << 11)
                         | (((len(palette) // 2) & 0xFF) << 22))
        records.append(struct.pack("<HI", frame_id, length_header)
                       + tilemap + tiles + palette)
    variable = len(set(durations)) != 1
    pointer_bytes = 4 + 4 * len(records)
    timing_bytes = 2 * len(records) if variable else 0
    cursor = pointer_bytes + timing_bytes
    pointers = []
    for record in records:
        pointers.append(cursor)
        cursor += len(record)
    payload = struct.pack("<I", len(records))
    payload += struct.pack("<" + "I" * len(pointers), *pointers)
    if variable:
        payload += struct.pack("<" + "H" * len(durations), *durations)
    payload += b"".join(records)
    stats = audit_clip(pak_path, name)
    stats.update({
        "width": WIDTH, "height": HEIGHT,
        # Variable clips retain a nominal 25 fps descriptor for legacy
        # readers; the per-frame table is authoritative when the flag is set.
        "fps_num": 25 if variable else Fraction(1000, durations[0]).numerator,
        "fps_den": 1 if variable else Fraction(1000, durations[0]).denominator,
        "frame_count": len(records), "flags": BORVID_FLAG_PER_FRAME_MS if variable else 0,
        "tilemap_bytes": TILEMAP_BYTES,
        "min_unique_tiles": min(item[4] for item in converted),
        "avg_unique_tiles": sum(item[4] for item in converted) / len(converted),
        "max_unique_tiles": max(item[4] for item in converted),
        "frames_reduced": sum(item[5] for item in converted),
        "max_tile_bytes": max(len(item[0]) for item in converted),
        "palette_bytes": len(converted[0][2]),
        "max_frame_record_bytes": max(map(len, records)),
        "payload_size": len(payload), "timing_table_bytes": timing_bytes,
        "pointers": pointers,
    })
    return payload, stats


def build_payloads(pak_path: str | Path = PAK):
    return {name: build_clip(pak_path, name) for name in CLIPS}


if __name__ == "__main__":
    for name in CLIPS:
        audit = audit_clip(PAK, name)
        print(name, {key: value for key, value in audit.items()
                     if key not in ("durations_ms", "disposals", "transparency")})
