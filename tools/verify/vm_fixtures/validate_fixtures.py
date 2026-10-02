#!/usr/bin/env python3
"""Validate the vendored Gate 0 VM fixtures against each other.

These files are the ground truth `plan_vm.md`'s Gate 0a and Gate 0 compare the
engine against, so they need to be trustworthy before either gate means
anything. They were vendored out of `openbor4086_sa1_bootstrap.zip`, where
nothing had ever been assembled or run -- so "the package shipped them" is not
evidence they are self-consistent. This script is that evidence.

It cross-checks, with no engine involved:
  - gate0_module.bin's revision-1 header against FORMAT.md's spec
  - its CRC32 (covering bytes $40..end) against the value stored in the header
  - its 8-byte instruction records against gate0_program.json
  - gate0_expected_slots.bin against the JSON's `expected.slots`

Run it before trusting a Gate 0 failure -- if this fails, the fixture is wrong,
not your interpreter.

This is also the seed of `verify_module`, one of the host-side tools listed in
plan_vm.md section 10. Extend it there rather than starting a new script.

    python tools/verify/vm_fixtures/validate_fixtures.py   -> FIXTURES: PASS
"""
from __future__ import annotations
import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# FORMAT.md "Initial slot images": type byte values.
VT = {"VT_EMPTY": 0, "VT_INTEGER": 1, "VT_DECIMAL": 2, "VT_PTR": 5, "VT_STR": 6}

SLOT_SIZE = 8      # numeric_profile 0 (Q16.16) -- 12 for profile 1 (binary64)
RECORD_SIZE = 8
HEADER_SIZE = 64


def main() -> int:
    mod = (ROOT / "gate0_module.bin").read_bytes()
    exp = (ROOT / "gate0_expected_slots.bin").read_bytes()
    fx = json.loads((ROOT / "gate0_program.json").read_text(encoding="utf-8"))

    failures: list[str] = []

    def chk(cond: bool, msg: str) -> None:
        print(f"  {'OK  ' if cond else 'FAIL'}  {msg}")
        if not cond:
            failures.append(msg)

    magic = mod[0:4]
    version, abi, profile = mod[4], mod[5], mod[6]
    instr_count, slot_count = struct.unpack_from("<HH", mod, 0x08)
    instr_off = struct.unpack_from("<I", mod, 0x18)[0]
    slots_off = struct.unpack_from("<I", mod, 0x1C)[0]
    module_size = struct.unpack_from("<I", mod, 0x34)[0]
    stored_crc = struct.unpack_from("<I", mod, 0x38)[0]

    print(f"module {len(mod)} B  expected_slots {len(exp)} B")
    print(f"instr_count={instr_count} slot_count={slot_count} "
          f"profile={profile} crc=0x{stored_crc:08X}\n")

    chk(magic == b"B48S", 'magic == "B48S"')
    chk(version == 1, "format_version == 1")
    chk(abi == 0x30, "opcode_abi == $30 (48 == OPCODE_END sentinel)")
    chk(profile == 0, "numeric_profile == 0 (Q16.16, the only profile in budget)")
    chk(module_size == len(mod), f"module_size {module_size} == actual {len(mod)}")
    chk(instr_count == len(fx["instructions"]),
        f"instruction_count {instr_count} == json {len(fx['instructions'])}")
    chk(slot_count == len(fx["initial_slots"]),
        f"slot_count {slot_count} == json {len(fx['initial_slots'])}")
    chk(HEADER_SIZE + instr_count * RECORD_SIZE + slot_count * SLOT_SIZE == len(mod),
        "header + records + slots == file size")
    chk(len(exp) == slot_count * SLOT_SIZE,
        f"expected_slots.bin is {slot_count} x {SLOT_SIZE} bytes")

    real_crc = zlib.crc32(mod[0x40:]) & 0xFFFFFFFF
    chk(real_crc == stored_crc,
        f"crc32 of $40..end == header crc (computed 0x{real_crc:08X})")

    bad_records = []
    for n, ins in enumerate(fx["instructions"]):
        off = instr_off + n * RECORD_SIZE
        opcode = mod[off]
        a, b, c = struct.unpack_from("<HHH", mod, off + 2)
        if (opcode, a, b, c) != (ins["opcode"], ins["a"], ins["b"], ins["c"]):
            bad_records.append(f"ip{n}({ins['name']})")
    chk(not bad_records,
        f"all {instr_count} instruction records match json {bad_records or ''}")

    bad_initial = []
    for n, slot in enumerate(fx["initial_slots"]):
        off = slots_off + n * SLOT_SIZE
        t = mod[off]
        v = struct.unpack_from("<i", mod, off + 4)[0]
        if t != VT[slot["type"]] or v != slot["value"]:
            bad_initial.append(f"slot{n}(got type={t} value={v})")
    chk(not bad_initial,
        f"initial slot image matches json {bad_initial or ''}")

    bad_expected = []
    for n, slot in enumerate(fx["expected"]["slots"]):
        off = n * SLOT_SIZE
        t = exp[off]
        v = struct.unpack_from("<i", exp, off + 4)[0]
        if t != VT[slot["type"]] or v != slot["value"]:
            bad_expected.append(f"slot{n}(got type={t} value={v})")
    chk(not bad_expected,
        f"expected_slots.bin matches json expected.slots {bad_expected or ''}")

    print()
    if failures:
        print(f"FIXTURES: FAIL ({len(failures)} check(s))")
        return 1
    print("FIXTURES: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
