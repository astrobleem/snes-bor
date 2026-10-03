#!/usr/bin/env python3
"""Focused G15 Batch M proof for BOR 6CEASY and the Rugal handoff."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, exact_input_edge, open_session, pasm_constant, pasm_constant_in
from game_g15_2easy import poll_until, u8, u16
import game_bor_startup_select as startup

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402
sys.path[:0] = [os.path.join(ROOT, 'tools', 'bg_converter'),
                os.path.join(ROOT, 'tools', 'bor_converter')]
from pak_extract import extract  # noqa: E402
from level_parse import parse_level  # noqa: E402
from spawn_parse import GroupEvent, SpawnEvent, WaitEvent, parse_spawns  # noqa: E402

PAK = os.path.join(ROOT, 'Beats of Rage Original [v.3.0 Build 4086].pak')
LEVEL = r'DATA\EASY\6CEASY.TXT'
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PREV = pasm_constant_in('src/core/game_state.pasm', 'Game_StatePrev')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
SCENE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_SCENE_FRAME')
STAGECLEAR = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_STAGECLEAR')
TITLE = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_TITLE')
CAMPAIGN_ID = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignId')
CAMPAIGN_ORDINAL = pasm_constant_in('src/core/game_state.pasm', 'Game_CampaignOrdinal')
STAGE_PENDING = pasm_constant_in('src/core/game_state.pasm', 'Stage_LoadPending')
STAGE_CLEARED = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
STAGE_DIRECTION = pasm_constant_in('src/core/game_state.pasm', 'Stage_ScrollDirection')
STAGE_RIGHT = pasm_constant_in('tools/audio/stage_scroll_config.pasm', 'STAGE_SCROLL_RIGHT')
SCENE_ACTIVE = pasm_constant('SceneVideo_TestActive')
SCENE_ID = pasm_constant('SceneVideo_RequestedSceneId')
SCENE_RUGAL = pasm_constant_in('src/generated/scene_video_meta.pasm', 'SceneVideo_Record0_SceneId')
SCENE_TRACK = pasm_constant('Music_LastTrack')
SCENE_TRANSITION = pasm_constant('Music_LastTransition')
MUSIC_STAGE = pasm_constant('MUSIC_TRANSITION_STAGE')
SCENE_SKIP = pasm_constant('SceneVideo_PlaySkipCount')
SCENE_SWAPS = pasm_constant('SceneVideo_PlaySwaps')
SCENE_LATE = pasm_constant('SceneVideo_PlayLateCount')
SCENE_RETRIES = pasm_constant('SceneVideo_PlayDmaRetries')
SCORE = pasm_constant_in('src/core/game_state.pasm', 'Game_Score32')
P1_LIVES = pasm_constant_in('src/core/game_state.pasm', 'P1_Lives16')
P2_LIVES = pasm_constant_in('src/core/game_state.pasm', 'P2_Lives16')
CREDITS = pasm_constant_in('src/core/game_state.pasm', 'Game_Credits')


def source_audit(r):
    text = extract(PAK, LEVEL).decode('latin1')
    level = parse_level(text, LEVEL)
    events = parse_spawns(text)
    spawns = [e for e in events if isinstance(e, SpawnEvent)]
    stage = next(s for s in build_rom.STAGE_CONFIGS
                 if s['source_level'].upper() == LEVEL.upper())
    index = build_rom.STAGE_CONFIGS.index(stage)
    manifest = json.load(open(os.path.join(ROOT, stage['bg'], 'manifest.json'), encoding='utf-8'))
    fp_manifest = json.load(open(os.path.join(ROOT, stage['frontpanel'], 'manifest.json'), encoding='utf-8'))
    blob = open(os.path.join(ROOT, stage['spawn']), 'rb').read()
    r.check('6CEASY is physical stage 21 and logical ordinal 14',
            index == 21 and build_rom.CAMPAIGN_ENTRY_MAPS['BOR_ORIGINAL'][-2:] ==
            [('scene', SCENE_RUGAL, 'RUGAL'), ('stage', 21, LEVEL)])
    r.check('BOR campaign contains 15 typed entries with Rugal before 6CEASY',
            len(build_rom.CAMPAIGN_ENTRY_MAPS['BOR_ORIGINAL']) == 15)
    r.check('Boss Hotel 6CEASY panels/dimensions/order are source-authored',
            level.background.lower().endswith(r'data\bgs\boss\back.gif')
            and level.frontpanel.lower().endswith(r'data\bgs\boss\front.gif')
            and len(level.panels) == 5 and ''.join(level.order) == 'abcde'
            and manifest['width_px'] == 280 and manifest['height_px'] == 224
            and manifest['width_tiles'] == 35 and fp_manifest['width_tiles'] == 35)
    r.check('6CEASY is right-scrolling with authored JOE music',
            any(x.strip().lower().split() == ['direction', 'right'] for x in text.splitlines())
            and any(x.strip().lower().startswith('music') and 'joe.bor' in x.lower()
                    for x in text.splitlines()))
    r.check('source queue has 34 records: 32 actors, one wait, one group',
            len(events) == 34 and len(spawns) == 32
            and sum(isinstance(e, WaitEvent) for e in events) == 1
            and sum(isinstance(e, GroupEvent) for e in events) == 1
            and len(blob) == 340)
    r.check('source boss and spawn order are preserved',
            spawns[0].character.lower() == 'rugal' and spawns[0].boss
            and spawns[0].alias == 'Mr._Y' and spawns[0].health == 350
            and [e.character.lower() for e in spawns[1:5]] ==
            ['yashiro', 'ralf', 'eiji', "k'"]
            and set(e.character.lower() for e in spawns) >=
            {'rugal', 'eiji', 'yashiro', 'ralf', 'shermie', 'angel', "k'"})
    r.check('6CEASY has no holes, endhole, or blocked directives',
            not any(x.strip().lower().startswith(('hole ', 'endhole ', 'blocked '))
                    for x in text.splitlines()))
    return index, len(events)


def setup_rugal(m):
    m.write_u8(CAMPAIGN_ID, 0)
    # Ordinal 12 is the active 6BEASY entry; the real stage-clear resolver
    # advances it to ordinal 13 (Rugal), then scene continuation advances to
    # ordinal 14 (6CEASY).
    m.write_u8(CAMPAIGN_ORDINAL, 12)
    m.write_u16(STAGE_INDEX, 20)
    m.write_u8(STAGE_PENDING, 1)
    m.write_u16(GAME_STATE, STAGECLEAR)


def snapshot(m):
    return (bytes(m.read_memory('snesMemory', SCORE, 32)[:4]),
            u16(m, P1_LIVES), u16(m, P2_LIVES), u8(m, CREDITS))


def reach_stage(m, r, skip=False):
    setup_rugal(m)
    saw_scene = poll_until(m, lambda s: u16(s, GAME_STATE) == SCENE
                           and u8(s, SCENE_ACTIVE) == 0xA5,
                           max_frames=900, step=1)
    if skip:
        m.run_frames(25)
        swaps = u16(m, SCENE_SWAPS)
        exact_input_edge(m, m.BTN_A, 1)
    else:
        swaps = None
    saw_title = False
    reached = False
    for _ in range(1900):
        m.run_frames(1)
        state = u16(m, GAME_STATE)
        if state == TITLE:
            saw_title = True
        if state == PLAYING and u8(m, CAMPAIGN_ORDINAL) == 14 and u16(m, STAGE_INDEX) == 21:
            reached = True
            break
    if not reached:
        print('handoff diagnostic:', {
            'state': u16(m, GAME_STATE),
            'prev': u16(m, GAME_STATE_PREV),
            'ordinal': u8(m, CAMPAIGN_ORDINAL),
            'stage': u16(m, STAGE_INDEX),
            'scene_active': u8(m, SCENE_ACTIVE),
            'scene_id': u8(m, SCENE_ID),
            'scene_skip': u8(m, SCENE_SKIP),
            'scene_swaps': u16(m, SCENE_SWAPS),
            'late': u16(m, SCENE_LATE),
            'retries': u16(m, SCENE_RETRIES), 'reached': reached, 'saw_scene': saw_scene,
            'saw_title': saw_title}, flush=True)
    return saw_scene, reached, saw_title, swaps


def main():
    r = Reporter('G15-BATCH-M-6CEASY', kind='GATE')
    stage_index, spawn_count = source_audit(r)
    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        before = snapshot(m)
        scene, natural, title, _ = reach_stage(m, r)
        r.check('Rugal natural completion enters 6CEASY without TITLE',
                scene and natural and not title)
        r.check('6CEASY runtime stage state/content/music is correct',
                u8(m, CAMPAIGN_ORDINAL) == 14 and u16(m, STAGE_INDEX) == stage_index
                and u16(m, GAME_STATE) == PLAYING and u8(m, STAGE_DIRECTION) == STAGE_RIGHT
                and u8(m, SPAWN_COUNT) == spawn_count and u8(m, SCENE_TRACK) == 7
                and u8(m, SCENE_TRANSITION) == MUSIC_STAGE)
        r.check('natural Rugal video proof remains intact',
                u16(m, SCENE_LATE) == 0 and u16(m, SCENE_RETRIES) == 0)
        r.check('Rugal preserves score/lives/credits into 6CEASY', snapshot(m) == before)

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        before = snapshot(m)
        scene, skipped_stage, title, swaps = reach_stage(m, r, skip=True)
        r.check('real Rugal skip continues directly into 6CEASY',
                scene and skipped_stage and not title and u8(m, SCENE_SKIP) == 1)
        r.check('skip has no post-skip swap and stage music owns handoff',
                swaps is not None and u16(m, SCENE_SWAPS) == swaps
                and u8(m, SCENE_TRACK) == 7 and u8(m, SCENE_TRANSITION) == MUSIC_STAGE)
        r.check('skip preserves score/lives/credits', snapshot(m) == before)

        m.write_u8(STAGE_PENDING, 1)
        m.write_u8(STAGE_CLEARED, 1)
        m.write_u16(GAME_STATE, STAGECLEAR)
        ended = poll_until(m, lambda s: u16(s, GAME_STATE) == TITLE,
                           max_frames=900, step=1)
        r.check('6CEASY temporary campaign end returns TITLE',
                ended and u8(m, CAMPAIGN_ORDINAL) == 14 and u16(m, GAME_STATE_PREV) == TITLE)
    r.finish()


if __name__ == '__main__':
    main()
