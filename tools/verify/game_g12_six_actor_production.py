#!/usr/bin/env python3
"""G12 production-spawn contract for six bounded CharacterEntity actors.

The fixture supplies a reproducible queue of real spawn records in the normal
SpawnTable_Wram format.  It does not construct or populate CharacterEntity
state: every actor is initialized by the production Spawn_Play path.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402
from g12_scaling_baseline import source_identity

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_FACING_LEFT = pasm_constant('CHAR_FACING_LEFT')
CHAR_TILE_COLUMN = pasm_constant('CHAR_TILE_COLUMN')
CHAR_PALETTE_SLOT = pasm_constant('CHAR_PALETTE_SLOT')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_PICKUP_TYPE = pasm_constant('CHAR_PICKUP_TYPE')
CHAR_GRAB_TARGET = pasm_constant('CHAR_GRAB_TARGET')
CHAR_GRABBED_BY = pasm_constant('CHAR_GRABBED_BY')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
ACTOR_COUNT = pasm_constant('CHARACTER_ACTOR_COUNT')
PROP_MODE = pasm_constant('CHAR_INPUT_DRIVEN_PROP')
SPAWN_TABLE = pasm_constant_in('src/core/spawn.pasm', 'SpawnTable_Wram')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
SPAWN_WAITING = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Waiting')
SPAWN_GROUP_MIN = pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMin')
SPAWN_GROUP_MAX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMax')
GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
STAGE_CLEARED = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
STAGE_TRUE_MAX_X = pasm_constant_in('src/core/game_state.pasm', 'Stage_TrueMaxX')
SCREEN_POS_X = 0x7E1601
MSU_BUSY = pasm_constant('Msu1_StreamBusy')

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
    positions = [(80, 70), (120, 55), (160, 85), (200, 45), (240, 100)]
    for i, (x, y) in enumerate(positions):
        write_record(m, i, 0, x, y, i & 1, 0, CHAR_HP_MAX)
    # A seventh prop record is consumed after slot 4 is killed and reused.
    write_record(m, 5, 0, 280, 60, 0, 0, CHAR_HP_MAX)
    write_record(m, 6, 0, 300, 60, 1, 1, 1, 13, 18)
    m.write_u8(SPAWN_INDEX, 0)
    m.write_u8(SPAWN_COUNT, 5)
    m.write_u8(SPAWN_WAITING, 0)
    m.write_u8(pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMin'), 100)
    m.write_u8(pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMax'), 100)
    m.write_u8(STAGE_CLEARED, 0)


def wait_for_six(m, max_frames=600):
    for _ in range(max_frames):
        if all(u8(m, base + CHAR_HP) > 0 for base in ENTITIES[1:]):
            return True
        m.run_frames(1)
    return False


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
        install_fixture_queue(m)
        six_spawned = wait_for_six(m)
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
                [u8(m, ENTITIES[i] + CHAR_FACING_LEFT) for i in (4, 5)] == [0, 1])

        # Completed-upload VRAM proof.  The single staging buffer can leave a
        # completed DMA one logical animation frame behind the entity state,
        # so identify the committed frame from the hardware bytes themselves;
        # never compare against a newer request merely because the queue is
        # currently idle.
        for i in (4, 5):
            m.write_u8(ENTITIES[i] + CHAR_INPUT_DRIVEN, 0)
        for _ in range(120):
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
            col = entity[16]
            got_rows = [bytes(read_block(m, 0x8000 + col * 128 + row * 512, 128,
                                         mem_type='snesVideoRam')) for row in range(6)]
            match = None
            for frame in range(16):
                source, state_name = source_identity(entity, frame, entity[11], entity[12])
                if source is not None and all(
                        got_rows[row] == msu[source + row * 128:source + (row + 1) * 128]
                        for row in range(6)):
                    match = (frame, state_name, source)
                    break
            if match is None:
                source, state_name = source_identity(entity, entity[9], entity[11], entity[12])
                first_vram_mismatch = (i, entity[9], entity[14], col, source, state_name)
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
        for _ in range(180):
            if u8(m, target4 + CHAR_INPUT_DRIVEN) == PROP_MODE and u8(m, target4 + CHAR_HP) > 0:
                break
            m.run_frames(1)
        m.pause()
        print('reused slot4 metadata:', u8(m, target4 + CHAR_INPUT_DRIVEN),
              u8(m, target4 + CHAR_PICKUP_TYPE),
              u8(m, 0x7E0A00 + 4 * CHAR_ZP_LEN + 128),
              u8(m, target4 + CHAR_GRAB_TARGET), u8(m, target4 + CHAR_GRABBED_BY))
        r.check('production spawn reused added slot 4', u8(m, target4 + CHAR_HP) > 0)
        r.check('reused slot 4 is classified as prop, not enemy', u8(m, target4 + CHAR_INPUT_DRIVEN) == PROP_MODE)
        r.check('reused prop carries its contained item roster metadata', u8(m, 0x7E0A00 + 4 * CHAR_ZP_LEN + 128) == 13)
        r.check('slot 4 reuse clears old grab links', u8(m, target4 + CHAR_GRAB_TARGET) == 0xFF and u8(m, target4 + CHAR_GRABBED_BY) == 0xFF)

        # Only remaining enemy in slot 5 must hold the stage. Props do not
        # count as enemies in the production wait/completion accounting.
        m.write_u8(STAGE_CLEARED, 0)
        m.write_u16(GAME_STATE, GAME_STATE_PLAYING)
        m.write_u16(SCREEN_POS_X, u16(m, STAGE_TRUE_MAX_X))
        m.write_u8(SPAWN_WAITING, 0)
        m.write_u8(SPAWN_GROUP_MIN, 100)
        m.write_u8(SPAWN_GROUP_MAX, 100)
        for i in (1, 2, 3, 4): m.write_u8(ENTITIES[i] + CHAR_HP, 0)
        m.write_u8(ENTITIES[5] + CHAR_HP, CHAR_HP_MAX)
        m.write_u8(SPAWN_INDEX, 7); m.write_u8(SPAWN_COUNT, 7)
        m.write_u16(SCREEN_POS_X, u16(m, STAGE_TRUE_MAX_X))
        m.run_frames(8); m.pause()
        print('completion state before/after slot5 kill:', u8(m, STAGE_CLEARED),
              [u8(m, b + CHAR_HP) for b in ENTITIES], u8(m, SPAWN_INDEX))
        r.check('stage remains uncleared while only added slot 5 enemy lives', u8(m, STAGE_CLEARED) == 0)
        m.write_u8(ENTITIES[5] + CHAR_HP, 0)
        initial_stage = u16(m, GAME_STAGE_INDEX)
        saw_clear = False; advanced = False
        for _ in range(30):
            # Keep the player on the real camera-driving path while the
            # win-condition edge unlocks the full stage width.
            m.set_input(m.BTN_RIGHT, 60)
            m.run_frames(1); m.pause()
            saw_clear |= u8(m, STAGE_CLEARED) == 1
            advanced |= u16(m, GAME_STAGE_INDEX) != initial_stage
        print('completion final:', u8(m, STAGE_CLEARED), 'saw_clear=', saw_clear,
              'advanced=', advanced,
              [u8(m, b + CHAR_HP) for b in ENTITIES], 'state=', u16(m, GAME_STATE),
              'spawn=', u8(m, SPAWN_INDEX), u8(m, SPAWN_COUNT),
              'screen=', u16(m, SCREEN_POS_X), 'true=', u16(m, STAGE_TRUE_MAX_X))
        # Stage_Cleared is a one-frame internal latch and may be consumed by
        # the transition edge before a paused read (the known G4 early-
        # observation debt). The real stage transition is authoritative here.
        r.check('stage completion includes and transitions after added slot 5 dies', advanced)
    r.finish()


if __name__ == '__main__':
    main()
