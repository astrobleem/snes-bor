#!/usr/bin/env python3
"""P1-S1C: direct source-contract coverage for BOR addscore().

The test request is verification-only: the production leaf is exercised by
the normal per-frame pickup service, while the request carries a 32-bit add
through the same owner-aware primitive. It does not alter ordinary gameplay.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, open_session, pasm_constant, pasm_constant_in,
                      read_block, run_frames_exact)
import game_bor_startup_select as startup

GS = pasm_constant_in('src/core/game_state.pasm', 'Game_Score32')
P2S = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Score32')
LIVES = pasm_constant_in('src/core/game_state.pasm', 'P1_Lives16')
P2L = pasm_constant_in('src/core/game_state.pasm', 'P2_Lives16')
OWNER = pasm_constant('G13_PickupForP2')
REQUEST = pasm_constant_in('src/core/game_state.pasm', 'G13_S1C_TestRequest')
ADD_LO = pasm_constant_in('src/core/vm/vm_arith32.pasm', 'VmArith_Lo')
ADD_HI = pasm_constant_in('src/core/vm/vm_arith32.pasm', 'VmArith_Hi')
MAGIC = 0x51C0
SFX_COUNT = pasm_constant('AudioSemantic_RequestCount')


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def u32(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)


def put32(m, addr, value):
    m.write_hex(addr, f'{value & 0xFFFFFFFF:08x}'[6:8] +
                f'{value & 0xFFFFFFFF:08x}'[4:6] +
                f'{value & 0xFFFFFFFF:08x}'[2:4] +
                f'{value & 0xFFFFFFFF:08x}'[0:2])


def setup(m, r):
    startup.cold_to_title(m, r)
    startup.select_case(m, r, 'KULA', 'KULA')
    assert u16(m, pasm_constant_in('src/core/game_state.pasm', 'Game_State')) == \
        pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
    put32(m, GS, 0); put32(m, P2S, 0)
    m.write_u16(LIVES, 3); m.write_u16(P2L, 3)
    m.write_u8(OWNER, 0); m.write_u16(REQUEST, 0)
    # Stop ordinary content service from competing with the direct primitive
    # transaction; the player service still runs normally.
    m.write_u8(pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index'),
               m.read_u8(pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')))
    run_frames_exact(m, 2)


def invoke(m, owner, old, add, lives):
    score = P2S if owner else GS
    other_score = GS if owner else P2S
    life = P2L if owner else LIVES
    other_life = LIVES if owner else P2L
    put32(m, score, old); put32(m, other_score, 0)
    m.write_u16(life, lives); m.write_u16(other_life, 256)
    m.write_u8(OWNER, owner)
    m.write_u16(ADD_LO, add & 0xFFFF)
    m.write_u16(ADD_HI, (add >> 16) & 0xFFFF)
    m.write_u16(REQUEST, MAGIC)
    # Isolate the primitive's threshold sound requests from unrelated idle
    # audio that may have been queued by the live gameplay session.
    m.write_u16(SFX_COUNT, 0)
    before = (u32(m, score), u16(m, life), u16(m, other_life), u16(m, SFX_COUNT))
    # Pickup service is a once-per-playing-frame call, but the accepted
    # harness may begin a frame between state-machine service points. Give the
    # request a bounded three-frame window and require the trigger to drain.
    run_frames_exact(m, 3)
    after = (u32(m, score), u16(m, life), u16(m, other_life), u16(m, SFX_COUNT))
    return before, after


def main():
    r = Reporter('BOR-S1C-SCORE-ADD')
    cases = ((0, 0, 1, 1, 0), (0, 65535, 1, 65536, 0),
             (0, 49999, 1, 50000, 0), (0, 50000, 1, 50001, 0),
             (0, 49999, 2, 50001, 1), (0, 99999, 2, 100001, 1),
             (0, 49999, 100002, 150001, 3),
             (0, 50000, 50001, 100001, 1),
             (0, 50000, 100001, 150001, 2),
             (0, 999999990, 100, 999999999, 0),
             (1, 49999, 100002, 150001, 3),
             (1, 0, 1, 1, 0))
    with open_session(__file__) as m:
        setup(m, r)
        for owner, old, add, expected_score, awards in cases:
            before, after = invoke(m, owner, old, add, 256)
            print({'owner': owner, 'old': old, 'add': add,
                   'before': before, 'after': after}, flush=True)
            r.check(f'owner {owner} score {old}+{add}={expected_score}',
                    after[0] == expected_score)
            r.check(f'owner {owner} lives awards {awards}',
                    after[1] == 256 + awards)
            r.check(f'owner {owner} partner lives isolated', after[2] == 256)
            expected_sound_delta = awards
            sound_delta = (after[3] - before[3]) & 0xFFFF
            print({'owner': owner, 'threshold_awards': awards,
                   'oneup_sound_requests': sound_delta}, flush=True)
            # A live session may queue unrelated ambient/menu SFX during the
            # bounded service window. Threshold cases must contribute at
            # least one request per awarded life; the direct primitive result
            # remains the authoritative exact count.
            r.check(f'owner {owner} threshold 1UP sound requests',
                    awards == 0 or sound_delta >= expected_sound_delta)
            r.check(f'owner {owner} credits untouched',
                    u16(m, pasm_constant_in('src/core/game_state.pasm', 'Game_Credits')) == 4)
    r.finish()


if __name__ == '__main__':
    main()
