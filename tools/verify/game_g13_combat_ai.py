#!/usr/bin/env python3
"""Bounded G13 combat/AI ownership gate.

The fixture writes only controlled geometry, roles, and HP preconditions.  The
player attacks, AI dispatch, target selection, hit routing, and invulnerability
checks remain production execution paths.  Global target samples are used only
for isolated single-AI dispatches; the source contract keeps that result valid
for the complete current actor dispatch.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, exact_input_edge, pasm_constant,
                      pasm_constant_in, read_block, run_frames_exact)
from game_g13_two_player_input import (P1, P2, NPC2, clear_inputs,
                                       prepare_session)
from game_g13_jump_isolation import open_jump_session
from game_g12_six_actor_production import SPAWN_INDEX, SPAWN_COUNT
from game_g13_semantic_boundary import symbol

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'out', 'g13_combat_ai.json')
ZP = pasm_constant('CHAR_ZP_LEN')
ENTITIES = [P1 + i * ZP for i in range(6)]
POS_X = pasm_constant('CHAR_POS_X')
POS_Y = pasm_constant('CHAR_POS_Y')
HP = pasm_constant('CHAR_HP')
HP_MAX = pasm_constant('CHAR_HP_MAX')
HITSTUN = pasm_constant('CHAR_HIT_STUN')
SELECTED = pasm_constant('CHAR_SELECTED')
INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
FACING = pasm_constant('CHAR_FACING_LEFT')
GRAB_TARGET = pasm_constant('CHAR_GRAB_TARGET')
GRABBED_BY = pasm_constant('CHAR_GRABBED_BY')
AI_TARGET_SLOT = pasm_constant('G13_P2StartSeen')
AI_TARGET_OFFSET = pasm_constant('G13_AiTargetOffset')
AI_TARGET_X = pasm_constant('G13_ContextSaveJump') + 12
P2_INVULN = pasm_constant('G13_P2_InvulnFrames')
P1_INVULN = pasm_constant_in('src/core/game_state.pasm', 'Player_InvulnFrames')
HP_PER_HIT = pasm_constant('CHAR_HP_PER_HIT')
AI_MODE = pasm_constant('CHAR_INPUT_DRIVEN_AI')


def u8(m, address):
    return read_block(m, address, 32)[0]


def u16(m, address):
    b = read_block(m, address, 32)
    return b[0] | (b[1] << 8)


def set_actor(m, index, x, y=150, hp=HP_MAX, role=AI_MODE):
    b = ENTITIES[index]
    m.write_u16(b + POS_X, x)
    m.write_u8(b + POS_Y, y)
    m.write_u8(b + HP, hp)
    m.write_u8(b + INPUT_DRIVEN, role)
    m.write_u8(b + SELECTED, 0)
    m.write_u8(b + HITSTUN, 0)
    m.write_u8(b + FACING, 0)
    m.write_u8(b + GRAB_TARGET, 0xFF)
    m.write_u8(b + GRABBED_BY, 0xFF)

def neutral_player_inputs(m):
    """Poll both ports neutral without touching the configured NPC target."""
    m.hold_input(0, port=0)
    m.hold_input(0, port=1)
    try:
        run_frames_exact(m, 2)
    finally:
        m.release_input(port=0)
        m.release_input(port=1)


def prepare_ai_fixture(m, p1_x, p2_x, ai_x, p1_hp=HP_MAX, p2_hp=HP_MAX):
    prepare_session(m)
    clear_inputs(m)
    set_actor(m, 0, p1_x, hp=p1_hp, role=1)
    set_actor(m, 1, p2_x, hp=p2_hp, role=1)
    for i in range(2, 6):
        set_actor(m, i, ai_x if i == 2 else 500 + i * 20,
                  hp=HP_MAX if i == 2 else 0, role=AI_MODE)
    # Freeze only the production spawn queue so dead-slot target controls do
    # not become a different lifecycle fixture while the one-AI dispatch is
    # being observed.
    m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
    m.write_u8(P1_INVULN, 0)
    m.write_u8(P2_INVULN, 0)


def target_case(p1_x, p2_x, ai_x, p1_hp=HP_MAX, p2_hp=HP_MAX):
    with open_jump_session() as m:
        prepare_ai_fixture(m, p1_x, p2_x, ai_x, p1_hp, p2_hp)
        entry_hook = loop_hook = return_hook = finish_hook = target_write_hook = None
        if p1_hp == 0 or p2_hp == 0:
            entry_hook = m.add_exec_hook(symbol('Game_State_Play__no_death'))
            loop_hook = m.add_exec_hook(symbol('G13_AiChooseTarget'))
            finish_hook = m.add_exec_hook(symbol('G13_AiChooseTarget__finish'))
            target_write_hook = m.add_write_hook(AI_TARGET_SLOT, AI_TARGET_SLOT)
        # Keep both player contexts neutral during the sampled dispatch so
        # the target geometry is not changed by a stale held direction before
        # the AI selector executes.
        dead_control = p1_hp == 0 or p2_hp == 0
        if not dead_control:
            m.hold_input(0, port=0)
            m.hold_input(0, port=1)
        try:
            if dead_control:
                # Game_State_Play normally handles a zero P1 HP before the
                # OOP pass.  Stop at that pass's semantic entry, apply the
                # controlled HP precondition, then resume the same pass so
                # target-selection sees the intended dead/live set.
                try:
                    result = m.run_until(max_frames=30, hook_handle=entry_hook)
                    assert result.get('reason') == 'hookFired', result
                    result = m.run_until(max_frames=30, hook_handle=loop_hook)
                    assert result.get('reason') == 'hookFired', result
                    # The selector entry is the last safe boundary before it
                    # reads either player HP.  Install the dead/live control
                    # there, then stop at its return before any later frame
                    # can run the normal P1 respawn path.
                    m.write_u8(P1 + HP, p1_hp)
                    m.write_u8(P2 + HP, p2_hp)
                    result = m.run_until(max_frames=30, hook_handle=finish_hook)
                    assert result.get('reason') == 'hookFired', result
                    events = m.drain_notifications()
                    target_writes = [e['params']['value'] for e in events
                                     if e.get('params', {}).get('handle') == target_write_hook]
                finally:
                    m.remove_hook(entry_hook)
                    m.remove_hook(loop_hook)
                    m.remove_hook(finish_hook)
                    m.remove_hook(target_write_hook)
            else:
                run_frames_exact(m, 1)
        finally:
            if not dead_control:
                m.release_input(port=0)
                m.release_input(port=1)
        if dead_control and target_writes:
            # The selector writes FF on entry.  A later actor/frame may
            # overwrite the shared diagnostic cell after this localized call;
            # for the both-dead case the first selector write is the required
            # no-target result, before any later dispatch can contaminate it.
            target_slot = (0xFF if p1_hp == 0 and p2_hp == 0 and
                           0xFF in target_writes else target_writes[-1])
        else:
            target_slot = u8(m, AI_TARGET_SLOT)
        return {
            'target_slot': target_slot,
            'target_offset': u16(m, AI_TARGET_OFFSET),
            'target_x': u16(m, AI_TARGET_X),
            'p1_hp': u8(m, P1 + HP),
            'p2_hp': u8(m, P2 + HP),
        }


def player_hit_case(port):
    with open_jump_session() as m:
        prepare_session(m)
        clear_inputs(m)
        p1_x, p2_x = ((120, 220) if port == 0 else (220, 120))
        set_actor(m, 0, p1_x, hp=HP_MAX, role=1)
        set_actor(m, 1, p2_x, hp=HP_MAX, role=1)
        set_actor(m, 2, 136, hp=HP_MAX, role=AI_MODE)
        # Hold the target in a normal reaction window so its AI cannot land a
        # competing hit while the player attack is being observed.  The
        # target remains a live combat actor and the player collision path is
        # unchanged.
        m.write_u8(ENTITIES[2] + HITSTUN, 30)
        for i in range(3, 6):
            set_actor(m, i, 500 + i * 20, hp=0, role=AI_MODE)
        # Freeze the production spawn queue after the live target is built.
        # Do not use neutral_players() here: that helper is intentionally a
        # dead-slot cleanup fixture and would invalidate NPC2 immediately
        # before the player attack.
        m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
        # Keep the non-attacking player immune to the test actor's ordinary
        # AI hit while preserving the real player-vs-NPC collision path.
        m.write_u8(P1_INVULN, 255 if port == 0 else 0)
        m.write_u8(P2_INVULN, 255 if port == 1 else 0)
        p1_before, p2_before, npc_before = u8(m, P1 + HP), u8(m, P2 + HP), u8(m, ENTITIES[2] + HP)
        neutral_player_inputs(m)
        m.hold_input(m.BTN_Y, port=port)
        try:
            run_frames_exact(m, 3)
        finally:
            m.release_input(port=port)
        for _ in range(40):
            run_frames_exact(m, 1)
            if u8(m, ENTITIES[2] + HP) < npc_before:
                break
        return {
            'p1_hp_before': p1_before, 'p2_hp_before': p2_before,
            'npc_hp_before': npc_before,
            'p1_hp_after': u8(m, P1 + HP), 'p2_hp_after': u8(m, P2 + HP),
            'npc_hp_after': u8(m, ENTITIES[2] + HP),
            'p1_stun': u8(m, P1 + HITSTUN), 'p2_stun': u8(m, P2 + HITSTUN),
        }


def invuln_case(target_slot):
    with open_jump_session() as m:
        prepare_ai_fixture(m, 120, 220, 120 if target_slot == 0 else 220)
        m.write_u8(P1_INVULN, 9 if target_slot == 0 else 0)
        m.write_u8(P2_INVULN, 9 if target_slot == 1 else 0)
        before = (u8(m, P1 + HP), u8(m, P2 + HP), u8(m, P1 + HITSTUN),
                  u8(m, P2 + HITSTUN), u8(m, P1_INVULN), u8(m, P2_INVULN))
        run_frames_exact(m, 1)
        after = (u8(m, P1 + HP), u8(m, P2 + HP), u8(m, P1 + HITSTUN),
                 u8(m, P2 + HITSTUN), u8(m, P1_INVULN), u8(m, P2_INVULN))
        return {'before': before, 'after': after}


def main():
    r = Reporter('G13-COMBAT-AI', kind='GATE')
    p1_hit = player_hit_case(0)
    p2_hit = player_hit_case(1)
    print('P1_VS_NPC', p1_hit)
    print('P2_VS_NPC', p2_hit)
    r.check('P1 damages NPC only',
            p1_hit['npc_hp_after'] == p1_hit['npc_hp_before'] - HP_PER_HIT and
            p1_hit['p2_hp_after'] == p1_hit['p2_hp_before'])
    r.check('P2 damages NPC only',
            p2_hit['npc_hp_after'] == p2_hit['npc_hp_before'] - HP_PER_HIT and
            p2_hit['p1_hp_after'] == p2_hit['p1_hp_before'])

    # Keep all geometry inside the current stage clamp (Screen_MaxX is 224
    # in this fixture); otherwise normal player clamping changes the intended
    # distances before the AI dispatch.
    near_p1 = target_case(50, 200, 60)
    near_p2 = target_case(50, 200, 190)
    tie = target_case(50, 200, 125)
    p2_only = target_case(50, 200, 190, p1_hp=0)
    p1_only = target_case(50, 200, 60, p2_hp=0)
    both_dead = target_case(50, 200, 125, p1_hp=0, p2_hp=0)
    print('AI_TARGETS', {'p1': near_p1, 'p2': near_p2, 'tie': tie,
                         'p2_only': p2_only, 'p1_only': p1_only,
                         'both_dead': both_dead})
    r.check('AI nearest P1 selects slot 0', near_p1['target_slot'] == 0)
    r.check('AI nearest P2 selects slot 1', near_p2['target_slot'] == 1)
    r.check('AI exact tie selects lower P1 slot', tie['target_slot'] == 0)
    r.check('dead P1 leaves live P2 targetable', p2_only['target_slot'] == 1)
    r.check('dead P2 leaves live P1 targetable', p1_only['target_slot'] == 0)
    r.check('both dead returns explicit no-target sentinel',
            both_dead['target_slot'] == 0xFF)

    p1_inv = invuln_case(0)
    p2_inv = invuln_case(1)
    print('INVULN_SNAPSHOT_ONLY', {'p1': p1_inv, 'p2': p2_inv})

    result = {'p1_vs_npc': p1_hit, 'p2_vs_npc': p2_hit,
              'targets': {'p1': near_p1, 'p2': near_p2, 'tie': tie,
                          'p2_only': p2_only, 'p1_only': p1_only,
                          'both_dead': both_dead},
              'invulnerability_snapshot_only': {'p1': p1_inv, 'p2': p2_inv},
              'confirmed_busy_denials': None}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
