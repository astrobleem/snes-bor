#!/usr/bin/env python3
"""Focused G15 L3A proof: load and display real Rugal frame 0 only."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, read_block, run_frames_exact, pasm_constant_in  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scene_video'))
import convert_rugal  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
INTRO = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_INTRO')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
REQUEST = pasm_constant_in('src/main.pasm', 'SceneVideo_TestRequest')
ACTIVE = pasm_constant_in('src/main.pasm', 'SceneVideo_TestActive')
ERROR = pasm_constant_in('src/main.pasm', 'SceneVideo_TestError')
REQUEST_SEEN = pasm_constant_in('src/main.pasm', 'SceneVideo_TestRequestSeen')
REQUEST_CONSUMED = pasm_constant_in('src/main.pasm', 'SceneVideo_TestRequestConsumed')
HANDLER_ENTRIES = pasm_constant_in('src/main.pasm', 'SceneVideo_TestHandlerEntries')
FRAME_ID = pasm_constant_in('src/main.pasm', 'SceneVideo_TestFrameId')
MAP_BYTES = pasm_constant_in('src/main.pasm', 'SceneVideo_TestMapBytes')
TILE_BYTES = pasm_constant_in('src/main.pasm', 'SceneVideo_TestTileBytes')
PAL_BYTES = pasm_constant_in('src/main.pasm', 'SceneVideo_TestPaletteBytes')
FRAME_OFFSET = pasm_constant_in('src/main.pasm', 'SceneVideo_TestFrameOffset')
WIDTH = pasm_constant_in('src/main.pasm', 'SceneVideo_TestWidth')
HEIGHT = pasm_constant_in('src/main.pasm', 'SceneVideo_TestHeight')
STAGING = pasm_constant_in('src/main.pasm', 'SceneVideo_FrameStaging')
# These are deliberately simple aliases in main.pasm; derive their offsets
# here so the verifier does not depend on expression parsing in _harness.
MAP_STAGE = STAGING
TILE_STAGE = STAGING + 0x0800
PALETTE_STAGE = STAGING + 0x3820
BLANK_INDEX = pasm_constant_in('src/main.pasm', 'SceneVideo_BlankTileIndex')
SCENE_STATE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_SCENE_FRAME')


def u16(m, address):
    b = read_block(m, address, 32)
    return b[0] | b[1] << 8


def u32(m, address):
    b = read_block(m, address, 32)
    return b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24


def main():
    r = Reporter('BOR-L3A-SCENE-VIDEO-FRAME', kind='GATE')
    payload, stats = convert_rugal.build_payload(PAK)
    pointer = struct.unpack_from('<I', payload, 4)[0]
    frame_id, packed = struct.unpack_from('<HI', payload, pointer)
    map_len = (packed & 0x7FF) * 2
    tile_len = ((packed >> 11) & 0x7FF) * 32
    pal_len = ((packed >> 22) & 0xFF) * 2
    frame_data = payload[pointer + 6:pointer + 6 + map_len + tile_len + pal_len]
    packed_map = frame_data[:map_len]
    packed_tiles = frame_data[map_len:map_len + tile_len]
    packed_palette = frame_data[map_len + tile_len:]

    with open_session(__file__, boot_wait=2.0) as m:
        m.reset_emulator()
        # Mesen reset preserves WRAM; establish a clean, explicit request
        # fixture so telemetry cannot turn stale bytes into a false pass.
        m.write_u16(REQUEST, 0)
        m.write_u8(ACTIVE, 0)
        m.write_u8(ERROR, 0)
        m.write_u16(REQUEST_SEEN, 0)
        m.write_u16(REQUEST_CONSUMED, 0)
        m.write_u16(HANDLER_ENTRIES, 0)
        m.write_u16(STATE, TITLE)
        m.write_u16(STATE + 2, TITLE)
        run_frames_exact(m, 180)
        m.write_u16(REQUEST, 1)
        m.write_u16(STATE, INTRO)
        # The normal state transition first clears/uploads gameplay OAM; the
        # scene dispatcher is reached after that bounded DMA handshake.
        run_frames_exact(m, 12)

        r.check('metadata-driven frame test state active', u8(m, ACTIVE) == 0xA5)
        r.check('request was observed', u16(m, REQUEST_SEEN) >= 1)
        r.check('request was consumed', u16(m, REQUEST_CONSUMED) >= 1)
        r.check('exact scene frame state', u16(m, STATE) == SCENE_STATE)
        r.check('scene frame handler entered', u16(m, HANDLER_ENTRIES) >= 1)
        r.check('malformed payload error is clear', u8(m, ERROR) == 0)
        r.check('frame id is zero', u16(m, FRAME_ID) == 0)
        r.check('parsed dimensions are 256x192', u16(m, WIDTH) == 256 and u16(m, HEIGHT) == 192)
        r.check('parsed map length is 1536', u16(m, MAP_BYTES) == map_len == 1536)
        r.check('parsed tile length matches frame 0', u16(m, TILE_BYTES) == tile_len)
        r.check('parsed palette length is 64', u16(m, PAL_BYTES) == pal_len == 64)
        r.check('frame absolute offset is metadata base plus pointer',
                u32(m, FRAME_OFFSET) == 4046360 + pointer)
        r.check('scene state entered', u16(m, STATE) == SCENE_STATE)
        vram_map = bytes(m.read_memory('snesVideoRam', 0xC000, 2048))
        vram_tiles = bytes(m.read_memory('snesVideoRam', 0, tile_len + 32))
        cgram = bytes(m.read_memory('snesCgRam', 0, 64))
        expected_map = bytearray(struct.pack('<H', 0) * 1024)
        blank_word = struct.pack('<H', (tile_len // 32))
        for offset in range(0, len(expected_map), 2):
            expected_map[offset:offset + 2] = blank_word
        expected_map[128:128 + len(packed_map)] = packed_map
        expected_tiles = packed_tiles + bytes(32)
        r.check('DMA map contains 16px borders and 24 video rows', vram_map == bytes(expected_map))
        r.check('DMA tiles match packed frame plus blank tile', vram_tiles == expected_tiles)
        r.check('DMA palette matches packed frame', cgram == packed_palette)
        shot = m.take_screenshot()
        print('frame0_screenshot:', shot, flush=True)
        r.check('frame screenshot captured', isinstance(shot, dict))

        m.write_u16(REQUEST, 2)
        m.write_u16(STATE, INTRO)
        run_frames_exact(m, 12)
        r.check('cleanup returns to TITLE', u16(m, STATE) == TITLE)
        r.check('scene active marker cleared', u8(m, ACTIVE) == 0)
        title_shot = m.take_screenshot()
        print('title_screenshot:', title_shot, flush=True)
        r.check('post-cleanup screen captured', isinstance(title_shot, dict))

    print('frame0_pointer_relative:', pointer)
    print('frame0_map_bytes:', map_len)
    print('frame0_tile_bytes:', tile_len)
    print('frame0_palette_bytes:', pal_len)
    print('payload_stats:', stats)
    return r.finish()


def u8(m, address):
    return read_block(m, address, 32)[0]


if __name__ == '__main__':
    raise SystemExit(main())
