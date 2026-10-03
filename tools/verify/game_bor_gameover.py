#!/usr/bin/env python3
"""P1-L4 source game-over and title-return gate.

This gate uses the real startup/session path, then establishes bounded
post-death fixtures to isolate the terminal lifecycle.  It does not use the
retired GAMEOVER continue restoration path.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, exact_input_edge, open_session,
                      pasm_constant, pasm_constant_in, read_block,
                      run_frames_exact, poll_until)
from game_bor_startup_select import cold_to_title, select_case

STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAMEOVER = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_GAMEOVER')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
LIVES = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')
P2_LIVES = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Lives')
CREDITS = pasm_constant_in('src/core/game_state.pasm', 'Game_Credits')
TIMER = pasm_constant_in('src/core/game_state.pasm', 'GameOver_ContinueTimer')
P1_OUT = pasm_constant_in('src/main.pasm', 'G13_P1Out')
P2_OUT = pasm_constant_in('src/main.pasm', 'G13_P2Out')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
GRACE = pasm_constant_in('src/core/game_state.pasm', 'BOR_ALL_OUT_GRACE_FRAMES')
SHORT_GRACE = pasm_constant_in('src/core/game_state.pasm', 'BOR_NO_CREDIT_GRACE_FRAMES')
DISPLAY = pasm_constant_in('src/core/game_state.pasm', 'BOR_GAME_OVER_DISPLAY_FRAMES')

P1 = 0x7E0A00
P2 = P1 + CHAR_ZP_LEN


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def start_2p(m, r):
    cold_to_title(m, r)
    select_case(m, r, 'KULA', 'MIGHTY')
    r.check('2P fixture is PLAYING', u16(m, STATE) == PLAYING)


def set_out(m, p1=True, p2=True, credits=4):
    m.write_u8(CREDITS, credits)
    m.write_u8(P1_OUT, 1 if p1 else 0)
    m.write_u8(P2_OUT, 1 if p2 else 0)
    m.write_u8(P1 + CHAR_HP, 0 if p1 else CHAR_HP_MAX)
    m.write_u8(P2 + CHAR_HP, 0 if p2 else CHAR_HP_MAX)
    m.write_u16(LIVES, 0 if p1 else 3)
    m.write_u16(P2_LIVES, 0 if p2 else 3)
    m.write_u8(TIMER, 0)


def main():
    r = Reporter('BOR-GAMEOVER', kind='GATE')

    with open_session(__file__) as m:
        m.reset_emulator()
        cold_to_title(m, r)
        select_case(m, r, 'KULA', 'MIGHTY')
        p2_lives = u16(m, P2_LIVES)
        set_out(m, p1=True, p2=False, credits=4)
        run_frames_exact(m, 3)
        r.check('P1 OUT with active P2 does not GAME OVER',
                u16(m, STATE) == PLAYING and u8(m, P2_OUT) == 0 and
                u8(m, TIMER) == 0 and u16(m, P2_LIVES) == p2_lives)

    with open_session(__file__) as m:
        m.reset_emulator()
        start_2p(m, r)
        set_out(m, p1=True, p2=True, credits=4)
        run_frames_exact(m, 3)
        armed = (u16(m, STATE), u16(m, TIMER), u8(m, CREDITS))
        print('both OUT, credits remain:', armed, flush=True)
        r.check('both OUT opens source re-entry window',
                armed[0] == PLAYING and 0 < armed[1] <= GRACE and
                armed[2] == 4)
        run_frames_exact(m, 2)
        r.check('both OUT remains nonterminal before grace expiry',
                u16(m, STATE) == PLAYING and u8(m, P1_OUT) == 1 and
                u8(m, P2_OUT) == 1)
        m.set_input(m.BTN_START, 1, port=0)
        run_frames_exact(m, 1)
        joined = (u16(m, STATE), u8(m, P1_OUT), u8(m, P1 + CHAR_HP),
                  u16(m, LIVES), u8(m, CREDITS), u8(m, P2_OUT), u8(m, TIMER))
        print('P1 re-entry before terminal:', joined, flush=True)
        r.check('eligible Start prevents premature GAME OVER',
                joined == (PLAYING, 0, CHAR_HP_MAX, 3, 3, 1, 0))

    with open_session(__file__) as m:
        m.reset_emulator()
        start_2p(m, r)
        set_out(m, p1=True, p2=True, credits=0)
        run_frames_exact(m, 3)
        r.check('no-credit both OUT uses short source grace',
                u16(m, STATE) == PLAYING and 0 < u16(m, TIMER) <= SHORT_GRACE)
        r.check('short source grace expires into GAME OVER',
                poll_until(m, lambda s: u16(s, STATE) == GAMEOVER, 60))
        gameover = (u16(m, STATE), u16(m, TIMER), u8(m, CREDITS),
                    u8(m, P1_OUT), u8(m, P2_OUT))
        print('terminal GAME OVER:', gameover, flush=True)
        r.check('exact terminal condition enters GAME OVER once',
                gameover[0] == GAMEOVER and
                DISPLAY - 2 <= gameover[1] <= DISPLAY and
                gameover[2:] == (0, 1, 1))
        run_frames_exact(m, 2)
        r.check('GAME OVER freezes gameplay without countdown restore',
                u16(m, STATE) == GAMEOVER and u8(m, CREDITS) == 0 and
                u8(m, P1_OUT) == 1 and u8(m, P2_OUT) == 1)
        m.set_input(m.BTN_START, 1, port=0)
        run_frames_exact(m, 1)
        r.check('GAME OVER Start returns to TITLE', u16(m, STATE) == TITLE)

    with open_session(__file__) as m:
        m.reset_emulator()
        cold_to_title(m, r)
        select_case(m, r, 'KULA')
        r.check('next new run resets source stock and credits',
                u16(m, LIVES) == 3 and u8(m, CREDITS) == 4)

    r.finish()


if __name__ == '__main__':
    main()
