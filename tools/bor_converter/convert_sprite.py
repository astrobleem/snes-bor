#!/usr/bin/env python3
"""Convert one OpenBOR sprite frame (an indexed-color GIF inside a .pak) into
SNES-native 4bpp source data for the CC-DMA pipeline validated in main.pasm.

Output is a 32x48 byte-per-pixel bitmap (one byte per pixel, color index
0-15 in the low nibble) matching the format CC-DMA's "always bitmap mode"
$60-6F BW-RAM window auto-packs into real nibble-packed storage -- see
build.md's "How CC-DMA Type 1 actually works" for why that specific format
is required. Also emits the frame's reduced 16-color palette, both as raw
BGR555 values and as ready-to-paste Poppy `lda #$imm16` lines for
main.pasm's inline CGRAM load (there is no automated asset-linking/ROM-
packing stage yet -- see SNES-BOR-Engine-Prompt.md section 5 for the full
intended pipeline, of which this script is only the frame-conversion piece).

Usage:
    python convert_sprite.py <pak_path> <entry_name> <out_prefix>

Example:
    python convert_sprite.py "Beats of Rage Original [v.3.0 Build 4086].pak" \\
        "DATA\\CHARS\\RALF\\IDLE1.GIF" out/ralf_idle1
    # -> out/ralf_idle1.bin, out/ralf_idle1_palette.txt, out/ralf_idle1_preview.png
"""
import sys
import os
from PIL import Image

sys.path.append(os.path.dirname(__file__))
from pak_extract import extract

TARGET_W, TARGET_H = 32, 48
MAX_COLORS = 15  # + 1 reserved index (0, mapped to black -- the canvas backdrop)
BG_DIST_THRESHOLD = 60  # euclidean RGB distance below which a pixel counts as background


def dist2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def to_bgr555(rgb):
    r, g, b = rgb
    return ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)


def convert(gif_bytes, out_prefix):
    tmp_gif = out_prefix + '_source.gif'
    with open(tmp_gif, 'wb') as f:
        f.write(gif_bytes)

    im = Image.open(tmp_gif).convert('P')
    bg_rgb = tuple(im.getpalette()[0:3])  # BOR convention: index 0 = magenta transparency marker
    rgb = im.convert('RGB')
    w, h = rgb.size
    px = rgb.load()

    minx, miny, maxx, maxy = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            if dist2(px[x, y], bg_rgb) > BG_DIST_THRESHOLD ** 2:
                minx, miny = min(minx, x), min(miny, y)
                maxx, maxy = max(maxx, x), max(maxy, y)
    if maxx < minx:
        raise ValueError('frame appears to be entirely background -- wrong entry?')
    crop = rgb.crop((minx, miny, maxx + 1, maxy + 1))
    cw, ch = crop.size

    scale = min(TARGET_W / cw, TARGET_H / ch)
    new_w, new_h = max(1, round(cw * scale)), max(1, round(ch * scale))
    # NEAREST, not a smoothing filter: any interpolating resize blends
    # foreground pixels against the matte background color right at the
    # silhouette edge, producing a halo of near-background shades that
    # then eats most of the 15-color budget under quantization. Pixel art
    # at this target resolution doesn't want smoothing anyway.
    resized = crop.resize((new_w, new_h), Image.NEAREST)

    canvas = Image.new('RGB', (TARGET_W, TARGET_H), bg_rgb)
    off_x = (TARGET_W - new_w) // 2
    off_y = TARGET_H - new_h  # feet-aligned to the bottom, matching BOR's hotspot convention
    canvas.paste(resized, (off_x, off_y))
    cpx = canvas.load()

    mask = [[dist2(cpx[x, y], bg_rgb) > BG_DIST_THRESHOLD ** 2 for x in range(TARGET_W)] for y in range(TARGET_H)]

    # Replace background pixels with the average foreground color before
    # quantizing -- leaving real background shades in place still skews
    # median-cut toward them (a large, low-variance cluster). A single flat
    # substitute color barely perturbs the boundaries since it's one point,
    # not a cluster.
    fg_pixels = [cpx[x, y] for y in range(TARGET_H) for x in range(TARGET_W) if mask[y][x]]
    if not fg_pixels:
        raise ValueError('no foreground pixels survived the background threshold')
    avg_fg = tuple(sum(c[i] for c in fg_pixels) // len(fg_pixels) for i in range(3))
    quant_src = Image.new('RGB', (TARGET_W, TARGET_H))
    qspx = quant_src.load()
    for y in range(TARGET_H):
        for x in range(TARGET_W):
            qspx[x, y] = cpx[x, y] if mask[y][x] else avg_fg
    quant = quant_src.quantize(colors=MAX_COLORS, method=Image.MEDIANCUT)
    qpal = quant.getpalette()
    qpx = quant.load()

    indices = [[0] * TARGET_W for _ in range(TARGET_H)]
    palette = {0: (0, 0, 0)}  # index 0 reserved: black, this canvas's real backdrop
    for y in range(TARGET_H):
        for x in range(TARGET_W):
            if mask[y][x]:
                qi = qpx[x, y] + 1  # shift up so index 0 stays reserved
                indices[y][x] = qi
                palette.setdefault(qi, tuple(qpal[(qi - 1) * 3:(qi - 1) * 3 + 3]))

    out_bin = bytearray(indices[y][x] & 0x0F for y in range(TARGET_H) for x in range(TARGET_W))
    bin_path = out_prefix + '.bin'
    with open(bin_path, 'wb') as f:
        f.write(out_bin)

    pal_path = out_prefix + '_palette.txt'
    with open(pal_path, 'w') as f:
        for idx in range(16):
            rgb_val = palette.get(idx, (0, 0, 0))
            f.write(f'    lda #${to_bgr555(rgb_val):04X}\n')

    preview = Image.new('RGB', (TARGET_W, TARGET_H))
    ppx = preview.load()
    for y in range(TARGET_H):
        for x in range(TARGET_W):
            ppx[x, y] = palette.get(indices[y][x], (255, 0, 255))
    preview_path = out_prefix + '_preview.png'
    preview.resize((TARGET_W * 8, TARGET_H * 8), Image.NEAREST).save(preview_path)

    return {
        'bin_path': bin_path, 'pal_path': pal_path, 'preview_path': preview_path,
        'colors_used': len(palette), 'source_bbox': (cw, ch), 'resized_to': (new_w, new_h),
    }


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        raise SystemExit(1)
    pak_path, entry_name, out_prefix = sys.argv[1:4]
    os.makedirs(os.path.dirname(out_prefix) or '.', exist_ok=True)
    gif_bytes = extract(pak_path, entry_name)
    result = convert(gif_bytes, out_prefix)
    for k, v in result.items():
        print(f'{k}: {v}')


if __name__ == '__main__':
    main()
