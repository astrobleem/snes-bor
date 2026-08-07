#!/usr/bin/env python3
"""Phase 1 isolation verification for pack_msu_roster.py -- no ROM, no
emulator. Two checks:

1. Pack the real Ralf + JHUN rosters, then re-derive every directory field
   and every blob byte independently (fresh manifest/palette loads, fresh
   bake_anim_bytes calls) and compare against what's actually sitting in the
   packed .msu bytes at each record's own data_offset. This is a genuine
   round-trip check against source `out/` data, not just re-checking the
   packer's output against itself.

2. Pack a synthetic 3-character roster where the first character is
   deliberately oversized (~90 idle frames of solid dummy pixel data) so
   that the second real character's data_offset lands past 65536 -- a real
   multi-character roster can cross this boundary well before all 8 slots
   are full (see pack_msu_roster.py's docstring).

   IMPORTANT SCOPE NOTE: this only proves the *file format* round-trips a
   >65536 offset correctly (struct's '<I' is 32-bit throughout, and Python
   ints have no 16-bit boundary to trip over -- there is no way for this
   check to fail the way real 65816 carry-propagation code can). It does
   NOT exercise, and cannot stand in for, the 24-bit (lo16+hi8) carry-add
   logic `Anim_LoadCharacter` will need in Phase 2 when it computes
   `idle_base = data_offset+32`, `walk_base = idle_base + idle_count*768`,
   etc. on real 65816 hardware/emulation. Treat that as entirely unverified
   until Phase 2 actually tests it against a build with a >65536-offset
   character loaded.

Usage:
    python verify_msu_roster.py   (must be run from the repo root -- the
    prefixes below are relative paths like "out/ralf")
"""
import json
import os
import shutil
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_pasm_animset
import pack_msu_roster as pmr

FRAME_PIXELS = pmr.bake_vram_frames.TARGET_W * pmr.bake_vram_frames.TARGET_H  # 1536


def parse_header(data):
    magic, version, roster_count = struct.unpack_from("<8sBB", data, 0)
    assert magic == pmr.MAGIC, f"bad magic: {magic!r}"
    return version, roster_count


def parse_record(data, slot):
    off = pmr.DIRECTORY_BASE + slot * pmr.RECORD_SIZE
    idle_c, walk_c, attack_c, idle_d, walk_d, attack_d, data_offset = \
        struct.unpack_from("<BBBBBB2xI4x", data, off)
    return {
        "idle_frame_count": idle_c, "walk_frame_count": walk_c, "attack_frame_count": attack_c,
        "idle_delay": idle_d, "walk_delay": walk_d, "attack_delay": attack_d,
        "data_offset": data_offset,
    }


def check_real_roster():
    print("=== Check 1: pack Ralf + JHUN, round-trip every field/byte against out/ ===")
    prefixes = ["out/ralf", "out/jhun"]
    msu_bytes, sidecar = pmr.pack_roster(prefixes)

    version, roster_count = parse_header(msu_bytes)
    assert version == pmr.FORMAT_VERSION, f"version mismatch: {version}"
    assert roster_count == len(prefixes), f"roster_count mismatch: {roster_count}"
    print(f"header OK: version={version} roster_count={roster_count}")

    # ralf's delays are documented (gen_pasm_animset.py's own docstring) as
    # already-validated ground truth (median-of-per-frame-delays, confirmed
    # to reproduce the original hand-written constants exactly). Assert
    # against that fixed oracle, not just load_manifest()'s own output --
    # comparing the packed record to load_manifest() alone would pass even
    # if load_manifest()'s median logic were wrong, since both sides of
    # that comparison call the same function.
    RALF_KNOWN_DELAYS = {"idle": 10, "walk": 8, "attack": 10}

    mismatches = 0
    for slot, prefix in enumerate(prefixes):
        record = parse_record(msu_bytes, slot)

        idle_count, idle_delay = gen_pasm_animset.load_manifest(f"{prefix}_idle")
        walk_count, walk_delay = gen_pasm_animset.load_manifest(f"{prefix}_walk")
        attack_count, attack_delay = gen_pasm_animset.load_manifest(f"{prefix}_attack")
        palette = gen_pasm_animset.load_palette(f"{prefix}_idle")

        if prefix == "out/ralf":
            actual_delays = {"idle": idle_delay, "walk": walk_delay, "attack": attack_delay}
            if actual_delays != RALF_KNOWN_DELAYS:
                print(f"  MISMATCH slot {slot} {prefix}: delays {actual_delays} != known-good {RALF_KNOWN_DELAYS}")
                mismatches += 1

        expected_record = {
            "idle_frame_count": idle_count, "walk_frame_count": walk_count, "attack_frame_count": attack_count,
            "idle_delay": idle_delay, "walk_delay": walk_delay, "attack_delay": attack_delay,
        }
        for k, v in expected_record.items():
            if record[k] != v:
                print(f"  MISMATCH slot {slot} {prefix} field {k}: packed={record[k]} expected={v}")
                mismatches += 1

        data_offset = record["data_offset"]
        expected_palette = b"".join(struct.pack("<H", v) for v in palette)
        actual_palette = msu_bytes[data_offset:data_offset + pmr.PALETTE_BYTES]
        if actual_palette != expected_palette:
            print(f"  MISMATCH slot {slot} {prefix}: palette bytes differ")
            mismatches += 1

        cursor = data_offset + pmr.PALETTE_BYTES
        for anim_name, count in (("idle", idle_count), ("walk", walk_count), ("attack", attack_count)):
            expected_bytes = pmr.bake_anim_bytes(f"{prefix}_{anim_name}")
            actual_bytes = msu_bytes[cursor:cursor + len(expected_bytes)]
            if actual_bytes != expected_bytes:
                n_diff = sum(1 for a, b in zip(actual_bytes, expected_bytes) if a != b)
                print(f"  MISMATCH slot {slot} {prefix} {anim_name}: {n_diff}/{len(expected_bytes)} bytes differ")
                mismatches += 1
            cursor += len(expected_bytes)

        print(f"  slot {slot} {prefix}: data_offset={data_offset} blob_size={cursor - data_offset} -- checked")

    # Unused slots (2-7) must be fully zeroed.
    for slot in range(len(prefixes), pmr.MAX_CHARACTERS):
        off = pmr.DIRECTORY_BASE + slot * pmr.RECORD_SIZE
        if msu_bytes[off:off + pmr.RECORD_SIZE] != b"\x00" * pmr.RECORD_SIZE:
            print(f"  MISMATCH: unused slot {slot} is not fully zeroed")
            mismatches += 1

    print(f"total file size: {len(msu_bytes)} bytes")
    print("PASS" if mismatches == 0 else f"FAIL ({mismatches} mismatches)")
    return mismatches == 0


def make_synthetic_char(base_dir, name, idle_frames, walk_frames=1, attack_frames=1):
    """Writes a minimal synthetic character directory tree (manifest.json +
    palette.txt + frameNN.bin, matching convert_animation.py's real output
    format) with a deliberately large idle_frame_count, so this character's
    blob alone is big enough to push a following real character's
    data_offset past 65536."""
    palette_lines = "".join(f"    lda #${(i * 0x111) & 0xFFFF:04X}\n" for i in range(16))
    for anim_name, frame_count, loop in (
        ("idle", idle_frames, 1), ("walk", walk_frames, 1), ("attack", attack_frames, 0)
    ):
        anim_dir = os.path.join(base_dir, f"{name}_{anim_name}")
        os.makedirs(anim_dir, exist_ok=True)
        frames = []
        for i in range(frame_count):
            bin_name = f"frame{i:02d}.bin"
            with open(os.path.join(anim_dir, bin_name), "wb") as f:
                f.write(bytes([i & 0x0F]) * FRAME_PIXELS)
            frames.append({"delay": 10, "bin": bin_name})
        manifest = {"entity": name, "anim": anim_name, "loop": loop, "frames": frames}
        with open(os.path.join(anim_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        with open(os.path.join(anim_dir, "palette.txt"), "w", encoding="utf-8") as f:
            f.write(palette_lines)
    return os.path.join(base_dir, name)


def check_large_offset_roster():
    print("\n=== Check 2: synthetic oversized roster, verify data_offset > 65536 round-trips ===")
    tmp_dir = tempfile.mkdtemp(prefix="msu_roster_synth_")
    try:
        # idle_frames=90 -> blob0 = 32 + (90+1+1)*768 = 70688 bytes, comfortably
        # pushing slot 1's data_offset (144 + 70688 = 70832) past 65536.
        pad_prefix = make_synthetic_char(tmp_dir, "padchar", idle_frames=90)
        real_prefix = "out/ralf"

        msu_bytes, sidecar = pmr.pack_roster([pad_prefix, real_prefix])

        pad_record = parse_record(msu_bytes, 0)
        real_record = parse_record(msu_bytes, 1)
        print(f"slot 0 (padchar): idle_frame_count={pad_record['idle_frame_count']} data_offset={pad_record['data_offset']}")
        print(f"slot 1 (ralf):    idle_frame_count={real_record['idle_frame_count']} data_offset={real_record['data_offset']}")

        if real_record["data_offset"] <= 65536:
            print(f"FAIL: slot 1 data_offset {real_record['data_offset']} did not cross 65536 -- "
                  f"increase padchar's idle_frames and retry")
            return False

        # Round-trip ralf's actual bytes at this >65536 offset against a fresh
        # independent recompute, proving no 16-bit truncation anywhere in the
        # packer's offset bookkeeping or in this parser's struct format.
        idle_count, _ = gen_pasm_animset.load_manifest(f"{real_prefix}_idle")
        palette = gen_pasm_animset.load_palette(f"{real_prefix}_idle")
        data_offset = real_record["data_offset"]
        expected_palette = b"".join(struct.pack("<H", v) for v in palette)
        actual_palette = msu_bytes[data_offset:data_offset + pmr.PALETTE_BYTES]
        if actual_palette != expected_palette:
            print("FAIL: ralf's palette at the >65536 offset does not match source data")
            return False

        expected_idle = pmr.bake_anim_bytes(f"{real_prefix}_idle")
        cursor = data_offset + pmr.PALETTE_BYTES
        actual_idle = msu_bytes[cursor:cursor + len(expected_idle)]
        if actual_idle != expected_idle:
            print("FAIL: ralf's idle frames at the >65536 offset do not match source data")
            return False

        print(f"total file size: {len(msu_bytes)} bytes")
        print("PASS")
        return True
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    ok1 = check_real_roster()
    ok2 = check_large_offset_roster()
    if ok1 and ok2:
        print("\nAll checks passed.")
        return 0
    print("\nSome checks FAILED.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
