#!/usr/bin/env python3
"""Verifier-only Phase5 lifecycle-state A/B diagnostic."""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, run_frames_exact

P1 = 0x7E0A00
ZP = pasm_constant('CHAR_ZP_LEN')
HP = pasm_constant('CHAR_HP')
ROLE = pasm_constant('CHAR_INPUT_DRIVEN')
SELECTED = pasm_constant('CHAR_SELECTED')
FRAME = pasm_constant('CHAR_FRAME_INDEX')
TICK = pasm_constant('CHAR_TICK_COUNTER')
HITSTUN = pasm_constant('CHAR_HIT_STUN')
STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
LIVES = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')
P2LIVES = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Lives')
P1INV = pasm_constant_in('src/core/game_state.pasm', 'Player_InvulnFrames')
P2INV = pasm_constant('G13_P2_InvulnFrames')
MODE = pasm_constant('G13_TwoPlayerEnabled')
OUT1 = pasm_constant('G13_P1Out')
OUT2 = pasm_constant('G13_P2Out')

def b(m, a):
    return read_block(m, a, 32)[0]

def actor(m, base):
    return {k: b(m, base + off) for k, off in
            (('hp', HP), ('role', ROLE), ('selected', SELECTED),
             ('frame', FRAME), ('tick', TICK), ('hitstun', HITSTUN))}

def sample(m):
    return {'mode': b(m, MODE), 'p1_out': b(m, OUT1), 'p2_out': b(m, OUT2),
            'state': b(m, STATE), 'lives': b(m, LIVES), 'p2_lives': b(m, P2LIVES),
            'p1_invuln': b(m, P1INV), 'p2_invuln': b(m, P2INV),
            'p1': actor(m, P1), 'slot1': actor(m, P1 + ZP),
            'slot1_frames': [], 'slot1_hitstun': []}

def main():
    result = {}
    with open_session(__file__) as m:
        m.reset_emulator()
        run_frames_exact(m, 60)
        m.pause()
        result['cold_boot'] = sample(m)
        for name, flags in (('untouched', None), ('p1_zero', (0, None)),
                            ('p2_zero', (None, 0)), ('both_zero', (0, 0))):
            if flags is not None:
                if flags[0] is not None: m.write_u8(OUT1, flags[0])
                if flags[1] is not None: m.write_u8(OUT2, flags[1])
            m.write_u8(OUT1, b(m, OUT1)); m.write_u8(OUT2, b(m, OUT2))
            row = sample(m)
            for _ in range(6):
                run_frames_exact(m, 48)
                row['slot1_frames'].append(b(m, P1 + ZP + FRAME))
                row['slot1_hitstun'].append(b(m, P1 + ZP + HITSTUN))
            result[name] = row
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
