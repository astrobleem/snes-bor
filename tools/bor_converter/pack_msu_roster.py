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
    0x08       format_version = 4               [was 2 -- see BG record v3/v4 below]
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

    then       BG directory (only when bg_count > 0): 4 records x 32 bytes,
               located at bg_directory_offset. Bumped 16->20 in v3 to fit a
               streaming level's real width (up to 688 tiles for warehouse --
               doesn't fit a u8) and tile count (up to 65535, doesn't fit the
               old implicit <=1024 VRAM-fit assumption). Bumped again 20->32
               in v4 to add three precomputed absolute region offsets
               (tilemap_offset/tiles_offset/hud_tiles_offset) -- these are
               `data_offset + 256`, `+ tilemap_bytes`, `+ bg_tile_count*32`
               respectively, and could be derived by the engine at runtime,
               but the streaming loader needs to re-seek to each region
               independently (see StageColumn's header comment for why: its
               per-tile pixel fetches interleave with the tilemap read and
               break MSU-1's auto-increment sequential position, unlike the
               static loader's single unbroken burst). Computing them in
               Python once, here, avoids a 16x16->32-bit multiply-with-carry
               on the 65816 side for values that are already known and fixed
               at pack time -- this project's standing preference (see
               CLAUDE.md) is to keep computed-offset arithmetic off the
               65816 wherever a build-time constant will do.
      record N:
        +0     mode            (u8, BG_MODE_STATIC=0 or BG_MODE_STREAMING=1)
        +1     reserved
        +2-3   width_tiles     (u16 LE)
               STATIC:    32 or 64 (see BG_VALID_WIDTHS_STATIC; 64 means the
                          tilemap blob is two concatenated 32x32 pages)
               STREAMING: the level's real content width in tiles, no cap
                          beyond the u16 field (688 for warehouse) -- this is
                          also the level's real scroll-clamp width; there is
                          no separate padded/unpadded distinction the way
                          Phase 8's whole-level static mode needed, because
                          streaming never pads to a page boundary.
        +4     height_tiles    (u8, 28 -- real visible rows; always 28, even
               when a static width_tiles==64 stores 32 padding rows/page)
        +5     hud_tile_count  (u8)
        +6-7   reserved
        +8-9   bg_tile_count   (u16 LE) -- unique tile count. STATIC: <=1024
               (VRAM-fit budget). STREAMING: <=65535 (no VRAM-fit ceiling;
               see bg_converter/convert_bg.py's MAX_STREAMING_TILES).
        +10-11 reserved
        +12-15 data_offset       (u32 LE) -- absolute byte offset of this
               screen's blob (the CGRAM region's start) from the start of
               the file. Both modes use this for the initial seek.
        +16-19 tilemap_offset    (u32 LE) -- data_offset + 256. STREAMING
               only; the static loader never re-seeks mid-blob.
        +20-23 tiles_offset      (u32 LE) -- tilemap_offset + tilemap_bytes.
               STREAMING only.
        +24-27 hud_tiles_offset  (u32 LE) -- tiles_offset + bg_tile_count*32.
               STREAMING only.
        +28-31 reserved

    then       BG blobs, packed sequentially. One blob is everything the engine
               needs to stand up one screen, in the order it uploads them:
      +0..255       CGRAM image: 8 sub-palettes x 16 BGR555 LE. Sub-palette 0
                    holds the BG3 HUD colors (see bg_converter/convert_bg.py's
                    PALETTE_OFFSET note on why BG1 only uses slots 1-7);
                    slots 1-7 are the backdrop.
      +256..        BG1 tilemap.
               STATIC:    real-SNES tilemap words (2 bytes/tile), row-major.
                          1792 bytes (32x28) if width_tiles==32; 4096 bytes
                          (two concatenated 32x32 pages) if width_tiles==64 --
                          see _expected_tilemap_bytes().
               STREAMING: cache-format entries (3 bytes/tile -- u16 tile_id +
                          u8 attribute, see bg_converter/snes_tiles.
                          encode_tilemap_cache_entry), COLUMN-major (not
                          row-major): column 0 top-to-bottom, then column 1,
                          etc. width_tiles*height_tiles*3 bytes total. The
                          engine's column streamer seeks directly to
                          column_index * height_tiles * 3 within this region,
                          not through a separate index.
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
FORMAT_VERSION = 4
MAX_CHARACTERS = 8
RECORD_SIZE = 16
DIRECTORY_BASE = 0x10
HEADER_SIZE = DIRECTORY_BASE + MAX_CHARACTERS * RECORD_SIZE  # 0x90

PALETTE_BYTES = 32  # 16 BGR555 colors, 2 bytes each
ANIM_FRAME_BYTES = 768

# --- BG section (v2 static, v3 adds streaming) ---
MAX_BGS = 4
BG_RECORD_SIZE = 32         # bumped 16->20 in v3, 20->32 in v4 -- see module docstring

SPAWN_RECORD_SIZE = 7       # see build_spawn_table.py's module docstring for the layout
BG_CGRAM_BYTES = 256        # 8 sub-palettes x 16 colors x 2 bytes
BG_WIDTH_TILES = 32         # historical Phase 6 single-screen width
BG_HEIGHT_TILES = 28
# Phase 8 (plan.md 2.7): a whole-level static BG can also be 64 tiles wide (a
# real BG1SC 64x32 map, two horizontally-adjacent 32x32 pages -- see
# bg_converter/snes_tiles.encode_tilemap_paged and convert_bg.py's
# convert_level()). Only 32 and 64 are valid widths for a single static load.
BG_VALID_WIDTHS_STATIC = (32, 64)

BG_MODE_STATIC = 0
BG_MODE_STREAMING = 1

CACHE_ENTRY_BYTES = 3       # Phase 9: u16 tile_id + u8 attribute (streaming)


def _expected_tilemap_bytes(mode, width_tiles, height_tiles=BG_HEIGHT_TILES):
    """Bytes convert_bg.py emits for a given tilemap mode/width.

    STATIC width=32 is the historical single-page format: only the 28 real
    rows are stored (1792B). width=64 is two FULL 32x32 pages (4096B) --
    page B must start exactly 1024 words after page A regardless of how many
    rows are visible, so rows 28-31 of each page are stored (zero-padded)
    even though they're never displayed.

    STREAMING has no page concept: exactly width_tiles*height_tiles entries,
    column-major, 3 bytes each (see snes_tiles.encode_tilemap_cache_entry).
    """
    if mode == BG_MODE_STREAMING:
        return width_tiles * height_tiles * CACHE_ENTRY_BYTES
    if width_tiles == 32:
        return BG_WIDTH_TILES * BG_HEIGHT_TILES * 2
    if width_tiles == 64:
        return 64 * 32 * 2
    raise ValueError(f"unsupported static tilemap width_tiles={width_tiles} "
                      f"(expected one of {BG_VALID_WIDTHS_STATIC})")


BG_BYTES_PER_TILE = 32      # 4bpp
HUD_BYTES_PER_TILE = 16     # 2bpp
# BG1 char data must fit VRAM words $0000-$3FFF (1024 tiles); see
# bg_converter/convert_bg.py's docstring -- Phase 8 (plan.md 2.7) removed the
# boot-time BG2 blank-tile write that used to cap this at 512. Streaming
# (Phase 9) is exempt -- its whole point is a distinct-tile count that
# exceeds this, cached into VRAM at runtime rather than loaded whole.
BG_MAX_TILES_STATIC = 1024
BG_MAX_TILES_STREAMING = 65535  # u16 field ceiling, not a VRAM budget


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

    `bg_dir` is a tools/bg_converter/convert_bg.py output directory (static
    convert()/convert_level(), or Phase 9 convert_streaming() -- selected by
    the presence of manifest.json's "streaming" key), `hud_dir` a
    make_hud_tiles.py output directory. The HUD's 16-color sub-palette is
    merged over CGRAM slot 0, which convert_bg.py deliberately leaves zeroed
    for exactly this purpose -- so the engine can upload one contiguous
    256-byte CGRAM image rather than two separate transfers.
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

    mode = BG_MODE_STREAMING if bg_manifest.get("streaming") else BG_MODE_STATIC
    width_tiles = bg_manifest["width_tiles"]
    height_tiles = bg_manifest["height_tiles"]
    if height_tiles != BG_HEIGHT_TILES:
        raise ValueError(f"{bg_dir}: height_tiles={height_tiles}, expected {BG_HEIGHT_TILES}")

    tile_count = bg_manifest["unique_tiles"]
    max_tiles = BG_MAX_TILES_STREAMING if mode == BG_MODE_STREAMING else BG_MAX_TILES_STATIC

    if mode == BG_MODE_STATIC and width_tiles not in BG_VALID_WIDTHS_STATIC:
        raise ValueError(f"{bg_dir}: width_tiles={width_tiles}, expected one of "
                         f"{BG_VALID_WIDTHS_STATIC}")
    if not (0 <= width_tiles <= 0xFFFF):
        raise ValueError(f"{bg_dir}: width_tiles={width_tiles} out of u16 range")

    expected_tilemap_bytes = _expected_tilemap_bytes(mode, width_tiles, height_tiles)
    if len(palette) != BG_CGRAM_BYTES:
        raise ValueError(f"{bg_dir}: palette.bin is {len(palette)}B, expected {BG_CGRAM_BYTES}")
    if len(tilemap) != expected_tilemap_bytes:
        raise ValueError(f"{bg_dir}: tilemap.bin is {len(tilemap)}B, expected "
                         f"{expected_tilemap_bytes} for mode={mode} width_tiles={width_tiles}")
    if len(hud_palette) != PALETTE_BYTES:
        raise ValueError(f"{hud_dir}: hud_palette.bin is {len(hud_palette)}B, "
                         f"expected {PALETTE_BYTES}")

    if len(tiles) != tile_count * BG_BYTES_PER_TILE:
        raise ValueError(f"{bg_dir}: tiles.bin is {len(tiles)}B, expected "
                         f"{tile_count * BG_BYTES_PER_TILE}")
    if tile_count > max_tiles:
        raise ValueError(f"{bg_dir}: {tile_count} tiles exceeds the {max_tiles}-tile "
                         f"budget for mode={mode}")

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
        "mode": mode,
        "bg_tile_count": tile_count,
        "width_tiles": width_tiles,
        "height_tiles": height_tiles,
        "hud_tile_count": hud_tile_count,
        "tilemap_bytes": len(tilemap),
        "blob_size": len(blob),
    }
    return blob, info


def build_bg_record(info, data_offset, fp_offset=0):
    tilemap_offset = data_offset + BG_CGRAM_BYTES
    tiles_offset = tilemap_offset + info["tilemap_bytes"]
    hud_tiles_offset = tiles_offset + info["bg_tile_count"] * BG_BYTES_PER_TILE
    # Last 4 bytes were reserved padding through v4; v5 (Phase 10, plan.md
    # 2.10) repurposes them for fp_offset -- the absolute byte offset of this
    # BG's optional frontpanel blob (see pack_fp_blob/FP_RECORD_SIZE below),
    # or 0 if this BG has none. Deliberately NOT a new top-level directory
    # (the primary 16-byte header has no spare bytes to grow into without
    # shifting every existing absolute offset in the file) -- a frontpanel
    # is level-specific 1:1 with the BG it overlays, so hanging it off the
    # BG record it belongs to is the honest structure, not a workaround.
    record = struct.pack(
        "<BxHBB2xH2xIIIII",
        info["mode"],
        info["width_tiles"],
        info["height_tiles"],
        info["hud_tile_count"],
        info["bg_tile_count"],
        data_offset,
        tilemap_offset,
        tiles_offset,
        hud_tiles_offset,
        fp_offset,
    )
    assert len(record) == BG_RECORD_SIZE
    return record


# --- Frontpanel (FP) section (v5, Phase 10, plan.md 2.10): a second,
# independent streaming tile source for BG3, hung off a BG record via its
# now-repurposed reserved bytes (see build_bg_record above). Always
# streaming-mode (no static frontpanel path exists) and always 2bpp (BG3 in
# Mode 1) -- unlike the BG section, there is no mode/bpp field, because
# there is only one shape this data can take.
#
# Blob layout, self-describing (an inline 16-byte record prefix, not a
# separate directory -- see build_bg_record's comment for why):
#   +0-1   width_tiles   (u16 LE) -- MUST equal the owning BG's width_tiles;
#          both layers share one camera-column index, see
#          convert_frontpanel.py's own docstring on this constraint.
#   +2     height_tiles  (u8, always 28)
#   +3     reserved
#   +4-5   tile_count    (u16 LE)
#   +6-7   reserved
#   +8-11  tilemap_offset (u32 LE, absolute) -- precomputed here (Python),
#          not derived from a multiply on the 65816, matching BG record v4's
#          own precedent.
#   +12-15 tiles_offset   (u32 LE, absolute)
#   +16..  palette: 4 sub-palettes x 4 colors x 2 bytes = 32 bytes (BG3's
#          real usable ID range in this engine -- see
#          convert_frontpanel.py's CGRAM budget note. Sub-palette 0 stays
#          zeroed, same HUD-reservation convention as the BG section.)
#   next   tilemap: width_tiles*height_tiles*CACHE_ENTRY_BYTES(3) bytes,
#          column-major (identical format to the BG streaming tilemap).
#   next   tiles: tile_count * FP_BYTES_PER_TILE(16) bytes, 2bpp planar.
FP_RECORD_SIZE = 16
FP_PALETTE_BYTES = 32       # 4 sub-palettes x 4 colors x 2 bytes
FP_BYTES_PER_TILE = 16      # 2bpp
FP_MAX_TILES = 65535        # u16 field ceiling, not a real expected limit


def build_fp_blob(fp_dir, expected_width_tiles, data_offset):
    """Returns (blob_bytes, info_dict) for one frontpanel layer, with its
    self-describing 16-byte header already correctly filled in. Needs
    `data_offset` (where this blob will land in the final file) up front,
    unlike pack_bg_blob/build_bg_record's split -- this blob's own bytes
    (the header) depend on that offset, since there's no external directory
    record for it (see build_bg_record's comment for why)."""
    with open(os.path.join(fp_dir, "manifest.json"), "r", encoding="utf-8") as f:
        manifest = json.load(f)

    def _read(name):
        with open(os.path.join(fp_dir, name), "rb") as f:
            return f.read()

    palette = _read("palette.bin")
    tilemap = _read("tilemap.bin")
    tiles = _read("tiles.bin")

    if not manifest.get("streaming"):
        raise ValueError(f"{fp_dir}: not a streaming conversion (frontpanel "
                         f"has no static path)")
    width_tiles = manifest["width_tiles"]
    height_tiles = manifest["height_tiles"]
    tile_count = manifest["unique_tiles"]

    if width_tiles != expected_width_tiles:
        raise ValueError(f"{fp_dir}: width_tiles={width_tiles} does not match "
                         f"the owning BG's width_tiles={expected_width_tiles} "
                         f"-- both layers must share one camera-column index")
    if len(palette) != FP_PALETTE_BYTES:
        raise ValueError(f"{fp_dir}: palette.bin is {len(palette)}B, expected "
                         f"{FP_PALETTE_BYTES}")
    expected_tilemap_bytes = width_tiles * height_tiles * CACHE_ENTRY_BYTES
    if len(tilemap) != expected_tilemap_bytes:
        raise ValueError(f"{fp_dir}: tilemap.bin is {len(tilemap)}B, expected "
                         f"{expected_tilemap_bytes}")
    if len(tiles) != tile_count * FP_BYTES_PER_TILE:
        raise ValueError(f"{fp_dir}: tiles.bin is {len(tiles)}B, expected "
                         f"{tile_count * FP_BYTES_PER_TILE}")
    if tile_count > FP_MAX_TILES:
        raise ValueError(f"{fp_dir}: {tile_count} tiles exceeds the "
                         f"{FP_MAX_TILES}-tile field ceiling")

    tilemap_offset = data_offset + FP_RECORD_SIZE + FP_PALETTE_BYTES
    tiles_offset = tilemap_offset + len(tilemap)
    header = struct.pack(
        "<HBxH2xII",
        width_tiles, height_tiles, tile_count,
        tilemap_offset, tiles_offset,
    )
    assert len(header) == FP_RECORD_SIZE
    blob = header + palette + tilemap + tiles

    info = {
        "fp_dir": fp_dir,
        "width_tiles": width_tiles,
        "height_tiles": height_tiles,
        "tile_count": tile_count,
        "tilemap_offset": tilemap_offset,
        "tiles_offset": tiles_offset,
        "blob_size": len(blob),
    }
    return blob, info


def pack_roster(prefixes, bgs=None, fps=None, spawn_blob=None):
    """Returns (msu_bytes, manifest_sidecar_dict).

    `prefixes` is a list of 1-8 out/<name> character prefixes; unused
    directory slots stay zeroed. `bgs` is an optional list of
    (bg_dir, hud_dir) pairs, appended as the v2 BG section after the
    character blobs so no character data_offset moves. `fps` (v5, Phase 10,
    plan.md 2.10) is an optional list the SAME LENGTH as `bgs` -- fps[i] is
    either an out/<name> convert_frontpanel.py output dir for bgs[i], or
    None if that BG has no frontpanel layer. Each present frontpanel is
    packed immediately after its owning BG's own blob (see build_fp_blob),
    with its offset threaded into that BG's record (build_bg_record).

    `spawn_blob` (spawn-table phase, 2026-08-16) is an optional raw bytes
    blob from build_spawn_table.py -- this project's single global spawn
    queue, not a per-slot directory entry (there is only ever one level's
    worth of spawn data, same "bake one instance in" pattern as BG_SCREENS/
    FP_SCREENS). Appended at the very end of the file so it can never move
    any earlier section's offset. Its absolute file offset and record count
    (spawn_blob is a flat array of 7-byte records, see build_spawn_table.py)
    are returned in the sidecar for build_rom.py to cross-check against
    main.pasm's hand-synced SPAWN_MSU_OFFSET/SPAWN_COUNT constants -- same
    "computed here, hardcoded there, checked at build time" convention as
    the RESET/NMI/IRQ vector constants CLAUDE.md already documents as a
    standing, accepted (not automatically enforced) risk.
    """
    if not (1 <= len(prefixes) <= MAX_CHARACTERS):
        raise ValueError(f"roster must have 1-{MAX_CHARACTERS} characters, got {len(prefixes)}")
    bgs = bgs or []
    if len(bgs) > MAX_BGS:
        raise ValueError(f"at most {MAX_BGS} BG screens, got {len(bgs)}")
    fps = fps or ([None] * len(bgs))
    if len(fps) != len(bgs):
        raise ValueError(f"fps must be the same length as bgs ({len(bgs)}), got {len(fps)}")

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
            this_bg_data_offset = bg_data_offset
            bg_blobs.append(blob)
            bg_data_offset += len(blob)

            fp_offset = 0
            fp_info = None
            fp_dir = fps[slot]
            if fp_dir is not None:
                fp_offset = bg_data_offset
                fp_blob, fp_info = build_fp_blob(fp_dir, info["width_tiles"], fp_offset)
                bg_blobs.append(fp_blob)
                bg_data_offset += len(fp_blob)

            bg_dir_bytes[slot * BG_RECORD_SIZE:(slot + 1) * BG_RECORD_SIZE] = \
                build_bg_record(info, this_bg_data_offset, fp_offset)
            sidecar_bg = {"slot": slot, "data_offset": this_bg_data_offset, **info}
            if fp_info is not None:
                sidecar_bg["fp"] = {"data_offset": fp_offset, **fp_info}
            sidecar_bgs.append(sidecar_bg)

        bg_directory = bytes(bg_dir_bytes)

    header = struct.pack("<8sBBBxI", MAGIC, FORMAT_VERSION, len(prefixes),
                         len(bgs), bg_directory_offset)
    assert len(header) == DIRECTORY_BASE

    msu_bytes = (header + bytes(directory) + b"".join(blobs)
                 + bg_directory + b"".join(bg_blobs))

    spawn_offset = 0
    spawn_count = 0
    if spawn_blob:
        spawn_offset = len(msu_bytes)
        spawn_count = len(spawn_blob) // SPAWN_RECORD_SIZE
        assert len(spawn_blob) % SPAWN_RECORD_SIZE == 0, \
            f"spawn_blob length {len(spawn_blob)} not a multiple of {SPAWN_RECORD_SIZE}"
        msu_bytes = msu_bytes + spawn_blob

    sidecar = {
        "format_version": FORMAT_VERSION,
        "roster_count": len(prefixes),
        "header_size": HEADER_SIZE,
        "total_size": len(msu_bytes),
        "characters": sidecar_characters,
        "bg_count": len(bgs),
        "bg_directory_offset": bg_directory_offset,
        "bgs": sidecar_bgs,
        "spawn_offset": spawn_offset,
        "spawn_count": spawn_count,
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
