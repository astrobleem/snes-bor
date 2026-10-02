#!/usr/bin/env python3
"""Focused G15-R6 Normal 3A import and boundary gate."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant_in, read_block
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
EASY = r'DATA\EASY\3AEASY.TXT'
NORMAL = r'DATA\NORMAL\3A.TXT'
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
COMPLETE_ADVANCES = pasm_constant_in('src/main.pasm', 'StageComplete_AdvanceCount')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
MUSIC = pasm_constant_in('src/main.pasm', 'Music_LastTrack')


def u8(m, a):
    return read_block(m, a, 32)[0]


def u16(m, a):
    b = read_block(m, a, 32)
    return b[0] | b[1] << 8


def source_gate(r):
    texts = {p: extract(PAK, p).decode('latin1') for p in (EASY, NORMAL)}
    levels = {p: parse_level(texts[p], p) for p in texts}
    events = {p: parse_spawns(texts[p]) for p in texts}
    e, n = levels[EASY], levels[NORMAL]
    es = [x for x in events[EASY] if isinstance(x, SpawnEvent)]
    ns = [x for x in events[NORMAL] if isinstance(x, SpawnEvent)]
    r.check('Normal 3A source path is authoritative', NORMAL in texts)
    r.check('Normal 3A reuses Easy 3A Boat2 presentation',
            n.background == e.background and n.frontpanel == e.frontpanel
            and n.panels == e.panels and n.order == e.order
            and len(n.panels) == 6 and len(n.order) == 30)
    r.check('Normal 3A uses supported right scroll and control music',
            'direction left' not in texts[NORMAL].lower()
            and 'direction down' not in texts[NORMAL].lower()
            and 'music\t\tdata/music/control.bor' in texts[NORMAL].lower())
    r.check('Normal 3A source queue is 45 records / 38 spawns / 3 waits / 4 groups',
            len(events[NORMAL]) == 45 and len(ns) == 38
            and sum(isinstance(x, WaitEvent) for x in events[NORMAL]) == 3
            and sum(isinstance(x, GroupEvent) for x in events[NORMAL]) == 4)
    r.check('Easy 3A comparison is 38 records / 31 spawns / 3 waits / 4 groups',
            len(events[EASY]) == 38 and len(es) == 31
            and sum(isinstance(x, WaitEvent) for x in events[EASY]) == 3
            and sum(isinstance(x, GroupEvent) for x in events[EASY]) == 4)
    r.check('Normal 3A encounter deltas are source-authored',
            any(x.character.lower() == 'angel' and x.at == 20 and x.health == 100 for x in ns)
            and any(x.character.lower() == 'angel' and x.at == 10 and x.health == 150 for x in ns)
            and any(x.character.lower() == 'ralf' and x.at == 500 and x.health == 100 for x in ns)
            and any(x.character.lower() == 'billy' and x.at == 2100 and x.health == 100 for x in ns))
    r.check('Normal 3A supported identities and items resolve',
            {x.character.lower() for x in ns} <= {'angel', 'ralf', 'yashiro', 'shermie', 'box', "k'", 'billy'}
            and any(x.character.lower() == 'box' and x.item == 'apple' for x in ns)
            and any(x.character.lower() == 'box' and x.item == 'gold' for x in ns))
    normal_set = next(s for s in parse_levels_from_pak(PAK) if s.name == 'Normal')
    entries = normal_set.entries
    r.check('Normal 3A has no authored next before 3B',
            entries[6][0] == 'file' and entries[7][0] == 'file')


def catalog_gate(r):
    def find(path):
        return next((i, s) for i, s in enumerate(build_rom.STAGE_CONFIGS)
                    if s['source_level'].upper() == path.upper())
    idx, stage = find(NORMAL)
    r.check('Normal 3A is derived physical catalog tail index 26',
            idx == len(build_rom.STAGE_CONFIGS) - 1 == 26)
    blob = open(os.path.join(ROOT, stage['spawn']), 'rb').read()
    r.check('packed queue count is 45 records', len(blob) // 10 == 45)
    r.check('internal Normal map is 22,23,24,25,26',
            build_rom.CAMPAIGN_STAGE_MAPS['BOR_NORMAL_1A_INTERNAL'] == [22, 23, 24, 25, 26])
    generated = open(os.path.join(ROOT, 'tools', 'audio', 'campaign_config.pasm'), encoding='ascii').read()
    r.check('generated boundary flags are 0,0,1,1,0',
            'Campaign_BorNormalDev_NextFlags:\n    .db 0, 0, 1, 1, 0' in generated)
    r.check('Normal remains unavailable', 'BorSet_ContentAvailable:\n    .db 1, 0, 0, 0' in generated)
    music_ids = open(os.path.join(ROOT, 'tools', 'audio', 'audio_music_ids.pasm'), encoding='ascii').read()
    r.check('stage music table covers appended physical records', 'Music_StageTrackCount = 27' in music_ids)
    return idx


def load(m, ordinal, expected, r):
    startup.cold_to_title(m, r)
    startup.select_case(m, r, 'KULA')
    m.run_frames(60)
    m.write_u8(CAMPAIGN, 3); m.write_u8(ORDINAL, ordinal)
    m.write_u8(PENDING, 1); m.write_u16(STATE, STAGECLEAR)
    for _ in range(900):
        m.run_frames(1)
        if u16(m, STATE) == PLAYING and u16(m, STAGE) == expected:
            return True
    return False


def runtime_gate(r, stage):
    with open_session(__file__) as m:
        loaded = load(m, 3, stage, r)
        r.check('Normal 2 next enters Normal 3A through typed Stage_Load', loaded)
        r.check('Normal 3A packed runtime queue is 45 records', loaded and u8(m, SPAWN_COUNT) == 45)
        print('R6 music diagnostic:', {'loaded': loaded, 'last_track': u8(m, MUSIC), 'stage': u16(m, STAGE)})
        r.check('Normal 3A stage music is selected normally', loaded and u8(m, MUSIC) == 4)
        before_times, before_adv = u8(m, TIMES), u16(m, COMPLETE_ADVANCES)
        m.write_u8(PENDING, 1); m.write_u16(STATE, STAGECLEAR)
        for _ in range(30):
            m.run_frames(1)
            if u16(m, STATE) == TITLE:
                break
        r.check('Normal 3A no-next clear bypasses showcomplete to DEV TITLE',
                u16(m, STATE) == TITLE and u8(m, COMPLETE_ACTIVE) == 0)
        r.check('3A DEV boundary does not credit set completion',
                u8(m, TIMES) == before_times and u16(m, COMPLETE_ADVANCES) == before_adv)


def main():
    r = Reporter('G15-BATCH-R6-NORMAL-3A', kind='GATE')
    source_gate(r); stage = catalog_gate(r); runtime_gate(r, stage); r.finish()


if __name__ == '__main__':
    main()
