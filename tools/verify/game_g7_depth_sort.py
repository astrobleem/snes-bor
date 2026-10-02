#!/usr/bin/env python3
"""G7 depth-sort regression for the configured bounded actor count.

The fixture retains a four-visible-actor control and adds a six-visible-actor
case. Expected order is derived independently from written ground-Y values;
hardware OAM is scanned by identifiable on-screen X content.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_SELECTED_JUMP = pasm_constant('CHAR_SELECTED_JUMP')
CHAR_THROW_ZPOS = pasm_constant('CHAR_THROW_ZPOS')
PLAYER_JUMP_FCOUNT = pasm_constant('Player_JumpFCount')
CHAR_SELECT_INDEX = pasm_constant('CharSelect_Index')

CONFIGURED_COUNT = pasm_constant('CHARACTER_ACTOR_COUNT')
CONTROL_COUNT = 4
if CONFIGURED_COUNT < 6:
    raise AssertionError(f'configured actor count is only {CONFIGURED_COUNT}')
BASE = 0x7E0A00
ENTITY_BASES = [BASE + i * CHAR_ZP_LEN for i in range(CONFIGURED_COUNT)]
PLAYER = ENTITY_BASES[0]
SCREEN_POS_X = 0x7E1601
TEST_X = [40, 80, 120, 160, 200, 240]
TEST_Y = [70, 40, 90, 55, 90, 25]

def byte(m, addr):
    return read_block(m, addr, 32)[0]
def word(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)
def i16(m, addr):
    v = word(m, addr)
    return v - 0x10000 if v & 0x8000 else v

def freeze_and_pin(m, count, xs=TEST_X, ys=TEST_Y):
    for i, base in enumerate(ENTITY_BASES):
        m.write_u16(base + CHAR_POS_X, xs[i])
        m.write_u8(base + CHAR_POS_Y, ys[i])
        m.write_u8(base + CHAR_INPUT_DRIVEN, 0)
        m.write_u8(base + CHAR_HIT_STUN, 0)
        if i != 0:
            m.write_u8(base + CHAR_SELECTED, 0)
        m.write_u8(base + CHAR_HP, CHAR_HP_MAX if i < count else 0)
    m.write_u8(PLAYER + CHAR_INPUT_DRIVEN, 1)
    m.write_u8(PLAYER + CHAR_HIT_STUN, 0)

def expected_x(m, count, xs=TEST_X):
    camera = i16(m, SCREEN_POS_X) & 0xFFFF
    return {i: (xs[i] - camera) & 0xFF for i in range(count)}

def read_oam_by_x(m, screen_x_by_actor):
    oam = read_block(m, 0, 512, mem_type='snesSpriteRam')
    matches = {actor: [] for actor in screen_x_by_actor}
    for slot in range(128):
        off = slot * 4
        for actor, sx in screen_x_by_actor.items():
            if oam[off] == sx:
                matches[actor].append((slot, oam[off + 1]))
    bad = {a: v for a, v in matches.items() if len(v) != 1}
    assert not bad, f'hardware OAM actor identification failed: {bad}'
    return {a: v[0] for a, v in matches.items()}

def expected_order(ground_y, count):
    # Established equal-depth tie rule: lower actor index first.
    return sorted(range(count), key=lambda actor: (-ground_y[actor], actor))

def pin_and_sample(m, count, xs=TEST_X, ys=TEST_Y):
    freeze_and_pin(m, count, xs, ys)
    m.run_frames(2)
    m.pause()
    actual_y = [byte(m, b + CHAR_POS_Y) for b in ENTITY_BASES[:count]]
    by = read_oam_by_x(m, expected_x(m, count, xs))
    order = [a for a, _ in sorted(by.items(), key=lambda item: item[1][0])]
    return actual_y, by, order

def check_static(m, r, count):
    actual_y, by, order = pin_and_sample(m, count)
    want = expected_order(actual_y, count)
    print(f'{count}-actor ground Y: {actual_y}')
    print(f'{count}-actor OAM by actor: {by}')
    print(f'{count}-actor expected order: {want}')
    print(f'{count}-actor actual order: {order}')
    r.check(f'{count}-actor ground Y held', actual_y == TEST_Y[:count])
    r.check(f'{count}-actor every intended actor appears exactly once in hardware OAM', len(by) == count)
    r.check(f'{count}-actor descending ground depth and equal-depth tie order', order == want)
    r.check(f'{count}-actor grounded OAM Y matches ground Y',
            all(by[i][1] == actual_y[i] for i in range(count)))
    return by

def select_leo(m):
    for _ in range(20):
        if byte(m, CHAR_SELECT_INDEX) == 12:
            return
        m.set_input(m.BTN_SELECT, 10)
        m.run_frames(20)
        m.pause()
    raise AssertionError('LEO roster index 12 not reached')

def enter_jump(m):
    m.set_input(m.BTN_A, 1)
    m.run_frames(1)
    for _ in range(40):
        m.pause()
        if byte(m, PLAYER + CHAR_SELECTED) == CHAR_SELECTED_JUMP:
            return
        m.run_frames(1)
    raise AssertionError('player never entered jump state')

def main():
    r = Reporter('G7-DEPTH-SORT', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator(); m.run_frames(150); m.pause()
        check_static(m, r, CONTROL_COUNT)
        check_static(m, r, CONFIGURED_COUNT)

        select_leo(m); freeze_and_pin(m, CONFIGURED_COUNT); m.run_frames(2); m.pause()
        r.check('LEO real jump data loaded', byte(m, PLAYER_JUMP_FCOUNT) != 0)
        enter_jump(m)
        airborne_orders = []; airborne_player_y = []; max_z = 0
        for _ in range(30):
            freeze_and_pin(m, CONFIGURED_COUNT); m.run_frames(1); m.pause()
            z = i16(m, PLAYER + CHAR_THROW_ZPOS); max_z = max(max_z, z)
            ys = [byte(m, b + CHAR_POS_Y) for b in ENTITY_BASES]
            if ys != TEST_Y: raise AssertionError(f'ground Y changed during jump: {ys}')
            if z > 0:
                by = read_oam_by_x(m, expected_x(m, CONFIGURED_COUNT))
                airborne_orders.append([a for a, _ in sorted(by.items(), key=lambda item: item[1][0])])
                airborne_player_y.append(by[0][1])
        r.check('six-actor player became airborne', max_z > 0)
        r.check('six-actor rank ignores jump altitude', bool(airborne_orders) and
                all(order == expected_order(TEST_Y, CONFIGURED_COUNT) for order in airborne_orders))
        r.check('six-actor player OAM Y moved while airborne', bool(airborne_player_y) and
                any(y != TEST_Y[0] for y in airborne_player_y))
        for _ in range(120):
            freeze_and_pin(m, CONFIGURED_COUNT); m.run_frames(1); m.pause()
            if i16(m, PLAYER + CHAR_THROW_ZPOS) == 0 and byte(m, PLAYER + CHAR_SELECTED) != CHAR_SELECTED_JUMP: break
        else: raise AssertionError('player never landed')
        _, landed, landed_order = pin_and_sample(m, CONFIGURED_COUNT)
        r.check('six-actor landing restores depth order', landed_order == expected_order(TEST_Y, CONFIGURED_COUNT))
        r.check('six-actor landing restores OAM Y', all(landed[a][1] == TEST_Y[a] for a in range(CONFIGURED_COUNT)))

        # Actor 2 crosses player ground Y while the player is airborne.
        xs = [40, 41, 140, 160, 200, 240]; start = TEST_Y[:]
        freeze_and_pin(m, CONFIGURED_COUNT, xs, start); m.run_frames(2); m.pause(); enter_jump(m)
        observed = []
        for joe_y in range(30, 111, 4):
            ys = [start[0], start[1], joe_y, start[3], start[4], start[5]]
            freeze_and_pin(m, CONFIGURED_COUNT, xs, ys); m.run_frames(2); m.pause()
            by = read_oam_by_x(m, expected_x(m, CONFIGURED_COUNT, xs))
            actual = [a for a, _ in sorted(by.items(), key=lambda item: item[1][0])]
            held_y = [byte(m, b + CHAR_POS_Y) for b in ENTITY_BASES]
            if held_y != ys:
                raise AssertionError(f'crossover Y={joe_y}: actor ground Y changed {held_y} != {ys}')
            want = expected_order(held_y, CONFIGURED_COUNT)
            # OAM is a hardware mirror of the shadow written by the prior
            # frame.  Poll for the independently-derived order to commit,
            # rather than mistaking one legitimate frame of propagation lag
            # for a sort error.
            for _ in range(20):
                if actual == want:
                    break
                m.run_frames(1); m.pause()
                by = read_oam_by_x(m, expected_x(m, CONFIGURED_COUNT, xs))
                actual = [a for a, _ in sorted(by.items(), key=lambda item: item[1][0])]
            if actual != want: raise AssertionError(f'crossover Y={joe_y}: {actual} != {want}')
            observed.append((joe_y, actual, i16(m, PLAYER + CHAR_THROW_ZPOS)))
        r.check('six-actor crossover changes rank in both directions',
                observed[0][1].index(2) > observed[0][1].index(0) and observed[-1][1].index(2) < observed[-1][1].index(0))
        r.check('six-actor crossover included airborne samples', any(z > 0 for _, _, z in observed))
    r.finish()

if __name__ == '__main__':
    main()
