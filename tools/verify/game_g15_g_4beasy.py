#!/usr/bin/env python3
"""Focused G15 Batch G gate for authoritative BOR 4BEASY."""
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
LEVEL = r'DATA\EASY\4BEASY.TXT'
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')


def main():
    r = Reporter('G15-BATCH-G-4BEASY', kind='GATE')
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
    manifest = __import__('json').load(open(os.path.join(ROOT, stage['bg'], 'manifest.json')))
    fp_manifest = __import__('json').load(open(os.path.join(ROOT, stage['frontpanel'], 'manifest.json')))

    r.check('4BEASY is appended at physical catalog index 16', stage_index == 16)
    r.check('BOR campaign resolves through 4BEASY then TITLE',
            build_rom.CAMPAIGN_STAGE_MAPS['BOR_ORIGINAL'] ==
            [0, 1, 2, 11, 12, 13, 14, 15, 16])
    r.check('warehouse panel/order and streaming dimensions are preserved',
            level.background.lower().endswith(r'warehous\back.gif')
            and level.frontpanel.lower().endswith(r'warehous\front.gif')
            and len(level.panels) == 6 and len(level.order) == 36
            and manifest['width_px'] == 5504 and manifest['height_px'] == 224
            and fp_manifest['width_tiles'] == manifest['width_tiles'])
    r.check('source event inventory is preserved',
            len(events) == 50 and len(spawns) == 42
            and len(waits) == 4 and len(groups) == 4)
    r.check('source models, boss, and contained items are preserved',
            {e.character.lower() for e in spawns} ==
            {'angel', 'billy', 'crate', 'jhun', "k'", 'mrbig',
             'ralf', 'shermie', 'yashiro', 'box'}
            and sum(e.boss for e in spawns) == 1
            and sum(bool(e.item) for e in spawns) == 4
            and sum(e.if2p for e in spawns) == 1)
    r.check('packed queue preserves all ordered records', len(blob) == 500)
    r.check('4BEASY uses no hole/endhole/blocked directive',
            all(word not in text.lower() for word in ('\nhole', '\nendhole', '\nblocked')))
    r.check('source music and water/layer requirements are preserved',
            'music\t\tdata/music/' in text.lower())
    r.check('Mr Big is authored as the final boss record',
            next(e for e in spawns if e.character.lower() == 'mrbig').boss)
    r.check('selection roster remains 13', build_rom.PLAYABLE_ROSTER_COUNT == 13)

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        for current, target in ((0, 1), (1, 2), (2, 11), (11, 12),
                                (12, 13), (13, 14), (14, 15), (15, stage_index)):
            r.check(f'campaign edge {current} reaches {target}',
                    clear_loaded_stage(m, r, target))
        r.check('4AEASY -> 4BEASY enters PLAYING',
                u16(m, GAME_STATE) == PLAYING
                and u16(m, STAGE_INDEX) == stage_index
                and u8(m, CAMPAIGN_ORDINAL) == 8)
        m.pause()
        m.set_input(m.BTN_RIGHT, 180)
        m.run_frames(180)
        m.pause()
        r.check('4BEASY authored queue begins',
                u8(m, SPAWN_INDEX) > 0 and u8(m, SPAWN_COUNT) == 50
                and u16(m, GAME_STATE) == PLAYING)
        r.check('4BEASY completion returns TITLE, never catalog tail',
                clear_loaded_stage(m, r, None)
                and u16(m, GAME_STATE) == TITLE
                and u8(m, CAMPAIGN_ORDINAL) == 8)
    r.finish()


if __name__ == '__main__':
    main()
