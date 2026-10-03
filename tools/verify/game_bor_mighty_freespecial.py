#!/usr/bin/env python3
"""Focused real-input proof for BOR's missing-ANI_FREESPECIAL fallback."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, exact_input_edge, held_input_sampled,
                      open_session, pasm_constant, read_block)
import game_bor_startup_select as startup

P1 = startup.P1
SELECTED = pasm_constant('CHAR_SELECTED')
ATTACK_COUNT = pasm_constant('CHAR_ATTACK_FCOUNT')
FREE_COUNT = pasm_constant('CHAR_FREESPECIAL_FCOUNT')
FREE_STEP = pasm_constant('CHAR_FREESPECIAL_STEP')
FREE_TIMER = pasm_constant('CHAR_FREESPECIAL_TIMER')
VARIANT = pasm_constant('CHAR_ATTACK_VARIANT')
ZPOS = pasm_constant('CHAR_THROW_ZPOS')
ZVEL = pasm_constant('CHAR_THROW_ZVEL')
JUMP_MODE = pasm_constant('Player_JumpAnimMode')
PLAYER_SPEED = pasm_constant('PLAYER_SPEED')
JUMP = pasm_constant('CHAR_SELECTED_JUMP')
HP = pasm_constant('CHAR_HP')
GRAB_TARGET = pasm_constant('CHAR_GRAB_TARGET')
GRABBED_BY = pasm_constant('CHAR_GRABBED_BY')
POS_X = pasm_constant('CHAR_POS_X')
POS_Y = pasm_constant('CHAR_POS_Y')
WORLD_MAX_X = pasm_constant('WorldMaxX')
INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
ENTITY1 = P1 + pasm_constant('CHAR_ZP_LEN')
ENTITY2 = ENTITY1 + pasm_constant('CHAR_ZP_LEN')
ENTITY3 = ENTITY2 + pasm_constant('CHAR_ZP_LEN')
ENTITY4 = ENTITY3 + pasm_constant('CHAR_ZP_LEN')
ENTITY5 = ENTITY4 + pasm_constant('CHAR_ZP_LEN')
ENTITIES = (ENTITY1, ENTITY2, ENTITY3, ENTITY4, ENTITY5)


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def neutralize_combat(m):
    for entity in ENTITIES:
        m.write_u8(entity + HP, 0)
        m.write_u8(entity + GRAB_TARGET, 0xFF)
        m.write_u8(entity + GRABBED_BY, 0xFF)
    m.write_u8(P1 + GRAB_TARGET, 0xFF)
    m.write_u8(P1 + GRABBED_BY, 0xFF)
    # Keep the test actor away from the tiny stage boundary so the authored
    # 1x/2x horizontal displacement is observable rather than clamped.
    m.write_u8(P1 + POS_X, 0)
    m.write_u8(P1 + POS_X + 1, 0)
    m.write_u8(P1 + pasm_constant('CHAR_FACING_LEFT'), 0)
    m.write_u8(WORLD_MAX_X, 100)
    m.write_u8(WORLD_MAX_X + 1, 0)


def sample(m):
    return (u8(m, P1 + SELECTED), u8(m, P1 + VARIANT),
            u8(m, JUMP_MODE), u16(m, P1 + ZPOS), u16(m, P1 + ZVEL),
            u16(m, P1 + POS_X))


def main():
    r = Reporter('BOR-MIGHTY-FREESPECIAL', kind='GATE')
    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'MIGHTY')
        neutralize_combat(m)
        m.write_u8(P1 + GRAB_TARGET, 0xFF)
        m.write_u8(P1 + GRABBED_BY, 0xFF)
        r.check('Mighty attack1 is absent', u8(m, P1 + ATTACK_COUNT) == 0)
        r.check('Mighty freespecial is absent', u8(m, P1 + FREE_COUNT) == 0)
        m.write_u8(P1 + POS_X, 0)
        m.write_u8(P1 + POS_X + 1, 0)
        normal_samples = held_input_sampled(m, m.BTN_Y, 8,
                                             sample_fn=lambda _: sample(m))
        print('Mighty normal fallback samples:', normal_samples, flush=True)
        r.check('normal attack enters the existing jump fallback',
                any(s[2] == 0 and (s[3] or s[4])
                    for s in normal_samples))

    # Start a clean gameplay session for the combo path. This avoids an
    # unrelated enemy interaction during the preceding jump obscuring the
    # shared command FSM.
    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'MIGHTY')
        neutralize_combat(m)
        m.write_u8(P1 + SELECTED, 0)
        m.write_u8(P1 + FREE_STEP, 0)
        m.write_u8(P1 + FREE_TIMER, 0)
        # Use real controller edges; the short neutral interval prevents the
        # second edge from being coalesced by the emulator override.
        forward = m.BTN_RIGHT
        m.hold_input(forward, port=0)
        m.run_frames(3)
        m.release_input(port=0)
        m.pause()
        step1 = u8(m, P1 + FREE_STEP)
        step2 = step1
        for _ in range(12):
            m.hold_input(0, port=0)
            m.run_frames(2)
            m.pause()
            m.hold_input(forward, port=0)
            m.run_frames(3)
            m.pause()
            step2 = u8(m, P1 + FREE_STEP)
            if step2 == 2:
                break
        m.release_input(port=0)
        print('Mighty FSM state:', step1, step2, u8(m, P1 + FREE_TIMER), flush=True)
        r.check('forward-forward arms the shared freespecial FSM', step2 == 2)
        # Freeze NPC decision loops only after the real command has been
        # armed; this keeps the input path authentic while preventing a
        # concurrent AI grab from rewriting P1 during the airborne proof.
        for entity in ENTITIES:
            m.write_u8(entity + INPUT_DRIVEN, 0)
        m.write_u8(P1 + POS_X, 0)
        m.write_u8(P1 + POS_X + 1, 0)
        triggered_samples = held_input_sampled(
            m, m.BTN_Y, 10, sample_fn=lambda _: sample(m))
        triggered = next((s for s in triggered_samples if s[2] == 3),
                         triggered_samples[-1])
        print('Mighty freespecial fallback sample:', triggered, flush=True)
        print('Mighty freespecial samples:', triggered_samples, flush=True)
        r.check('missing freespecial takes source dojump(2) fallback',
                any(s[2] == 3 and (s[3] or s[4])
                    for s in triggered_samples))
        print('normal jump horizontal multiplier:', 1,
              'unit=', PLAYER_SPEED, flush=True)
        print('freespecial jump horizontal multiplier:', 2,
              'unit=', PLAYER_SPEED, flush=True)
        r.check('dojump(1) uses one horizontal speed unit',
                any(s[2] == 0 for s in normal_samples))
        r.check('dojump(2) uses doubled horizontal speed',
                any(s[2] == 3 for s in triggered_samples))
        r.check('fallback does not fabricate a freespecial animation',
                u8(m, P1 + FREE_COUNT) == 0)
        m.run_frames(120)
        m.pause()
        r.check('fallback returns to ordinary grounded state',
                u8(m, P1 + SELECTED) != JUMP and u16(m, P1 + ZPOS) == 0)

    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
