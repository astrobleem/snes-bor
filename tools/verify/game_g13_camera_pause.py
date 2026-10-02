#!/usr/bin/env python3
"""Focused G13 shared-camera, tether, and global-pause gate.

This verifier uses controlled two-player sessions and real controller edges.
It does not write gameplay action state.  Camera arithmetic is sampled from
the production screen pass; pause tests exercise the production state machine.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, pasm_constant_in,
                      read_block, run_frames_exact, exact_input_edge, Reporter)
from game_g13_two_player_input import (P1, P2, select_two_player)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'out', 'g13_camera_pause.json')
SYM = os.path.join(ROOT, 'src', 'main.sym')

ZP_LEN = pasm_constant('CHAR_ZP_LEN')
POS_X = pasm_constant('CHAR_POS_X')
POS_Y = pasm_constant('CHAR_POS_Y')
HP = pasm_constant('CHAR_HP')
SELECTED = pasm_constant('CHAR_SELECTED')
HITSTUN = pasm_constant('CHAR_HIT_STUN')
THROW_ZPOS = pasm_constant('CHAR_THROW_ZPOS')
THROW_ZVEL = pasm_constant('CHAR_THROW_ZVEL')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STATE_PAUSED = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PAUSED')
P2_MODE = pasm_constant('G13_TwoPlayerEnabled')
PAUSE_STEP = pasm_constant_in('src/core/pausemenu.pasm', 'Pause_Step')
PAUSE_STEP_WAIT = pasm_constant_in('src/core/pausemenu.pasm', 'PAUSE_STEP_WAIT')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
P1_INVULN = pasm_constant_in('src/core/game_state.pasm', 'Player_InvulnFrames')
P2_INVULN = pasm_constant('G13_P2_InvulnFrames')
ACTOR_INVULN = pasm_constant_in('src/core/game_state.pasm', 'Actor_InvulnFrames')


def symbol(name):
    rx = re.compile(r'^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4,6})\s+' + re.escape(name) + r'\s*$')
    with open(SYM, encoding='utf-8') as f:
        for line in f:
            m = rx.match(line.strip())
            if m:
                return (int(m.group(1), 16) << 16) | int(m.group(2), 16)
    raise KeyError(name)


def wram_symbol(name):
    value = symbol(name)
    return value if value >= 0x7E0000 else 0x7E0000 + value


SCREEN_POS_X = wram_symbol('Screen_PosX')
SCREEN_TARGET_X = wram_symbol('Screen_TargetX')
SCREEN_SIZE_X = wram_symbol('Screen_SizeX')
SCREEN_MIN_X = wram_symbol('Screen_MinX')
SCREEN_MAX_X = wram_symbol('Screen_MaxX')
NMI_FRAME = wram_symbol('Nmi_FrameCounter')


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def neutral_joint(m):
    """Obtain a real neutral poll after a prior held-input interval."""
    m.hold_input(0, port=0)
    m.hold_input(0, port=1)
    try:
        run_frames_exact(m, 4)
    finally:
        m.release_input(port=0)
        m.release_input(port=1)
    state = (read_block(m, 0x7E0410, 32)[:6].hex(),
             read_block(m, 0x7E0416, 32)[:6].hex())
    assert state == ('000000000000', '000000000000'), state
    return state


def actor(m, base):
    return {'x': u16(m, base + POS_X), 'y': u8(m, base + POS_Y),
            'hp': u8(m, base + HP), 'selected': u8(m, base + SELECTED),
            'hitstun': u8(m, base + HITSTUN), 'zpos': u16(m, base + THROW_ZPOS),
            'zvel': u16(m, base + THROW_ZVEL)}


def neutral_fixture(m, two_player=True):
    # This is the established jump/combat isolation pattern: the real session
    # owns player roles; only unrelated NPC traffic is made inert.
    m.write_u8(P2_MODE, 1 if two_player else 0)
    m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
    for slot in range(2, 6):
        b = P1 + slot * ZP_LEN
        m.write_u8(b + HP, 0)
        m.write_u8(b + SELECTED, 0)
        m.write_u8(b + HITSTUN, 0)
        m.write_u16(b + THROW_ZPOS, 0)
        m.write_u16(b + THROW_ZVEL, 0)
        m.write_u8(ACTOR_INVULN + slot, 0)
    for b, x, hp in ((P1, 120, CHAR_HP_MAX), (P2, 180, CHAR_HP_MAX)):
        m.write_u16(b + POS_X, x)
        m.write_u8(b + POS_Y, 150)
        m.write_u8(b + HP, hp if (b == P1 or two_player) else 0)
        m.write_u8(b + SELECTED, 0)
        m.write_u8(b + HITSTUN, 0)
        m.write_u16(b + THROW_ZPOS, 0)
        m.write_u16(b + THROW_ZVEL, 0)
    m.write_u8(P1_INVULN, 0)
    m.write_u8(P2_INVULN, 0)
    neutral_joint(m)


def setup(m, two_player=True):
    m.reset_emulator()
    run_frames_exact(m, 180)
    m.set_input(m.BTN_SELECT, 10)
    run_frames_exact(m, 40)
    select_two_player(m)
    neutral_fixture(m, two_player)
    m.write_u16(GAME_STATE, GAME_STATE_PLAYING)
    run_frames_exact(m, 4)


def screen_state(m):
    return {'target_x': u16(m, SCREEN_TARGET_X), 'pos_x': u16(m, SCREEN_POS_X),
            'size_x': u16(m, SCREEN_SIZE_X), 'min_x': u16(m, SCREEN_MIN_X),
            'max_x': u16(m, SCREEN_MAX_X)}


def camera_arithmetic(m, p1x, p2x):
    m.write_u16(P1 + POS_X, p1x)
    m.write_u16(P2 + POS_X, p2x)
    # One frame can still be the tail of the fixture's prior screen pass;
    # use a short bounded pair and sample the settled target, not an arbitrary
    # transient endpoint.
    run_frames_exact(m, 2)
    result = screen_state(m)
    result['p1_x'] = u16(m, P1 + POS_X)
    result['p2_x'] = u16(m, P2 + POS_X)
    result['two_player'] = u8(m, P2_MODE)
    return result


def pause_snapshot(m):
    return {'state': u8(m, GAME_STATE), 'step': u8(m, PAUSE_STEP),
            'p1': actor(m, P1), 'p2': actor(m, P2),
            'npc2': actor(m, P1 + 2 * ZP_LEN),
            'spawn_index': u8(m, SPAWN_INDEX), 'screen_x': u16(m, SCREEN_POS_X),
            'p1_invuln': u8(m, P1_INVULN), 'p2_invuln': u8(m, P2_INVULN),
            'nmi': u16(m, NMI_FRAME)}


def pause_round(m, port):
    neutral_joint(m)
    exact_input_edge(m, m.BTN_START, 1, port=port)
    for _ in range(20):
        if u8(m, GAME_STATE) == GAME_STATE_PAUSED and u8(m, PAUSE_STEP) == PAUSE_STEP_WAIT:
            break
        run_frames_exact(m, 1)
    before = pause_snapshot(m)
    run_frames_exact(m, 5)
    frozen = pause_snapshot(m)
    neutral_joint(m)
    exact_input_edge(m, m.BTN_START, 1, port=port)
    for _ in range(20):
        if u8(m, GAME_STATE) == GAME_STATE_PLAYING:
            break
        run_frames_exact(m, 1)
    return before, frozen, pause_snapshot(m)


def main():
    r = Reporter('G13-CAMERA-PAUSE', kind='GATE')
    report = {'camera': {}, 'tether': {}, 'pause': {}, 'regressions': {}}
    with open_session(__file__) as m:
        setup(m)
        a = camera_arithmetic(m, 80, 200)
        b = camera_arithmetic(m, 200, 80)
        print('camera samples:', a, b)
        expected = (80 + 200) // 2 - a['size_x'] // 2
        r.check(f'both-live midpoint target {a["target_x"]} == {expected}', a['target_x'] == expected)
        r.check(f'swapped midpoint target invariant ({b["target_x"]})', b['target_x'] == expected)
        odd = camera_arithmetic(m, 81, 200)
        r.check(f'odd midpoint floors ({odd["target_x"]})', odd['target_x'] == ((81 + 200) // 2 - odd['size_x'] // 2))
        left = camera_arithmetic(m, 0, 8)
        r.check(f'left target does not wrap ({left["target_x"]})', left['target_x'] == 0)
        m.write_u16(SCREEN_MAX_X, 300)
        right = camera_arithmetic(m, 600, 700)
        r.check(f'right camera position is clamped ({right["pos_x"]} <= {right["max_x"]})', right['pos_x'] <= right['max_x'])
        report['camera'] = {'midpoint': a, 'swapped': b, 'odd': odd, 'left': left,
                            'right': right,
                            'survivor_follow': {
                                'status': 'SOURCE_CONTRACT_VERIFIED_RUNTIME_HOOK_UNMEASURED',
                                'p1_branch': 'P1 live -> PlayerEntity_PosX',
                                'p2_branch': 'P1 dead -> Entity1_PosX'}}

        # Tether is tested through actual player movement, not by calling the
        # helper or writing the resulting coordinate.
        m.write_u16(SCREEN_POS_X, 100)
        m.write_u16(P1 + POS_X, 20)
        m.write_u16(P2 + POS_X, 350)
        neutral_joint(m)
        exact_input_edge(m, m.BTN_LEFT, 1, port=0)
        exact_input_edge(m, m.BTN_RIGHT, 1, port=1)
        tether_left_right = (u16(m, P1 + POS_X), u16(m, P2 + POS_X))
        tether_screen = screen_state(m)
        r.check(f'tether left stays in shared viewport ({tether_left_right[0]} >= {tether_screen["pos_x"]})',
                tether_left_right[0] >= tether_screen['pos_x'])
        r.check(f'tether right stays in shared viewport ({tether_left_right[1]} <= {tether_screen["pos_x"] + tether_screen["size_x"] - 31})',
                tether_left_right[1] <= tether_screen['pos_x'] + tether_screen['size_x'] - 31)
        report['tether']['left_right'] = {'actors': tether_left_right, 'screen': tether_screen}

        setup(m)
        m.write_u16(P1 + POS_X, 130)
        m.write_u16(P2 + POS_X, 190)
        m.write_u16(SCREEN_POS_X, 0)
        neutral_joint(m)
        m.hold_input(m.BTN_RIGHT, port=0)
        m.hold_input(m.BTN_RIGHT, port=1)
        try:
            before_move = screen_state(m)
            run_frames_exact(m, 8)
            easing_right = {'before': before_move, 'after': screen_state(m),
                             'p1': u16(m, P1 + POS_X), 'p2': u16(m, P2 + POS_X)}
        finally:
            m.release_input(port=0); m.release_input(port=1)
        r.check('live camera eases right with players',
                easing_right['after']['target_x'] > easing_right['before']['target_x'] and
                easing_right['after']['pos_x'] > easing_right['before']['pos_x'] and
                easing_right['p1'] > 130 and easing_right['p2'] > 190)
        neutral_joint(m)
        m.hold_input(m.BTN_LEFT, port=0)
        m.hold_input(m.BTN_LEFT, port=1)
        try:
            before_left = screen_state(m)
            run_frames_exact(m, 8)
            easing_left = {'before': before_left, 'after': screen_state(m),
                           'p1': u16(m, P1 + POS_X), 'p2': u16(m, P2 + POS_X)}
        finally:
            m.release_input(port=0); m.release_input(port=1)
        r.check('live camera eases left with players',
                easing_left['after']['target_x'] < easing_left['before']['target_x'] and
                easing_left['after']['pos_x'] <= easing_left['before']['pos_x'] and
                easing_left['p1'] < easing_right['p1'] and easing_left['p2'] < easing_right['p2'])
        report['camera']['easing'] = {'right': easing_right, 'left': easing_left}

        setup(m)
        m.write_u16(P1 + POS_X, 140)
        m.write_u16(P2 + POS_X, 160)
        neutral_joint(m)
        m.hold_input(m.BTN_LEFT, port=0)
        m.hold_input(m.BTN_RIGHT, port=1)
        try:
            run_frames_exact(m, 20)
        finally:
            m.release_input(port=0); m.release_input(port=1)
        apart = {'p1': u16(m, P1 + POS_X), 'p2': u16(m, P2 + POS_X),
                 'screen': screen_state(m)}
        r.check('players moving apart remain ordered and tethered',
                apart['p1'] < apart['p2'] and apart['p1'] >= apart['screen']['pos_x'] and
                apart['p2'] <= apart['screen']['pos_x'] + apart['screen']['size_x'] - 32)
        report['tether']['apart'] = apart

        setup(m, two_player=False)
        m.write_u16(SCREEN_POS_X, 100)
        m.write_u16(P1 + POS_X, 20)
        neutral_joint(m)
        exact_input_edge(m, m.BTN_LEFT, 1, port=0)
        one_player_x = u16(m, P1 + POS_X)
        r.check(f'1P proposed X is not G13-tethered ({one_player_x})', one_player_x < 100)
        report['tether']['one_player'] = {'p1_x': one_player_x, 'screen': screen_state(m)}

        # P1 and P2 pause entry/resume use the same global menu row.
        setup(m)
        p1_before, p1_frozen, p1_after = pause_round(m, 0)
        r.check(f'P1 Start enters PAUSED/WAIT ({p1_before["state"]},{p1_before["step"]})',
                p1_before['state'] == GAME_STATE_PAUSED and p1_before['step'] == PAUSE_STEP_WAIT)
        r.check('P1 pause freezes gameplay but NMI advances',
                p1_frozen['nmi'] != p1_before['nmi'] and
                p1_frozen['p1'] == p1_before['p1'] and p1_frozen['p2'] == p1_before['p2'] and
                p1_frozen['npc2'] == p1_before['npc2'] and
                p1_frozen['spawn_index'] == p1_before['spawn_index'] and
                p1_frozen['screen_x'] == p1_before['screen_x'])
        r.check(f'P1 Start resumes PLAYING ({p1_after["state"]})', p1_after['state'] == GAME_STATE_PLAYING)
        setup(m)
        p2_before, p2_frozen, p2_after = pause_round(m, 1)
        r.check(f'P2 Start enters PAUSED/WAIT ({p2_before["state"]},{p2_before["step"]})',
                p2_before['state'] == GAME_STATE_PAUSED and p2_before['step'] == PAUSE_STEP_WAIT)
        r.check(f'P2 Start resumes PLAYING ({p2_after["state"]})', p2_after['state'] == GAME_STATE_PLAYING)
        report['pause'] = {'p1_before': p1_before, 'p1_frozen': p1_frozen,
                           'p1_after': p1_after, 'p2_before': p2_before,
                           'p2_frozen': p2_frozen, 'p2_after': p2_after}

        setup(m, two_player=False)
        neutral_joint(m)
        exact_input_edge(m, m.BTN_START, 1, port=1)
        run_frames_exact(m, 2)
        r.check(f'1P P2 Start does not pause ({u8(m, GAME_STATE)})', u8(m, GAME_STATE) != GAME_STATE_PAUSED)
        exact_input_edge(m, m.BTN_START, 1, port=0)
        run_frames_exact(m, 2)
        r.check(f'1P P1 Start still pauses ({u8(m, GAME_STATE)})', u8(m, GAME_STATE) == GAME_STATE_PAUSED)
        report['pause']['one_player_negative'] = {'state': u8(m, GAME_STATE)}

        setup(m)
        neutral_joint(m)
        m.hold_input(m.BTN_START, port=0)
        m.hold_input(m.BTN_START, port=1)
        try:
            run_frames_exact(m, 1)
        finally:
            m.release_input(port=0); m.release_input(port=1)
        r.check(f'simultaneous Start enters PAUSED once ({u8(m, GAME_STATE)})', u8(m, GAME_STATE) == GAME_STATE_PAUSED)
        run_frames_exact(m, 4)
        r.check('simultaneous Start remains one global pause', u8(m, GAME_STATE) == GAME_STATE_PAUSED)
        report['pause']['simultaneous'] = {'state': u8(m, GAME_STATE)}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    r.finish()


if __name__ == '__main__':
    main()
