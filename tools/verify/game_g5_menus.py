#!/usr/bin/env python3
"""plan_game.md Phase G5 gate: title screen + character-select screen
(core/game_state.pasm's Game_State_Play__title dispatch and core/
charselect.pasm's Game_State_Play__charselect dispatch).

Scope of this phase, per the advisor consult recorded in core/game_state.pasm's
own Phase G5 header: GAME_STATE_PLAYING stays the boot default (every other
routine gate in this project drives the ROM from boot expecting gameplay
already running); TITLE is reached the same way game_g2_states.py already
tests it -- a forced Game_State write, simulating what a real GAME OVER
timeout / pause-quit path already does for real (Game_State_Play__gameover_
timeout, Phase G3).

Character select was added later in the same phase: Start at the title
screen now lands in GAME_STATE_CHARSELECT (not straight to PLAYING) --
core/charselect.pasm re-skins the roster machinery that already existed
(CharSelect_Index/RosterCount/Loaded, Anim_LoadCharacter, the same live-
reselect path the Select button has used since plan.md Phase 5) as a real
screen: a header row, the current character's name, an instructions row,
and Left/Right navigation before Start proceeds into PLAYING.

Everything checked here is against ground truth the engine did not produce
(the string constants themselves and real hardware state), never a
screenshot (memory mesen_screenshot_stale_hud_layer: screenshots can show a
frozen BG3 layer even when VRAM already changed):

  1. The title drip (unchanged from before charselect existed): two rows,
     one frame apart, decoded from the BG3 tilemap the same way
     game_g1_text.py does (FONT_TILE_INDEX_BASE/FONT_CGRAM_PAL_ID).
  2. Start at title lands in GAME_STATE_CHARSELECT now, not PLAYING.
  3. The charselect drip: header/name/instr rows, each decoded the same way.
     Name row must show the roster's slot-0 character (RALF) initially --
     CharSelect_Index starts at 0 (boot default, plan.md Phase 5).
  4. Right cycles CharSelect_Index forward and redraws the name row
     immediately (one DrawString call, same frame) -- also confirms
     Anim_LoadCharacter actually re-ran (CharSelect_Loaded stays 1, the
     entity's own CGRAM palette changes to the new character's, same
     ground truth phase12_roster.py uses for the Select button).
  5. Left wraps back to the roster's last slot from slot 0.
  6. Start at charselect finishes the teardown drip (all three rows
     cleared) AND lands in GAME_STATE_PLAYING -- a menu screen that forgot
     to blank its own rows would leave real, visible garbage during
     gameplay (BG3 draws above OBJ), not a cosmetic nit.

Usage: python tools/verify/game_g5_menus.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant_in, read_block, Reporter  # noqa: E402

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STATE_TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
GAME_STATE_CHARSELECT = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_CHARSELECT')
TITLE_ROW_MAIN = pasm_constant_in('src/core/game_state.pasm', 'TITLE_ROW_MAIN')
TITLE_ROW_PRESS = pasm_constant_in('src/core/game_state.pasm', 'TITLE_ROW_PRESS')
CHARSELECT_ROW_HEADER = pasm_constant_in('src/core/game_state.pasm', 'CHARSELECT_ROW_HEADER')
CHARSELECT_ROW_NAME = pasm_constant_in('src/core/game_state.pasm', 'CHARSELECT_ROW_NAME')
CHARSELECT_ROW_INSTR = pasm_constant_in('src/core/game_state.pasm', 'CHARSELECT_ROW_INSTR')

CharSelect_Index = 0x7E53B6
CharSelect_RosterCount = 0x7E53B7
CharSelect_Loaded = 0x7E53B8
PLAYER_PALETTE_ADDR = 0x100   # CHAR_PALETTE_SLOT==0, same layout phase12_roster.py uses

FONT_TILES_VRAM_WORD = pasm_constant_in('src/core/text.pasm', 'FONT_TILES_VRAM_WORD')
BG3_TILES_VRAM_WORD = pasm_constant_in('src/main.pasm', 'BG3_TILES_VRAM_WORD')
FONT_TILE_INDEX_BASE = (FONT_TILES_VRAM_WORD - BG3_TILES_VRAM_WORD) // 8
FONT_CGRAM_PAL_ID = pasm_constant_in('src/core/text.pasm', 'FONT_CGRAM_PAL_ID')
FONT_ASCII_FIRST = pasm_constant_in('src/core/text.pasm', 'FONT_ASCII_FIRST')
BG3_TILEMAP_VRAM_WORD = pasm_constant_in('src/main.pasm', 'BG3_TILEMAP_VRAM_WORD')

TEXT_ROW_ENTRIES = 32

# Same 32-column, trailing-space-padded strings core/game_state.pasm and
# core/charselect.pasm draw -- see main.pasm's Text_StringPool for why the
# padding is real content, not cosmetic (avoids stale-column garbage from
# TextStaging's buffer reuse).
EXPECT_MAIN = 'SNES-BOR'.ljust(TEXT_ROW_ENTRIES)
EXPECT_PRESS = 'PRESS START'.ljust(TEXT_ROW_ENTRIES)
EXPECT_BLANK = ' ' * TEXT_ROW_ENTRIES
EXPECT_HEADER = 'CHARACTER SELECT'.ljust(TEXT_ROW_ENTRIES)
EXPECT_INSTR = 'LEFT/RIGHT SELECT  START GO'.ljust(TEXT_ROW_ENTRIES)
EXPECT_RALF = 'RALF'.ljust(TEXT_ROW_ENTRIES)
EXPECT_JHUN = 'JHUN'.ljust(TEXT_ROW_ENTRIES)
# The roster's last slot -- was YASHIRO (index 3) through Phase 15; grew to
# 6 (MOUSER, FOOT01) for the TMNT campaign, 8 (ROCK, LEATHER) for the
# spawn-driven roster-reassignment slice, and 12 (BEBOP, FOOT02-04) for the
# roster-growth slice (pack_msu_roster.py's MAX_CHARACTERS 8->15), so the
# wrap-from-slot-0 target is now roster_count-1 == 11 (FOOT04, displayed as
# "FOOT SOLDIER" -- same real display name as FOOT01-03, they're mechanical
# clones in the source pak -- see main.pasm's CharSelect_NamePtrs). Real bug
# caught by this exact check TWICE already: CharSelect_NamePtrs hadn't grown
# to match ROSTER_PREFIXES and read garbage past its own end -- this
# constant must be updated every time the roster's real last slot changes.
EXPECT_LAST_SLOT = 'FOOT SOLDIER'.ljust(TEXT_ROW_ENTRIES)


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

        # --- Force TITLE, same as game_g2_states.py. ---
        set_game_state(m, GAME_STATE_TITLE)
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

        # --- Start at title: teardown drip (blank both title rows), then
        # CHARSELECT (not PLAYING directly anymore). ---
        m.set_input(m.BTN_START, 10)
        m.run_frames(60)
        m.pause()

        got_state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'Start at title transitions to GAME_STATE_CHARSELECT ({got_state})',
                 got_state == GAME_STATE_CHARSELECT)

        # Not checking title rows 10/12 for blank here: charselect's own
        # NAME/INSTR rows are the SAME physical rows (deliberate reuse --
        # title already cleared them before handing off, and charselect's
        # own drip has had time to draw over them again by now, which is
        # exactly what the checks just below assert).

        # --- charselect draw drip: header, name, instr (one frame each). ---
        got_header = decode_row(m, CHARSELECT_ROW_HEADER)
        got_name = decode_row(m, CHARSELECT_ROW_NAME)
        got_instr = decode_row(m, CHARSELECT_ROW_INSTR)
        r.check(f'charselect header row ({CHARSELECT_ROW_HEADER}) matches ({got_header!r})',
                 got_header == EXPECT_HEADER)
        r.check(f'charselect name row ({CHARSELECT_ROW_NAME}) shows RALF initially ({got_name!r})',
                 got_name == EXPECT_RALF)
        r.check(f'charselect instructions row ({CHARSELECT_ROW_INSTR}) matches ({got_instr!r})',
                 got_instr == EXPECT_INSTR)

        idx = read_block(m, CharSelect_Index, 32)[0]
        roster_count = read_block(m, CharSelect_RosterCount, 32)[0]
        loaded = read_block(m, CharSelect_Loaded, 32)[0]
        r.check(f'CharSelect_Index starts at 0 ({idx})', idx == 0)
        r.check(f'CharSelect_Loaded == 1 ({loaded})', loaded == 1)

        # --- Right: cycles forward, redraws the name row same-frame,
        # reloads the character (ground truth: CGRAM palette changes,
        # same signal phase12_roster.py uses for the Select button). ---
        pal_before = bytes(read_block(m, PLAYER_PALETTE_ADDR, 32, mem_type='snesCgRam'))
        m.set_input(m.BTN_RIGHT, 10)
        m.run_frames(30)
        m.pause()

        idx = read_block(m, CharSelect_Index, 32)[0]
        got_name = decode_row(m, CHARSELECT_ROW_NAME)
        loaded = read_block(m, CharSelect_Loaded, 32)[0]
        pal_after = bytes(read_block(m, PLAYER_PALETTE_ADDR, 32, mem_type='snesCgRam'))
        r.check(f'Right advances CharSelect_Index to 1 ({idx})', idx == 1)
        r.check(f'name row redrawn to JHUN after Right ({got_name!r})',
                 got_name == EXPECT_JHUN)
        r.check(f'CharSelect_Loaded still 1 after Right reselect ({loaded})', loaded == 1)
        r.check('CGRAM palette changed after Right reselect (real reload, not just the index)',
                 pal_after != pal_before)

        # --- Left from slot 1 goes back to slot 0 (RALF). ---
        m.set_input(m.BTN_LEFT, 10)
        m.run_frames(30)
        m.pause()
        idx = read_block(m, CharSelect_Index, 32)[0]
        got_name = decode_row(m, CHARSELECT_ROW_NAME)
        r.check(f'Left decrements CharSelect_Index back to 0 ({idx})', idx == 0)
        r.check(f'name row redrawn to RALF after Left ({got_name!r})', got_name == EXPECT_RALF)

        # --- Left again from slot 0 wraps to the roster's last slot. ---
        m.set_input(m.BTN_LEFT, 10)
        m.run_frames(30)
        m.pause()
        idx = read_block(m, CharSelect_Index, 32)[0]
        got_name = decode_row(m, CHARSELECT_ROW_NAME)
        r.check(f'Left from slot 0 wraps to roster_count-1 ({idx} == {roster_count - 1})',
                 idx == roster_count - 1)
        r.check(f'name row redrawn to the roster\'s real last slot after wrap ({got_name!r})',
                 got_name == EXPECT_LAST_SLOT)

        # --- Start at charselect: teardown drip (blank all three rows),
        # then GAME_STATE_PLAYING. ---
        m.set_input(m.BTN_START, 10)
        m.run_frames(60)
        m.pause()

        got_state = read_block(m, GAME_STATE, 32)[0]
        r.check(f'Start at charselect transitions to GAME_STATE_PLAYING ({got_state})',
                 got_state == GAME_STATE_PLAYING)

        got_header = decode_row(m, CHARSELECT_ROW_HEADER)
        got_name = decode_row(m, CHARSELECT_ROW_NAME)
        got_instr = decode_row(m, CHARSELECT_ROW_INSTR)
        r.check(f'charselect header row cleared on exit ({got_header!r})', got_header == EXPECT_BLANK)
        r.check(f'charselect name row cleared on exit ({got_name!r})', got_name == EXPECT_BLANK)
        r.check(f'charselect instructions row cleared on exit ({got_instr!r})', got_instr == EXPECT_BLANK)

    r.finish()


if __name__ == '__main__':
    main()
