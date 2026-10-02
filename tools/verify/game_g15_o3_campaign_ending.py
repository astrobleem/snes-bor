#!/usr/bin/env python3
"""Focused O3 proof: real 6CEASY stage-clear -> BOR ENDING scene."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, exact_input_edge, open_session, pasm_constant, pasm_constant_in
from game_g15_2easy import poll_until, u8, u16
import game_bor_startup_select as startup

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402

STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
STATE_PREV = pasm_constant_in('src/core/game_state.pasm', 'Game_StatePrev')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
SCENE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_SCENE_FRAME')
STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
CAMPAIGN = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
STAGE = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
REQUEST = pasm_constant_in('src/main.pasm', 'SceneVideo_TestRequest')
PROBE = pasm_constant_in('src/main.pasm', 'SceneVideo_MsuDmaProbe')
RESOLVED_KIND = pasm_constant('Game_Campaign_ResolvedKind')
RESOLVED_VALUE = pasm_constant('Game_Campaign_ResolvedValue')
END_COUNT = pasm_constant('Game_Campaign_EndCount')
SCENE_ID = pasm_constant('SceneVideo_RequestedSceneId')
SCENE_ACTIVE = pasm_constant('SceneVideo_TestActive')
SCENE_CONT = pasm_constant('SceneVideo_Continuation')
SCENE_TRACK = pasm_constant('Music_LastTrack')
SCENE_REPEAT = pasm_constant('SceneVideo_PlayAudioRepeat')
SCENE_PRESENTED = pasm_constant('SceneVideo_PlayPresented')
SCENE_TRANSITIONS = pasm_constant('SceneVideo_SequenceTransitions')
SCENE_LATE = pasm_constant('SceneVideo_PlayLateCount')
SCENE_RETRIES = pasm_constant('SceneVideo_PlayDmaRetries')
SCENE_COMPLETE = pasm_constant('SceneVideo_PlayCompletion')
SCENE_SKIP = pasm_constant('SceneVideo_PlaySkipCount')
SCENE_SKIP_SWAPS = pasm_constant('SceneVideo_PlaySkipSwaps')
SCENE_SWAPS = pasm_constant('SceneVideo_PlaySwaps')
SCENE_ENDING = pasm_constant_in('src/generated/scene_sequence_meta.pasm', 'SceneSequence_Ending')
MUSIC_SCENE = pasm_constant('MUSIC_TRANSITION_SCENE')
LAST_TRANSITION = pasm_constant('Music_LastTransition')
SCORE = pasm_constant_in('src/core/game_state.pasm', 'Game_Score32')
P1_LIVES = pasm_constant_in('src/core/game_state.pasm', 'P1_Lives16')
P2_LIVES = pasm_constant_in('src/core/game_state.pasm', 'P2_Lives16')
CREDITS = pasm_constant_in('src/core/game_state.pasm', 'Game_Credits')


def snapshot(m):
    return (bytes(m.read_memory('snesMemory', SCORE, 32)[:4]),
            u16(m, P1_LIVES), u16(m, P2_LIVES), u8(m, CREDITS))


def setup_6ceasy_clear(m):
    # Establish the same clean scene-test seam as the direct O2 gate while
    # still entering through the real stage-clear dispatcher below.
    m.write_u16(REQUEST, 0)
    m.write_u8(PROBE, 0)
    m.write_u8(SCENE_ACTIVE, 0)
    m.write_u8(CAMPAIGN, 0)
    m.write_u8(ORDINAL, 14)
    m.write_u16(STAGE, 21)
    m.write_u8(PENDING, 1)
    m.write_u16(STATE, STAGECLEAR)


def reach_ending(m):
    setup_6ceasy_clear(m)
    return poll_until(m, lambda s: u16(s, STATE) == SCENE
                      and u8(s, ORDINAL) == 15
                      and u16(s, STAGE) == 21
                      and u8(s, SCENE_ID) == SCENE_ENDING
                      and u8(s, SCENE_ACTIVE) == 0xA5,
                      max_frames=900, step=1)


def source_config_checks(r):
    entries = build_rom.CAMPAIGN_ENTRY_MAPS['BOR_ORIGINAL']
    r.check('generated BOR campaign has 16 entries', len(entries) == 16)
    r.check('ordinal 13 is Rugal scene', entries[13] == ('scene', 1, 'RUGAL'))
    r.check('ordinal 14 is 6CEASY stage 21', entries[14] == ('stage', 21, r'DATA\EASY\6CEASY.TXT'))
    r.check('ordinal 15 is ENDING scene 2', entries[15] == ('scene', 2, 'ENDING'))
    r.check('ENDING scene ID is generated', SCENE_ENDING == 2)
    r.check('ENDING is the current BOR campaign end', len(entries) == 16 and entries[-1][0] == 'scene')


def natural(r):
    with open_session(__file__, boot_wait=2.0) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        before = snapshot(m)
        entered = reach_ending(m)
        r.check('6CEASY clear enters ENDING without TITLE', entered and u16(m, STATE) == SCENE)
        r.check('typed dispatch selects ENDING scene 2 and keeps stage 21',
                entered and u8(m, RESOLVED_KIND) == 1 and u8(m, RESOLVED_VALUE) == 2
                and u16(m, STAGE) == 21 and u8(m, SCENE_CONT) == 1)
        r.check('6CEASY -> ENDING selects TIME repeat-on',
                entered and u8(m, SCENE_ID) == 2 and u8(m, SCENE_TRACK) == 13
                and u8(m, SCENE_REPEAT) == 1 and u8(m, SCENE_CONT) == 1
                and u8(m, LAST_TRANSITION) == MUSIC_SCENE)
        for _ in range(30):
            m.run_frames(240)
            if u16(m, STATE) == TITLE:
                break
        r.check('natural ENDING reaches TITLE through campaign end',
                u16(m, STATE) == TITLE and u8(m, ORDINAL) == 15 and u16(m, STAGE) == 21
                and u16(m, END_COUNT) >= 1)
        r.check('natural ENDING playback remains complete',
                u16(m, SCENE_PRESENTED) == 1997 and u16(m, SCENE_TRANSITIONS) == 4
                and u16(m, SCENE_LATE) == 0 and u16(m, SCENE_RETRIES) == 0
                and u16(m, SCENE_COMPLETE) == 1 and u8(m, SCENE_SKIP) == 0)
        r.check('ENDING scene preserves score/lives/credits', snapshot(m) == before)


def skip(r):
    with open_session(__file__, boot_wait=2.0) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        before = snapshot(m)
        entered = reach_ending(m)
        for _ in range(20):
            m.run_frames(1)
            if u16(m, SCENE_PRESENTED) >= 20:
                break
        before_swaps = u16(m, SCENE_SWAPS)
        exact_input_edge(m, m.BTN_A, 1, port=0)
        skipped = poll_until(m, lambda s: u16(s, STATE) == TITLE,
                             max_frames=180, step=1)
        r.check('real ENDING skip reaches campaign end/TITLE',
                entered and skipped and u8(m, SCENE_SKIP) == 1
                and u8(m, SCENE_ID) == 2 and u8(m, SCENE_CONT) == 1)
        r.check('skip preserves stage index and has no later scene swap',
                u16(m, STAGE) == 21 and u16(m, SCENE_SKIP_SWAPS) == u16(m, SCENE_SWAPS)
                and u16(m, SCENE_SWAPS) >= before_swaps)
        r.check('skip preserves score/lives/credits', snapshot(m) == before)


def main():
    r = Reporter('G15-O3-BOR-ENDING-CAMPAIGN', kind='GATE')
    source_config_checks(r)
    natural(r)
    skip(r)
    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
