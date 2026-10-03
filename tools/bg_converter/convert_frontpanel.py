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
import hashlib
import json
import re
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


def frontpanel_sequence_geometry(pak_index, sequence):
    """BOR loadfrontpanel clips sprites; the first clipped width is the stride.

    Full image masks retain the -clipl/-clipt sprite-center offsets without
    cropping away their original placement. Declaration order is never sorted.
    """
    if isinstance(sequence, (str, bytes)) or not sequence:
        raise ValueError('FRONTPANEL_SEQUENCE_EMPTY_OR_SCALAR')
    images, provenance = [], []
    for authored in sequence:
        name = str(authored).replace('/', '\\')
        rgb, mask = pak_index.image(name)
        ys, xs = np.nonzero(mask)
        bounds = [int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1] if len(xs) else [0]*4
        images.append((rgb,mask))
        provenance.append(dict(source_path=name,sha256=hashlib.sha256(pak_index.read(name)).hexdigest(),
                               size=[rgb.shape[1],rgb.shape[0]],opaque_bounds=bounds))
    stride = provenance[0]['opaque_bounds'][2]-provenance[0]['opaque_bounds'][0]
    if stride <= 0:
        raise ValueError('FRONTPANEL_SEQUENCE_ZERO_SOURCE_STRIDE')
    return images,provenance,stride


def composite_frontpanel_sequence(pak_index, sequence, width, frontpanel_y=0, *, scroll_x=0):
    """Authored cycle at first-sprite stride; source-space integer offset.

    This is a camera-aligned static target atlas when scroll_x=0, not an
    implementation of source advancex*1.4 or the runtime BG3 scroll register.
    """
    from composite_scene import _blit
    if width <= 0 or scroll_x < 0:
        raise ValueError('FRONTPANEL_SEQUENCE_COORDINATES')
    images, _, stride = frontpanel_sequence_geometry(pak_index,sequence)
    canvas = np.full((BOR_SCREEN_H,width,3),TRANS_RGB,dtype=np.uint8)
    first, remainder = divmod(scroll_x,stride)
    for n,x in enumerate(range(-remainder,width+1,stride),first):
        rgb,mask = images[n % len(images)]
        _blit(canvas,rgb,mask,x,frontpanel_y)
    return canvas


def frontpanel_runtime_limits():
    """Actual BG3 cache/row ownership, used only by the explicit sequence API."""
    root = Path(__file__).resolve().parents[2]
    cache = (root/'src/core/stream_cache_fp.pasm').read_text(encoding='utf-8')
    main = (root/'src/main.pasm').read_text(encoding='utf-8')
    motion = (root/'src/core/stage_frontpanel.pasm').read_text(encoding='utf-8')
    def constant(text,name):
        values = re.findall(r'^\s*'+name+r'\s*=\s*([^;\r\n]+)',text,re.MULTILINE)
        if len(values) != 1 or not re.fullmatch(r'[0-9]+|\$[0-9A-Fa-f]+',values[0].strip()):
            raise ValueError('FRONTPANEL_RUNTIME_CONSTANT_UNBOUND: '+name)
        value = values[0].strip()
        return int(value[1:],16) if value.startswith('$') else int(value)
    limits = dict(tile_ids=constant(cache,'STREAM_FP_MAX_TILE_IDS'),
                  usable_slots=constant(cache,'STREAM_FP_CACHE_USABLE'),
                  viewport_columns=constant(motion,'StageFp_ViewportColumns'),
                  row_start=constant(main,'STREAM_FP_TILEMAP_ROW_START'),
                  row_count=constant(main,'FP_CONTENT_ROW_COUNT'))
    if (not 1 <= limits['tile_ids'] <= 65535 or not 1 <= limits['usable_slots'] <= 1023
            or not 1 <= limits['viewport_columns'] <= 64 or limits['row_start'] < 0
            or not 1 <= limits['row_count'] <= H_TILES
            or limits['row_start']+limits['row_count'] > H_TILES):
        raise ValueError('FRONTPANEL_RUNTIME_LIMITS_INVALID')
    return limits


def verify_sequence_resources(entries, n_tiles, w_tiles, limits):
    if not 1 <= n_tiles <= limits['tile_ids']:
        raise ValueError(f'FRONTPANEL_TILE2SLOT_CAPACITY: {n_tiles} > {limits["tile_ids"]}')
    if len(entries) != w_tiles*H_TILES:
        raise ValueError('FRONTPANEL_SEQUENCE_MAP_SIZE')
    visible = entries[limits['row_start']*w_tiles:(limits['row_start']+limits['row_count'])*w_tiles]
    worst,col = verify_window_budget(visible,w_tiles,limits['row_count'],limits['viewport_columns'])
    if worst > limits['usable_slots']:
        raise ValueError(f'FRONTPANEL_RESIDENT_CAPACITY: {worst} > {limits["usable_slots"]}')
    return dict(worst_unique_tiles=worst,worst_column=col,**limits)


def normal_font_palette_binding():
    """Bind CGRAM 4..7 to Core_Text_Init's actual ROM palette, fail closed."""
    root = Path(__file__).resolve().parents[2]
    main = (root/'src/main.pasm').read_text(encoding='utf-8')
    owner = (root/'src/core/text.pasm').read_text(encoding='utf-8')
    matches = re.findall(r'Font_PaletteData:\s*\.incbin\s+"([^"]+)"',main)
    if (len(matches) != 1 or not re.search(r'^FONT_CGRAM_PAL_ID\s*=\s*1\b',owner,re.M)
            or not re.search(r'^FONT_PALETTE_BYTES\s*=\s*8\b',owner,re.M)
            or 'lda.l Font_PaletteData,x' not in owner):
        raise ValueError('FRONTPANEL_FONT_PALETTE_UNBOUND')
    path = root/'src'/matches[0]
    data = path.read_bytes()
    if len(data) != 8:
        raise ValueError('FRONTPANEL_FONT_PALETTE_SIZE')
    words = np.frombuffer(data,dtype='<u2').tolist()
    if any(w > 32767 for w in words):
        raise ValueError('FRONTPANEL_FONT_PALETTE_COLOR')
    return words,dict(source_path=path.relative_to(root).as_posix(),
        sha256=hashlib.sha256(data).hexdigest(),words=words,cgram_first=4,
        owner='Core_Text_Init__pal_loop',adapter='ACCEPTED_COMPAT_FIXED_FONT_PAL1_OPTIMIZED_PAL2_3')


def quantize_normal_frontpanel(unique_raw, trans_bgr):
    fixed,binding = normal_font_palette_binding()
    optimized,_,_ = build_palettes_tileaware(unique_raw,num_palettes=2,
        colors_per_palette=4,trans_color=trans_bgr)
    palettes = [fixed]+list(optimized)
    flat = unique_raw.reshape(len(unique_raw),64).astype(np.int32)
    rgb = np.stack((flat&31,(flat>>5)&31,(flat>>10)&31),axis=-1)
    indices,errors = [],[]
    for palette in palettes:
        p = np.asarray(palette[1:],dtype=np.int32)
        colors = np.stack((p&31,(p>>5)&31,(p>>10)&31),axis=-1)
        distances = (((rgb[:,:,None,:]-colors)**2)*[2,4,1]).sum(axis=-1)
        chosen = distances.argmin(axis=-1)
        error = np.take_along_axis(distances,chosen[:,:,None],axis=-1)[:,:,0]
        error[flat == trans_bgr] = 0
        indices.append(chosen+1)
        errors.append(error.sum(axis=1))
    ids = np.asarray(errors).argmin(axis=0).astype(np.uint8)
    indexed = np.asarray(indices)[ids,np.arange(len(ids))].reshape(unique_raw.shape).astype(np.uint8)
    indexed[unique_raw == trans_bgr] = 0
    return palettes,indexed,ids,binding


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
                                 verbose=True, *, frontpanel_sequence=None, normal_font_palette=False,
                                 full_height=False):
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
    if frontpanel_sequence is None:
        scene = _composite_frontpanel_only(idx, level, bor_w, frontpanel_y=frontpanel_y)
    else:
        if isinstance(frontpanel_sequence,(str,bytes)):
            raise ValueError('FRONTPANEL_SEQUENCE_EMPTY_OR_SCALAR')
        frontpanel_sequence = tuple(frontpanel_sequence)
        _,sequence_sources,sequence_stride = frontpanel_sequence_geometry(idx,frontpanel_sequence)
        scene = composite_frontpanel_sequence(idx,frontpanel_sequence,bor_w,frontpanel_y)
    Image.fromarray(scene).save(out_dir / 'scene_preview.png')

    scale = SNES_W / 320  # BOR_SCREEN_W, matching convert_bg.py's own constant
    owner_width_tiles = w_tiles
    snes_w = w_tiles * st.TILE_SIZE
    snes_w_raw = round(bor_w * scale)
    if frontpanel_sequence is not None and (snes_w_raw+7)//8 != w_tiles:
        raise ValueError('FRONTPANEL_SEQUENCE_BG_WIDTH_MISMATCH')

    if frontpanel_sequence is None:
        snes_img = Image.fromarray(scene).resize((snes_w_raw, SNES_H), Image.NEAREST)
        rgb = np.full((SNES_H, snes_w, 3), TRANS_RGB, dtype=np.uint8)
        copy_w = min(snes_w_raw, snes_w)
        rgb[:, :copy_w] = np.array(snes_img, dtype=np.uint8)[:, :copy_w]
    else:
        # Compile one complete cycle, then repeat at tile-aligned phase. A
        # whole-level resize otherwise creates new tile IDs at every sub-tile
        # occurrence (four 183px source panels exceeded the 768-ID FP domain).
        # Explicit target adaptation: round the 4/5-scale cycle to nearest 8px.
        source_cycle_width = sequence_stride*len(frontpanel_sequence)
        # A sprite extending past its stride can overlap the next cycle.
        # That needs a viewport-dependent compositor, not silent atlas clipping.
        if any(r['opaque_bounds'][2] > sequence_stride for r in sequence_sources):
            raise ValueError('FRONTPANEL_SEQUENCE_OVERHANG_UNSUPPORTED')
        target_cycle_width = max(8,((source_cycle_width+5)//10)*8)
        if full_height and target_cycle_width > snes_w:
            snes_w = target_cycle_width
            w_tiles = snes_w//8
        cycle = composite_frontpanel_sequence(idx,frontpanel_sequence,source_cycle_width,frontpanel_y)
        cycle = np.asarray(Image.fromarray(cycle).resize((target_cycle_width,SNES_H),Image.NEAREST))
        rgb = np.tile(cycle,(1,(snes_w+target_cycle_width-1)//target_cycle_width,1))[:, :snes_w]
    if frontpanel_sequence is not None:
        limits = frontpanel_runtime_limits()
        if full_height:
            limits = dict(limits,row_start=0,row_count=H_TILES)
        y0,y1 = limits['row_start']*8,(limits['row_start']+limits['row_count'])*8
        if np.any(rgb[:y0] != TRANS_RGB) or np.any(rgb[y1:] != TRANS_RGB):
            raise ValueError('FRONTPANEL_CONTENT_OUTSIDE_RUNTIME_ROWS')

    bgr = st.rgb_array_to_bgr555(rgb)
    raw_tiles = st.image_to_tiles(bgr)
    assert raw_tiles.shape[0] == w_tiles * H_TILES

    unique_raw, pos_to_uid, flip_flags = st.dedup_bgr555(raw_tiles)
    if verbose:
        print(f'{raw_tiles.shape[0]} tiles -> {len(unique_raw)} unique BGR555 patterns '
              f'(flip-aware)')

    trans_bgr = st.rgb_to_bgr555(*TRANS_RGB)
    if normal_font_palette:
        palettes,uniq_indexed,uniq_pal_ids,font_binding = quantize_normal_frontpanel(unique_raw,trans_bgr)
    else:
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

    if frontpanel_sequence is not None:
        sequence_resources = verify_sequence_resources(entries,n_tiles,w_tiles,limits)

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
    if frontpanel_sequence is not None:
        manifest.update(frontpanel_sequence=sequence_sources,source_stride=sequence_stride,
                        source_cycle_width=source_cycle_width,target_cycle_width=target_cycle_width,
                        target_cycle_rounding='nearest_8px_after_4_over_5_scale',
                        sequence_resources=sequence_resources,
                        sequence_adapter='NORMAL_ORDERED_FP_CYCLE_INTEGER_CAMERA_V1')
    if normal_font_palette:
        manifest['font_palette_binding'] = font_binding
    if full_height:
        manifest['full_height_frontpanel'] = True
        manifest['owner_width_tiles'] = owner_width_tiles
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
