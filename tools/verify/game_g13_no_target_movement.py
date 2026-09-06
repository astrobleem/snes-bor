#!/usr/bin/env python3
"""Semantic negative proof for the AI no-target movement contract.

The fixture deliberately invalidates both players only at the sole live AI's
selector entry.  It then stops at the same OOP pass's completion, avoiding the
next Game_State_Play death/respawn check.  Target coordinates are retained as
stale diagnostics; the slot sentinel is the only validity signal.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, read_block, run_frames_exact
from game_g13_combat_ai import (ENTITIES, GRAB_TARGET, GRABBED_BY, HP,
                                HITSTUN, POS_X, POS_Y, AI_TARGET_SLOT,
                                AI_TARGET_X, AI_TARGET_OFFSET, prepare_ai_fixture,
                                u8, u16)
from game_g13_jump_isolation import open_jump_session
from game_g13_semantic_boundary import symbol

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'out', 'g13_no_target_movement.json')
P1 = ENTITIES[0]
P2 = ENTITIES[1]


def main():
    r = Reporter('G13-NO-TARGET-MOVEMENT', kind='GATE')
    with open_jump_session() as m:
        prepare_ai_fixture(m, 80, 220, 140)
        m.write_u8(ENTITIES[2] + POS_Y, 110)
        m.drain_notifications()
        # First complete pass establishes a valid target and leaves its X/Y
        # coordinates available as deliberately stale diagnostics.
        run_frames_exact(m, 1)
        stale = {'x': u16(m, AI_TARGET_X), 'y': u8(m, AI_TARGET_X + 2),
                 'slot': u8(m, AI_TARGET_SLOT)}
        before = {
            'x': u16(m, ENTITIES[2] + POS_X),
            'y': u8(m, ENTITIES[2] + POS_Y),
            'p1_hp': u8(m, P1 + HP), 'p2_hp': u8(m, P2 + HP),
            'p1_stun': u8(m, P1 + HITSTUN), 'p2_stun': u8(m, P2 + HITSTUN),
            'p1_grab': u8(m, P1 + GRAB_TARGET), 'p2_grab': u8(m, P2 + GRAB_TARGET),
            'ai_grab': u8(m, ENTITIES[2] + GRABBED_BY),
        }
        entry = m.add_exec_hook(symbol('G13_AiChooseTarget'))
        done = m.add_exec_hook(symbol('Core_Oop_Play__done'))
        target_write = m.add_write_hook(AI_TARGET_SLOT, AI_TARGET_SLOT)
        try:
            m.drain_notifications()
            q = m.run_until(max_frames=30, hook_handle=entry)
            assert q.get('reason') == 'hookFired', q
            entry_events = m.drain_notifications()
            entry_frame = next((e['params'].get('frame') for e in entry_events
                                if e.get('params', {}).get('handle') == entry), None)
            # This is the selector-localized precondition, not a later death
            # or respawn state.
            m.write_u8(P1 + HP, 0)
            m.write_u8(P2 + HP, 0)
            # Continue directly to the OOP semantic end.  The resolver's
            # return hook is intentionally not used: this MCP stops at a
            # subroutine RTL on the next command boundary, which can make a
            # same-pass claim ambiguous even though the OOP end is reliable.
            target_slot = u8(m, AI_TARGET_SLOT)
            stale_after = {'x': u16(m, AI_TARGET_X), 'y': u8(m, AI_TARGET_X + 2)}
            q = m.run_until(max_frames=30, hook_handle=done)
            assert q.get('reason') == 'hookFired', q
            done_events = m.drain_notifications()
            target_events = [e['params'] for e in entry_events + done_events
                             if e.get('params', {}).get('handle') == target_write]
            target_slot = next((e['value'] for e in target_events if e['value'] == 0xFF),
                               u8(m, AI_TARGET_SLOT))
            done_frame = next((e['params'].get('frame') for e in done_events
                               if e.get('params', {}).get('handle') == done), None)
            after = {
                'x': u16(m, ENTITIES[2] + POS_X),
                'y': u8(m, ENTITIES[2] + POS_Y),
                'p1_hp': u8(m, P1 + HP), 'p2_hp': u8(m, P2 + HP),
                'p1_stun': u8(m, P1 + HITSTUN), 'p2_stun': u8(m, P2 + HITSTUN),
                'p1_grab': u8(m, P1 + GRAB_TARGET), 'p2_grab': u8(m, P2 + GRAB_TARGET),
                'ai_grab': u8(m, ENTITIES[2] + GRABBED_BY),
            }
        finally:
            for h in (entry, done, target_write):
                m.remove_hook(h)
    same_pass = entry_frame == done_frame
    r.check('valid first pass populated a target', stale['slot'] != 0xFF)
    r.check('selector returned no-target sentinel before OOP completion',
            target_slot == 0xFF)
    r.check('stale target coordinates remain diagnostics only', stale_after ==
            {'x': stale['x'], 'y': stale['y']})
    r.check('invalid target holds both AI axes',
            (after['x'], after['y']) == (before['x'], before['y']))
    r.check('no-target AI pass changes no player reaction state',
            after['p1_hp'] == before['p1_hp'] and after['p2_hp'] == before['p2_hp'] and
            after['p1_stun'] == before['p1_stun'] and after['p2_stun'] == before['p2_stun'] and
            after['p1_grab'] == before['p1_grab'] and after['p2_grab'] == before['p2_grab'])
    payload = {'entry_frame': entry_frame,
               'done_frame': done_frame, 'same_oop_pass': same_pass,
               'stale': stale, 'stale_after': stale_after,
               'target_slot': target_slot, 'before': before, 'after': after,
               'confirmed_busy_denials': None}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
        f.write('\n')
    print('NO_TARGET_MOVEMENT', payload)
    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
