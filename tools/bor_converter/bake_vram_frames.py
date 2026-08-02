#!/usr/bin/env python3
"""Bake an animation directory's per-frame byte-per-pixel .bin files (as
produced by convert_animation.py) into precomputed CC-DMA-converted
VRAM-format tile data, ready to `.incbin` into main.pasm and DMA straight
into VRAM per animation tick -- no runtime CC-DMA involved for animation
playback (see handoff.md's "Option B" for why: it reuses the already-boot-
time-validated CC-DMA source format/geometry while avoiding a second SA-1/
S-CPU handshake protocol for frame changes).

This is a from-scratch, byte-validated reimplementation of Mesen2's
Sa1::ReadCharConvertType1 (Core/SNES/Coprocessors/SA1/Sa1.cpp), specialized
to this project's fixed CC-DMA configuration: CDMA=$09 -> CharConvFormat=1
(4bpp), CharConvWidth=2 (4 tiles/line), i.e. a 32x48 source image (4x6
tiles). Validated byte-for-byte against Mesen2's real VRAM output for the
already-shipped static sprite (see handoff.md) before trusting it for new
frames -- don't skip that check if this script's geometry assumptions ever
change (different sprite size/tile grid).

Usage:
    python bake_vram_frames.py <anim_dir> <out_bin> [frame_indices]

frame_indices is an optional comma-separated list of 0-based indices into
manifest.json's frame list (e.g. "0,1,3,4,5,7") -- bakes only that subset,
in the given order, instead of every frame. Exists because bank 0 is a
single fixed-size 32KB window ($8000-$FFFF, see CLAUDE.md's "Fixed .org
directives silently truncate") with no free room to grow arbitrarily; when
a full animation doesn't fit, drop frames here rather than fight the ROM
layout.

Example:
    python bake_vram_frames.py out/ralf_idle assets/anim_ralf_idle.bin
    # -> assets/anim_ralf_idle.bin: N frames * 768 bytes, frame order
    #    matching manifest.json, ready for a single main.pasm .incbin.
"""
import sys
import os
import json

TARGET_W, TARGET_H = 32, 48
TILES_X, TILES_Y = TARGET_W // 8, TARGET_H // 8


def convert_frame_to_vram(pixels):
    """pixels: 1536 bytes, byte-per-pixel (low nibble = 4bpp color index),
    row-major 32x48. Returns 768 bytes of standard SNES 4bpp planar tile
    data, 24 tiles in row-major tile order -- exactly what CC-DMA's pump
    loop reads out of IRAM for this project's fixed SDA/CDMA config.
    """
    assert len(pixels) == TARGET_W * TARGET_H

    # Pack into real BW-RAM nibble format (2 px/byte), matching
    # Sa1BwRamHandler::WriteBitmapMode: shift = (x&1)*4 -> even source index
    # packs into the low nibble, odd into the high nibble of the same byte.
    packed = bytearray((TARGET_W * TARGET_H) // 2)
    for i in range(0, TARGET_W * TARGET_H, 2):
        lo = pixels[i] & 0x0F
        hi = pixels[i + 1] & 0x0F
        packed[i // 2] = lo | (hi << 4)

    bytes_per_line = (TILES_X * 8) >> 1  # CharConvFormat=1 (4bpp) -> >>1
    out = bytearray(TILES_X * TILES_Y * 32)
    for tile_num in range(TILES_X * TILES_Y):
        tile_x = tile_num % TILES_X
        tile_y = tile_num // TILES_X
        src_addr = tile_y * 8 * bytes_per_line + tile_x * 4
        dest = tile_num * 32
        for y in range(8):
            row_addr = src_addr + y * bytes_per_line
            data = (packed[row_addr] | (packed[row_addr + 1] << 8) |
                    (packed[row_addr + 2] << 16) | (packed[row_addr + 3] << 24))
            result = [0, 0, 0, 0]
            for x in range(8):
                for i in range(4):
                    result[i] |= (data & 1) << (7 - x)
                    data >>= 1
            for i in range(4):
                offset = (y << 1) + ((i >> 1) << 4) + (i & 1)
                out[dest + offset] = result[i]
    return bytes(out)


def bake(anim_dir, out_bin, frame_indices=None):
    manifest_path = os.path.join(anim_dir, 'manifest.json')
    with open(manifest_path) as f:
        manifest = json.load(f)

    frames = manifest['frames']
    if frame_indices is not None:
        frames = [frames[i] for i in frame_indices]

    blob = bytearray()
    for frame in frames:
        bin_path = os.path.join(anim_dir, frame['bin'])
        with open(bin_path, 'rb') as f:
            pixels = f.read()
        blob += convert_frame_to_vram(pixels)

    os.makedirs(os.path.dirname(out_bin) or '.', exist_ok=True)
    with open(out_bin, 'wb') as f:
        f.write(blob)

    return {
        'frames': len(frames),
        'bytes_per_frame': 768,
        'total_bytes': len(blob),
        'delays': [f['delay'] for f in frames],
        'loop': manifest['loop'],
        'out_bin': out_bin,
    }


def main():
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        raise SystemExit(1)
    anim_dir, out_bin = sys.argv[1:3]
    frame_indices = None
    if len(sys.argv) == 4:
        frame_indices = [int(x) for x in sys.argv[3].split(',')]
    result = bake(anim_dir, out_bin, frame_indices)
    for k, v in result.items():
        print(f'{k}: {v}')


if __name__ == '__main__':
    main()
