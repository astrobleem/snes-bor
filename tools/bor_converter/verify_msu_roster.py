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


def parse_bg_header(data):
    magic, version, roster_count, bg_count, bg_dir_offset = \
        struct.unpack_from("<8sBBBxI", data, 0)
    assert magic == pmr.MAGIC, f"bad magic: {magic!r}"
    return version, roster_count, bg_count, bg_dir_offset


def parse_bg_record(data, bg_dir_offset, slot):
    off = bg_dir_offset + slot * pmr.BG_RECORD_SIZE
    mode, w, h, hud_count, tile_count, data_offset, tilemap_offset, tiles_offset, hud_tiles_offset = \
        struct.unpack_from("<BxHBB2xH2xIIII4x", data, off)
    return {"mode": mode, "bg_tile_count": tile_count, "width_tiles": w,
            "height_tiles": h, "hud_tile_count": hud_count, "data_offset": data_offset,
            "tilemap_offset": tilemap_offset, "tiles_offset": tiles_offset,
            "hud_tiles_offset": hud_tiles_offset}


def check_bg_section(bg_dir="out/bg_boss", hud_dir="out/hud"):
    """Round-trip the static-mode BG section against bg_converter's own
    output files.

    Ground truth here is the converter's emitted .bin files read straight off
    disk -- not anything this packer computed -- so a packer offset/ordering
    bug cannot pass by agreeing with itself.
    """
    print("\n=== Check 3: BG section round-trips against bg_converter output (static) ===")
    if not os.path.isdir(bg_dir):
        print(f"SKIP: {bg_dir} does not exist (run tools/bg_converter/convert_bg.py)")
        return True

    prefixes = ["out/ralf", "out/jhun"]
    plain, _ = pmr.pack_roster(prefixes)
    msu_bytes, sidecar = pmr.pack_roster(prefixes, bgs=[(bg_dir, hud_dir)])

    version, roster_count, bg_count, bg_dir_offset = parse_bg_header(msu_bytes)
    assert version == pmr.FORMAT_VERSION, f"expected format_version {pmr.FORMAT_VERSION}, got {version}"
    assert bg_count == 1, f"expected bg_count 1, got {bg_count}"
    print(f"header OK: version={version} roster_count={roster_count} "
          f"bg_count={bg_count} bg_dir_offset={bg_dir_offset}")

    # Adding the BG section must not disturb the character directory or any
    # character blob. The 16-byte header itself legitimately differs -- bg_count
    # (0x0A) and bg_directory_offset (0x0C-0x0F) are exactly what v2 adds -- so
    # the stable region starts at DIRECTORY_BASE, not at 0.
    if msu_bytes[pmr.DIRECTORY_BASE:len(plain)] != plain[pmr.DIRECTORY_BASE:]:
        print("FAIL: appending the BG section changed the character directory or blobs")
        return False
    if msu_bytes[:pmr.DIRECTORY_BASE] == plain[:pmr.DIRECTORY_BASE]:
        print("FAIL: header did not record the BG section at all")
        return False
    if bg_dir_offset != len(plain):
        print(f"FAIL: bg_dir_offset {bg_dir_offset} != end of character data {len(plain)}")
        return False
    print(f"character region byte-identical to a v1-shaped pack ({len(plain)} bytes)")

    def _read(d, name):
        with open(os.path.join(d, name), "rb") as f:
            return f.read()

    with open(os.path.join(bg_dir, "manifest.json"), "r", encoding="utf-8") as f:
        bg_manifest = json.load(f)
    with open(os.path.join(hud_dir, "manifest.json"), "r", encoding="utf-8") as f:
        hud_manifest = json.load(f)

    rec = parse_bg_record(msu_bytes, bg_dir_offset, 0)
    expected = {"mode": pmr.BG_MODE_STATIC,
                "bg_tile_count": bg_manifest["unique_tiles"],
                "width_tiles": bg_manifest["width_tiles"],
                "height_tiles": bg_manifest["height_tiles"],
                "hud_tile_count": hud_manifest["tile_count"]}
    for k, v in expected.items():
        if rec[k] != v:
            print(f"FAIL: BG record {k} = {rec[k]}, expected {v}")
            return False
    print(f"BG record OK: mode={rec['mode']} {rec['bg_tile_count']} tiles, "
          f"{rec['width_tiles']}x{rec['height_tiles']}, "
          f"{rec['hud_tile_count']} hud tiles @ offset {rec['data_offset']}")

    exp_tilemap_offset = rec["data_offset"] + pmr.BG_CGRAM_BYTES
    exp_tiles_offset = exp_tilemap_offset + len(_read(bg_dir, "tilemap.bin"))
    exp_hud_tiles_offset = exp_tiles_offset + rec["bg_tile_count"] * pmr.BG_BYTES_PER_TILE
    if (rec["tilemap_offset"], rec["tiles_offset"], rec["hud_tiles_offset"]) != \
            (exp_tilemap_offset, exp_tiles_offset, exp_hud_tiles_offset):
        print(f"FAIL: v4 precomputed offsets {rec['tilemap_offset']}/{rec['tiles_offset']}/"
              f"{rec['hud_tiles_offset']} != expected {exp_tilemap_offset}/{exp_tiles_offset}/"
              f"{exp_hud_tiles_offset}")
        return False
    print(f"  v4 offsets OK: tilemap={rec['tilemap_offset']} tiles={rec['tiles_offset']} "
          f"hud_tiles={rec['hud_tiles_offset']}")

    if rec["bg_tile_count"] > pmr.BG_MAX_TILES_STATIC:
        print(f"FAIL: {rec['bg_tile_count']} tiles exceeds BG1 budget {pmr.BG_MAX_TILES_STATIC}")
        return False

    # Byte-compare each region against the converter's files.
    cur = rec["data_offset"]
    cgram = msu_bytes[cur:cur + pmr.BG_CGRAM_BYTES]
    exp_pal = bytearray(_read(bg_dir, "palette.bin"))
    exp_pal[:pmr.PALETTE_BYTES] = _read(hud_dir, "hud_palette.bin")
    if cgram != bytes(exp_pal):
        print("FAIL: CGRAM image does not match palette.bin + hud_palette.bin merge")
        return False
    if cgram[:pmr.PALETTE_BYTES] == b"\x00" * pmr.PALETTE_BYTES:
        print("FAIL: CGRAM sub-palette 0 is zeroed -- HUD colors were not merged in")
        return False
    cur += pmr.BG_CGRAM_BYTES

    for name, expected_bytes in (
            ("tilemap", _read(bg_dir, "tilemap.bin")),
            ("tiles", _read(bg_dir, "tiles.bin")),
            ("hud tiles", _read(hud_dir, "hud_tiles.bin"))):
        actual = msu_bytes[cur:cur + len(expected_bytes)]
        if actual != expected_bytes:
            print(f"FAIL: BG {name} region does not match source ({len(expected_bytes)} bytes)")
            return False
        print(f"  {name}: {len(expected_bytes)} bytes byte-identical")
        cur += len(expected_bytes)

    if cur != len(msu_bytes):
        print(f"FAIL: BG blob ends at {cur}, file is {len(msu_bytes)} bytes")
        return False

    print(f"total file size: {len(msu_bytes)} bytes")
    print("PASS")
    return True


def check_bg_section_streaming(bg_dir="out/bg_warehouse_stream", hud_dir="out/hud"):
    """Same round-trip as check_bg_section, but for a Phase 9 streaming BG:
    confirms the record reports mode=STREAMING with a width_tiles that
    would not fit the old static record's u8 field, and that the
    column-major cache-format tilemap comes back byte-identical to the
    converter's own tilemap.bin (not just the same length)."""
    print("\n=== Check 4: BG section round-trips against bg_converter output (streaming) ===")
    if not os.path.isdir(bg_dir):
        print(f"SKIP: {bg_dir} does not exist (run tools/bg_converter/convert_bg.py --streaming)")
        return True

    prefixes = ["out/ralf", "out/jhun"]
    msu_bytes, sidecar = pmr.pack_roster(prefixes, bgs=[(bg_dir, hud_dir)])
    version, roster_count, bg_count, bg_dir_offset = parse_bg_header(msu_bytes)
    assert version == pmr.FORMAT_VERSION, f"expected format_version {pmr.FORMAT_VERSION}, got {version}"

    def _read(d, name):
        with open(os.path.join(d, name), "rb") as f:
            return f.read()

    with open(os.path.join(bg_dir, "manifest.json"), "r", encoding="utf-8") as f:
        bg_manifest = json.load(f)
    with open(os.path.join(hud_dir, "manifest.json"), "r", encoding="utf-8") as f:
        hud_manifest = json.load(f)

    rec = parse_bg_record(msu_bytes, bg_dir_offset, 0)
    expected = {"mode": pmr.BG_MODE_STREAMING,
                "bg_tile_count": bg_manifest["unique_tiles"],
                "width_tiles": bg_manifest["width_tiles"],
                "height_tiles": bg_manifest["height_tiles"],
                "hud_tile_count": hud_manifest["tile_count"]}
    for k, v in expected.items():
        if rec[k] != v:
            print(f"FAIL: BG record {k} = {rec[k]}, expected {v}")
            return False
    print(f"BG record OK: mode={rec['mode']} (STREAMING) {rec['bg_tile_count']} tiles, "
          f"{rec['width_tiles']}x{rec['height_tiles']}, "
          f"{rec['hud_tile_count']} hud tiles @ offset {rec['data_offset']}")

    exp_tilemap_offset = rec["data_offset"] + pmr.BG_CGRAM_BYTES
    exp_tiles_offset = exp_tilemap_offset + len(_read(bg_dir, "tilemap.bin"))
    exp_hud_tiles_offset = exp_tiles_offset + rec["bg_tile_count"] * pmr.BG_BYTES_PER_TILE
    if (rec["tilemap_offset"], rec["tiles_offset"], rec["hud_tiles_offset"]) != \
            (exp_tilemap_offset, exp_tiles_offset, exp_hud_tiles_offset):
        print(f"FAIL: v4 precomputed offsets {rec['tilemap_offset']}/{rec['tiles_offset']}/"
              f"{rec['hud_tiles_offset']} != expected {exp_tilemap_offset}/{exp_tiles_offset}/"
              f"{exp_hud_tiles_offset}")
        return False
    # Also confirm hud_tiles_offset actually lands on the real HUD tiles region
    # in the packed bytes -- the engine will jump straight there via a raw
    # seek with no other ground-truth check along the way.
    exp_hud_tiles = _read(hud_dir, "hud_tiles.bin")
    actual_hud_tiles = msu_bytes[rec["hud_tiles_offset"]:rec["hud_tiles_offset"] + len(exp_hud_tiles)]
    if actual_hud_tiles != exp_hud_tiles:
        print(f"FAIL: bytes at hud_tiles_offset {rec['hud_tiles_offset']} don't match hud_tiles.bin")
        return False
    print(f"  v4 offsets OK: tilemap={rec['tilemap_offset']} tiles={rec['tiles_offset']} "
          f"hud_tiles={rec['hud_tiles_offset']} (hud tiles byte-identical at that offset)")

    if rec["width_tiles"] > 255:
        print(f"  width_tiles={rec['width_tiles']} exceeds a u8 -- confirms this record "
              f"genuinely needed the wider v3 field, not just a format bump")

    cur = rec["data_offset"] + pmr.BG_CGRAM_BYTES  # skip CGRAM, already checked by check_bg_section
    exp_tilemap = _read(bg_dir, "tilemap.bin")
    actual_tilemap = msu_bytes[cur:cur + len(exp_tilemap)]
    if actual_tilemap != exp_tilemap:
        print(f"FAIL: streaming tilemap region does not match tilemap.bin "
              f"({len(exp_tilemap)} bytes)")
        return False
    print(f"  column-major tilemap: {len(exp_tilemap)} bytes byte-identical")
    cur += len(exp_tilemap)

    exp_tiles = _read(bg_dir, "tiles.bin")
    actual_tiles = msu_bytes[cur:cur + len(exp_tiles)]
    if actual_tiles != exp_tiles:
        print(f"FAIL: streaming tiles region does not match tiles.bin ({len(exp_tiles)} bytes)")
        return False
    print(f"  tiles: {len(exp_tiles)} bytes byte-identical")

    print(f"total file size: {len(msu_bytes)} bytes")
    print("PASS")
    return True


def main():
    ok1 = check_real_roster()
    ok2 = check_large_offset_roster()
    ok3 = check_bg_section()
    ok4 = check_bg_section_streaming()
    if ok1 and ok2 and ok3 and ok4:
        print("\nAll checks passed.")
        return 0
    print("\nSome checks FAILED.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
