#!/usr/bin/env python3
"""plan_game.md Phase G5 gate: title screen (core/game_state.pasm's
Game_State_Play__title dispatch).

Scope of this phase, per the advisor consult recorded in core/game_state.pasm's
own Phase G5 header: only the title screen is built. GAME_STATE_PLAYING stays
the boot default (every other routine gate in this project drives the ROM
from boot expecting gameplay already running); TITLE is reached the same way
game_g2_states.py already tests it -- a forced Game_State write, simulating
what a future GAME OVER timeout / pause-quit path already does for real
(Game_State_Play__gameover_timeout, Phase G3).

Two things checked, both against ground truth the engine did not produce
(the string constants themselves and real hardware state), never a
screenshot (memory mesen_screenshot_stale_hud_layer: screenshots can show a
frozen BG3 layer even when VRAM already changed):

  1. The drip. Core_Text_DrawString shares one WRAM staging buffer with a
     QUEUED (not synchronous) DMA -- two calls in the same frame corrupt each
     other (text.pasm's own documented "1024-BOR" bug). The title screen
     draws two full-width rows one frame apart (Title_Step), so this gate
     runs enough frames for the whole drip (draw main, draw press-start, then
     idle) and reads BOTH rows back from the BG3 tilemap, decoding each tile
     word the same way game_g1_text.py does (FONT_TILE_INDEX_BASE/
     FONT_CGRAM_PAL_ID -- this project's own converter constants, not
     hardcoded numbers).
  2. The teardown. Start (via set_input, wall-clock-based -- memory
     mesen_set_input_wall_clock, so this only asserts the eventual
     transition/clear, never an exact frame count) should clear both rows
     back to blank AND land back in GAME_STATE_PLAYING. A title screen that
     forgot to blank its own rows would leave "PRESS START" burned into BG3
     during gameplay -- BG3 draws above OBJ (HUD_ENTRY_HIGH), so this would
     be a real, visible bug, not a cosmetic nit.

Usage: python tools/verify/game_g5_menus.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant_in, read_block, Reporter  # noqa: E402

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STATE_TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
TITLE_ROW_MAIN = pasm_constant_in('src/core/game_state.pasm', 'TITLE_ROW_MAIN')
TITLE_ROW_PRESS = pasm_constant_in('src/core/game_state.pasm', 'TITLE_ROW_PRESS')

FONT_TILES_VRAM_WORD = pasm_constant_in('src/core/text.pasm', 'FONT_TILES_VRAM_WORD')
BG3_TILES_VRAM_WORD = pasm_constant_in('src/main.pasm', 'BG3_TILES_VRAM_WORD')
FONT_TILE_INDEX_BASE = (FONT_TILES_VRAM_WORD - BG3_TILES_VRAM_WORD) // 8
FONT_CGRAM_PAL_ID = pasm_constant_in('src/core/text.pasm', 'FONT_CGRAM_PAL_ID')
FONT_ASCII_FIRST = pasm_constant_in('src/core/text.pasm', 'FONT_ASCII_FIRST')
BG3_TILEMAP_VRAM_WORD = pasm_constant_in('src/main.pasm', 'BG3_TILEMAP_VRAM_WORD')

TEXT_ROW_ENTRIES = 32

# Same 32-column, trailing-space-padded strings core/game_state.pasm draws --
# see main.pasm's Text_StringPool for why the padding is real content, not
# cosmetic (avoids stale-column garbage from TextStaging's buffer reuse).
EXPECT_MAIN = 'SNES-BOR'.ljust(TEXT_ROW_ENTRIES)
EXPECT_PRESS = 'PRESS START'.ljust(TEXT_ROW_ENTRIES)
EXPECT_BLANK = ' ' * TEXT_ROW_ENTRIES


def read_row_words(m, row, count=TEXT_ROW_ENTRIES):
    byte_off = (BG3_TILEMAP_VRAM_WORD + row * TEXT_ROW_ENTRIES) * 2
    length = max(32, count * 2)
    raw = read_block(m, byte_off, length=length, mem_type='snesVideoRam')
    words = []
    for i in range(count):
        lo, hi = raw[i * 2], raw[i * 2 + 1]
        words.append(lo | (hi << 8))
    return words


def decode_row(m, row):
    words = read_row_words(m, row)
    chars = []
    for w in words:
        tile_id = w & 0x03FF
        chars.append(chr(tile_id - FONT_TILE_INDEX_BASE + FONT_ASCII_FIRST))
    return ''.join(chars)


def set_game_state(m, value):
    m.write_u16(GAME_STATE, value)


def main():
    r = Reporter('G5', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        # --- Force TITLE, same as game_g2_states.py -- there is no menu
        # content anywhere else yet that reaches it organically within a
        # short gate run (only a real GAME OVER timeout does, Phase G3). ---
        set_game_state(m, GAME_STATE_TITLE)

        # Let the drip run to completion: draw main row, draw press-start
        # row, then settle into the wait step. Each step advances at most
        # once per frame (Game_State_Play__title runs once per
        # scpu_main_loop iteration), so a healthy handful of frames is far
        # more than the 2 steps actually needed.
        m.run_frames(30)
        m.pause()

        got_main = decode_row(m, TITLE_ROW_MAIN)
        got_press = decode_row(m, TITLE_ROW_PRESS)
        r.check(f'title row ({TITLE_ROW_MAIN}) matches ({got_main!r})',
                 got_main == EXPECT_MAIN)
        r.check(f'press-start row ({TITLE_ROW_PRESS}) matches ({got_press!r})',
                 got_press == EXPECT_PRESS)

        got_state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'Game_State still GAME_STATE_TITLE after the drip settles ({got_state})',
                 got_state == GAME_STATE_TITLE)

        # --- Start: teardown drip (blank both rows), then PLAYING. ---
        m.set_input(m.BTN_START, 10)
        m.run_frames(60)
        m.pause()

        got_state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'Start transitions back to GAME_STATE_PLAYING ({got_state})',
                 got_state == GAME_STATE_PLAYING)

        got_main = decode_row(m, TITLE_ROW_MAIN)
        got_press = decode_row(m, TITLE_ROW_PRESS)
        r.check(f'title row ({TITLE_ROW_MAIN}) cleared on exit ({got_main!r})',
                 got_main == EXPECT_BLANK)
        r.check(f'press-start row ({TITLE_ROW_PRESS}) cleared on exit ({got_press!r})',
                 got_press == EXPECT_BLANK)

    r.finish()


if __name__ == '__main__':
    main()
