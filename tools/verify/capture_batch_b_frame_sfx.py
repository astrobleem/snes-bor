#!/usr/bin/env python3
"""Parameterized physical oracle for real Batch-B authored frame sounds."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'verify'))

from _harness import open_session, pasm_constant, read_block
import audio_semantic_diesound as semantic
import game_g8_pickup as pickup
import game_g7_throw as throw
from game_g8_get_leo import load_char_onto_player
from game_g7_jump import CHAR_SELECTED, CHAR_THROW_ZPOS, CHAR_THROW_ZVEL, ENTITY_BASES

FRAME_REQUESTS = pasm_constant('AudioSemantic_FrameSoundRequestCount')
SEMANTIC_REQUESTS = pasm_constant('AudioSemantic_RequestCount')
CURRENT_SEMANTIC = pasm_constant('AudioSemantic_CurrentId')
STREAM_ACTIVE = pasm_constant('AudioSemantic_FootDieStreamActive')
STREAM_PENDING = pasm_constant('TadPrivate_stream_pending')
STREAM_OFFSET = pasm_constant('TadPrivate_stream_source_offset')
STREAM_LENGTH = pasm_constant('AudioStream_SourceLength')
STREAM_SOURCE = pasm_constant('AudioStream_SourceId')
STREAM_BUDGET = pasm_constant('TadPrivate_stream_budget')
STREAM_CONSUMER_BUDGET = pasm_constant('TadPrivate_stream_consumer_budget')
SPC_PLAY_SFX = 0x08C1
SFX_QUEUE = 0x7E0020

FIXTURES = {
    'spin': {'roster': 12, 'button': 'a', 'semantic': 0x11, 'local_id': 9},
    'dash': {'roster': 12, 'button': 'down-a', 'prehold': 'down', 'semantic': 0x12, 'local_id': 10},
    'metal': {'roster': 4, 'button': 'x', 'semantic': 0x10, 'local_id': 11},
    'punch0': {'roster': 12, 'button': 'jump-x', 'semantic': 0x13, 'stream_source': 10},
    'gunshot': {'roster': 6, 'button': 'y', 'semantic': 0x15, 'stream_source': 9},
    'wave': {'roster': 8, 'button': 'y', 'semantic': 0x16, 'stream_source': 14},
    'pizza1': {'roster': 12, 'kind': 'pickup', 'semantic': 0x18, 'stream_source': 12,
               'tail_frames': 240},
    'throw': {'roster': 12, 'button': 'x', 'kind': 'throw', 'semantic': 0x14, 'stream_source': 13},
    'boar': {'roster': 12, 'button': 'y', 'kind': 'pain', 'semantic': 0x17, 'stream_source': 8,
             'observe_frames': 10},
}


def u16(m, address: int) -> int:
    b = read_block(m, address, 32)
    return b[0] | (b[1] << 8)


def neutralize_non_player(m) -> None:
    for base in semantic.ENTITY_BASES[1:]:
        semantic.w8(m, base + semantic.CHAR_HP, 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('fixture', choices=sorted(FIXTURES))
    parser.add_argument('--direct', action='store_true', help='queue the fixture resident SFX through Tad_Process')
    parser.add_argument('--voice', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 0 <= args.voice <= 7:
        raise SystemExit('physical voice must be in 0..7')

    config = FIXTURES[args.fixture]
    output = args.output.resolve()
    arm = Path(str(output) + '.arm')
    output.parent.mkdir(parents=True, exist_ok=True)
    for path in (output, Path(str(output) + '.json'), Path(str(output) + '.trace'), arm):
        path.unlink(missing_ok=True)

    env = {
        'MESEN_VOICE_CAPTURE_PATH': str(output),
        'MESEN_VOICE_CAPTURE_VOICE': str(args.voice),
        'MESEN_VOICE_CAPTURE_ARM_FILE': str(arm),
    }
    with open_session(__file__, env=env) as m:
        semantic.boot(m)
        load_char_onto_player(m, config['roster'])
        neutralize_non_player(m)
        for _ in range(30):
            m.run_frames(1)
            m.pause()
        if config.get('prehold') == 'down':
            m.set_input(m.BTN_DOWN, 1)
            m.run_frames(1)
            m.pause()
        if config.get('kind') == 'pickup':
            pickup.reset_combat_state(m)
            m.write_u8(pickup.Entity2 + pickup.CHAR_INPUT_DRIVEN, pickup.CHAR_INPUT_DRIVEN_PROP)
            m.write_u8(pickup.Entity2 + pickup.CHAR_HP, pickup.CHAR_HP_PER_HIT)
            m.write_u8(pickup.Entity2 + pickup.CHAR_PICKUP_TYPE, pickup.PICKUP_TYPE_APPLE)
            m.write_u8(pickup.Entity2_ItemRosterIdx, 0)
            pickup.overlap_entity2_with_player(m)
        if config.get('kind') == 'throw':
            throw.reset_combat_state(m)
            m.write_u8(throw.Entity2 + throw.CHAR_HP, 0)
            m.write_u8(throw.Entity3 + throw.CHAR_HP, 0)
            m.write_u8(throw.Entity1 + throw.CHAR_INPUT_DRIVEN, 0)
            throw.overlap_entity_with_player(m, throw.Entity1)
            m.set_input(m.BTN_R, 1)
            if not throw.poll_until(m, lambda: throw.read_u8(m, throw.PlayerEntity + throw.CHAR_GRAB_TARGET) != 0xFF, 30):
                raise AssertionError('LEO R grab did not establish before THROW capture')
            m.write_u8(throw.Entity1 + throw.CHAR_INPUT_DRIVEN, 2)
            throw.release_gap(m)
        if config.get('kind') == 'pain':
            semantic.prepare_target(m, semantic.ENTITY_BASES[1], 8, 100)

        frame_before = u16(m, FRAME_REQUESTS)
        semantic_before = u16(m, SEMANTIC_REQUESTS)
        if args.direct:
            if 'local_id' not in config:
                raise SystemExit('--direct requires a resident fixture')
            button = None
        elif config.get('kind') == 'pickup':
            button = None
        elif args.fixture in ('spin', 'punch0'):
            m.write_u8(ENTITY_BASES[0] + CHAR_SELECTED, 0)
            m.write_u16(ENTITY_BASES[0] + CHAR_THROW_ZPOS, 0)
            m.write_u16(ENTITY_BASES[0] + CHAR_THROW_ZVEL, 0)
            button = m.BTN_A
        else:
            m.write_u8(ENTITY_BASES[0] + CHAR_SELECTED, 0)
            buttons = {
                'x': m.BTN_X,
                'y': m.BTN_Y,
                'down-a': m.BTN_DOWN | m.BTN_A,
            }
            button = buttons[config['button']]

        hook = m.add_exec_hook(SPC_PLAY_SFX, SPC_PLAY_SFX, cpu_type='Spc')
        if args.direct:
            m.write_memory('snesMemory', SFX_QUEUE + 1, '40')
            m.write_memory('snesMemory', SFX_QUEUE, f"{config['local_id']:02x}")
            arm.touch()
        elif button is not None:
            arm.touch()
            m.set_input(button, 1)
        else:
            arm.touch()
        if not args.direct and args.fixture == 'punch0':
            # Production jumpattack2: the X edge is delivered only after the
            # real grounded A jump has entered its airborne state.
            m.run_frames(1)
            m.pause()
            m.set_input(m.BTN_X, 1)
        if not args.direct:
            m.run_frames(1)
            m.pause()
            m.set_input(0, 1)
        queue_samples = []
        stream_samples = []
        for frame in range(config.get('observe_frames', 24)):
            m.run_frames(1)
            m.pause()
            queue = read_block(m, SFX_QUEUE, 32)
            queue_samples.append({
                'frame': frame,
                'sfx': queue[0],
                'pan': queue[1],
                'semantic': read_block(m, CURRENT_SEMANTIC, 32)[0],
            })
            stream_samples.append({
                'frame': frame,
                'source': read_block(m, STREAM_SOURCE, 32)[0],
                'active': read_block(m, STREAM_ACTIVE, 32)[0],
                'pending': read_block(m, STREAM_PENDING, 32)[0],
                'offset': u16(m, STREAM_OFFSET),
                'length': u16(m, STREAM_LENGTH),
                'producer_offset': u16(m, STREAM_OFFSET),
                'budget': u16(m, STREAM_BUDGET),
                'consumer_budget': u16(m, STREAM_CONSUMER_BUDGET),
            })
        tail_frames = config.get('tail_frames', 156)
        if tail_frames:
            m.run_frames(tail_frames)
            m.pause()
        events = m.drain_notifications()
        m.remove_hook(hook)
        state = m.get_audio_state()
        frame_after = u16(m, FRAME_REQUESTS)
        semantic_after = u16(m, SEMANTIC_REQUESTS)
        current_semantic = read_block(m, CURRENT_SEMANTIC, 32)[0]
        stream_state = {
            'active': read_block(m, STREAM_ACTIVE, 32)[0],
            'pending': read_block(m, STREAM_PENDING, 32)[0],
            'offset': u16(m, STREAM_OFFSET),
            'length': u16(m, STREAM_LENGTH),
        }

    raw = output.read_bytes() if output.exists() else b''
    sidecar_path = Path(str(output) + '.json')
    sidecar = json.loads(sidecar_path.read_text(encoding='utf-8').splitlines()[0]) if sidecar_path.exists() else {}
    payload = {
        **sidecar,
        'fixture': args.fixture,
        'direct': args.direct,
        'voice': args.voice,
        'expected_semantic': config['semantic'],
        'local_id': config.get('local_id'),
        'stream_source': config.get('stream_source'),
        'frame_request_delta': (frame_after - frame_before) & 0xffff,
        'semantic_request_delta': (semantic_after - semantic_before) & 0xffff,
        'current_semantic': current_semantic,
        'stream_state': stream_state,
        'queue_samples': queue_samples,
        'stream_samples': stream_samples,
        'spc_play_handler_count': sum(1 for e in events if e.get('params', {}).get('handle') == hook),
        'capture_bytes': len(raw),
        'capture_sha256': hashlib.sha256(raw).hexdigest(),
        'audio_state': state,
    }
    Path(str(output) + '.report.json').write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(payload, sort_keys=True))
    return 0 if raw else 1


if __name__ == '__main__':
    raise SystemExit(main())
