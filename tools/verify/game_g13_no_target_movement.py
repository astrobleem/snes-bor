#!/usr/bin/env python3
"""Ordered-event proof of the AI no-target movement contract."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, read_block, run_frames_exact
from game_g13_combat_ai import (ENTITIES, GRAB_TARGET, GRABBED_BY, HP,
    HITSTUN, POS_X, POS_Y, AI_TARGET_SLOT, AI_TARGET_X, AI_TARGET_Y,
    prepare_ai_fixture, u8, u16)
from game_g13_jump_isolation import open_jump_session
from game_g13_semantic_boundary import symbol

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'out', 'g13_no_target_movement.json')
P1, P2 = ENTITIES[0], ENTITIES[1]


def main():
    r = Reporter('G13-NO-TARGET-MOVEMENT', kind='GATE')
    with open_jump_session() as m:
        prepare_ai_fixture(m, 80, 220, 140)
        m.write_u8(ENTITIES[2] + POS_Y, 110)
        m.drain_notifications()
        run_frames_exact(m, 1)
        stale = {'x': u16(m, AI_TARGET_X), 'y': u8(m, AI_TARGET_Y),
                 'slot': u8(m, AI_TARGET_SLOT)}
        entry = m.add_exec_hook(symbol('G13_AiChooseTarget'))
        target_valid = m.add_exec_hook(symbol('G13_AiTargetValid'))
        x_valid = m.add_exec_hook(symbol('Character_PlayFrame__ai_x_target_valid'))
        hold_y = m.add_exec_hook(symbol('Character_PlayFrame__hold_y'))
        hit_target = m.add_exec_hook(symbol('Character_HitApply_VsPlayer__has_target'))
        done = m.add_exec_hook(symbol('Core_Oop_Play__done'))
        target_write = m.add_write_hook(AI_TARGET_SLOT, AI_TARGET_SLOT)
        x_write = m.add_write_hook(ENTITIES[2] + POS_X, ENTITIES[2] + POS_X)
        y_write = m.add_write_hook(ENTITIES[2] + POS_Y, ENTITIES[2] + POS_Y)
        player_writes = [m.add_write_hook(a, a) for a in
                         (P1 + HP, P2 + HP, P1 + HITSTUN, P2 + HITSTUN,
                          P1 + GRAB_TARGET, P2 + GRAB_TARGET,
                          P1 + GRABBED_BY, P2 + GRABBED_BY)]
        handles = {entry: 'selector_entry', target_valid: 'target_valid',
                   x_valid: 'x_target_valid', hold_y: 'hold_y',
                   hit_target: 'hit_target', done: 'oop_done',
                   target_write: 'target_slot_write', x_write: 'ai_x_write',
                   y_write: 'ai_y_write', **{h: 'player_write' for h in player_writes}}
        try:
            m.drain_notifications()
            q = m.run_until(max_frames=30, hook_handle=entry)
            assert q.get('reason') == 'hookFired', q
            entry_result = q
            before = {'x': u16(m, ENTITIES[2] + POS_X),
                      'y': u8(m, ENTITIES[2] + POS_Y),
                      'p1_hp': u8(m, P1 + HP), 'p2_hp': u8(m, P2 + HP),
                      'p1_stun': u8(m, P1 + HITSTUN), 'p2_stun': u8(m, P2 + HITSTUN),
                      'p1_grab': u8(m, P1 + GRAB_TARGET), 'p2_grab': u8(m, P2 + GRAB_TARGET),
                      'p1_by': u8(m, P1 + GRABBED_BY), 'p2_by': u8(m, P2 + GRABBED_BY),
                      'ai_by': u8(m, ENTITIES[2] + GRABBED_BY),
                      'stale_x': u16(m, AI_TARGET_X), 'stale_y': u8(m, AI_TARGET_Y)}
            m.write_u8(P1 + HP, 0)
            m.write_u8(P2 + HP, 0)
            m.drain_notifications()
            q = m.run_until(max_frames=30, hook_handle=done)
            assert q.get('reason') == 'hookFired', q
            done_result = q
            notifications = m.drain_notifications()
        finally:
            for h in (entry, target_valid, x_valid, hold_y, hit_target, done,
                      target_write, x_write, y_write, *player_writes):
                m.remove_hook(h)
    if not any(e.get('params', {}).get('handle') == entry for e in notifications):
        if isinstance(entry_result, dict) and entry_result.get('address') is not None:
            notifications.insert(0, {'params': {'handle': entry,
                                                 'address': entry_result.get('address'),
                                                 'frame': entry_result.get('frame'),
                                                 'value': entry_result.get('value')}})
    entry_index = max((i for i, e in enumerate(notifications)
                       if e.get('params', {}).get('handle') == entry), default=-1)
    done_index = next((i for i, e in enumerate(notifications[entry_index + 1:],
                                                entry_index + 1)
                       if e.get('params', {}).get('handle') == done), None)
    events = notifications[entry_index:done_index + 1] if done_index is not None else []
    if done_index is None:
        # run_until returns the stopping notification directly on MCP builds
        # that do not enqueue it a second time.
        direct = done_result.get('notification') or done_result.get('event')
        if isinstance(direct, dict):
            notifications.append(direct)
            events = notifications
    if done_index is None:
        print('DONE_RUN_UNTIL_RESULT', done_result)
    names = [handles.get(e.get('params', {}).get('handle')) for e in events]
    def values(name):
        return [e['params'].get('value') for e in events
                if handles.get(e.get('params', {}).get('handle')) == name]
    target_values = values('target_slot_write')
    x_values, y_values = values('ai_x_write'), values('ai_y_write')
    player_events = [n for n in names if n == 'player_write']
    target_slot = next((v for v in target_values if v == 0xFF), None)
    after = {'x_writes': x_values, 'y_writes': y_values,
             'player_write_events': player_events}
    r.check('valid first pass populated a target', stale['slot'] != 0xFF)
    r.check('selector writes explicit no-target sentinel', target_slot == 0xFF)
    r.check('stale target coordinates remain unchanged diagnostics',
            (before['stale_x'], before['stale_y']) == (stale['x'], stale['y']))
    r.check('target-valid helper executes', 'target_valid' in names)
    r.check('invalid target bypasses X target-valid path', 'x_target_valid' not in names)
    r.check('invalid target reaches Y hold tail', 'hold_y' in names)
    r.check('invalid target bypasses player hit leaf', 'hit_target' not in names)
    r.check('AI X has no changed write', not any(v != before['x'] for v in x_values))
    r.check('AI Y writes are absent or same-value',
            not any(v != before['y'] for v in y_values))
    r.check('no post-fixture player HP/stun/grab writes', not player_events)
    ordered = [{'name': handles.get(e.get('params', {}).get('handle')),
                'frame': e.get('params', {}).get('frame'),
                'value': e.get('params', {}).get('value')}
               for e in events]
    payload = {'events_to_first_oop_done': ordered, 'stale': stale,
               'before_selector_entry': before, 'target_slot_write_values': target_values,
               'after': after, 'first_oop_done_seen': done_index is not None,
               'confirmed_busy_denials': None}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
        f.write('\n')
    print('NO_TARGET_MOVEMENT', payload)
    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
