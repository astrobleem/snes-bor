#!/usr/bin/env python3
"""P1-S1D focused score-event contract gate.

Uses the normal BOR startup and the narrow verification-only event trigger to
exercise the production force*5 wrapper.  The trigger supplies a source force
without changing gameplay event data; item integration remains covered by the
existing G13 pickup gate.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant, pasm_constant_in, read_block, run_frames_exact
import game_bor_startup_select as startup

GS = pasm_constant_in('src/core/game_state.pasm', 'Game_Score32')
P2S = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Score32')
LIVES = pasm_constant_in('src/core/game_state.pasm', 'P1_Lives16')
P2L = pasm_constant_in('src/core/game_state.pasm', 'P2_Lives16')
OWNER = pasm_constant('G13_PickupForP2')
REQUEST = pasm_constant_in('src/core/game_state.pasm', 'G13_S1C_TestRequest')
FORCE = pasm_constant_in('src/core/game_state.pasm', 'G13_S1D_TestForce')
MAGIC = 0x51D0


def u16(m, address):
    b = read_block(m, address, 32)
    return b[0] | (b[1] << 8)


def u32(m, address):
    b = read_block(m, address, 32)
    return b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24


def put32(m, address, value):
    h = f'{value & 0xFFFFFFFF:08x}'
    m.write_hex(address, h[6:8] + h[4:6] + h[2:4] + h[0:2])


def invoke(m, owner, force):
    score = P2S if owner else GS
    life = P2L if owner else LIVES
    other_life = LIVES if owner else P2L
    put32(m, score, 0)
    put32(m, GS if owner else P2S, 0)
    m.write_u16(life, 256)
    m.write_u16(other_life, 256)
    m.write_u8(OWNER, owner)
    m.write_u16(FORCE, force)
    m.write_u16(REQUEST, MAGIC)
    run_frames_exact(m, 3)
    return u32(m, score), u16(m, life), u16(m, other_life)


def main():
    r = Reporter('BOR-S1D-SCORE-EVENTS')
    for owner, label in ((0, 'P1'), (1, 'P2')):
        for force, expected in ((1, 5), (10, 50)):
            with open_session(__file__) as m:
                startup.cold_to_title(m, r)
                startup.select_case(m, r, 'KULA', 'KULA')
                score, lives, partner_lives = invoke(m, owner, force)
                print({'owner': label, 'force': force, 'score_delta': score,
                       'lives': lives, 'partner_lives': partner_lives}, flush=True)
                r.check(f'{label} force {force} awards force*5', score == expected)
                r.check(f'{label} force {force} leaves owner lives unchanged', lives == 256)
                r.check(f'{label} force {force} leaves partner untouched', partner_lives == 256)
        # The production wrapper receives force, not the old kill boolean;
        # source-level shape check prevents the retired fixed kill path from
        # silently returning.
        with open('src/core/player2_context.pasm', encoding='utf-8') as f:
            source = f.read()
        r.check('production event wrapper is force-based',
                'source attack force to force*5' in source and
                'G13_Game_Score_Award__amount' in source)
        r.check('retired KILL_SCORE symbol absent from production',
                'KILL_SCORE' not in open('src/main.pasm', encoding='utf-8').read())
    r.finish()


if __name__ == '__main__':
    main()
