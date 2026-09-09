#!/usr/bin/env python3
"""G14 bounded player-facing two-player presentation gate.

The accepted G13 session model remains fixed-session: JOY2 selects 2P before
character select and slot 1 is explicitly loaded as LEO.  This gate proves
that presentation policy and the independent P2 HUD state are live without
altering production WRAM during a running frame.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, exact_input_edge, open_session,
                      pasm_constant, pasm_constant_in, read_block,
                      run_frames_exact)  # noqa: E402

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
GAME_STATE_CHARSELECT = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_CHARSELECT')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE_STEP = pasm_constant_in('src/core/game_state.pasm', 'Title_Step')
MODE = pasm_constant('G13_TwoPlayerEnabled')
P2_SCORE = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Score')
P2_LIVES = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Lives')
P2_OUT = pasm_constant('G13_P2Out')
PLAYER_BASE = 0x7E0A00
P2_BASE = PLAYER_BASE + pasm_constant('CHAR_ZP_LEN')
P2_HP = P2_BASE + pasm_constant('CHAR_HP')
P1_HP = PLAYER_BASE + pasm_constant('CHAR_HP')
P1_SCORE = pasm_constant_in('src/core/game_state.pasm', 'Game_Score')
P1_LIVES = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')
ZP_LEN = pasm_constant('CHAR_ZP_LEN')
ROSTER_INDEX = pasm_constant('CHAR_ROSTER_INDEX')
HUD_P2_HP = pasm_constant('HudCachedP2Hp')
HUD_P2_SCORE = pasm_constant('HudCachedP2Score')
HUD_P2_LIVES = pasm_constant('HudCachedP2Lives')
HUD_P1_HP = pasm_constant('HudCachedHp')
HUD_P1_SCORE = pasm_constant('HudCachedScore')
HUD_P1_LIVES = pasm_constant('HudCachedLives')


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def main():
    r = Reporter('G14', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        run_frames_exact(m, 180)
        m.pause()

        m.write_u16(GAME_STATE, GAME_STATE_TITLE)
        m.write_u8(TITLE_STEP, 2)
        run_frames_exact(m, 2)

        # JOY2 chooses the fixed two-player session before P1's character
        # select Start edge.  Both edges are delivered between frame polls.
        exact_input_edge(m, m.BTN_START, 1, port=1)
        run_frames_exact(m, 2)
        r.check('title JOY2 Start enables 2P session', u8(m, MODE) == 1)
        r.check('2P slot 1 loads fixed LEO roster entry', u8(m, P2_BASE + ROSTER_INDEX) == 12)

        exact_input_edge(m, m.BTN_START, 1, port=0)
        run_frames_exact(m, 60)
        r.check('P1 Start enters character select', u16(m, GAME_STATE) == GAME_STATE_CHARSELECT)
        r.check('P2 remains fixed LEO in character select', u8(m, P2_BASE + ROSTER_INDEX) == 12)

        exact_input_edge(m, m.BTN_START, 1, port=0)
        run_frames_exact(m, 60)
        r.check('2P session reaches gameplay', u16(m, GAME_STATE) == GAME_STATE_PLAYING)
        r.check('P2 is not OUT at session start', u8(m, P2_OUT) == 0)

        run_frames_exact(m, 20)
        r.check('P1 HP cache follows P1 state', u8(m, HUD_P1_HP) == u8(m, P1_HP))
        r.check('P2 HP cache follows P2 state', u8(m, HUD_P2_HP) == u8(m, P2_HP))
        r.check('P1 score cache follows P1 score', u16(m, HUD_P1_SCORE) == u16(m, P1_SCORE))
        r.check('P2 score cache follows P2 score', u16(m, HUD_P2_SCORE) == u16(m, P2_SCORE))
        r.check('P1 lives cache follows P1 lives', u8(m, HUD_P1_LIVES) == u8(m, P1_LIVES))
        r.check('P2 lives cache follows P2 lives', u8(m, HUD_P2_LIVES) == u8(m, P2_LIVES))

        # Presentation-only state isolation fixture: change each owner’s
        # already-existing state between frames and verify its own cache.
        p1_score = u16(m, P1_SCORE)
        p2_score = u16(m, P2_SCORE)
        m.write_u16(P2_SCORE, p2_score + 37)
        m.write_u8(P2_HP, 32)
        run_frames_exact(m, 2)
        r.check('P2 score presentation is independent', u16(m, HUD_P2_SCORE) == p2_score + 37)
        r.check('P2 HP presentation is independent', u8(m, HUD_P2_HP) == 32)
        r.check('P1 score presentation is unchanged', u16(m, P1_SCORE) == p1_score)

    r.finish()


if __name__ == '__main__':
    main()
