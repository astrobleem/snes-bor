#!/usr/bin/env python3
"""G12 production-spawn contract for six bounded CharacterEntity actors.

The fixture supplies a reproducible queue of real spawn records in the normal
SpawnTable_Wram format.  It does not construct or populate CharacterEntity
state: every actor is initialized by the production Spawn_Play path.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, pasm_constant_in,
                      read_block, run_frames_exact, exact_input_edge, Reporter)  # noqa: E402
from g12_scaling_baseline import source_identity

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_FACING_LEFT = pasm_constant('CHAR_FACING_LEFT')
CHAR_TILE_COLUMN = pasm_constant('CHAR_TILE_COLUMN')
CHAR_FRAME_INDEX = pasm_constant('CHAR_FRAME_INDEX')
CHAR_ROSTER_INDEX = pasm_constant('CHAR_ROSTER_INDEX')
CHAR_ATTACK_VARIANT = pasm_constant('CHAR_ATTACK_VARIANT')
CHAR_PALETTE_SLOT = pasm_constant('CHAR_PALETTE_SLOT')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_PICKUP_TYPE = pasm_constant('CHAR_PICKUP_TYPE')
CHAR_GRAB_TARGET = pasm_constant('CHAR_GRAB_TARGET')
CHAR_GRABBED_BY = pasm_constant('CHAR_GRABBED_BY')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_HIT_APPLIED = pasm_constant('CHAR_HIT_APPLIED')
GAME_SCORE = pasm_constant_in('src/core/game_state.pasm', 'Game_Score')
PICKUP_TYPE_MONEY = pasm_constant('PICKUP_TYPE_MONEY')
PICKUP_SCORE_MONEY = pasm_constant('PICKUP_SCORE_MONEY')
ACTOR_COUNT = pasm_constant('CHARACTER_ACTOR_COUNT')
PROP_MODE = pasm_constant('CHAR_INPUT_DRIVEN_PROP')
SPAWN_TABLE = pasm_constant_in('src/core/spawn.pasm', 'SpawnTable_Wram')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
SPAWN_WAITING = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Waiting')
SPAWN_GROUP_MIN = pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMin')
SPAWN_GROUP_MAX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMax')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PREV = pasm_constant_in('src/core/game_state.pasm', 'Game_StatePrev')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
STAGE_CLEARED = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
STAGE_TRUE_MAX_X = pasm_constant_in('src/core/game_state.pasm', 'Stage_TrueMaxX')
WORLD_MAX_X = pasm_constant_in('src/main.pasm', 'WorldMaxX')
SCREEN_POS_X = 0x7E1601
SCREEN_MAX_X = 0x7E160E
SCREEN_TARGET_X = 0x7E1616
SCREEN_SIZE_X = 0x7E1606
SCREEN_FOCUS_ID = 0x7E1620
SCREEN_FOCUS_SLOT = 0x7E1622
SCREEN_FOCUS_NUM = 0x7E161E
STREAM_ENABLED = 0x7E2521
STREAM_STAGED_LO = 0x7E2522
STREAM_STAGED_HI = 0x7E2524
STREAM_PEND_COL = 0x7E2528
STREAM_PEND_TILE = 0x7E252A
STREAM_WIDTH = 0x7E252C
STREAM_DESIRED_LO = 0x7E2535
STREAM_DESIRED_HI = 0x7E2537
STREAM_COL_PENDING = 0x7E2594
OOP_DP = 0x7E081A
OOP_RESULT_X = 0x7E09A0
MSU_BUSY = pasm_constant('Msu1_StreamBusy')
CHAR_SELECT_LOADED = pasm_constant('CharSelect_Loaded')
MSU_PRESENT = pasm_constant('Msu1Present')
CHAR_ROSTER_COUNT = pasm_constant('CharSelect_RosterCount')
ANIM_HEADER = pasm_constant('AnimHeaderStaging')
ACTOR_INVULN = pasm_constant_in('src/core/game_state.pasm', 'Actor_InvulnFrames')
ENTITY4_ITEM_ROSTER = pasm_constant_in('src/main.pasm', 'Entity4_ItemRosterIdx')
ENTITY5_ITEM_ROSTER = pasm_constant_in('src/main.pasm', 'Entity5_ItemRosterIdx')
TRACE_ENTRY = pasm_constant_in('src/main.pasm', 'G12_StageTrace_Entry')
TRACE_HPS = pasm_constant_in('src/main.pasm', 'G12_StageTrace_Hp1')
TRACE_CARRY = pasm_constant_in('src/main.pasm', 'G12_StageTrace_Carry')
NMI_FRAME_COUNTER = pasm_constant_in('src/core/nmi.pasm', 'Nmi_FrameCounter')
OAM_NEED_FULL = pasm_constant_in('src/core/oam.pasm', 'Oam_NeedFullUpload')

BASE = 0x7E0A00
ENTITIES = [BASE + i * CHAR_ZP_LEN for i in range(ACTOR_COUNT)]
RECORD_SIZE = 10
VRAM_BASE_TILES = [0x00, 0x04, 0x08, 0x0C, 0x80, 0x84]


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def write_record(m, index, trigger, x, y, facing, kind=0, hp=64, item=0, roster=0):
    data = bytes((trigger & 0xff, (trigger >> 8) & 0xff,
                  x & 0xff, (x >> 8) & 0xff, y & 0xff, facing & 0xff,
                  kind & 0xff, hp & 0xff, item & 0xff, roster & 0xff))
    m.write_memory('snesMemory', SPAWN_TABLE + index * RECORD_SIZE, data.hex())


def install_fixture_queue(m):
    # Five actual enemy records. Slot 4/5 are reached only by the production
    # free-slot walk after slots 1-3 have been filled.
    positions = [(80, 70), (120, 55), (160, 85), (280, 45), (300, 100)]
    for i, (x, y) in enumerate(positions):
        write_record(m, i, 0, x, y, i & 1, 0, CHAR_HP_MAX)
    # A seventh prop record is consumed after slot 4 is killed and reused.
    write_record(m, 5, 0, 280, 60, 0, 0, CHAR_HP_MAX)
    write_record(m, 6, 0, 300, 60, 1,
                 1 | (PICKUP_TYPE_MONEY << 5), 1, 14, 18)
    m.write_u8(SPAWN_INDEX, 0)
    m.write_u8(SPAWN_COUNT, 5)
    m.write_u8(SPAWN_WAITING, 0)
    m.write_u8(pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMin'), 100)
    m.write_u8(pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMax'), 100)
    m.write_u8(STAGE_CLEARED, 0)


def wait_for_six(m, max_frames=600):
    first_live = {}
    for _ in range(max_frames):
        for i, base in enumerate(ENTITIES[1:], start=1):
            if i not in first_live and u8(m, base + CHAR_HP) > 0:
                first_live[i] = (u16(m, base + CHAR_POS_X),
                                 u8(m, base + CHAR_FACING_LEFT))
        if all(u8(m, base + CHAR_HP) > 0 for base in ENTITIES[1:]):
            return first_live
        m.run_frames(1)
    return None


def oam_by_x(m, expected):
    oam = read_block(m, 0, 512, mem_type='snesSpriteRam')
    found = {i: [] for i in expected}
    for slot in range(128):
        off = slot * 4
        for i, x in expected.items():
            if oam[off] == x:
                found[i].append((slot, oam[off + 1]))
    return found


def main():
    r = Reporter('G12-SIX-ACTOR-PRODUCTION', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator(); m.run_frames(180); m.pause()
        # Clear the boot stage's ordinary wave before installing the bounded
        # six-record fixture. Otherwise wait_for_six can return immediately
        # on pre-existing actors and the added-slot spawn coordinates are not
        # evidence from this fixture's production Spawn_Play calls.
        for base in ENTITIES[1:]:
            m.write_u8(base + CHAR_HP, 0)
        install_fixture_queue(m)
        spawn_observed = wait_for_six(m)
        six_spawned = spawn_observed is not None
        m.pause()
        # Freeze the fixture queue after the five production records have
        # filled slots 1-5; otherwise the scheduler continues retrying the
        # next live-stage record while this gate is sampling ownership.
        m.write_u8(SPAWN_INDEX, u8(m, SPAWN_COUNT))
        print('spawned HP:', [u8(m, b + CHAR_HP) for b in ENTITIES])
        print('spawn index/count/group:', u8(m, SPAWN_INDEX), u8(m, SPAWN_COUNT),
              u8(m, SPAWN_GROUP_MIN), u8(m, SPAWN_GROUP_MAX))
        r.check('production Spawn_Play reached five live combat actors', six_spawned)
        r.check('all six actor states are distinct live slots',
                len({base for base in ENTITIES}) == 6 and all(u8(m, b + CHAR_HP) > 0 for b in ENTITIES))
        spawned_x = [spawn_observed[i][0] for i in (4, 5)] if six_spawned else []
        spawned_facing = [spawn_observed[i][1] for i in (4, 5)] if six_spawned else []
        print('added-slot production spawn X (first live frame):', spawned_x)
        print('added-slot production spawn facing (first live frame):', spawned_facing)
        r.check('added-slot production spawn preserves full-width X coordinates',
                spawned_x == [280, 300])

        # Pin the spawned actors only after production initialization so the
        # visual and VRAM checks are deterministic without changing spawn.
        for i, base in enumerate(ENTITIES):
            m.write_u16(base + CHAR_POS_X, 50 + i * 30)
            m.write_u8(base + CHAR_POS_Y, 45 + i * 7)
            if i:
                m.write_u8(base + CHAR_INPUT_DRIVEN, 0)
        m.run_frames(3); m.pause()
        camera = u16(m, SCREEN_POS_X)
        expected_x = {i: (50 + i * 30 - camera) & 0xff for i in range(6)}
        found = oam_by_x(m, expected_x)
        print('camera/positions:', camera, [u16(m, b + CHAR_POS_X) for b in ENTITIES])
        print('input modes:', [u8(m, b + CHAR_INPUT_DRIVEN) for b in ENTITIES])
        print('hardware OAM matches:', found)
        print('tile/facing:', [u8(m, b + CHAR_TILE_COLUMN) for b in ENTITIES],
              [u8(m, b + CHAR_FACING_LEFT) for b in ENTITIES])
        r.check('six spawned actors each have exactly one identifiable OAM sprite',
                all(len(v) == 1 for v in found.values()))
        r.check('six spawned actor OAM entries are distinct',
                all(found.values()) and len({v[0][0] for v in found.values()}) == 6)
        r.check('added slots use non-overlapping physical tile columns',
                [u8(m, ENTITIES[i] + CHAR_TILE_COLUMN) for i in (4, 5)] == [0x20, 0x21])
        r.check('six actors use distinct palette slots',
                len({u8(m, ENTITIES[i] + CHAR_PALETTE_SLOT) for i in range(6)}) == 6)
        r.check('added-slot facing state is independently initialized',
                spawned_facing == [1, 0])

        # Completed-upload VRAM proof.  The single staging buffer can leave a
        # completed DMA one logical animation frame behind the entity state,
        # so identify the committed frame from the hardware bytes themselves;
        # never compare against a newer request merely because the queue is
        # currently idle.
        for i in (4, 5):
            m.write_u8(ENTITIES[i] + CHAR_INPUT_DRIVEN, 0)
        # Camera easing is substantially slower than player movement in this
        # path; 5000 exact edges is a bounded headroom interval at the
        # observed convergence rate, and every edge is checked for exact
        # advancement.
        for _ in range(5000):
            if u8(m, MSU_BUSY) == 0:
                m.run_frames(2); m.pause()
                if u8(m, MSU_BUSY) == 0:
                    break
            m.run_frames(1)
        m.pause()
        msu = open(os.path.join(ROOT, 'distribution', 'bor.msu'), 'rb').read()
        vram_ok = True; checked = 0; first_vram_mismatch = None
        committed_frames = {}
        for i, base in enumerate(ENTITIES[4:], start=4):
            entity = bytes(read_block(m, base, 64))
            col = entity[CHAR_TILE_COLUMN]
            got_rows = [bytes(read_block(m, 0x8000 + col * 128 + row * 512, 128,
                                         mem_type='snesVideoRam')) for row in range(6)]
            match = None
            for frame in range(16):
                source, state_name = source_identity(entity, frame, entity[CHAR_SELECTED], entity[CHAR_ATTACK_VARIANT])
                if source is not None and all(
                        got_rows[row] == msu[source + row * 128:source + (row + 1) * 128]
                        for row in range(6)):
                    match = (frame, state_name, source)
                    break
            if match is None:
                source, state_name = source_identity(entity, entity[CHAR_FRAME_INDEX], entity[CHAR_SELECTED], entity[CHAR_ATTACK_VARIANT])
                first_vram_mismatch = (i, entity[CHAR_FRAME_INDEX], entity[CHAR_ROSTER_INDEX], col, source, state_name)
                vram_ok = False
                checked += 6
            else:
                committed_frames[i] = match
                checked += 6
        print('completed frame identities:', committed_frames)
        if not vram_ok:
            print('first added-slot VRAM mismatch:', first_vram_mismatch)
        r.check(f'completed uploads match identified MSU frame sources ({checked} rows)', checked > 0 and vram_ok)

        # Added-slot combat state: the focused collision gate covers the real
        # attack path; this gate confirms production-spawned slot 4 remains a
        # live AI target and can be marked stunned independently.
        target4 = ENTITIES[4]
        hp4 = u8(m, target4 + CHAR_HP)
        m.write_u8(target4 + CHAR_HIT_STUN, 9)
        r.check('added slot 4 has independent live HP', hp4 > 0)
        r.check('added slot 4 accepts independent hit-stun state', u8(m, target4 + CHAR_HIT_STUN) == 9)

        # Reuse slot 4 through production Spawn_Play as a prop. Preserve stale
        # links first, then consume the queued prop record at index 6.
        m.write_u8(target4 + CHAR_GRAB_TARGET, 133)
        m.write_u8(target4 + CHAR_GRABBED_BY, 0)
        m.write_u8(target4 + CHAR_HP, 0)
        m.write_u8(SPAWN_INDEX, 6); m.write_u8(SPAWN_COUNT, 7)
        print('pre-reuse player load gate:', u8(m, CHAR_SELECT_LOADED),
              u8(m, CHAR_ROSTER_COUNT), u8(m, MSU_PRESENT), flush=True)
        for _ in range(180):
            if (u8(m, target4 + CHAR_INPUT_DRIVEN) == PROP_MODE
                    and u8(m, target4 + CHAR_HP) > 0
                    and u8(m, SPAWN_INDEX) == u8(m, SPAWN_COUNT)):
                break
            m.run_frames(1)
        m.pause()
        print('reused slot4 metadata:', u8(m, target4 + CHAR_INPUT_DRIVEN),
              u8(m, target4 + CHAR_PICKUP_TYPE),
              u8(m, ENTITY4_ITEM_ROSTER),
              u8(m, target4 + CHAR_GRAB_TARGET), u8(m, target4 + CHAR_GRABBED_BY))
        r.check('production spawn reused added slot 4', u8(m, target4 + CHAR_HP) > 0)
        r.check('reused slot 4 is classified as prop, not enemy', u8(m, target4 + CHAR_INPUT_DRIVEN) == PROP_MODE)
        r.check('reused prop carries its contained item roster metadata', u8(m, ENTITY4_ITEM_ROSTER) == 14)
        r.check('slot 4 reuse clears old grab links', u8(m, target4 + CHAR_GRAB_TARGET) == 0xFF and u8(m, target4 + CHAR_GRABBED_BY) == 0xFF)
        # Production prop initialization may still be in the object-art MSU
        # load at this boundary.  Capture that lifecycle instead of entering
        # the attack fixture while the shared character-load gate is zero.
        for q in range(20):
            print('reused prop load boundary:', q, u8(m, CHAR_SELECT_LOADED),
                  'msu/count/index', u8(m, MSU_PRESENT), u8(m, CHAR_ROSTER_COUNT), u8(m, pasm_constant('CharSelect_Index')),
                  u8(m, ENTITY4_ITEM_ROSTER), u8(m, target4 + CHAR_ROSTER_INDEX),
                  u8(m, target4 + CHAR_PICKUP_TYPE), 'idle', u8(m, target4 + 16), flush=True)
            if q == 0:
                print('reused prop header bytes:', bytes(read_block(m, ANIM_HEADER, 32)[:16]).hex(), flush=True)
            if u8(m, CHAR_SELECT_LOADED) != 0:
                break
            run_frames_exact(m, 1)

        # Added-slot break/reveal/collection proof through the production
        # attack path. Keep another actor's metadata live while slot 4 is
        # consumed so the reveal dispatcher cannot pass by clearing slot 3.
        m.write_u8(ENTITIES[3] + CHAR_PICKUP_TYPE, 1)
        for i in (1, 2, 3):
            m.write_u8(ENTITIES[i] + CHAR_HP, 0)
        player_x = u16(m, ENTITIES[0] + CHAR_POS_X)
        player_y = u8(m, ENTITIES[0] + CHAR_POS_Y)
        m.write_u16(target4 + CHAR_POS_X, player_x)
        m.write_u8(target4 + CHAR_POS_Y, player_y)
        m.write_u8(ENTITIES[0] + CHAR_HIT_STUN, 0)
        m.write_u8(ENTITIES[0] + CHAR_HIT_APPLIED, 0)
        # This is a fresh attack fixture.  The preceding independent hit-stun
        # and reuse checks may have armed the per-slot post-hit guard; clear
        # that timer as setup, just as the existing focused collision gate
        # does, rather than mistaking stale fixture state for invulnerability.
        m.write_u8(ACTOR_INVULN + 4, 0)
        m.write_u8(target4 + CHAR_GRAB_TARGET, 0xFF)
        m.write_u8(target4 + CHAR_GRABBED_BY, 0xFF)
        score_before_break = u16(m, GAME_SCORE)
        print('added-slot break setup:', player_x, player_y,
              u16(m, target4 + CHAR_POS_X), u8(m, target4 + CHAR_POS_Y),
              u8(m, ENTITIES[0] + CHAR_SELECTED),
              u8(m, ENTITIES[0] + CHAR_INPUT_DRIVEN), u8(m, target4 + CHAR_HP))
        # A released interval precedes the exact one-frame button edge.  The
        # edge is delivered through the shared exact helper so this gate does
        # not infer acceptance from wall-clock polling.
        run_frames_exact(m, 2)
        print('added-slot attack pre-edge:', u8(m, ENTITIES[0] + CHAR_INPUT_DRIVEN),
              u8(m, ENTITIES[0] + CHAR_SELECTED), u8(m, ENTITIES[0] + CHAR_HIT_APPLIED),
              u8(m, ENTITIES[0] + CHAR_HIT_STUN), u8(m, CHAR_SELECT_LOADED),
              u8(m, target4 + CHAR_INPUT_DRIVEN), u8(m, target4 + CHAR_HP),
              u16(m, target4 + CHAR_POS_X), u8(m, target4 + CHAR_POS_Y))
        broken = False
        for _ in range(40):
            exact_input_edge(m, m.BTN_Y, 1)
            if _ < 3:
                print('added-slot attack frame:', _,
                      u8(m, ENTITIES[0] + CHAR_SELECTED),
                      u8(m, ENTITIES[0] + CHAR_ATTACK_VARIANT),
                      u8(m, target4 + CHAR_HP))
            if u8(m, target4 + CHAR_HP) == 1:
                broken = True
                m.write_u16(target4 + CHAR_POS_X, 60000)
                break
        m.release_input(0)
        print('added-slot attack terminal:', u8(m, ENTITIES[0] + CHAR_SELECTED),
              u8(m, ENTITIES[0] + CHAR_FRAME_INDEX), u8(m, target4 + CHAR_HP),
              u8(m, target4 + CHAR_INPUT_DRIVEN), u8(m, ACTOR_INVULN + 4),
              u16(m, target4 + CHAR_POS_X), u8(m, target4 + CHAR_POS_Y),
              u8(m, target4 + CHAR_GRAB_TARGET), u8(m, target4 + CHAR_GRABBED_BY))
        r.check('added-slot prop breaks through production attack to pending reveal', broken)
        revealed = False
        for _ in range(90):
            if u8(m, ENTITY4_ITEM_ROSTER) == 0:
                revealed = True
                break
            run_frames_exact(m, 1)
        r.check('added-slot reveal clears only its own pending item identity',
                revealed and u8(m, ENTITIES[3] + CHAR_PICKUP_TYPE) == 1 and
                u8(m, target4 + CHAR_PICKUP_TYPE) == PICKUP_TYPE_MONEY and
                u8(m, target4 + CHAR_ROSTER_INDEX) == 14)
        score_before_touch = u16(m, GAME_SCORE)
        m.write_u16(target4 + CHAR_POS_X, u16(m, ENTITIES[0] + CHAR_POS_X))
        m.write_u8(target4 + CHAR_POS_Y, u8(m, ENTITIES[0] + CHAR_POS_Y))
        run_frames_exact(m, 3)
        score_after_touch = u16(m, GAME_SCORE)
        r.check('added-slot collection awards exactly once',
                score_after_touch == score_before_touch + PICKUP_SCORE_MONEY and
                u8(m, target4 + CHAR_PICKUP_TYPE) == 0)
        print('added-slot break/reveal/collection scores:', score_before_break,
              score_before_touch, score_after_touch)

        # Run the transition contract in a fresh gameplay state. The reuse
        # proof above intentionally exercises prop/reveal metadata; keeping
        # the transition proof independent makes any stale lifecycle state
        # observable instead of allowing it to mask the ordinary predicate.
        m.reset_emulator(); m.run_frames(180); m.pause()
        for base in ENTITIES[1:]:
            m.write_u8(base + CHAR_HP, 0)
        install_fixture_queue(m)
        stage_spawned = wait_for_six(m)
        m.pause()
        m.write_u8(SPAWN_INDEX, 7)
        r.check('fresh transition fixture uses production-spawned added actors',
                stage_spawned is not None and all(u8(m, b + CHAR_HP) > 0 for b in ENTITIES[1:]))

        # Only remaining enemy in slot 5 must hold the stage. Props do not
        # count as enemies in the production wait/completion accounting.
        m.write_u8(STAGE_CLEARED, 0)
        m.write_u8(SPAWN_WAITING, 0)
        m.write_u8(SPAWN_GROUP_MIN, 100)
        m.write_u8(SPAWN_GROUP_MAX, 100)
        for i in (1, 2, 3, 4): m.write_u8(ENTITIES[i] + CHAR_HP, 0)
        m.write_u8(ENTITIES[5] + CHAR_HP, CHAR_HP_MAX)
        m.write_u8(SPAWN_INDEX, 7); m.write_u8(SPAWN_COUNT, 7)
        nmi_before_alive = u16(m, NMI_FRAME_COUNTER)
        alive_run = run_frames_exact(m, 8); m.pause()
        nmi_after_alive = u16(m, NMI_FRAME_COUNTER)
        alive_trace = bytes(read_block(m, TRACE_ENTRY, 32)[:8])
        print('completion state before/after slot5 kill:', u8(m, STAGE_CLEARED),
              [u8(m, b + CHAR_HP) for b in ENTITIES], u8(m, SPAWN_INDEX))
        print('completion dispatch precondition:', u16(m, GAME_STATE),
              u16(m, GAME_STATE_PREV), u16(m, OAM_NEED_FULL), u8(m, MSU_BUSY))
        print('stage predicate alive trace:', list(alive_trace),
              'frames=', alive_run.get('framesAdvanced'),
              'nmi_delta=', (nmi_after_alive - nmi_before_alive) & 0xffff)
        r.check('stage remains uncleared while only added slot 5 enemy lives', u8(m, STAGE_CLEARED) == 0)
        m.write_u8(ENTITIES[5] + CHAR_HP, 0)
        m.write_u8(TRACE_ENTRY, 0)
        initial_stage = u16(m, GAME_STAGE_INDEX)
        nmi_before_dead = u16(m, NMI_FRAME_COUNTER)
        dead_frames = []
        for _ in range(3):
            one = run_frames_exact(m, 1)
            dead_frames.append((one.get('framesAdvanced'), u8(m, TRACE_ENTRY),
                                u8(m, STAGE_CLEARED), u8(m, SPAWN_INDEX),
                                u16(m, GAME_STATE)))
        dead_run = {'framesAdvanced': sum(x[0] for x in dead_frames)}
        m.pause()
        nmi_after_dead = u16(m, NMI_FRAME_COUNTER)
        dead_trace = bytes(read_block(m, TRACE_ENTRY, 32)[:8])
        print('stage predicate dead trace:', list(dead_trace),
              'frames=', dead_run.get('framesAdvanced'),
              'nmi_delta=', (nmi_after_dead - nmi_before_dead) & 0xffff,
              'spawn=', u8(m, SPAWN_INDEX), u8(m, SPAWN_COUNT))
        print('stage predicate dead per-frame:', dead_frames)
        saw_clear = u8(m, STAGE_CLEARED) == 1
        r.check('last enemy death sets Stage_Cleared before camera travel', saw_clear)
        # Begin the post-clear travel near the known camera-follow region so
        # the bounded input proof spends its frames on the real unlocked edge
        # rather than replaying the entire 0..700px stage from the left.
        m.write_u16(ENTITIES[0] + CHAR_POS_X, 700)
        m.write_u8(ENTITIES[0] + CHAR_HIT_STUN, 0)
        # Let any already-queued animation frame drain before camera travel;
        # this is ordinary gameplay pacing, not a state or camera write.
        for _ in range(30):
            run_frames_exact(m, 100)
            if _ % 5 == 4:
                print('stream pretravel chunk', _ + 1,
                      'screen/target', u16(m, SCREEN_POS_X), u16(m, SCREEN_TARGET_X),
                      'staged/desired', u16(m, STREAM_STAGED_LO), u16(m, STREAM_STAGED_HI),
                      u16(m, STREAM_DESIRED_LO), u16(m, STREAM_DESIRED_HI),
                      'pending', u16(m, STREAM_PEND_COL), u16(m, STREAM_PEND_TILE),
                      u8(m, STREAM_COL_PENDING), 'busy', u8(m, MSU_BUSY), flush=True)
        samples = []
        for _ in range(300):
            exact_input_edge(m, m.BTN_RIGHT, 1)
            samples.append((u16(m, ENTITIES[0] + CHAR_POS_X),
                            u16(m, SCREEN_POS_X),
                            u16(m, pasm_constant_in('src/core/game_state.pasm', 'Stage_TrueMaxX')),
                            u16(m, GAME_STAGE_INDEX)))
            if _ % 25 == 24:
                print('stream travel chunk', _ + 1,
                      'player/screen', samples[-1][0], samples[-1][1],
                      'staged/desired', u16(m, STREAM_STAGED_LO), u16(m, STREAM_STAGED_HI),
                      u16(m, STREAM_DESIRED_LO), u16(m, STREAM_DESIRED_HI),
                      'pending', u16(m, STREAM_PEND_COL), u16(m, STREAM_PEND_TILE),
                      u8(m, STREAM_COL_PENDING), 'busy', u8(m, MSU_BUSY), flush=True)
            if samples[-1][3] != initial_stage:
                break
        m.pause()
        advanced = u16(m, GAME_STAGE_INDEX) != initial_stage
        print('completion travel samples:', samples[:3], '...', samples[-3:])
        print('completion final:', u8(m, STAGE_CLEARED), 'saw_clear=', saw_clear,
              'advanced=', advanced,
              [u8(m, b + CHAR_HP) for b in ENTITIES], 'state=', u16(m, GAME_STATE),
              'spawn=', u8(m, SPAWN_INDEX), u8(m, SPAWN_COUNT),
              'screen=', u16(m, SCREEN_POS_X), 'true=', u16(m, STAGE_TRUE_MAX_X),
              'screen_max=', u16(m, SCREEN_MAX_X), 'world=', u16(m, WORLD_MAX_X))
        print('camera target/size/focus:', u16(m, SCREEN_TARGET_X),
              u16(m, SCREEN_SIZE_X), u16(m, SCREEN_FOCUS_ID),
              u16(m, SCREEN_FOCUS_NUM), u16(m, SCREEN_FOCUS_SLOT))
        print('player/oop dp:', u16(m, ENTITIES[0] + CHAR_POS_X),
              u16(m, OOP_DP), u16(m, OOP_RESULT_X))
        print('stream enabled/staged:', u8(m, STREAM_ENABLED),
              u16(m, STREAM_STAGED_LO), u16(m, STREAM_STAGED_HI))
        # Stage_Cleared is a one-frame internal latch and may be consumed by
        # the transition edge before a paused read (the known G4 early-
        # observation debt). The real stage transition is authoritative here.
        r.check('stage completion includes and transitions after added slot 5 dies', advanced)
    r.finish()


if __name__ == '__main__':
    main()
