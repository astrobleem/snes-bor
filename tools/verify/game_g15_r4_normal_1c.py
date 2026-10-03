#!/usr/bin/env python3
"""Focused G15-R4 Normal 1C import and authored-next gate."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, exact_input_edge, open_session, pasm_constant_in, read_block
import game_bor_startup_select as startup

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
sys.path[:0] = [os.path.join(ROOT, 'tools', 'bor_converter'),
                os.path.join(ROOT, 'tools', 'bg_converter')]
import build_rom  # noqa: E402
from pak_extract import extract  # noqa: E402
from level_parse import parse_level  # noqa: E402
from spawn_parse import parse_spawns, SpawnEvent, GroupEvent  # noqa: E402

PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
EASY = r'DATA\EASY\1CEASY.TXT'
NORMAL_A = r'DATA\NORMAL\1A.TXT'
NORMAL_B = r'DATA\NORMAL\1B.TXT'
NORMAL_C = r'DATA\NORMAL\1C.TXT'
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
P1_TARGET = pasm_constant_in('src/main.pasm', 'StageComplete_P1Target')
P1_LIVES = pasm_constant_in('src/core/game_state.pasm', 'P1_Lives16')


def u8(m, address):
    return read_block(m, address, 32)[0]


def u16(m, address):
    b = read_block(m, address, 32)
    return b[0] | b[1] << 8


def source_gate(r):
    texts = {p: extract(PAK, p).decode('latin1') for p in (EASY, NORMAL_A, NORMAL_B, NORMAL_C)}
    levels = {p: parse_level(texts[p], p) for p in texts}
    events = {p: parse_spawns(texts[p]) for p in texts}
    easy, normal = levels[EASY], levels[NORMAL_C]
    es = [x for x in events[EASY] if isinstance(x, SpawnEvent)]
    ns = [x for x in events[NORMAL_C] if isinstance(x, SpawnEvent)]
    r.check('Normal 1C source path is authoritative', NORMAL_C in texts)
    r.check('Normal 1C reuses Easy 1C presentation topology',
            normal.background == easy.background and normal.frontpanel == easy.frontpanel
            and normal.panels == easy.panels and normal.order == easy.order)
    r.check('Normal 1C is Alley right-scrolling geometry',
            len(normal.panels) == 5 and normal.order == 'abcde'
            and 'direction left' not in texts[NORMAL_C].lower()
            and 'direction down' not in texts[NORMAL_C].lower())
    r.check('Normal 1C authored music is 1boss and blocked is present',
            any(line.strip().lower().split()[:2] == ['music', 'data/music/1boss.bor']
                for line in texts[NORMAL_C].splitlines())
            and '\nblocked\t1' in texts[NORMAL_C].lower())
    r.check('Normal 1C queue is 22 records / 21 spawns / one group',
            len(events[NORMAL_C]) == 22 and len(ns) == 21
            and sum(isinstance(x, GroupEvent) for x in events[NORMAL_C]) == 1)
    r.check('Easy 1C comparison is 20 records / 19 spawns / one group',
            len(events[EASY]) == 20 and len(es) == 19
            and sum(isinstance(x, GroupEvent) for x in events[EASY]) == 1)
    r.check('Normal 1C preserves supported directives and identities',
            not any(k in texts[NORMAL_C].lower() for k in ('\nhole ', '\nendhole ', '\nmap '))
            and {x.character.lower() for x in ns} <=
            {'shermie', 'trash', 'yamazaki', 'yashiro', 'ralf', 'angel'})
    r.check('Normal 1C encounter delta is source-specific',
            sum(x.character.lower() == 'shermie' and x.at == 30 for x in ns) == 1
            and sum(x.character.lower() == 'shermie' and x.at == 30 for x in es) == 0
            and any(x.character.lower() == 'shermie' and x.at == 20 and x.map == 0 for x in ns)
            and any(x.character.lower() == 'shermie' and x.at == 20 and x.map == 1 for x in es)
            and sum(x.character.lower() == 'yashiro' and x.at == 160 and x.health == 80 for x in ns) == 1
            and sum(x.character.lower() == 'yashiro' and x.at == 160 for x in es) == 0)
    # The real source boundary is checked mechanically, not copied into the
    # internal campaign declaration.
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'bor_converter'))
    from bor_levels import parse_levels_from_pak
    normal_set = next(s for s in parse_levels_from_pak(PAK) if s.name == 'Normal')
    files = [value.replace('/', '\\').upper() for directive, value in normal_set.entries if directive == 'file']
    boundaries = [directive for directive, value in normal_set.entries]
    r.check('Normal source has no next after 1A/1B and real next after 1C',
            files[:3] == [NORMAL_A, NORMAL_B, NORMAL_C]
            and boundaries[:4] == ['file', 'file', 'file', 'next'])
    return texts, events


def catalog_gate(r):
    def find(path):
        return next((i, s) for i, s in enumerate(build_rom.STAGE_CONFIGS)
                    if s['source_level'].upper() == path.upper())
    easy, normal_a = find(EASY), find(NORMAL_A)
    normal_b, normal_c = find(NORMAL_B), find(NORMAL_C)
    blob = open(os.path.join(ROOT, normal_c[1]['spawn']), 'rb').read()
    r.check('Normal 1C is derived physical catalog tail index 24',
            normal_c[0] == len(build_rom.STAGE_CONFIGS) - 1 == 24)
    r.check('Normal 1A/1B remain physical 22/23 and Easy records unchanged',
            normal_a[0] == 22 and normal_b[0] == 23 and easy[0] == 2
            and len({easy[0], normal_a[0], normal_b[0], normal_c[0]}) == 4)
    r.check('Normal 1C has independent 22-record packed queue', len(blob) == 220)
    r.check('internal Normal campaign is exactly 1A, 1B, 1C',
            build_rom.CAMPAIGN_STAGE_MAPS['BOR_NORMAL_1A_INTERNAL'] == [22, 23, 24]
            and len(build_rom.CAMPAIGN_ENTRY_MAPS['BOR_NORMAL_1A_INTERNAL']) == 3)
    generated = open(os.path.join(ROOT, 'tools', 'audio', 'campaign_config.pasm'), encoding='ascii').read()
    r.check('generated source boundary flags are 0, 0, 1',
            'Campaign_BorNormalDev_NextFlags:\n    .db 0, 0, 1' in generated)
    r.check('Normal remains unavailable and thresholds unchanged',
            'BorSet_ContentAvailable:\n    .db 1, 0, 0, 0' in generated
            and 'BorSet_IfComplete:\n    .db 0, 0, 0, 1' in generated)
    return normal_a[0], normal_b[0], normal_c[0]


def load_fixture(m, ordinal, expected_stage, r):
    startup.cold_to_title(m, r)
    startup.select_case(m, r, 'KULA')
    m.run_frames(60)
    m.write_u8(CAMPAIGN, 3)
    m.write_u8(ORDINAL, ordinal)
    m.write_u8(PENDING, 1)
    m.write_u16(STATE, STAGECLEAR)
    for _ in range(600):
        m.run_frames(1)
        if u16(m, STATE) == PLAYING and u16(m, STAGE) == expected_stage:
            return True
    return False


def runtime_gate(r, stage_b, stage_c):
    with open_session(__file__) as m:
        loaded = load_fixture(m, 0, stage_b, r)
        r.check('Normal 1B loads from ordinal 0 clear without completion', loaded)
        r.check('1B -> 1C has no showcomplete', loaded and u8(m, COMPLETE_ACTIVE) == 0)

    with open_session(__file__) as m:
        loaded = load_fixture(m, 1, stage_c, r)
        r.check('Normal 1C loads from ordinal 1 clear directly', loaded)
        before = u8(m, TIMES)
        m.write_u16(P1_LIVES, 3)
        m.write_u8(ORDINAL, 2)
        m.write_u8(PENDING, 1)
        m.write_u16(STATE, STAGECLEAR)
        active = False
        for _ in range(30):
            m.run_frames(1)
            if u8(m, COMPLETE_ACTIVE):
                active = True
                break
        r.check('1C authored next enters existing completion presentation', active)
        print('R4 completion diagnostic:', {'active': active, 'target': u16(m, P1_TARGET),
                                             'state': u16(m, STATE), 'ordinal': u8(m, ORDINAL),
                                             'times': u8(m, TIMES)})
        r.check('completion target uses accepted bonus formula', active and u16(m, P1_TARGET) == 13000)
        r.check('Normal partial completion does not credit BOR set', u8(m, TIMES) == before)
        exact_input_edge(m, m.BTN_A, 2)
        for _ in range(300):
            m.run_frames(1)
            if u16(m, STATE) == TITLE:
                break
        print('R4 completion skip diagnostic:', {'state': u16(m, STATE), 'active': u8(m, COMPLETE_ACTIVE),
                                                   'ordinal': u8(m, ORDINAL)})
        r.check('completion skip reaches temporary DEV TITLE boundary', u16(m, STATE) == TITLE)
        r.check('completion skip leaves set counter unchanged', u8(m, TIMES) == before)


def main():
    r = Reporter('G15-BATCH-R4-NORMAL-1C', kind='GATE')
    source_gate(r)
    _, stage_b, stage_c = catalog_gate(r)
    runtime_gate(r, stage_b, stage_c)
    r.finish()


if __name__ == '__main__':
    main()
