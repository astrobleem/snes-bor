#!/usr/bin/env python3
"""Focused G15 Batch K gate for authoritative BOR 6BEASY."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant, pasm_constant_in
import game_bor_startup_select as startup
from game_g15_2easy import u8, u16, poll_until

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402
sys.path[:0] = [os.path.join(ROOT, 'tools', 'bg_converter'),
               os.path.join(ROOT, 'tools', 'bor_converter')]
from pak_extract import extract  # noqa: E402
from spawn_parse import parse_spawns, SpawnEvent, WaitEvent, GroupEvent  # noqa: E402

PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
LEVEL = r'DATA\EASY\6BEASY.TXT'
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
STAGE_LOAD_PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
STAGE_DIRECTION = pasm_constant_in('src/core/game_state.pasm', 'Stage_ScrollDirection')
STAGE_MIRROR = pasm_constant_in('src/core/game_state.pasm', 'Stage_Mirror')
STAGE_LEFT = pasm_constant_in('tools/audio/stage_scroll_config.pasm', 'STAGE_SCROLL_LEFT')
SCREEN_POS_X = 0x7E0000 + pasm_constant_in('src/core/screen.pasm', 'Screen_PosX_Lo')
STAGE_TRUE_MAX_X = pasm_constant_in('src/core/game_state.pasm', 'Stage_TrueMaxX')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')


def main():
    r = Reporter('G15-BATCH-K-6BEASY', kind='GATE')
    text = extract(PAK, LEVEL).decode('latin1')
    events = parse_spawns(text)
    spawns = [e for e in events if isinstance(e, SpawnEvent)]
    stage = next(s for s in build_rom.STAGE_CONFIGS
                 if s['source_level'].upper() == LEVEL.upper())
    stage_index = build_rom.STAGE_CONFIGS.index(stage)
    manifest = json.load(open(os.path.join(ROOT, stage['bg'], 'manifest.json')))
    fp_manifest = json.load(open(os.path.join(ROOT, stage['frontpanel'], 'manifest.json')))
    blob = open(os.path.join(ROOT, stage['spawn']), 'rb').read()

    r.check('6BEASY follows 6AEASY at physical index 20',
            stage_index == 20 and build_rom.CAMPAIGN_STAGE_MAPS['BOR_ORIGINAL'] ==
            [0, 1, 2, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
    r.check('boss hotel panels and dimensions are preserved',
            manifest['width_px'] == 336 and manifest['height_px'] == 224
            and manifest['width_tiles'] == 42 and fp_manifest['width_tiles'] == 42)
    r.check('source queue inventory is preserved',
            len(events) == 15 and len(spawns) == 11
            and sum(isinstance(e, WaitEvent) for e in events) == 2
            and sum(isinstance(e, GroupEvent) for e in events) == 2
            and len(blob) == 150)
    r.check('source direction and content are represented',
            any(x.strip().lower().split() == ['direction', 'left'] for x in text.splitlines())
            and stage.get('scroll_direction') == 'left'
            and not any(x.strip().lower().startswith(('hole ', 'endhole ', 'blocked '))
                        for x in text.splitlines())
            and not any(e.boss for e in spawns)
            and {e.character.lower() for e in spawns} ==
            {'shermie', 'yashiro', "k'", 'angel', 'billy', 'joe', 'jhun', 'ralf'})
    r.check('frontpanel and authored queue are shipped',
            stage.get('frontpanel') == 'out/fp_6beasy'
            and all(e.at == 1 for e in spawns))
    r.check('selection roster and actor capacity remain bounded',
            build_rom.PLAYABLE_ROSTER_COUNT == 13
            and pasm_constant('CHARACTER_ACTOR_COUNT') == 6)

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        m.write_u8(CAMPAIGN_ORDINAL, 11)
        m.write_u16(STAGE_INDEX, 19)
        m.write_u8(STAGE_LOAD_PENDING, 1)
        m.write_u16(GAME_STATE, STAGECLEAR)
        loaded = poll_until(m, lambda s: u16(s, STAGE_INDEX) == stage_index
                            and u16(s, GAME_STATE) == PLAYING,
                            max_frames=600, step=1)
        r.check('6AEASY -> 6BEASY enters PLAYING', loaded)
        r.check('6BEASY starts as source SCROLL_LEFT at right edge',
                u8(m, STAGE_DIRECTION) == STAGE_LEFT
                and u8(m, STAGE_MIRROR) == 0
                and u16(m, SCREEN_POS_X) >= u16(m, STAGE_TRUE_MAX_X))
        m.pause()
        m.set_input(m.BTN_LEFT, 120)
        m.run_frames(120)
        m.pause()
        r.check('left traversal advances queue from logical levelpos',
                u16(m, SCREEN_POS_X) < u16(m, STAGE_TRUE_MAX_X)
                and u8(m, SPAWN_INDEX) > 0 and u8(m, SPAWN_COUNT) == 15)
        m.write_u16(GAME_STATE, TITLE)
        r.check('6BEASY temporary completion returns TITLE',
                u16(m, GAME_STATE) == TITLE and u8(m, CAMPAIGN_ORDINAL) == 12)
    r.finish()


if __name__ == '__main__':
    main()
