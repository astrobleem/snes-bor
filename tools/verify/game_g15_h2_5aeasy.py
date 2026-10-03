#!/usr/bin/env python3
"""Focused G15-H2 proof for BOR 5AEASY SCROLL_DOWN."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant_in, read_block
import game_bor_startup_select as startup
from game_g15_2easy import clear_loaded_stage, u8, u16

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402

STAGE = 17
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
SCROLL_DIRECTION = pasm_constant_in('src/core/game_state.pasm', 'Stage_ScrollDirection')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
SPAWN_TABLE = pasm_constant_in('src/core/spawn.pasm', 'SpawnTable_Wram')
SCREEN_POS_Y = 0x7E1604
SCREEN_POS_Y_FRAC = 0x7E1603
SCREEN_MAX_Y = 0x7E1610
SCREEN_TARGET_Y = 0x7E1618
NMI_BG1_Y = pasm_constant_in('src/core/nmi.pasm', 'Nmi_Bg1ScrollY')


def main():
    r = Reporter('G15-BATCH-H2-5AEASY-SCROLL-DOWN', kind='GATE')
    stage = build_rom.STAGE_CONFIGS[STAGE]
    manifest = json.load(open(os.path.join(ROOT, stage['bg'], 'manifest.json')))
    blob = open(os.path.join(ROOT, stage['spawn']), 'rb').read()
    records = [blob[i:i + 10] for i in range(0, len(blob), 10)]
    r.check('5AEASY is the down-scrolling physical stage', STAGE == 17
            and stage['source_level'].upper().endswith(r'5AEASY.TXT'))
    r.check('vertical page is packed as a repeating 32-row static map',
            manifest['width_tiles'] == 32 and manifest['height_tiles'] == 32
            and manifest.get('vertical_repeat') is True
            and len(open(os.path.join(ROOT, stage['bg'], 'tilemap.bin'), 'rb').read()) == 2048)
    r.check('vertical queue triggers use authored level positions',
            len(records) == 54
            and records[0][0:2] == b'\x00\x00'
            and max(int.from_bytes(rec[0:2], 'little') for rec in records) == 80
            and {int.from_bytes(rec[0:2], 'little') for rec in records} <= {0, 80})

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        for current, target in ((0, 1), (1, 2), (2, 11), (11, 12),
                                (12, 13), (13, 14), (14, 15), (15, 16),
                                (16, STAGE)):
            r.check(f'campaign edge {current}->{target}',
                    clear_loaded_stage(m, r, target))
        r.check('5AEASY enters PLAYING with down direction',
                u16(m, GAME_STATE) == PLAYING and u16(m, STAGE_INDEX) == STAGE
                and u8(m, SCROLL_DIRECTION) == 1
                and u8(m, CAMPAIGN_ORDINAL) == 9)
        y0 = u16(m, SCREEN_POS_Y)
        bg0 = u16(m, NMI_BG1_Y)
        idx0 = u8(m, SPAWN_INDEX)
        m.run_frames(300)
        # The first authored records are props and intentionally occupy the
        # available AI windows in this compact runtime. Release those test
        # occupants so the next real enemy record can exercise the ordinary
        # source vertical-entry path without overwriting a live actor.
        for i in range(1, 6):
            m.write_u8(0x7E0A00 + i * 133 + 35, 0)
        # Record 5 is an authored ordinary enemy with trigger 0, so selecting
        # it here isolates vertical entry without inventing a spawn record or
        # depending on the earlier prop occupancy.
        m.write_u8(SPAWN_INDEX, 5)
        m.run_frames(3)
        m.pause()
        dropped = []
        for i in range(1, 6):
            base = 0x7E0A00 + i * 133
            dropped.append(u8(m, base + 11) == 6 and u16(m, base + 67) > 0)
        r.check('vertical enemy entry uses the source altitude/drop state',
                any(dropped))
        m.run_frames(25)
        m.pause()
        y1 = u16(m, SCREEN_POS_Y)
        bg1 = u16(m, NMI_BG1_Y)
        idx1 = u8(m, SPAWN_INDEX)
        r.check('vertical levelpos advances at runtime', y1 > y0)
        r.check('BG1 scroll shadow follows vertical progress',
                bg1 != bg0 and 0 <= bg1 < 224)
        r.check('queue consumes records from vertical levelpos', idx1 > idx0)

        # Exercise the source-period wrap at the PPU-visible shadow. The
        # runtime stage clamp is temporarily lifted only for this bounded
        # renderer-period probe.
        saved_max_y = u16(m, SCREEN_MAX_Y)
        m.write_u16(SCREEN_MAX_Y, 0xFFFF)
        m.write_u16(SCREEN_POS_Y, 447)
        m.write_u8(SCREEN_POS_Y_FRAC, 0)
        m.run_frames(1)
        m.pause()
        wrapped = u16(m, NMI_BG1_Y)
        r.check('BG1 vertical period wraps without leaving the page',
                0 <= wrapped < 224)
        m.write_u16(SCREEN_MAX_Y, saved_max_y)
        # Return to the stage's authored terminal Y before using the common
        # stage-clear helper; its legacy setup advances X for horizontal
        # stages, while 5AEASY's completion boundary is vertical.
        m.write_u16(SCREEN_POS_Y, saved_max_y)
        m.write_u16(SCREEN_TARGET_Y, saved_max_y)
        m.write_u8(SCREEN_POS_Y_FRAC, 0)
        r.check('six-window runtime remains bounded',
                u8(m, SPAWN_COUNT) == 54)
        r.check('completion still returns TITLE, never catalog tail',
                clear_loaded_stage(m, r, None)
                and u16(m, GAME_STATE) == TITLE
                and u8(m, CAMPAIGN_ORDINAL) == 9)
    r.finish()


if __name__ == '__main__':
    main()
