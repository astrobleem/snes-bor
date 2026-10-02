#!/usr/bin/env python3
"""Source-normal Mighty missing-ANI_ATTACK1 runtime gate."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, exact_input_edge, open_session, pasm_constant,
                      held_input_sampled, read_block)
import game_bor_startup_select as startup

P1 = startup.P1
ROSTER = startup.CHAR_ROSTER_INDEX
ATTACK_COUNT = pasm_constant('CHAR_ATTACK_FCOUNT')
SELECTED = pasm_constant('CHAR_SELECTED')
POS_Y = pasm_constant('CHAR_POS_Y')
THROW_ZPOS = pasm_constant('CHAR_THROW_ZPOS')
THROW_ZVEL = pasm_constant('CHAR_THROW_ZVEL')
JUMP_SELECTED = pasm_constant('CHAR_SELECTED_JUMP')


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def run_case(r, identity, expect_fallback):
    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, identity)
        before = (u8(m, P1 + ATTACK_COUNT), u8(m, P1 + SELECTED),
                  u16(m, P1 + POS_Y), u16(m, P1 + THROW_ZPOS),
                  u16(m, P1 + THROW_ZVEL))
        samples = held_input_sampled(m, m.BTN_Y, 3, port=0,
                                     sample_fn=lambda _: (
                                         u8(m, P1 + ATTACK_COUNT),
                                         u8(m, P1 + SELECTED),
                                         u16(m, P1 + POS_Y),
                                         u16(m, P1 + THROW_ZPOS),
                                         u16(m, P1 + THROW_ZVEL)))
        after = samples[-1]
        print(f'{identity} attack before={before} samples={samples}')
        r.check(f'{identity} remains live after attack input', u16(m, startup.STATE) == startup.PLAYING)
        r.check(f'{identity} attack count is stable', all(s[0] == (0 if expect_fallback else before[0]) for s in samples))
        if expect_fallback:
            r.check('Mighty has no attack frames', before[0] == 0 and after[0] == 0)
            r.check('Mighty enters source fallback jump', any(s[1] == JUMP_SELECTED for s in samples))
            r.check('Mighty fallback has real jump data', any(s[4] != 0 or s[3] != 0 for s in samples))
        else:
            r.check('Kula uses real attack1', before[0] != 0 and any(s[1] != JUMP_SELECTED for s in samples))


def main():
    r = Reporter('BOR-MIGHTY', kind='GATE')
    for _ in range(3):
        run_case(r, 'MIGHTY', True)
    for _ in range(3):
        run_case(r, 'KULA', False)
    r.finish()


if __name__ == '__main__':
    main()
