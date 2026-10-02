#!/usr/bin/env python3
"""Focused G15-O1 ending clip/sequence packaging gate."""
from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools" / "bor_converter"), str(ROOT / "tools" / "scene_video")]
import build_rom  # noqa: E402
import convert_ending  # noqa: E402
import convert_rugal  # noqa: E402
import pack_msu_roster  # noqa: E402
import scene_sequences  # noqa: E402
from pak_extract import extract  # noqa: E402


def pack(entries):
    return pack_msu_roster.pack_roster(
        build_rom.ROSTER_PREFIXES,
        bgs=build_rom.BG_SCREENS,
        fps=build_rom.FP_SCREENS,
        spawns=[Path(p).read_bytes() for p in build_rom.SPAWN_TABLES],
        vm_blob=Path(build_rom.VM_MODULE).read_bytes(),
        playable_count=build_rom.PLAYABLE_ROSTER_COUNT,
        scene_video_entries=entries)


def parse_record(data, offset, limit):
    if offset + 6 > limit:
        raise AssertionError("frame header outside payload")
    frame_id, packed = struct.unpack_from("<HI", data, offset)
    map_len = (packed & 0x7FF) * 2
    tile_len = ((packed >> 11) & 0x7FF) * 32
    palette_len = ((packed >> 22) & 0xFF) * 2
    end = offset + 6 + map_len + tile_len + palette_len
    if end > limit:
        raise AssertionError("frame record outside payload")
    return frame_id, map_len, tile_len, palette_len, end


def main():
    pak = str(ROOT / "Beats of Rage Original [v.3.0 Build 4086].pak")
    clips = convert_ending.build_payloads(pak)
    rugal, rugal_stats = convert_rugal.build_payload(pak)
    entries = [{"scene_id": 1, "flags": 0, "width": 256, "height": 192,
                "fps_num": 25, "fps_den": 1, "frame_count": 126, "payload": rugal}]
    for name in convert_ending.CLIPS:
        payload, stats = clips[name]
        entries.append({"scene_id": stats["clip_id"], "flags": stats["flags"],
                        "width": stats["width"], "height": stats["height"],
                        "fps_num": stats["fps_num"], "fps_den": stats["fps_den"],
                        "frame_count": stats["frame_count"], "payload": payload})
    first, sidecar = pack(entries)
    second, sidecar2 = pack(entries)
    assert first == second and sidecar == sidecar2
    assert first[:8] == b"BORMSU1\0"
    section = len(first) - sum(len(e["payload"]) for e in entries) - 16 - 24 * len(entries)
    assert first[section:section + 8] == b"BORVID1\0"
    count = struct.unpack_from("<H", first, section + 10)[0]
    assert count == 6
    finalized = sidecar["scene_video"]
    assert len(finalized) == 6
    for entry, expected in zip(finalized, entries):
        assert entry["scene_id"] == expected["scene_id"]
        assert entry["payload_size"] == len(expected["payload"])
        base = entry["payload_offset"]
        limit = base + entry["payload_size"]
        frame_count, = struct.unpack_from("<I", first, base)
        assert frame_count == entry["frame_count"]
        pointers = struct.unpack_from("<" + "I" * frame_count, first, base + 4)
        assert len(pointers) == frame_count and list(pointers) == sorted(pointers)
        timing_start = base + 4 + 4 * frame_count
        if entry["flags"] & convert_ending.BORVID_FLAG_PER_FRAME_MS:
            timing_end = timing_start + 2 * frame_count
            timings = struct.unpack_from("<" + "H" * frame_count, first, timing_start)
            assert timing_end <= limit and all(timings)
        else:
            timing_end = timing_start
        ids = []
        cursor_ends = []
        for pointer in pointers:
            absolute = base + pointer
            assert base <= absolute < limit
            parsed = parse_record(first, absolute, limit)
            ids.append(parsed[0]); cursor_ends.append(parsed[-1])
            assert parsed[1] == 1536 and parsed[2] <= 384 * 32 and parsed[3] == 64
        assert ids == list(range(frame_count))
        assert max(cursor_ends) == limit
        assert entry["payload_offset"] + entry["payload_size"] <= len(first)
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
    time_asset = next(a for f in manifest["families"] for a in f["assets"]
                      if a.get("source_path") == "DATA\\MUSIC\\TIME.BOR")
    catalog = json.loads((ROOT / "tools/audio/music_catalog.json").read_text(encoding="utf-8"))
    time_track = next(a for a in catalog["tracks"]
                      if a.get("track_key") == "bor-original:DATA\\MUSIC\\TIME.BOR")
    assert time_asset["msu_track_id"] == time_track["track_id"] and time_track["repeat"] is True
    sequences = scene_sequences.render([
        {"scene_id": 1, "audio_track": 6, "audio_repeat": 0, "clips": [1]},
        {"scene_id": 2, "audio_track": time_track["track_id"], "audio_repeat": 1,
         "clips": [convert_ending.CLIP_IDS[n] for n in convert_ending.CLIPS]},
    ])
    assert "SceneSequence_Record1_ClipCount = 5" in sequences
    assert "    .db 2, 3, 4, 5, 6" in sequences
    print("PASS: ENDING source clips, BORVID1 records, timing extensions, sequence order")
    print("msu_size:", len(first), "sha256:", hashlib.sha256(first).hexdigest())
    for name, (_, stats) in clips.items():
        print(name, {k: stats[k] for k in ("source_frame_count", "total_duration_ms", "flags", "payload_size", "max_unique_tiles", "frames_reduced", "max_frame_record_bytes")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
