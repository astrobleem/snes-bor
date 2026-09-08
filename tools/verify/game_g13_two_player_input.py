#!/usr/bin/env python3
"""Focused G13 input-context localization gate.

The action-localization cases use a direct-state fixture: ``select_two_player``
establishes P2 ownership and PLAYING directly so the gate isolates actor input
ownership from stage spawning and combat traffic.  This does not claim the
production title-screen activation path; that path is covered separately by
``game_g13_p2_session.py``.  No player action result is forced: positions and
neutral state are setup, while movement and attack edges come from hardware
input contexts.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (exact_input_edge, open_session, pasm_constant,
                      pasm_constant_in, read_block, run_frames_exact,
                      Reporter)  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ZP = pasm_constant('CHAR_ZP_LEN')
POS_X = pasm_constant('CHAR_POS_X')
POS_Y = pasm_constant('CHAR_POS_Y')
SELECTED = pasm_constant('CHAR_SELECTED')
HITSTUN = pasm_constant('CHAR_HIT_STUN')
HP = pasm_constant('CHAR_HP')
INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
TITLE_STEP = pasm_constant_in('src/core/game_state.pasm', 'Title_Step')
GAME_STATE_TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE_STEP_WAIT = pasm_constant_in('src/core/game_state.pasm', 'TITLE_STEP_WAIT')
P2_MODE = pasm_constant('G13_TwoPlayerEnabled')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')

P1 = 0x7E0A00
P2 = P1 + ZP
NPC2 = P1 + 2 * ZP


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def select_two_player(m):
    # The production title-screen mode edge is covered independently by
    # game_g13_p2_session.py.  This gate starts at that ownership boundary so
    # stale Start state from setup cannot contaminate actor-context checks.
    m.write_u8(P2_MODE, 1)
    m.write_u8(P2 + INPUT_DRIVEN, 1)
    m.write_u8(P2 + HP, CHAR_HP_MAX)
    m.write_u16(GAME_STATE, GAME_STATE_PLAYING)
    m.write_u16(GAME_STATE + 2, GAME_STATE_PLAYING)
    run_frames_exact(m, 2)


def neutral_players(m):
    # The six-actor engine owns NPC slots 2-5.  Neutralize every NPC slot so
    # input/ownership tests cannot be contaminated by later spawn or combat
    # service traffic; P1/P2 ownership fields remain untouched.
    m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
    for b, x in ((P1, 120), (P2, 180)):
        m.write_u16(b + POS_X, x)
        m.write_u8(b + POS_Y, 150)
        m.write_u8(b + SELECTED, 0)
        m.write_u8(b + HITSTUN, 0)
        m.write_u8(b + HP, CHAR_HP_MAX)
    for slot in range(2, 6):
        npc = P1 + slot * ZP
        m.write_u8(npc + HP, 0)
        m.write_u8(npc + SELECTED, 0)
        m.write_u8(npc + HITSTUN, 0)


def movement_delta(m, p1_buttons, p2_buttons, frames=12):
    clear_inputs(m) if 'clear_inputs' in globals() else None
    neutral_players(m)
    x0 = (u16(m, P1 + POS_X), u16(m, P2 + POS_X))
    m.hold_input(p1_buttons, port=0)
    m.hold_input(p2_buttons, port=1)
    try:
        run_frames_exact(m, frames)
    finally:
        m.release_input(port=0)
        m.release_input(port=1)
    x1 = (u16(m, P1 + POS_X), u16(m, P2 + POS_X))
    return x0, x1


def clear_inputs(m):
    # The edge detector needs a real neutral poll between independent action
    # cases; this is a test-input boundary, not a longer gameplay pulse.
    exact_input_edge(m, 0, 2, port=0)
    exact_input_edge(m, 0, 2, port=1)


def sampled_edge(m, buttons, port, sample):
    """Deliver one edge across a bounded complete actor-service window.

    A fixture write can leave the emulator before the next input poll.  The
    semantic-boundary gate separately proves the stronger Core_Oop_Play end.
    """
    m.hold_input(buttons, port=port)
    try:
        result = run_frames_exact(m, 3)
        return result, sample()
    finally:
        m.release_input(port=port)


def sampled_simultaneous(m, buttons0, buttons1, sample):
    """Deliver one synchronized edge across a bounded actor-service window."""
    m.hold_input(buttons0, port=0)
    m.hold_input(buttons1, port=1)
    try:
        result = run_frames_exact(m, 3)
        return result, sample()
    finally:
        m.release_input(port=0)
        m.release_input(port=1)


def neutral_joint(m):
    """Converge both complete input contexts to neutral, bounded."""
    m.hold_input(0, port=0)
    m.hold_input(0, port=1)
    try:
        state = None
        for _ in range(6):
            run_frames_exact(m, 1)
            state = (read_block(m, 0x7E0410, 32)[:6].hex(),
                     read_block(m, 0x7E0416, 32)[:6].hex())
            if state == ('000000000000', '000000000000'):
                return state
        raise AssertionError(f'neutral_joint did not converge: {state}')
    finally:
        m.release_input(port=0)
        m.release_input(port=1)


def prepare_session(m):
    m.reset_emulator()
    run_frames_exact(m, 180)
    m.set_input(m.BTN_SELECT, 10)
    run_frames_exact(m, 40)
    select_two_player(m)


def action_case(port, buttons):
    """Run one action-edge case in its own clean emulator session."""
    with open_session(__file__) as m:
        prepare_session(m)
        clear_inputs(m)
        neutral_players(m)
        _, sample = sampled_edge(
            m, buttons, port=port,
            sample=lambda: (u8(m, P1 + SELECTED), u8(m, P2 + SELECTED),
                            read_block(m, 0x7E0410, 32)[:6].hex(),
                            read_block(m, 0x7E0416, 32)[:6].hex()))
        return sample


def simultaneous_action_case():
    with open_session(__file__) as m:
        prepare_session(m)
        neutral_joint(m)
        neutral_players(m)
        _, sample = sampled_simultaneous(
            m, m.BTN_Y, m.BTN_Y,
            sample=lambda: (u8(m, P1 + SELECTED), u8(m, P2 + SELECTED),
                            read_block(m, 0x7E0410, 32)[:6].hex(),
                            read_block(m, 0x7E0416, 32)[:6].hex(),
                            read_block(m, 0x7E041C, 32)[:4].hex()))
        return sample


def main():
    r = Reporter('G13-TWO-PLAYER-INPUT', kind='GATE')
    with open_session(__file__) as m:
        def prepare():
            m.reset_emulator()
            run_frames_exact(m, 180)
            # Match the established controller-delivery warm-up used by the
            # accepted JOY1/JOY2 boundary gate.
            m.set_input(m.BTN_SELECT, 10)
            run_frames_exact(m, 40)
            select_two_player(m)

        prepare()
        print('P2_PLAY_SETUP', {
            'state': u8(m, GAME_STATE),
            'mode': u8(m, P2_MODE),
            'p1_role': u8(m, P1 + INPUT_DRIVEN),
            'p2_role': u8(m, P2 + INPUT_DRIVEN),
            'p1_loaded': read_block(m, 0x7E53B8, 32)[0],
            'nmi': u16(m, 0x7E5023),
        })

        x0, x1 = movement_delta(m, m.BTN_LEFT, 0)
        print('P1_LEFT_ONLY', x0, x1)
        r.check('P1 Left moves only P1', x1[0] < x0[0] and x1[1] == x0[1])
        prepare()

        x0, x1 = movement_delta(m, 0, m.BTN_RIGHT)
        print('P2_RIGHT_ONLY', x0, x1)
        r.check('P2 Right moves only P2', x1[0] == x0[0] and x1[1] > x0[1])
        prepare()

        x0, x1 = movement_delta(m, m.BTN_LEFT, m.BTN_RIGHT)
        print('OPPOSITE_SIMULTANEOUS', x0, x1)
        r.check('simultaneous contrary directions remain independent',
                x1[0] < x0[0] and x1[1] > x0[1])
        prepare()

        p1_sample = action_case(0, m.BTN_Y)
        p1_attack, p2_attack, p1_in, p2_in = p1_sample
        print('P1_ATTACK_ONLY', p1_attack, p2_attack, p1_in, p2_in)
        r.check('P1 attack edge reaches only P1', p1_attack == 2 and p2_attack != 2)
        # LEO is a chain-bearing roster entry.  Its production attack path
        # consumes Y through Jump_AtchainTrigger; X is the separate attack2
        # route and is intentionally unavailable when ATTACK2_FCOUNT==0.
        p2_sample = action_case(1, m.BTN_Y)
        p1_attack, p2_attack, p1_in, p2_in = p2_sample
        print('P2_ATTACK_ONLY', p1_attack, p2_attack,
              'p1ctx', p1_in, 'p2ctx', p2_in,
              'raws', 'captured-in-action-case')
        r.check('P2 attack edge reaches only P2', p2_attack == 2 and p1_attack != 2)
        simultaneous_sample = simultaneous_action_case()
        print('SIMULTANEOUS_ATTACK', simultaneous_sample,
              'bounded post-service control; semantic proof is game_g13_semantic_boundary.py')
        r.check('simultaneous distinct attack edges remain distinct',
                simultaneous_sample[0] == 2 and simultaneous_sample[1] == 2)

    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
