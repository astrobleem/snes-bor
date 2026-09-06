#!/usr/bin/env python3
"""Semantic one-pass proof for the two player invulnerability timers."""
import json
import os
import sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, pasm_constant, pasm_constant_in, read_block,
                      run_frames_exact)
from game_g13_jump_isolation import open_jump_session
from game_g13_two_player_input import prepare_session
from game_g13_semantic_boundary import symbol

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'out', 'g13_invuln_timing.json')
P1_INV = 0x7E2755
P2_INV = 0x7E26CC
P2_MODE = pasm_constant('G13_TwoPlayerEnabled')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PAUSED = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PAUSED')

def u8(m, address):
    return read_block(m, address, 32)[0]


def grouped_events(events, p1_handle, p2_handle):
    grouped = defaultdict(lambda: defaultdict(list))
    for event in events:
        p = event.get('params', {})
        if p.get('handle') == p1_handle:
            grouped[p['frame']]['p1'].append(p['value'])
        elif p.get('handle') == p2_handle:
            grouped[p['frame']]['p2'].append(p['value'])
    return grouped


def negative_case(two_player, p1_seed, p2_seed, paused=False):
    """Exercise the ownership negatives with event writes as authority."""
    with open_jump_session() as m:
        prepare_session(m)
        m.write_u8(P2_MODE, 1 if two_player else 0)
        entry = m.add_exec_hook(symbol('Game_State_Play__no_death'))
        done = m.add_exec_hook(symbol('Game_State_TickExtraActorTimers__done'))
        p1_writes = m.add_write_hook(P1_INV, P1_INV)
        p2_writes = m.add_write_hook(P2_INV, P2_INV)
        try:
            m.drain_notifications()
            if paused:
                m.write_u8(P1_INV, p1_seed)
                m.write_u8(P2_INV, p2_seed)
                m.drain_notifications()
                m.write_u8(GAME_STATE, GAME_STATE_PAUSED)
                run_frames_exact(m, 4)
                events = m.drain_notifications()
                return {'writes': events, 'paused': True,
                        'values': (u8(m, P1_INV), u8(m, P2_INV))}
            q = m.run_until(max_frames=30, hook_handle=entry)
            assert q.get('reason') == 'hookFired', q
            m.write_u8(P1_INV, p1_seed)
            m.write_u8(P2_INV, p2_seed)
            m.drain_notifications()
            q = m.run_until(max_frames=30, hook_handle=done)
            assert q.get('reason') == 'hookFired', q
            events = m.drain_notifications()
            return {'writes': events, 'paused': False,
                    'values': (u8(m, P1_INV), u8(m, P2_INV)),
                    'grouped': {str(k): dict(v) for k, v in
                                grouped_events(events, p1_writes, p2_writes).items()}}
        finally:
            for h in (entry, done, p1_writes, p2_writes):
                m.remove_hook(h)

def main():
    r = Reporter('G13-INVULN-TIMING', kind='GATE')
    rows = []
    with open_jump_session() as m:
        prepare_session(m)
        entry = m.add_exec_hook(symbol('Game_State_Play__no_death'))
        extra = m.add_exec_hook(symbol('Game_State_TickExtraActorTimers'))
        done = m.add_exec_hook(symbol('Game_State_TickExtraActorTimers__done'))
        p1_writes = m.add_write_hook(P1_INV, P1_INV)
        p2_writes = m.add_write_hook(P2_INV, P2_INV)
        try:
            for pass_no in (1, 2):
                q = m.run_until(max_frames=30, hook_handle=entry)
                assert q.get('reason') == 'hookFired', q
                before = (u8(m, P1_INV), u8(m, P2_INV))
                if pass_no == 1:
                    m.write_u8(P1_INV, 9)
                    m.write_u8(P2_INV, 9)
                q = m.run_until(max_frames=30, hook_handle=extra)
                assert q.get('reason') == 'hookFired', q
                at_extra = (u8(m, P1_INV), u8(m, P2_INV))
                q = m.run_until(max_frames=30, hook_handle=done)
                assert q.get('reason') == 'hookFired', q
                after = (u8(m, P1_INV), u8(m, P2_INV))
                events = m.drain_notifications()
                rows.append({'pass': pass_no, 'before': before,
                             'at_extra_entry': at_extra, 'after': after,
                             'write_events': [e for e in events
                                              if e.get('params', {}).get('handle') in
                                              (p1_writes, p2_writes)]})
        finally:
            m.remove_hook(entry)
            m.remove_hook(extra)
            m.remove_hook(done)
            m.remove_hook(p1_writes)
            m.remove_hook(p2_writes)
    print('TIMER_PASSES', rows)
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        for event in row['write_events']:
            p = event['params']
            address = 'p1' if p['handle'] == p1_writes else 'p2'
            grouped[p['frame']][address].append(p['value'])
    frames = sorted(grouped)
    no_duplicates = all(len(grouped[f]['p1']) <= 1 and
                        len(grouped[f]['p2']) <= 1 for f in frames)
    p1_values = [grouped[f]['p1'][0] for f in frames if grouped[f]['p1']]
    p2_values = [grouped[f]['p2'][0] for f in frames if grouped[f]['p2']]
    p1_stepwise = all(b == a - 1 for a, b in zip(p1_values, p1_values[1:]))
    p2_stepwise = all(b == a - 1 for a, b in zip(p2_values, p2_values[1:]))
    paired_equal = all(grouped[f]['p1'][0] == grouped[f]['p2'][0]
                       for f in frames if grouped[f]['p1'] and grouped[f]['p2'])
    r.check('one write per timer per observed frame', no_duplicates)
    r.check('P1 writes are exactly one-step decrements',
            len(p1_values) >= 2 and p1_stepwise)
    r.check('P2 writes are exactly one-step decrements',
            len(p2_values) >= 2 and p2_stepwise)
    r.check('equal starting timers remain equal on paired writes', paired_equal)
    one_p = negative_case(False, 9, 9)
    p1_only = negative_case(True, 9, 0)
    p2_only = negative_case(True, 0, 9)
    paused = negative_case(True, 9, 9, paused=True)
    cold = negative_case(False, 0, 0)
    def writes_by(row):
        return [e for e in row['writes']
                if e.get('params', {}).get('address') in (P1_INV, P2_INV)]
    one_p_writes = writes_by(one_p)
    p1_only_writes = writes_by(p1_only)
    p2_only_writes = writes_by(p2_only)
    paused_writes = writes_by(paused)
    r.check('1P seeded P2 timer has no decrement write',
            not any(e['params']['address'] == P2_INV for e in one_p_writes))
    r.check('2P asymmetric P1-only write',
            any(e['params']['address'] == P1_INV for e in p1_only_writes) and
            not any(e['params']['address'] == P2_INV for e in p1_only_writes))
    r.check('2P asymmetric P2-only write',
            any(e['params']['address'] == P2_INV for e in p2_only_writes) and
            not any(e['params']['address'] == P1_INV for e in p2_only_writes))
    r.check('PAUSED leaves both timers unchanged', not paused_writes)
    r.check('cold/disabled timer is explicitly zero', cold['values'][1] == 0)
    print('TIMER_NEGATIVES', {'1p': one_p, 'p1_only': p1_only,
                              'p2_only': p2_only, 'paused': paused,
                              'cold': cold})
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'passes': rows, 'negatives': {'1p': one_p,
                   'p1_only': p1_only, 'p2_only': p2_only,
                   'paused': paused, 'cold': cold},
                   'confirmed_busy_denials': None}, f, indent=2)
        f.write('\n')
    return r.finish()

if __name__ == '__main__':
    raise SystemExit(main())
