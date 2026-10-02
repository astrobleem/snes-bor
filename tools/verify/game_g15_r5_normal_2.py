#!/usr/bin/env python3
"""Focused G15-R5 Normal 2 import and chained-next gate."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, exact_input_edge, open_session, pasm_constant_in, read_block
import game_bor_startup_select as startup

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
sys.path[:0] = [os.path.join(ROOT, 'tools', 'bor_converter'), os.path.join(ROOT, 'tools', 'bg_converter')]
import build_rom  # noqa: E402
from pak_extract import extract  # noqa: E402
from level_parse import parse_level  # noqa: E402
from spawn_parse import parse_spawns, SpawnEvent, WaitEvent, GroupEvent  # noqa: E402
from bor_levels import parse_levels_from_pak  # noqa: E402

PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
EASY = r'DATA\EASY\2EASY.TXT'
NORMAL = r'DATA\NORMAL\2.TXT'
STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
CAMPAIGN = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
STAGE = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
TIMES = pasm_constant_in('src/core/options.pasm', 'Bor_TimesCompleted')
COMPLETE_ACTIVE = pasm_constant_in('src/main.pasm', 'StageComplete_Active')
COMPLETE_TRACK = pasm_constant_in('src/main.pasm', 'Music_LastTrack')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')


def u8(m, a):
    return read_block(m, a, 32)[0]


def u16(m, a):
    b = read_block(m, a, 32)
    return b[0] | b[1] << 8


def source_gate(r):
    texts = {p: extract(PAK, p).decode('latin1') for p in (EASY, NORMAL)}
    levels = {p: parse_level(texts[p], p) for p in texts}
    events = {p: parse_spawns(texts[p]) for p in texts}
    easy, normal = levels[EASY], levels[NORMAL]
    es = [x for x in events[EASY] if isinstance(x, SpawnEvent)]
    ns = [x for x in events[NORMAL] if isinstance(x, SpawnEvent)]
    r.check('Normal 2 source path is authoritative', NORMAL in texts)
    r.check('Normal 2 reuses Easy 2 Bridge presentation',
            normal.background == easy.background and normal.frontpanel == easy.frontpanel
            and normal.panels == easy.panels and normal.order == easy.order
            and len(normal.panels) == 10 and len(normal.order) == 38)
    r.check('Normal 2 preserves authored music, bossmusic, holes and maps',
            all(token in texts[NORMAL].lower() for token in
                ('music\t\tdata/music/saviour.bor', 'bossmusic\tdata/music/1boss.bor',
                 'hole\t490', 'hole\t1900', 'hole\t2300'))
            and texts[NORMAL].lower().count('\nmap\t1') == 8)
    r.check('Normal 2 has 81 source records: 65 spawns, 6 waits, 10 groups',
            len(events[NORMAL]) == 81 and len(ns) == 65
            and sum(isinstance(x, WaitEvent) for x in events[NORMAL]) == 6
            and sum(isinstance(x, GroupEvent) for x in events[NORMAL]) == 10)
    r.check('Easy 2 comparison has 74 records and 58 spawns', len(events[EASY]) == 74 and len(es) == 58)
    r.check('Normal 2 adds supported Biker-K and Heavy identities',
            {x.character.lower() for x in ns} >= {"biker-k'", 'heavy', 'billy', 'fence'}
            and {'out/biker_k', 'out/heavy', 'out/billy'} <= set(build_rom.ROSTER_PREFIXES))
    r.check('Normal 2 source tuning differs from Easy 2',
            any(x.character.lower() == 'heavy' and x.boss and x.health == 300 for x in ns)
            and any(x.character.lower() == 'billy' and x.health == 200 for x in ns)
            and sum(x.character.lower() == "biker-k'" for x in ns) == 8
            and sum(x.character.lower() == "biker-k'" for x in es) == 5)
    normal_set = next(s for s in parse_levels_from_pak(PAK) if s.name == 'Normal')
    entries = normal_set.entries
    r.check('Normal source has next after 1C and after Normal 2',
            entries[2][0] == 'file' and entries[3][0] == 'next'
            and entries[4][0] == 'file' and entries[5][0] == 'next')


def catalog_gate(r):
    def find(path):
        return next((i, s) for i, s in enumerate(build_rom.STAGE_CONFIGS)
                    if s['source_level'].upper() == path.upper())
    normal = find(NORMAL)
    r.check('Normal 2 is derived catalog tail physical 25', normal[0] == len(build_rom.STAGE_CONFIGS) - 1 == 25)
    r.check('internal Normal map is 22,23,24,25',
            build_rom.CAMPAIGN_STAGE_MAPS['BOR_NORMAL_1A_INTERNAL'] == [22, 23, 24, 25])
    generated = open(os.path.join(ROOT, 'tools', 'audio', 'campaign_config.pasm'), encoding='ascii').read()
    r.check('generated boundary flags are 0,0,1,1',
            'Campaign_BorNormalDev_NextFlags:\n    .db 0, 0, 1, 1' in generated)
    r.check('Normal remains unavailable', 'BorSet_ContentAvailable:\n    .db 1, 0, 0, 0' in generated)


def load(m, ordinal, expected, r):
    startup.cold_to_title(m, r)
    startup.select_case(m, r, 'KULA')
    m.run_frames(60)
    m.write_u8(CAMPAIGN, 3); m.write_u8(ORDINAL, ordinal)
    m.write_u8(PENDING, 1); m.write_u16(STATE, STAGECLEAR)
    for _ in range(800):
        m.run_frames(1)
        if u16(m, STATE) == PLAYING and u16(m, STAGE) == expected:
            return True
    return False


def runtime_gate(r, stage):
    with open_session(__file__) as m:
        loaded = load(m, 2, stage, r)
        r.check('Normal 2 Stage_Load dispatches at ordinal 3', loaded)
        r.check('Normal 2 runtime queue count is 84', loaded and u8(m, SPAWN_COUNT) == 84)
        before = u8(m, TIMES)
        # A second clear from ordinal 3 has a real source `next`; it must enter
        # the same completion presenter before the partial boundary.
        m.write_u8(PENDING, 1); m.write_u16(STATE, STAGECLEAR)
        active = False
        for _ in range(30):
            m.run_frames(1)
            if u8(m, COMPLETE_ACTIVE):
                active = True; break
        r.check('Normal 2 real next enters showcomplete', active)
        r.check('completion track is active during Normal 2 boundary', active and u8(m, COMPLETE_TRACK) == 3)
        r.check('Normal partial clear does not credit set completion', u8(m, TIMES) == before)
        exact_input_edge(m, m.BTN_A, 2)
        for _ in range(300):
            m.run_frames(1)
            if u16(m, STATE) == TITLE:
                break
        r.check('Normal 2 completion skip reaches temporary TITLE', u16(m, STATE) == TITLE)
        r.check('completion path leaves set counter unchanged', u8(m, TIMES) == before)


def main():
    r = Reporter('G15-BATCH-R5-NORMAL-2', kind='GATE')
    source_gate(r); catalog_gate(r)
    stage = next(i for i, s in enumerate(build_rom.STAGE_CONFIGS) if s['source_level'].upper() == NORMAL.upper())
    runtime_gate(r, stage)
    r.finish()


if __name__ == '__main__':
    main()
