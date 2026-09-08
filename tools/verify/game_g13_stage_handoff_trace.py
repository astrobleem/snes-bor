#!/usr/bin/env python3
"""Verifier-only semantic trace for one G4 stage-clear handoff."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block
from game_g4_transition import (ENTITY_BASES, CHAR_HP, CHAR_INPUT_DRIVEN,
                                 CHAR_INPUT_DRIVEN_AI, SPAWN_INDEX,
                                 SPAWN_COUNT_ADDR, STAGE_CLEARED,
                                 STAGE_TRUE_MAX_X, GAME_STATE, G13_MODE,
                                 byte_at, word_at)
SYM = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src', 'main.sym')

def symbol(name):
    wanted = re.compile(r'^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+' + re.escape(name) + r'\s*$')
    with open(SYM, encoding='utf-8') as f:
        for line in f:
            hit = wanted.match(line.strip())
            if hit:
                return (int(hit.group(1), 16) << 16) | int(hit.group(2), 16)
    raise KeyError(name)

SCREEN_POS_X = 0x7E1601
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')

def main():
    out = {'events': [], 'states': []}
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        count = byte_at(m, SPAWN_COUNT_ADDR)
        m.write_u8(SPAWN_INDEX, count)
        for base in ENTITY_BASES[1:]:
            if byte_at(m, base + CHAR_INPUT_DRIVEN) == CHAR_INPUT_DRIVEN_AI:
                m.write_u8(base + CHAR_HP, 0)
        for _ in range(180):
            m.run_frames(1)
            if byte_at(m, STAGE_CLEARED):
                break
        m.pause()
        assert byte_at(m, STAGE_CLEARED) == 1
        target = word_at(m, STAGE_TRUE_MAX_X)
        m.write_u8(SCREEN_POS_X, target & 0xFF)
        m.write_u8(SCREEN_POS_X + 1, target >> 8)

        names = ['Game_State_Play__stageclear',
                 'Game_State_Play__after_stage_load',
                 'G13_EnsureP2AfterStage',
                 'G13_EnsureP2AfterStage__done',
                 'Game_State_Play__after_p2_restore',
                 'Game_State_Play__after_playing_store',
                 'Game_State_Play__stageclear_done',
                 'Game_State_Play__done']
        hooks = {n: m.add_exec_hook(symbol(n)) for n in names}
        for name in names:
            q = m.run_until(max_frames=120, hook_handle=hooks[name])
            row = {'name': name, 'run': q,
                   'state': word_at(m, GAME_STATE),
                   'pending': byte_at(m, PENDING),
                   'cleared': byte_at(m, STAGE_CLEARED),
                   'mode': byte_at(m, G13_MODE)}
            out['events'].append(row)
            if q.get('reason') != 'hookFired':
                break
            m.remove_hook(hooks[name])
        out['final'] = {'state': word_at(m, GAME_STATE),
                        'playing': PLAYING, 'stageclear': STAGECLEAR,
                        'pending': byte_at(m, PENDING)}
        for h in hooks.values():
            try: m.remove_hook(h)
            except Exception: pass
    print(json.dumps(out, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
