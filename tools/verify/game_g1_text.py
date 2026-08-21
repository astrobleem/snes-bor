#!/usr/bin/env python3
"""plan_game.md Phase G1 gate: BG3 text renderer (core/text.pasm).

Draws a known string and a known number at boot (see main.pasm's Phase G1
boot block, right after Vm_Boot) and reads the results back from real
hardware state -- BG3 tilemap VRAM and CGRAM -- rather than a screenshot
(see project memory mesen_screenshot_stale_hud_layer: screenshots can show a
frozen/stale BG3 layer even when the underlying VRAM already changed).

Two independent boot-time calls are checked:
  - Core_Text_DrawString(row=4, col=0, "SNES-BOR")
  - Core_Text_DrawNumber(row=5, col=0, 1024)  -- exercises a mid-number zero
    digit and leading-zero suppression, neither of which DrawString's own
    call path touches at all.

Each tilemap word is decoded back to a character via this project's own
converter constants (FONT_TILE_INDEX_BASE, FONT_CGRAM_PAL_ID), not
hardcoded numbers, so this gate tracks core/text.pasm if it ever changes
layout. The font palette write is checked too, since that was a real,
previously-silent bug (see core/text.pasm's Core_Text_Init comment).

Usage: python tools/verify/game_g1_text.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant_in, read_block, repo_root_from, Reporter  # noqa: E402

ROOT = repo_root_from(None)

# FONT_TILE_INDEX_BASE is an expression in source
# ((FONT_TILES_VRAM_WORD - BG3_TILES_VRAM_WORD) / 8), not a plain literal, so
# pasm_constant_in (which only parses `NAME = <int>`) can't read it directly.
# Derive it the same way the source does instead of hardcoding 288.
FONT_TILES_VRAM_WORD = pasm_constant_in('src/core/text.pasm', 'FONT_TILES_VRAM_WORD')
BG3_TILES_VRAM_WORD = pasm_constant_in('src/main.pasm', 'BG3_TILES_VRAM_WORD')
FONT_TILE_INDEX_BASE = (FONT_TILES_VRAM_WORD - BG3_TILES_VRAM_WORD) // 8
FONT_CGRAM_PAL_ID = pasm_constant_in('src/core/text.pasm', 'FONT_CGRAM_PAL_ID')
FONT_ASCII_FIRST = pasm_constant_in('src/core/text.pasm', 'FONT_ASCII_FIRST')
BG3_TILEMAP_VRAM_WORD = pasm_constant_in('src/main.pasm', 'BG3_TILEMAP_VRAM_WORD')
HUD_ENTRY_HIGH = pasm_constant_in('src/main.pasm', 'HUD_ENTRY_HIGH')

TEXT_ROW_ENTRIES = 32

EXPECT_STRING = 'SNES-BOR'
EXPECT_STRING_ROW = 4
EXPECT_NUMBER = 1024
EXPECT_NUMBER_ROW = 5


def read_file(path):
    with open(path, 'rb') as f:
        return f.read()


def read_row_words(m, row, count):
    """Read `count` tilemap words starting at (row, col=0) as decoded
    16-bit little-endian ints. Always reads >=32 bytes (harness rule) even
    if `count` needs fewer."""
    byte_off = (BG3_TILEMAP_VRAM_WORD + row * TEXT_ROW_ENTRIES) * 2
    length = max(32, count * 2)
    raw = read_block(m, byte_off, length=length, mem_type='snesVideoRam')
    words = []
    for i in range(count):
        lo, hi = raw[i * 2], raw[i * 2 + 1]
        words.append(lo | (hi << 8))
    return words


def decode_char(word):
    """Tilemap word -> (ascii_char, palette_id, priority_bit_set)."""
    tile_id = word & 0x03FF
    palette_id = (word >> 10) & 0x07
    priority = bool(word & 0x2000)
    char = chr(tile_id - FONT_TILE_INDEX_BASE + FONT_ASCII_FIRST)
    return char, palette_id, priority


def main():
    r = Reporter('G1', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        # --- DrawString: "SNES-BOR" at row 4 ---
        words = read_row_words(m, EXPECT_STRING_ROW, len(EXPECT_STRING))
        decoded = [decode_char(w) for w in words]
        got_string = ''.join(c for c, _, _ in decoded)
        r.check(f'DrawString text matches ({got_string!r})', got_string == EXPECT_STRING)
        r.check('DrawString palette id == FONT_CGRAM_PAL_ID for every glyph',
                 all(p == FONT_CGRAM_PAL_ID for _, p, _ in decoded))
        r.check('DrawString priority bit set for every glyph',
                 all(pr for _, _, pr in decoded))

        # --- DrawNumber: 1024 at row 5 (interior zero, leading-zero suppression) ---
        digit_str = str(EXPECT_NUMBER)
        words = read_row_words(m, EXPECT_NUMBER_ROW, len(digit_str))
        decoded = [decode_char(w) for w in words]
        got_number = ''.join(c for c, _, _ in decoded)
        r.check(f'DrawNumber digits match ({got_number!r})', got_number == digit_str)
        r.check('DrawNumber palette id == FONT_CGRAM_PAL_ID for every digit',
                 all(p == FONT_CGRAM_PAL_ID for _, p, _ in decoded))

        # --- Font palette landed in CGRAM (colors 4-7) and wasn't clobbered
        # by a later CGRAM load (Bg_LoadScene runs before Core_Text_Init on
        # purpose -- see core/text.pasm's Core_Text_Init comment). ---
        font_palette_expected = read_file(os.path.join(ROOT, 'src', 'assets', 'font_palette.bin'))
        cgram_off = FONT_CGRAM_PAL_ID * 4 * 2
        cgram = read_block(m, cgram_off, length=max(32, len(font_palette_expected)),
                            mem_type='snesCgRam')
        got_palette = cgram[:len(font_palette_expected)]
        r.check('Font CGRAM palette matches font_palette.bin',
                 got_palette == font_palette_expected)

    r.finish()


if __name__ == '__main__':
    main()
