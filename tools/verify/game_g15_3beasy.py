#!/usr/bin/env python3
"""Focused G15 Batch D gate for the source BOR 3BEASY stage."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant_in
import game_bor_startup_select as startup
from game_g15_2easy import clear_loaded_stage, u8, u16

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, 'tools', 'bor_converter'))
from pak_extract import extract  # noqa: E402
from level_parse import parse_level  # noqa: E402
from spawn_parse import parse_spawns, SpawnEvent, WaitEvent, GroupEvent  # noqa: E402

PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
LEVEL = r'DATA\EASY\3BEASY.TXT'
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
CAMPAIGN_ID = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
def main():
    r = Reporter('G15-BATCH-D-3BEASY', kind='GATE')
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
    records = [blob[i:i + 10] for i in range(0, len(blob), 10)]
    names = [e.character.lower() for e in spawns]
    source_names = [e.character.lower() for e in spawns]

    r.check('3BEASY is appended at physical catalog index 13', stage_index == 13)
    r.check('BOR campaign resolves through 3BEASY then TITLE',
            build_rom.CAMPAIGN_STAGE_MAPS['BOR_ORIGINAL'] == [0, 1, 2, 11, 12, 13])
    r.check('source boat panel/order inventory is preserved',
            level.background.lower().endswith('boat\\back.gif')
            and level.frontpanel.lower().endswith('boat\\front.gif')
            and len(level.panels) == 3 and len(level.order) == 24)
    r.check('source event classes and ordering are preserved',
            len(events) == 38 and len(spawns) == 31 and len(waits) == 2
            and len(groups) == 5 and names[:2] == ['ralf', 'ralf']
            and names[-3:] == ["k'", "k'", "k'"])
    r.check('3BEASY has no unrepresented hole/endhole/blocked records',
            all(word not in text.lower() for word in ('\nhole', '\nendhole', '\nblocked')))
    r.check('packed queue preserves authored waits/groups and item records',
            len(records) == 38
            and sum((rec[6] & 7) == 2 for rec in records) == 2
            and sum((rec[6] & 7) == 3 for rec in records) == 5
            and sum((rec[6] & 7) == 1 for rec in records) == 4
            and records[5][8] != 0 and records[6][8] != 0)
    r.check('3BEASY item/2pitem source distinction is preserved',
            [(e.character.lower(), e.item, e.if2p) for e in spawns
             if e.item] == [('box', 'meat', False), ('box', 'meat', True),
                            ('box', 'apple', False), ('box', 'apple', False)])
    expected = {'angel': 29, 'shermie': 30, "k'": 31, 'box': 33}
    source_indices = {name: build_rom.ROSTER_PREFIXES.index('out/' + alias)
                      for name, alias in [('angel', 'angel'), ('shermie', 'shermie'),
                                          ("k'", 'k_prime'), ('box', 'box')]}
    r.check('Batch C runtime-only identities remain appended and unselectable',
            source_indices == expected
            and build_rom.PLAYABLE_ROSTER_COUNT == 13
            and all(not e['normal_player_selectable']
                     for e in build_rom.ROSTER_CONFIGS[29:]))
    r.check('identified enemy records use their real runtime identities',
            {rec[9] for rec in records if (rec[6] & 7) == 5
             and ((rec[6] >> 5) & 3) == 2}
            >= {29, 30, 31})
    r.check('no authored boss flag: final encounter is ordinary queue exhaustion',
            not any(e.boss for e in spawns)
            and source_names[-3:] == ["k'", "k'", "k'"]
            and isinstance(events[-1], WaitEvent))

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        for current, target in ((0, 1), (1, 2), (2, 11), (11, 12), (12, stage_index)):
            r.check(f'campaign edge {current} reaches next stage',
                    clear_loaded_stage(m, r, target))
        r.check('3AEASY -> 3BEASY enters PLAYING at campaign ordinal 5',
                u16(m, GAME_STATE) == PLAYING and u16(m, STAGE_INDEX) == stage_index
                and u8(m, CAMPAIGN_ID) == 0 and u8(m, CAMPAIGN_ORDINAL) == 5)
        m.run_frames(120)
        m.pause()
        m.set_input(m.BTN_RIGHT, 90)
        m.run_frames(90)
        m.pause()
        r.check('3BEASY early authored queue begins',
                u8(m, SPAWN_INDEX) > 0 and u16(m, GAME_STATE) == PLAYING)
        r.check('3BEASY final authored record is K-prime',
                records[-4][9] == 31 and records[-3][9] == 31
                and records[-2][9] == 31 and (records[-1][6] & 7) == 2)
        r.check('3BEASY completion returns TITLE, never TMNT',
                clear_loaded_stage(m, r, None) and u16(m, GAME_STATE) == TITLE
                and u8(m, CAMPAIGN_ORDINAL) == 5)
    r.finish()


if __name__ == '__main__':
    main()
