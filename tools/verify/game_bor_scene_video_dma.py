#!/usr/bin/env python3
"""Focused fixed-source MSU_DATA -> WRAM proof for O2."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import open_session, run_frames_exact, read_block, pasm_constant_in

ROOT = Path(__file__).resolve().parents[2]
MSU = ROOT / 'distribution' / 'bor.msu'
REQ = pasm_constant_in('src/main.pasm', 'SceneVideo_TestRequest')
STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
SCENE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_SCENE_FRAME')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
SCENE_ID = pasm_constant_in('src/main.pasm', 'SceneVideo_RequestedSceneId')
STAGE = pasm_constant_in('src/main.pasm', 'SceneVideo_FrameStaging') + 0x80
PROBE = pasm_constant_in('src/main.pasm', 'SceneVideo_MsuDmaProbe')

def main():
    data = MSU.read_bytes()
    payload = 5_732_022
    rel = int.from_bytes(data[payload + 4:payload + 8], 'little')
    body = payload + rel + 6
    expected = data[body:body + 64]
    with open_session(__file__, boot_wait=2.0) as m:
        m.reset_emulator()
        m.write_u16(STATE, TITLE)
        m.write_u16(STATE + 2, TITLE)
        run_frames_exact(m, 180)
        m.write_u8(SCENE_ID, 2)
        m.write_u8(PROBE, 1)
        m.write_u16(REQ, 1)
        m.write_u16(STATE, SCENE)
        run_frames_exact(m, 1)
        actual = bytes(read_block(m, STAGE, 64))
        assert actual == expected, (actual.hex(), expected.hex())
    print('fixed-source MSU_DATA -> WRAM: PASS')

if __name__ == '__main__':
    main()
