#!/usr/bin/env python3
"""P1-L1: source BOR stock/credit foundation.

This gate intentionally stops at initialization and persistence.  It does not
exercise the still-project-invented death, continue, rejoin, or game-over
semantics; those belong to later fidelity slices.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, open_session, pasm_constant, pasm_constant_in,
                      read_block)
import game_bor_startup_select as startup
import game_g15_stage1_campaign as stage1

STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
LIVES = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')
CREDITS = pasm_constant_in('src/core/game_state.pasm', 'Game_Credits')
P2_LIVES = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Lives')
STAGE = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
GAME_LIVES_START = pasm_constant_in('src/core/game_state.pasm', 'GAME_LIVES_START')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
P1 = 0x7E0A00


def u8(m, address):
    return read_block(m, address, 32)[0]


def u16(m, address):
    b = read_block(m, address, 32)
    return b[0] | (b[1] << 8)


def main():
    r = Reporter('BOR-LIFE-CREDIT-FOUNDATION', kind='GATE')
    r.check('source stock constant is 3', GAME_LIVES_START == 3)
    r.check('one run-global credit symbol exists', CREDITS == 0x7E2694)
    r.check('P2 stock is a separate player cell', P2_LIVES != LIVES)

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        # Stage persistence is proved on the authoritative 1P progression
        # path.  The dedicated 2P lifecycle gates cover slot independence;
        # this foundation assertion must not depend on the stale 2P clear
        # fixture's development-tail handoff behavior.
        startup.select_case(m, r, 'KULA')
        # select_case uses real title/difficulty/player input and returns at
        # the PLAYING boundary.  Stage 1A's first trigger can award a real
        # 1UP on a subsequent gameplay frame, so capture before advancing it.
        r.check('new run reaches PLAYING', u16(m, STATE) == PLAYING)
        reset_sample = (u16(m, LIVES), u16(m, P2_LIVES), u8(m, CREDITS),
                        u16(m, STAGE))
        print('new-run post-reset boundary sample:', reset_sample, flush=True)
        r.check('new run credits initialized to 4', reset_sample[2] == 4)
        r.check('P1 initial stock is 3 at boundary', reset_sample[0] == 3)
        r.check('P2 initial stock is 3 at boundary', reset_sample[1] == 3)

        # Prove the two stock cells are not mirrored.  This is a bounded
        # fixture write, not a reward/death outcome and no production branch
        # is used to manufacture a pass.
        m.write_u16(LIVES, 2)
        r.check('changing P1 stock leaves P2 stock at 3',
                u16(m, LIVES) == 2 and u16(m, P2_LIVES) == 3)
        m.write_u16(LIVES, 3)

        before_stage = u8(m, CREDITS)
        # Let the real 1A frontpanel/queue settle before using the established
        # production stage-clear precondition.
        m.run_frames(60)
        m.pause()
        r.check('1A -> 1B stage transition preserves credits',
                stage1.clear_stage(m, r, 0) and
                u16(m, STAGE) == 1 and u8(m, CREDITS) == before_stage)
        r.check('credits remain one shared state, not P2 mirrored state',
                u8(m, CREDITS) == 4 and CREDITS != P2_LIVES)
    r.finish()


if __name__ == '__main__':
    main()
