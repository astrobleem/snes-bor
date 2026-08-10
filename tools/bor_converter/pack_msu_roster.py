#!/usr/bin/env python3
"""Packs up to 8 characters' idle/walk/attack animation data into a single
bor.msu file for runtime selection over MSU-1 (see the plan at
`temporal-swinging-hartmanis.md`), replacing the old flow of baking exactly
one character's data into the ROM at build time via gen_pasm_animset.py +
.incbin.

Reuses (imports, does not duplicate) gen_pasm_animset.py's manifest/palette
loading and bake_vram_frames.py's convert_frame_to_vram -- the same
byte-validated CC-DMA-format converter already shipped and proven correct
against real Mesen2 VRAM output.

File format (see the plan for the authoritative spec):

    0x00-0x07  magic "BORMSU1\0"
    0x08       format_version = 2
    0x09       roster_count (1-8)
    0x0A       bg_count (0-4)              [v2]
    0x0B       reserved
    0x0C-0x0F  bg_directory_offset (u32 LE, 0 when bg_count == 0)   [v2]

    0x10       directory: 8 records x 16 bytes = 128 bytes (0x10-0x8F)
      record N at 0x10 + (N<<4):
        +0  idle_frame_count   (u8)
        +1  walk_frame_count   (u8)
        +2  attack_frame_count (u8)
        +3  idle_delay         (u8)
        +4  walk_delay         (u8)
        +5  attack_delay       (u8)
        +6-7  reserved
        +8-11 data_offset (u32 LE) -- absolute byte offset of this
              character's blob from the start of the file
        +12-15 reserved

    0x90+      character blobs, packed sequentially:
      +0..31   palette: 16 x BGR555 LE
      +32..    idle_frame_count * 768 bytes
      next     walk_frame_count * 768 bytes
      next     attack_frame_count * 768 bytes

    then       BG directory (v2, only when bg_count > 0): 4 records x 16 bytes,
               located at bg_directory_offset.
      record N:
        +0-1   bg_tile_count   (u16 LE, <= 1024)
        +2     width_tiles     (u8, 32 or 64 -- see BG_VALID_WIDTHS; 64 means
               the tilemap blob below is two concatenated 32x32 pages, not one)
        +3     height_tiles    (u8, 28 -- real visible rows; always 28, even
               when width_tiles==64 stores 32 padding rows per page on disk)
        +4     hud_tile_count  (u8)
        +5-7   reserved
        +8-11  data_offset     (u32 LE) -- absolute byte offset of this
               screen's blob from the start of the file
        +12-15 reserved

    then       BG blobs, packed sequentially. One blob is everything the engine
               needs to stand up one screen, in the order it uploads them:
      +0..255       CGRAM image: 8 sub-palettes x 16 BGR555 LE. Sub-palette 0
                    holds the BG3 HUD colors (see bg_converter/convert_bg.py's
                    PALETTE_OFFSET note on why BG1 only uses slots 1-7);
                    slots 1-7 are the backdrop.
      +256..        BG1 tilemap: real-SNES tilemap words, row-major. 1792
                    bytes (32x28) if width_tiles==32; 4096 bytes (two
                    concatenated 32x32 pages) if width_tiles==64 -- see
                    _expected_tilemap_bytes().
      next          BG1 tiles: bg_tile_count * 32 bytes (4bpp planar)
      next          BG3 HUD tiles: hud_tile_count * 16 bytes (2bpp planar)

The BG section is appended AFTER the character blobs so that adding it does not
move any character data_offset -- a v1-era reader that ignores the new header
fields still finds every character exactly where it used to be.

Unused directory slots (roster_count <= N < 8) are left fully zeroed --
main.pasm's Anim_LoadCharacter treats a zero idle_frame_count as "no
character here" (see the plan's Phase 5, MSU-absent / zero-frame-count path).

data_offset is a full 32-bit field even though realistic rosters stay under
16MB, because a real multi-character roster can push it past 65536 well
before 8 slots are full -- every WRAM quantity derived from it in
Anim_LoadCharacter must be handled as 24-bit (lo16+hi8) with explicit carry
propagation, not a bare 16-bit add. This packer itself has no 16-bit
limitation (Python ints are arbitrary precision), so verify_msu_roster.py's
synthetic oversized-roster test only proves the *file format* round-trips a
>65536 offset correctly -- it cannot exercise, and is not a substitute for,
the real 65816 carry-add logic Phase 2 has to write and test on real
hardware/emulation.

Usage:
    python pack_msu_roster.py <out_msu_path> <prefix1> [<prefix2> ... up to 8]

Each <prefixN> follows the existing out/<name>_{idle,walk,attack}/
convention (convert_animation.py / convert_character.py output). Emits
<out_msu_path>.manifest.json alongside the .msu file: per-slot name, frame
counts, delays, and computed data_offset -- the independent ground truth
verify_msu_roster.py (and any future Mesen2 verification) checks packed
WRAM/file state against.
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_pasm_animset
import bake_vram_frames

MAGIC = b"BORMSU1\x00"
FORMAT_VERSION = 2
MAX_CHARACTERS = 8
RECORD_SIZE = 16
DIRECTORY_BASE = 0x10
HEADER_SIZE = DIRECTORY_BASE + MAX_CHARACTERS * RECORD_SIZE  # 0x90

PALETTE_BYTES = 32  # 16 BGR555 colors, 2 bytes each
ANIM_FRAME_BYTES = 768

# --- v2 BG section ---
MAX_BGS = 4
BG_RECORD_SIZE = 16
BG_CGRAM_BYTES = 256        # 8 sub-palettes x 16 colors x 2 bytes
BG_WIDTH_TILES = 32         # historical Phase 6 single-screen width
BG_HEIGHT_TILES = 28
# Phase 8 (plan.md 2.7): a whole-level BG can also be 64 tiles wide (a real
# BG1SC 64x32 map, two horizontally-adjacent 32x32 pages -- see
# bg_converter/snes_tiles.encode_tilemap_paged and convert_bg.py's
# convert_level()). Only 32 and 64 are valid widths for a single static load.
BG_VALID_WIDTHS = (32, 64)


def _expected_tilemap_bytes(width_tiles):
    """Bytes convert_bg.py emits for a given tilemap width.

    width=32 keeps the historical single-page format: only the 28 real rows
    are stored (1792B), since there is no second page and nothing ever reads
    past row 28. width=64 is two FULL 32x32 pages (4096B) -- page B must
    start exactly 1024 words after page A regardless of how many rows are
    visible, so rows 28-31 of each page are stored (zero-padded) even though
    they're never displayed.
    """
    if width_tiles == 32:
        return BG_WIDTH_TILES * BG_HEIGHT_TILES * 2
    if width_tiles == 64:
        return 64 * 32 * 2
    raise ValueError(f"unsupported BG tilemap width_tiles={width_tiles} "
                      f"(expected one of {BG_VALID_WIDTHS})")


BG_BYTES_PER_TILE = 32      # 4bpp
HUD_BYTES_PER_TILE = 16     # 2bpp
# BG1 char data must fit VRAM words $0000-$3FFF (1024 tiles); see
# bg_converter/convert_bg.py's docstring -- Phase 8 (plan.md 2.7) removed the
# boot-time BG2 blank-tile write that used to cap this at 512.
BG_MAX_TILES = 1024


def bake_anim_bytes(anim_dir):
    """Like bake_vram_frames.bake(), but returns bytes in-memory instead of
    writing a separate .bin file -- this packer emits one combined .msu
    blob per character, not per-animation asset files."""
    manifest_path = os.path.join(anim_dir, "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    blob = bytearray()
    for frame in manifest["frames"]:
        bin_path = os.path.join(anim_dir, frame["bin"])
        with open(bin_path, "rb") as f:
            pixels = f.read()
        blob += bake_vram_frames.convert_frame_to_vram(pixels)
    return bytes(blob)


def pack_character_blob(prefix):
    """Returns (blob_bytes, info_dict) for one character's palette + baked
    idle/walk/attack frames, sourced from <prefix>_{idle,walk,attack}/."""
    idle_dir = f"{prefix}_idle"
    walk_dir = f"{prefix}_walk"
    attack_dir = f"{prefix}_attack"

    idle_count, idle_delay = gen_pasm_animset.load_manifest(idle_dir)
    walk_count, walk_delay = gen_pasm_animset.load_manifest(walk_dir)
    attack_count, attack_delay = gen_pasm_animset.load_manifest(attack_dir)
    palette = gen_pasm_animset.load_palette(idle_dir)

    for count, name in ((idle_count, "idle"), (walk_count, "walk"), (attack_count, "attack")):
        if not (0 <= count <= 255):
            raise ValueError(f"{prefix}: {name}_frame_count {count} out of u8 range (0-255)")
    for delay, name in ((idle_delay, "idle"), (walk_delay, "walk"), (attack_delay, "attack")):
        if not (0 <= delay <= 255):
            raise ValueError(f"{prefix}: {name}_delay {delay} out of u8 range (0-255)")

    palette_bytes = b"".join(struct.pack("<H", v) for v in palette)
    assert len(palette_bytes) == PALETTE_BYTES

    idle_bytes = bake_anim_bytes(idle_dir)
    walk_bytes = bake_anim_bytes(walk_dir)
    attack_bytes = bake_anim_bytes(attack_dir)
    assert len(idle_bytes) == idle_count * ANIM_FRAME_BYTES
    assert len(walk_bytes) == walk_count * ANIM_FRAME_BYTES
    assert len(attack_bytes) == attack_count * ANIM_FRAME_BYTES

    blob = palette_bytes + idle_bytes + walk_bytes + attack_bytes

    info = {
        "prefix": prefix,
        "idle_frame_count": idle_count,
        "walk_frame_count": walk_count,
        "attack_frame_count": attack_count,
        "idle_delay": idle_delay,
        "walk_delay": walk_delay,
        "attack_delay": attack_delay,
        "blob_size": len(blob),
    }
    return blob, info


def build_record(info, data_offset):
    record = struct.pack(
        "<BBBBBB2xI4x",
        info["idle_frame_count"],
        info["walk_frame_count"],
        info["attack_frame_count"],
        info["idle_delay"],
        info["walk_delay"],
        info["attack_delay"],
        data_offset,
    )
    assert len(record) == RECORD_SIZE
    return record


def pack_bg_blob(bg_dir, hud_dir):
    """Returns (blob_bytes, info_dict) for one screen: CGRAM image + BG1
    tilemap + BG1 tiles + BG3 HUD tiles.

    `bg_dir` is a tools/bg_converter/convert_bg.py output directory,
    `hud_dir` a make_hud_tiles.py output directory. The HUD's 16-color
    sub-palette is merged over CGRAM slot 0, which convert_bg.py deliberately
    leaves zeroed for exactly this purpose -- so the engine can upload one
    contiguous 256-byte CGRAM image rather than two separate transfers.
    """
    with open(os.path.join(bg_dir, "manifest.json"), "r", encoding="utf-8") as f:
        bg_manifest = json.load(f)
    with open(os.path.join(hud_dir, "manifest.json"), "r", encoding="utf-8") as f:
        hud_manifest = json.load(f)

    def _read(d, name):
        with open(os.path.join(d, name), "rb") as f:
            return f.read()

    palette = bytearray(_read(bg_dir, "palette.bin"))
    tilemap = _read(bg_dir, "tilemap.bin")
    tiles = _read(bg_dir, "tiles.bin")
    hud_palette = _read(hud_dir, "hud_palette.bin")
    hud_tiles = _read(hud_dir, "hud_tiles.bin")

    width_tiles = bg_manifest["width_tiles"]
    height_tiles = bg_manifest["height_tiles"]
    if width_tiles not in BG_VALID_WIDTHS:
        raise ValueError(f"{bg_dir}: width_tiles={width_tiles}, expected one of {BG_VALID_WIDTHS}")
    if height_tiles != BG_HEIGHT_TILES:
        raise ValueError(f"{bg_dir}: height_tiles={height_tiles}, expected {BG_HEIGHT_TILES}")

    expected_tilemap_bytes = _expected_tilemap_bytes(width_tiles)
    if len(palette) != BG_CGRAM_BYTES:
        raise ValueError(f"{bg_dir}: palette.bin is {len(palette)}B, expected {BG_CGRAM_BYTES}")
    if len(tilemap) != expected_tilemap_bytes:
        raise ValueError(f"{bg_dir}: tilemap.bin is {len(tilemap)}B, expected "
                         f"{expected_tilemap_bytes} for width_tiles={width_tiles}")
    if len(hud_palette) != PALETTE_BYTES:
        raise ValueError(f"{hud_dir}: hud_palette.bin is {len(hud_palette)}B, "
                         f"expected {PALETTE_BYTES}")

    tile_count = bg_manifest["unique_tiles"]
    if len(tiles) != tile_count * BG_BYTES_PER_TILE:
        raise ValueError(f"{bg_dir}: tiles.bin is {len(tiles)}B, expected "
                         f"{tile_count * BG_BYTES_PER_TILE}")
    if tile_count > BG_MAX_TILES:
        raise ValueError(f"{bg_dir}: {tile_count} tiles exceeds the {BG_MAX_TILES}-tile "
                         f"BG1 VRAM budget")

    hud_tile_count = hud_manifest["tile_count"]
    if len(hud_tiles) != hud_tile_count * HUD_BYTES_PER_TILE:
        raise ValueError(f"{hud_dir}: hud_tiles.bin is {len(hud_tiles)}B, expected "
                         f"{hud_tile_count * HUD_BYTES_PER_TILE}")
    if not (0 <= hud_tile_count <= 255):
        raise ValueError(f"{hud_dir}: hud_tile_count {hud_tile_count} out of u8 range")

    # Merge the HUD's sub-palette over CGRAM slot 0.
    if any(palette[:PALETTE_BYTES]):
        raise ValueError(f"{bg_dir}: CGRAM sub-palette 0 is not zeroed; it is "
                         f"reserved for the BG3 HUD (see convert_bg.py PALETTE_OFFSET)")
    palette[:PALETTE_BYTES] = hud_palette

    blob = bytes(palette) + tilemap + tiles + hud_tiles
    info = {
        "bg_dir": bg_dir,
        "hud_dir": hud_dir,
        "level_entry": bg_manifest.get("level_entry"),
        "bg_tile_count": tile_count,
        "width_tiles": width_tiles,
        "height_tiles": height_tiles,
        "hud_tile_count": hud_tile_count,
        "blob_size": len(blob),
    }
    return blob, info


def build_bg_record(info, data_offset):
    record = struct.pack(
        "<HBBB3xI4x",
        info["bg_tile_count"],
        info["width_tiles"],
        info["height_tiles"],
        info["hud_tile_count"],
        data_offset,
    )
    assert len(record) == BG_RECORD_SIZE
    return record


def pack_roster(prefixes, bgs=None):
    """Returns (msu_bytes, manifest_sidecar_dict).

    `prefixes` is a list of 1-8 out/<name> character prefixes; unused
    directory slots stay zeroed. `bgs` is an optional list of
    (bg_dir, hud_dir) pairs, appended as the v2 BG section after the
    character blobs so no character data_offset moves.
    """
    if not (1 <= len(prefixes) <= MAX_CHARACTERS):
        raise ValueError(f"roster must have 1-{MAX_CHARACTERS} characters, got {len(prefixes)}")
    bgs = bgs or []
    if len(bgs) > MAX_BGS:
        raise ValueError(f"at most {MAX_BGS} BG screens, got {len(bgs)}")

    directory = bytearray(RECORD_SIZE * MAX_CHARACTERS)
    blobs = []
    sidecar_characters = []

    data_offset = HEADER_SIZE
    for slot, prefix in enumerate(prefixes):
        blob, info = pack_character_blob(prefix)
        record = build_record(info, data_offset)
        directory[slot * RECORD_SIZE:(slot + 1) * RECORD_SIZE] = record

        sidecar_characters.append({"slot": slot, "data_offset": data_offset, **info})

        blobs.append(blob)
        data_offset += len(blob)

    # --- v2 BG section, appended after every character blob ---
    bg_directory = b""
    bg_blobs = []
    sidecar_bgs = []
    bg_directory_offset = 0

    if bgs:
        # data_offset currently points just past the last character blob.
        bg_directory_offset = data_offset
        bg_dir_bytes = bytearray(BG_RECORD_SIZE * MAX_BGS)
        bg_data_offset = bg_directory_offset + BG_RECORD_SIZE * MAX_BGS

        for slot, (bg_dir, hud_dir) in enumerate(bgs):
            blob, info = pack_bg_blob(bg_dir, hud_dir)
            bg_dir_bytes[slot * BG_RECORD_SIZE:(slot + 1) * BG_RECORD_SIZE] = \
                build_bg_record(info, bg_data_offset)
            sidecar_bgs.append({"slot": slot, "data_offset": bg_data_offset, **info})
            bg_blobs.append(blob)
            bg_data_offset += len(blob)

        bg_directory = bytes(bg_dir_bytes)

    header = struct.pack("<8sBBBxI", MAGIC, FORMAT_VERSION, len(prefixes),
                         len(bgs), bg_directory_offset)
    assert len(header) == DIRECTORY_BASE

    msu_bytes = (header + bytes(directory) + b"".join(blobs)
                 + bg_directory + b"".join(bg_blobs))

    sidecar = {
        "format_version": FORMAT_VERSION,
        "roster_count": len(prefixes),
        "header_size": HEADER_SIZE,
        "total_size": len(msu_bytes),
        "characters": sidecar_characters,
        "bg_count": len(bgs),
        "bg_directory_offset": bg_directory_offset,
        "bgs": sidecar_bgs,
    }
    return msu_bytes, sidecar


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    out_msu_path = sys.argv[1]
    prefixes = sys.argv[2:]

    msu_bytes, sidecar = pack_roster(prefixes)

    os.makedirs(os.path.dirname(out_msu_path) or ".", exist_ok=True)
    with open(out_msu_path, "wb") as f:
        f.write(msu_bytes)

    manifest_path = out_msu_path + ".manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(sidecar, f, indent=2)

    print(f"wrote {out_msu_path}: {len(msu_bytes)} bytes, {len(prefixes)} character(s)")
    for c in sidecar["characters"]:
        print(f"  slot {c['slot']}: {c['prefix']} @ offset {c['data_offset']} "
              f"({c['blob_size']} bytes; idle={c['idle_frame_count']} "
              f"walk={c['walk_frame_count']} attack={c['attack_frame_count']})")
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
