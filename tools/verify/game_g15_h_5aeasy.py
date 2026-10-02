#!/usr/bin/env python3
"""Focused G15 Batch H gate for authoritative BOR 5AEASY."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant_in
import game_bor_startup_select as startup
from game_g15_2easy import clear_loaded_stage, u8, u16

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402
sys.path[:0] = [os.path.join(ROOT, 'tools', 'bg_converter'),
               os.path.join(ROOT, 'tools', 'bor_converter')]
from pak_extract import extract  # noqa: E402
from level_parse import parse_level  # noqa: E402
from spawn_parse import parse_spawns, SpawnEvent, WaitEvent, GroupEvent  # noqa: E402

PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
LEVEL = r'DATA\EASY\5AEASY.TXT'
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
SCREEN_POS_Y = 0x7E1604
SCREEN_TARGET_Y = 0x7E1618
SCREEN_MAX_Y = 0x7E1610


def main():
    r = Reporter('G15-BATCH-H-5AEASY', kind='GATE')
    text = extract(PAK, LEVEL).decode('latin1')
    level = parse_level(text, LEVEL)
    events = parse_spawns(text)
    spawns = [e for e in events if isinstance(e, SpawnEvent)]
    waits = [e for e in events if isinstance(e, WaitEvent)]
    groups = [e for e in events if isinstance(e, GroupEvent)]
    stage = next(s for s in build_rom.STAGE_CONFIGS
                 if s['source_level'].upper() == LEVEL.upper())
    stage_index = build_rom.STAGE_CONFIGS.index(stage)
    blob = open(os.path.join(ROOT, stage['spawn']), 'rb').read()
    manifest = json.load(open(os.path.join(ROOT, stage['bg'], 'manifest.json')))

    r.check('5AEASY is appended at physical catalog index 17', stage_index == 17)
    r.check('BOR campaign resolves through 5AEASY then TITLE',
            build_rom.CAMPAIGN_STAGE_MAPS['BOR_ORIGINAL'] ==
            [0, 1, 2, 11, 12, 13, 14, 15, 16, 17])
    r.check('source elevator panel/order is preserved',
            level.background.lower().endswith(r'elevator\back.gif')
            and len(level.panels) == 1 and level.order == 'a'
            and manifest['width_px'] == 256 and manifest['height_px'] == 224)
    r.check('source event inventory is preserved',
            len(events) == 54 and len(spawns) == 45
            and not waits and len(groups) == 9)
    r.check('source models and contained items are preserved',
            {e.character.lower() for e in spawns} ==
            {'angel', 'billy', 'drum', 'jhun', 'joe', "k'", 'ralf', 'ramon',
             'shermie', 'time', 'yashiro'}
            and sum(bool(e.item) for e in spawns) == 2
            and sum(e.if2p for e in spawns) == 1)
    r.check('packed queue preserves all ordered records', len(blob) == 540)
    r.check('source direction/endhole records are retained for audit',
            'direction\tdown' in text.lower()
            and 'endhole\t\t1' in text.lower())
    r.check('no hole or blocked record is authored',
            all(word not in text.lower() for word in ('\nhole', '\nblocked')))
    r.check('5AEASY direction-down runtime is source-equivalent',
            'direction\tdown' in text.lower())
    r.check('selection roster remains 13', build_rom.PLAYABLE_ROSTER_COUNT == 13)

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        for current, target in ((0, 1), (1, 2), (2, 11), (11, 12),
                                (12, 13), (13, 14), (14, 15), (15, 16),
                                (16, stage_index)):
            r.check(f'campaign edge {current} reaches {target}',
                    clear_loaded_stage(m, r, target))
        r.check('4BEASY -> 5AEASY enters PLAYING',
                u16(m, GAME_STATE) == PLAYING
                and u16(m, STAGE_INDEX) == stage_index
                and u8(m, CAMPAIGN_ORDINAL) == 9)
        m.run_frames(60)
        r.check('5AEASY authored queue begins',
                u8(m, SPAWN_INDEX) > 0 and u8(m, SPAWN_COUNT) == 54
                and u16(m, GAME_STATE) == PLAYING)
        # Vertical completion uses the authored Y terminal boundary; the
        # common campaign helper otherwise only advances horizontal stages.
        m.write_u16(SCREEN_POS_Y, u16(m, SCREEN_MAX_Y))
        m.write_u16(SCREEN_TARGET_Y, u16(m, SCREEN_MAX_Y))
        r.check('5AEASY completion returns TITLE, never catalog tail',
                clear_loaded_stage(m, r, None)
                and u16(m, GAME_STATE) == TITLE
                and u8(m, CAMPAIGN_ORDINAL) == 9)
    r.finish()


if __name__ == '__main__':
    main()
