#!/usr/bin/env python3
"""Generate the BG3 HUD tileset procedurally -- no art asset required.

BG3 in mode 1 is 2bpp: 4 colors per palette, index 0 transparent. The HUD owns
CGRAM sub-palette 0 (colors 0-15), which `convert_bg.py` deliberately leaves
unused by the backdrop -- see its PALETTE_OFFSET comment for why BG3's 2bpp
palette windows would otherwise collide with BG1's 4bpp ones.

Colors used (BG3 tilemap palette 0 -> CGRAM 0-3):
    0  transparent (not drawn)
    1  bar fill
    2  bar empty
    3  bar frame / border

Tileset layout (each tile 8x8, 16 bytes):
    0            blank
    1..9         bar body with 0..8 columns filled, framed top and bottom
    10           bar left cap
    11           bar right cap

A health bar is drawn as: left cap, N body tiles, right cap. With HUD_BAR_TILES
body tiles at 8 px each, one bar represents HUD_BAR_TILES*8 HP.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import snes_tiles as st  # noqa: E402

C_TRANS, C_FILL, C_EMPTY, C_FRAME = 0, 1, 2, 3

TILE_BLANK = 0
TILE_FILL_BASE = 1      # + n  (n = 0..8 filled columns)
TILE_CAP_LEFT = 10
TILE_CAP_RIGHT = 11
HUD_TILE_COUNT = 12

# Body tiles per bar -> 8 px each -> max HP represented.
HUD_BAR_TILES = 8
HUD_MAX_HP = HUD_BAR_TILES * 8   # 64

# CGRAM colors 0-3, BGR555. Color 0's value is irrelevant for BG3 (index 0 is
# never drawn) but is also the global backdrop color, so keep it black.
HUD_PALETTE = [
    st.rgb_to_bgr555(0, 0, 0),        # 0 transparent / backdrop
    st.rgb_to_bgr555(248, 56, 56),    # 1 fill   (red health)
    st.rgb_to_bgr555(64, 24, 24),     # 2 empty  (dark red)
    st.rgb_to_bgr555(248, 248, 200),  # 3 frame  (bone white)
]


def _body_tile(filled_cols):
    """8x8 bar body: 1px frame top and bottom, `filled_cols` columns of fill."""
    t = np.full((8, 8), C_EMPTY, dtype=np.uint8)
    t[0, :] = C_FRAME
    t[7, :] = C_FRAME
    if filled_cols > 0:
        t[1:7, :filled_cols] = C_FILL
    return t


def _cap_tile(side):
    """Rounded end cap: vertical frame bar on the outer edge."""
    t = np.full((8, 8), C_EMPTY, dtype=np.uint8)
    t[0, :] = C_FRAME
    t[7, :] = C_FRAME
    if side == 'left':
        t[:, 0] = C_FRAME
    else:
        t[:, 7] = C_FRAME
    return t


def build_hud_tiles():
    tiles = [np.full((8, 8), C_TRANS, dtype=np.uint8)]        # 0 blank
    for n in range(9):                                        # 1..9
        tiles.append(_body_tile(n))
    tiles.append(_cap_tile('left'))                           # 10
    tiles.append(_cap_tile('right'))                          # 11
    assert len(tiles) == HUD_TILE_COUNT
    return tiles


def build_hud_palette():
    """CGRAM sub-palette 0 as 16 BGR555 words (colors 4-15 unused, zeroed)."""
    return list(HUD_PALETTE) + [0] * (16 - len(HUD_PALETTE))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('-o', '--output', default='out/hud')
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    tiles = build_hud_tiles()
    tiles_bin = st.encode_tileset(tiles, bpp=2)
    (out / 'hud_tiles.bin').write_bytes(tiles_bin)

    pal = build_hud_palette()
    (out / 'hud_palette.bin').write_bytes(
        b''.join(int(c).to_bytes(2, 'little') for c in pal))

    manifest = {
        'tile_count': HUD_TILE_COUNT,
        'bpp': 2,
        'bytes': len(tiles_bin),
        'tile_blank': TILE_BLANK,
        'tile_fill_base': TILE_FILL_BASE,
        'tile_cap_left': TILE_CAP_LEFT,
        'tile_cap_right': TILE_CAP_RIGHT,
        'bar_tiles': HUD_BAR_TILES,
        'max_hp': HUD_MAX_HP,
        'cgram_palette': 0,
    }
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))

    # Preview: decode straight back out of the emitted binary.
    prev = np.zeros((8, HUD_TILE_COUNT * 8, 3), dtype=np.uint8)
    for i in range(HUD_TILE_COUNT):
        raw = tiles_bin[i * st.BYTES_PER_2BPP_TILE:(i + 1) * st.BYTES_PER_2BPP_TILE]
        for y in range(8):
            bp0, bp1 = raw[y * 2], raw[y * 2 + 1]
            for x in range(8):
                bit = 7 - x
                idx = ((bp0 >> bit) & 1) | (((bp1 >> bit) & 1) << 1)
                prev[y, i * 8 + x] = st.bgr555_to_rgb(pal[idx])
    Image.fromarray(prev).resize((HUD_TILE_COUNT * 8 * 6, 48), Image.NEAREST).save(
        out / 'preview.png')

    print(f'wrote {out}/: hud_tiles.bin {len(tiles_bin)}B '
          f'({HUD_TILE_COUNT} 2bpp tiles), hud_palette.bin, preview.png')
    print(f'bar: {HUD_BAR_TILES} body tiles -> max HP {HUD_MAX_HP}')


if __name__ == '__main__':
    main()
