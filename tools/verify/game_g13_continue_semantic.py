#!/usr/bin/env python3
"""Semantic Start-edge probes for the unpublished G13 lifecycle work.

This is a bounded evidence probe: controller poll and lifecycle branch hooks
are installed together, so the result is tied to the consuming service
invocation rather than a later PPU-frame snapshot.
"""
import sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from _harness import (open_session, pasm_constant, pasm_constant_in,
                      read_block, run_frames_exact, Reporter)
from game_g13_camera_pause import setup, P1, P2
from game_g13_two_player_input import neutral_joint

GS = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
PAUSED = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PAUSED')
HP = pasm_constant('CHAR_HP')
MODE = pasm_constant('G13_TwoPlayerEnabled')
P1OUT = pasm_constant('G13_P1Out')
P2OUT = pasm_constant('G13_P2Out')
P2LIVES = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Lives')
LIVES = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
ZP_LEN = pasm_constant('CHAR_ZP_LEN')

def u8(m, a): return read_block(m, a, 32)[0]
def u16(m, a):
    b = read_block(m, a, 32)
    return b[0] | (b[1] << 8)
def sym(n):
    for line in open('src/main.sym', encoding='utf-8'):
        p = line.split()
        if len(p) == 2 and p[1] == n:
            b, o = p[0].split(':')
            return int(b, 16) * 0x10000 + int(o, 16)
    raise KeyError(n)

def edge_probe(m, port, out_addr, hp_addr, lives_addr, out_value=1):
    # Establish the legal OUT state, then obtain an actual neutral poll.
    m.write_u8(out_addr, out_value); m.write_u8(hp_addr, 0 if out_value else 64); m.write_u8(lives_addr, 0 if out_value else 1)
    m.write_u8(GS, PLAYING)
    neutral_joint(m)
    before = {
        'raw_expected_api': 0, 'input_press': u16(m, 0x7E0410 if port == 0 else 0x7E0418),
        'input_trigger': u16(m, 0x7E0412 if port == 0 else 0x7E041A),
        'input_old': u16(m, 0x7E0414 if port == 0 else 0x7E041C),
    }
    names = ('Core_Input_Poll', 'Core_Input_Poll_P2', 'G13_HandleOutContinue',
             'G13_HandleOutContinue__yes', 'G13_HandleOutContinue__p2',
             'Game_State_Pause_CheckEntry', 'Game_State_Pause_CheckEntry__enter',
             'Game_State_Play__done')
    hooks = {m.add_exec_hook(sym(n)): n for n in names}
    m.hold_input(m.BTN_START, port=port)
    try:
        result = run_frames_exact(m, 3)
    finally:
        m.release_input(port=port)
    notes = m.drain_notifications()
    for h in hooks: m.remove_hook(h)
    events = [{'name': hooks[x['params']['handle']], 'frame': x['params'].get('frame')}
              for x in notes if x.get('method', '').endswith('hookFired')
              and x.get('params', {}).get('handle') in hooks]
    context = (0x7E0410 if port == 0 else 0x7E0418)
    after = {'raw_expected_api': m.BTN_START,
             'input_press': u16(m, context), 'input_trigger': u16(m, context + 2),
             'input_old': u16(m, context + 4), 'out': u8(m, out_addr),
             'hp': u8(m, hp_addr), 'lives': u8(m, lives_addr), 'state': u16(m, GS)}
    return {'port': port, 'neutral': before, 'set_input': result,
            'events': events, 'after': after}

def main():
    r = Reporter('G13-CONTINUE-SEMANTIC', kind='PROBE')
    with open_session(__file__) as m:
        setup(m)
        m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
        for slot in range(2, 6): m.write_u8(P1 + slot * ZP_LEN + HP, 0)
        m.write_u8(MODE, 1); m.write_u8(P1OUT, 0); m.write_u8(P2OUT, 1)
        m.write_u8(P1 + HP, 64)
        m.write_u8(LIVES, 1)
        p2 = edge_probe(m, 1, P2OUT, P2 + HP, P2LIVES)
        print('P2 OUT continue semantic:', p2, flush=True)
        m.write_u8(P1OUT, 0); m.write_u8(P2OUT, 0); m.write_u8(P1 + HP, 64); m.write_u8(P2 + HP, 64)
        m.write_u8(LIVES, 1); m.write_u8(P2LIVES, 1); m.write_u8(GS, PLAYING)
        p1 = edge_probe(m, 0, P1OUT, P1 + HP, LIVES, out_value=0)
        print('active P1 pause semantic:', p1, flush=True)
        r.check('P2 continue branch observed', any(e['name'] == 'G13_HandleOutContinue__yes' for e in p2['events']) and p2['after']['out'] == 0)
        r.check('active P1 pause branch observed', any(e['name'] == 'Game_State_Pause_CheckEntry__enter' for e in p1['events']) and p1['after']['state'] == PAUSED)
    r.finish()
if __name__ == '__main__': main()
