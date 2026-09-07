#!/usr/bin/env python3
"""Bounded G13 combat ownership gates.

Fixtures establish only legal geometry/state and freeze spawning.  Inputs,
target selection, collision, damage, invulnerability, and grab/throw remain
production paths.  A controlled AI attack state is used only for the matrix
where organic attack timing would make the result nondeterministic.
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, exact_input_edge, read_block, run_frames_exact, pasm_constant, pasm_constant_in
from game_g13_combat_ai import (ENTITIES, HP, HP_MAX, HITSTUN, SELECTED,
    INPUT_DRIVEN, FACING, GRAB_TARGET, GRABBED_BY, ATTACK_VARIANT,
    HIT_APPLIED, ACTOR_INVULN, P1_INVULN, P2_INVULN, SPAWN_INDEX, SPAWN_COUNT,
    AI_TARGET_SLOT, prepare_ai_fixture, set_actor, u8, u16, player_hit_case)
from game_g13_two_player_input import clear_inputs, prepare_session
from game_g13_jump_isolation import open_jump_session
from game_g13_semantic_boundary import symbol

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'out', 'g13_combat_closeout.json')
POS_X = pasm_constant('CHAR_POS_X')
POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_THROW_ZPOS = pasm_constant('CHAR_THROW_ZPOS')
CHAR_THROW_ZVEL = pasm_constant('CHAR_THROW_ZVEL')
CHAR_SELECTED_THROWN = pasm_constant('CHAR_SELECTED_THROWN')
CHAR_ATTACK2_IS_GRAB = pasm_constant('CHAR_ATTACK2_IS_GRAB')
CHAR_ROSTER_INDEX = pasm_constant('CHAR_ROSTER_INDEX')
CHAR_GRABMOVE_FCOUNT = pasm_constant('CHAR_GRABMOVE_FCOUNT')
CHAR_FRAME_INDEX = pasm_constant('CHAR_FRAME_INDEX')
CHAR_TICK_COUNTER = pasm_constant('CHAR_TICK_COUNTER')
CHAR_CHAINLENGTH = pasm_constant('CHAR_CHAINLENGTH')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STATE_TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
TITLE_STEP = pasm_constant_in('src/core/game_state.pasm', 'Title_Step')
P1, P2, NPC2, NPC3 = ENTITIES[:4]

def snap(m, b):
    return {'hp': u8(m, b + HP), 'stun': u8(m, b + HITSTUN),
            'grab': u8(m, b + GRAB_TARGET), 'by': u8(m, b + GRABBED_BY),
            'selected': u8(m, b + SELECTED),
            'x': u16(m, b + POS_X), 'y': u8(m, b + POS_Y)}

def freeze(m):
    m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))

def setup_players(m, p1x=120, p2x=180):
    prepare_session(m); clear_inputs(m)
    set_actor(m, 0, p1x, hp=HP_MAX, role=1)
    set_actor(m, 1, p2x, hp=HP_MAX, role=1)
    for i in range(2, 6):
        set_actor(m, i, 500 + i * 20, hp=0, role=2)
    freeze(m)
    m.write_u8(P1_INVULN, 0); m.write_u8(P2_INVULN, 0)
    run_frames_exact(m, 1)

def player_friendly(port):
    with open_jump_session() as m:
        setup_players(m, 140, 140)
        before = (snap(m, P1), snap(m, P2))
        exact_input_edge(m, m.BTN_Y, 1, port=port)
        run_frames_exact(m, 3)
        after = (snap(m, P1), snap(m, P2))
        return {'before': before, 'after': after}

def ai_hit(target_slot, invuln, p1_inv=0, p2_inv=0):
    with open_jump_session() as m:
        p1x, p2x = (120, 220) if target_slot == 0 else (220, 120)
        prepare_ai_fixture(m, p1x, p2x, p1x if target_slot == 0 else p2x)
        a = NPC2
        m.write_u8(a + SELECTED, 2)
        m.write_u8(a + ATTACK_VARIANT, 0)
        m.write_u8(a + HIT_APPLIED, 0)
        # Start at the production attack-entry sentinel, not an inherited
        # nearly-complete frame.  This keeps the deterministic matrix from
        # ending the attack before Character_HitApply runs.
        m.write_u8(a + CHAR_FRAME_INDEX, 0xFF)
        m.write_u8(a + CHAR_TICK_COUNTER, 1)
        m.write_u8(a + POS_Y, 150)
        m.write_u8(P1_INVULN, p1_inv)
        m.write_u8(P2_INVULN, p2_inv)
        # The target's own standalone AI timer is not part of this player hit.
        m.write_u8(ACTOR_INVULN + 2, 0)
        before = (snap(m, P1), snap(m, P2))
        run_frames_exact(m, 1)
        after = (snap(m, P1), snap(m, P2))
        return {'target_slot': u8(m, AI_TARGET_SLOT),
                'before': before, 'after': after,
                'target_invuln': invuln}

def ai_pair(reverse=False):
    with open_jump_session() as m:
        p1x, p2x = 60, 190
        a2x, a3x = ((190, 60) if reverse else (60, 190))
        prepare_ai_fixture(m, p1x, p2x, a2x)
        set_actor(m, 3, a3x, hp=HP_MAX, role=2)
        for b in (NPC2, NPC3):
            m.write_u8(b + SELECTED, 2)
            m.write_u8(b + ATTACK_VARIANT, 0)
            m.write_u8(b + HIT_APPLIED, 0)
            m.write_u8(b + CHAR_FRAME_INDEX, 0xFF)
            m.write_u8(b + CHAR_TICK_COUNTER, 1)
            m.write_u8(b + HITSTUN, 0)
            m.write_u8(b + POS_Y, 150)
            m.write_u8(ACTOR_INVULN + (b - P1) // pasm_constant('CHAR_ZP_LEN'), 0)
        m.write_u8(P1_INVULN, 0); m.write_u8(P2_INVULN, 0)
        before = (snap(m, P1), snap(m, P2))
        # One bounded service interval is sufficient for the normal ordering;
        # the reversed geometry can need the immediately following actor
        # continuation after the first actor's hit reaction.
        run_frames_exact(m, 2)
        after = (snap(m, P1), snap(m, P2))
        return {'before': before, 'after': after,
                'ai2_hit_applied': u8(m, NPC2 + HIT_APPLIED),
                'ai3_hit_applied': u8(m, NPC3 + HIT_APPLIED),
                'reverse': reverse}

def p2_leo_grab_throw(player_only=False):
    with open_jump_session() as m:
        # Unlike direct localization fixtures, this gate must retain the
        # production P2 loader result: the fixed session path establishes LEO
        # in slot 1 before PLAYING.
        m.reset_emulator(); run_frames_exact(m, 180)
        clear_inputs(m)
        # Boot remains PLAYING; place the ordinary state machine at its title
        # WAIT boundary, then use the real second-controller Start edge to
        # activate the fixed session.  The fixture enters PLAYING only after
        # that production ownership/LEO path has completed.
        activation_attempts = []
        for _ in range(3):
            m.write_u16(GAME_STATE, GAME_STATE_TITLE)
            m.write_u16(GAME_STATE + 2, GAME_STATE_TITLE)
            m.write_u8(TITLE_STEP, 2)
            exact_input_edge(m, m.BTN_START, 1, port=1)
            activation_attempts.append({
                'mode': u8(m, pasm_constant('G13_TwoPlayerEnabled')),
                'roster': u8(m, P2 + CHAR_ROSTER_INDEX),
                'role': u8(m, P2 + INPUT_DRIVEN),
                'grabmove': u8(m, P2 + CHAR_GRABMOVE_FCOUNT)})
            if (activation_attempts[-1]['mode'] == 1 and
                    activation_attempts[-1]['roster'] == 12 and
                    activation_attempts[-1]['role'] == 1 and
                    activation_attempts[-1]['grabmove'] != 0):
                break
            # A failed/partial production loader must not be mistaken for a
            # valid session.  Release the mode latch so the next neutral-
            # separated title edge retries the same production entry path.
            m.write_u8(pasm_constant('G13_TwoPlayerEnabled'), 0)
            clear_inputs(m)
        activation = activation_attempts[-1]
        m.write_u16(GAME_STATE, GAME_STATE_PLAYING)
        m.write_u16(GAME_STATE + 2, GAME_STATE_PLAYING)
        for i in range(2, 6):
            set_actor(m, i, 500 + i * 20, hp=0, role=2)
        set_actor(m, 0, 300, hp=HP_MAX, role=1)
        # Preserve slot 1's production-loaded LEO fields; only normalize its
        # live state and position for the legal grab geometry.
        m.write_u16(P2 + POS_X, 140); m.write_u8(P2 + POS_Y, 150)
        m.write_u8(P2 + HP, HP_MAX); m.write_u8(P2 + SELECTED, 0)
        m.write_u8(P2 + HITSTUN, 0); m.write_u8(P2 + GRAB_TARGET, 0xFF)
        m.write_u8(P2 + GRABBED_BY, 0xFF)
        m.write_u8(P2 + ATTACK_VARIANT, 0)
        m.write_u8(P2 + CHAR_FRAME_INDEX, 0xFF)
        m.write_u8(P2 + CHAR_TICK_COUNTER, 1)
        m.write_u8(P2 + HIT_APPLIED, 0)
        set_actor(m, 2, 500 if player_only else 140,
                  hp=HP_MAX, role=2)
        m.write_u8(ACTOR_INVULN + 2, 0)
        m.write_u8(NPC2 + HITSTUN, 255)
        m.write_u8(NPC2 + CHAR_FRAME_INDEX, 0xFF)
        m.write_u8(NPC2 + CHAR_TICK_COUNTER, 1)
        m.write_u8(P1_INVULN, 255); m.write_u8(P2_INVULN, 90)
        m.write_u16(P1 + POS_X, 140 if player_only else 300)
        freeze(m)
        clear_inputs(m)
        # Neutral polling is part of the input precondition.  Re-establish
        # the legal overlap after those polls so any ordinary player drift
        # from the production activation handoff cannot turn this into an
        # edge-of-range observation.
        m.write_u16(P2 + POS_X, 140)
        m.write_u8(P2 + POS_Y, 150)
        m.write_u8(P2 + SELECTED, 0)
        m.write_u8(P2 + CHAR_FRAME_INDEX, 0xFF)
        m.write_u8(P2 + CHAR_TICK_COUNTER, 1)
        m.write_u8(NPC2 + POS_X, 140)
        m.write_u8(NPC2 + POS_Y, 150)
        m.write_u8(NPC2 + HITSTUN, 255)
        m.write_u8(ACTOR_INVULN + 2, 0)
        neutral = {'press': u16(m, 0x7E0416),
                   'old': u16(m, 0x7E0418),
                   'trigger': u16(m, 0x7E041A)}
        entity_hook = m.add_exec_hook(symbol('CharacterEntity_Play'))
        player_input_hook = m.add_exec_hook(symbol('Anim_Play__player_input'))
        gate_entry_hook = m.add_exec_hook(symbol('Jump_PlayerInputGate'))
        grab_hook = m.add_exec_hook(symbol('Jump_PlayerInputGate__grab_trigger'))
        frame_result = exact_input_edge(m, m.BTN_R, 1, port=1)
        hook_events = m.drain_notifications()
        entity_results = [sum(e.get('params', {}).get('handle') == entity_hook
                              for e in hook_events)]
        player_input_result = {'events': sum(e.get('params', {}).get('handle') == player_input_hook for e in hook_events)}
        gate_entry_result = {'events': sum(e.get('params', {}).get('handle') == gate_entry_hook for e in hook_events)}
        gate_result = {'events': sum(e.get('params', {}).get('handle') == grab_hook for e in hook_events)}
        m.remove_hook(entity_hook)
        m.remove_hook(player_input_hook)
        m.remove_hook(gate_entry_hook)
        m.remove_hook(grab_hook)
        # Capture the immediate production action state before polling for a
        # later link; this keeps an input rejection distinguishable from a
        # missed link observation.
        immediate = {'p2': snap(m, P2),
                     'raw_input2': read_block(m, 0x7E0416, 32)[:6].hex(),
                     'grabmove_fcount': u8(m, P2 + CHAR_GRABMOVE_FCOUNT),
                     'chainlength': u8(m, P2 + CHAR_CHAINLENGTH),
                     'frame': u8(m, P2 + CHAR_FRAME_INDEX),
                     'tick': u8(m, P2 + CHAR_TICK_COUNTER),
                     'attack_variant': u8(m, P2 + ATTACK_VARIANT),
                     'hit_applied': u8(m, P2 + HIT_APPLIED)}
        immediate['game_state'] = u8(m, GAME_STATE)
        immediate['p2_input_driven'] = u8(m, P2 + INPUT_DRIVEN)
        immediate['two_player'] = u8(m, pasm_constant('G13_TwoPlayerEnabled'))
        immediate['oop_flags_0_1'] = [u16(m, 0x7E078A), u16(m, 0x7E078C)]
        immediate['oop_slot_ptr'] = u16(m, 0x7E074C)
        immediate['charselect_loaded'] = u8(m, pasm_constant('CharSelect_Loaded'))
        immediate['activation'] = activation
        immediate['activation_attempts'] = activation_attempts
        immediate['neutral_before_r'] = neutral
        immediate['gate_entry_result'] = gate_entry_result
        immediate['player_input_result'] = player_input_result
        immediate['entity_results'] = entity_results
        immediate['frame_result'] = frame_result
        immediate['hook_events'] = hook_events
        immediate['gate_result'] = gate_result
        m.release_input(port=1)
        grabbed = False
        for _ in range(30):
            run_frames_exact(m, 1)
            if u8(m, P2 + GRAB_TARGET) == 2:
                grabbed = True; break
        held = {'p2': snap(m, P2), 'npc': snap(m, NPC2),
                'p1': snap(m, P1), 'grabbed': grabbed}
        held['p2_attack2_is_grab'] = u8(m, P2 + CHAR_ATTACK2_IS_GRAB)
        held['p2_roster'] = u8(m, P2 + CHAR_ROSTER_INDEX)
        held['immediate'] = immediate
        if not grabbed:
            return {'held': held, 'thrown': None}
        exact_input_edge(m, 0, 2, port=1)
        exact_input_edge(m, m.BTN_Y, 1, port=1)
        throw_trace = []
        for _ in range(180):
            run_frames_exact(m, 1)
            throw_trace.append({'grab': u8(m, P2 + GRAB_TARGET),
                                'npc_hp': u8(m, NPC2 + HP),
                                'selected': u8(m, NPC2 + SELECTED),
                                'zpos': u16(m, NPC2 + CHAR_THROW_ZPOS),
                                'zvel': u16(m, NPC2 + CHAR_THROW_ZVEL)})
        thrown = {'p2': snap(m, P2), 'npc': snap(m, NPC2),
                  'p1': snap(m, P1),
                  'zpos': u8(m, NPC2 + CHAR_THROW_ZPOS),
                  'zvel': u8(m, NPC2 + CHAR_THROW_ZVEL),
                  'selected_thrown': any(s['selected'] == CHAR_SELECTED_THROWN for s in throw_trace),
                  'nonzero_throw_z': any(s['zpos'] != 0 or s['zvel'] != 0 for s in throw_trace),
                  'landed_fall': any(s['selected'] == pasm_constant('CHAR_SELECTED_FALL')
                                     for s in throw_trace),
                  'trace': throw_trace}
        return {'held': held, 'thrown': thrown}

def main():
    r = Reporter('G13-COMBAT-CLOSEOUT', kind='GATE')
    ff1 = player_friendly(0); ff2 = player_friendly(1)
    print('FRIENDLY_FIRE', {'p1': ff1, 'p2': ff2})
    r.check('P1 cannot damage/stun/link P2', ff1['after'][1] == ff1['before'][1])
    r.check('P2 cannot damage/stun/link P1', ff2['after'][0] == ff2['before'][0])
    ff_r = p2_leo_grab_throw(player_only=True)
    r.check('P2 LEO R cannot grab P1',
            not ff_r['held']['grabbed'] and
            ff_r['held']['p2']['grab'] == 0xFF and
            ff_r['held']['p1']['by'] == 0xFF and
            ff_r['held']['p1']['hp'] == 64 and
            ff_r['held']['p1']['stun'] == 0)

    matrix = {}
    # Vulnerable controls are paired with each invulnerable case.
    for slot in (0, 1):
        key = 'p1' if slot == 0 else 'p2'
        matrix[key] = {'vulnerable': ai_hit(slot, 0),
                       'invulnerable': ai_hit(slot, 9,
                                              p1_inv=9 if slot == 0 else 0,
                                              p2_inv=9 if slot == 1 else 0)}
        print('AI_MATRIX', key, matrix[key])
        target_before = matrix[key]['vulnerable']['before'][slot]['hp']
        target_after = matrix[key]['vulnerable']['after'][slot]['hp']
        inv_after = matrix[key]['invulnerable']['after'][slot]
        r.check(f'{key} vulnerable control lands', target_after == target_before - 4)
        r.check(f'{key} invulnerability blocks hp/stun',
                inv_after['hp'] == target_before and inv_after['stun'] == 0)

    pairs = {'normal': [ai_pair(False) for _ in range(10)],
             'reversed': [ai_pair(True) for _ in range(10)]}
    print('MULTI_AI', pairs)
    for label, rows in pairs.items():
        r.check(f'{label} 10x two AI attacks land independently',
                all(row['after'][0]['hp'] == 60 and row['after'][1]['hp'] == 60
                    for row in rows))

    grab_throw = p2_leo_grab_throw()
    print('P2_LEO_GRAB_THROW', grab_throw)
    grab_ok = grab_throw['held']['grabbed'] and grab_throw['held']['p2']['grab'] == 2 and grab_throw['held']['npc']['by'] == 1
    throw = grab_throw['thrown']
    r.check('P2 LEO real grab establishes reciprocal NPC link', grab_ok)
    r.check('P2 LEO real throw releases and launches NPC',
            throw is not None and throw['p2']['grab'] == 0xFF and
            throw['npc']['by'] == 0xFF and throw['selected_thrown'] and
            throw['nonzero_throw_z'] and throw['landed_fall'] and
            throw['p1']['hp'] == 64 and throw['p1']['grab'] == 0xFF)

    p1 = player_hit_case(0); p2 = player_hit_case(1)
    r.check('P1 hits NPC while partner remains untouched',
            p1['npc_hp_after'] == p1['npc_hp_before'] - 4 and
            p1['p2_hp_after'] == p1['p2_hp_before'])
    r.check('P2 hits NPC while partner remains untouched',
            p2['npc_hp_after'] == p2['npc_hp_before'] - 4 and
            p2['p1_hp_after'] == p2['p1_hp_before'])
    result = {'friendly_fire': {'p1': ff1, 'p2': ff2, 'p2_r': ff_r},
              'ai_matrix': matrix, 'player_npc': {'p1': p1, 'p2': p2},
              'confirmed_busy_denials': None,
              'multi_ai': pairs,
              'p2_grab_throw': grab_throw}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2); f.write('\n')
    return r.finish()

if __name__ == '__main__':
    raise SystemExit(main())
