#!/usr/bin/env python3
"""Focused G15 Batch C gate for the source BOR 3AEASY stage."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant, pasm_constant_in, read_block
import game_bor_startup_select as startup
from game_g15_2easy import clear_loaded_stage, u8, u16

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, 'tools', 'bor_converter'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'bg_converter'))
from pak_extract import extract  # noqa: E402
from level_parse import parse_level  # noqa: E402
from spawn_parse import parse_spawns, SpawnEvent, WaitEvent, GroupEvent  # noqa: E402

PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
LEVEL = r'DATA\EASY\3AEASY.TXT'
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
CAMPAIGN_ID = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
SPAWN_TABLE = pasm_constant_in('src/core/spawn.pasm', 'SpawnTable_Wram')
SPAWN_WAITING = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Waiting')
SPAWN_GROUP_MAX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMax')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_ROSTER_INDEX = pasm_constant('CHAR_ROSTER_INDEX')
ENTITY_BASE = 0x7E0A00
ENTITIES = [ENTITY_BASE + i * CHAR_ZP_LEN for i in range(6)]


def main():
    r = Reporter('G15-BATCH-C-3AEASY', kind='GATE')
    text = extract(PAK, LEVEL).decode('latin1')
    level = parse_level(text, LEVEL)
    events = parse_spawns(text)
    spawns = [e for e in events if isinstance(e, SpawnEvent)]
    waits = [e for e in events if isinstance(e, WaitEvent)]
    groups = [e for e in events if isinstance(e, GroupEvent)]
    stage = next(s for s in build_rom.STAGE_CONFIGS if s['source_level'].upper() == LEVEL.upper())
    stage_index = build_rom.STAGE_CONFIGS.index(stage)
    blob = open(os.path.join(ROOT, stage['spawn']), 'rb').read()
    records = [blob[i:i + 10] for i in range(0, len(blob), 10)]
    names = [e.character.lower() for e in spawns]

    r.check('3AEASY is appended at physical catalog index 12', stage_index == 12)
    r.check('BOR campaign resolves through 3AEASY then its TITLE boundary',
            build_rom.CAMPAIGN_STAGE_MAPS['BOR_ORIGINAL'] == [0, 1, 2, 11, 12])
    r.check('source boat panel/order inventory is preserved',
            level.background.lower().endswith('boat2\\back.gif')
            and len(level.panels) == 6 and len(level.order) == 30)
    r.check('source event classes and ordering are preserved',
            len(events) == 38 and len(spawns) == 31 and len(waits) == 3
            and len(groups) == 4 and names[:2] == ['angel', 'angel']
            and names[-1] == 'billy')
    r.check('3AEASY has no unrepresented hole/endhole/blocked records',
            all(word not in text.lower() for word in ('\nhole', '\nendhole', '\nblocked')))
    r.check('3AEASY packed queue preserves waits/groups and authored box items',
            len(records) == 38
            and sum((rec[6] & 7) == 2 for rec in records) == 3
            and sum((rec[6] & 7) == 3 for rec in records) == 4
            and sum((rec[6] & 7) == 1 for rec in records) == 2)
    r.check('runtime-only source identities are not selectable',
            build_rom.PLAYABLE_ROSTER_COUNT == 13
            and all(not e['normal_player_selectable'] for e in build_rom.ROSTER_CONFIGS[29:]))
    expected = {'angel': 29, 'shermie': 30, "k'": 31, 'billy': 32, 'box': 33}
    source_indices = {name: build_rom.ROSTER_PREFIXES.index('out/' + alias)
                      for name, alias in [('angel', 'angel'), ('shermie', 'shermie'),
                                          ("k'", 'k_prime'), ('billy', 'billy'), ('box', 'box')]}
    r.check('3AEASY source models map to appended runtime identities',
            source_indices == expected)
    r.check('authored new enemy records carry their own runtime identities',
            {rec[9] for rec in records
             if (rec[6] & 7) == 5 and ((rec[6] >> 5) & 3) == 2}
            >= {expected[name] for name in ('angel', 'shermie', "k'", 'billy')})

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        for current, target in ((0, 1), (1, 2), (2, 11), (11, stage_index)):
            r.check(f'campaign edge {current} reaches next stage',
                    clear_loaded_stage(m, r, target))
        r.check('2EASY -> 3AEASY enters PLAYING at campaign ordinal 4',
                u16(m, GAME_STATE) == PLAYING and u16(m, STAGE_INDEX) == stage_index
                and u8(m, CAMPAIGN_ID) == 0 and u8(m, CAMPAIGN_ORDINAL) == 4)
        m.run_frames(120)
        m.pause()
        m.set_input(m.BTN_RIGHT, 90)
        m.run_frames(90)
        m.pause()
        r.check('3AEASY early authored queue begins',
                u8(m, SPAWN_INDEX) > 0 and u16(m, GAME_STATE) == PLAYING)
        r.check('3AEASY final authored record is Billy',
                records[-1][9] == expected['billy']
                and ((records[-1][6] >> 5) & 3) == 2)
        r.check('3AEASY completion returns TITLE, never TMNT',
                clear_loaded_stage(m, r, None) and u16(m, GAME_STATE) == TITLE
                and u8(m, CAMPAIGN_ORDINAL) == 4)
    r.finish()


if __name__ == '__main__':
    main()
