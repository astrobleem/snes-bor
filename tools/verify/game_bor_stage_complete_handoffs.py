#!/usr/bin/env python3
"""Small BOR completion-to-scene ordering checks.

The stage-clear edge is accelerated at its already-authoritative handoff
precondition; the completion presenter itself, resolver, and scene request
run on real emulator frames.  No scene/video body is replayed here.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant_in
from game_g15_2easy import poll_until, u8, u16
import game_bor_startup_select as startup

STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
SCENE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_SCENE_FRAME')
CAMPAIGN = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
STAGE = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
COMPLETE_ACTIVE = pasm_constant_in('src/main.pasm', 'StageComplete_Active')
ACTIVE = pasm_constant_in('src/main.pasm', 'SceneVideo_TestActive')
SCENE_ID = pasm_constant_in('src/main.pasm', 'SceneVideo_RequestedSceneId')
MUSIC_STATE = pasm_constant_in('src/main.pasm', 'Music_PlayState')


def check(r, stage, ordinal, scene_id, label):
    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(30)
        m.write_u8(CAMPAIGN, 0)
        m.write_u8(ORDINAL, ordinal)
        m.write_u16(STAGE, stage)
        m.write_u8(PENDING, 1)
        m.write_u16(STATE, STAGECLEAR)
        entered = poll_until(m, lambda s: u16(s, STATE) == SCENE and
                             u8(s, SCENE_ID) == scene_id and u8(s, ACTIVE) == 0xA5,
                             max_frames=900)
        if not entered:
            print(f'{label} diagnostic:', {'state': hex(u16(m, STATE)),
                  'ordinal': u8(m, ORDINAL), 'stage': u16(m, STAGE),
                  'active': u8(m, ACTIVE), 'scene': u8(m, SCENE_ID),
                  'pending': u8(m, PENDING)}, flush=True)
        r.check(f'{label}: completion finishes before scene starts', entered)
        r.check(f'{label}: scene remains after completion ordering',
                entered and u8(m, ORDINAL) == ordinal + 1 and
                u16(m, STAGE) == stage and u8(m, SCENE_ID) == scene_id)
        if entered:
            print(f'{label} result:', {'ordinal': u8(m, ORDINAL),
                  'stage': u16(m, STAGE), 'scene': u8(m, SCENE_ID),
                  'music_state': u8(m, MUSIC_STATE)}, flush=True)


def main():
    r = Reporter('BOR-STAGE-COMPLETE-HANDOFFS', kind='GATE')
    check(r, 20, 12, 1, '6BEASY -> RUGAL')
    check(r, 21, 14, 2, '6CEASY -> ENDING')
    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
