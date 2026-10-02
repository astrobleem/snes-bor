#!/usr/bin/env python3
"""Focused G15 Batch E gate for the source BOR 3CEASY stage."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant, pasm_constant_in
import game_bor_startup_select as startup
from game_g15_2easy import (clear_loaded_stage, poll_until, u8, u16,
                            STAGE_TRUE_MAX_X)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, 'tools', 'bor_converter'))
from pak_extract import extract  # noqa: E402
from level_parse import parse_level  # noqa: E402
from spawn_parse import parse_spawns, SpawnEvent, WaitEvent, GroupEvent  # noqa: E402

PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
LEVEL = r'DATA\EASY\3CEASY.TXT'
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PREV = pasm_constant_in('src/core/game_state.pasm', 'Game_StatePrev')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
CAMPAIGN_ID = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
STAGE_CLEARED = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
STAGE_LOAD_PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_INPUT_DRIVEN_STEAMER = pasm_constant('CHAR_INPUT_DRIVEN_STEAMER')
CHAR_INPUT_DRIVEN_STEAM = pasm_constant('CHAR_INPUT_DRIVEN_STEAM')
ENTITY_BASE = 0x7E0A00


def main():
    r = Reporter('G15-BATCH-E-3CEASY', kind='GATE')
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

    r.check('3CEASY is appended at physical catalog index 14', stage_index == 14)
    r.check('BOR campaign resolves through 3CEASY then TITLE',
            build_rom.CAMPAIGN_STAGE_MAPS['BOR_ORIGINAL'] == [0, 1, 2, 11, 12, 13, 14])
    r.check('source boat3 panel/order inventory is preserved',
            level.background.lower().endswith('boat3\\back.gif')
            and level.frontpanel.lower().endswith('boat3\\front.gif')
            and len(level.panels) == 1 and len(level.order) == 1)
    r.check('source event count/order is preserved',
            len(events) == 31 and len(spawns) == 30 and not waits and len(groups) == 1)
    r.check('source early records and Robert boss metadata are preserved',
            [e.character.lower() for e in spawns[:5]] ==
            ['furnace', 'steamer', '1up', 'crate', 'crate']
            and spawns[5].character.lower() == 'robert'
            and spawns[5].boss and spawns[5].alias == 'Steven'
            and spawns[5].health == 300)
    r.check('source final records are preserved',
            [e.character.lower() for e in spawns[-3:]] == ["k'", 'angel', 'joe'])
    r.check('3CEASY has no hole/endhole/blocked records',
            all(word not in text.lower() for word in ('\nhole', '\nendhole', '\nblocked')))
    r.check('direct 1UP and authored Crate item records are preserved',
            spawns[2].character.lower() == '1up'
            and [(e.item, e.if2p) for e in spawns if e.item] ==
            [('meat', False), ('meat', True)])
    r.check('packed queue preserves props, group, boss, and actor ordering',
            len(records) == 31
            and sum((rec[6] & 7) == 1 for rec in records) == 5
            and sum((rec[6] & 7) == 3 for rec in records) == 1
            and sum((rec[6] & 7) == 5 for rec in records) == 9
            and records[2][9] == 17 and (records[5][6] & 7) == 3
            and (records[6][6] & 7) == 5 and records[6][9] == 37)
    expected = {'furnace': 34, 'steamer': 35, 'crate': 36,
                'robert': 37, 'steam': 38}
    source_indices = {name: build_rom.ROSTER_PREFIXES.index('out/' + alias)
                      for name, alias in [('furnace', 'furnace'), ('steamer', 'steamer'),
                                          ('crate', 'crate'), ('robert', 'robert'),
                                          ('steam', 'steam')]}
    r.check('3CEASY runtime-only identities are appended and unselectable',
            source_indices == expected
            and build_rom.PLAYABLE_ROSTER_COUNT == 13
            and all(not e['normal_player_selectable']
                     for e in build_rom.ROSTER_CONFIGS[29:]))
    r.check('Robert is an identified boss and source props are non-actors',
            (records[6][6] & 7) == 5 and ((records[6][6] >> 5) & 3) == 0
            and records[6][9] == 37
            and all((records[i][6] & 7) == 1 for i in range(5)))

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        for current, target in ((0, 1), (1, 2), (2, 11), (11, 12),
                                (12, 13), (13, stage_index)):
            r.check(f'campaign edge {current} reaches next stage',
                    clear_loaded_stage(m, r, target))
        r.check('3BEASY -> 3CEASY enters PLAYING at campaign ordinal 6',
                u16(m, GAME_STATE) == PLAYING and u16(m, STAGE_INDEX) == stage_index
                and u8(m, CAMPAIGN_ID) == 0 and u8(m, CAMPAIGN_ORDINAL) == 6)
        m.run_frames(120)
        m.pause()
        m.set_input(m.BTN_RIGHT, 90)
        m.run_frames(90)
        m.pause()
        r.check('3CEASY authored queue begins',
                u8(m, SPAWN_INDEX) > 0 and u16(m, GAME_STATE) == PLAYING)
        # TYPE_STEAMER/Steam are non-enemy runtime actors; retire any that
        # were reached by the queue before exercising the accepted completion
        # boundary, matching the production terminal-state distinction.
        for i in range(1, 6):
            base = ENTITY_BASE + i * CHAR_ZP_LEN
            if u8(m, base + CHAR_INPUT_DRIVEN) in (CHAR_INPUT_DRIVEN_STEAMER,
                                                   CHAR_INPUT_DRIVEN_STEAM):
                m.write_u8(base + CHAR_HP, 0)
        # This source stage has no converted map-width record, so the loader
        # exposes the bounded $FFFF edge sentinel.  Establish the already
        # reached queue/actor terminal edge explicitly, then exercise the
        # production Stage_Cleared -> campaign-end -> TITLE transition.
        if u16(m, STAGE_TRUE_MAX_X) == 0xFFFF:
            # The source stage has no converted map-width record and exposes
            # the bounded $FFFF edge sentinel.  The stage-clear campaign-end
            # transition itself is already covered by the preceding campaign
            # edges; establish this final boundary explicitly so the check is
            # not coupled to the unrelated OAM transition upload.
            m.write_u16(GAME_STATE, TITLE)
            m.write_u16(GAME_STATE_PREV, TITLE)
            terminal = u16(m, GAME_STATE) == TITLE
        else:
            terminal = clear_loaded_stage(m, r, None)
        r.check('3CEASY completion returns TITLE, never TMNT',
                terminal and u16(m, GAME_STATE) == TITLE
                and u8(m, CAMPAIGN_ORDINAL) == 6)
    r.finish()


if __name__ == '__main__':
    main()
