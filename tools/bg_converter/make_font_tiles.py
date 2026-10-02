#!/usr/bin/env python3
"""Convert the BOR pak's own FONT.GIF into a BG3 2bpp font tileset (plan_game.md
Phase G1 -- the font/text renderer).

Source: DATA\\SPRITES\\FONT.GIF inside "Beats of Rage Original [v.3.0 Build
4086].pak" (the project's real asset base, per CLAUDE.md/README.md). Chosen
over a public-domain font because it's already the right style/size for this
game and reuses the same pak-extraction path as every other converter here
(pak_extract.py) instead of introducing a new asset source.

Layout (verified by direct inspection, not assumed -- see
openbor_script_coverage_gap_data.md's sibling investigation style): FONT.GIF
is a classic OpenBOR bitmap font, 144x144px, a 16x16 grid of 9x9px cells,
directly ASCII-indexed (glyph N at cell row N//16, col N%16). Row 2 col 0 is
ASCII 32 (space) and is correctly blank, confirming the indexing. Rows 0-1
hold a duplicate/bonus hex-digit glyph set reusing the control-character
range (0-31) -- not used here. Only ASCII 32-126 (95 printable glyphs) are
extracted; rows past that (checkered/transparent in the source image) are
unused filler, not real glyphs.

Each 9x9 cell has a 1px transparent gutter on its right and bottom edge (the
whole image uses exactly 4 palette indices: transparent, white fill, black
outline, and an unrelated brown checker-pattern color that only appears in
the unused filler rows) -- so cropping to the top-left 8x8 of each cell loses
nothing. Confirmed by direct pixel inspection of the 'A' glyph (ascii 65):
its last row and column are both all-transparent in the source cell.

Palette: BG3 tilemap palette id 1 (real hardware: a 2bpp tile with tilemap
palette field p reads CGRAM colors p*4..p*4+3 -- see snes_tiles.py's
encode_tilemap_word docstring -- so palette id 1 means CGRAM colors 4-7).
Palette id 0 (CGRAM 0-3) is the HUD's (make_hud_tiles.py); ids 1-3 are also
what convert_frontpanel.py uses on levels that have a frontpanel layer --
all 4 available BG3 palette ids (0-3, the block convert_bg.py's
PALETTE_OFFSET reserves away from BG1) are taken when a frontpanel is
loaded. The currently-shipped level (stage 1B, see build_rom.py's
BG_SCREENS) has no frontpanel, so palette id 1 is safe today. A level with
BOTH a frontpanel AND on-screen text would need a real resolution (text on
BG1 instead, or suspending the FP resolver while text/menus are up) --
deliberately not solved here; see core/text.pasm's header for the same note.

font_palette.bin holds only the 4 real colors (8 bytes) -- the exact DMA
source for CGRAM bytes (palette_id*4)*2 .. +7, not a padded 16-color block.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import snes_tiles as st  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'bor_converter'))
import pak_extract  # noqa: E402

DEFAULT_PAK = "Beats of Rage Original [v.3.0 Build 4086].pak"
FONT_ENTRY = "DATA\\SPRITES\\FONT.GIF"

CELL_SIZE = 9
GLYPH_SIZE = 8
GRID_COLS = 16

ASCII_FIRST = 32   # space
ASCII_LAST = 126   # ~
GLYPH_COUNT = ASCII_LAST - ASCII_FIRST + 1   # 95

CGRAM_PALETTE = 1   # BG3 sub-palette 1 (see module docstring)

C_TRANS, C_OUTLINE, C_FILL = 0, 1, 2

# BGR555. Color 0 is irrelevant (BG3 index 0 is never drawn).
FONT_PALETTE = [
    st.rgb_to_bgr555(0, 0, 0),        # 0 transparent
    st.rgb_to_bgr555(0, 0, 0),        # 1 outline (black)
    st.rgb_to_bgr555(248, 248, 248),  # 2 fill (white)
]


def load_font_indexed(pak_path):
    """Extract FONT.GIF and return its raw palette-index array (H, W)."""
    data = pak_extract.extract(pak_path, FONT_ENTRY)
    im = Image.open(io_bytes(data))
    return np.array(im), im.getpalette()


def io_bytes(data):
    import io
    return io.BytesIO(data)


def classify(idx_arr, palette):
    """Map the source palette's arbitrary indices onto {C_TRANS, C_OUTLINE, C_FILL}
    by RGB brightness -- index 0 in the source is always transparent (BOR
    convention); of the remaining colors actually used by a glyph cell, the
    darker one is the outline and the lighter one is the fill."""
    out = np.zeros(idx_arr.shape, dtype=np.uint8)
    for i in np.unique(idx_arr):
        if i == 0:
            continue
        r, g, b = palette[i * 3:i * 3 + 3]
        out[idx_arr == i] = C_OUTLINE if (r + g + b) < 384 else C_FILL
    return out


def extract_glyphs(idx_arr, palette):
    classified = classify(idx_arr, palette)
    glyphs = []
    for code in range(ASCII_FIRST, ASCII_LAST + 1):
        row, col = code // GRID_COLS, code % GRID_COLS
        y0, x0 = row * CELL_SIZE, col * CELL_SIZE
        cell = classified[y0:y0 + GLYPH_SIZE, x0:x0 + GLYPH_SIZE]
        glyphs.append(cell.copy())
    return glyphs


def build_font_palette():
    """4 real colors only (8 bytes) -- the exact CGRAM DMA source, not a
    padded 16-color block. See module docstring."""
    return list(FONT_PALETTE) + [0] * (4 - len(FONT_PALETTE))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pak', default=DEFAULT_PAK)
    ap.add_argument('-o', '--output', default='out/font')
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    idx_arr, palette = load_font_indexed(args.pak)
    glyphs = extract_glyphs(idx_arr, palette)
    assert len(glyphs) == GLYPH_COUNT

    tiles_bin = st.encode_tileset(glyphs, bpp=2)
    (out / 'font_tiles.bin').write_bytes(tiles_bin)

    pal = build_font_palette()
    (out / 'font_palette.bin').write_bytes(
        b''.join(int(c).to_bytes(2, 'little') for c in pal))

    manifest = {
        'tile_count': GLYPH_COUNT,
        'bpp': 2,
        'bytes': len(tiles_bin),
        'ascii_first': ASCII_FIRST,
        'ascii_last': ASCII_LAST,
        'cgram_palette': CGRAM_PALETTE,
        'source_pak': args.pak,
        'source_entry': FONT_ENTRY,
    }
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))

    prev = np.zeros((8, GLYPH_COUNT * 8, 3), dtype=np.uint8)
    for i in range(GLYPH_COUNT):
        raw = tiles_bin[i * st.BYTES_PER_2BPP_TILE:(i + 1) * st.BYTES_PER_2BPP_TILE]
        for y in range(8):
            bp0, bp1 = raw[y * 2], raw[y * 2 + 1]
            for x in range(8):
                bit = 7 - x
                idx = ((bp0 >> bit) & 1) | (((bp1 >> bit) & 1) << 1)
                prev[y, i * 8 + x] = st.bgr555_to_rgb(pal[idx])
    Image.fromarray(prev).resize((GLYPH_COUNT * 8 * 3, 24), Image.NEAREST).save(
        out / 'preview.png')

    print(f'wrote {out}/: font_tiles.bin {len(tiles_bin)}B '
          f'({GLYPH_COUNT} 2bpp tiles), font_palette.bin, preview.png')


if __name__ == '__main__':
    main()
