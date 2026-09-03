#!/usr/bin/env python3
"""Extract and canonicalize the authoritative resident JUMP.WAV source."""
from __future__ import annotations

import hashlib
import io
import json
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter")]
from pak_extract import extract
from production_sfx import canonical_wav

PAK = ROOT / "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak"
ENTRY = "DATA" + chr(92) + "SOUNDS" + chr(92) + "JUMP.WAV"
EXPECTED_RAW_SHA = "0f9ffe9cfed79c7cc5af789b1ba2407f238d325918149a702bb294171e41faf9"


def main() -> int:
    raw = extract(PAK, ENTRY)
    raw_sha = hashlib.sha256(raw).hexdigest()
    if raw_sha != EXPECTED_RAW_SHA:
        raise SystemExit(f"FAIL: JUMP.WAV raw SHA drifted: {raw_sha}")
    canonical, rate = canonical_wav(raw)
    with wave.open(io.BytesIO(raw)) as wav:
        raw_frames = wav.getnframes()
    with wave.open(io.BytesIO(canonical)) as wav:
        frames = wav.getnframes()
    out = ROOT / "soundwork/tad/project/samples/jump.wav"
    out.write_bytes(canonical)
    metadata = {
        "asset": "tmnt:DATA\\SOUNDS\\JUMP.WAV",
        "source_pak": PAK.name,
        "source_pak_sha256": hashlib.sha256(PAK.read_bytes()).hexdigest(),
        "raw_sha256": raw_sha,
        "raw_bytes": len(raw),
        "raw_channels": 1,
        "raw_sample_format": "unsigned 8-bit PCM",
        "raw_sample_rate_hz": rate,
        "raw_frames": raw_frames,
        "raw_duration_seconds": raw_frames / rate,
        "canonical_path": "soundwork/tad/project/samples/jump.wav",
        "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "canonical_frames": frames,
        "canonical_duration_seconds": frames / rate,
        "padding_rule": "canonical_wav pads to a complete 16-sample BRR block",
        "brr_bytes": ((frames + 15) // 16) * 9,
        "backend": "resident_tad_sfx",
    }
    path = ROOT / "assets/audio/jump.source.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
