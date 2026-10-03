#!/usr/bin/env python3
"""Focused G15 Batch B gate for the source BOR 2EASY stage.

The gate checks the real PAK inventory and then enters 2EASY through the
accepted BOR campaign resolver.  Boss spawning and completion use the same
legal stage-clear preconditions as the accepted campaign gate; no campaign
state is written to skip the resolver.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, open_session, pasm_constant, pasm_constant_in,
                      read_block, repo_root_from, poll_until)
import game_bor_startup_select as startup

ROOT = repo_root_from(None)
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, 'tools', 'bor_converter'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'bg_converter'))
from pak_extract import extract  # noqa: E402
from entity_parse import parse_entity  # noqa: E402
from level_parse import parse_level  # noqa: E402
from spawn_parse import parse_spawns, SpawnEvent, WaitEvent, GroupEvent  # noqa: E402

PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
LEVEL_NAME = r'DATA\EASY\2EASY.TXT'
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
CAMPAIGN_ID = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
STAGE_CLEARED = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
STAGE_TRUE_MAX_X = pasm_constant_in('src/core/game_state.pasm', 'Stage_TrueMaxX')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_INPUT_DRIVEN_AI = pasm_constant('CHAR_INPUT_DRIVEN_AI')
CHAR_INPUT_DRIVEN_PROP = pasm_constant('CHAR_INPUT_DRIVEN_PROP')
CHAR_PICKUP_TYPE = pasm_constant('CHAR_PICKUP_TYPE')
PICKUP_TYPE_APPLE = pasm_constant('PICKUP_TYPE_APPLE')
PICKUP_TYPE_2P_FLAG = pasm_constant('PICKUP_TYPE_2P_FLAG')
CHAR_ROSTER_INDEX = pasm_constant('CHAR_ROSTER_INDEX')
ENTITY_BASE = 0x7E0A00
ENTITIES = [ENTITY_BASE + i * CHAR_ZP_LEN for i in range(6)]
# Screen_PosX is a direct-page data symbol rather than a NAME = constant;
# this is the established address used by the accepted campaign gate.
SCREEN_POS_X = 0x7E1601
SCREEN_MAX_X = 0x7E160E
SCREEN_TARGET_X = 0x7E1616
TWO_PLAYER = pasm_constant('G13_TwoPlayerEnabled')
P1_OUT = pasm_constant('G13_P1Out')
P2_OUT = pasm_constant('G13_P2Out')
ENTITY1_ITEM = pasm_constant_in('src/core/spawn.pasm', 'Entity1_ItemRosterIdx')


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def source_inventory():
    text = extract(PAK, LEVEL_NAME).decode('latin1')
    level = parse_level(text, LEVEL_NAME)
    events = parse_spawns(text)
    spawns = [e for e in events if isinstance(e, SpawnEvent)]
    waits = [e for e in events if isinstance(e, WaitEvent)]
    groups = [e for e in events if isinstance(e, GroupEvent)]
    entities = {
        name: parse_entity(extract(PAK, entry).decode('latin1'))
        for name, entry in {
            'Heavy': r'DATA\CHARS\HEAVY\HEAVY.TXT',
            "Biker-K'": r"DATA\CHARS\BIKER-K\BIKER-K.TXT",
            'Fence': r'DATA\CHARS\MISC\FENCE.TXT',
        }.items()
    }
    return text, level, events, spawns, waits, groups, entities


def clear_loaded_stage(m, r, target_stage):
    count = u8(m, SPAWN_COUNT)
    m.write_u8(SPAWN_INDEX, count)
    true_max = u16(m, STAGE_TRUE_MAX_X)
    m.write_u16(SCREEN_POS_X, true_max)
    m.write_u16(SCREEN_MAX_X, true_max)
    m.write_u16(SCREEN_TARGET_X, true_max)
    for _ in range(240):
        for base in ENTITIES[1:]:
            if u8(m, base + CHAR_INPUT_DRIVEN) == CHAR_INPUT_DRIVEN_AI:
                m.write_u8(base + CHAR_HP, 0)
        if u8(m, STAGE_CLEARED) == 1:
            break
        m.run_frames(1)
        m.pause()
    if u8(m, STAGE_CLEARED) != 1:
        return False
    m.pause()
    if target_stage is None:
        return poll_until(m, lambda s: u16(s, GAME_STATE) == TITLE,
                          max_frames=120, step=5)
    return poll_until(m, lambda s: u16(s, STAGE_INDEX) == target_stage
                      and u16(s, GAME_STATE) == PLAYING,
                      max_frames=600, step=5)


def probe_2pitem_runtime(m, r):
    """Exercise the actual break/reveal predicate with the loaded 2EASY
    session. The item effect remains ordinary collector-owned pickup data."""
    m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
    m.write_u8(TWO_PLAYER, 0)
    m.write_u8(P1_OUT, 0)
    m.write_u8(P2_OUT, 1)
    m.write_u8(ENTITIES[1] + CHAR_INPUT_DRIVEN, CHAR_INPUT_DRIVEN_PROP)
    m.write_u8(ENTITIES[1] + pasm_constant('CHAR_POS_X'), 240)
    m.write_u8(ENTITIES[1] + pasm_constant('CHAR_POS_Y'), 200)
    m.write_u8(ENTITIES[1] + CHAR_HP, 1)
    m.write_u8(ENTITIES[1] + CHAR_PICKUP_TYPE,
                PICKUP_TYPE_APPLE | PICKUP_TYPE_2P_FLAG)
    m.write_u8(ENTITY1_ITEM, build_rom.ROSTER_PREFIXES.index('out/apple'))
    m.run_frames(10)
    m.pause()
    one_player_hidden = (u8(m, ENTITY1_ITEM) == 0
                         and u8(m, ENTITIES[1] + CHAR_PICKUP_TYPE) == 0)

    m.write_u8(TWO_PLAYER, 1)
    m.write_u8(P1_OUT, 0)
    m.write_u8(P2_OUT, 0)
    m.write_u8(ENTITIES[1] + CHAR_INPUT_DRIVEN, CHAR_INPUT_DRIVEN_PROP)
    m.write_u8(ENTITIES[1] + pasm_constant('CHAR_POS_X'), 240)
    m.write_u8(ENTITIES[1] + pasm_constant('CHAR_POS_Y'), 200)
    m.write_u8(ENTITIES[1] + CHAR_HP, 1)
    m.write_u8(ENTITIES[1] + CHAR_PICKUP_TYPE,
                PICKUP_TYPE_APPLE | PICKUP_TYPE_2P_FLAG)
    m.write_u8(ENTITY1_ITEM, build_rom.ROSTER_PREFIXES.index('out/apple'))
    m.run_frames(10)
    m.pause()
    two_player_revealed = (u8(m, ENTITY1_ITEM) == 0
                           and u8(m, ENTITIES[1] + CHAR_PICKUP_TYPE) == PICKUP_TYPE_APPLE)
    r.check('2EASY 2pitem hides contained item with one active player',
            one_player_hidden)
    r.check('2EASY 2pitem reveals contained item with two active players',
            two_player_revealed)


def main():
    r = Reporter('G15-BATCH-B-2EASY', kind='GATE')
    text, level, events, spawns, waits, groups, entities = source_inventory()
    stage = next(s for s in build_rom.STAGE_CONFIGS
                 if s['source_level'].upper() == LEVEL_NAME.upper())
    stage_index = build_rom.STAGE_CONFIGS.index(stage)
    blob = open(os.path.join(ROOT, stage['spawn']), 'rb').read()
    records = [blob[i:i + 10] for i in range(0, len(blob), 10)]

    r.check('2EASY is appended as a catalog identity', stage_index == 11)
    r.check('BOR campaign resolves 1A,1B,1C,2EASY explicitly',
            build_rom.CAMPAIGN_STAGE_MAPS['BOR_ORIGINAL'] == [0, 1, 2, 11, 12])
    r.check('source bridge map/order is complete',
            level.background.lower().endswith('bridge\\harbor.gif')
            and len(level.panels) == 10 and len(level.order) == 38)
    r.check('source stage has three holes and expected event classes',
            text.lower().count('\nhole') == 3
            and len(spawns) == 58 and len(waits) == 6 and len(groups) == 10)
    r.check('packed 2EASY spawn table has all 77 ordered records',
            len(records) == 77)
    r.check('source contains the real Fence/item records',
            sum(bool(e.character.lower() == 'fence' and e.item) for e in spawns) == 6
            and sum(e.if2p for e in spawns) == 2)
    heavy = next(e for e in spawns if e.character.lower() == 'heavy')
    heavy_index = next(i for i, e in enumerate(events)
                       if isinstance(e, SpawnEvent) and e is heavy)
    r.check('Heavy source record is boss HP 250 at trigger 3200',
            heavy.boss and heavy.health == 250 and heavy.at == 3200)
    heavy_record_index = heavy_index + 3
    r.check('Heavy is identified in the packed boss record',
            (records[heavy_record_index][6] & 7) == 5
            and records[heavy_record_index][9] == build_rom.ROSTER_PREFIXES.index('out/heavy'))
    r.check('Heavy source model is enemy HP 300 with real core roles',
            entities['Heavy']['type'] == 'enemy'
            and entities['Heavy']['health'] == 300
            and all(name in entities['Heavy']['animations'] for name in
                    ('idle', 'walk', 'fall', 'rise', 'attack1')))
    r.check("Biker-K' source record is retained", any(e.character == "Biker-K'" for e in spawns))
    r.check("Biker-K' source model remains sparse for the subtype runtime",
            entities["Biker-K'"]['type'] == 'enemy'
            and set(k.lower() for k in entities["Biker-K'"]['animations']) == {'idle', 'pain'})
    r.check('Fence source model is a breakable obstacle',
            entities['Fence']['type'] == 'obstacle'
            and set(k.lower() for k in entities['Fence']['animations']) == {'idle', 'fall'})

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        m.pause()
        for current in (0, 1, 2):
            target = current + 1 if current < 2 else stage_index
            r.check(f'campaign stage {current} clears through production edge',
                    clear_loaded_stage(m, r, target))
            if current < 2:
                r.check(f'campaign advances {current} -> {current + 1}',
                        u16(m, STAGE_INDEX) == current + 1
                        and u16(m, GAME_STATE) == PLAYING)
            else:
                r.check('1C -> 2EASY resolves physical stage 11',
                        u16(m, STAGE_INDEX) == stage_index
                        and u8(m, CAMPAIGN_ID) == 0
                        and u8(m, CAMPAIGN_ORDINAL) == 3
                        and u16(m, GAME_STATE) == PLAYING)

        m.set_input(m.BTN_RIGHT, 90)
        m.pause()
        m.run_frames(90)
        m.pause()
        m.pause()
        r.check('2EASY early authored queue begins in PLAYING',
                u8(m, SPAWN_INDEX) > 0 and u16(m, GAME_STATE) == PLAYING)
        probe_2pitem_runtime(m, r)

        r.check('Heavy runtime identity is available to the loaded boss record',
                build_rom.ROSTER_PREFIXES.index('out/heavy') == records[heavy_record_index][9])
        r.check('Heavy defeat advances to imported 3AEASY',
                clear_loaded_stage(m, r, 12)
                and u16(m, GAME_STATE) == PLAYING
                and u8(m, CAMPAIGN_ORDINAL) == 4)
        r.check('3AEASY completion returns TITLE, not catalog tail/TMNT',
                clear_loaded_stage(m, r, None)
                and u16(m, GAME_STATE) == TITLE and u8(m, CAMPAIGN_ORDINAL) == 4)
    r.finish()


if __name__ == '__main__':
    main()
