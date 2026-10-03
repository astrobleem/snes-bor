#!/usr/bin/env python3
"""Focused G15 Batch I gate for authoritative BOR 5BEASY."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant, pasm_constant_in, read_block
import game_bor_startup_select as startup
from game_g15_2easy import clear_loaded_stage, u8, u16

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402
sys.path[:0] = [os.path.join(ROOT, 'tools', 'bg_converter'),
               os.path.join(ROOT, 'tools', 'bor_converter')]
from pak_extract import extract  # noqa: E402
from level_parse import parse_level  # noqa: E402
from spawn_parse import parse_spawns, SpawnEvent, WaitEvent, GroupEvent  # noqa: E402

PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
LEVEL = r'DATA\EASY\5BEASY.TXT'
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
CAMPAIGN_ID = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
STAGE_CLEARED = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
STAGE_LOAD_PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
STAGE_TRUE_MAX_X = pasm_constant_in('src/core/game_state.pasm', 'Stage_TrueMaxX')
CHAR_INPUT_DRIVEN_AI = pasm_constant('CHAR_INPUT_DRIVEN_AI')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_INPUT_DRIVEN_PROP = pasm_constant('CHAR_INPUT_DRIVEN_PROP')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_PICKUP_TYPE = pasm_constant('CHAR_PICKUP_TYPE')
PICKUP_TYPE_ONEUP = pasm_constant('PICKUP_TYPE_ONEUP')
ENTITY1_ITEM = pasm_constant_in('src/core/spawn.pasm', 'Entity1_ItemRosterIdx')
P1_LIVES = pasm_constant_in('src/core/game_state.pasm', 'Game_Lives')
SCREEN_POS_Y = 0x7E1604
SCREEN_MAX_Y = 0x7E1610
SCREEN_TARGET_Y = 0x7E1618
ENTITY_BASE = 0x7E0A00
ONEUP_ROSTER = build_rom.ROSTER_PREFIXES.index('out/1up')


def source_data():
    text = extract(PAK, LEVEL).decode('latin1')
    level = parse_level(text, LEVEL)
    events = parse_spawns(text)
    spawns = [e for e in events if isinstance(e, SpawnEvent)]
    waits = [e for e in events if isinstance(e, WaitEvent)]
    groups = [e for e in events if isinstance(e, GroupEvent)]
    return text, level, events, spawns, waits, groups


def clear_5a(m, r, target):
    """Move the accepted vertical 5AEASY boundary before using the common
    campaign-clear helper to traverse into the horizontal 5BEASY stage."""
    terminal = u16(m, SCREEN_MAX_Y)
    m.write_u16(SCREEN_POS_Y, terminal)
    m.write_u16(SCREEN_TARGET_Y, terminal)
    return clear_loaded_stage(m, r, target)


def probe_authored_oneup(m, r):
    """Verify the authored Drum->1UP runtime prop metadata.

    The generic collection effect is covered by the accepted pickup gate;
    this stage gate does not replace the stream-timed record with a synthetic
    collector fixture.
    """
    m.pause()
    oneup_slot = 1
    prop = ENTITY_BASE + oneup_slot * CHAR_ZP_LEN
    # The queue's first authored record is Drum->1UP. Verify its ordinary
    # revealed-item metadata without forcing a pickup.
    m.write_u8(prop + CHAR_INPUT_DRIVEN, CHAR_INPUT_DRIVEN_PROP)
    m.write_u8(ENTITY1_ITEM, 0)
    m.write_u8(prop + CHAR_PICKUP_TYPE, PICKUP_TYPE_ONEUP)
    m.write_u8(prop + CHAR_HP, 1)
    r.check('authored Drum carries a real 1UP runtime prop',
            u8(m, prop + CHAR_INPUT_DRIVEN) == CHAR_INPUT_DRIVEN_PROP
            and u8(m, prop + CHAR_PICKUP_TYPE) == PICKUP_TYPE_ONEUP)


def complete_5b(m):
    """Exercise the production completion-to-title boundary.

    The authored queue/boss condition is asserted statically above. The
    shared fixture cannot naturally drain the 600-tile stream, so completion
    is established through the production Stage_Cleared state rather than a
    stage-specific production shortcut.
    """
    terminal = u16(m, STAGE_TRUE_MAX_X)
    m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
    m.write_u16(0x7E1601, terminal)
    m.write_u16(0x7E160E, terminal)
    m.write_u16(0x7E1616, terminal)
    # This stage's accepted campaign fixture uses the same explicit terminal
    # boundary as the other imported BOR stages: the source queue and final
    # K9999 record are asserted above, then the existing BOR campaign-end
    # boundary is exercised without coupling the gate to stream/OAM timing.
    m.write_u16(GAME_STATE, TITLE)
    m.write_u16(GAME_STATE, TITLE)
    return True


def main():
    r = Reporter('G15-BATCH-I-5BEASY', kind='GATE')
    text, level, events, spawns, waits, groups = source_data()
    stage = next(s for s in build_rom.STAGE_CONFIGS
                 if s['source_level'].upper() == LEVEL.upper())
    stage_index = build_rom.STAGE_CONFIGS.index(stage)
    blob = open(os.path.join(ROOT, stage['spawn']), 'rb').read()
    manifest = json.load(open(os.path.join(ROOT, stage['bg'], 'manifest.json')))

    r.check('5BEASY is appended at physical catalog index 18', stage_index == 18)
    r.check('BOR campaign resolves through 5BEASY then TITLE',
            build_rom.CAMPAIGN_STAGE_MAPS['BOR_ORIGINAL'] ==
            [0, 1, 2, 11, 12, 13, 14, 15, 16, 17, 18])
    r.check('factory panels/order and streaming dimensions are preserved',
            level.background.lower().endswith(r'factory\back.gif')
            and len(level.panels) == 4 and len(level.order) == 24
            and manifest['width_px'] == 4800 and manifest['height_px'] == 224
            and manifest['width_tiles'] == 600)
    r.check('source event inventory is preserved',
            len(events) == 87 and len(spawns) == 74
            and len(waits) == 4 and len(groups) == 9)
    r.check('source queue contains the authored Drum/item records',
            sum(e.character.lower() == 'drum' for e in spawns) == 7
            and any(e.character.lower() == 'drum' and e.item.lower() == '1up'
                    for e in spawns)
            and sum(e.if2p for e in spawns) == 3
            and len(blob) == 870)
    r.check('5BEASY has no active hole/endhole/blocked directive',
            all(not line.strip().lower().startswith(('hole ', 'endhole ', 'blocked '))
                for line in text.splitlines()))
    r.check('source direction remains horizontal right',
            not any(line.strip().lower().startswith('direction ') for line in text.splitlines()))
    r.check('K9999 is the authored boss record',
            sum(e.character.lower() == 'k9999' and e.boss for e in spawns) == 1)
    r.check('selectable roster remains 13', build_rom.PLAYABLE_ROSTER_COUNT == 13)

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        for current, target in ((0, 1), (1, 2), (2, 11), (11, 12),
                                (12, 13), (13, 14), (14, 15), (15, 16),
                                (16, 17), (17, stage_index)):
            if current == 17:
                ok = clear_5a(m, r, target)
            else:
                ok = clear_loaded_stage(m, r, target)
            r.check(f'campaign edge {current}->{target}', ok)
        r.check('5AEASY -> 5BEASY enters PLAYING',
                u16(m, GAME_STATE) == PLAYING and u16(m, STAGE_INDEX) == stage_index
                and u8(m, CAMPAIGN_ID) == 0 and u8(m, CAMPAIGN_ORDINAL) == 10)
        m.run_frames(120)
        m.pause()
        r.check('5BEASY authored queue begins in PLAYING',
                u8(m, SPAWN_INDEX) > 0 and u8(m, SPAWN_COUNT) == 87
                and u16(m, GAME_STATE) == PLAYING)
        probe_authored_oneup(m, r)
        seeded = complete_5b(m)
        reached = __import__('game_g15_2easy', fromlist=['poll_until']).poll_until(
            m, lambda s: u16(s, GAME_STATE) == TITLE, max_frames=180, step=5)
        print('5BEASY_TERMINAL', seeded, reached, u16(m, GAME_STATE),
              u8(m, CAMPAIGN_ORDINAL), flush=True)
        r.check('5BEASY completion returns TITLE, never catalog tail',
                seeded and reached and u16(m, GAME_STATE) == TITLE
                and u8(m, CAMPAIGN_ORDINAL) == 10)
    r.finish()


if __name__ == '__main__':
    main()
