#!/usr/bin/env python3
"""Focused G15 Batch L2 verifier for the real BOR Rugal video payload."""
import hashlib
import io
import os
import struct
import sys
import tempfile

import numpy as np
from PIL import Image, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "tools", "bor_converter"))
import pack_msu_roster  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "tools", "scene_video"))
import convert_rugal  # noqa: E402


def pack():
    spawns = [open(path, "rb").read() for path in build_rom.SPAWN_TABLES]
    vm_blob = open(build_rom.VM_MODULE, "rb").read()
    payload, stats = convert_rugal.build_payload(build_rom.STAGE_CONFIGS[0]["pak"])
    entry = {
        "scene_id": convert_rugal.RUGAL_SCENE_ID,
        "flags": 0,
        "width": convert_rugal.WIDTH,
        "height": convert_rugal.HEIGHT,
        "fps_num": 25,
        "fps_den": 1,
        "frame_count": convert_rugal.SOURCE_FRAMES,
        "payload": payload,
    }
    msu, sidecar = pack_msu_roster.pack_roster(
        build_rom.ROSTER_PREFIXES, bgs=build_rom.BG_SCREENS,
        fps=build_rom.FP_SCREENS, spawns=spawns, vm_blob=vm_blob,
        playable_count=build_rom.PLAYABLE_ROSTER_COUNT,
        scene_video_entries=[entry])
    return msu, sidecar, stats


def frame_records(payload):
    count = struct.unpack_from("<I", payload)[0]
    pointers = struct.unpack_from("<" + "I" * count, payload, 4)
    records = []
    for pointer in pointers:
        frame_id, lengths = struct.unpack_from("<HI", payload, pointer)
        tm = ((lengths >> 0) & 0x7FF) * 2
        tiles = ((lengths >> 11) & 0x7FF) * 32
        palette = ((lengths >> 22) & 0xFF) * 2
        start = pointer + 6
        records.append({"id": frame_id, "pointer": pointer, "tilemap": payload[start:start + tm],
                        "tiles": payload[start + tm:start + tm + tiles],
                        "palette": payload[start + tm + tiles:start + tm + tiles + palette],
                        "end": start + tm + tiles + palette})
    return count, pointers, records


def reconstruct(record):
    tilemap = struct.unpack("<" + "H" * (len(record["tilemap"]) // 2), record["tilemap"])
    palettes = [struct.unpack_from("<16H", record["palette"], p * 32)
                for p in range(len(record["palette"]) // 32)]
    tiles = record["tiles"]
    rgb = np.zeros((convert_rugal.HEIGHT, convert_rugal.WIDTH, 3), dtype=np.uint8)
    for cell, word in enumerate(tilemap):
        tile = word & 0x3FF
        palette = (word >> 10) & 0x7
        for y in range(8):
            for x in range(8):
                bit = 7 - x
                index = (((tiles[tile * 32 + 2 * y] >> bit) & 1)
                         | (((tiles[tile * 32 + 2 * y + 1] >> bit) & 1) << 1)
                         | (((tiles[tile * 32 + 16 + 2 * y] >> bit) & 1) << 2)
                         | (((tiles[tile * 32 + 16 + 2 * y + 1] >> bit) & 1) << 3))
                color = palettes[palette][index]
                rgb[(cell // convert_rugal.TILE_W) * 8 + y,
                    (cell % convert_rugal.TILE_W) * 8 + x] = (
                    (color & 0x1F) * 255 // 31,
                    ((color >> 5) & 0x1F) * 255 // 31,
                    ((color >> 10) & 0x1F) * 255 // 31)
    return Image.fromarray(rgb, "RGB")


def main():
    msu, sidecar, stats = pack()
    msu_again, sidecar_again, stats_again = pack()
    scene = sidecar["scene_video"][0]
    scene_again = sidecar_again["scene_video"][0]
    base = scene["payload_offset"]
    section_start = base - pack_msu_roster.SCENE_VIDEO_HEADER_SIZE - pack_msu_roster.SCENE_VIDEO_ENTRY_SIZE
    payload = msu[base:base + scene["payload_size"]]
    count, pointers, records = frame_records(payload)
    source_data, source_frames, durations = convert_rugal.source_frames(build_rom.STAGE_CONFIGS[0]["pak"])
    scaled = convert_rugal.scaled_frames(source_frames)

    with tempfile.TemporaryDirectory(prefix="g15_l2_preview_") as temp:
        preview_results = []
        for index in (0, 63, 125):
            preview = reconstruct(records[index])
            expected = scaled[index]
            preview.save(os.path.join(temp, f"frame_{index}.png"))
            diff = ImageChops.difference(expected, preview)
            preview_results.append(diff.getbbox() is not None)

    checks = [
        ("source GIF is 320x240", Image.open(io.BytesIO(source_data)).size == (320, 240)),
        ("source has 126 frames", len(source_frames) == 126),
        ("source durations are all 40ms", durations == [40] * 126),
        ("BORMSU1 remains at offset zero", msu[:8] == b"BORMSU1\0"),
        ("BORVID1 entry count is one", msu[section_start:section_start + 8] == b"BORVID1\0"),
        ("Rugal metadata is exact", scene == {
            "scene_id": convert_rugal.RUGAL_SCENE_ID, "flags": 0,
            "width": 256, "height": 192, "fps_num": 25, "fps_den": 1,
            "frame_count": 126, "payload_offset": base,
            "payload_size": len(payload)}),
        ("payload has exactly 126 pointers", count == 126 and len(pointers) == 126),
        ("frame IDs are 0..125", [r["id"] for r in records] == list(range(126))),
        ("pointers are monotonic and in payload", list(pointers) == sorted(pointers)
         and all(base <= base + pointer < base + len(payload) for pointer in pointers)),
        ("tilemaps are 1536 bytes", all(len(r["tilemap"]) == 1536 for r in records)),
        ("tile sets are within 384 tiles", all(len(r["tiles"]) // 32 <= 384 for r in records)),
        ("palettes are valid", all(len(r["palette"]) == 64 for r in records)),
        ("final frame ends in payload", records[-1]["end"] == len(payload)),
        ("no synthetic duplicate frames", count == convert_rugal.SOURCE_FRAMES),
        ("repeated conversion is identical", msu_again == msu and scene_again == scene
         and stats_again == stats),
        ("packed previews reconstruct", all(preview_results)),
    ]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL") + ": " + name)
    print("source_sha256:", hashlib.sha256(source_data).hexdigest())
    print("payload_sha256:", hashlib.sha256(payload).hexdigest())
    print("scene_video_offset:", base)
    print("scene_video_size:", len(payload))
    print("msu_size:", len(msu))
    print("stats:", stats)
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
