#!/usr/bin/env python3
"""Bounded G13 P1/P2 jump-family ownership gate.

The gate uses fresh sessions and real controller edges.  It does not write
selected/jump state to manufacture an action.  P1 and P2 continue to use the
existing CharacterEntity_Play bridge and the accepted single staging buffer.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (MESEN_EXE, _free_tcp_port, exact_input_edge,
                      pasm_constant,
                      pasm_constant_in, poll_until, read_block,
                      run_frames_exact, Reporter)
from game_g13_two_player_input import (P1, P2, neutral_joint,
                                       neutral_players, clear_inputs)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'out', 'g13_jump_isolation.json')

from mesen_mcp.session import McpSession  # noqa: E402


def open_jump_session():
    # Mesen detects the MSU-1 sidecar relative to its working directory.  The
    # review worktree intentionally carries only the matching bor.msu; the
    # existing full test package (selected by G13_MESEN_CWD) supplies the
    # unchanged production PCM sidecars without copying or modifying audio.
    cwd = os.environ.get('G13_MESEN_CWD', os.path.join(ROOT, 'distribution'))
    return McpSession(rom=os.path.join(ROOT, 'distribution', 'bor.sfc'),
                      mesen=MESEN_EXE, cwd=cwd, port=_free_tcp_port())

POS_X = pasm_constant('CHAR_POS_X')
SELECTED = pasm_constant('CHAR_SELECTED')
FRAME_INDEX = pasm_constant('CHAR_FRAME_INDEX')
THROW_ZPOS = pasm_constant('CHAR_THROW_ZPOS')
THROW_ZVEL = pasm_constant('CHAR_THROW_ZVEL')
ROSTER_INDEX = pasm_constant('CHAR_ROSTER_INDEX')
INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')

P2_JUMP_BASE = pasm_constant('Player2_JumpFCount')
P2_JUMP_MODE = pasm_constant('Player2_JumpAnimMode')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
TITLE_STEP = pasm_constant_in('src/core/game_state.pasm', 'Title_Step')
TITLE_STEP_WAIT = pasm_constant_in('src/core/game_state.pasm', 'TITLE_STEP_WAIT')
CHARSELECT_STEP = pasm_constant_in('src/core/game_state.pasm', 'CharSelect_Step')
CHARSELECT_STEP_WAIT = pasm_constant_in('src/core/game_state.pasm', 'CHARSELECT_STEP_WAIT')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
CHARSELECT_INDEX = pasm_constant('CharSelect_Index')
LEO_ROSTER_INDEX = 12


def u8(m, address):
    return read_block(m, address, 32)[0]


def u16(m, address):
    data = read_block(m, address, 32)
    return data[0] | (data[1] << 8)


def actor(m, base):
    return {
        'selected': u8(m, base + SELECTED),
        'frame': u8(m, base + FRAME_INDEX),
        'x': u16(m, base + POS_X),
        'zpos': u16(m, base + THROW_ZPOS),
        'zvel': u16(m, base + THROW_ZVEL),
        'roster': u8(m, base + ROSTER_INDEX),
        'input_driven': u8(m, base + INPUT_DRIVEN),
    }


def p1_jump(m):
    # The two-byte bases are deliberately read as two individual bytes so the
    # logical layout does not imply a contiguous 16-byte block.
    return {
        'fcount': u8(m, pasm_constant('Player_JumpFCount')),
        'delay': u8(m, pasm_constant('Player_JumpDelay')),
        'attack_fcount': u8(m, pasm_constant('Player_JumpAttackFCount')),
        'attack_delay': u8(m, pasm_constant('Player_JumpAttackDelay')),
        'attack2_fcount': u8(m, pasm_constant('Player_JumpAttack2FCount')),
        'attack2_delay': u8(m, pasm_constant('Player_JumpAttack2Delay')),
        'base': [u8(m, pasm_constant('Player_JumpBaseLo')),
                 u8(m, pasm_constant('Player_JumpBaseLo') + 1),
                 u8(m, pasm_constant('Player_JumpBaseHi'))],
        'attack_base': [u8(m, pasm_constant('Player_JumpAttackBaseLo')),
                        u8(m, pasm_constant('Player_JumpAttackBaseLo') + 1),
                        u8(m, pasm_constant('Player_JumpAttackBaseHi'))],
        'attack2_base': [u8(m, pasm_constant('Player_JumpAttack2BaseLo')),
                         u8(m, pasm_constant('Player_JumpAttack2BaseLo') + 1),
                         u8(m, pasm_constant('Player_JumpAttack2BaseHi'))],
        'mode': u8(m, pasm_constant('Player_JumpAnimMode')),
    }


def p2_jump(m):
    return {
        'block': read_block(m, P2_JUMP_BASE, 32)[:16].hex(),
        'fcount': u8(m, P2_JUMP_BASE),
        'attack_fcount': u8(m, P2_JUMP_BASE + 2),
        'attack2_fcount': u8(m, P2_JUMP_BASE + 4),
        'mode': u8(m, P2_JUMP_MODE),
    }


def setup(m, p1_roster=0, force_p1_reload=False):
    # Use the real pre-PLAYING P2 session path.  The direct-state helper is
    # intentionally not used here because it does not load LEO's jump family.
    m.reset_emulator()
    run_frames_exact(m, 180)
    m.hold_input(m.BTN_START, port=1)
    run_frames_exact(m, 1)
    m.release_input(port=1)
    clear_inputs(m)
    m.write_u16(GAME_STATE, GAME_STATE_TITLE)
    m.write_u16(GAME_STATE + 2, GAME_STATE_TITLE)
    m.write_u8(TITLE_STEP, TITLE_STEP_WAIT)
    clear_inputs(m)
    exact_input_edge(m, m.BTN_START, 1, port=1)
    run_frames_exact(m, 1)
    # Activation is a title-state transition; the first post-transition poll
    # can still expose the consumed Start word.  Drain both ports with a
    # persistent neutral override before the jump edge.  Do not assert the
    # transient context bytes here; the activation gate owns that evidence.
    m.hold_input(0, port=0)
    m.hold_input(0, port=1)
    try:
        run_frames_exact(m, 4)
    finally:
        m.release_input(port=0)
        m.release_input(port=1)
    clear_inputs(m)
    neutral_players(m)
    run_frames_exact(m, 1)
    # Complete the real fixed-session handoff.  P2 Start selects the session
    # while TITLE is active; P1 Start then advances TITLE, CHARSELECT, and
    # the canonical NewGameReset/Stage_Load path.  Stopping after the P2
    # selection leaves the P2 jump-family block populated only by the
    # bring-up helper, which is not a gameplay jump proof.
    # Keep the P1 edge installed through the poll itself.  This is equivalent
    # to exact_input_edge for delivery, but makes the title-state boundary
    # explicit and avoids sampling the released state as the transition cue.
    m.hold_input(m.BTN_START, port=0)
    m.hold_input(0, port=1)
    try:
        run_frames_exact(m, 1)
    finally:
        m.release_input(port=0)
        m.release_input(port=1)
    clear_inputs(m)
    neutral_players(m)
    m.hold_input(0, port=0)
    m.hold_input(0, port=1)
    try:
        reached_charselect = poll_until(m, lambda mm: u16(mm, GAME_STATE) == 2, 120)
    finally:
        m.release_input(port=0)
        m.release_input(port=1)
    assert reached_charselect, (
        'P1 title Start did not reach CHARSELECT: ' +
        hex(u16(m, GAME_STATE)))
    m.hold_input(0, port=0)
    m.hold_input(0, port=1)
    try:
        at_charselect_wait = poll_until(
            m, lambda mm: u8(mm, CHARSELECT_STEP) == CHARSELECT_STEP_WAIT, 120)
    finally:
        m.release_input(port=0)
        m.release_input(port=1)
    assert at_charselect_wait, (
        'CHARSELECT did not reach WAIT: ' + hex(u8(m, CHARSELECT_STEP)))
    # For jump-family tests P1 must use the one currently converted roster
    # entry with real jump/jumpattack/jumpattack2 content.  This is an
    # ordinary character-select reload, not a WRAM state injection.  The
    # default keeps RALF for the asymmetric ownership negative control.
    if force_p1_reload and p1_roster == 0:
        # Reload RALF through the ordinary selector path once.  This makes
        # the negative control's standalone P1 jump globals come from the
        # current RALF record, rather than from the earlier P2 LEO load that
        # the bridge must preserve around its own loader call.
        exact_input_edge(m, m.BTN_LEFT, 1, port=0)
        m.hold_input(0, port=0)
        m.hold_input(0, port=1)
        try:
            run_frames_exact(m, 12)
        finally:
            m.release_input(port=0)
            m.release_input(port=1)
    attempts = 0
    while u8(m, CHARSELECT_INDEX) != p1_roster and attempts < 32:
        exact_input_edge(m, m.BTN_RIGHT, 1, port=0)
        m.hold_input(0, port=0)
        m.hold_input(0, port=1)
        try:
            # Anim_LoadCharacter is a synchronous MSU read plus queued
            # palette DMA; keep the neutral poll active until that ordinary
            # reselect has returned before issuing the next edge.
            run_frames_exact(m, 12)
        finally:
            m.release_input(port=0)
            m.release_input(port=1)
        attempts += 1
    m.hold_input(0, port=0)
    m.hold_input(0, port=1)
    try:
        selection_ready = poll_until(
            m, lambda mm: u8(mm, CHARSELECT_STEP) == CHARSELECT_STEP_WAIT, 120)
    finally:
        m.release_input(port=0)
        m.release_input(port=1)
    assert selection_ready, 'character-select reselect did not return to WAIT'
    assert u8(m, CHARSELECT_INDEX) == p1_roster, (
        'character-select roster did not reach requested P1 roster: ' +
        f'{u8(m, CHARSELECT_INDEX)} != {p1_roster}')
    reached_playing = False
    for _ in range(3):
        m.hold_input(m.BTN_START, port=0)
        m.hold_input(0, port=1)
        try:
            run_frames_exact(m, 1)
        finally:
            m.release_input(port=0)
            m.release_input(port=1)
        m.hold_input(0, port=0)
        m.hold_input(0, port=1)
        try:
            reached_playing = poll_until(
                m, lambda mm: u16(mm, GAME_STATE) == GAME_STATE_PLAYING, 120)
        finally:
            m.release_input(port=0)
            m.release_input(port=1)
        if reached_playing:
            break
    clear_inputs(m)
    neutral_players(m)
    assert reached_playing, (
        'P1 CHARSELECT Start did not reach PLAYING: ' + hex(u16(m, GAME_STATE)))
    run_frames_exact(m, 1)
    if p1_roster == LEO_ROSTER_INDEX:
        # NewGameReset reinitializes the actor-0 window from the production
        # start roster.  Use the existing live Select/reload path to put P1
        # on LEO for the positive jump-family cases; no actor fields are
        # written by the fixture.
        attempts = 0
        while u8(m, P1 + ROSTER_INDEX) != LEO_ROSTER_INDEX and attempts < 64:
            exact_input_edge(m, m.BTN_SELECT, 1, port=0)
            m.hold_input(0, port=0)
            m.hold_input(0, port=1)
            try:
                run_frames_exact(m, 20)
            finally:
                m.release_input(port=0)
                m.release_input(port=1)
            attempts += 1
        assert u8(m, P1 + ROSTER_INDEX) == LEO_ROSTER_INDEX, (
            'live P1 reselect did not load LEO')


def edge_window(m, p1_buttons=0, p2_buttons=0, frames=4):
    m.hold_input(p1_buttons, port=0)
    m.hold_input(p2_buttons, port=1)
    samples = []
    try:
        for _ in range(frames):
            run_frames_exact(m, 1)
            samples.append({'p1': actor(m, P1), 'p2': actor(m, P2),
                            'p1_jump': p1_jump(m), 'p2_jump': p2_jump(m)})
    finally:
        m.release_input(port=0)
        m.release_input(port=1)
    return samples


def jump_case(p1_buttons=0, p2_buttons=0, frames=4):
    with open_jump_session() as m:
        p1_roster = LEO_ROSTER_INDEX if p1_buttons else 0
        setup(m, p1_roster=p1_roster,
              force_p1_reload=(p1_roster == 0))
        clear_inputs(m)
        neutral_players(m)
        before = {'p1': actor(m, P1), 'p2': actor(m, P2),
                  'p1_jump': p1_jump(m), 'p2_jump': p2_jump(m)}
        samples = edge_window(m, p1_buttons, p2_buttons, frames)
        return {'before': before, 'samples': samples,
                'after': {'p1': actor(m, P1), 'p2': actor(m, P2),
                          'p1_jump': p1_jump(m), 'p2_jump': p2_jump(m)}}


def family_case(port, buttons):
    with open_jump_session() as m:
        setup(m, p1_roster=LEO_ROSTER_INDEX)
        clear_inputs(m)
        neutral_players(m)
        edge_window(m, m.BTN_A if port == 0 else 0,
                    m.BTN_A if port == 1 else 0, 4)
        # A jump edge can finish with the emulator paused before the next
        # neutral poll has committed both old-state words.  Use the existing
        # exact neutral helper, rather than treating that transient as a
        # bridge failure.
        clear_inputs(m)
        before = {'p1': p1_jump(m), 'p2': p2_jump(m)}
        samples = edge_window(m, buttons if port == 0 else 0,
                              buttons if port == 1 else 0, 4)
        return {'before': before, 'samples': samples,
                'after': {'p1': p1_jump(m), 'p2': p2_jump(m)}}


def asymmetric_family_case():
    with open_jump_session() as m:
        setup(m, force_p1_reload=True)
        clear_inputs(m)
        neutral_players(m)
        before = {'p1': p1_jump(m), 'p2': p2_jump(m),
                  'rosters': [u8(m, P1 + ROSTER_INDEX),
                              u8(m, P2 + ROSTER_INDEX)]}
        samples = edge_window(m, 0, m.BTN_A, 4)
        return {'before': before, 'samples': samples,
                'after': {'p1': p1_jump(m), 'p2': p2_jump(m)}}


def landing_case():
    with open_jump_session() as m:
        setup(m, p1_roster=LEO_ROSTER_INDEX)
        clear_inputs(m)
        neutral_players(m)
        edge_window(m, m.BTN_A, 0, 4)
        clear_inputs(m)
        edge_window(m, 0, m.BTN_A, 4)
        timeline = []
        for _ in range(140):
            run_frames_exact(m, 1)
            timeline.append({'p1': actor(m, P1), 'p2': actor(m, P2),
                             'p1_jump': p1_jump(m), 'p2_jump': p2_jump(m)})
            if ((timeline[-1]['p1']['selected'] != 5 and
                 timeline[-1]['p2']['selected'] == 5) or
                (timeline[-1]['p2']['selected'] != 5 and
                 timeline[-1]['p1']['selected'] == 5)):
                break
        return timeline


def airborne_movement_case():
    with open_jump_session() as m:
        setup(m, p1_roster=LEO_ROSTER_INDEX)
        clear_inputs(m)
        neutral_players(m)
        edge_window(m, m.BTN_A, m.BTN_A, 4)
        x0 = (u16(m, P1 + POS_X), u16(m, P2 + POS_X))
        samples = edge_window(m, m.BTN_LEFT, m.BTN_RIGHT, 4)
        x1 = (samples[-1]['p1']['x'], samples[-1]['p2']['x'])
        return {'x0': x0, 'x1': x1, 'samples': samples}


def main():
    report = Reporter('G13-JUMP-ISOLATION', kind='GATE')
    result = {
        'p1_only': jump_case(p1_buttons=0x001, p2_buttons=0),
        'p2_only': jump_case(p1_buttons=0, p2_buttons=0x001),
        'simultaneous': jump_case(p1_buttons=0x001, p2_buttons=0x001),
        'p1_attack_y': family_case(0, 0x800),
        'p2_attack_y': family_case(1, 0x800),
        'p1_attack2_x': family_case(0, 0x100),
        'p2_attack2_x': family_case(1, 0x100),
        'asymmetric': asymmetric_family_case(),
        'landing': landing_case(),
        'airborne_movement': airborne_movement_case(),
    }
    # API masks are kept local to this verifier: BTN_A=1, BTN_X=0x100,
    # BTN_Y=0x800.  Source-side jump tests observe the resulting state only.
    p1_only = result['p1_only']['after']
    p2_only = result['p2_only']['after']
    simultaneous = result['simultaneous']['after']
    report.check('P1-only jump is airborne and P2 stays grounded',
                 p1_only['p1']['selected'] == 5 and p1_only['p1']['zpos'] != 0 and
                 p1_only['p2']['selected'] != 5 and p1_only['p2']['zpos'] == 0)
    report.check('P2-only jump is airborne and P1 stays grounded',
                 p2_only['p2']['selected'] == 5 and p2_only['p2']['zpos'] != 0 and
                 p2_only['p1']['selected'] != 5 and p2_only['p1']['zpos'] == 0)
    report.check('P1 globals restored after P2 dispatch',
                 result['p2_only']['before']['p1_jump'] == p2_only['p1_jump'])
    report.check('simultaneous jumps are independently airborne',
                 simultaneous['p1']['selected'] == 5 and
                 simultaneous['p2']['selected'] == 5 and
                 simultaneous['p1']['zpos'] != 0 and
                 simultaneous['p2']['zpos'] != 0)
    for key, mode in (('p1_attack_y', 1), ('p2_attack_y', 1),
                      ('p1_attack2_x', 2), ('p2_attack2_x', 2)):
        item = result[key]['after']
        field = item['p1' if key.startswith('p1') else 'p2']
        report.check(f'{key} mode isolated', field['mode'] == mode)
    asymmetric = result['asymmetric']
    report.check('asymmetric non-LEO P1 does not acquire P2 jump family',
                 asymmetric['after']['p1']['fcount'] == 0 and
                 asymmetric['after']['p1']['attack_fcount'] == 0 and
                 asymmetric['after']['p1']['attack2_fcount'] == 0 and
                 asymmetric['after']['p2']['fcount'] != 0 and
                 asymmetric['after']['p2']['mode'] == 0 and
                 asymmetric['after']['p1']['mode'] == 0)
    landing = result['landing']
    report.check('staggered landing leaves the other actor airborne',
                 any((row['p1']['selected'] != 5 and row['p2']['selected'] == 5) or
                     (row['p2']['selected'] != 5 and row['p1']['selected'] == 5)
                     for row in landing))
    movement = result['airborne_movement']
    report.check('airborne horizontal input remains actor-local',
                 movement['x1'][0] < movement['x0'][0] and
                 movement['x1'][1] > movement['x0'][1])
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps(result, indent=2))
    return report.finish()


if __name__ == '__main__':
    raise SystemExit(main())
