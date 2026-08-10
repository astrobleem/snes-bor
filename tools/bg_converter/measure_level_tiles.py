#!/usr/bin/env python3
"""Measure how a BOR level's unique-tile count scales with level width.

This is the number that decides the scroll architecture (plan.md 2.7 /
Phase 8), and it is the one that cannot be guessed -- the intuition it
kills is a strong one.

WHY THE OBVIOUS GUESS IS WRONG
------------------------------
A BOR level is `order abcdefabcdef...` -- a short list of unique panels
laid side by side, repeated. So it looks like a wide level should reuse
nearly all of its tiles and stay resident in VRAM with no streaming at
all. It does not. Measured on the stock warehouse level, every fresh
320px screen adds ~800 NEW unique tiles and the cumulative curve never
flattens, because:

  * panels are 191px wide -- not a multiple of 8 -- so each repeat lands
    on a different 8x8 tile phase, and
  * convert_bg.py resamples 320x240 -> 256x224 (a 0.8 scale), so even an
    8-aligned panel would not stay aligned.

Panel repetition therefore buys you nothing, and a wide level needs a
streaming tile cache (SMI's ring-buffer model). Re-run this before
assuming otherwise about any *other* level.

WHAT IT MEASURES, AND ITS CALIBRATION
-------------------------------------
It mirrors convert_bg.py's pipeline up to the flip-aware dedup step and
stops there -- palette quantization is skipped because it can only reduce
the count (it maps distinct BGR555 patterns onto shared indexed ones), so
these are conservative upper bounds.

The shave is small and known: on the boss level's screen 0 this reports
447 unique patterns where out/bg_boss/manifest.json records 429 post-
quantization unique tiles -- about 4%. So treat the numbers here as ~4%
high, not as a different order of magnitude.

Reference results (stock pak, 2026-08-10):

    boss      DATA\\EASY\\6BEASY.TXT    420px   1.3 screens     993 tiles
    warehouse DATA\\EASY\\4BEASY.TXT   6876px  21.5 screens   9,869 tiles

Usage:
    python tools/bg_converter/measure_level_tiles.py
    python tools/bg_converter/measure_level_tiles.py --level "DATA\\EASY\\4BEASY.TXT"
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import snes_tiles as st  # noqa: E402
from composite_scene import (BOR_SCREEN_W, PakIndex,  # noqa: E402
                             composite_screen, load_level)

SNES_W, SNES_H = 256, 224
BG1_BUDGET = 512                    # current BG1 tile budget, $0000-$1FFF
BG1_BUDGET_RECLAIMED = 1024         # if dead BG2 ($2000-$3FFF) is reclaimed

DEFAULT_LEVELS = [
    (r'DATA\EASY\6BEASY.TXT', 'boss'),
    (r'DATA\EASY\4BEASY.TXT', 'warehouse'),
]


def canonical(tile):
    """Flip-aware canonical form, matching snes_tiles.dedup_bgr555's notion
    of 'the same visual pattern'."""
    return min(np.ascontiguousarray(v).tobytes()
               for v, _hflip, _vflip in st._flip_variants(tile))


def measure(idx, level_entry, name):
    level = load_level(idx, level_entry)
    ordered = level.ordered_panels()

    widths = []
    for panel in ordered:
        rgb, _mask = idx.image(panel)
        widths.append(rgb.shape[1])
    total_w = sum(widths)

    print(f'\n=== {name} ({level_entry}) ===')
    print(f'  {len(level.panels)} unique panels, order len {len(level.order)} '
          f'-> {len(ordered)} placed')
    print(f'  panel widths: {widths[:8]}{"..." if len(widths) > 8 else ""}')
    print(f'  total level width: {total_w}px '
          f'({total_w / BOR_SCREEN_W:.1f} screens)')

    seen = set()
    rows = []
    for scroll in range(0, max(total_w, 1), BOR_SCREEN_W):
        scene = composite_screen(idx, level, scroll_x=scroll)
        img = Image.fromarray(scene).resize((SNES_W, SNES_H), Image.NEAREST)
        bgr = st.rgb_array_to_bgr555(np.array(img, dtype=np.uint8))
        uniq, _pos_to_uid, _flips = st.dedup_bgr555(st.image_to_tiles(bgr))
        for tile in uniq:
            seen.add(canonical(tile))
        rows.append((scroll, len(uniq), len(seen)))

    print(f'  {len(rows)} screens walked')
    print(f'  {"scroll_x":>9} {"this screen":>12} {"cumulative":>11}')
    for scroll, this_screen, cum in rows:
        print(f'  {scroll:>9} {this_screen:>12} {cum:>11}')

    per_screen = max(r[1] for r in rows)
    print(f'\n  WORKING SET (worst single screen): {per_screen} tiles')
    for label, budget in (('512 (current BG1)', BG1_BUDGET),
                          ('1024 (reclaiming dead BG2)', BG1_BUDGET_RECLAIMED)):
        verdict = 'FITS' if per_screen <= budget else f'OVER by {per_screen - budget}'
        print(f'    vs {label}: {verdict}')

    print(f'  WHOLE LEVEL: {len(seen)} tiles  '
          f'({"resident, no streaming needed" if len(seen) <= BG1_BUDGET_RECLAIMED else "streaming required"})')
    return len(seen), per_screen


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pak', default='Beats of Rage Original [v.3.0 Build 4086].pak')
    ap.add_argument('--level', action='append', default=None,
                    help='level entry, e.g. "DATA\\EASY\\4BEASY.TXT" (repeatable)')
    args = ap.parse_args()

    idx = PakIndex(args.pak)
    levels = ([(lv, lv) for lv in args.level] if args.level else DEFAULT_LEVELS)
    for entry, name in levels:
        measure(idx, entry, name)


if __name__ == '__main__':
    main()
