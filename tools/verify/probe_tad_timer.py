#!/usr/bin/env python3
"""Bounded TAD TIMER_1/SFX-branch liveness probe.

This is deliberately a BOR-local diagnostic: the hook mechanism is generic,
but the ROM and current-build SPC address are BOR-specific.  It never reads
the destructive TIMER_1 output register; execution at the current generated
SFX branch target is the liveness oracle.
"""
import argparse
import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ROM = os.path.join(ROOT, 'distribution', 'bor.sfc')
sys.path.insert(0, os.path.dirname(__file__))
from _harness import open_session, run_frames_exact
import audio_semantic_diesound as semantic

SFX_PROCESS_ENTRY = 0x03E5
TAD_STATE = 0x7E0032
TAD_QUEUE_SFX = 0x7E0020
TAD_QUEUE_PAN = 0x7E0021


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('idle', 'direct', 'gameplay'), default='idle')
    parser.add_argument('--frames', type=int, default=60)
    args = parser.parse_args()
    rom_sha = hashlib.sha256(open(ROM, 'rb').read()).hexdigest()
    with open_session(__file__) as m:
        semantic.boot(m)
        semantic.clear_observation(m)
        hook = m.add_exec_hook(SFX_PROCESS_ENTRY, SFX_PROCESS_ENTRY, cpu_type='Spc')
        fall_before = fall_after = None
        fall_rows = []
        if args.mode == 'direct':
            semantic.w8(m, TAD_QUEUE_PAN, 0x40)
            semantic.w8(m, TAD_QUEUE_SFX, 1)
        elif args.mode == 'gameplay':
            fall_before, fall_after, fall_rows = semantic.fall_target(m)
        else:
            pass
        setup_hook = m.add_exec_hook(0x098F, 0x098F, cpu_type='Spc')
        events = []
        setup_events = []
        for _ in range(args.frames):
            run_frames_exact(m, 1)
            m.pause()
            frame_events = [n.get('params', {}) for n in m.drain_notifications()]
            events.extend(x for x in frame_events if x.get('handle') == hook)
            setup_events.extend(x for x in frame_events if x.get('handle') == setup_hook)
        m.remove_hook(setup_hook)
        m.remove_hook(hook)
        print(json.dumps({
            'rom_sha256': rom_sha,
            'launcher': 'standard-Mesen-open_session',
            'mode': args.mode,
            'frames_requested': args.frames,
            'tad_state': m.read_memory('snesMemory', TAD_STATE, 32)[0],
            'timer1_target_FB': m.read_memory('spcMemory', 0x00FB, 32)[0],
            'sfx_process_entry': SFX_PROCESS_ENTRY,
            'sfx_process_events': events,
            'sfx_process_count': len(events),
            'setup_events': setup_events,
            'setup_count': len(setup_events),
            'fall_request_delta': None if args.mode != 'gameplay' else fall_after - fall_before,
            'fall_semantic_trace': fall_rows,
        }, sort_keys=True))


if __name__ == '__main__':
    main()
