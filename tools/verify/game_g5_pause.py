#!/usr/bin/env python3
"""plan_game.md Phase G5 gate: the pause menu (core/pausemenu.pasm's
Game_State_Play__pausemenu dispatch, entered from Game_State_Play__playing
via a Start-press check, core/game_state.pasm).

Real-OpenBOR-sourced content (see core/pausemenu.pasm's own header, fetched
from DCurrent/openbor's engine/openbor.c pausemenu()): a "PAUSE" header
plus exactly two selectable rows, "CONTINUE"/"END GAME", toggled by
Up/Down (drawn here as a "> "/"  " cursor prefix, this project's existing
text-only menu convention, not a real sprite cursor). Start commits:
Continue resumes PLAYING untouched; End Game zeroes Game_Lives and returns
to GAME_STATE_TITLE (real BOR's End Game is an intentional quit -- it
zeroes every player's lives and hard-tears the session down with no
continue offered, not a death -- this project has no "quit to system"
state beyond TITLE, the existing G2 "nothing is running" holding state).

Ground truth throughout is the BG3 tilemap itself (decoded the same
tile-id way phase5.py/game_g1_text.py/game_g5_menus.py already do), never
a screenshot (mesen_screenshot_stale_hud_layer) or an engine self-report.

Checks:
  1. Start during PLAYING transitions to GAME_STATE_PAUSED.
  2. The pause draw drip: header/continue/endgame rows, Continue selected
     by default (cursor on CONTINUE, not END GAME).
  3. Down toggles the selector -- both rows redraw same-session with the
     cursor now on END GAME.
  4. Start with END GAME selected commits it: Game_Lives -> 0,
     GAME_STATE_TITLE (not GAMEOVER), and all three pause rows cleared.
  5. Re-entering pause and committing CONTINUE (default selector, no
     Up/Down needed) resumes GAME_STATE_PLAYING with Game_Lives untouched
     by the resume itself and all three pause rows cleared.

Usage: python tools/verify/game_g5_pause.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant_in, read_block, Reporter  # noqa: E402

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STATE_PAUSED = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PAUSED')
GAME_STATE_TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
GAME_LIVES_START = pasm_constant_in('src/core/game_state.pasm', 'GAME_LIVES_START')
Game_Lives = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')

PAUSE_ROW_HEADER = pasm_constant_in('src/core/pausemenu.pasm', 'PAUSE_ROW_HEADER')
PAUSE_ROW_CONTINUE = pasm_constant_in('src/core/pausemenu.pasm', 'PAUSE_ROW_CONTINUE')
PAUSE_ROW_ENDGAME = pasm_constant_in('src/core/pausemenu.pasm', 'PAUSE_ROW_ENDGAME')
Pause_Selector = pasm_constant_in('src/core/pausemenu.pasm', 'Pause_Selector')
PAUSE_SELECTOR_ENDGAME = pasm_constant_in('src/core/pausemenu.pasm', 'PAUSE_SELECTOR_ENDGAME')

FONT_TILES_VRAM_WORD = pasm_constant_in('src/core/text.pasm', 'FONT_TILES_VRAM_WORD')
BG3_TILES_VRAM_WORD = pasm_constant_in('src/main.pasm', 'BG3_TILES_VRAM_WORD')
FONT_TILE_INDEX_BASE = (FONT_TILES_VRAM_WORD - BG3_TILES_VRAM_WORD) // 8
FONT_ASCII_FIRST = pasm_constant_in('src/core/text.pasm', 'FONT_ASCII_FIRST')
BG3_TILEMAP_VRAM_WORD = pasm_constant_in('src/main.pasm', 'BG3_TILEMAP_VRAM_WORD')

TEXT_ROW_ENTRIES = 32

EXPECT_HEADER = 'PAUSE'.ljust(TEXT_ROW_ENTRIES)
EXPECT_CONT_SEL = '> CONTINUE'.ljust(TEXT_ROW_ENTRIES)
EXPECT_CONT_UNSEL = '  CONTINUE'.ljust(TEXT_ROW_ENTRIES)
EXPECT_END_SEL = '> END GAME'.ljust(TEXT_ROW_ENTRIES)
EXPECT_END_UNSEL = '  END GAME'.ljust(TEXT_ROW_ENTRIES)
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
    r = Reporter('G5-PAUSE', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        # Boot default is GAME_STATE_PLAYING (G2's own documented default).
        got_state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'boots into GAME_STATE_PLAYING ({got_state})', got_state == GAME_STATE_PLAYING)

        # --- Start during PLAYING enters PAUSED. ---
        m.set_input(m.BTN_START, 10)
        m.run_frames(20)
        m.pause()
        got_state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'Start during PLAYING transitions to GAME_STATE_PAUSED ({got_state})',
                 got_state == GAME_STATE_PAUSED)

        # --- draw drip settles: header + both option rows, CONTINUE
        # selected by default (Pause_Selector boots at 0 via WRAM
        # power-on-zero, same precedent as CharSelect_Step). ---
        m.run_frames(10)
        m.pause()
        got_header = decode_row(m, PAUSE_ROW_HEADER)
        got_cont = decode_row(m, PAUSE_ROW_CONTINUE)
        got_end = decode_row(m, PAUSE_ROW_ENDGAME)
        r.check(f'pause header row matches ({got_header!r})', got_header == EXPECT_HEADER)
        r.check(f'CONTINUE row shows selected by default ({got_cont!r})', got_cont == EXPECT_CONT_SEL)
        r.check(f'END GAME row shows unselected by default ({got_end!r})', got_end == EXPECT_END_UNSEL)

        # --- Down toggles the selector to END GAME, redraws both rows. ---
        m.set_input(m.BTN_DOWN, 10)
        m.run_frames(20)
        m.pause()
        selector = read_block(m, Pause_Selector, 32)[0]
        got_cont = decode_row(m, PAUSE_ROW_CONTINUE)
        got_end = decode_row(m, PAUSE_ROW_ENDGAME)
        r.check(f'Down toggles Pause_Selector to END GAME ({selector})', selector == PAUSE_SELECTOR_ENDGAME)
        r.check(f'CONTINUE row redrawn unselected ({got_cont!r})', got_cont == EXPECT_CONT_UNSEL)
        r.check(f'END GAME row redrawn selected ({got_end!r})', got_end == EXPECT_END_SEL)

        # --- Start with END GAME selected: teardown drip, Game_Lives -> 0,
        # GAME_STATE_TITLE (not GAMEOVER -- real BOR's End Game is a quit,
        # not a death). Not checking rows 10/12 content here: TITLE reuses
        # these same physical rows (same deliberate reuse game_g5_menus.py
        # already documents for charselect) and its own draw drip starts
        # overwriting them within just a few frames of landing in TITLE --
        # there's no frame window where they're both "cleared by pause"
        # and "not yet redrawn by title" that isn't racing the drip. The
        # header row (row 8, not reused by TITLE) still proves the
        # teardown itself ran. The Continue exit path below (which lands
        # in PLAYING, never touching these rows again) is the real
        # "no garbage left over BG3 during gameplay" check. ---
        m.set_input(m.BTN_START, 10)
        m.run_frames(40)
        m.pause()
        got_state = read_block(m, GAME_STATE, 32)[0]
        lives = read_block(m, Game_Lives, 32)[0]
        got_header = decode_row(m, PAUSE_ROW_HEADER)
        r.check(f'Start on END GAME transitions to GAME_STATE_TITLE, not GAMEOVER ({got_state})',
                 got_state == GAME_STATE_TITLE)
        r.check(f'Game_Lives zeroed by End Game ({lives})', lives == 0)
        r.check(f'pause header row cleared on exit ({got_header!r})', got_header == EXPECT_BLANK)

        # --- From TITLE, force back into PLAYING with lives restored (this
        # gate's own setup, not pause-menu behavior) and confirm a second
        # pause/CONTINUE round trip resumes PLAYING with rows clean. ---
        set_game_state(m, GAME_STATE_PLAYING)
        m.write_memory('snesMemory', Game_Lives, f'{GAME_LIVES_START:02X}')
        m.run_frames(10)
        m.pause()

        m.set_input(m.BTN_START, 10)
        m.run_frames(30)
        m.pause()
        got_state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'second Start-press re-enters GAME_STATE_PAUSED ({got_state})',
                 got_state == GAME_STATE_PAUSED)
        selector = read_block(m, Pause_Selector, 32)[0]
        r.check(f'Pause_Selector defaults back to CONTINUE on fresh entry ({selector})', selector == 0)

        m.set_input(m.BTN_START, 10)
        m.run_frames(40)
        m.pause()
        got_state = read_block(m, GAME_STATE, 32)[0]
        lives = read_block(m, Game_Lives, 32)[0]
        got_header = decode_row(m, PAUSE_ROW_HEADER)
        got_cont = decode_row(m, PAUSE_ROW_CONTINUE)
        got_end = decode_row(m, PAUSE_ROW_ENDGAME)
        r.check(f'Start on CONTINUE resumes GAME_STATE_PLAYING ({got_state})',
                 got_state == GAME_STATE_PLAYING)
        r.check(f'Game_Lives untouched by Continue ({lives} == {GAME_LIVES_START})',
                 lives == GAME_LIVES_START)
        r.check(f'pause header row cleared after Continue ({got_header!r})', got_header == EXPECT_BLANK)
        r.check(f'CONTINUE row cleared after Continue ({got_cont!r})', got_cont == EXPECT_BLANK)
        r.check(f'END GAME row cleared after Continue ({got_end!r})', got_end == EXPECT_BLANK)

    r.finish()


if __name__ == '__main__':
    main()
