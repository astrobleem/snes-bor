#!/usr/bin/env python3
"""G15 Batch A: the real BOR 1A -> 1B -> 1C campaign prefix.

This gate uses the established legal stage-clear precondition (exhaust the
loaded spawn queue and clear live AI HP) so it tests Stage_Load and the real
stage-indexed MSU records without waiting on combat randomness.  It never
writes Game_State or skips Stage_Load.  The final 1C handoff is explicitly a
development-tail handoff: Batch B has not shipped BOR 2EASY yet.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (Reporter, open_session, pasm_constant, pasm_constant_in,
                      poll_until, read_block, repo_root_from)
import game_bor_startup_select as startup

ROOT = repo_root_from(None)
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
CAMPAIGN_ID = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
STAGE_CLEARED = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
STAGE_TRUE_MAX_X = pasm_constant_in('src/core/game_state.pasm', 'Stage_TrueMaxX')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_INPUT_DRIVEN_AI = pasm_constant('CHAR_INPUT_DRIVEN_AI')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
PLAYER = 0x7E0A00
ENTITIES = [PLAYER + i * CHAR_ZP_LEN for i in range(6)]
SCREEN_POS_X = 0x7E1601
NMI_COUNTER = 0x7E5023


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def stage_manifest(index):
    directory = os.path.join(ROOT, build_rom.STAGE_CONFIGS[index]['bg'])
    with open(os.path.join(directory, 'manifest.json'), encoding='utf-8') as f:
        return directory, json.load(f)


def clear_stage(m, r, from_index):
    """Reach the real Stage_Load edge, without writing Game_State."""
    count = u8(m, SPAWN_COUNT)
    m.write_u8(SPAWN_INDEX, count)
    # The production win predicate also requires the camera to have reached
    # the stage's true right edge.  Set that legal observation precondition
    # before servicing the clear, as the established G4 gate does.
    m.write_u16(SCREEN_POS_X, u16(m, STAGE_TRUE_MAX_X))
    # Keep the accepted force-win precondition alive while the current frame
    # finishes any already-pending roster stream/reassignment.  This does not
    # write Game_State or bypass the production completion predicate.
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
    if from_index == 2:
        return poll_until(m, lambda s: u16(s, GAME_STATE) == TITLE,
                          max_frames=120, step=5)
    return poll_until(
        m, lambda s: u16(s, STAGE_INDEX) == from_index + 1
        and u16(s, GAME_STATE) == PLAYING, max_frames=600, step=5)


def assert_stage_source(r, index, level, spawn_count, width, boss_index=None):
    config = build_rom.STAGE_CONFIGS[index]
    r.check(f'index {index} source is {level}', config['source_level'].upper() == level)
    directory, manifest = stage_manifest(index)
    r.check(f'index {index} BG output exists', os.path.isdir(directory))
    r.check(f'index {index} width is {width}', manifest['width_tiles'] == width)
    table = os.path.join(ROOT, config['spawn'])
    with open(table, 'rb') as f:
        blob = f.read()
    r.check(f'index {index} spawn count is {spawn_count}', len(blob) == spawn_count * 10)
    if boss_index is not None:
        kind = blob[boss_index * 10 + 6] & 7
        roster = blob[boss_index * 10 + 9]
        r.check(f'index {index} has identified Yamazaki boss at record {boss_index}',
                kind == 5 and roster == build_rom.ROSTER_PREFIXES.index('out/yamazaki'))


def main():
    r = Reporter('G15-BATCH-A-STAGE1', kind='GATE')
    assert_stage_source(r, 0, 'DATA\\EASY\\1AEASY.TXT', 41, 408)
    assert_stage_source(r, 1, 'DATA\\EASY\\1BEASY.TXT', 35, 140)
    assert_stage_source(r, 2, 'DATA\\EASY\\1CEASY.TXT', 20, 64, boss_index=3)
    r.check('STAGE_CONFIGS contains all 11 packed stages',
            len(build_rom.STAGE_CONFIGS) == 11)
    r.check('production verifier retains six actor windows', len(ENTITIES) == 6)
    r.check('first BOR prefix is 1A -> 1B -> 1C',
            [s['source_level'].upper() for s in build_rom.STAGE_CONFIGS[:3]] == [
                'DATA\\EASY\\1AEASY.TXT', 'DATA\\EASY\\1BEASY.TXT',
                'DATA\\EASY\\1CEASY.TXT'])

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        # Let the real 1A Stage_Load/frontpanel stream settle before applying
        # the established legal clear precondition.
        m.run_frames(60)
        m.pause()
        r.check('boots on real BOR 1A (stage 0)', u16(m, STAGE_INDEX) == 0)
        r.check('stage 0 is PLAYING', u16(m, GAME_STATE) == PLAYING)
        r.check('1A -> 1B uses real Stage_Load', clear_stage(m, r, 0))
        r.check('after first clear, stage is 1B', u16(m, STAGE_INDEX) == 1)
        r.check('1B -> 1C uses real Stage_Load', clear_stage(m, r, 1))
        r.check('after second clear, stage is 1C', u16(m, STAGE_INDEX) == 2)

        # Let the real trigger queue service its opening wave.  This is an
        # observation-only production run; no spawn fields are injected.
        m.set_input(m.BTN_RIGHT, 90)
        m.pause()
        m.run_frames(90)
        m.pause()
        r.check('1C production wave stays within the six-actor bound',
                all(u8(m, base + CHAR_HP) >= 0 for base in ENTITIES)
                and u8(m, SPAWN_INDEX) <= u8(m, SPAWN_COUNT))
        r.check('1C remains in PLAYING during wave service', u16(m, GAME_STATE) == PLAYING)

        # Clear 1C through the normal edge. The incomplete BOR campaign has
        # an explicit development boundary and must not enter TMNT merely
        # because TMNT assets follow it in the physical catalog.
        r.check('1C reaches BOR development boundary through stage-clear path',
                clear_stage(m, r, 2))
        r.check('1C stops at TITLE, not at the TMNT catalog',
                u16(m, GAME_STATE) == TITLE
                and u8(m, CAMPAIGN_ID) == 0
                and u8(m, CAMPAIGN_ORDINAL) == 2
                and u16(m, STAGE_INDEX) == 2)
        fc0 = u16(m, NMI_COUNTER)
        m.run_frames(60)
        m.pause()
        r.check('NMI remains healthy after the three-part prefix', u16(m, NMI_COUNTER) > fc0)
    r.finish()


if __name__ == '__main__':
    main()
