import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, read_block, pasm_constant, pasm_constant_in
from game_g4_transition import ENTITY_BASES, CHAR_HP, PLAYER_INVULN_FRAMES, SPAWN_INDEX, SPAWN_COUNT_ADDR, GAME_STAGE_INDEX, GAME_STATE, STAGE_CLEARED, STAGE_TRUE_MAX_X, SCREEN_POS_X, G13_MODE

def byte(m, a): return read_block(m, a, 32)[0]
def word(m, a):
    b = read_block(m, a, 32)
    return b[0] | (b[1] << 8)

def main():
    with open_session(__file__, boot_wait=2.0) as m:
        m.reset_emulator(); m.run_frames(60); m.pause()
        boot = word(m, GAME_STAGE_INDEX)
        count = byte(m, SPAWN_COUNT_ADDR)
        m.write_u8(SPAWN_INDEX, count)
        for base in ENTITY_BASES[1:]: m.write_u8(base + CHAR_HP, 0)
        cleared = False
        for _ in range(240):
            m.run_frames(1)
            if byte(m, STAGE_CLEARED): cleared = True; break
        m.pause()
        true_max = word(m, STAGE_TRUE_MAX_X)
        m.write_u8(SCREEN_POS_X, true_max & 255); m.write_u8(SCREEN_POS_X + 1, true_max >> 8)
        print(f'fixture boot_stage={boot} cleared={int(cleared)} stage={word(m,GAME_STAGE_INDEX)} state={byte(m,GAME_STATE)}')
        rows=[]
        pending_addr = 0x7E275D
        for i in range(20):
            m.run_frames(30)
            m.pause()
            rows.append((i+1, byte(m,GAME_STATE), byte(m,pending_addr), word(m,GAME_STAGE_INDEX), byte(m,G13_MODE)))
        m.pause()
        print('first=' + repr(rows[:10]))
        print('last=' + repr(rows[-10:]))
        print('playing_frames=' + repr([r for r in rows if r[1] == 0][:10]))
        print('unique_states=' + repr(sorted(set(r[1] for r in rows))))
if __name__ == '__main__': main()
