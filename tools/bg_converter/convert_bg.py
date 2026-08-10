#!/usr/bin/env python3
"""Convert one BOR level screen into SNES Mode 1 BG1 data.

Pipeline:
    composite_scene  ->  320x240 RGB screen at scroll 0
    resize NEAREST   ->  256x224 (the SNES frame; see the aspect note below)
    -> 8x8 BGR555 tiles
    -> dedup_bgr555        (collapse visual duplicates BEFORE quantizing)
    -> build_palettes_tileaware  (k-means joint tile/sub-palette assignment)
    -> dedup_tiles         (collapse again after indexing)
    -> 4bpp planar tiles + real-SNES tilemap words + CGRAM palette

Aspect: BOR renders 320x240 (4:3, square pixels); the SNES renders 256x224 into
that same 4:3 frame with non-square pixels. Resampling 320x240 -> 256x224
directly is therefore geometrically correct on a 4:3 display, not a distortion.
NEAREST matches `bor_converter/convert_sprite.py`'s deliberate choice to avoid
smoothing, which would invent colors against a hard 15-color-per-palette budget.

Tile budget: BG1 character data lives at VRAM word $0000, so tile N occupies
word N*16 and tile 512 sits at word $2000 -- BG2's char base. Nothing renders
BG2 (TM = $15 = BG1+BG3+OBJ), so tiles there are never visible garbage; the
only real hazard was scpu_boot's one-shot BG2 blank-tile write (16 zero words
at word $2000, `scpu_bg2_blank` in main.pasm), which would have clobbered real
BG1 tile data past index 512. Phase 8 (plan.md 2.7) removed that write, so the
budget is now 1024 tiles -- also the 10-bit tilemap tile-index limit and
exactly where OBJ tiles start at word $4000.

(An earlier version of this comment claimed $2000-$3F7F was being rewritten
every frame by the SA-1 compositor. That is wrong: Scpu_CcdmaPump is defined in
main.pasm but never called -- the main loop dropped it when the character moved
to real OAM sprites. Checked before relying on it.)

The converter hard-errors above the cap rather than truncating; pick a simpler
scene instead. Measured whole-screen counts for the stock BOR levels range
from 395 (hotel) to 896 (pier/elevator, i.e. no dedup at all) -- all under
1024. See tools/bg_converter/measure_level_tiles.py for whole-LEVEL counts,
which is a different (larger) number once a level is wider than one screen.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

import snes_tiles as st  # noqa: E402
from composite_scene import (BOR_SCREEN_H, BOR_SCREEN_W, PakIndex,  # noqa: E402
                             composite_level, composite_screen, level_width,
                             load_level)
from tiledpalettequant import build_palettes_tileaware  # noqa: E402

SNES_W = 256
SNES_H = 224
W_TILES = SNES_W // st.TILE_SIZE   # 32
H_TILES = SNES_H // st.TILE_SIZE   # 28

# CGRAM sub-palette 0 (colors 0-15) is RESERVED for the BG3 HUD and is not
# available to the backdrop.
#
# Why: BG3 in mode 1 is 2bpp, and a 2bpp tile with tilemap palette field p reads
# CGRAM colors p*4 .. p*4+3. That range overlaps BG1's 4bpp palettes, which read
# p*16 .. p*16+15. If BG1 used all 8 sub-palettes there would be no CGRAM the
# HUD could own, and its colors would be whatever the backdrop happened to put
# in CGRAM 0-3. Leaving sub-palette 0 to the HUD gives BG3 palettes 0-3
# (CGRAM 0-15) exclusively, at the cost of one backdrop sub-palette.
#
# The backdrop therefore quantizes to 7 palettes and its tilemap palette ids are
# shifted up by PALETTE_OFFSET when encoded.
NUM_PALETTES = 7
PALETTE_OFFSET = 1
TOTAL_PALETTES = 8
COLORS_PER_PALETTE = 16

# BG1 tiles occupy VRAM words $0000-$3FFF (1024 tiles * 16 words/tile). The
# SA-1 compositor's Scpu_CcdmaPump, which used to write into $2000-$3F7F every
# frame, is dead code (defined, never called -- see this module's docstring);
# the only real hazard was scpu_boot's one-shot BG2 blank-tile write at word
# $2000, removed in Phase 8 (plan.md 2.7) specifically to raise this ceiling.
MAX_BG1_TILES = 1024


def convert(pak_path, level_entry, out_dir, panel_y=0, background_y=0,
            frontpanel_y=0, scroll_x=0, max_tiles=MAX_BG1_TILES, verbose=True):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    idx = PakIndex(pak_path)
    level = load_level(idx, level_entry)
    if verbose:
        print(f'level: {level}')

    # --- 1. composite one screen, then resample to the SNES frame ---
    scene = composite_screen(idx, level, panel_y=panel_y,
                             background_y=background_y,
                             frontpanel_y=frontpanel_y, scroll_x=scroll_x)
    Image.fromarray(scene).save(out_dir / 'scene_preview.png')

    snes_img = Image.fromarray(scene).resize((SNES_W, SNES_H), Image.NEAREST)
    rgb = np.array(snes_img, dtype=np.uint8)
    if verbose:
        print(f'composited {BOR_SCREEN_W}x{BOR_SCREEN_H} -> {SNES_W}x{SNES_H}, '
              f'{len(np.unique(rgb.reshape(-1, 3), axis=0))} unique colors')

    # --- 2. slice to BGR555 tiles ---
    bgr = st.rgb_array_to_bgr555(rgb)
    raw_tiles = st.image_to_tiles(bgr)
    assert raw_tiles.shape[0] == W_TILES * H_TILES

    # --- 3. dedup visual patterns before quantizing ---
    unique_raw, pos_to_uid, flip_flags = st.dedup_bgr555(raw_tiles)
    if verbose:
        print(f'{raw_tiles.shape[0]} tiles -> {len(unique_raw)} unique BGR555 patterns '
              f'(flip-aware)')

    # --- 4. tile-aware palette optimization over the unique patterns ---
    palettes, uniq_indexed, uniq_pal_ids = build_palettes_tileaware(
        unique_raw, num_palettes=NUM_PALETTES, colors_per_palette=COLORS_PER_PALETTE)
    if verbose:
        print(f'built {len(palettes)} sub-palettes of {COLORS_PER_PALETTE}')

    # --- 5. rebuild every screen position, re-applying its flip ---
    indexed_tiles = np.zeros((len(raw_tiles), st.TILE_SIZE, st.TILE_SIZE), dtype=np.uint8)
    pal_ids = np.zeros(len(raw_tiles), dtype=np.uint8)
    for i, uid in enumerate(pos_to_uid):
        tile = uniq_indexed[uid]
        hf, vf = flip_flags[i]
        if hf:
            tile = tile[:, ::-1]
        if vf:
            tile = tile[::-1, :]
        indexed_tiles[i] = tile
        pal_ids[i] = uniq_pal_ids[uid]

    # --- 6. dedup again post-indexing, then encode ---
    # Shift backdrop palette ids past the HUD-reserved sub-palette 0.
    unique_tiles, entries = st.dedup_tiles(indexed_tiles, pal_ids + PALETTE_OFFSET)
    n_tiles = len(unique_tiles)
    if verbose:
        print(f'{len(indexed_tiles)} tiles -> {n_tiles} unique 4bpp tiles')

    if n_tiles > max_tiles:
        raise SystemExit(
            f'ERROR: {n_tiles} unique tiles exceeds the {max_tiles}-tile BG1 budget.\n'
            f'  BG1 character data must fit VRAM words $0000-$3FFF (1024 tiles) --\n'
            f'  the 10-bit tilemap tile-index limit and where OBJ tiles start at\n'
            f'  word $4000. Pick a simpler scene, or composite a narrower window\n'
            f'  of a wider level (a whole multi-screen level needs the Phase 8\n'
            f'  streaming tile cache, not a bigger single-screen budget). Not\n'
            f'  truncating.')

    tiles_bin = st.encode_tileset(unique_tiles, bpp=4)
    tilemap_bin = st.encode_tilemap(entries, W_TILES, H_TILES)
    # Slot 0 stays zeroed here; make_hud_tiles.py owns CGRAM 0-15 and the
    # packer writes the HUD colors over it.
    cgram_palettes = [[0] * COLORS_PER_PALETTE] * PALETTE_OFFSET + list(palettes)
    palette_bin = st.encode_palette(cgram_palettes, TOTAL_PALETTES, COLORS_PER_PALETTE)

    (out_dir / 'tiles.bin').write_bytes(tiles_bin)
    (out_dir / 'tilemap.bin').write_bytes(tilemap_bin)
    (out_dir / 'palette.bin').write_bytes(palette_bin)

    manifest = {
        'level_entry': level_entry,
        'background': level.background,
        'panels': level.panels,
        'frontpanel': level.frontpanel,
        'width_px': SNES_W, 'height_px': SNES_H,
        'width_tiles': W_TILES, 'height_tiles': H_TILES,
        'unique_tiles': n_tiles,
        'num_palettes': NUM_PALETTES,
        'palette_offset': PALETTE_OFFSET,
        'colors_per_palette': COLORS_PER_PALETTE,
        'tiles_bytes': len(tiles_bin),
        'tilemap_bytes': len(tilemap_bin),
        'palette_bytes': len(palette_bin),
        'panel_y': panel_y, 'background_y': background_y,
        'frontpanel_y': frontpanel_y, 'scroll_x': scroll_x,
    }
    (out_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2))

    render_preview(tiles_bin, tilemap_bin, palette_bin, out_dir / 'preview.png')

    if verbose:
        print(f'wrote {out_dir}/: tiles.bin {len(tiles_bin)}B, '
              f'tilemap.bin {len(tilemap_bin)}B, palette.bin {len(palette_bin)}B')
        print(f'VRAM: {n_tiles} tiles = {n_tiles * 16} words '
              f'(${n_tiles * 16:04X} of $2000 budget)')
    return manifest


# Valid SNES BG1SC tilemap widths for a single static (non-streamed) load:
# 32 tiles (one 32x32 page, the historical Phase 6 format) or 64 tiles (two
# horizontally-adjacent 32x32 pages -- see snes_tiles.encode_tilemap_paged).
# A level whose real content is wider than 64 tiles (512 SNES px / 640 BOR px)
# needs the Phase 8 streaming tile cache, which does not exist yet -- this
# path hard-errors above that rather than silently truncating or picking a
# window.
PAGE_TILES = 32
MAX_WHOLE_LEVEL_TILES = 64


def convert_level(pak_path, level_entry, out_dir, panel_y=0, background_y=0,
                  frontpanel_y=0, max_tiles=MAX_BG1_TILES, verbose=True):
    """Convert an ENTIRE level (not one 320px screen) into a single static
    BG1 backdrop, for the Phase 8 "cheap version" scroll test: a level whose
    real content fits within 64 SNES tiles wide loads fully resident, with
    zero runtime streaming, so a real camera can pan across it.

    Differs from convert() only in what gets composited (the whole panel
    strip, not a 320px window) and how the tilemap is encoded (paged 64x32
    if the content needs a second page, per snes_tiles.encode_tilemap_paged) --
    the tile-dedup/quantize pipeline itself is identical.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    idx = PakIndex(pak_path)
    level = load_level(idx, level_entry)
    if verbose:
        print(f'level: {level}')

    # --- 1. composite the WHOLE level, then resample at the same 0.8 scale
    # convert() uses for a single screen (320x240 BOR -> 256x224 SNES) ---
    bor_w = level_width(idx, level)
    scene = composite_level(idx, level, panel_y=panel_y,
                            background_y=background_y,
                            frontpanel_y=frontpanel_y)
    assert scene.shape[1] == bor_w
    Image.fromarray(scene).save(out_dir / 'scene_preview.png')

    scale = SNES_W / BOR_SCREEN_W  # 0.8, same aspect-correct factor convert() uses
    snes_w_raw = round(bor_w * scale)
    content_w_tiles = -(-snes_w_raw // st.TILE_SIZE)  # ceil to a tile boundary
    if content_w_tiles > MAX_WHOLE_LEVEL_TILES:
        raise SystemExit(
            f'ERROR: level is {content_w_tiles} SNES tiles wide, exceeding the '
            f'{MAX_WHOLE_LEVEL_TILES}-tile single-static-load budget (a 64x32 '
            f'BG1SC map is the widest that can be loaded without runtime '
            f'streaming). This level needs the Phase 8 streaming tile cache, '
            f'not this whole-level path.')
    w_tiles = PAGE_TILES if content_w_tiles <= PAGE_TILES else MAX_WHOLE_LEVEL_TILES
    snes_w = w_tiles * st.TILE_SIZE

    snes_img = Image.fromarray(scene).resize((snes_w_raw, SNES_H), Image.NEAREST)
    rgb = np.zeros((SNES_H, snes_w, 3), dtype=np.uint8)  # pad to the page boundary
    rgb[:, :snes_w_raw] = np.array(snes_img, dtype=np.uint8)
    if verbose:
        print(f'composited {bor_w}x{BOR_SCREEN_H} -> {snes_w_raw}x{SNES_H} '
              f'(padded to {snes_w}x{SNES_H}, {content_w_tiles}/{w_tiles} tiles wide), '
              f'{len(np.unique(rgb.reshape(-1, 3), axis=0))} unique colors')

    # --- 2. slice to BGR555 tiles ---
    bgr = st.rgb_array_to_bgr555(rgb)
    raw_tiles = st.image_to_tiles(bgr)
    assert raw_tiles.shape[0] == w_tiles * H_TILES

    # --- 3. dedup visual patterns before quantizing ---
    unique_raw, pos_to_uid, flip_flags = st.dedup_bgr555(raw_tiles)
    if verbose:
        print(f'{raw_tiles.shape[0]} tiles -> {len(unique_raw)} unique BGR555 patterns '
              f'(flip-aware)')

    # --- 4. tile-aware palette optimization over the unique patterns ---
    palettes, uniq_indexed, uniq_pal_ids = build_palettes_tileaware(
        unique_raw, num_palettes=NUM_PALETTES, colors_per_palette=COLORS_PER_PALETTE)
    if verbose:
        print(f'built {len(palettes)} sub-palettes of {COLORS_PER_PALETTE}')

    # --- 5. rebuild every screen position, re-applying its flip ---
    indexed_tiles = np.zeros((len(raw_tiles), st.TILE_SIZE, st.TILE_SIZE), dtype=np.uint8)
    pal_ids = np.zeros(len(raw_tiles), dtype=np.uint8)
    for i, uid in enumerate(pos_to_uid):
        tile = uniq_indexed[uid]
        hf, vf = flip_flags[i]
        if hf:
            tile = tile[:, ::-1]
        if vf:
            tile = tile[::-1, :]
        indexed_tiles[i] = tile
        pal_ids[i] = uniq_pal_ids[uid]

    # --- 6. dedup again post-indexing, then encode ---
    unique_tiles, entries = st.dedup_tiles(indexed_tiles, pal_ids + PALETTE_OFFSET)
    n_tiles = len(unique_tiles)
    if verbose:
        print(f'{len(indexed_tiles)} tiles -> {n_tiles} unique 4bpp tiles')

    if n_tiles > max_tiles:
        raise SystemExit(
            f'ERROR: {n_tiles} unique tiles exceeds the {max_tiles}-tile BG1 budget.\n'
            f'  Pick a simpler level -- this whole-level path has no streaming\n'
            f'  fallback. Not truncating.')

    tiles_bin = st.encode_tileset(unique_tiles, bpp=4)
    if w_tiles == PAGE_TILES:
        tilemap_bin = st.encode_tilemap(entries, w_tiles, H_TILES)
    else:
        tilemap_bin = st.encode_tilemap_paged(entries, w_tiles, H_TILES,
                                              page_width=PAGE_TILES, page_height=PAGE_TILES)
    cgram_palettes = [[0] * COLORS_PER_PALETTE] * PALETTE_OFFSET + list(palettes)
    palette_bin = st.encode_palette(cgram_palettes, TOTAL_PALETTES, COLORS_PER_PALETTE)

    (out_dir / 'tiles.bin').write_bytes(tiles_bin)
    (out_dir / 'tilemap.bin').write_bytes(tilemap_bin)
    (out_dir / 'palette.bin').write_bytes(palette_bin)

    manifest = {
        'level_entry': level_entry,
        'background': level.background,
        'panels': level.panels,
        'frontpanel': level.frontpanel,
        'whole_level': True,
        'width_px': snes_w, 'height_px': SNES_H,
        'width_tiles': w_tiles, 'height_tiles': H_TILES,
        'content_width_tiles': content_w_tiles,  # real (unpadded) tile width;
                                                  # the camera must clamp scroll
                                                  # against THIS, not width_tiles,
                                                  # so padding tiles are never shown
        'unique_tiles': n_tiles,
        'num_palettes': NUM_PALETTES,
        'palette_offset': PALETTE_OFFSET,
        'colors_per_palette': COLORS_PER_PALETTE,
        'tiles_bytes': len(tiles_bin),
        'tilemap_bytes': len(tilemap_bin),
        'palette_bytes': len(palette_bin),
        'panel_y': panel_y, 'background_y': background_y,
        'frontpanel_y': frontpanel_y,
    }
    (out_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2))

    render_preview_paged(tiles_bin, tilemap_bin, palette_bin, w_tiles, H_TILES,
                         out_dir / 'preview.png')

    if verbose:
        print(f'wrote {out_dir}/: tiles.bin {len(tiles_bin)}B, '
              f'tilemap.bin {len(tilemap_bin)}B, palette.bin {len(palette_bin)}B')
        print(f'VRAM: {n_tiles} tiles = {n_tiles * 16} words '
              f'(${n_tiles * 16:04X} of $2000 budget); tilemap {w_tiles}x{PAGE_TILES}')
    return manifest


def render_preview_paged(tiles_bin, tilemap_bin, palette_bin, w_tiles, h_tiles_visible,
                         out_path, page_width=32, page_height=32):
    """Like render_preview, but decodes a paged (or single-page) tilemap and
    only draws the h_tiles_visible real rows of each page (the padding rows
    below that are never displayed)."""
    pal = np.frombuffer(palette_bin, dtype='<u2').reshape(-1, COLORS_PER_PALETTE)
    n_tiles = len(tiles_bin) // st.BYTES_PER_4BPP_TILE
    tiles = [st.decode_4bpp_tile(tiles_bin[i * 32:(i + 1) * 32]) for i in range(n_tiles)]
    words = np.frombuffer(tilemap_bin, dtype='<u2')
    n_pages = w_tiles // page_width

    out = np.zeros((h_tiles_visible * 8, w_tiles * 8, 3), dtype=np.uint8)
    for page in range(n_pages):
        base = page * page_width * page_height
        for row in range(h_tiles_visible):
            for col in range(page_width):
                w = int(words[base + row * page_width + col])
                tid = w & 0x03FF
                pid = (w >> 10) & 0x07
                hf = bool(w & (1 << 14))
                vf = bool(w & (1 << 15))
                t = tiles[tid]
                if hf:
                    t = t[:, ::-1]
                if vf:
                    t = t[::-1, :]
                out_col = page * page_width + col
                for y in range(8):
                    for x in range(8):
                        out[row * 8 + y, out_col * 8 + x] = st.bgr555_to_rgb(int(pal[pid][t[y, x]]))
    Image.fromarray(out).save(out_path)


def render_preview(tiles_bin, tilemap_bin, palette_bin, out_path):
    """Rebuild the screen FROM the emitted binaries.

    This decodes the real output rather than re-rendering the source, so a
    packing/tilemap bug shows up as a visibly wrong preview instead of hiding
    behind a correct-looking source image.
    """
    pal = np.frombuffer(palette_bin, dtype='<u2').reshape(-1, COLORS_PER_PALETTE)
    n_tiles = len(tiles_bin) // st.BYTES_PER_4BPP_TILE
    tiles = [st.decode_4bpp_tile(tiles_bin[i * 32:(i + 1) * 32]) for i in range(n_tiles)]

    out = np.zeros((H_TILES * 8, W_TILES * 8, 3), dtype=np.uint8)
    words = np.frombuffer(tilemap_bin, dtype='<u2')
    for row in range(H_TILES):
        for col in range(W_TILES):
            w = int(words[row * W_TILES + col])
            tid = w & 0x03FF
            pid = (w >> 10) & 0x07
            hf = bool(w & (1 << 14))
            vf = bool(w & (1 << 15))
            t = tiles[tid]
            if hf:
                t = t[:, ::-1]
            if vf:
                t = t[::-1, :]
            for y in range(8):
                for x in range(8):
                    out[row * 8 + y, col * 8 + x] = st.bgr555_to_rgb(int(pal[pid][t[y, x]]))
    Image.fromarray(out).save(out_path)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pak', default='Beats of Rage Original [v.3.0 Build 4086].pak')
    ap.add_argument('--level', default=r'DATA\EASY\4BEASY.TXT')
    ap.add_argument('-o', '--output', default='out/bg_warehouse')
    ap.add_argument('--panel-y', type=int, default=0)
    ap.add_argument('--background-y', type=int, default=0)
    ap.add_argument('--frontpanel-y', type=int, default=0)
    ap.add_argument('--scroll-x', type=int, default=0)
    ap.add_argument('--max-tiles', type=int, default=MAX_BG1_TILES)
    ap.add_argument('--whole-level', action='store_true',
                    help='composite the ENTIRE level (up to 64 SNES tiles wide) '
                         'instead of one 320px screen, for Phase 8 scroll testing')
    args = ap.parse_args()

    if args.whole_level:
        convert_level(args.pak, args.level, args.output,
                      panel_y=args.panel_y, background_y=args.background_y,
                      frontpanel_y=args.frontpanel_y, max_tiles=args.max_tiles)
    else:
        convert(args.pak, args.level, args.output,
                panel_y=args.panel_y, background_y=args.background_y,
                frontpanel_y=args.frontpanel_y, scroll_x=args.scroll_x,
                max_tiles=args.max_tiles)


if __name__ == '__main__':
    main()
