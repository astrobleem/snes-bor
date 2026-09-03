#!/usr/bin/env python3
"""Extract and canonicalize the authoritative resident FALL.WAV source."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter")]
from pak_extract import extract
from production_sfx import canonical_wav

PAK = ROOT / "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak"
ENTRY = "DATA" + chr(92) + "SOUNDS" + chr(92) + "FALL.WAV"
EXPECTED_RAW_SHA = "b55008537a246b99b1a20f3f5056012f292997fb6dec083398fd394539ca89ef"
EXPECTED_FRAMES = 11466
EXPECTED_RATE = 22050


def main() -> int:
    raw = extract(PAK, ENTRY)
    raw_sha = hashlib.sha256(raw).hexdigest()
    if raw_sha != EXPECTED_RAW_SHA:
        raise SystemExit(f"FAIL: FALL.WAV raw SHA drifted: {raw_sha}")
    canonical, rate = canonical_wav(raw)
    import io, wave
    with wave.open(io.BytesIO(canonical), "rb") as wav:
        frames = wav.getnframes()
    if rate != EXPECTED_RATE or frames != 11472:
        raise SystemExit(f"FAIL: canonical FALL geometry rate={rate} frames={frames}")
    out = ROOT / "soundwork/tad/project/samples/fall.wav"
    out.write_bytes(canonical)
    metadata = {
        "asset": "tmnt:DATA\\SOUNDS\\FALL.WAV",
        "source_pak": PAK.name,
        "source_pak_sha256": hashlib.sha256(PAK.read_bytes()).hexdigest(),
        "raw_sha256": raw_sha,
        "raw_channels": 1,
        "raw_sample_format": "unsigned 8-bit PCM",
        "raw_sample_rate_hz": EXPECTED_RATE,
        "raw_frames": EXPECTED_FRAMES,
        "raw_duration_seconds": EXPECTED_FRAMES / EXPECTED_RATE,
        "canonical_path": "soundwork/tad/project/samples/fall.wav",
        "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "canonical_frames": frames,
        "padding_rule": "canonical_wav pads to a complete 16-sample BRR block",
        "backend": "resident_tad_sfx",
    }
    (ROOT / "assets/audio/fall.source.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
