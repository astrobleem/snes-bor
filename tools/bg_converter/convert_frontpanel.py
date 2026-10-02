#!/usr/bin/env python3
"""Convert a BOR level's frontpanel art into a streaming BG3 foreground layer.

Phase 10 (plan.md 2.10), Step 1. This is the frontpanel-occlusion fix's
converter half: BOR's frontpanel (e.g. a chain-link fence) is meant to
render IN FRONT of characters, which this project's existing BG1 backdrop
pipeline cannot do (OBJ sprites always render above BG1 here). This module
produces a SEPARATE streaming tile source for BG3, using BG3's existing
per-tile priority bit (already proven by the HUD) to sit above OBJ.

Pipeline (deliberately parallel to convert_bg.py's convert_streaming(),
reusing the same snes_tiles.py primitives -- see that function's docstring
for the shared shape):
    composite frontpanel ONLY (not background+panels -- composite_scene.py's
        _composite() always flattens all three; this module has its own
        frontpanel-only compositor that keeps the transparency mask instead
        of discarding it)
    resize NEAREST -> same 0.8x scale as the BG1 pipeline, same w_tiles, so
        both layers' tilemaps index identical world columns
    -> 8x8 BGR555 tiles (masked-out pixels baked to a fixed sentinel color
        so they quantize to color index 0 = transparent, letting BG1/OBJ
        show through in real SNES 2bpp/4bpp semantics -- no separate "is
        this tile blank" bookkeeping needed)
    -> dedup_bgr555 (flip-aware, same as BG1)
    -> build_palettes_tileaware, but 2bpp (colors_per_palette=4) and
        constrained to the 3 sub-palette IDs the BG3/HUD CGRAM layout
        actually leaves free (see NUM_PALETTES below -- do not raise this
        without also revisiting main.pasm's CGRAM allocation, it is not a
        converter-side knob)
    -> dedup_tiles, encode 2bpp planar tiles + column-major streaming
        tilemap (CACHE_ENTRY_BYTES format, unchanged from BG1's -- no
        priority bit stored per-tile; every frontpanel tile needs the
        priority bit, so the ENGINE sets it uniformly when committing to
        VRAM, not this converter -- see plan.md 2.10 Step 2/3)

CGRAM budget (plan.md 2.10's own sizing note, restated precisely here
after checking main.pasm/convert_bg.py's actual CGRAM allocation -- the
plan's first-pass estimate of "7 free BG3 sub-palettes" was wrong):
BG3 in mode 1 is 2bpp, tilemap palette field reads CGRAM[id*4, id*4+4).
BG1 is 4bpp and already uses sub-palette IDs 1-7 (CGRAM 16-127) for real
background content (convert_bg.py's PALETTE_OFFSET=1), leaving only
CGRAM 0-15 -- BG3 IDs 0-3 -- free for BG3 at all; using BG3 ID 4+ would
alias into CGRAM bytes BG1 already owns and corrupt one or the other. The
HUD (main.pasm, `Character_HitApply`-adjacent HUD code) hardcodes BG3
palette 0. That leaves exactly 3 free BG3 sub-palette IDs (1, 2, 3) for
the frontpanel: 3 palettes x 3 usable colors (index 0 reserved
transparent) = 9 real distinct colors, well under the ~22 measured in
stage 1A's fence art. This is a real, load-bearing quantization
constraint, not a rough guess -- if the output looks visibly posterized,
that is this budget, not a bug, and the only ways out are: accept it,
reduce frontpanel content requirements, or claw back CGRAM from BG1's
7-palette budget (a real product tradeoff against background quality, not
a converter change).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

import snes_tiles as st  # noqa: E402
from composite_scene import BOR_SCREEN_H, PakIndex, level_width, load_level  # noqa: E402
from tiledpalettequant import build_palettes_tileaware  # noqa: E402

SNES_W = 256
SNES_H = 224
H_TILES = SNES_H // st.TILE_SIZE  # 28

# See module docstring's CGRAM budget note -- do not raise without also
# changing main.pasm's CGRAM allocation.
NUM_PALETTES = 3
PALETTE_OFFSET = 1     # BG3 sub-palette 0 belongs to the HUD
TOTAL_PALETTES = 4     # BG3's real usable ID range in this engine (0-3)
COLORS_PER_PALETTE = 4

# BOR's own transparency convention (composite_scene.py's docstring: GIF
# palette index 0 decodes to this RGB in the stock pak). Baking masked-out
# pixels to this exact color, then telling the quantizer it's the
# transparent color, keeps "is this pixel real content" decidable purely
# from the already-existing RGB/BGR555 data -- no parallel mask array has
# to survive dedup/quantize/pack, all of which only know about pixel
# colors.
TRANS_RGB = (252, 0, 255)

# Cache-entry tile-ID field is a full 16-bit LE integer (see
# snes_tiles.encode_tilemap_cache_entry) -- generous headroom, not a real
# expected limit. The worst-case-window number that actually matters is
# checked separately by verify_window_budget() below.
MAX_STREAMING_TILES = 65536


def _composite_frontpanel_only(pak_index, level, width, frontpanel_y=0):
    """Like composite_scene.py's _composite(), but frontpanel ONLY --
    background and panels are never drawn, and (unlike that function,
    which discards transparency once background/panels are painted
    underneath) the mask survives so masked-out pixels can be baked to
    TRANS_RGB instead of staying whatever composite_scene would have put
    there (that function always leaves unmasked canvas pixels at (0,0,0)
    -- coincidentally close to TRANS_RGB's intent but not guaranteed
    stable, so don't rely on it silently matching).
    """
    canvas = np.full((BOR_SCREEN_H, width, 3), TRANS_RGB, dtype=np.uint8)
    if not level.frontpanel:
        return canvas
    f_rgb, f_mask = pak_index.image(level.frontpanel)
    sh = min(f_rgb.shape[0], BOR_SCREEN_H - frontpanel_y)
    if sh <= 0:
        return canvas
    f_rgb_c = f_rgb[:sh]
    f_mask_c = f_mask[:sh]
    sw = f_rgb.shape[1]
    x = 0
    while x < width:
        dw = min(sw, width - x)
        region = canvas[frontpanel_y:frontpanel_y + sh, x:x + dw]
        sub_mask = f_mask_c[:, :dw]
        region[sub_mask] = f_rgb_c[:, :dw][sub_mask]
        x += sw
    return canvas


def verify_window_budget(entries, w_tiles, h_tiles, window):
    """Recompute the worst-case unique-tile count in any `window`-column
    slice of the FINAL emitted tilemap -- ground truth from the actual
    output, not a re-run of the offline measurement script this was sized
    against. Returns (worst, worst_col)."""
    worst = 0
    worst_col = 0
    for start in range(0, max(1, w_tiles - window + 1)):
        tiles = set()
        for row in range(h_tiles):
            for col in range(start, min(start + window, w_tiles)):
                tid, pal, hf, vf = entries[row * w_tiles + col]
                tiles.add(tid)  # tile ID alone bounds VRAM slots needed
        worst = max(worst, len(tiles))
        if len(tiles) == worst:
            worst_col = start
    return worst, worst_col


def render_preview_2bpp(tiles_bin, tilemap_bin, palette_bin, w_tiles, h_tiles, out_path):
    """Decode straight from the emitted binaries (ground truth), matching
    convert_bg.py's render_preview_streaming discipline. Renders on a
    magenta backdrop so transparent (index 0) pixels are visibly distinct
    from real content, rather than invisible black-on-black."""
    pal = np.frombuffer(palette_bin, dtype='<u2').reshape(-1, COLORS_PER_PALETTE)
    n_tiles = len(tiles_bin) // st.BYTES_PER_2BPP_TILE
    tiles = [st.decode_2bpp_tile(tiles_bin[i * 16:(i + 1) * 16]) for i in range(n_tiles)]
    entries = st.decode_tilemap_column_major(tilemap_bin, w_tiles, h_tiles)

    out = np.full((h_tiles * 8, w_tiles * 8, 3), TRANS_RGB, dtype=np.uint8)
    for row in range(h_tiles):
        for col in range(w_tiles):
            tid, pid, hf, vf = entries[row * w_tiles + col]
            t = tiles[tid]
            if hf:
                t = t[:, ::-1]
            if vf:
                t = t[::-1, :]
            for y in range(8):
                for x in range(8):
                    idx = int(t[y, x])
                    if idx == 0:
                        continue  # transparent -- leave the magenta backdrop
                    out[row * 8 + y, col * 8 + x] = st.bgr555_to_rgb(int(pal[pid][idx]))
    Image.fromarray(out).save(out_path)


def convert_frontpanel_streaming(pak_path, level_entry, out_dir, w_tiles,
                                 frontpanel_y=0, max_tiles=MAX_STREAMING_TILES,
                                 verbose=True):
    """Convert a level's frontpanel into a streaming BG3 source.

    `w_tiles` MUST equal the level's BG1 streaming conversion's own
    width_tiles (out/bg_stage1a/manifest.json's "width_tiles") -- both
    layers have to agree on what world column N means, or the engine's
    single camera-column index can't drive both caches from one number.
    Passed in explicitly rather than recomputed, so a mismatch is the
    caller's problem to notice, not silently papered over here by two
    independently-rounded scale computations landing on different values.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    idx = PakIndex(pak_path)
    level = load_level(idx, level_entry)
    if verbose:
        print(f'level: {level}')
        print(f'frontpanel: {level.frontpanel}')

    bor_w = level_width(idx, level)
    scene = _composite_frontpanel_only(idx, level, bor_w, frontpanel_y=frontpanel_y)
    Image.fromarray(scene).save(out_dir / 'scene_preview.png')

    scale = SNES_W / 320  # BOR_SCREEN_W, matching convert_bg.py's own constant
    snes_w = w_tiles * st.TILE_SIZE
    snes_w_raw = round(bor_w * scale)

    snes_img = Image.fromarray(scene).resize((snes_w_raw, SNES_H), Image.NEAREST)
    rgb = np.full((SNES_H, snes_w, 3), TRANS_RGB, dtype=np.uint8)
    copy_w = min(snes_w_raw, snes_w)
    rgb[:, :copy_w] = np.array(snes_img, dtype=np.uint8)[:, :copy_w]

    bgr = st.rgb_array_to_bgr555(rgb)
    raw_tiles = st.image_to_tiles(bgr)
    assert raw_tiles.shape[0] == w_tiles * H_TILES

    unique_raw, pos_to_uid, flip_flags = st.dedup_bgr555(raw_tiles)
    if verbose:
        print(f'{raw_tiles.shape[0]} tiles -> {len(unique_raw)} unique BGR555 patterns '
              f'(flip-aware)')

    trans_bgr = st.rgb_to_bgr555(*TRANS_RGB)
    palettes, uniq_indexed, uniq_pal_ids = build_palettes_tileaware(
        unique_raw, num_palettes=NUM_PALETTES, colors_per_palette=COLORS_PER_PALETTE,
        trans_color=trans_bgr)

    # build_palettes_tileaware's nearest-color pixel assignment NEVER maps a
    # pixel to index 0 (see its own `dist[:, :, 0] = np.inf` -- correct for
    # convert_bg.py's opaque BG1 use of this same shared quantizer, wrong
    # here). It only PREPENDS trans_color as slot 0 of each output palette,
    # so a genuinely transparent (TRANS_RGB-keyed) source pixel still gets
    # nearest-color-matched to a REAL palette entry instead of index 0 --
    # confirmed via direct VRAM inspection (Mesen2) rendering as solid
    # opaque magenta over most of the screen instead of see-through
    # backdrop, root-caused to CGRAM sub-palette 1 index 2 decoding to
    # R=31,G=0,B=31. Force it back to index 0 by exact match on the RAW
    # (pre-quantization) pixel color, which is decidable independent of
    # whatever the quantizer chose. ---
    uniq_indexed[unique_raw == trans_bgr] = 0
    if verbose:
        print(f'built {len(palettes)} sub-palettes of {COLORS_PER_PALETTE} '
              f'({COLORS_PER_PALETTE - 1} usable colors each, '
              f'{len(palettes) * (COLORS_PER_PALETTE - 1)} total budget)')

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

    unique_tiles, entries = st.dedup_tiles(indexed_tiles, pal_ids + PALETTE_OFFSET)
    n_tiles = len(unique_tiles)
    if verbose:
        print(f'{len(indexed_tiles)} tiles -> {n_tiles} unique 2bpp tiles')

    if n_tiles > max_tiles:
        raise SystemExit(
            f'ERROR: {n_tiles} unique tiles exceeds the {max_tiles}-tile cache-entry\n'
            f'  tile-ID space. Not truncating.')

    tiles_bin = st.encode_tileset(unique_tiles, bpp=2)
    tilemap_bin = st.encode_tilemap_column_major(entries, w_tiles, H_TILES)
    cgram_palettes = [[0] * COLORS_PER_PALETTE] * PALETTE_OFFSET + list(palettes)
    palette_bin = st.encode_palette(cgram_palettes, TOTAL_PALETTES, COLORS_PER_PALETTE)

    (out_dir / 'tiles.bin').write_bytes(tiles_bin)
    (out_dir / 'tilemap.bin').write_bytes(tilemap_bin)
    (out_dir / 'palette.bin').write_bytes(palette_bin)

    manifest = {
        'level_entry': level_entry,
        'frontpanel': level.frontpanel,
        'streaming': True,
        'layer': 'BG3_frontpanel',
        'width_px': snes_w, 'height_px': SNES_H,
        'width_tiles': w_tiles, 'height_tiles': H_TILES,
        'content_width_tiles': w_tiles,
        'unique_tiles': n_tiles,
        'num_palettes': NUM_PALETTES,
        'palette_offset': PALETTE_OFFSET,
        'colors_per_palette': COLORS_PER_PALETTE,
        'tiles_bytes': len(tiles_bin),
        'tilemap_bytes': len(tilemap_bin),
        'palette_bytes': len(palette_bin),
        'frontpanel_y': frontpanel_y,
    }
    (out_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2))

    render_preview_2bpp(tiles_bin, tilemap_bin, palette_bin, w_tiles, H_TILES,
                        out_dir / 'preview.png')

    if verbose:
        print(f'wrote {out_dir}/: tiles.bin {len(tiles_bin)}B, '
              f'tilemap.bin {len(tilemap_bin)}B, palette.bin {len(palette_bin)}B')
        print(f'VRAM (2bpp): {n_tiles} tiles = {n_tiles * 8} words')

        for window in (40,):
            worst, worst_col = verify_window_budget(entries, w_tiles, H_TILES, window)
            print(f'worst-case unique tiles in any {window}-col window: {worst} '
                  f'(at col {worst_col})')

    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pak', default='Beats of Rage Original [v.3.0 Build 4086].pak')
    ap.add_argument('--level', required=True)
    ap.add_argument('-o', '--output', required=True)
    ap.add_argument('--width-tiles', type=int, required=True,
                    help='MUST match the level\'s BG1 streaming conversion\'s '
                         'width_tiles (see out/<bg_dir>/manifest.json)')
    ap.add_argument('--frontpanel-y', type=int, default=0)
    args = ap.parse_args()

    convert_frontpanel_streaming(args.pak, args.level, args.output, args.width_tiles,
                                 frontpanel_y=args.frontpanel_y)


if __name__ == '__main__':
    main()
