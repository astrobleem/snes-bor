#!/usr/bin/env python3
"""plan_game.md G10 gate: ending/credits sequence + return to title +
new-game state reset (core/ending.pasm's Game_State_Play__ending dispatch,
core/game_state.pasm's GAME_STATE_ENDING wiring, and Game_State_
NewGameReset).

Real-source grounding (see core/ending.pasm's own header for the full
citation): the last level-order entry in every one of BOR's real 3
difficulty sets is `scene data/scenes/ending.txt`, reached only once the
final stage's own `next` marker advances past the last real level -- this
project's own Game_StageIndex+1>=STAGE_COUNT edge in
Game_State_Play__stageclear. This gate accelerates ONLY that precondition
(direct WRAM force of Game_StageIndex/Stage_LoadPending, same technique
game_health_override.py/game_g9_wait_group_boss.py already established as
safe) -- the actual STAGECLEAR -> ENDING -> credits -> TITLE -> CHARSELECT
-> PLAYING transition chain below all runs via real engine frames, not
direct state writes, per claude_begin_g10_with_approval.md's own "prove
the real flow" requirement.

Checks, in order:
  1. Forcing the STACECLEAR-with-no-stages-left precondition and running
     real frames lands in GAME_STATE_ENDING (not looped/crashed).
  2. Gameplay is genuinely quiescent in ENDING: OAM is hidden (same
     DEAD_OAM_Y convention game_g5_menus.py already uses to prove a
     non-playing state isn't drawing gameplay sprites) and Game_Score
     does not change across many frames (no combat/scoring running).
  3. Real ending/credits text appears in VRAM (decoded via decode_row,
     ground truth, never a screenshot -- mesen_screenshot_stale_hud_layer
     project memory) for all 3 real pages (completion message, credits,
     thanks), matching main.pasm's own Text_Str_Ending* strings exactly.
  4. Advancing (skip via any button, matching real playgif()'s own
     FLAG_ANYBUTTON-skips-a-clip behavior, sourced from openbor.c
     directly) moves through all 3 pages and returns to GAME_STATE_TITLE.
  5. Ending_Step self-resets (next real ENDING entry starts at page A
     again, not wherever it was left).
  6. Driving TITLE -> CHARSELECT -> PLAYING for real (Start presses, the
     same real input path game_g5_menus.py already uses) proves the G10
     state-reset audit: Game_Score/Game_StageIndex/Game_Lives are back to
     their real fresh-game values, not the just-finished playthrough's.

Usage: python tools/verify/game_g10_ending_credits.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, pasm_constant_in,
                      exact_input_edge, poll_until, read_block, Reporter)  # noqa: E402

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STATE_TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
GAME_STATE_STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
GAME_STATE_ENDING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_ENDING')
STAGE_COUNT = pasm_constant_in('src/core/game_state.pasm', 'STAGE_COUNT')
GAME_LIVES_START = pasm_constant_in('src/core/game_state.pasm', 'GAME_LIVES_START')
Game_StageIndex = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
Stage_LoadPending = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
Stage_Cleared = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
Game_Score = pasm_constant_in('src/core/game_state.pasm', 'Game_Score')
Game_Lives = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')
MUSIC_LAST_TRACK = pasm_constant('Music_LastTrack')
MUSIC_LAST_TRANSITION = pasm_constant('Music_LastTransition')
MUSIC_PLAY_STATE = pasm_constant('Music_PlayState')
MUSIC_TRANSITION_ENDING = pasm_constant('MUSIC_TRANSITION_ENDING')
MUSIC_ENDING_TRACK = pasm_constant_in('tools/audio/audio_music_ids.pasm', 'Music_EndingTrack')

TITLE_STEP_WAIT = pasm_constant_in('src/core/game_state.pasm', 'TITLE_STEP_WAIT')
Title_Step = pasm_constant_in('src/core/game_state.pasm', 'Title_Step')
Ending_Step = pasm_constant_in('src/core/ending.pasm', 'Ending_Step')
ENDING_ROW_LINE1 = pasm_constant_in('src/core/ending.pasm', 'ENDING_ROW_LINE1')
ENDING_ROW_LINE2 = pasm_constant_in('src/core/ending.pasm', 'ENDING_ROW_LINE2')

FONT_TILES_VRAM_WORD = pasm_constant_in('src/core/text.pasm', 'FONT_TILES_VRAM_WORD')
BG3_TILES_VRAM_WORD = pasm_constant_in('src/main.pasm', 'BG3_TILES_VRAM_WORD')
FONT_TILE_INDEX_BASE = (FONT_TILES_VRAM_WORD - BG3_TILES_VRAM_WORD) // 8
FONT_ASCII_FIRST = pasm_constant_in('src/core/text.pasm', 'FONT_ASCII_FIRST')
BG3_TILEMAP_VRAM_WORD = pasm_constant_in('src/main.pasm', 'BG3_TILEMAP_VRAM_WORD')

TEXT_ROW_ENTRIES = 32
DEAD_OAM_Y = 0xF0

# Same real strings main.pasm's Text_Str_Ending* db lines carry -- ground
# truth the engine did not produce, transcribed here for comparison the
# same way every other text gate in this project (game_g1_text.py,
# game_g5_menus.py) already does.
EXPECT_A1 = 'YOU HAVE COMPLETED THE GAME'.ljust(TEXT_ROW_ENTRIES)
EXPECT_A2 = 'CONGRATULATIONS'.ljust(TEXT_ROW_ENTRIES)
EXPECT_B1 = 'SNES-BOR: A FAN SA-1 SNES PORT'.ljust(TEXT_ROW_ENTRIES)
EXPECT_B2 = 'OF BEATS OF RAGE BY SENILETEAM'.ljust(TEXT_ROW_ENTRIES)
EXPECT_C1 = 'THANKS FOR PLAYING'.ljust(TEXT_ROW_ENTRIES)
EXPECT_C2 = 'MADE WITH POPPY + TAD + MESEN2'.ljust(TEXT_ROW_ENTRIES)
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


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def oam_hidden(m):
    # Same convention game_g5_menus.py already uses: real hardware OAM
    # (mem_type='snesSpriteRam', NOT the WRAM shadow), slot-0's Y byte
    # (entry 0's 4-byte record is X,Y,tile,attr -- Y is byte offset 1),
    # hidden == DEAD_OAM_Y.
    oam = read_block(m, 0, 128, mem_type='snesSpriteRam')
    return oam[1] == DEAD_OAM_Y


def wait_for_page(m, row1, row2, expect1, expect2, max_frames=120):
    for _ in range(max_frames):
        if decode_row(m, row1) == expect1 and decode_row(m, row2) == expect2:
            return True
        m.run_frames(1)
        m.pause()
    return False


def main():
    r = Reporter('G10', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        m.pause()

        # ================= precondition: accelerate to final-stage-clear =================
        # Direct WRAM force (real technique this project's own gates already
        # use), NOT a direct write of GAME_STATE_ENDING itself -- the real
        # STAGECLEAR dispatch (core/game_state.pasm) is what must actually
        # observe "no stages left" and transition, not this script.
        m.write_u16(Game_StageIndex, STAGE_COUNT - 1)
        m.write_memory('snesMemory', Stage_LoadPending, '01')
        m.write_memory('snesMemory', Stage_Cleared, '00')
        m.write_u16(GAME_STATE, GAME_STATE_STAGECLEAR)
        entered_ending = poll_until(
            m, lambda session: u16(session, GAME_STATE) == GAME_STATE_ENDING,
            max_frames=120,
        )
        m.pause()
        state = u16(m, GAME_STATE)
        r.check('final-stage completion (Game_StageIndex+1>=STAGE_COUNT) reaches '
                f'GAME_STATE_ENDING via the real STAGECLEAR dispatch (got {state})',
                entered_ending and state == GAME_STATE_ENDING)
        r.check('the real ENDING transition requested its authored MSU track',
                u8(m, MUSIC_LAST_TRACK) == MUSIC_ENDING_TRACK
                and u8(m, MUSIC_LAST_TRANSITION) == MUSIC_TRANSITION_ENDING
                and u8(m, MUSIC_PLAY_STATE) == 1)

        # ================= gameplay is genuinely quiescent =================
        r.check('OAM slot 0 is hidden in ENDING (no gameplay sprites drawn)',
                oam_hidden(m))
        score_before = u16(m, Game_Score)
        m.run_frames(60)
        m.pause()
        score_after = u16(m, Game_Score)
        r.check('Game_Score does not change across 60 ENDING frames (no combat/'
                f'scoring running): {score_before} -> {score_after}',
                score_before == score_after)
        r.check('Game_State is still GAME_STATE_ENDING after 60 quiescent frames '
                '(not accidentally advancing on its own)',
                u16(m, GAME_STATE) == GAME_STATE_ENDING)

        # ================= real page A (completion message) =================
        got_a = wait_for_page(m, ENDING_ROW_LINE1, ENDING_ROW_LINE2, EXPECT_A1, EXPECT_A2)
        r.check('page A (completion message) real text appears in VRAM, matching '
                'main.pasm\'s own Text_Str_EndingA1/A2 byte-for-byte', got_a)

        # ================= skip/advance is real (any button) =================
        m.set_input(m.BTN_START, 2)
        m.run_frames(1)
        m.pause()
        got_b = wait_for_page(m, ENDING_ROW_LINE1, ENDING_ROW_LINE2, EXPECT_B1, EXPECT_B2)
        r.check('any-button skip (matching real playgif()\'s own FLAG_ANYBUTTON '
                'behavior) advances page A -> page B (credits), real text in VRAM',
                got_b)

        m.set_input(m.BTN_START, 2)
        m.run_frames(1)
        m.pause()
        got_c = wait_for_page(m, ENDING_ROW_LINE1, ENDING_ROW_LINE2, EXPECT_C1, EXPECT_C2)
        r.check('any-button skip advances page B -> page C (thanks), real text in VRAM',
                got_c)

        # ================= completion returns cleanly to title =================
        m.set_input(m.BTN_START, 2)
        found_title = False
        for _ in range(120):
            m.run_frames(1)
            m.pause()
            if u16(m, GAME_STATE) == GAME_STATE_TITLE:
                found_title = True
                break
        r.check('page C skip returns to GAME_STATE_TITLE (real completion -> title '
                'transition, not a stuck/looping ending)', found_title)

        r.check('title row(s) are clean of leftover ending text (both ending rows '
                'blanked before the return)',
                decode_row(m, ENDING_ROW_LINE1) == EXPECT_BLANK
                and decode_row(m, ENDING_ROW_LINE2) == EXPECT_BLANK)

        r.check('Ending_Step self-reset back to page A\'s own first step for the '
                'next real ENDING entry (same discipline as Title_Step)',
                u8(m, Ending_Step) == 0)

        # ================= state-reset audit: drive a real new game =================
        # Corrupt Game_Score/Game_StageIndex/Game_Lives to values that could
        # never legitimately survive into a fresh game, exactly the "stale
        # state leaks into a new game" failure G10's own reset audit exists
        # to catch -- if Game_State_NewGameReset is missing/broken, these
        # poisoned values would still be here after CHARSELECT->PLAYING.
        m.write_u16(Game_Score, 12345)
        m.write_memory('snesMemory', Game_Lives, '01')

        # TITLE -> CHARSELECT (real Start press, same technique
        # game_g5_menus.py already uses). Poll for Title_Step==WAIT first --
        # Input_trigger is edge-triggered (real per-frame "newly pressed"
        # detection, core/input.pasm), so pressing Start while the title's
        # own draw drip hasn't reached its WAIT step yet (it only checks
        # Input_trigger there) can miss the single-frame edge entirely if
        # the whole set_input hold window elapses before WAIT is reached --
        # real live-debugging finding this gate hit directly (the ending
        # sequence's own return to TITLE lands mid-drip, unlike game_g5_
        # menus.py's own reference sequence, which forces GAME_STATE_TITLE
        # directly from a settled boot state with no drip in flight yet).
        for _ in range(30):
            if u8(m, Title_Step) == TITLE_STEP_WAIT:
                break
            m.run_frames(1)
            m.pause()
        exact_input_edge(m, m.BTN_START, 1)
        m.run_frames(60)
        m.pause()
        m.run_frames(30)
        m.pause()
        exact_input_edge(m, m.BTN_START, 1)
        for _ in range(120):
            if u16(m, GAME_STATE) == GAME_STATE_PLAYING:
                break
            m.run_frames(1)
            m.pause()
        # The exact frame that leaves CHARSELECT is the reset boundary: the
        # reset routine has completed and written fresh session state, while
        # no later PLAYING frame has yet had a chance to collect 1AEASY's
        # trigger-0 1UP.
        reset_boundary = {'score': u16(m, Game_Score),
                          'lives': u8(m, Game_Lives),
                          'stage': u16(m, Game_StageIndex),
                          'state': u16(m, GAME_STATE)}
        m.run_frames(60)
        m.pause()
        new_state = u16(m, GAME_STATE)
        r.check(f'a real TITLE->CHARSELECT->PLAYING run reaches GAME_STATE_PLAYING '
                f'(got {new_state})', new_state == GAME_STATE_PLAYING)
        r.check(f'Game_Score reset to 0 for the new game (was poisoned to 12345), '
                f'got {u16(m, Game_Score)}', u16(m, Game_Score) == 0)
        r.check(f'Game_StageIndex reset to 0 for the new game, got {u16(m, Game_StageIndex)}',
                u16(m, Game_StageIndex) == 0)
        r.check(f'NewGameReset boundary lives={GAME_LIVES_START} (got {reset_boundary["lives"]})',
                reset_boundary['lives'] == GAME_LIVES_START)
        r.check(f'NewGameReset boundary score/stage/state are fresh ({reset_boundary})',
                reset_boundary['score'] == 0 and reset_boundary['stage'] == 0 and
                reset_boundary['state'] == GAME_STATE_PLAYING)
        r.check(f'1AEASY first gameplay window preserves legitimate pickup behavior '
                f'(late lives={u8(m, Game_Lives)})', u8(m, Game_Lives) >= GAME_LIVES_START)

    r.finish()


if __name__ == '__main__':
    main()
