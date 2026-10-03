#!/usr/bin/env python3
"""Focused O2 proof for the generated BOR authored-scene sequence."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, read_block, run_frames_exact, pasm_constant_in  # noqa: E402

STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
SCENE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_SCENE_FRAME')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
REQ = pasm_constant_in('src/main.pasm', 'SceneVideo_TestRequest')
SCENE_ID = pasm_constant_in('src/main.pasm', 'SceneVideo_RequestedSceneId')
ACTIVE = pasm_constant_in('src/main.pasm', 'SceneVideo_TestActive')
ERROR = pasm_constant_in('src/main.pasm', 'SceneVideo_TestError')
ERROR_CODE = pasm_constant_in('src/main.pasm', 'SceneVideo_TestErrorCode')
PRESENTED = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayPresented')
LATE = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayLateCount')
RETRIES = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayDmaRetries')
COMPLETE = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayCompletion')
SEEN = pasm_constant_in('src/main.pasm', 'SceneVideo_TestRequestSeen')
CONSUMED = pasm_constant_in('src/main.pasm', 'SceneVideo_TestRequestConsumed')
SEQ_SCENE = pasm_constant_in('src/main.pasm', 'SceneVideo_SequenceSceneId')
SEQ_CLIP = pasm_constant_in('src/main.pasm', 'SceneVideo_SequenceClipId')
SEQ_ORD = pasm_constant_in('src/main.pasm', 'SceneVideo_SequenceClipOrdinal')
TRANS = pasm_constant_in('src/main.pasm', 'SceneVideo_SequenceTransitions')
AUDIO = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayAudioStartCount')
FRAME_ID = pasm_constant_in('src/main.pasm', 'SceneVideo_TestFrameId')
MAP = pasm_constant_in('src/main.pasm', 'SceneVideo_TestMapBytes')
TILES = pasm_constant_in('src/main.pasm', 'SceneVideo_TestTileBytes')
BASE = pasm_constant_in('src/main.pasm', 'SceneVideo_TestPayloadBase')
PAYLOAD_SIZE = pasm_constant_in('src/main.pasm', 'SceneVideo_TestPayloadSize')
COUNT = pasm_constant_in('src/main.pasm', 'SceneVideo_TestFrameCount')
PTR = pasm_constant_in('src/main.pasm', 'SceneVideo_TestFramePointer')
INDEX = pasm_constant_in('src/main.pasm', 'SceneVideo_TestFrameIndex')
LOADS = pasm_constant_in('src/main.pasm', 'SceneVideo_LoadCount')
PLAY_STATE = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayState')
PROBE = pasm_constant_in('src/main.pasm', 'SceneVideo_MsuDmaProbe')


def u8(m, a):
    return read_block(m, a, 32)[0]


def u16(m, a):
    return int.from_bytes(read_block(m, a, 32)[:2], 'little')


def run_scene(m, scene_id, frames=6000):
    m.write_u8(REQ, 0)
    m.write_u8(ACTIVE, 0)
    m.write_u8(ERROR, 0)
    m.write_u8(PROBE, 0)
    m.write_u8(SCENE_ID, scene_id)
    m.write_u16(SEEN, 0)
    m.write_u16(CONSUMED, 0)
    m.write_u16(PRESENTED, 0)
    m.write_u16(LATE, 0)
    m.write_u16(RETRIES, 0)
    m.write_u16(COMPLETE, 0)
    m.write_u16(TRANS, 0)
    m.write_u16(AUDIO, 0)
    m.write_u16(REQ, 1)
    m.write_u16(STATE + 2, TITLE)
    m.write_u16(STATE, SCENE)
    remaining = frames
    while remaining:
        step = min(240, remaining)
        run_frames_exact(m, step)
        remaining -= step
        if u16(m, STATE) == TITLE:
            break


def main():
    r = Reporter('BOR-O2-AUTHORED-SCENE-SEQUENCE', kind='GATE')
    with open_session(__file__, boot_wait=2.0) as m:
        print('session_ready', flush=True)
        m.reset_emulator()
        m.write_u16(STATE, TITLE)
        m.write_u16(STATE + 2, TITLE)
        run_frames_exact(m, 180)
        print('warmup_ready', flush=True)
        run_scene(m, 2, frames=6000)
        print('request_telemetry:', {'seen': u16(m, SEEN), 'consumed': u16(m, CONSUMED),
                                     'state': u16(m, STATE), 'request': u16(m, REQ),
                                     'active': u8(m, ACTIVE), 'error': u8(m, ERROR), 'error_code': u8(m, ERROR_CODE),
                                     'scene': u8(m, SEQ_SCENE), 'clip': u8(m, SEQ_CLIP),
                                     'frame_id': u16(m, FRAME_ID), 'map': u16(m, MAP),
                                     'tiles': u16(m, TILES), 'base': int.from_bytes(read_block(m, BASE, 32)[:4], 'little'),
                                     'size': int.from_bytes(read_block(m, PAYLOAD_SIZE, 32)[:4], 'little'),
                                     'count': int.from_bytes(read_block(m, COUNT, 32)[:4], 'little'),
                                     'ptr': int.from_bytes(read_block(m, PTR, 32)[:4], 'little'),
                                     'index': u16(m, INDEX), 'loads': u16(m, LOADS),
                                     'play_state': u8(m, PLAY_STATE)}, flush=True)
        r.check('sequence ends at title', u16(m, STATE) == TITLE)
        r.check('no scene parse error', u8(m, ERROR) == 0)
        r.check('scene inactive after completion', u8(m, ACTIVE) == 0)
        r.check('ending scene id retained', u8(m, SEQ_SCENE) in (0, 2))
        r.check('all 1997 frames presented', u16(m, PRESENTED) == 1997)
        r.check('four clip transitions', u16(m, TRANS) == 4)
        r.check('audio started once', u16(m, AUDIO) == 1)
        r.check('zero late frames', u16(m, LATE) == 0)
        r.check('zero DMA retries', u16(m, RETRIES) == 0)
        r.check('completion exactly once', u16(m, COMPLETE) == 1)
        print('sequence_telemetry:', {
            'state': u16(m, STATE), 'scene': u8(m, SEQ_SCENE),
            'clip': u8(m, SEQ_CLIP), 'ordinal': u8(m, SEQ_ORD),
            'presented': u16(m, PRESENTED), 'transitions': u16(m, TRANS),
            'audio_starts': u16(m, AUDIO), 'late': u16(m, LATE),
            'retries': u16(m, RETRIES), 'completion': u16(m, COMPLETE)}, flush=True)
    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
