#!/usr/bin/env python3
"""Fail the build if resident semantic SFX IDs drift from generated TAD IDs.

Poppy cannot .include a ca65 .enum file directly, so main.pasm carries its
own literal `SFX_HIT_ID = N` constant (see that definition's own comment).
This script is the enforcement half of that convention: it parses the real
compiler-generated enum and the Poppy literal, and fails loudly if they
ever disagree, rather than trusting a comment to stay honest by hand.

Run from anywhere; paths are derived from this file's location.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENUMS_INC = REPO_ROOT / "soundwork" / "tad" / "build" / "audio-enums.inc"
MAIN_PASM = REPO_ROOT / "src" / "main.pasm"


def parse_enum_sfx_ids(text: str) -> dict[str, int]:
    m = re.search(r"\.enum\s+SFX\b(.*?)\.endenum", text, re.S)
    if not m:
        raise SystemExit(f"FAIL: no '.enum SFX ... .endenum' block found in {ENUMS_INC}")
    body = m.group(1)
    values = {}
    for name in ("sfx_hit", "sfx_fall"):
        m2 = re.search(rf"\b{name}\s*=\s*(\d+)", body)
        if not m2:
            raise SystemExit(f"FAIL: no '{name} = N' entry inside SFX enum in {ENUMS_INC}")
        values[name] = int(m2.group(1))
    if len(set(values.values())) != len(values):
        raise SystemExit(f"FAIL: duplicate generated resident SFX IDs: {values}")
    return values


def parse_pasm_sfx_ids(text: str) -> dict[str, int]:
    values = {}
    for name in ("SFX_HIT_ID", "SFX_FALL_ID"):
        m = re.search(rf"^{name}\s*=\s*(\d+)", text, re.M)
        if not m:
            raise SystemExit(f"FAIL: no '{name} = N' constant found in {MAIN_PASM}")
        values[name] = int(m.group(1))
    return values


def main() -> int:
    if not ENUMS_INC.exists():
        print(f"FAIL: {ENUMS_INC} does not exist -- run soundwork/tad/rebuild.py first")
        return 1
    if not MAIN_PASM.exists():
        print(f"FAIL: {MAIN_PASM} does not exist")
        return 1

    generated = parse_enum_sfx_ids(ENUMS_INC.read_text())
    pasm = parse_pasm_sfx_ids(MAIN_PASM.read_text())
    expected = {"SFX_HIT_ID": generated["sfx_hit"], "SFX_FALL_ID": generated["sfx_fall"]}
    if pasm != expected:
        print(f"FAIL: resident SFX ID drift -- main.pasm={pasm}, generated={expected}")
        return 1
    print(f"OK: resident SFX IDs in sync ({pasm}) with audio-enums.inc")
    return 0


if __name__ == "__main__":
    sys.exit(main())
