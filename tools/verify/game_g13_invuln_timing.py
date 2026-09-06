#!/usr/bin/env python3
"""Semantic one-pass proof for the two player invulnerability timers."""
import json
import os
import sys
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
    def writes_for(rows_, handle):
        return [e['params']['value'] for row in rows_ for e in row['write_events']
                if e['params']['handle'] == handle]
    p1_values = writes_for(rows, p1_writes)
    p2_values = writes_for(rows, p2_writes)
    r.check('semantic writes decrement P1 once per pass',
            p1_values[:2] == [8, 7] and len(p1_values) >= 2)
    r.check('semantic writes decrement P2 once per pass',
            p2_values[:2] == [8, 7] and len(p2_values) >= 2)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'passes': rows, 'confirmed_busy_denials': None}, f, indent=2)
        f.write('\n')
    return r.finish()

if __name__ == '__main__':
    raise SystemExit(main())
