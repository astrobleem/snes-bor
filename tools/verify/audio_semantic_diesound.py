#!/usr/bin/env python3
"""Focused live proof of semantic diesound emission.

The harness only prepares deterministic entity state.  The request itself must
come from the real player attack -> hit dispatch -> ApplyDamage kill path.
This is deliberately narrower than the eventual streaming gate: it does not
start a playback backend or alter TAD.
"""
import argparse
import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, pasm_constant_in, read_block, exact_input_edge,
                      run_frames_exact, held_input_sampled)


def run_frames_exact(m, count):
    """Use the clean capture path; Nexen omits the frame-count response field."""
    for _ in range(count):
        m.run_frames(1)
        m.pause()

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_FALL_STATE_TIMER = pasm_constant('CHAR_FALL_STATE_TIMER')
CHAR_KNOCKDOWN_COUNT = pasm_constant('CHAR_KNOCKDOWN_COUNT')
CHAR_KNOCKDOWN_TIMER = pasm_constant('CHAR_KNOCKDOWN_TIMER')
CHAR_TICK_COUNTER = pasm_constant('CHAR_TICK_COUNTER')
CHAR_FRAME_INDEX = pasm_constant('CHAR_FRAME_INDEX')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_ROSTER_INDEX = pasm_constant('CHAR_ROSTER_INDEX')
CHAR_HIT_APPLIED = pasm_constant('CHAR_HIT_APPLIED')
CHAR_THROW_ZPOS = pasm_constant('CHAR_THROW_ZPOS')
CHAR_THROW_ZVEL = pasm_constant('CHAR_THROW_ZVEL')
CHAR_SELECTED_THROWN = pasm_constant('CHAR_SELECTED_THROWN')
JUMP_INITIAL_VEL = pasm_constant('JUMP_INITIAL_VEL')
CHAR_HP_PER_HIT = pasm_constant('CHAR_HP_PER_HIT')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
ENTITY_INVULN = [None,
                  pasm_constant_in('src/core/game_state.pasm', 'Entity1_InvulnFrames'),
                  pasm_constant_in('src/core/game_state.pasm', 'Entity2_InvulnFrames'),
                  pasm_constant_in('src/core/game_state.pasm', 'Entity3_InvulnFrames')]
SEM_NONE = pasm_constant('AUDIO_SEMANTIC_NONE')
SEM_FOOTDIE = pasm_constant('AUDIO_SEMANTIC_FOOTDIE')
SEM_ROCKDIE = pasm_constant('AUDIO_SEMANTIC_ROCKDIE')
REQ_COUNT = pasm_constant('AudioSemantic_RequestCount')
TRACE_INDEX = pasm_constant('AudioSemantic_TraceWriteIndex')
TRACE_BASE = pasm_constant('AudioSemantic_TraceBase')
TRACE_OVERFLOW = pasm_constant('AudioSemantic_TraceOverflow')
FOOT_COUNT = pasm_constant('AudioSemantic_FootDieRequestCount')
FALL_COUNT = pasm_constant('AudioSemantic_FallRequestCount')
STREAM_START_COUNT = pasm_constant('AudioSemantic_FootDieStreamStartCount')
COALESCED_COUNT = pasm_constant('AudioSemantic_FootDieSameFrameCoalescedCount')
SUPPRESSED_COUNT = pasm_constant('AudioSemantic_FootDieWhileActiveSuppressedCount')
ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
PLAYER, SLOT1, SLOT2, SLOT3 = ENTITY_BASES


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def w8(m, addr, value):
    m.write_memory('snesMemory', addr, f'{value & 0xff:02X}')


def w16(m, addr, value):
    m.write_memory('snesMemory', addr, f'{value & 0xff:02X}{(value >> 8) & 0xff:02X}')


def trace(m):
    n = u8(m, TRACE_INDEX)
    raw = read_block(m, TRACE_BASE, 128)
    rows = []
    for i in range(min(n, 16)):
        p = i * 8
        rows.append({
            'frame': raw[p] | (raw[p + 1] << 8),
            'sequence': raw[p + 2],
            'semantic_id': raw[p + 3],
            'actor_slot': raw[p + 4],
            'roster_index': raw[p + 5],
            'event_type': raw[p + 6],
        })
    return rows


def prepare_target(m, base, roster_index, hp):
    w8(m, base + CHAR_INPUT_DRIVEN, 0)  # deterministic static target setup
    w8(m, base + CHAR_ROSTER_INDEX, roster_index)
    w8(m, base + CHAR_HIT_STUN, 0)
    w16(m, base + CHAR_POS_X, u16(m, PLAYER + CHAR_POS_X))
    w16(m, base + CHAR_POS_Y, u16(m, PLAYER + CHAR_POS_Y))
    w8(m, base + CHAR_HP, hp)
    slot = ENTITY_BASES.index(base)
    w8(m, ENTITY_INVULN[slot], 0)


def boot(m):
    m.reset_emulator()
    run_frames_exact(m, 150)
    m.pause()
    for base in ENTITY_BASES[2:]:
        w8(m, base + CHAR_HP, 0)
    run_frames_exact(m, 30)
    # Establish entity fixtures only while the CPU is paused.  The accepted
    # G11 gate uses the same boundary; writing these fields while the game is
    # running lets Anim_Play/Spawn logic race the setup and can leave the
    # target out of overlap before the real attack edge is delivered.
    m.pause()


def clear_observation(m):
    w16(m, REQ_COUNT, 0)
    w8(m, TRACE_INDEX, 0)
    w8(m, TRACE_OVERFLOW, 0)
    w16(m, FOOT_COUNT, 0)
    w16(m, FALL_COUNT, 0)
    m.write_memory('snesMemory', TRACE_BASE, '00' * 128)


def kill_target(m, slot_index, roster_index):
    for i, base in enumerate(ENTITY_BASES[1:], 1):
        w8(m, base + CHAR_HP, 0 if i != slot_index else 1)
        w8(m, ENTITY_INVULN[i], 0)
        w8(m, base + CHAR_INPUT_DRIVEN, 0)
    prepare_target(m, ENTITY_BASES[slot_index], roster_index, 1)
    # AudioSemantic_EmitDiesound consumes the production mirror maintained by
    # the entity tick, not the paused test fixture's raw CHAR_ROSTER_INDEX
    # write.  Advance one real frame so the target identity is authenticated
    # before the real lethal attack edge is delivered.
    run_frames_exact(m, 1)
    m.pause()
    w8(m, PLAYER + CHAR_HIT_STUN, 0)
    w8(m, PLAYER + CHAR_HIT_APPLIED, 0)
    before = u16(m, REQ_COUNT)
    held_input_sampled(m, m.BTN_Y, 3)
    # The real attack can land after the three sampled input frames.  Keep a
    # single bounded observation window, matching the accepted G11 gate's
    # 3-frame edge plus recovery/windup window rather than treating an early
    # no-hit read as proof that the semantic path did not run.
    for _ in range(60):
        run_frames_exact(m, 1)
        m.pause()
    after = u16(m, REQ_COUNT)
    return before, after, u8(m, ENTITY_BASES[slot_index] + CHAR_HP), trace(m)


def kill_spawned_target(m, slot_index):
    """Kill a target whose production spawn path already set its identity."""
    sentinel = next(i for i in range(1, 4) if i != slot_index)
    for i, base in enumerate(ENTITY_BASES[1:], 1):
        if i != slot_index:
            w8(m, base + CHAR_HP, 0)
        w8(m, ENTITY_INVULN[i], 0)
        w8(m, base + CHAR_INPUT_DRIVEN, 0)
    # Keep the level live after the target dies.  This fixture sentinel is
    # deliberately outside the combat overlap; it prevents the normal
    # no-enemy stage transition from resetting the target before the audio
    # observation window closes.
    w8(m, ENTITY_BASES[sentinel] + CHAR_HP, CHAR_HP_MAX)
    w16(m, ENTITY_BASES[sentinel] + CHAR_POS_X, u16(m, PLAYER + CHAR_POS_X) + 200)
    w16(m, ENTITY_BASES[sentinel] + CHAR_POS_Y, u16(m, PLAYER + CHAR_POS_Y))
    target = ENTITY_BASES[slot_index]
    w8(m, target + CHAR_INPUT_DRIVEN, 0)
    w8(m, target + CHAR_HIT_STUN, 0)
    w16(m, target + CHAR_POS_X, u16(m, PLAYER + CHAR_POS_X))
    w16(m, target + CHAR_POS_Y, u16(m, PLAYER + CHAR_POS_Y))
    w8(m, target + CHAR_HP, 1)
    w8(m, PLAYER + CHAR_HIT_STUN, 0)
    w8(m, PLAYER + CHAR_HIT_APPLIED, 0)
    before = u16(m, REQ_COUNT)
    roster_samples = held_input_sampled(
        m, m.BTN_Y, 3,
        sample_fn=lambda _: {
            'roster': u8(m, target + CHAR_ROSTER_INDEX),
            'requests': u16(m, REQ_COUNT),
            'trace_index': u8(m, TRACE_INDEX),
        })
    for _ in range(60):
        run_frames_exact(m, 1)
        m.pause()
    after = u16(m, REQ_COUNT)
    return before, after, u8(m, target + CHAR_HP), trace(m), roster_samples


def fall_target(m, slot_index=1, roster_index=5):
    for i, base in enumerate(ENTITY_BASES[1:], 1):
        w8(m, base + CHAR_HP, 0 if i != slot_index else CHAR_HP_MAX)
        w8(m, ENTITY_INVULN[i], 0)
        w8(m, base + CHAR_INPUT_DRIVEN, 0)
    prepare_target(m, ENTITY_BASES[slot_index], roster_index, CHAR_HP_MAX)
    # OpenBOR emits FALL at a qualifying ground bounce, not when damage first
    # enters the knockdown state. Exercise the existing SNES equivalent:
    # ordinary thrown landing, with no safe UP+A land command.
    w8(m, ENTITY_BASES[slot_index] + CHAR_SELECTED, CHAR_SELECTED_THROWN)
    w16(m, ENTITY_BASES[slot_index] + CHAR_THROW_ZPOS, 0)
    w16(m, ENTITY_BASES[slot_index] + CHAR_THROW_ZVEL, JUMP_INITIAL_VEL)
    w8(m, ENTITY_BASES[slot_index] + CHAR_HIT_STUN, 0)
    before = u16(m, FALL_COUNT)
    for _ in range(120):
        run_frames_exact(m, 1)
        m.pause()
        if u8(m, ENTITY_BASES[slot_index] + CHAR_SELECTED) != CHAR_SELECTED_THROWN:
            break
    return before, u16(m, FALL_COUNT), trace(m)


def kill_all_targets(m):
    for base in ENTITY_BASES[1:]:
        prepare_target(m, base, 5, 1)
    w8(m, PLAYER + CHAR_HIT_APPLIED, 0)
    w8(m, PLAYER + CHAR_HIT_STUN, 0)
    before = u16(m, REQ_COUNT)
    held_input_sampled(m, m.BTN_Y, 3)
    for _ in range(60):
        run_frames_exact(m, 1)
        m.pause()
    after = u16(m, REQ_COUNT)
    return after - before, trace(m)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom-sha256', required=True)
    parser.add_argument('--fall-only', action='store_true')
    args = parser.parse_args()
    rom = Path(__file__).resolve().parents[2] / 'distribution' / 'bor.sfc'
    actual = hashlib.sha256(rom.read_bytes()).hexdigest()
    if actual != args.rom_sha256.lower():
        raise SystemExit(f'ROM SHA mismatch: expected {args.rom_sha256}, actual {actual}')

    if args.fall_only:
        with open_session(__file__) as m:
            boot(m)
            clear_observation(m)
            before, after, rows = fall_target(m)
            fall_id = pasm_constant('AUDIO_SEMANTIC_FALL')
            if after - before != 1 or not any(row['semantic_id'] == fall_id for row in rows):
                raise SystemExit(f'FAIL: ordinary thrown landing did not emit exactly one FALL request: before={before} after={after} rows={rows}')
            print(f'FALL_THROW_LANDING: request_delta={after - before} rows={rows}')
        return

    # Fresh session per case prevents prior entity teardown/reassignment from
    # contaminating provenance or the negative control.
    with open_session(__file__) as m:
        boot(m)
        clear_observation(m)
        for base in ENTITY_BASES[1:]:
            w8(m, base + CHAR_HP, CHAR_HP_MAX)
            w8(m, base + CHAR_INPUT_DRIVEN, 0)
        prepare_target(m, SLOT1, 5, CHAR_HP_MAX)
        w8(m, PLAYER + CHAR_HIT_APPLIED, 0)
        before = u16(m, REQ_COUNT)
        held_input_sampled(m, m.BTN_Y, 3)
        after = u16(m, REQ_COUNT)
        print(f'NONLETHAL_REQUEST_DELTA={after - before} HP={u8(m, SLOT1 + CHAR_HP)} TRACE={trace(m)}')

    with open_session(__file__) as m:
        boot(m)
        clear_observation(m)
        before, after, rows = fall_target(m)
        fall_id = pasm_constant('AUDIO_SEMANTIC_FALL')
        if after - before != 1 or not any(row['semantic_id'] == fall_id for row in rows):
            raise SystemExit(f'FAIL: FALL transition did not emit exactly one semantic request: before={before} after={after} rows={rows}')
        print(f'FALL_TRANSITION: request_delta={after - before} rows={rows}')
        before_repeat = after
        for _ in range(60):
            run_frames_exact(m, 1)
            m.pause()
        if u16(m, FALL_COUNT) != before_repeat:
            raise SystemExit(f'FAIL: FALL repeated while actor remained in fall state: before={before_repeat} after={u16(m, FALL_COUNT)}')
        print(f'FALL_HELD: request_delta={u16(m, FALL_COUNT) - before_repeat}')
        second_before, second_after, second_rows = fall_target(m)
        if second_after - second_before != 1:
            raise SystemExit(f'FAIL: second FALL transition request delta={second_after - second_before} rows={second_rows}')
        print(f'FALL_SECOND_TRANSITION: request_delta={second_after - second_before} rows={second_rows}')

    for slot in (1, 2, 3):
        with open_session(__file__) as m:
            boot(m)
            clear_observation(m)
            before, after, hp, rows = kill_target(m, slot, 5)
            print(f'SLOT {slot}: hp={hp} request_delta={after - before} rows={rows}')

    with open_session(__file__) as m:
        boot(m)
        clear_observation(m)
        before, after, hp, rows = kill_target(m, 1, 6)
        print(f'REASSIGNED_IDENTITY_SETUP: hp={hp} request_delta={after - before} rows={rows}')

    with open_session(__file__) as m:
        boot(m)
        clear_observation(m)
        delta, rows = kill_all_targets(m)
        print(f'SAME_FRAME_TRIPLE: request_delta={delta} rows={rows}')
        print(f'BACKEND: starts={u16(m, STREAM_START_COUNT)} coalesced={u16(m, COALESCED_COUNT)} suppressed={u16(m, SUPPRESSED_COUNT)}')

    with open_session(__file__) as m:
        boot(m)
        clear_observation(m)
        before, after, _, first = kill_target(m, 1, 5)
        w8(m, PLAYER + CHAR_HIT_APPLIED, 0)
        run_frames_exact(m, 60)
        prepare_target(m, SLOT2, 5, 1)
        held_input_sampled(m, m.BTN_Y, 3)
        print(f'STAGGERED: first_delta={after - before} second_delta={u16(m, REQ_COUNT) - after} rows={trace(m)} backend=(starts={u16(m, STREAM_START_COUNT)},suppressed={u16(m, SUPPRESSED_COUNT)})')


if __name__ == '__main__':
    main()
