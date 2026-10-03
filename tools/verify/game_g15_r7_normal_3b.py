#!/usr/bin/env python3
"""Focused G15-R7 Normal 3B import and typed-boundary gate."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant_in, read_block
import game_bor_startup_select as startup
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
sys.path[:0] = [os.path.join(ROOT, 'tools', 'bor_converter'), os.path.join(ROOT, 'tools', 'bg_converter')]
import build_rom
from pak_extract import extract
from level_parse import parse_level
from spawn_parse import parse_spawns, SpawnEvent, WaitEvent, GroupEvent
from bor_levels import parse_levels_from_pak

PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
EASY, NORMAL = r'DATA\EASY\3BEASY.TXT', r'DATA\NORMAL\3B.TXT'
STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
CAMPAIGN = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
STAGE = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
TIMES = pasm_constant_in('src/core/options.pasm', 'Bor_TimesCompleted')
COMPLETE = pasm_constant_in('src/main.pasm', 'StageComplete_Active')
ADVANCES = pasm_constant_in('src/main.pasm', 'StageComplete_AdvanceCount')
MUSIC = pasm_constant_in('src/main.pasm', 'Music_LastTrack')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')

def u8(m, a): return read_block(m, a, 32)[0]
def u16(m, a):
    b = read_block(m, a, 32); return b[0] | b[1] << 8

def source_gate(r):
    text = {p: extract(PAK, p).decode('latin1') for p in (EASY, NORMAL)}
    level = {p: parse_level(text[p], p) for p in text}
    events = {p: parse_spawns(text[p]) for p in text}
    e, n = level[EASY], level[NORMAL]
    es = [x for x in events[EASY] if isinstance(x, SpawnEvent)]
    ns = [x for x in events[NORMAL] if isinstance(x, SpawnEvent)]
    r.check('authoritative Normal 3B source exists', NORMAL in text)
    r.check('Boat presentation is source-identical',
            (n.background, n.frontpanel, n.panels, n.order) ==
            (e.background, e.frontpanel, e.panels, e.order)
            and len(n.order) == 24)
    r.check('Normal 3B is supported normal/right scrolling with control music',
            'direction left' not in text[NORMAL].lower() and
            'direction down' not in text[NORMAL].lower() and
            'music\t\tdata/music/control.bor' in text[NORMAL].lower())
    r.check('Normal queue is 40 records / 34 spawns / 2 waits / 4 groups',
            len(events[NORMAL]) == 40 and len(ns) == 34 and
            sum(isinstance(x, WaitEvent) for x in events[NORMAL]) == 2 and
            sum(isinstance(x, GroupEvent) for x in events[NORMAL]) == 4)
    r.check('Easy comparison is 38 records / 31 spawns / 2 waits / 5 groups',
            len(events[EASY]) == 38 and len(es) == 31 and
            sum(isinstance(x, WaitEvent) for x in events[EASY]) == 2 and
            sum(isinstance(x, GroupEvent) for x in events[EASY]) == 5)
    r.check('Normal encounter deltas are preserved',
            sum(x.character.lower() == 'joe' for x in ns) == 3 and
            any(x.character.lower() == 'shermie' and x.at == 700 and x.coords[1] == 170 for x in ns) and
            sum(x.character.lower() == "k'" for x in ns) == 8 and
            any(x.character.lower() == 'joe' and x.health == 150 for x in ns))
    r.check('items and all identities are supported',
            any(x.item == 'meat' for x in ns) and any(x.item == 'apple' for x in ns) and
            {x.character.lower() for x in ns} <= {'angel','box','joe',"k'",'ralf','shermie','yashiro'})
    normal = next(s for s in parse_levels_from_pak(PAK) if s.name == 'Normal').entries
    r.check('3A and 3B have no authored next boundary',
            normal[6][0] == 'file' and normal[7][0] == 'file' and normal[8][0] == 'file')

def catalog_gate(r):
    found = [(i,s) for i,s in enumerate(build_rom.STAGE_CONFIGS) if s['source_level'].upper() == NORMAL]
    r.check('Normal 3B is the appended physical tail', len(found) == 1 and found[0][0] == len(build_rom.STAGE_CONFIGS)-1 == 27)
    idx, stage = found[0]
    blob = open(os.path.join(ROOT, stage['spawn']), 'rb').read()
    r.check('packed queue count is independently 40 records', len(blob) // 10 == 40)
    r.check('internal Normal map is 22..27', build_rom.CAMPAIGN_STAGE_MAPS['BOR_NORMAL_1A_INTERNAL'] == [22,23,24,25,26,27])
    generated = open(os.path.join(ROOT, 'tools/audio/campaign_config.pasm'), encoding='ascii').read()
    r.check('generated flags are 0,0,1,1,0,0', 'Campaign_BorNormalDev_NextFlags:\n    .db 0, 0, 1, 1, 0, 0' in generated)
    r.check('Normal remains unavailable', 'BorSet_ContentAvailable:\n    .db 1, 0, 0, 0' in generated)
    music = open(os.path.join(ROOT, 'tools/audio/audio_music_ids.pasm'), encoding='ascii').read()
    r.check('stage music table covers 28 physical stages', 'Music_StageTrackCount = 28' in music)
    return idx

def load(m, ordinal, expected):
    startup.cold_to_title(m, Reporter('startup', kind='SUB'))
    startup.select_case(m, Reporter('select', kind='SUB'), 'KULA')
    m.run_frames(60)
    m.write_u8(CAMPAIGN, 3); m.write_u8(ORDINAL, ordinal)
    m.write_u8(PENDING, 1); m.write_u16(STATE, STAGECLEAR)
    for _ in range(900):
        m.run_frames(1)
        if u16(m, STATE) == PLAYING and u16(m, STAGE) == expected: return True
    return False

def runtime_gate(r, stage):
    with open_session(__file__) as m:
        loaded = load(m, 4, stage)
        r.check('3A -> 3B is direct typed STAGE dispatch', loaded)
        r.check('3B packed queue is 40 records', loaded and u8(m, SPAWN_COUNT) == 40)
        r.check('3B normal music selected (track 4)', loaded and u8(m, MUSIC) == 4)
        before = (u8(m, TIMES), u16(m, ADVANCES))
        m.write_u8(PENDING, 1); m.write_u16(STATE, STAGECLEAR)
        for _ in range(60):
            m.run_frames(1)
            if u16(m, STATE) == TITLE: break
        r.check('3B DEV boundary reaches TITLE without showcomplete',
                u16(m, STATE) == TITLE and u8(m, COMPLETE) == 0)
        r.check('DEV boundary does not credit set completion or advance bonus',
                (u8(m, TIMES), u16(m, ADVANCES)) == before)

def main():
    r = Reporter('G15-BATCH-R7-NORMAL-3B', kind='GATE')
    source_gate(r); runtime_gate(r, catalog_gate(r)); r.finish()
if __name__ == '__main__': main()
