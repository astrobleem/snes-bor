#!/usr/bin/env python3
"""Verify the active generated TAD runtime driver is not the legacy vendor blob."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "soundwork/tad/driver_baseline.json"
AUDIO_BIN = ROOT / "soundwork/tad/build/audio-data.bin"
AUDIO_ASM = ROOT / "soundwork/tad/build/audio-data.s"
BLOB_SYMS = ROOT / "soundwork/tad/build/tad_blob_syms.pasm"
VENDOR = ROOT / "soundwork/tad/vendor/tad-audio-driver.bin"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    blob = AUDIO_BIN.read_bytes()
    offset = m["runtime_graph"]["driver_offset"]
    size = m["runtime_graph"]["driver_size_after_patch"]
    driver = blob[offset:offset + size]
    assert len(driver) == size, "generated audio blob is shorter than driver range"
    assert sha(driver) == m["runtime_graph"]["driver_sha256_after_patch"]
    text = AUDIO_ASM.read_text(encoding="utf-8")
    assert re.search(r"Tad_AudioDriver_SIZE\s*=\s*3266", text)
    syms = BLOB_SYMS.read_text(encoding="utf-8")
    assert "Tad_AudioDriver_Bin = $0180A7" in syms
    assert "Tad_AudioDriver_SIZE = 3266" in syms
    vendor = VENDOR.read_bytes()
    assert len(vendor) == m["legacy_vendor"]["size"]
    assert sha(vendor) == m["legacy_vendor"]["sha256"]
    assert sha(vendor) != sha(driver)
    patch = (ROOT / m["patch"]["path"]).read_bytes()
    assert sha(patch) == m["patch"]["sha256"]
    print(f"active generated TAD driver: offset={offset} size={size} sha256={sha(driver)}")
    print(f"legacy vendor TAD driver: size={len(vendor)} sha256={sha(vendor)} status=non-runtime")
    print("TAD DRIVER BASELINE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
