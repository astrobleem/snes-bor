#!/usr/bin/env python3
"""Source-normal BOR cold-start and independent player-selection gate."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'audio'))
from _harness import (Reporter, exact_input_edge, open_session, pasm_constant,
                      pasm_constant_in, read_block, run_frames_exact,
                      poll_until)  # noqa: E402
from shipped_content import STAGE_CONFIGS, normal_player_entries  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
INTRO = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_INTRO')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
CHARSELECT = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_CHARSELECT')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE_STEP = pasm_constant_in('src/core/game_state.pasm', 'Title_Step')
CHAR_STEP = pasm_constant_in('src/core/game_state.pasm', 'CharSelect_Step')
DIFFICULTY = pasm_constant('BorDifficulty_Chosen')
ORDINAL = pasm_constant('BorSelect_Ordinal')
P2_ORDINAL = pasm_constant('BorSelect_P2Ordinal')
P1_READY = pasm_constant('BorSelect_P1Ready')
P2_READY = pasm_constant('BorSelect_P2Ready')
CAMPAIGN_ID = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_ROSTER_INDEX = pasm_constant('CHAR_ROSTER_INDEX')
P1 = 0x7E0A00
P2 = P1 + CHAR_ZP_LEN
MODE = pasm_constant('G13_TwoPlayerEnabled')

BOR = 0  # campaign_config.pasm: BOR_ORIGINAL


def entry_name(entry):
    return entry['source_character'].rsplit('\\', 1)[-1]


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def wait_state(m, state, limit=240):
    return poll_until(m, lambda s: u16(s, STATE) == state, limit)


def title_to_charselect(m, two_player=False):
    if two_player:
        exact_input_edge(m, m.BTN_START, 1, port=1)
        run_frames_exact(m, 2)
    exact_input_edge(m, m.BTN_START, 1, port=0)
    if not wait_state(m, CHARSELECT):
        raise AssertionError('title did not reach character select')
    if not poll_until(m, lambda s: u8(s, DIFFICULTY) == 1, 120):
        raise AssertionError('difficulty selector did not become visible')
    exact_input_edge(m, m.BTN_START, 1, port=0)
    if not poll_until(m, lambda s: u8(s, DIFFICULTY) == 3, 120):
        raise AssertionError('Easy confirmation did not complete')
    if not poll_until(m, lambda s: u8(s, CHAR_STEP) == 3, 180):
        raise AssertionError('character selector did not become ready')


def cold_to_title(m, r):
    m.reset_emulator()
    # Boot performs the existing forced-blank hardware/content setup before
    # the first paced main-loop iteration; wait for that real boot boundary.
    # Keep each MCP advance bounded so a transient tool timeout cannot leave
    # the emulator two frames short and masquerade as a frozen boot.
    for _ in range(18):
        run_frames_exact(m, 10)
    r.check('cold reset enters INTRO, not TITLE/PLAYING', u16(m, STATE) == INTRO)
    r.check('cold reset is not PLAYING', u16(m, STATE) != PLAYING)
    run_frames_exact(m, 1)
    r.check('INTRO remains reachable through second scene card', u16(m, STATE) == INTRO)
    exact_input_edge(m, m.BTN_START, 1, port=0)
    if not wait_state(m, TITLE):
        raise AssertionError('INTRO did not transition to TITLE')
    r.check('INTRO -> TITLE', u16(m, STATE) == TITLE)
    if not poll_until(m, lambda s: u8(s, TITLE_STEP) == 2, 120):
        raise AssertionError('TITLE did not reach its input wait')


def select_case(m, r, p1_name, p2_name=None):
    entries = normal_player_entries('bor-original')
    by_name = {entry_name(entry).upper(): (ordinal, index)
               for ordinal, (index, entry) in enumerate(entries)}
    p1_key = p1_name.upper()
    p2_key = p2_name.upper() if p2_name else None
    title_to_charselect(m, p2_name is not None)
    for _ in range(by_name[p1_key][0]):
        exact_input_edge(m, m.BTN_RIGHT, 1, port=0)
        run_frames_exact(m, 1)
    if p2_key is not None:
        for _ in range(by_name[p2_key][0]):
            exact_input_edge(m, m.BTN_RIGHT, 1, port=1)
            run_frames_exact(m, 1)
        exact_input_edge(m, m.BTN_START, 1, port=1)
    exact_input_edge(m, m.BTN_START, 1, port=0)
    if not wait_state(m, PLAYING, 300):
        raise AssertionError(f'{p1_name}/{p2_name or "1P"} did not reach PLAYING')
    p1_runtime = by_name[p1_key][1]
    actual_p1 = u8(m, P1 + CHAR_ROSTER_INDEX)
    r.check(f'{p1_name} runtime identity ({actual_p1}, expected {p1_runtime})', actual_p1 == p1_runtime)
    r.check(f'{p1_name} campaign start', u8(m, CAMPAIGN_ID) == BOR and
            u8(m, CAMPAIGN_ORDINAL) == 0 and u8(m, STAGE_INDEX) == 0)
    if p2_key is not None:
        p2_runtime = by_name[p2_key][1]
        actual_p2 = u8(m, P2 + CHAR_ROSTER_INDEX)
        r.check(f'{p2_name} runtime identity ({actual_p2}, expected {p2_runtime})', actual_p2 == p2_runtime)
        r.check('2P slot ownership', u8(m, MODE) == 1)
        r.check('P1/P2 readiness completed independently', u8(m, P1_READY) == 1 and u8(m, P2_READY) == 1)


def main():
    r = Reporter('BOR-STARTUP', kind='GATE')
    entries = normal_player_entries('bor-original')
    print('BOR source-normal map:', [(entry_name(entry), index)
                                    for index, entry in entries])
    with open_session(__file__) as m:
        cold_to_title(m, r)
    for _, entry in entries:
        name = entry_name(entry)
        with open_session(__file__) as m:
            cold_to_title(m, r)
            select_case(m, r, name)
    for p1, p2 in [('KULA', 'MIGHTY'), ('MIGHTY', 'KULA'),
                   ('MAXIMA', 'MARY'), ('MARY', 'MAXIMA'), ('KULA', 'KULA')]:
        with open_session(__file__) as m:
            cold_to_title(m, r)
            select_case(m, r, p1, p2)
    r.finish()


if __name__ == '__main__':
    main()
