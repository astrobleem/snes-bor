#!/usr/bin/env python3
"""Extract and canonicalize the reachable BOR global resident SFX set."""
from __future__ import annotations

import hashlib
import io
import json
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/audio"), str(ROOT / "tools/bor_converter")]
from pak_extract import extract  # noqa: E402
from production_sfx import canonical_wav  # noqa: E402

PAK = ROOT / "Beats of Rage Original [v.3.0 Build 4086].pak"
PAK_SHA256 = "a2a55cdd5e1145e845607ecec3ad85a342529492e7120449a928f3a6eaea81d6"
SOURCES = {
    "get": ("GET.WAV", "df44cae1360524e01e6d7c0e080788ba3f2085cca5de5fa12eeb08b60fa409e3"),
    "money": ("MONEY.WAV", "52d26d9929b5a4ae7853e44e2f342d088d4f9388aad3aa1b9c8d18b41ef53f77"),
    "punch": ("PUNCH.WAV", "aefa21ba4960a65153ba6a2e2526f6c90d660afe7b3981d924da4dc3aee4f6e1"),
    "oneup": ("1UP.WAV", "2a92eaad3b7de0047c78abc230eb78d9fa464833cb2492f153e8c91b9ce4cbad"),
    "beep": ("BEEP.WAV", "bd6176e03abdd0c5ca2a4a78a864075b7345bece23d0decb0d46a2ff838b5d0f"),
    "beep2": ("BEEP2.WAV", "0c84854b2f8f8cff540a40623f383bc3db11c90356d7f8d46677979a347a020a"),
}


def wav_metadata(raw: bytes) -> tuple[int, int, int, int]:
    with wave.open(io.BytesIO(raw), "rb") as wav:
        return wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()


def main() -> int:
    if hashlib.sha256(PAK.read_bytes()).hexdigest() != PAK_SHA256:
        raise SystemExit("FAIL: BOR-original source PAK SHA drifted")
    for local, (filename, expected_raw_sha) in SOURCES.items():
        entry = "DATA\\SOUNDS\\" + filename
        raw = extract(PAK, entry)
        raw_sha = hashlib.sha256(raw).hexdigest()
        if raw_sha != expected_raw_sha:
            raise SystemExit(f"FAIL: {entry} raw SHA drifted: {raw_sha}")
        channels, width, rate, frames = wav_metadata(raw)
        if channels != 1 or width != 1:
            raise SystemExit(f"FAIL: {entry} is not mono 8-bit PCM")
        canonical, canonical_rate = canonical_wav(raw)
        with wave.open(io.BytesIO(canonical), "rb") as wav:
            canonical_frames = wav.getnframes()
        sample_path = ROOT / "soundwork/tad/project/samples" / f"{local}.wav"
        sample_path.write_bytes(canonical)
        record = {
            "asset": f"bor-original:{entry}",
            "source_pak": PAK.name,
            "source_pak_sha256": PAK_SHA256,
            "raw_sha256": raw_sha,
            "raw_bytes": len(raw),
            "raw_channels": channels,
            "raw_sample_width_bytes": width,
            "raw_sample_format": "unsigned 8-bit PCM",
            "raw_sample_rate_hz": rate,
            "raw_frames": frames,
            "raw_duration_seconds": frames / rate,
            "canonical_path": str(sample_path.relative_to(ROOT)).replace("\\", "/"),
            "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
            "canonical_frames": canonical_frames,
            "canonical_duration_seconds": canonical_frames / canonical_rate,
            "padding_rule": "canonical_wav pads to a complete 16-sample BRR block",
            "brr_bytes": ((canonical_frames + 15) // 16) * 9,
            "brr_blocks": (canonical_frames + 15) // 16,
            "backend": "resident_tad_sfx",
        }
        (ROOT / "assets/audio" / f"{local}.source.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(record, indent=2))

    pause = {
        "asset": "bor-original:DATA\\SOUNDS\\PAUSE.WAV",
        "source_pak": PAK.name,
        "source_pak_sha256": PAK_SHA256,
        "source_present": False,
        "fallback_asset": "bor-original:DATA\\SOUNDS\\BEEP2.WAV",
        "backend": "resident_tad_sfx_shared_beep2",
        "reason": "OpenBOR load_special_sounds falls back global_sample_list.pause to beep_2 when PAUSE.WAV is absent",
    }
    (ROOT / "assets/audio/pause.source.json").write_text(
        json.dumps(pause, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
