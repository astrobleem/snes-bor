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
    asm_size = int(re.search(r"Tad_AudioDriver_SIZE\s*=\s*(\d+)", text).group(1))
    assert asm_size == size
    syms = BLOB_SYMS.read_text(encoding="utf-8")
    main_sym = (ROOT / "src/main.sym").read_text(encoding="utf-8-sig", errors="replace")
    blob_match = re.search(r"^\s*([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+__Tad_AudioData_0\s*$", main_sym, re.M)
    assert blob_match, "fresh main.sym lacks __Tad_AudioData_0"
    blob_base = (int(blob_match.group(1), 16) << 16) | int(blob_match.group(2), 16)
    sym_offset = int(re.search(r"Tad_AudioDriver_Bin = \$([0-9A-Fa-f]+)", syms).group(1), 16)
    sym_size = int(re.search(r"Tad_AudioDriver_SIZE = (\d+)", syms).group(1))
    assert sym_offset == blob_base + offset
    assert sym_size == size
    assert sha(blob) == m["runtime_graph"]["audio_data_sha256_after_patch"]
    data_table = int(re.search(r"Tad_DataTable = \$([0-9A-Fa-f]+)", syms).group(1), 16)
    assert m["runtime_graph"]["data_table"] == f"${data_table:06X}"
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
