#!/usr/bin/env python3
"""P1-L3 source credit-based join/re-entry gate.

This gate intentionally stops before the source both-player game-over/title
path, which is P1-L4 work.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, open_session, pasm_constant, pasm_constant_in,
                      read_block, run_frames_exact)
from game_bor_startup_select import cold_to_title, select_case

STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
PAUSED = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PAUSED')
LIVES = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')
P2_LIVES = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Lives')
CREDITS = pasm_constant_in('src/core/game_state.pasm', 'Game_Credits')
TIMER = pasm_constant_in('src/core/game_state.pasm', 'GameOver_ContinueTimer')
P1_OUT = pasm_constant_in('src/main.pasm', 'G13_P1Out')
P2_OUT = pasm_constant_in('src/main.pasm', 'G13_P2Out')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')

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
    r.check('2P re-entry fixture is PLAYING', u16(m, STATE) == PLAYING)


def main():
    r = Reporter('BOR-CREDIT-REENTRY', kind='GATE')

    # P1 can re-enter while P2 remains active.  No death/game-over machinery
    # is invoked here; OUT is the L2-established absent-player boundary.
    with open_session(__file__) as m:
        m.reset_emulator()
        start_2p(m, r)
        credits_before = u8(m, CREDITS)
        p2_lives_before = u16(m, P2_LIVES)
        m.write_u8(P1_OUT, 1)
        m.write_u8(P1 + CHAR_HP, 0)
        m.write_u16(LIVES, 0)
        run_frames_exact(m, 3)
        r.check('OUT P1 remains absent without Start',
                u8(m, P1_OUT) == 1 and u8(m, P1 + CHAR_HP) == 0)
        r.check('partner continues while P1 is absent',
                u16(m, STATE) == PLAYING and u8(m, P2 + CHAR_HP) != 0)
        r.check('no BOR continue countdown is armed',
                u8(m, TIMER) == 0 and u16(m, STATE) != PAUSED)
        m.set_input(m.BTN_START, 1, port=0)
        run_frames_exact(m, 1)
        p1_join = (u8(m, P1_OUT), u16(m, LIVES), u8(m, P1 + CHAR_HP),
                   u8(m, CREDITS), u16(m, P2_LIVES), u16(m, STATE))
        print('P1 join:', p1_join)
        r.check('P1 Start performs one credit-gated re-entry',
                p1_join[0] == 0 and p1_join[1] == 3 and
                p1_join[2] == CHAR_HP_MAX and p1_join[3] == credits_before - 1)
        r.check('P1 re-entry leaves P2 stock and gameplay intact',
                p1_join[4] == p2_lives_before and p1_join[5] == PLAYING)

    # Symmetric P2 re-entry and global credit ownership.
    with open_session(__file__) as m:
        m.reset_emulator()
        start_2p(m, r)
        credits_before = u8(m, CREDITS)
        p1_lives_before = u16(m, LIVES)
        m.write_u8(P2_OUT, 1)
        m.write_u8(P2 + CHAR_HP, 0)
        m.write_u16(P2_LIVES, 0)
        run_frames_exact(m, 2)
        m.set_input(m.BTN_START, 1, port=1)
        run_frames_exact(m, 1)
        p2_join = (u8(m, P2_OUT), u16(m, P2_LIVES), u8(m, P2 + CHAR_HP),
                   u8(m, CREDITS), u16(m, LIVES), u16(m, STATE))
        print('P2 join:', p2_join)
        r.check('P2 Start performs one credit-gated re-entry',
                p2_join[0] == 0 and p2_join[1] == 3 and
                p2_join[2] == CHAR_HP_MAX and p2_join[3] == credits_before - 1)
        r.check('P2 re-entry leaves P1 stock intact',
                p2_join[4] == p1_lives_before and p2_join[5] == PLAYING)

    # Failed join attempts do not consume credits or manufacture a player.
    with open_session(__file__) as m:
        m.reset_emulator()
        start_2p(m, r)
        m.write_u8(CREDITS, 0)
        m.write_u8(P1_OUT, 1)
        m.write_u8(P1 + CHAR_HP, 0)
        m.write_u16(LIVES, 0)
        m.set_input(m.BTN_START, 1, port=0)
        run_frames_exact(m, 1)
        r.check('zero-credit P1 Start does not restore the player',
                u8(m, P1_OUT) == 1 and u8(m, P1 + CHAR_HP) == 0 and
                u16(m, LIVES) == 0 and u8(m, CREDITS) == 0)

    # An active player's Start remains pause input, but is not a credit join.
    with open_session(__file__) as m:
        m.reset_emulator()
        start_2p(m, r)
        credits_before = u8(m, CREDITS)
        lives_before = u16(m, LIVES)
        m.set_input(m.BTN_START, 1, port=0)
        run_frames_exact(m, 1)
        r.check('active Start consumes no credit or stock',
                u8(m, CREDITS) == credits_before and
                u16(m, LIVES) == lives_before)

    r.finish()


if __name__ == '__main__':
    main()
