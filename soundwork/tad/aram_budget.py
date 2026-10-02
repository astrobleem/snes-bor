#!/usr/bin/env python3
"""Report TAD v0.3.0 ARAM spans from generated audio-data artifacts."""
from __future__ import annotations

import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASM = ROOT / "soundwork/tad/build/audio-data.s"
BIN = ROOT / "soundwork/tad/build/audio-data.bin"


def exported(name: str) -> int:
    match = re.search(rf"^Tad_{name}\s*:=\s*__Tad_AudioData_0\s*\+\s*([0-9]+)$",
                      ASM.read_text(encoding="utf-8"), re.M)
    if not match:
        raise SystemExit(f"missing generated export Tad_{name}")
    return int(match.group(1))


def main() -> int:
    text = ASM.read_text(encoding="utf-8")
    data = BIN.read_bytes()
    loader = int(re.search(r"Tad_Loader_SIZE\s*=\s*([0-9]+)", text).group(1))
    driver = int(re.search(r"Tad_AudioDriver_SIZE\s*=\s*([0-9]+)", text).group(1))
    table = exported("DataTable")
    entries = [int.from_bytes(data[table + i * 3:table + i * 3 + 3], "little")
               for i in range(2)]
    end = int.from_bytes(data[table + 6:table + 8], "little")
    common = entries[1] - entries[0]
    song = end - entries[1]
    resident = driver + common + song
    aram = 0x10000 - 0x0200
    print(f"TAD loader (transient): {loader} bytes")
    print(f"TAD driver (resident): {driver} bytes")
    print(f"common data (including BEAT1): {common} bytes")
    print(f"song data: {song} bytes")
    print(f"resident used from $0200: {resident} bytes")
    print(f"resident free to $FFFF: {aram - resident} bytes")
    if common <= 0 or song <= 0 or resident > aram:
        raise SystemExit("ARAM budget invalid")
    print("TAD ARAM BUDGET PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
