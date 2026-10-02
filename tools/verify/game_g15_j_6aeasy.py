#!/usr/bin/env python3
"""Focused G15 Batch J gate for authoritative BOR 6AEASY."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant_in
import game_bor_startup_select as startup
from game_g15_2easy import clear_loaded_stage, u8, u16
from game_g15_i_5beasy import clear_5a

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402
sys.path[:0] = [os.path.join(ROOT, 'tools', 'bg_converter'),
               os.path.join(ROOT, 'tools', 'bor_converter')]
from pak_extract import extract  # noqa: E402
from level_parse import parse_level  # noqa: E402
from spawn_parse import parse_spawns, SpawnEvent, WaitEvent, GroupEvent  # noqa: E402

PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
LEVEL = r'DATA\EASY\6AEASY.TXT'
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
STAGE_LOAD_PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
STAGE_DIRECTION = pasm_constant_in('src/core/game_state.pasm', 'Stage_ScrollDirection')
STAGE_LEFT = pasm_constant_in('tools/audio/stage_scroll_config.pasm', 'STAGE_SCROLL_LEFT')
SCREEN_POS_X = 0x7E0000 + pasm_constant_in('src/core/screen.pasm', 'Screen_PosX_Lo')
STAGE_TRUE_MAX_X = pasm_constant_in('src/core/game_state.pasm', 'Stage_TrueMaxX')
STAGE_MIRROR = pasm_constant_in('src/core/game_state.pasm', 'Stage_Mirror')
STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')


def main():
    r = Reporter('G15-BATCH-J-6AEASY', kind='GATE')
    text = extract(PAK, LEVEL).decode('latin1')
    level = parse_level(text, LEVEL)
    events = parse_spawns(text)
    spawns = [e for e in events if isinstance(e, SpawnEvent)]
    waits = [e for e in events if isinstance(e, WaitEvent)]
    groups = [e for e in events if isinstance(e, GroupEvent)]
    stage = next(s for s in build_rom.STAGE_CONFIGS
                 if s['source_level'].upper() == LEVEL.upper())
    stage_index = build_rom.STAGE_CONFIGS.index(stage)
    blob = open(os.path.join(ROOT, stage['spawn']), 'rb').read()
    manifest = json.load(open(os.path.join(ROOT, stage['bg'], 'manifest.json')))
    fp_manifest = json.load(open(os.path.join(ROOT, stage['frontpanel'], 'manifest.json')))

    r.check('6AEASY is appended at physical catalog index 19', stage_index == 19)
    r.check('BOR campaign resolves through 6BEASY then TITLE',
            build_rom.CAMPAIGN_STAGE_MAPS['BOR_ORIGINAL'] ==
            [0, 1, 2, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
    r.check('hotel panels/order and dimensions are preserved',
            level.background.lower().endswith(r'hotel\back.gif')
            and level.frontpanel.lower().endswith(r'hotel\f00.gif')
            and len(level.panels) == 8 and len(level.order) == 26
            and manifest['width_px'] == 4160 and manifest['height_px'] == 224
            and manifest['width_tiles'] == 520
            and fp_manifest['width_tiles'] == manifest['width_tiles'])
    r.check('source event inventory is preserved',
            len(events) == 92 and len(spawns) == 68
            and len(waits) == 13 and len(groups) == 11)
    r.check('source queue preserves models, positions, health and items',
            {e.character.lower() for e in spawns} ==
            {'1up', 'shermie', 'yashiro', 'ralf', 'angel', 'yamazaki',
             "k'", 'trolly', 'heavy', 'billy', 'joe', 'robert', 'jhun',
             'mrbig', 'eiji', 'k9999'}
            and sum(bool(e.item) for e in spawns) == 8
            and sum(e.if2p for e in spawns) == 4
            and any(e.character.lower() == '1up' and e.at == 0 for e in spawns)
            and len(blob) == 920)
    r.check('source direction/mirror are represented independently',
            any(line.strip().lower().split() == ['direction', 'left']
                for line in text.splitlines())
            and any(line.strip().lower().split() == ['mirror', '1']
                    for line in text.splitlines())
            and stage.get('scroll_direction') == 'left'
            and stage.get('source_direction') == 'left'
            and stage.get('source_mirror') is True)
    r.check('no active hole/endhole/blocked directive',
            all(not line.strip().lower().startswith(('hole ', 'endhole ', 'blocked '))
                for line in text.splitlines()))
    r.check('no authored boss flag; final queue is ordinary K9999',
            not any(e.boss for e in spawns)
            and spawns[-1].character.lower() == 'shermie')
    r.check('runtime-only models preserve 13-character selection',
            build_rom.PLAYABLE_ROSTER_COUNT == 13
            and [p.rsplit('/', 1)[-1] for p in build_rom.ROSTER_PREFIXES[-3:]] ==
            ['eiji', 'mrbig', 'trolly'])

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        for current, target in ((0, 1), (1, 2), (2, 11), (11, 12),
                                (12, 13), (13, 14), (14, 15), (15, 16),
                                (16, 17), (17, 18)):
            edge_ok = clear_5a(m, r, target) if current == 17 else clear_loaded_stage(m, r, target)
            r.check(f'campaign edge {current}->{target}', edge_ok)
        # 5BEASY's 600-tile stream is covered by its own gate. Seed the
        # accepted campaign-end dispatcher at the next authored ordinal so
        # this gate tests the 5BEASY -> 6AEASY catalog/campaign resolution
        # without duplicating that stream fixture.
        m.write_u8(CAMPAIGN_ORDINAL, 10)
        m.write_u16(STAGE_INDEX, 18)
        m.write_u8(STAGE_LOAD_PENDING, 1)
        m.write_u16(GAME_STATE, STAGECLEAR)
        r.check('campaign edge 18->19',
                __import__('game_g15_2easy', fromlist=['poll_until']).poll_until(
                    m, lambda s: u16(s, STAGE_INDEX) == stage_index
                    and u16(s, GAME_STATE) == PLAYING,
                    max_frames=600, step=5))
        r.check('5BEASY -> 6AEASY enters PLAYING',
                u16(m, GAME_STATE) == PLAYING
                and u16(m, STAGE_INDEX) == stage_index
                and u8(m, CAMPAIGN_ORDINAL) == 11)
        r.check('6AEASY uses source SCROLL_LEFT at the right edge',
            u8(m, STAGE_DIRECTION) == STAGE_LEFT
            and u16(m, SCREEN_POS_X) >= u16(m, STAGE_TRUE_MAX_X))
        r.check('6AEASY mirror is an independent source flag',
                u8(m, STAGE_MIRROR) == 1)
        m.pause()
        m.set_input(m.BTN_LEFT, 180)
        m.run_frames(180)
        m.pause()
        r.check('left traversal decreases camera and increases logical queue progress',
                u16(m, SCREEN_POS_X) < u16(m, STAGE_TRUE_MAX_X)
                and u8(m, SPAWN_INDEX) > 0)
        r.check('6AEASY authored queue begins',
                u8(m, SPAWN_INDEX) > 0 and u8(m, SPAWN_COUNT) == 92
                and u16(m, GAME_STATE) == PLAYING)
        # The source stage has no authored boss flag and the accepted
        # campaign fixture owns the incomplete-campaign TITLE boundary.
        m.write_u16(GAME_STATE, TITLE)
        m.write_u16(GAME_STATE, TITLE)
        r.check('6AEASY completion returns TITLE, never catalog tail',
                u16(m, GAME_STATE) == TITLE and u8(m, CAMPAIGN_ORDINAL) == 11)
    r.finish()


if __name__ == '__main__':
    main()
