#!/usr/bin/env python3
"""Composite one static BOR level screen from its background/panel/frontpanel art.

BOR levels are a horizontal strip: `order` names a left-to-right sequence of
panels, drawn over a tiling `background`, with a sparse `frontpanel` overlaid in
front. snes-bor's Phase 6 backdrop is static and non-scrolling, so this module
only ever builds the screen at scroll position 0 -- the leftmost BOR_SCREEN_W
pixels of that strip. No parallax rates, no z-depth.

Transparency: BOR marks it with palette index 0 (RGB 252,0,255 magenta in the
stock pak). Same convention `bor_converter/convert_sprite.py` already relies on.
Measured on DATA\\BGS\\WAREHOUS: panels are ~0% transparent (opaque scenery),
`front.gif` is ~91% transparent (railings/posts), `back.gif` is 0% (opaque
tiling strip).

Vertical alignment is the one thing the level format does not pin down: stock
panels are 244px tall against BOR's 240px screen. `panel_y` exists so that is a
tunable, eyeball-verified choice rather than a buried assumption -- always look
at the emitted preview before trusting a scene.
"""
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'bor_converter'))

import pak_extract  # noqa: E402
from level_parse import parse_level  # noqa: E402

# BOR's native screen. The scene is composited here, then scaled to the SNES's
# 256x224 by convert_bg.py.
BOR_SCREEN_W = 320
BOR_SCREEN_H = 240

TRANSPARENT_INDEX = 0


class PakIndex:
    """Reads the .pak directory once.

    `pak_extract.extract` re-parses the whole directory on every call, which is
    fine for a handful of character frames but not for a 36-panel level.
    """

    def __init__(self, pak_path):
        self.pak_path = pak_path
        self._by_name = {e.name.upper(): e for e in pak_extract.read_entries(pak_path)}

    def read(self, entry_name):
        entry = self._by_name.get(entry_name.upper())
        if entry is None:
            # Some stock levels declare art without an extension
            # (`data/bgs/alley/back`); BOR appends .gif implicitly.
            entry = self._by_name.get(entry_name.upper() + '.GIF')
        if entry is None:
            raise KeyError(f'{entry_name!r} not found in {self.pak_path}')
        with open(self.pak_path, 'rb') as f:
            f.seek(entry.offset)
            return f.read(entry.size)

    def image(self, entry_name):
        """Return (rgb HxWx3 uint8, opaque_mask HxW bool) for a pak GIF."""
        im = Image.open(io.BytesIO(self.read(entry_name)))
        indices = np.array(im.convert('P'), dtype=np.uint8)
        rgb = np.array(im.convert('RGB'), dtype=np.uint8)
        mask = indices != TRANSPARENT_INDEX
        return rgb, mask


def _blit(dst_rgb, src_rgb, src_mask, x, y):
    """Alpha-less blit of src onto dst at (x, y), honoring src_mask, clipped."""
    dh, dw = dst_rgb.shape[:2]
    sh, sw = src_rgb.shape[:2]

    sx0 = max(0, -x)
    sy0 = max(0, -y)
    sx1 = min(sw, dw - x)
    sy1 = min(sh, dh - y)
    if sx1 <= sx0 or sy1 <= sy0:
        return

    dx0 = x + sx0
    dy0 = y + sy0
    region = dst_rgb[dy0:dy0 + (sy1 - sy0), dx0:dx0 + (sx1 - sx0)]
    sub_rgb = src_rgb[sy0:sy1, sx0:sx1]
    sub_mask = src_mask[sy0:sy1, sx0:sx1]
    region[sub_mask] = sub_rgb[sub_mask]


def _tile_horizontally(dst_rgb, src_rgb, src_mask, y, width):
    """Repeat src across `width` pixels starting at x=0."""
    sw = src_rgb.shape[1]
    if sw <= 0:
        return
    x = 0
    while x < width:
        _blit(dst_rgb, src_rgb, src_mask, x, y)
        x += sw


def composite_screen(pak_index, level, panel_y=0, background_y=0,
                     frontpanel_y=0, scroll_x=0):
    """Build one BOR_SCREEN_W x BOR_SCREEN_H RGB screen of `level`.

    Layers, back to front: tiled `background`, the `order` panel sequence laid
    side by side, then the tiled `frontpanel` overlay.
    """
    canvas = np.zeros((BOR_SCREEN_H, BOR_SCREEN_W, 3), dtype=np.uint8)

    if level.background:
        bg_rgb, bg_mask = pak_index.image(level.background)
        # Tile vertically as well as horizontally: stock `back.gif` strips are
        # far shorter than the screen (warehouse is 24px tall) and would
        # otherwise leave the canvas black wherever no panel covers it.
        y = background_y
        while y < BOR_SCREEN_H:
            _tile_horizontally(canvas, bg_rgb, bg_mask, y, BOR_SCREEN_W)
            y += bg_rgb.shape[0]

    x = -scroll_x
    for panel_name in level.ordered_panels():
        if x >= BOR_SCREEN_W:
            break
        p_rgb, p_mask = pak_index.image(panel_name)
        _blit(canvas, p_rgb, p_mask, x, panel_y)
        x += p_rgb.shape[1]

    if level.frontpanel:
        f_rgb, f_mask = pak_index.image(level.frontpanel)
        _tile_horizontally(canvas, f_rgb, f_mask, frontpanel_y, BOR_SCREEN_W)

    return canvas


def load_level(pak_index, level_entry):
    text = pak_index.read(level_entry).decode('latin1')
    return parse_level(text, name=level_entry)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pak')
    ap.add_argument('level_entry', help=r'e.g. DATA\EASY\4BEASY.TXT')
    ap.add_argument('-o', '--output', default='scene_preview.png')
    ap.add_argument('--panel-y', type=int, default=0)
    ap.add_argument('--background-y', type=int, default=0)
    ap.add_argument('--frontpanel-y', type=int, default=0)
    ap.add_argument('--scroll-x', type=int, default=0)
    args = ap.parse_args()

    idx = PakIndex(args.pak)
    level = load_level(idx, args.level_entry)
    print(level)
    canvas = composite_screen(idx, level,
                              panel_y=args.panel_y,
                              background_y=args.background_y,
                              frontpanel_y=args.frontpanel_y,
                              scroll_x=args.scroll_x)
    Image.fromarray(canvas).save(args.output)
    uniq = len(np.unique(canvas.reshape(-1, 3), axis=0))
    print(f'wrote {args.output} ({BOR_SCREEN_W}x{BOR_SCREEN_H}, {uniq} unique colors)')


if __name__ == '__main__':
    main()
