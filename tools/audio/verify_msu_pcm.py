#!/usr/bin/env python3
"""Fail-closed validation for generated MSU-1 PCM and its catalog."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "tools/audio/music_catalog.json"
FORMAT = "MSU-1 PCM: MSU1 header + signed 16-bit LE stereo 44100 Hz"


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    errors = []
    if catalog.get("format") != FORMAT:
        errors.append("catalog format is not MSU1 header + stereo PCM")
    seen = set()
    for track in catalog.get("tracks", []):
        track_id = track["track_id"]
        if track_id in seen:
            errors.append(f"duplicate track id {track_id}")
        seen.add(track_id)
        path = ROOT / track.get("msu_pcm_path", "")
        if not path.exists():
            errors.append(f"missing generated PCM: {path}")
            continue
        data = path.read_bytes()
        if data[:4] != b"MSU1" or len(data) < 8 or (len(data) - 8) % 4:
            errors.append(f"track {track_id}: invalid MSU1 header/payload")
            continue
        loop, = struct.unpack_from("<I", data, 4)
        frames = (len(data) - 8) // 4
        if loop > frames:
            errors.append(f"track {track_id}: loop frame outside payload")
        if track.get("msu_loop_frame") != loop:
            errors.append(f"track {track_id}: catalog loop frame mismatch")
        if track.get("repeat") is not True and not (track.get("scene_audio") and track.get("repeat") is False):
            errors.append(f"track {track_id}: runtime repeat semantic is not explicit")
        if hashlib.sha256(data).hexdigest() != track.get("msu_pcm_hash"):
            errors.append(f"track {track_id}: catalog hash mismatch")
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print(f"MSU PCM PASS: {len(seen)} tracks, headers/payloads/loops/hashes verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
