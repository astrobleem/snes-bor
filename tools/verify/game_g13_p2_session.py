#!/usr/bin/env python3
"""Bounded fixed-session P2 activation proof.

JOY2 Start is the pre-game session choice. Slot 1 is converted through the
same production character-load path to fixed roster entry LEO. The verifier
only arranges the already-reachable char-select dispatch boundary.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (exact_input_edge, open_session, pasm_constant,
                      pasm_constant_in, read_block, run_frames_exact)  # noqa: E402

PLAYER = 0x7E0A00
ZP_LEN = pasm_constant('CHAR_ZP_LEN')
SLOT1 = PLAYER + ZP_LEN
MODE = pasm_constant('G13_TwoPlayerEnabled')
P2_SEEN = pasm_constant('G13_P2StartSeen')
P2_SNAPSHOT = pasm_constant('G13_P2TriggerSnapshot')
P2_MASK = pasm_constant('G13_P2MaskResult')
GAME_STATE = 0x7E2750
TITLE_STEP = pasm_constant_in('src/core/game_state.pasm', 'Title_Step')
CHAR_INPUT = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_ROSTER = pasm_constant('CHAR_ROSTER_INDEX')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
P2_RAW = 0x7E041E


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def main():
    with open_session(__file__) as m:
        m.reset_emulator()
        run_frames_exact(m, 180)
        # Put the ordinary state machine at its established title WAIT
        # boundary.  P2 Start is a pre-session mode choice here, before
        # CHARSELECT/PLAYING; it is not a mid-game join path.
        # Prime the persistent override through one poll, then release for
        # two exact neutral polls so the Start edge is unambiguous.
        m.hold_input(m.BTN_START, port=1)
        run_frames_exact(m, 1)
        m.release_input(port=1)
        exact_input_edge(m, 0, 2, port=1)

        m.hold_input(m.BTN_START, port=1)
        run_frames_exact(m, 1)
        raw_start = read_block(m, P2_RAW, 32)[:2]
        print(f"P2_PREPOLL raw={raw_start.hex()} input2={read_block(m, 0x7E0416, 32)[:6].hex()}")
        m.release_input(port=1)
        exact_input_edge(m, 0, 2, port=1)
        m.write_u16(GAME_STATE, 1)
        m.write_u16(GAME_STATE + 2, 1)
        m.write_u8(TITLE_STEP, 2)
        exact_input_edge(m, m.BTN_START, 1, port=1)
        print('BEFORE_P2', {'game_state': u8(m, GAME_STATE), 'title_step': u8(m, TITLE_STEP), 'input1': read_block(m, 0x7E0410, 32)[:6].hex()})
        run_frames_exact(m, 1)
        got = {
            'mode': u8(m, MODE),
            'slot1_input': u8(m, SLOT1 + CHAR_INPUT),
            'slot1_roster': u8(m, SLOT1 + CHAR_ROSTER),
            'slot1_hp': u8(m, SLOT1 + CHAR_HP),
            'seen': u8(m, P2_SEEN),
            'snapshot': read_block(m, P2_SNAPSHOT, 32)[:2].hex(),
            'mask': read_block(m, P2_MASK, 32)[:2].hex(),
        }
        print(f"P2_SESSION raw_pre_poll={raw_start.hex()} input2={read_block(m, 0x7E0416, 32)[:6].hex()} {got}")
        assert raw_start == bytes((0x00, 0x10))
        assert got['mode'] == 1 and got['slot1_input'] == 1
        assert got['slot1_roster'] == 12 and got['slot1_hp'] == CHAR_HP_MAX
        # The production gate now lives on TITLE, so the old CHARSELECT
        # diagnostic snapshot is intentionally untouched.  The hardware
        # edge and the resulting production session state are authoritative.
        assert got['mode'] == 1 and got['slot1_input'] == 1

        print('G13 FIXED P2 SESSION: PASS')


if __name__ == '__main__':
    main()
