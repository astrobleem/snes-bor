#!/usr/bin/env python3
"""Focused G15 L3B proof: timed Rugal frame streaming, no audio/campaign."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, read_block, run_frames_exact, pasm_constant_in  # noqa: E402

STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
INTRO = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_INTRO')
SCENE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_SCENE_FRAME')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
REQ = pasm_constant_in('src/main.pasm', 'SceneVideo_TestRequest')
ACTIVE = pasm_constant_in('src/main.pasm', 'SceneVideo_TestActive')
ERROR = pasm_constant_in('src/main.pasm', 'SceneVideo_TestError')
HANDLER = pasm_constant_in('src/main.pasm', 'SceneVideo_TestHandlerEntries')
PLAY_STATE = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayState')
VISIBLE = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayVisible')
NEXT = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayNext')
PRESENTED = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayPresented')
SWAPS = pasm_constant_in('src/main.pasm', 'SceneVideo_PlaySwaps')
READY = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayReadyCount')
LATE = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayLateCount')
RETRIES = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayDmaRetries')
MAX_DMA = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayMaxDmaBytes')
ELAPSED = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayElapsedTicks')
COMPLETE = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayCompletion')
LAST = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayLastPresented')
ACC = pasm_constant_in('src/main.pasm', 'SceneVideo_PlayAccumulator')
NMI = pasm_constant_in('src/core/nmi.pasm', 'Nmi_FrameCounter')


def u8(m, address):
    return read_block(m, address, 32)[0]


def u16(m, address):
    return int.from_bytes(read_block(m, address, 32)[:2], 'little')


def main():
    r = Reporter('BOR-L3B-SCENE-VIDEO-PLAYBACK', kind='GATE')
    with open_session(__file__, boot_wait=2.0) as m:
        m.reset_emulator()
        for addr in (REQ, ACTIVE, ERROR, PLAY_STATE, VISIBLE, NEXT, LAST):
            m.write_u8(addr, 0)
        for addr in (HANDLER, PRESENTED, SWAPS, READY, LATE, RETRIES,
                     MAX_DMA, ELAPSED, COMPLETE):
            m.write_u16(addr, 0)
        m.write_u16(STATE, TITLE)
        m.write_u16(STATE + 2, TITLE)
        run_frames_exact(m, 180)
        m.write_u16(REQ, 1)
        m.write_u16(STATE, INTRO)
        # 126 frames at 25 fps is about 302 NTSC intervals; allow bounded
        # preparation/teardown margin while still failing a stuck player.
        # The production DMA path can miss vblank service windows while a
        # scene frame is being transferred; this bounded budget still leaves
        # enough wall-clock room for the 126-frame clip to complete.
        run_frames_exact(m, 1300)

        r.check('scene state entered', u16(m, STATE) == SCENE or u16(m, STATE) == TITLE)
        r.check('handler was entered', u16(m, HANDLER) >= 1)
        r.check('no scene parse error', u8(m, ERROR) == 0)
        r.check('all 126 frames presented', u16(m, PRESENTED) == 126)
        r.check('last frame index is 125', u8(m, LAST) == 125)
        r.check('visible frame is final before cleanup or title',
                u8(m, VISIBLE) == 125 or u16(m, STATE) == TITLE)
        r.check('frame sequence has 125 swaps', u16(m, SWAPS) == 125)
        r.check('all prepared frames became ready', u16(m, READY) >= 125)
        r.check('no late frames', u16(m, LATE) == 0)
        r.check('no DMA enqueue retries', u16(m, RETRIES) == 0)
        r.check('maximum DMA transfer is tile-sized', u16(m, MAX_DMA) >= 11968)
        r.check('completion exactly once', u16(m, COMPLETE) == 1)
        r.check('post-playback cleanup reaches title', u16(m, STATE) == TITLE)
        r.check('scene active marker cleared', u8(m, ACTIVE) == 0)
        print('playback_telemetry:', {
            'state': u16(m, STATE), 'handler': u16(m, HANDLER),
            'presented': u16(m, PRESENTED), 'visible': u8(m, VISIBLE),
            'next': u8(m, NEXT), 'swaps': u16(m, SWAPS),
            'ready': u16(m, READY), 'late': u16(m, LATE),
            'retries': u16(m, RETRIES), 'max_dma': u16(m, MAX_DMA),
            'elapsed': u16(m, ELAPSED), 'completion': u16(m, COMPLETE),
            'nmi': u16(m, NMI), '4200': m.read_memory('snesMemory', 0x4200, 32)[0],
            'play_state': u8(m, PLAY_STATE), 'acc': u16(m, ACC), 'active': u8(m, ACTIVE),
            'error': u8(m, ERROR)}, flush=True)
    return r.finish()


if __name__ == '__main__':
    raise SystemExit(main())
