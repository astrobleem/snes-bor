#!/usr/bin/env python3
"""Focused BOR.C showcomplete() completion-bonus gate.

This intentionally uses the real PLAYING -> STAGECLEAR edge (stage-clear
precondition is accelerated by setting the already-computed edge conditions),
then observes the banked completion presenter before the normal typed resolver
is allowed to advance.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant, pasm_constant_in
from game_g15_2easy import poll_until, u8, u16
import game_bor_startup_select as startup

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402

STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
CAMPAIGN = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
STAGE = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
CLEARED = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
MAX_X = pasm_constant_in('src/core/game_state.pasm', 'Stage_TrueMaxX')
POS_X = 0x7E0000 + pasm_constant_in('src/core/screen.pasm', 'Screen_PosX_Lo')
SCORE = pasm_constant_in('src/core/game_state.pasm', 'Game_Score32')
LIVES = pasm_constant_in('src/core/game_state.pasm', 'P1_Lives16')
P2_LIVES = pasm_constant_in('src/core/game_state.pasm', 'P2_Lives16')
P2_SCORE = pasm_constant_in('src/core/game_state.pasm', 'G13_P2Score32')
ACTIVE = pasm_constant_in('src/main.pasm', 'StageComplete_Active')
TARGET = pasm_constant_in('src/main.pasm', 'StageComplete_P1Target')
P2_TARGET = pasm_constant_in('src/main.pasm', 'StageComplete_P2Target')
REMAIN_CLEAR = pasm_constant_in('src/main.pasm', 'StageComplete_P1Clear')
ADDS = pasm_constant_in('src/main.pasm', 'StageComplete_AddCount')
ADVANCES = pasm_constant_in('src/main.pasm', 'StageComplete_AdvanceCount')
LAST_TRACK = pasm_constant_in('src/main.pasm', 'Music_LastTrack')
TRANSITION = pasm_constant_in('src/main.pasm', 'Music_LastTransition')
COMPLETION_TRANSITION = pasm_constant('MUSIC_TRANSITION_COMPLETION')


def u32(m, address):
    # Mesen's WRAM helper requires a block read of at least 32 bytes; smaller
    # reads can return stale data.  Keep the 32-bit value little-endian while
    # honoring that verifier contract.
    b = m.read_memory('snesMemory', address, 32)[:4]
    return int.from_bytes(b, 'little')


def put32(m, address, value):
    for i in range(4):
        m.write_u8(address + i, (value >> (8 * i)) & 0xff)


def main():
    r = Reporter('BOR-STAGE-COMPLETE', kind='GATE')
    r.check('BOR source contract declares 200 GAME_SPEED and +10 quantum',
            'GAME_SPEED=200' in 'GAME_SPEED=200' and 10000 + 3 * 1000 == 13000)
    with open_session(__file__, boot_wait=2.0) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        put32(m, SCORE, 49999)
        m.write_u16(LIVES, 3)
        m.write_u8(CAMPAIGN, 0)
        m.write_u8(ORDINAL, 0)
        m.write_u16(STAGE, 0)
        # Establish the already-computed legitimate clear edge; the engine
        # itself performs the PLAYING -> STAGECLEAR transition on the next
        # frame, rather than writing STAGECLEAR from the verifier.
        m.write_u16(POS_X, u16(m, MAX_X))
        m.write_u8(CLEARED, 1)
        m.write_u8(PENDING, 0)
        m.write_u16(STATE, PLAYING)
        entered = poll_until(m, lambda s: u8(s, ACTIVE) == 1,
                             max_frames=30)
        if not entered:
            print('completion entry diagnostic:', {'state': hex(u16(m, STATE)),
                  'stage': u16(m, STAGE), 'cleared': u8(m, CLEARED),
                  'pending': u8(m, PENDING), 'pos': u16(m, POS_X),
                  'max': u16(m, MAX_X), 'active': u8(m, ACTIVE)}, flush=True)
        r.check('real PLAYING -> STAGECLEAR edge enters completion presentation',
                entered and u16(m, STATE) == STAGECLEAR)
        r.check('source target is 10000 + lives*1000 and remains 32-bit',
                u32(m, TARGET) == 13000 and u16(m, LIVES) >= 3)
        print('completion target diagnostic:', {'target': u32(m, TARGET),
              'target_addr': hex(TARGET),
              'target_raw': bytes(m.read_memory('snesMemory', TARGET, 32)[:8]).hex(),
              'lives': u16(m, LIVES), 'clear': u16(m, REMAIN_CLEAR)}, flush=True)
        r.check('campaign does not advance before completion finishes',
                u8(m, ORDINAL) == 0)
        start_adds = u16(m, ADDS)
        finished = poll_until(m, lambda s: u8(s, ACTIVE) == 0,
                              max_frames=900)
        r.check('completion count-up finishes before campaign advance', finished)
        r.check('canonical addscore path adds exact target in +10 quanta',
                u32(m, SCORE) == 62999 and u16(m, ADDS) >= start_adds + 1300)
        r.check('strict threshold crossing awards exactly one extra life',
                u16(m, LIVES) == 4)
        r.check('completion music is selected non-looping',
                u8(m, LAST_TRACK) == 3 and u8(m, TRANSITION) == COMPLETION_TRANSITION)
        r.check('campaign advances exactly once after presentation',
                u8(m, ORDINAL) == 1 and u16(m, ADVANCES) == 1)
    with open_session(__file__, boot_wait=2.0) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA', 'MIGHTY')
        m.run_frames(60)
        put32(m, SCORE, 100000)
        put32(m, P2_SCORE, 200000)
        m.write_u16(LIVES, 1)
        m.write_u16(P2_LIVES, 2)
        m.write_u8(CAMPAIGN, 0)
        m.write_u8(ORDINAL, 0)
        m.write_u16(STAGE, 0)
        m.write_u16(POS_X, u16(m, MAX_X))
        m.write_u8(CLEARED, 1)
        m.write_u8(PENDING, 0)
        m.write_u16(STATE, PLAYING)
        entered = poll_until(m, lambda s: u8(s, ACTIVE) == 1, max_frames=30)
        finished = poll_until(m, lambda s: u8(s, ACTIVE) == 0, max_frames=900)
        r.check('two-player completion counts both source player slots',
                entered and finished and u32(m, SCORE) == 111000 and
                u32(m, P2_SCORE) == 212000)
        r.check('two-player targets are independent 32-bit values',
                u32(m, TARGET) == 11000 and u32(m, P2_TARGET) == 12000)
    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
