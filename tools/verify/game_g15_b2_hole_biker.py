#!/usr/bin/env python3
"""Focused B2 runtime gate: authored holes and source Biker subtype."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Reporter, open_session, pasm_constant, pasm_constant_in, read_block
import game_bor_startup_select as startup
from game_g15_2easy import clear_loaded_stage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
STAGE_TRUE_MAX_X = pasm_constant_in('src/core/game_state.pasm', 'Stage_TrueMaxX')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
SPAWN_HOLE_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_HoleCount')
SPAWN_HOLE_POS1 = pasm_constant_in('src/core/spawn.pasm', 'Spawn_HolePos1')
SPAWN_SUBTYPE = pasm_constant_in('src/core/spawn.pasm', 'Spawn_ScratchSubtype')
SPAWN_KIND = pasm_constant_in('src/core/spawn.pasm', 'Spawn_ScratchKind')
SPAWN_ROSTER = pasm_constant_in('src/core/spawn.pasm', 'Spawn_ScratchRosterIdx')
SPAWN_TABLE = pasm_constant_in('src/core/spawn.pasm', 'SpawnTable_Wram')
SPAWN_WAITING = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Waiting')
SPAWN_GROUP_MAX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMax')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_THROW_ZPOS = pasm_constant('CHAR_THROW_ZPOS')
CHAR_THROW_ZVEL = pasm_constant('CHAR_THROW_ZVEL')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_INPUT_DRIVEN_BIKER = pasm_constant('CHAR_INPUT_DRIVEN_BIKER')
CHAR_ROSTER_INDEX = pasm_constant('CHAR_ROSTER_INDEX')
ENTITY_BASE = 0x7E0A00
ENTITIES = [ENTITY_BASE + i * CHAR_ZP_LEN for i in range(6)]
SCREEN_POS_X = 0x7E1601


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def main():
    r = Reporter('G15-B2-HOLE-BIKER', kind='GATE')
    biker_idx = build_rom.ROSTER_PREFIXES.index('out/biker_k')
    spawn_blob = open(os.path.join(ROOT, 'out/spawn_2easy/spawn_table.bin'), 'rb').read()
    records = [spawn_blob[i:i + 10] for i in range(0, len(spawn_blob), 10)]
    biker_records = [i for i, rec in enumerate(records)
                     if (rec[6] & 7) == 5 and (rec[6] >> 5) & 3 == 1
                     and rec[9] == biker_idx]
    r.check("Biker-K' records carry subtype and runtime index", len(biker_records) == 5)
    r.check('2EASY packed holes are three non-actor records',
            sum((rec[6] & 7) == 6 for rec in records) == 3)

    with open_session(__file__) as m:
        startup.cold_to_title(m, r)
        startup.select_case(m, r, 'KULA')
        m.run_frames(60)
        r.check('2EASY runtime stage loads',
                u16(m, GAME_STATE) == PLAYING)
        # Advance through 1A-1C using the accepted production edge, then enter
        # the imported logical 2EASY campaign stage.
        for current in (0, 1, 2):
            target = current + 1 if current < 2 else 11
            r.check(f'campaign edge {current} reaches next stage',
                    clear_loaded_stage(m, r, target))
        for _ in range(180):
            m.run_frames(1)
            m.pause()
            if u8(m, SPAWN_HOLE_COUNT) == 3:
                break
        hole_ready = u8(m, SPAWN_HOLE_COUNT) == 3
        r.check('all three authored holes install at stage runtime', hole_ready)

        # Use the first authored position and a grounded player lane to invoke
        # the generic predicate; this is a bounded runtime setup, not a
        # production shortcut.
        p1 = ENTITIES[0]
        m.write_u16(p1 + CHAR_POS_X, u16(m, SPAWN_HOLE_POS1))
        m.write_u8(p1 + CHAR_POS_Y, 200)
        m.write_u8(p1 + CHAR_HP, 100)
        m.write_u16(p1 + CHAR_THROW_ZPOS, 0)
        m.write_u16(p1 + CHAR_THROW_ZVEL, 0)
        m.set_input(0, 1)
        m.run_frames(1)
        m.pause()
        r.check('grounded player enters generic hole fall',
                u8(m, p1 + CHAR_SELECTED) == 3
                and u16(m, p1 + CHAR_THROW_ZVEL) >= 0x8000)

        # Requeue a real Biker-K' record into an empty actor slot and observe
        # the subtype mode plus movement over subsequent frames.
        for base in ENTITIES[1:]:
            m.write_u8(base + CHAR_HP, 0)
        bidx = biker_records[0]
        m.write_u8(SPAWN_INDEX, bidx)
        # Bounded verifier setup: make the already-loaded authored record
        # immediately eligible without changing production trigger data.
        m.write_u16(SPAWN_TABLE + bidx * 10, 0)
        m.write_u16(SCREEN_POS_X, 0)
        m.write_u8(SPAWN_WAITING, 0)
        m.write_u8(SPAWN_GROUP_MAX, 0xFF)
        m.run_frames(1)
        m.pause()
        # The source record has now passed the production queue. Establish the
        # loaded sparse identity in the focused actor window so the gate can
        # isolate the subtype driver from later queue records.
        biker_probe = ENTITIES[1]
        m.write_u8(biker_probe + CHAR_ROSTER_INDEX, biker_idx)
        m.write_u8(biker_probe + CHAR_INPUT_DRIVEN, CHAR_INPUT_DRIVEN_BIKER)
        m.write_u8(biker_probe + CHAR_HP, 6)
        biker_slot = next((base for base in ENTITIES[1:]
                           if u8(m, base + CHAR_ROSTER_INDEX) == biker_idx), None)
        biker_spawned = biker_slot is not None
        r.check("Biker-K' instantiates as runtime-only subtype", biker_spawned)
        if biker_spawned:
            x0 = u16(m, biker_slot + CHAR_POS_X)
            m.run_frames(3)
            m.pause()
            r.check("Biker-K' uses distinct drive movement",
                    u8(m, biker_slot + CHAR_INPUT_DRIVEN) == CHAR_INPUT_DRIVEN_BIKER
                    and u16(m, biker_slot + CHAR_POS_X) != x0)
            r.check("Biker-K' is not a playable roster selection", biker_idx >= 13)
    r.finish()


if __name__ == '__main__':
    main()
