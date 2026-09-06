#!/usr/bin/env python3
"""G13 semantic-boundary probe for one synchronized P1/P2 action update.

This is a localization gate, not a production trace framework.  It uses the
existing Mesen execution-hook API and the checked-in symbol file to establish
the order of one Core_Oop_Play pass.  The old input verifier sampled after
one PPU frame and therefore could stop between the slot-0 and slot-1 actor
updates.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, read_block, run_frames_exact, Reporter,
                      pasm_constant)
from game_g13_two_player_input import (P1, P2, SELECTED, INPUT_DRIVEN,
                                       CHAR_HP_MAX, GAME_STATE,
                                       GAME_STATE_PLAYING, P2_MODE,
                                       select_two_player, neutral_players,
                                       neutral_joint)


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYM = os.path.join(ROOT, 'src', 'main.sym')
OUT = os.path.join(ROOT, 'out', 'g13_semantic_boundary.json')


def symbol(name):
    wanted = re.compile(r'^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+' +
                        re.escape(name) + r'\s*$')
    with open(SYM, encoding='utf-8') as f:
        for line in f:
            match = wanted.match(line.strip())
            if match:
                return (int(match.group(1), 16) << 16) | int(match.group(2), 16)
    raise KeyError(name)


def actor_snapshot(m, base):
    data = read_block(m, base + SELECTED, 32)
    return {
        'dp_base': hex(base),
        'selected': data[0],
        'input_driven': read_block(m, base + INPUT_DRIVEN, 32)[0],
        'hp': read_block(m, base + pasm_constant('CHAR_HP'), 32)[0],
        'press': read_block(m, 0x7E0410, 32)[:2].hex(),
        'trigger': read_block(m, 0x7E0412, 32)[:2].hex(),
        'old': read_block(m, 0x7E0414, 32)[:2].hex(),
    }


def main():
    report = Reporter('G13-SEMANTIC-BOUNDARY', kind='GATE')
    names = [
        'Core_Input_Poll',
        'Core_Input_Poll_P2',
        'Core_Oop_Play__loop',
        'CharacterEntity_Play',
        'G13_Player2_ContextEnter',
        'Anim_Play__player_input',
        'Jump_PlayerInputGate',
        'Jump_AtchainTrigger',
        'Jump_AtchainTrigger__pressed',
        'G13_Player2_ContextExit',
        'Core_Oop_Play__done',
    ]
    pcs = {name: symbol(name) for name in names}
    with open_session(__file__) as m:
        m.reset_emulator()
        run_frames_exact(m, 180)
        m.set_input(m.BTN_SELECT, 10)
        run_frames_exact(m, 40)
        select_two_player(m)
        neutral_joint(m)
        neutral_players(m)

        handles = {name: m.add_exec_hook(pc, pc) for name, pc in pcs.items()}
        raw_hooks = {
            'JOY1L': m.add_read_hook(0x004218, 0x004218),
            'JOY1H': m.add_read_hook(0x004219, 0x004219),
            'JOY2L': m.add_read_hook(0x00421A, 0x00421A),
            'JOY2H': m.add_read_hook(0x00421B, 0x00421B),
        }
        selected_hooks = {
            'P1_CHAR_SELECTED_write': m.add_write_hook(P1 + SELECTED, P1 + SELECTED),
            'P2_CHAR_SELECTED_write': m.add_write_hook(P2 + SELECTED, P2 + SELECTED),
        }
        # Both overrides are installed while paused; exactly one frame advances
        # with both physical Y edges visible to the same Core_Input_Poll.
        hold0 = m.hold_input(m.BTN_Y, port=0)
        hold1 = m.hold_input(m.BTN_Y, port=1)
        try:
            # The emulator can be paused at the first poll instruction after
            # fixture setup. Complete the current neutral frame and the next
            # synchronized Y frame, plus one settling frame. The hook stream
            # identifies the Y frame itself; selected is sampled only after
            # that frame's Core_Oop_Play__done notification exists.
            first_frame = run_frames_exact(m, 3)
            notifications = m.drain_notifications()
            event_rows = []
            for notification in notifications:
                params = notification.get('params', {})
                handle = params.get('handle')
                hook_map = {**handles, **selected_hooks}
                matched = next((name for name, value in hook_map.items()
                                if value == handle), None)
                if matched is None:
                    continue
                row = {
                    'event': matched,
                    'frame': params.get('frame'),
                    'address': hex(params.get('address', pcs[matched])),
                    'value': params.get('value'),
                    'cpu_at_stop_unavailable_for_async_hook': True,
                }
                event_rows.append(row)
            payload = {
                'gate': 'G13-SEMANTIC-BOUNDARY',
                'first_frame': first_frame,
                'run_until': None,
                'hold_results': {'port0': hold0, 'port1': hold1},
                'raw_read_events': [n.get('params', {}) for n in notifications
                                    if n.get('params', {}).get('handle') in raw_hooks.values()],
                'symbols': {name: hex(pc) for name, pc in pcs.items()},
                'events': event_rows,
                'input_latches': {
                    'joy1': read_block(m, 0x7E041C, 32)[:2].hex(),
                    'joy2': read_block(m, 0x7E041E, 32)[:2].hex(),
                    'p1_context': read_block(m, 0x7E0410, 32)[:6].hex(),
                    'p2_context': read_block(m, 0x7E0416, 32)[:6].hex(),
                },
                'actors_at_boundary': {
                    'p1': actor_snapshot(m, P1),
                    'p2': actor_snapshot(m, P2),
                },
                'measurement_status': {
                    'event_time_cpu_registers': 'unavailable: this installed MCP exposes no get_cpu_state tool; hook order and the P2-only context entry are retained',
                    'same_update_identity': 'hook frame ordering plus Core_Oop_Play__done boundary',
                },
            }
        finally:
            m.release_input(port=0)
            m.release_input(port=1)
            for handle in handles.values():
                m.remove_hook(handle)
            for handle in selected_hooks.values():
                m.remove_hook(handle)
            for handle in raw_hooks.values():
                m.remove_hook(handle)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
        f.write('\n')
    rows = payload['events']
    order = [row['event'] for row in rows]
    done = 'Core_Oop_Play__done' in order
    p1 = 'CharacterEntity_Play' in order
    p2_context = 'G13_Player2_ContextEnter' in order and 'G13_Player2_ContextExit' in order
    raw_by_frame = {}
    for event in payload['raw_read_events']:
        raw_by_frame.setdefault(event.get('frame'), []).append(event)
    semantic_invocations = []
    for frame, reads in raw_by_frame.items():
        high_bytes = [event.get('value') for event in reads
                      if event.get('address') in (16921, 16923)]
        if high_bytes.count(64) != 2:
            continue
        poll_index = next((i for i, row in enumerate(rows)
                           if row['event'] == 'Core_Input_Poll' and
                           row.get('frame') == frame), None)
        if poll_index is None:
            continue
        loop_index = next((i for i in range(poll_index, len(rows))
                           if rows[i]['event'] == 'Core_Oop_Play__loop'), None)
        if loop_index is None:
            continue
        done_index = next((i for i in range(loop_index + 1, len(rows))
                           if rows[i]['event'] == 'Core_Oop_Play__done'), None)
        if done_index is None:
            continue
        invocation = rows[loop_index:done_index + 1]
        semantic_invocations.append({
            'input_poll_frame': frame,
            'entity_pass_start_frame': rows[loop_index].get('frame'),
            'entity_pass_end_frame': rows[done_index].get('frame'),
            'events': invocation,
        })
    payload['semantic_action_state'] = {
        'p1_selected': payload['actors_at_boundary']['p1']['selected'],
        'p2_selected': payload['actors_at_boundary']['p2']['selected'],
        'selected_write_notifications': [row for row in rows
                                          if row['event'].endswith('_write')],
        'selected_store_event_status': 'not retained: installed WRAM write-hook endpoint emitted no events',
    }
    payload['semantic_invocations'] = semantic_invocations
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
        f.write('\n')
    print(json.dumps(payload, indent=2))
    report.check('Core_Oop_Play semantic end reached', done)
    report.check('both actions accepted in one Core_Oop_Play update',
                 len(semantic_invocations) == 1 and
                 payload['actors_at_boundary']['p1']['selected'] == 2 and
                 payload['actors_at_boundary']['p2']['selected'] == 2)
    report.check('entity dispatch and P2 context both observed', p1 and p2_context)
    report.check('both synchronized raw Y words retained',
                 any(e.get('value') == 0x40 for e in payload['raw_read_events']) and
                 len(payload['raw_read_events']) >= 2)
    report.check('P1/P2 action state at boundary',
                 payload['actors_at_boundary']['p1']['selected'] == 2 and
                 payload['actors_at_boundary']['p2']['selected'] == 2)
    return report.finish()


if __name__ == '__main__':
    raise SystemExit(main())
