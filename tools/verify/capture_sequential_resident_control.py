#!/usr/bin/env python3
"""Harness-only sequential resident-SFX control; no APUIO polling."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'verify'))

import audio_semantic_diesound as semantic
from _harness import open_session

SFX_QUEUE = 0x7E0020
SPC_PLAY_SFX = 0x08C1


def main() -> int:
    os.environ['MESEN_EXE'] = r'E:\gh\Mesen2-runtime\voice-capture-5fb1f1b\Mesen.exe'
    os.environ['USE_STANDARD_MESEN'] = '1'
    with open_session(__file__) as m:
        semantic.boot(m)
        for base in semantic.ENTITY_BASES[1:]:
            semantic.w8(m, base + semantic.CHAR_HP, 0)
        for _ in range(30):
            m.run_frames(1)
            m.pause()
        hook = m.add_exec_hook(SPC_PLAY_SFX, cpu_type='Spc')
        for effect in (2, 9):
            m.write_memory('snesMemory', SFX_QUEUE + 1, '40')
            m.write_memory('snesMemory', SFX_QUEUE, f'{effect:02x}')
            result = m.run_until(60, hook)
            print(f'effect={effect} handler_reached={bool(result)}')
        m.remove_hook(hook)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
