#!/usr/bin/env python3
"""Semantic one-pass proof for the two player invulnerability timers."""
import json
import os
import sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, read_block
from game_g13_jump_isolation import open_jump_session
from game_g13_two_player_input import prepare_session
from game_g13_semantic_boundary import symbol

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'out', 'g13_invuln_timing.json')
P1_INV = 0x7E2755
P2_INV = 0x7E26CC

def u8(m, address):
    return read_block(m, address, 32)[0]

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
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'passes': rows, 'confirmed_busy_denials': None}, f, indent=2)
        f.write('\n')
    return r.finish()

if __name__ == '__main__':
    raise SystemExit(main())
