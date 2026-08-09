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

Tile budget: BG1 character data lives at VRAM word $0000 and must not run into
the BG2 char base at $2000, which caps this at 512 tiles (8192 words / 16).
That region is NOT reclaimable: although BG2 is disabled on the main screen, the
SA-1 compositor actively writes COMPOSITOR_BLIT_COUNT(21) * 24 = 504 tiles into
$2000-$3F7F every frame, and there is no free 8064-word region left to relocate
it to. 512 is a hard ceiling. The converter hard-errors above it rather than
truncating; pick a simpler scene instead. Measured counts for the stock BOR
levels range from 395 (hotel) to 896 (pier/elevator, i.e. no dedup at all), so
scene choice matters more than any tuning knob here.
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
                             composite_screen, load_level)
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

# BG1 tiles occupy VRAM words $0000-$1FFF. $2000 upward is NOT free: the SA-1
# compositor actively writes COMPOSITOR_BLIT_COUNT*24 = 504 tiles into the BG2
# char base at $2000-$3F7F every frame (see main.pasm's COMPOSITOR_BLIT_COUNT).
# 8192 words / 16 words-per-tile = 512 tiles is a hard ceiling, not a soft one.
MAX_BG1_TILES = 512


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
            f'  BG1 character data must fit VRAM words $0000-$1FFF to stay clear of\n'
            f'  the BG2 char base at $2000, which the SA-1 compositor writes every\n'
            f'  frame (504 tiles) -- that region is not reclaimable.\n'
            f'  Pick a simpler scene. Stock levels that fit: 6AEASY (hotel, 395),\n'
            f'  6BEASY (boss, 429). Not truncating.')

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
    args = ap.parse_args()

    convert(args.pak, args.level, args.output,
            panel_y=args.panel_y, background_y=args.background_y,
            frontpanel_y=args.frontpanel_y, scroll_x=args.scroll_x,
            max_tiles=args.max_tiles)


if __name__ == '__main__':
    main()
