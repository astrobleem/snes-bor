#!/usr/bin/env python3
"""Focused G15-R2 audit and runtime gate for the verifier-only Normal 1A import.

Normal is intentionally not selectable: this probe uses the explicit internal
one-entry campaign solely to exercise the ordinary Stage_Load path.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant_in, read_block
import game_bor_startup_select as startup

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [os.path.join(ROOT, 'tools', 'bor_converter'),
                os.path.join(ROOT, 'tools', 'bg_converter')]
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402
from pak_extract import extract  # noqa: E402
from level_parse import parse_level  # noqa: E402
from spawn_parse import (parse_spawns, SpawnEvent, WaitEvent,
                         GroupEvent)  # noqa: E402

PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
EASY = r'DATA\EASY\1AEASY.TXT'
NORMAL = r'DATA\NORMAL\1A.TXT'

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PREV = pasm_constant_in('src/core/game_state.pasm', 'Game_StatePrev')
STAGE = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
CAMPAIGN = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SCROLL = pasm_constant_in('src/core/game_state.pasm', 'Stage_ScrollDirection')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
RIGHT = pasm_constant_in('tools/audio/stage_scroll_config.pasm', 'STAGE_SCROLL_RIGHT')
TIMES = pasm_constant_in('src/core/options.pasm', 'Bor_TimesCompleted')
CLEARED = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
MAX_X = pasm_constant_in('src/core/game_state.pasm', 'Stage_TrueMaxX')
POS_X = 0x7E1601


def u8(m, address):
    return read_block(m, address, 32)[0]


def u16(m, address):
    b = read_block(m, address, 32)
    return b[0] | (b[1] << 8)


def source_data():
    texts = {p: extract(PAK, p).decode('latin1') for p in (EASY, NORMAL)}
    parsed = {p: (parse_level(t, p), parse_spawns(t)) for p, t in texts.items()}
    return texts, parsed


def source_gate(r, texts, parsed):
    easy, normal = parsed[EASY][0], parsed[NORMAL][0]
    ee, ne = parsed[EASY][1], parsed[NORMAL][1]
    es = [e for e in ee if isinstance(e, SpawnEvent)]
    ns = [e for e in ne if isinstance(e, SpawnEvent)]
    r.check('authoritative Normal 1A path is present', NORMAL in texts)
    r.check('Normal 1A shares Easy presentation topology',
            normal.background == easy.background
            and normal.frontpanel == easy.frontpanel
            and normal.panels == easy.panels
            and normal.order == easy.order)
    r.check('Normal 1A is ordinary right-scrolling source content',
            'direction left' not in texts[NORMAL].lower()
            and 'direction down' not in texts[NORMAL].lower())
    r.check('Normal 1A has 35 spawns, 6 waits, 2 groups',
            len(ns) == 35
            and sum(isinstance(e, WaitEvent) for e in ne) == 6
            and sum(isinstance(e, GroupEvent) for e in ne) == 2)
    r.check('Easy comparison has 33 spawns and same wait/group shape',
            len(es) == 33
            and sum(isinstance(e, WaitEvent) for e in ee) == 6
            and sum(isinstance(e, GroupEvent) for e in ee) == 2)
    r.check('Normal 1A has no boss/hole/blocked special primitive',
            not any(e.boss for e in ns)
            and not any(k in texts[NORMAL].lower() for k in
                        ('\nhole ', '\nendhole ', '\nblocked ', '\nmap ')))
    r.check('Normal 1A uses only existing source identities',
            {e.character.lower() for e in ns} <=
            {'1up', 'shermie', 'yashiro', 'trash', 'ralf', 'angel'})
    # The differences are deliberately asserted against source fields, not
    # inferred from the packed blob or from the neighboring Easy stage.
    oxn = next(e for e in ns if e.character.lower() == 'yashiro'
               and e.alias == 'Oxnard')
    jimmy = next(e for e in ns if e.character.lower() == 'ralf'
                 and e.alias == 'Jimmy')
    angel = next(e for e in ns if e.character.lower() == 'angel')
    r.check('Normal-specific health tuning is source-preserved',
            oxn.health == 50 and jimmy.health == 55 and angel.health == 150)
    r.check('Normal-specific additions and group tuning are source-preserved',
            any(e.character.lower() == 'shermie' and e.alias == 'Hubchen'
                and e.at == 470 and e.health == 40 and e.map == 2
                for e in ns)
            and any(e.character.lower() == 'ralf' and e.alias == 'Ralph_Malph'
                    and e.at == 1400 and e.health == 60 and e.map == 1
                    for e in ns)
            and any(isinstance(e, GroupEvent) and e.group_min == 1
                    and e.group_max == 3 and e.at == 950 for e in ne))
    return texts, parsed


def catalog_gate(r):
    easy = next((i, s) for i, s in enumerate(build_rom.STAGE_CONFIGS)
                if s['source_level'].upper() == EASY.upper())
    normal = next((i, s) for i, s in enumerate(build_rom.STAGE_CONFIGS)
                  if s['source_level'].upper() == NORMAL.upper())
    stage = normal[1]
    blob = open(os.path.join(ROOT, stage['spawn']), 'rb').read()
    r.check('Normal 1A is appended at derived physical index 22',
            normal[0] == len(build_rom.STAGE_CONFIGS) - 1 == 22)
    r.check('Easy 1A remains physical index 0 and records are distinct',
            easy[0] == 0 and easy[0] != normal[0]
            and stage['spawn'] != easy[1]['spawn'])
    r.check('Normal spawn table is independent and complete', len(blob) == 43 * 10)
    r.check('Normal internal fixture is separate from source set mapping',
            build_rom.CAMPAIGN_STAGE_MAPS['BOR_NORMAL_1A_INTERNAL'] == [22]
            and 'BOR_NORMAL_1A_INTERNAL' not in build_rom.CAMPAIGN_CONFIGS.get(
                'BOR_ORIGINAL', {}).get('source_levels', []))
    generated = open(os.path.join(ROOT, 'tools', 'audio', 'campaign_config.pasm'),
                     encoding='utf-8').read()
    r.check('generated set availability remains Easy-only',
            ' .db 1, 0, 0, 0' in generated.replace('    ', ' ')
            and 'BorSet_CampaignMap:\n    .db CAMPAIGN_BOR_ORIGINAL, BOR_SET_UNMAPPED, BOR_SET_UNMAPPED, BOR_SET_UNMAPPED' in generated)
    return normal[0]


def runtime_gate(r, stage_index):
    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        before = u8(m, TIMES)
        # Internal one-entry campaign: real StageComplete_Dispatch -> typed
        # resolver -> ordinary Stage_Load. No direct Stage_Load call or stage
        # index write is used here.
        m.write_u8(CAMPAIGN, 3)
        m.write_u8(ORDINAL, 0xFF)
        # Establish an already-legitimate stage-clear handoff. The production
        # StageComplete_Dispatch owns resolver -> Stage_Load; the fixture only
        # supplies its documented pending edge and never calls either routine.
        m.write_u8(PENDING, 1)
        m.write_u16(GAME_STATE_PREV, PLAYING)
        m.write_u16(GAME_STATE, STAGECLEAR)
        reached = False
        for _ in range(600):
            m.run_frames(1)
            if u16(m, GAME_STATE) == PLAYING and u16(m, STAGE) == stage_index:
                reached = True
                break
        m.pause()
        if not reached:
            print('Normal 1A runtime diagnostic:', {
                'state': hex(u16(m, GAME_STATE)),
                'prev': hex(u16(m, GAME_STATE_PREV)),
                'campaign': u8(m, CAMPAIGN),
                'ordinal': u8(m, ORDINAL),
                'stage': u16(m, STAGE),
                'pending': u8(m, PENDING),
                'cleared': u8(m, CLEARED),
                'spawn_index': u8(m, SPAWN_INDEX),
                'spawn_count': u8(m, SPAWN_COUNT)}, flush=True)
        r.check('Normal 1A real stage-clear dispatch reaches PLAYING', reached)
        r.check('Normal 1A runtime geometry/direction/queue are correct',
                u16(m, STAGE) == stage_index and u16(m, GAME_STATE) == PLAYING
                and u8(m, SCROLL) == RIGHT and u8(m, SPAWN_COUNT) == 43)
        m.run_frames(90)
        m.pause()
        r.check('Normal 1A queue begins through ordinary Spawn_Play path',
                u8(m, SPAWN_INDEX) > 0 and u8(m, SPAWN_INDEX) <= u8(m, SPAWN_COUNT))
        r.check('partial Normal development load does not credit BOR completion',
                u8(m, TIMES) == before)
        # The generated internal campaign has exactly one entry. This proves
        # its logical boundary is separate from physical catalog adjacency;
        # no Easy/TMNT record can be selected by resolver continuation.
        r.check('Normal 1A internal campaign has TITLE boundary metadata',
                build_rom.CAMPAIGN_CONFIGS['BOR_NORMAL_1A_INTERNAL']['incomplete_boundary'] == 'TITLE')
    return reached


def main():
    r = Reporter('G15-BATCH-R2-NORMAL-1A', kind='GATE')
    texts, parsed = source_data()
    source_gate(r, texts, parsed)
    stage_index = catalog_gate(r)
    runtime_gate(r, stage_index)
    r.finish()


if __name__ == '__main__':
    main()
