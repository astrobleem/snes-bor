#!/usr/bin/env python3
"""Narrow G15 L5 regression probe: TMNT typed STAGE -> STAGE dispatch.

This deliberately seeds an already-active ordinary TMNT stage.  It does not
walk the stale player-facing TMNT startup fixture; the state-clear latch is
then consumed by the normal Game_State_Play stage-clear path.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant, pasm_constant_in, poll_until

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STATE_STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
CAMPAIGN_ID = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
STAGE_CLEARED = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
STAGE_LOAD_PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
RESOLVED_KIND = pasm_constant('Game_Campaign_ResolvedKind')
RESOLVED_VALUE = pasm_constant('Game_Campaign_ResolvedValue')
ADVANCES = pasm_constant('Game_Campaign_AdvanceCount')
SCENE_REQUEST = pasm_constant('SceneVideo_TestRequest')
SCENE_ACTIVE = pasm_constant('SceneVideo_TestActive')
SCENE_AUDIO_STARTS = pasm_constant('SceneVideo_PlayAudioStartCount')
MUSIC_TRACK = pasm_constant('Music_LastTrack')
MUSIC_TRANSITION = pasm_constant('Music_LastTransition')

CAMPAIGN_TMNT = pasm_constant_in('src/core/game_state.pasm', 'CAMPAIGN_TMNT')
START_ORDINAL = 0
START_STAGE = 6       # Campaign_Tmnt_EntryValues[0] = sewer0
EXPECTED_ORDINAL = 1
EXPECTED_STAGE = 7    # Campaign_Tmnt_EntryValues[1] = streets2
CAMPAIGN_ENTRY_STAGE = pasm_constant_in('tools/audio/campaign_config.pasm', 'CAMPAIGN_ENTRY_STAGE')
MUSIC_TRANSITION_STAGE = pasm_constant('MUSIC_TRANSITION_STAGE')


def generated_stage_track(stage):
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        'tools', 'audio', 'audio_music_ids.pasm')
    previous = ''
    for line in open(path, encoding='utf-8'):
        if line.startswith('    .db ') and 'Music_StageTracks' in previous:
            values = [int(value.strip()) for value in line[8:].split(',')]
            return values[stage]
        previous = line.strip()
    raise RuntimeError('Music_StageTracks not found')


def u8(m, addr):
    return m.read_memory('snesMemory', addr, 32)[0]


def u16(m, addr):
    b = m.read_memory('snesMemory', addr, 32)
    return b[0] | (b[1] << 8)


def main():
    r = Reporter('G15-L5-TMNT-TYPED-RESOLVER', kind='GATE')
    r.check('TMNT adjacent entries are both typed STAGE entries',
            CAMPAIGN_ENTRY_STAGE == 0 and START_STAGE == 6 and EXPECTED_STAGE == 7)

    with open_session(__file__, boot_wait=2.0) as m:
        m.reset_emulator()
        m.run_frames(60)
        m.pause()

        # Capture the non-scene baseline before the real stage-clear handoff.
        scene_request_before = u16(m, SCENE_REQUEST)
        scene_active_before = u8(m, SCENE_ACTIVE)
        scene_audio_before = u16(m, SCENE_AUDIO_STARTS)

        # Minimum active-stage/ordinary-clear state.  Game_State_Play owns the
        # resolver call, typed dispatch, Stage_Load, and return to PLAYING.
        m.write_u8(CAMPAIGN_ID, CAMPAIGN_TMNT)
        m.write_u8(CAMPAIGN_ORDINAL, START_ORDINAL)
        m.write_u16(STAGE_INDEX, START_STAGE)
        m.write_u8(STAGE_CLEARED, 1)
        m.write_u8(STAGE_LOAD_PENDING, 1)
        m.write_u16(GAME_STATE, GAME_STATE_STAGECLEAR)

        settled = poll_until(
            m,
            lambda s: u8(s, CAMPAIGN_ORDINAL) == EXPECTED_ORDINAL
            and u16(s, STAGE_INDEX) == EXPECTED_STAGE
            and u16(s, GAME_STATE) == GAME_STATE_PLAYING,
            max_frames=900,
            step=1,
        )
        m.pause()

        r.check('real stage-clear handoff reaches next TMNT stage', settled)
        r.check('current and next entries dispatch STAGE -> STAGE',
                settled and u8(m, RESOLVED_KIND) == CAMPAIGN_ENTRY_STAGE
                and u8(m, RESOLVED_VALUE) == EXPECTED_STAGE)
        r.check('TMNT ordinal increments exactly once',
                settled and u8(m, CAMPAIGN_ORDINAL) == EXPECTED_ORDINAL
                and u16(m, ADVANCES) >= 1)
        r.check('Game_StageIndex is the expected physical next stage',
                settled and u16(m, STAGE_INDEX) == EXPECTED_STAGE)
        r.check('Stage_Load returns to ordinary PLAYING state',
                settled and u16(m, GAME_STATE) == GAME_STATE_PLAYING)
        r.check('no SceneVideo request or activity occurred',
                u16(m, SCENE_REQUEST) == scene_request_before
                and u8(m, SCENE_ACTIVE) == scene_active_before
                and u16(m, SCENE_AUDIO_STARTS) == scene_audio_before)
        r.check('TMNT stage music selected for the loaded stage',
                u8(m, MUSIC_TRANSITION) == MUSIC_TRANSITION_STAGE
                and u8(m, MUSIC_TRACK) == generated_stage_track(EXPECTED_STAGE))

    r.finish()


if __name__ == '__main__':
    main()
