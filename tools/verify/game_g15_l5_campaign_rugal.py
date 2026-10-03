#!/usr/bin/env python3
"""Focused G15 L5 proof: typed BOR stage/scene handoff through Rugal."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, exact_input_edge, open_session, pasm_constant, pasm_constant_in
from game_g15_2easy import poll_until, u8, u16
import game_bor_startup_select as startup

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PREV = pasm_constant_in('src/core/game_state.pasm', 'Game_StatePrev')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STATE_SCENE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_SCENE_FRAME')
GAME_STATE_TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
GAME_STATE_STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
CAMPAIGN_ID = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
STAGE_LOAD_PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
SCORE = pasm_constant_in('src/core/game_state.pasm', 'Game_Score32')
P1_LIVES = pasm_constant_in('src/core/game_state.pasm', 'P1_Lives16')
P2_LIVES = pasm_constant_in('src/core/game_state.pasm', 'P2_Lives16')
CREDITS = pasm_constant_in('src/core/game_state.pasm', 'Game_Credits')
RESOLVED_KIND = pasm_constant('Game_Campaign_ResolvedKind')
RESOLVED_VALUE = pasm_constant('Game_Campaign_ResolvedValue')
ADVANCES = pasm_constant('Game_Campaign_AdvanceCount')
ENDS = pasm_constant('Game_Campaign_EndCount')
SCENE_ACTIVE = pasm_constant('SceneVideo_TestActive')
SCENE_SKIP = pasm_constant('SceneVideo_PlaySkipCount')
SCENE_SWAPS = pasm_constant('SceneVideo_PlaySwaps')
SCENE_AUDIO_TRACK = pasm_constant('Music_LastTrack')
SCENE_AUDIO_REPEAT = pasm_constant('SceneVideo_PlayAudioRepeat')
SCENE_LATE = pasm_constant('SceneVideo_PlayLateCount')
SCENE_RETRIES = pasm_constant('SceneVideo_PlayDmaRetries')
SCENE_PRESENTED = pasm_constant('SceneVideo_PlayPresented')
SCENE_COMPLETION = pasm_constant('SceneVideo_PlayCompletion')
SCENE_CONTINUATION = pasm_constant('SceneVideo_Continuation')
SCENE_ID = pasm_constant('SceneVideo_RequestedSceneId')
SCENE_RUGAL = pasm_constant_in('src/generated/scene_video_meta.pasm', 'SceneVideo_Record0_SceneId')
BOR = 0
STAGE_6BEASY = 20


def snapshot(m):
    return (bytes(m.read_memory('snesMemory', SCORE, 32)[:4]),
            u16(m, P1_LIVES), u16(m, P2_LIVES), u8(m, CREDITS))


def setup_stage_clear(m, ordinal, stage):
    m.write_u8(CAMPAIGN_ID, BOR)
    m.write_u8(CAMPAIGN_ORDINAL, ordinal)
    m.write_u16(STAGE_INDEX, stage)
    m.write_u8(STAGE_LOAD_PENDING, 1)
    m.write_u16(GAME_STATE, GAME_STATE_STAGECLEAR)


def main():
    r = Reporter('G15-BATCH-L5-CAMPAIGN-RUGAL', kind='GATE')
    typed = build_rom.CAMPAIGN_ENTRY_MAPS['BOR_ORIGINAL']
    r.check('generated BOR campaign has 13 stages plus Rugal scene',
            len(typed) == 14 and typed[11][0] == 'stage'
            and typed[12][0] == 'stage' and typed[13] == ('scene', SCENE_RUGAL, 'RUGAL'))
    r.check('scene metadata exposes the generated Rugal ID', SCENE_RUGAL == 1)
    r.check('selection roster remains 13 and actor capacity six',
            build_rom.PLAYABLE_ROSTER_COUNT == 13 and pasm_constant('CHARACTER_ACTOR_COUNT') == 6)

    with open_session(__file__, boot_wait=2.0) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        before = snapshot(m)
        setup_stage_clear(m, 12, STAGE_6BEASY)
        entered = poll_until(m, lambda s: u16(s, GAME_STATE) == GAME_STATE_SCENE
                             and u8(s, CAMPAIGN_ORDINAL) == 13
                             and u8(s, SCENE_ACTIVE) == 0xA5,
                             max_frames=900, step=1)
        if not entered:
            print('natural entry diagnostic:', {
                'state': u16(m, GAME_STATE), 'prev': u16(m, GAME_STATE_PREV),
                'ordinal': u8(m, CAMPAIGN_ORDINAL), 'stage': u16(m, STAGE_INDEX),
                'kind': u8(m, RESOLVED_KIND), 'value': u8(m, RESOLVED_VALUE),
                'request': u16(m, pasm_constant('SceneVideo_TestRequest')),
                'active': u8(m, SCENE_ACTIVE), 'error': u8(m, pasm_constant('SceneVideo_TestError')),
                'handler': u16(m, pasm_constant('SceneVideo_TestHandlerEntries'))}, flush=True)
        r.check('6BEASY stage-clear resolves logical ordinal 12 -> 13', entered)
        r.check('ordinal 13 is SCENE/Rugal, not a physical stage',
                entered and u8(m, RESOLVED_KIND) == 1 and u8(m, RESOLVED_VALUE) == SCENE_RUGAL
                and u16(m, STAGE_INDEX) == STAGE_6BEASY)
        r.check('campaign scene request enters Rugal with audio mapping',
                entered and u8(m, SCENE_ID) == SCENE_RUGAL
                and u8(m, SCENE_AUDIO_TRACK) == 6 and u8(m, SCENE_AUDIO_REPEAT) == 0)
        natural = poll_until(m, lambda s: u16(s, GAME_STATE) == GAME_STATE_TITLE
                              and u8(s, CAMPAIGN_ORDINAL) == 13,
                              max_frames=1700, step=1)
        r.check('natural Rugal completion advances beyond scene to campaign end/TITLE',
                natural and u16(m, ENDS) >= 1 and u16(m, GAME_STATE_PREV) == GAME_STATE_TITLE)
        r.check('natural playback retained L4 frame proof',
                u16(m, SCENE_PRESENTED) == 126 and u16(m, SCENE_LATE) == 0
                and u16(m, SCENE_RETRIES) == 0 and u16(m, SCENE_COMPLETION) == 1)
        r.check('campaign scene leaves score/lives/credits unchanged', snapshot(m) == before)

    with open_session(__file__, boot_wait=2.0) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        before = snapshot(m)
        setup_stage_clear(m, 12, STAGE_6BEASY)
        active = poll_until(m, lambda s: u16(s, GAME_STATE) == GAME_STATE_SCENE
                            and u8(s, SCENE_ACTIVE) == 0xA5,
                            max_frames=900, step=1)
        m.run_frames(20)
        swaps = u16(m, SCENE_SWAPS)
        exact_input_edge(m, m.BTN_A, 1)
        skipped = poll_until(m, lambda s: u16(s, GAME_STATE) == GAME_STATE_TITLE,
                             max_frames=180, step=1)
        r.check('campaign Rugal skip uses real input and reaches TITLE', active and skipped
                and u16(m, SCENE_SKIP) == 1 and u16(m, ENDS) >= 1)
        r.check('skip has no post-cleanup scene swap and preserves state',
                u16(m, SCENE_SWAPS) == swaps and snapshot(m) == before)

    with open_session(__file__, boot_wait=2.0) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        setup_stage_clear(m, 11, 19)
        stage_transition = poll_until(
            m, lambda s: u16(s, GAME_STATE) == GAME_STATE_PLAYING
            and u8(s, CAMPAIGN_ORDINAL) == 12 and u16(s, STAGE_INDEX) == 20,
            max_frames=900, step=1)
        if not stage_transition:
            print('stage neighbor diagnostic:', {
                'state': u16(m, GAME_STATE), 'prev': u16(m, GAME_STATE_PREV),
                'ordinal': u8(m, CAMPAIGN_ORDINAL), 'stage': u16(m, STAGE_INDEX),
                'kind': u8(m, RESOLVED_KIND), 'value': u8(m, RESOLVED_VALUE)}, flush=True)
        r.check('neighbor BOR stage->stage 6AEASY -> 6BEASY remains intact',
                stage_transition and u8(m, RESOLVED_KIND) == 0
                and u8(m, RESOLVED_VALUE) == 20)
    r.finish()


if __name__ == '__main__':
    main()
