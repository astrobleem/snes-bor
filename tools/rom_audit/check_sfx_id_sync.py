#!/usr/bin/env python3
"""G11 hardening: fail the build if SFX_HIT_ID (src/main.pasm) drifts from
the real generated SFX::sfx_hit value in soundwork/tad/build/audio-enums.inc.

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


def parse_enum_sfx_hit(text: str) -> int:
    m = re.search(r"\.enum\s+SFX\b(.*?)\.endenum", text, re.S)
    if not m:
        raise SystemExit(f"FAIL: no '.enum SFX ... .endenum' block found in {ENUMS_INC}")
    body = m.group(1)
    m2 = re.search(r"\bsfx_hit\s*=\s*(\d+)", body)
    if not m2:
        raise SystemExit(f"FAIL: no 'sfx_hit = N' entry inside SFX enum in {ENUMS_INC}")
    return int(m2.group(1))


def parse_pasm_sfx_hit_id(text: str) -> int:
    m = re.search(r"^SFX_HIT_ID\s*=\s*(\d+)", text, re.M)
    if not m:
        raise SystemExit(f"FAIL: no 'SFX_HIT_ID = N' constant found in {MAIN_PASM}")
    return int(m.group(1))


def main() -> int:
    if not ENUMS_INC.exists():
        print(f"FAIL: {ENUMS_INC} does not exist -- run soundwork/tad/rebuild.py first")
        return 1
    if not MAIN_PASM.exists():
        print(f"FAIL: {MAIN_PASM} does not exist")
        return 1

    real_id = parse_enum_sfx_hit(ENUMS_INC.read_text())
    pasm_id = parse_pasm_sfx_hit_id(MAIN_PASM.read_text())

    if real_id != pasm_id:
        print(
            f"FAIL: SFX_HIT_ID drift -- main.pasm says {pasm_id}, but "
            f"audio-enums.inc's real SFX::sfx_hit is {real_id}. Update "
            f"src/main.pasm's SFX_HIT_ID constant to {real_id}."
        )
        return 1

    print(f"OK: SFX_HIT_ID in sync ({pasm_id}) with audio-enums.inc")
    return 0


if __name__ == "__main__":
    sys.exit(main())
