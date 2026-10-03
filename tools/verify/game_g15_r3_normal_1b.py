#!/usr/bin/env python3
"""Focused G15-R3 source, catalog, and internal Normal 1A->1B gate."""
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
from spawn_parse import parse_spawns, SpawnEvent, WaitEvent, GroupEvent  # noqa: E402

PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
EASY = r'DATA\EASY\1BEASY.TXT'
NORMAL_A = r'DATA\NORMAL\1A.TXT'
NORMAL_B = r'DATA\NORMAL\1B.TXT'
STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PREV = pasm_constant_in('src/core/game_state.pasm', 'Game_StatePrev')
STAGE = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
CAMPAIGN = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
CLEARED = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
RIGHT = pasm_constant_in('tools/audio/stage_scroll_config.pasm', 'STAGE_SCROLL_RIGHT')
SCROLL = pasm_constant_in('src/core/game_state.pasm', 'Stage_ScrollDirection')
POS_X = 0x7E1601
TIMES = pasm_constant_in('src/core/options.pasm', 'Bor_TimesCompleted')
COMPLETE_ACTIVE = pasm_constant_in('src/main.pasm', 'StageComplete_Active')
COMPLETE_ADVANCES = pasm_constant_in('src/main.pasm', 'StageComplete_AdvanceCount')
LAST_TRACK = pasm_constant_in('src/main.pasm', 'Music_LastTrack')


def u8(m, address):
    return read_block(m, address, 32)[0]


def u16(m, address):
    b = read_block(m, address, 32)
    return b[0] | b[1] << 8


def source_gate(r):
    texts = {p: extract(PAK, p).decode('latin1') for p in (EASY, NORMAL_A, NORMAL_B)}
    levels = {p: parse_level(texts[p], p) for p in texts}
    events = {p: parse_spawns(texts[p]) for p in texts}
    e, n = levels[EASY], levels[NORMAL_B]
    ee, ne = events[EASY], events[NORMAL_B]
    es = [x for x in ee if isinstance(x, SpawnEvent)]
    ns = [x for x in ne if isinstance(x, SpawnEvent)]
    r.check('Normal 1B source path is authoritative', NORMAL_B in texts)
    r.check('Normal 1B reuses Easy 1B presentation and music',
            n.background == e.background and n.frontpanel == e.frontpanel
            and n.panels == e.panels and n.order == e.order
            and any(x.lower().split()[:2] == ['music', 'data/music/kof.bor']
                    for x in texts[NORMAL_B].splitlines()))
    r.check('Normal 1B is right-scrolling with Bar geometry',
            'direction left' not in texts[NORMAL_B].lower()
            and 'direction down' not in texts[NORMAL_B].lower()
            and len(n.panels) == 2 and len(n.order) == 14)
    r.check('Normal 1B queue has 37 records: 30 spawns, 5 waits, 2 groups',
            len(ne) == 37 and len(ns) == 30
            and sum(isinstance(x, WaitEvent) for x in ne) == 5
            and sum(isinstance(x, GroupEvent) for x in ne) == 2)
    r.check('Easy 1B comparison has 35 records: 28 spawns, 5 waits, 2 groups',
            len(ee) == 35 and len(es) == 28
            and sum(isinstance(x, WaitEvent) for x in ee) == 5
            and sum(isinstance(x, GroupEvent) for x in ee) == 2)
    r.check('Normal 1B has no unsupported boss/hole/blocked primitive',
            not any(x.boss for x in ns)
            and not any(k in texts[NORMAL_B].lower() for k in
                        ('\nhole ', '\nendhole ', '\nblocked ', '\nmap ')))
    r.check('Normal 1B identities are all already packed',
            {x.character.lower() for x in ns} <=
            {'angel', 'chair', 'ralf', 'shermie', 'table', 'yashiro'})
    # Source-specific encounter assertions, including the changed 2P item.
    r.check('Normal 1B preserves added wave and tuning',
            sum(x.character.lower() == 'ralf' and x.at == 280 for x in ns) == 2
            and sum(x.character.lower() == 'ralf' and x.at == 280 for x in es) == 2
            and sum(x.character.lower() == 'yashiro' and x.at == 280 for x in ns) == 1
            and sum(x.character.lower() == 'yashiro' and x.at == 280 for x in es) == 0
            and any(x.character.lower() == 'angel' and x.at == 320
                    and x.health == 100 for x in ns)
            and any(x.character.lower() == 'ralf' and x.at == 320
                    and x.health == 70 for x in ns)
            and any(x.character.lower() == 'chair' and x.at == 721
                    and x.item == 'Apple' and x.if2p for x in ns))
    return texts, events


def catalog_gate(r):
    def find(path):
        return next((i, s) for i, s in enumerate(build_rom.STAGE_CONFIGS)
                    if s['source_level'].upper() == path.upper())
    ea, eb = find(r'DATA\EASY\1AEASY.TXT'), find(EASY)
    na, nb = find(NORMAL_A), find(NORMAL_B)
    blob = open(os.path.join(ROOT, nb[1]['spawn']), 'rb').read()
    r.check('Normal 1B is appended at derived physical index 23',
            nb[0] == len(build_rom.STAGE_CONFIGS) - 1 == 23)
    r.check('Normal 1A stays physical 22 and Easy records stay unchanged',
            na[0] == 22 and ea[0] == 0 and eb[0] == 1
            and len({ea[0], eb[0], na[0], nb[0]}) == 4)
    r.check('Normal 1B has an independent 37-record packed queue', len(blob) == 370)
    r.check('internal Normal campaign is exactly 1A then 1B',
            build_rom.CAMPAIGN_STAGE_MAPS['BOR_NORMAL_1A_INTERNAL'] == [22, 23]
            and len(build_rom.CAMPAIGN_ENTRY_MAPS['BOR_NORMAL_1A_INTERNAL']) == 2)
    generated = open(os.path.join(ROOT, 'tools', 'audio', 'campaign_config.pasm'),
                     encoding='utf-8').read()
    r.check('Normal remains unavailable and source thresholds remain unchanged',
            'BorSet_ContentAvailable:\n    .db 1, 0, 0, 0' in generated
            and 'BorSet_IfComplete:\n    .db 0, 0, 0, 1' in generated)
    return na[0], nb[0]


def runtime_gate(r, stage_a, stage_b):
    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        before_times_1b = u8(m, TIMES)
        before_times = u8(m, TIMES)
        before_advances = u16(m, COMPLETE_ADVANCES)
        before_track = u8(m, LAST_TRACK)
        m.write_u8(CAMPAIGN, 3)
        m.write_u8(ORDINAL, 0xFF)
        m.write_u8(PENDING, 1)
        m.write_u16(STATE, STAGECLEAR)
        first = False
        for _ in range(600):
            m.run_frames(1)
            if u16(m, STATE) == PLAYING and u16(m, STAGE) == stage_a:
                first = True
                break
        m.pause()
        r.check('internal Normal 1A loads through ordinary Stage_Load', first)
        r.check('1A->1B has no completion presentation in internal path',
                u8(m, TIMES) == before_times and u8(m, COMPLETE_ACTIVE) == 0
                and u16(m, COMPLETE_ADVANCES) == before_advances)

    # Load ordinal 1 through the same real StageComplete_Dispatch machinery in
    # a clean session. The first session above proves ordinal 0; this avoids
    # allowing the already-running 1A fixture to reach its edge while the
    # second handoff is being armed.
    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        m.write_u8(CAMPAIGN, 3)
        m.write_u8(ORDINAL, 0)
        m.write_u8(PENDING, 1)
        m.write_u16(STATE, STAGECLEAR)
        loaded = False
        for _ in range(600):
            m.run_frames(1)
            if u16(m, STATE) == PLAYING and u16(m, STAGE) == stage_b:
                loaded = True
                break
        m.pause()
        r.check('Normal 1B real Stage_Load resolves internal ordinal 1', loaded)
        r.check('Normal 1B runtime queue/direction are correct',
                loaded and u8(m, SPAWN_COUNT) == 37 and u8(m, SCROLL) == RIGHT)
        m.run_frames(90)
        m.pause()
        r.check('Normal 1B queue begins through ordinary Spawn_Play',
                loaded and u8(m, SPAWN_INDEX) > 0)
        r.check('partial Normal internal boundary is TITLE-only metadata',
                build_rom.CAMPAIGN_CONFIGS['BOR_NORMAL_1A_INTERNAL']['incomplete_boundary'] == 'TITLE')
        r.check('partial Normal path does not credit set completion',
                u8(m, TIMES) == before_times_1b and u8(m, COMPLETE_ACTIVE) == 0)


def main():
    r = Reporter('G15-BATCH-R3-NORMAL-1B', kind='GATE')
    source_gate(r)
    stage_a, stage_b = catalog_gate(r)
    runtime_gate(r, stage_a, stage_b)
    r.finish()


if __name__ == '__main__':
    main()
