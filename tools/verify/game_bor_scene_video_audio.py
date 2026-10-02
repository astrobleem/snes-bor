#!/usr/bin/env python3
"""Focused G15 L4 proof for Rugal scene music and any-button skip."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, exact_input_edge, open_session, read_block, read_snes_bus_block, run_frames_exact, pasm_constant_in  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
INTRO = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_INTRO')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
REQ = pasm_constant_in('src/main.pasm', 'SceneVideo_TestRequest')
REQ_SEEN = pasm_constant_in('src/main.pasm', 'SceneVideo_TestRequestSeen')
REQ_CONSUMED = pasm_constant_in('src/main.pasm', 'SceneVideo_TestRequestConsumed')
ACTIVE = pasm_constant_in('src/main.pasm', 'SceneVideo_TestActive')
PRESENTED = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayPresented')
SWAPS = pasm_constant_in('src/main.pasm', 'SceneVideo_PlaySwaps')
LATE = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayLateCount')
RETRIES = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayDmaRetries')
COMPLETE = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayCompletion')
AUDIO_STARTS = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayAudioStartCount')
AUDIO_ENDED = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayAudioEnded')
AUDIO_STOPS = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayAudioStops')
AUDIO_REPEAT = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayAudioRepeat')
SKIP_PENDING = pasm_constant_in('src/main.pasm', 'SceneVideo_SkipPending')
INPUT_POLLS = pasm_constant_in('src/main.pasm', 'SceneVideo_InputPollCount')
LOAD_COUNT = pasm_constant_in('src/main.pasm', 'SceneVideo_LoadCount')
LOAD_START_NMI = pasm_constant_in('src/main.pasm', 'SceneVideo_LoadStartNmi')
LOAD_END_NMI = pasm_constant_in('src/main.pasm', 'SceneVideo_LoadEndNmi')
LOAD_CHECKPOINTS = pasm_constant_in('src/main.pasm', 'SceneVideo_LoadCheckpoints')
RAW_AT_SKIP = pasm_constant_in('src/main.pasm', 'SceneVideo_InputRawAtSkip')
PRESS_AT_SKIP = pasm_constant_in('src/main.pasm', 'SceneVideo_InputPressAtSkip')
TRIGGER_AT_SKIP = pasm_constant_in('src/main.pasm', 'SceneVideo_InputTriggerAtSkip')
SKIP_SWAPS = pasm_constant_in('src/main.pasm', 'SceneVideo_PlaySkipSwaps')
LAST_TRACK = pasm_constant_in('src/main.pasm', 'Music_LastTrack')
LAST_TRANSITION = pasm_constant_in('src/main.pasm', 'Music_LastTransition')
PLAY_STATE = pasm_constant_in('src/main.pasm', 'Music_PlayState')
INPUT_PRESS = pasm_constant_in('src/core/input.pasm', 'Input_press_Addr')
INPUT_TRIGGER = pasm_constant_in('src/core/input.pasm', 'Input_trigger_Addr')
INPUT_RAW = pasm_constant_in('src/core/input.pasm', 'Input_last_raw_Addr')
INPUT2_PRESS = pasm_constant_in('src/core/input.pasm', 'Input2_press_Addr')
INPUT2_TRIGGER = pasm_constant_in('src/core/input.pasm', 'Input2_trigger_Addr')
INPUT2_TRIGGER_AT_SKIP = pasm_constant_in('src/main.pasm', 'SceneVideo_Input2TriggerAtSkip')
SCENE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_SCENE_FRAME')
SCENE_TRACK = pasm_constant_in('tools/audio/audio_music_ids.pasm', 'Music_SceneTrack_RUGAL')
SCENE_TRANSITION = pasm_constant_in('src/main.pasm', 'MUSIC_TRANSITION_SCENE')


def u8(m, address):
    return read_block(m, address, 32)[0]


def u16(m, address):
    b = read_block(m, address, 32)
    return b[0] | b[1] << 8


def reset_fixture(m):
    m.reset_emulator()
    for address in (REQ, ACTIVE, AUDIO_ENDED, AUDIO_STOPS, AUDIO_REPEAT):
        m.write_u8(address, 0)
    for address in (PRESENTED, SWAPS, LATE, RETRIES, COMPLETE, AUDIO_STARTS):
        m.write_u16(address, 0)
    m.write_u8(PLAY_STATE, 0)
    m.write_u16(STATE, TITLE)
    m.write_u16(STATE + 2, TITLE)
    run_frames_exact(m, 180)


def input_sample(m):
    return {
        'raw': read_block(m, INPUT_RAW, 32)[:2],
        'press': read_block(m, INPUT_PRESS, 32)[:2],
        'trigger': read_block(m, INPUT_TRIGGER, 32)[:2],
    }


def start_scene(m):
    m.write_u16(REQ, 1)
    m.write_u16(STATE, INTRO)
    run_frames_exact(m, 12)


def main():
    r = Reporter('BOR-L4-RUGAL-SCENE-AUDIO-SKIP', kind='GATE')
    with open_session(__file__, boot_wait=2.0) as m:
        reset_fixture(m)
        # Establish the controller path before touching the scene state.
        m.hold_input(m.BTN_A, port=0)
        run_frames_exact(m, 2)
        pre_scene_input = input_sample(m)
        print('pre_scene_input:', {k: v.hex() for k, v in pre_scene_input.items()}, flush=True)
        r.check('pre-scene raw input observed', pre_scene_input['raw'] != b'\x00\x00')
        r.check('pre-scene button press observed', pre_scene_input['press'] != b'\x00\x00')
        r.check('pre-scene button edge observed', pre_scene_input['trigger'] != b'\x00\x00')
        m.release_input(port=0)
        run_frames_exact(m, 2)
        # Clear the controller edge and title/intro state before the actual
        # natural-path scene request; the control A/B must not become scene
        # input or an intro-advance trigger.
        reset_fixture(m)
        start_scene(m)
        print('natural_entry_state:', {'state': u16(m, STATE), 'active': u8(m, ACTIVE),
                                        'request': u16(m, REQ), 'seen': u16(m, REQ_SEEN), 'consumed': u16(m, REQ_CONSUMED),
                                        'error': u8(m, pasm_constant_in('src/main.pasm', 'SceneVideo_TestError')),
                                        'handler': u16(m, pasm_constant_in('src/main.pasm', 'SceneVideo_TestHandlerEntries'))}, flush=True)
        r.check('natural scene entered', u16(m, STATE) == SCENE)
        r.check('generated scene track selected', u8(m, LAST_TRACK) == SCENE_TRACK)
        r.check('scene transition telemetry', u8(m, LAST_TRANSITION) == SCENE_TRANSITION)
        r.check('scene audio started once', u16(m, AUDIO_STARTS) == 1)
        r.check('scene repeat is disabled', u8(m, AUDIO_REPEAT) == 0)
        r.check('frame zero started with scene', u16(m, PRESENTED) >= 1)
        run_frames_exact(m, 1700)
        r.check('natural playback completes', u16(m, COMPLETE) == 1 and u16(m, STATE) == TITLE)
        r.check('audio ended before video cleanup', u8(m, AUDIO_ENDED) == 1)
        r.check('audio did not restart', u16(m, AUDIO_STARTS) == 1)
        r.check('natural audio cleanup stopped playback', u8(m, PLAY_STATE) == 0 and u8(m, AUDIO_STOPS) == 1)
        r.check('video remained lossless with audio active',
                u16(m, PRESENTED) == 126 and u16(m, LATE) == 0 and u16(m, RETRIES) == 0)
        print('natural_audio_telemetry:', {
            'track': u8(m, LAST_TRACK), 'repeat': u8(m, AUDIO_REPEAT),
            'starts': u16(m, AUDIO_STARTS), 'ended': u8(m, AUDIO_ENDED),
            'presented': u16(m, PRESENTED), 'swaps': u16(m, SWAPS),
            'late': u16(m, LATE), 'retries': u16(m, RETRIES),
            'loads': u16(m, LOAD_COUNT), 'load_start_nmi': u16(m, LOAD_START_NMI),
            'load_end_nmi': u16(m, LOAD_END_NMI), 'polls': u16(m, INPUT_POLLS),
            'checkpoints': u16(m, LOAD_CHECKPOINTS),
            'state': u16(m, STATE)}, flush=True)

        reset_fixture(m)
        start_scene(m)
        print('early_entry_state:', {'state': u16(m, STATE), 'active': u8(m, ACTIVE),
                                     'request': u16(m, REQ), 'seen': u16(m, REQ_SEEN), 'consumed': u16(m, REQ_CONSUMED),
                                     'error': u8(m, pasm_constant_in('src/main.pasm', 'SceneVideo_TestError')),
                                     'handler': u16(m, pasm_constant_in('src/main.pasm', 'SceneVideo_TestHandlerEntries'))}, flush=True)
        run_frames_exact(m, 20)
        before_skip = u16(m, SWAPS)
        exact_input_edge(m, m.BTN_A, 2, port=0)
        in_scene = {
            'raw': u16(m, RAW_AT_SKIP), 'press': u16(m, PRESS_AT_SKIP),
            'trigger': u16(m, TRIGGER_AT_SKIP), 'polls': u16(m, INPUT_POLLS),
            'checkpoints': u16(m, LOAD_CHECKPOINTS),
            'p2trigger': u16(m, INPUT2_TRIGGER_AT_SKIP),
        }
        print('skip_edge_telemetry_immediate:', {
            'raw': in_scene['raw'], 'press': in_scene['press'],
            'trigger': in_scene['trigger'], 'pending': u8(m, SKIP_PENDING),
            'skip_count': u8(m, pasm_constant_in('src/main.pasm', 'SceneVideo_PlaySkipCount'))}, flush=True)
        print('skip_input_sample:', {'press': read_block(m, INPUT_PRESS, 32)[:2].hex(),
                                     'trigger': read_block(m, INPUT_TRIGGER, 32)[:2].hex(),
                                     'raw': read_block(m, INPUT_RAW, 32)[:2].hex(),
                                     'p2press': read_block(m, INPUT2_PRESS, 32)[:2].hex(),
                                     'p2trigger': read_block(m, INPUT2_TRIGGER, 32)[:2].hex()}, flush=True)
        run_frames_exact(m, 3)
        print('in_scene_input:', {k: f'{v:04X}' if k != 'polls' and k != 'checkpoints' else v
                                  for k, v in in_scene.items()}, flush=True)
        r.check('skip exits promptly to title', u16(m, STATE) == TITLE)
        r.check('real in-scene raw input observed', in_scene['raw'] != 0)
        r.check('real in-scene press observed', in_scene['press'] != 0)
        r.check('real in-scene edge observed', in_scene['trigger'] != 0)
        r.check('cooperative input polling occurred', in_scene['polls'] != 0 and in_scene['checkpoints'] != 0)
        r.check('skip pending was consumed once', u8(m, ACTIVE) == 0 and u8(m, AUDIO_STOPS) == 1 and u8(m, PLAY_STATE) == 0 and u8(m, SKIP_PENDING) == 0)
        after_skip = u16(m, SWAPS)
        r.check('no post-skip swap commit', u16(m, SKIP_SWAPS) == after_skip)
        run_frames_exact(m, 8)
        r.check('skip prevents further frame swaps', u16(m, SWAPS) == after_skip == u16(m, SKIP_SWAPS))
        r.check('skip does not report natural completion', u16(m, COMPLETE) == 0)
        print('skip_audio_telemetry:', {
            'skip_swaps_before': before_skip, 'skip_swaps_after': after_skip,
            'starts': u16(m, AUDIO_STARTS), 'stops': u8(m, AUDIO_STOPS),
            'play_state': u8(m, PLAY_STATE), 'active': u8(m, ACTIVE),
            'skip_pending': u8(m, SKIP_PENDING), 'skip_count': u8(m, pasm_constant_in('src/main.pasm', 'SceneVideo_PlaySkipCount')),
            'skip_swaps': u16(m, SKIP_SWAPS), 'state': u16(m, STATE)}, flush=True)

        reset_fixture(m)
        start_scene(m)
        run_frames_exact(m, 230)
        r.check('audio ended while video remained active', u8(m, AUDIO_ENDED) == 1 and u8(m, ACTIVE) != 0)
        exact_input_edge(m, m.BTN_A, 2, port=0)
        run_frames_exact(m, 3)
        r.check('post-audio-end skip exits to title', u16(m, STATE) == TITLE)
        r.check('post-audio-end skip cleanup is safe', u8(m, AUDIO_STOPS) == 1 and u8(m, PLAY_STATE) == 0 and u16(m, COMPLETE) == 0)
    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
