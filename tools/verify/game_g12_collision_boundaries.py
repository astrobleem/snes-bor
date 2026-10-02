#!/usr/bin/env python3
"""G12 focused regression: symmetric player-to-actor hitbox boundaries.

This is deliberately a production attack-path test, not a direct call into
the native helper.  It positions the player and one live target, throws one
ordinary RALF attack, and observes the target's real HP and hit-stun fields.
The same cases run against the original slot 1 and the added slot 4.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, pasm_constant_in,
                      read_block, Reporter, run_frames_exact)  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_HIT_APPLIED = pasm_constant('CHAR_HIT_APPLIED')
CHAR_GRAB_TARGET = pasm_constant('CHAR_GRAB_TARGET')
CHAR_GRABBED_BY = pasm_constant('CHAR_GRABBED_BY')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_HITBOX_W = pasm_constant('CHAR_HITBOX_W')
CHAR_HITBOX_H = pasm_constant('CHAR_HITBOX_H')
CHAR_HP_PER_HIT = pasm_constant('CHAR_HP_PER_HIT')

GS_PATH = 'src/core/game_state.pasm'
Entity1_Invuln = pasm_constant_in(GS_PATH, 'Entity1_InvulnFrames')
Entity4_Invuln = pasm_constant_in(GS_PATH, 'Entity4_InvulnFrames')

BASE = 0x7E0A00
PLAYER = BASE
TARGETS = {1: BASE + CHAR_ZP_LEN, 4: BASE + CHAR_ZP_LEN * 4}
INVULN = {1: Entity1_Invuln, 4: Entity4_Invuln}


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def prepare_case(m, target_slot, dx, dy):
    """Freeze geometry and leave only the requested target alive."""
    target = TARGETS[target_slot]
    px = 400
    py = 100
    m.write_u16(PLAYER + CHAR_POS_X, px)
    m.write_u8(PLAYER + CHAR_POS_Y, py)
    m.write_u8(PLAYER + CHAR_SELECTED, 0)
    m.write_u8(PLAYER + CHAR_HIT_APPLIED, 0)
    m.write_u8(PLAYER + CHAR_HIT_STUN, 0)
    m.write_u8(PLAYER + CHAR_GRAB_TARGET, 0xFF)

    for slot, base in enumerate(BASE + i * CHAR_ZP_LEN for i in range(6)):
        if slot == 0:
            continue
        m.write_u8(base + CHAR_HP, CHAR_HP_MAX if slot == target_slot else 0)
        m.write_u8(base + CHAR_SELECTED, 0)
        m.write_u8(base + CHAR_HIT_STUN, 0)
        m.write_u8(base + CHAR_GRABBED_BY, 0xFF)
        # Freeze movement dispatch so the position-controlled geometry remains
        # the geometry observed by the real attack/collision path.  This does
        # not bypass collision: the target remains a live CharacterEntity with
        # production HP, hit-stun, and indexed target storage.
        m.write_u8(base + CHAR_INPUT_DRIVEN, 0)
    m.write_u8(INVULN[target_slot], 0)
    m.write_u16(target + CHAR_POS_X, (px + dx) & 0xFFFF)
    m.write_u8(target + CHAR_POS_Y, (py + dy) & 0xFF)
    # Give the frame boundary a chance to commit all setup writes before the
    # button edge.  No directional input is ever held by this fixture.
    run_frames_exact(m, 2)
    m.pause()


def throw_and_observe(m, target_slot):
    target = TARGETS[target_slot]
    hp_before = u8(m, target + CHAR_HP)
    m.set_input(m.BTN_Y, 1)  # one edge; established gates use this live path
    samples = []
    for _ in range(90):
        # The established collision gates use the Mesen frame runner directly
        # for this polling loop; the input edge above is the exact delivery
        # boundary.  A pause-boundary poll can report an adjacent frame when
        # wrapped in run_frames_exact, which is unrelated to the hit result.
        m.run_frames(1)
        m.pause()
        hp = u8(m, target + CHAR_HP)
        stun = u8(m, target + CHAR_HIT_STUN)
        samples.append((hp, stun))
        if hp != hp_before:
            break
    return hp_before, samples[-1], samples


def run_case(m, r, target_slot, label, dx, dy, should_hit):
    prepare_case(m, target_slot, dx, dy)
    hp_before, (hp_after, stun_after), samples = throw_and_observe(m, target_slot)
    hit = hp_after == hp_before - CHAR_HP_PER_HIT and stun_after > 0
    unchanged = all(hp == hp_before and stun == 0 for hp, stun in samples)
    print(f'slot{target_slot} {label}: dx={dx} dy={dy} '
          f'hp={hp_before}->{hp_after} stun={stun_after}')
    r.check(f'slot {target_slot} {label}: ' +
            ('strict overlap applies damage and hit-stun' if should_hit
             else 'outside boundary applies no damage or hit-stun'),
            hit if should_hit else unchanged)


def main():
    r = Reporter('G12-COLLISION-BOUNDARIES', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()
        for target_slot in (1, 4):
            # Vertical symmetry: player above and below, then just inside,
            # exactly at, and just outside the strict height threshold.
            run_case(m, r, target_slot, 'vertical above inside', 0, CHAR_HITBOX_H - 1, True)
            run_case(m, r, target_slot, 'vertical below inside', 0, -(CHAR_HITBOX_H - 1), True)
            run_case(m, r, target_slot, 'vertical above exact edge', 0, CHAR_HITBOX_H, False)
            run_case(m, r, target_slot, 'vertical below exact edge', 0, -CHAR_HITBOX_H, False)
            run_case(m, r, target_slot, 'vertical above outside', 0, CHAR_HITBOX_H + 1, False)
            run_case(m, r, target_slot, 'vertical below outside', 0, -(CHAR_HITBOX_H + 1), False)
            # Horizontal symmetry, holding Y overlap at zero.
            run_case(m, r, target_slot, 'horizontal right inside', CHAR_HITBOX_W - 1, 0, True)
            run_case(m, r, target_slot, 'horizontal left inside', -(CHAR_HITBOX_W - 1), 0, True)
            run_case(m, r, target_slot, 'horizontal right exact edge', CHAR_HITBOX_W, 0, False)
            run_case(m, r, target_slot, 'horizontal left exact edge', -CHAR_HITBOX_W, 0, False)
            run_case(m, r, target_slot, 'horizontal right outside', CHAR_HITBOX_W + 1, 0, False)
            run_case(m, r, target_slot, 'horizontal left outside', -(CHAR_HITBOX_W + 1), 0, False)
    r.finish()


if __name__ == '__main__':
    main()
