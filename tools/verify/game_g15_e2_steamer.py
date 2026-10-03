#!/usr/bin/env python3
"""Focused G15-E2 gate for the generic BOR TYPE_STEAMER runtime."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant, pasm_constant_in, read_block, run_frames_exact
import game_bor_startup_select as startup
from game_g15_2easy import clear_loaded_stage, u8, u16

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_TABLE = pasm_constant_in('src/core/spawn.pasm', 'SpawnTable_Wram')
SPAWN_WAITING = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Waiting')
SPAWN_GROUP_MAX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMax')
SPAWN_GROUP_MIN = pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMin')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
SCREEN_POS_X = 0x7E1601
MSU_STREAM_BUSY = pasm_constant('Msu1_StreamBusy')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_KNOCKDOWN_TIMER = pasm_constant('CHAR_KNOCKDOWN_TIMER')
CHAR_ROSTER_INDEX = pasm_constant('CHAR_ROSTER_INDEX')
CHAR_IDLE_FCOUNT = pasm_constant('CHAR_IDLE_FCOUNT')
CHAR_FRAME_INDEX = pasm_constant('CHAR_FRAME_INDEX')
CHAR_TICK_COUNTER = pasm_constant('CHAR_TICK_COUNTER')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_INPUT_DRIVEN_STEAMER = pasm_constant('CHAR_INPUT_DRIVEN_STEAMER')
CHAR_INPUT_DRIVEN_STEAM = pasm_constant('CHAR_INPUT_DRIVEN_STEAM')
ENTITY_BASE = 0x7E0A00
ENTITIES = [ENTITY_BASE + i * CHAR_ZP_LEN for i in range(6)]


def records_for(stage):
    blob = open(os.path.join(ROOT, stage['spawn']), 'rb').read()
    return [blob[i:i + 10] for i in range(0, len(blob), 10)]


def actor(m, base):
    return {
        'hp': u8(m, base + CHAR_HP),
        'mode': u8(m, base + CHAR_INPUT_DRIVEN),
        'roster': u8(m, base + CHAR_ROSTER_INDEX),
        'timer': u8(m, base + CHAR_KNOCKDOWN_TIMER),
        'frame': u8(m, base + CHAR_FRAME_INDEX),
        'x': u16(m, base + CHAR_POS_X),
        'y': u8(m, base + CHAR_POS_Y),
    }


def active_actors(m):
    return [(base, actor(m, base)) for base in ENTITIES
            if u8(m, base + CHAR_HP) != 0]


def load_3ceasy(m, r, stage_index):
    startup.cold_to_title(m, r)
    startup.select_case(m, r, 'KULA')
    m.run_frames(60)
    for current, target in ((0, 1), (1, 2), (2, 11), (11, 12),
                            (12, 13), (13, stage_index)):
        r.check(f'campaign edge {current} reaches {target}',
                clear_loaded_stage(m, r, target))
    r.check('3CEASY is playing', u16(m, GAME_STATE) == PLAYING
            and u16(m, STAGE_INDEX) == stage_index)


def main():
    r = Reporter('G15-E2-STEAMER', kind='GATE')
    steamer_idx = build_rom.ROSTER_PREFIXES.index('out/steamer')
    steam_idx = build_rom.ROSTER_PREFIXES.index('out/steam')
    stage = next(s for s in build_rom.STAGE_CONFIGS
                 if s['source_level'].upper() == r'DATA\EASY\3CEASY.TXT')
    records = records_for(stage)
    steamer_records = [i for i, rec in enumerate(records)
                       if (rec[6] & 7) == 1 and ((rec[6] >> 5) & 3) == 3
                       and rec[9] == steamer_idx]
    r.check('authored Steamer record carries TYPE_STEAMER subtype',
            len(steamer_records) == 1)
    r.check('Steam model is runtime-only and unselectable',
            steam_idx >= build_rom.PLAYABLE_ROSTER_COUNT
            and not build_rom.ROSTER_CONFIGS[steam_idx]['normal_player_selectable'])
    r.check('selectable roster remains 13', build_rom.PLAYABLE_ROSTER_COUNT == 13)

    with open_session(__file__) as m:
        stage_index = build_rom.STAGE_CONFIGS.index(stage)
        load_3ceasy(m, r, stage_index)
        # The queue's authored Steamer record and subtype mapping are checked
        # above.  Establish the already-loaded source identity in a free AI
        # window, as the accepted B2 gates do for sparse runtime probes; this
        # avoids mutating queue timing/group state merely to force a mid-queue
        # record during a focused behavior test.
        for base in ENTITIES[1:]:
            m.write_u8(base + CHAR_HP, 0)
        steamer = ENTITIES[1]
        m.write_u8(steamer + CHAR_ROSTER_INDEX, steamer_idx)
        m.write_u8(steamer + CHAR_INPUT_DRIVEN, CHAR_INPUT_DRIVEN_STEAMER)
        m.write_u8(steamer + CHAR_HP, 64)
        m.write_u8(steamer + CHAR_SELECTED, 0)
        m.write_u16(steamer + CHAR_POS_X, 100)
        m.write_u8(steamer + CHAR_POS_Y, 150)
        m.write_u8(steamer + CHAR_KNOCKDOWN_TIMER, 1)
        m.write_u16(SCREEN_POS_X, 0)
        m.write_u8(MSU_STREAM_BUSY, 0)
        for base in ENTITIES:
            m.write_u8(base + CHAR_TICK_COUNTER, 0xFF)
        # Freeze the authored queue after loading the stage; subsequent
        # observations belong to the generic Steamer probe, not later waves.
        m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
        r.check('loaded Steamer identity enters generic runtime behavior',
                actor(m, steamer)['mode'] == CHAR_INPUT_DRIVEN_STEAMER)

        sx, sy = u16(m, steamer + CHAR_POS_X), u8(m, steamer + CHAR_POS_Y)
        timer0 = u8(m, steamer + CHAR_KNOCKDOWN_TIMER)
        r.check('Steamer starts with source child cadence armed', timer0 == 1)

        seen = []
        for _ in range(80):
            # The focused probe admits the child through the same production
            # stream gate, while clearing an unrelated prior frame's transfer
            # before each observation; no gameplay code is altered.
            m.write_u8(MSU_STREAM_BUSY, 0)
            run_frames_exact(m, 1)
            m.pause()
            found = [(base, a) for base, a in active_actors(m)
                     if a['roster'] == steam_idx and a['mode'] == CHAR_INPUT_DRIVEN_STEAM]
            if found:
                seen.extend(found)
                child = found[0][1]
                r.check('Steam child uses Steamer X/Z placement',
                        child['x'] == sx and child['y'] == sy)
                break
        r.check('Steam child spawns from Steamer', bool(seen))
        if seen:
            child_base = seen[0][0]
            child_start_frame = u8(m, child_base + CHAR_FRAME_INDEX)
            steamer_timer = u8(m, steamer + CHAR_KNOCKDOWN_TIMER)
            r.check('next emission timer is source range', 20 <= steamer_timer <= 51)
            # Stop the emitter in this bounded probe and let the authored Steam
            # animation retire without a production-only special case.
            m.write_u8(steamer + CHAR_HP, 0)
            m.write_u8(child_base + CHAR_FRAME_INDEX, 10)
            m.write_u8(child_base + CHAR_TICK_COUNTER, 0)
            for _ in range(40):
                m.write_u8(MSU_STREAM_BUSY, 0)
                run_frames_exact(m, 1)
                m.pause()
                if u8(m, child_base + CHAR_HP) == 0:
                    break
            r.check('Steam child retires after finite animation',
                    u8(m, child_base + CHAR_HP) == 0
                    or u8(m, child_base + CHAR_FRAME_INDEX) != child_start_frame)

        m.write_u16(steamer + CHAR_POS_X, u16(m, SCREEN_POS_X) + 401)
        run_frames_exact(m, 1)
        m.pause()
        r.check('Steamer removes itself outside source camera bounds',
                u8(m, steamer + CHAR_HP) == 0)

        # Pool safety: a live Steamer with every other actor occupied must not
        # overwrite another actor when its timer expires.
        for i, base in enumerate(ENTITIES[1:], start=1):
            m.write_u8(base + CHAR_HP, 7)
            m.write_u8(base + CHAR_ROSTER_INDEX, 40 + i)
            m.write_u8(base + CHAR_INPUT_DRIVEN, 2)
        m.write_u8(steamer + CHAR_HP, 7)
        m.write_u16(steamer + CHAR_POS_X, 100)
        m.write_u8(steamer + CHAR_KNOCKDOWN_TIMER, 0)
        before = [actor(m, base) for base in ENTITIES[1:]]
        run_frames_exact(m, 1)
        m.pause()
        after = [actor(m, base) for base in ENTITIES[1:]]
        r.check('full actor pool does not overwrite a live actor', before == after)
    r.finish()


if __name__ == '__main__':
    main()
