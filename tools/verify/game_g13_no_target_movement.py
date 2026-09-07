#!/usr/bin/env python3
"""Direct run-to-hook proof of the AI no-target X/Y hold contract."""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, run_frames_exact
from game_g13_combat_ai import (ENTITIES, GRAB_TARGET, GRABBED_BY, HP,
    HITSTUN, POS_X, POS_Y, AI_TARGET_SLOT, AI_TARGET_X, AI_TARGET_Y,
    prepare_ai_fixture, u8, u16)
from game_g13_jump_isolation import open_jump_session
from game_g13_semantic_boundary import symbol

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'out', 'g13_no_target_movement.json')
P1, P2, AI = ENTITIES[0], ENTITIES[1], ENTITIES[2]

def state(m):
    return {'x': u16(m, AI + POS_X), 'y': u8(m, AI + POS_Y),
            'p1_hp': u8(m, P1 + HP), 'p2_hp': u8(m, P2 + HP),
            'p1_stun': u8(m, P1 + HITSTUN), 'p2_stun': u8(m, P2 + HITSTUN),
            'p1_grab': u8(m, P1 + GRAB_TARGET), 'p2_grab': u8(m, P2 + GRAB_TARGET),
            'p1_by': u8(m, P1 + GRABBED_BY), 'p2_by': u8(m, P2 + GRABBED_BY),
            'ai_by': u8(m, AI + GRABBED_BY)}

def main():
    r = Reporter('G13-NO-TARGET-MOVEMENT', kind='GATE')
    with open_jump_session() as m:
        prepare_ai_fixture(m, 80, 220, 140)
        m.write_u8(AI + POS_Y, 110)
        run_frames_exact(m, 1)
        stale = {'x': u16(m, AI_TARGET_X), 'y': u8(m, AI_TARGET_Y),
                 'slot': u8(m, AI_TARGET_SLOT)}
        entry = m.add_exec_hook(symbol('G13_AiChooseTarget'))
        no_target = m.add_exec_hook(symbol('G13_AiChooseTarget__no_target'))
        done = m.add_exec_hook(symbol('Core_Oop_Play__done'))
        try:
            m.drain_notifications()
            q = m.run_until(max_frames=30, hook_handle=entry)
            assert q.get('reason') == 'hookFired', q
            # This is the actual selector-entry baseline; no earlier movement
            # sample is used as the comparison state.
            before = state(m)
            before.update({'stale_x': u16(m, AI_TARGET_X),
                           'stale_y': u8(m, AI_TARGET_Y)})
            m.write_u8(P1 + HP, 0)
            m.write_u8(P2 + HP, 0)
            m.drain_notifications()
            q_no_target = m.run_until(max_frames=30, hook_handle=no_target)
            at_no_target = state(m)
            no_target_slot = u8(m, AI_TARGET_SLOT)
            no_target_stale = {'x': u16(m, AI_TARGET_X), 'y': u8(m, AI_TARGET_Y)}
            q = m.run_until(max_frames=30, hook_handle=done)
            assert q.get('reason') == 'hookFired', q
            at_done = state(m)
            done_target_slot = u8(m, AI_TARGET_SLOT)
            done_stale = {'x': u16(m, AI_TARGET_X), 'y': u8(m, AI_TARGET_Y)}
        finally:
            for h in (entry, no_target, done):
                m.remove_hook(h)
    r.check('valid first pass populated a target', stale['slot'] != 0xFF)
    r.check('selector no-target branch fired', q_no_target.get('reason') == 'hookFired')
    r.check('selector-to-OOP-done boundary fired', q.get('reason') == 'hookFired')
    r.check('selector no-target state is immediate', no_target_slot == 0xFF)
    r.check('stale target coordinates remain unchanged',
            (no_target_stale['x'], no_target_stale['y']) == (stale['x'], stale['y']))
    r.check('AI holds X and Y at invalid-target boundary',
            (at_no_target['x'], at_no_target['y']) == (before['x'], before['y']))
    r.check('AI remains held at OOP completion',
            (at_done['x'], at_done['y']) == (before['x'], before['y']))
    r.check('player HP/stun/grab remain fixture values',
            at_done['p1_hp'] == 0 and at_done['p2_hp'] == 0 and
            at_done['p1_stun'] == before['p1_stun'] and
            at_done['p2_stun'] == before['p2_stun'] and
            at_done['p1_grab'] == before['p1_grab'] and
            at_done['p2_grab'] == before['p2_grab'] and
            at_done['p1_by'] == before['p1_by'] and
            at_done['p2_by'] == before['p2_by'] and
            at_done['ai_by'] == before['ai_by'])
    payload = {'stale': stale, 'before_selector_entry': before,
               'at_no_target': at_no_target,
               'no_target_slot': no_target_slot,
               'no_target_stale': no_target_stale,
               'at_done': at_done,
               'selector_to_no_target': q_no_target,
               'done_target_slot': done_target_slot,
               'done_stale': done_stale, 'confirmed_busy_denials': None}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2); f.write('\n')
    print('NO_TARGET_MOVEMENT', payload)
    return r.finish()

if __name__ == '__main__':
    raise SystemExit(main())
