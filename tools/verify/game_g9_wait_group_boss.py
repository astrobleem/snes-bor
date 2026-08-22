#!/usr/bin/env python3
"""Gate for the wait/group/boss level-spawn slice (follow-up to plan_game.md
G8's prop/pickup work -- see core/spawn.pasm's own header for the real
BOR.C-sourced algorithm this implements).

Same "direct force write to SpawnTable_Wram, then let Spawn_Play claim it"
technique game_health_override.py already established as safe (that gate's
own docstring explains why). Every assertion reads ground-truth WRAM, never
engine self-report screenshots (CLAUDE.md's mesen_screenshot_stale_hud_layer
lesson).

`wait` and `group` are exercised against real, buildable BOR data (both
shipped stages use both -- see build_spawn_table.py's own header for the
measured counts). `boss` is exercised only via a hand-authored synthetic
record, NOT a real shipped level -- BOR's own two stages have zero `boss`
lines; only TMNT's pak (not converted/buildable in this repo yet) uses it
for real. This gate says so explicitly rather than implying real-level
coverage it doesn't have.

Usage: python tools/verify/game_g9_wait_group_boss.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_INPUT_DRIVEN = 15
CHAR_HP = 35
ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
CHAR_INPUT_DRIVEN_AI = pasm_constant('CHAR_INPUT_DRIVEN_AI')
CHAR_INPUT_DRIVEN_PROP = pasm_constant('CHAR_INPUT_DRIVEN_PROP')

Spawn_Index = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
Spawn_Count = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
SpawnTable_Wram = pasm_constant_in('src/core/spawn.pasm', 'SpawnTable_Wram')
SPAWN_KIND_ENEMY = pasm_constant_in('src/core/spawn.pasm', 'SPAWN_KIND_ENEMY')
SPAWN_KIND_WAIT = pasm_constant_in('src/core/spawn.pasm', 'SPAWN_KIND_WAIT')
SPAWN_KIND_GROUP = pasm_constant_in('src/core/spawn.pasm', 'SPAWN_KIND_GROUP')
SPAWN_KIND_BOSS = pasm_constant_in('src/core/spawn.pasm', 'SPAWN_KIND_BOSS')
Spawn_GroupMin = pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMin')
Spawn_GroupMax = pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMax')
Spawn_Waiting = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Waiting')
Spawn_PreClearHoldX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_PreClearHoldX')
Entity1_IsBoss = pasm_constant_in('src/core/spawn.pasm', 'Entity1_IsBoss')
Entity2_IsBoss = pasm_constant_in('src/core/spawn.pasm', 'Entity2_IsBoss')

# core/screen.pasm's `.enum $7E1600` struct fields, not plain NAME=value
# constants -- pasm_constant() can't parse those, hardcoded here the same
# way phase8.py already does (see that file's own comment on Screen_PosX).
Screen_PosX = 0x7E1601
Screen_MaxX = 0x7E160E


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def enemy_record(trigger_x, spawn_x, kind, spawn_hp=64):
    return struct.pack('<HHBBBB', trigger_x, spawn_x, 100, 0, kind, spawn_hp)


def wait_record(trigger_x):
    return struct.pack('<HHBBBB', trigger_x, 0, 0, 0, SPAWN_KIND_WAIT, 0)


def group_record(trigger_x, group_min, group_max):
    return struct.pack('<HBBBBBB', trigger_x, group_min, group_max, 0, 0, SPAWN_KIND_GROUP, 0)


def load_queue(m, records, screen_pos_x=0):
    blob = b''.join(records)
    m.write_memory('snesMemory', SpawnTable_Wram, blob.hex())
    m.write_memory('snesMemory', Spawn_Count, f'{len(records):02x}')
    m.write_memory('snesMemory', Spawn_Index, '00')
    m.write_memory('snesMemory', Screen_PosX, struct.pack('<H', screen_pos_x).hex())
    m.write_memory('snesMemory', Spawn_GroupMin, '64')  # 100 -- Spawn_Init's own default
    m.write_memory('snesMemory', Spawn_GroupMax, '64')
    m.write_memory('snesMemory', Spawn_Waiting, '00')


def main():
    r = Reporter('G9-WAIT-GROUP-BOSS', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()

        # ================= GROUP =================
        # queue: [0] group 1-1  [1] enemy->slot1  [2] enemy->slot2
        # all triggers at world-x 0 (already reached). Both AI slots start
        # free (HP forced to 0).
        m.write_memory('snesMemory', ENTITY_BASES[1] + CHAR_HP, '00')
        m.write_memory('snesMemory', ENTITY_BASES[2] + CHAR_HP, '00')
        m.write_memory('snesMemory', ENTITY_BASES[1] + CHAR_INPUT_DRIVEN,
                        f'{CHAR_INPUT_DRIVEN_AI:02x}')
        m.write_memory('snesMemory', ENTITY_BASES[2] + CHAR_INPUT_DRIVEN,
                        f'{CHAR_INPUT_DRIVEN_AI:02x}')
        load_queue(m, [
            group_record(0, 1, 1),
            enemy_record(0, 100, SPAWN_KIND_ENEMY),
            enemy_record(0, 150, SPAWN_KIND_ENEMY),
        ])
        m.run_frames(6)
        m.pause()
        idx_after_group = u8(m, Spawn_Index)
        gmin = u8(m, Spawn_GroupMin)
        gmax = u8(m, Spawn_GroupMax)
        print(f'after group+1 spawn settle: Spawn_Index={idx_after_group} '
              f'GroupMin={gmin} GroupMax={gmax}')
        r.check('group record updates Spawn_GroupMin/Max to 1/1', gmin == 1 and gmax == 1)
        r.check('queue advanced past the group marker and the first spawn '
                '(index==2, second enemy still gated)', idx_after_group == 2)
        hp1 = u8(m, ENTITY_BASES[1] + CHAR_HP)
        hp2 = u8(m, ENTITY_BASES[2] + CHAR_HP)
        print(f'entity1 hp={hp1} entity2 hp={hp2}')
        r.check('first enemy actually spawned (entity1 HP nonzero)', hp1 != 0)
        r.check('second enemy did NOT spawn yet -- group cap (max=1) blocked it '
                'while entity1 is alive', hp2 == 0)

        # stays blocked over more frames while entity1 lives
        m.run_frames(10)
        m.pause()
        idx_still = u8(m, Spawn_Index)
        r.check('still gated several frames later (index unchanged)', idx_still == 2)

        # kill entity1 -- group gate should release, second enemy spawns.
        # find_slot always prefers the lowest-numbered FREE slot, so the
        # newly-freed slot1 (not slot2) is where it lands -- that's real,
        # pre-existing Spawn_Play__find_slot behavior, not something this
        # slice changes, so check whichever slot actually got it.
        m.write_memory('snesMemory', ENTITY_BASES[1] + CHAR_HP, '00')
        m.run_frames(6)
        m.pause()
        idx_final = u8(m, Spawn_Index)
        hp1_final = u8(m, ENTITY_BASES[1] + CHAR_HP)
        hp2_final = u8(m, ENTITY_BASES[2] + CHAR_HP)
        print(f'after killing entity1: Spawn_Index={idx_final} '
              f'entity1 hp={hp1_final} entity2 hp={hp2_final}')
        r.check('queue drains to exhaustion (index==3) once the group count '
                'drops back under groupmin', idx_final == 3)
        r.check('second enemy spawns once the pool has room (into whichever '
                'slot find_slot picks -- slot1 was just freed)',
                hp1_final != 0 or hp2_final != 0)

        # ================= WAIT =================
        # queue: [0] wait (trigger 0). One AI slot forced alive so the wait
        # can't release immediately.
        m.write_memory('snesMemory', ENTITY_BASES[1] + CHAR_HP, '40')
        m.write_memory('snesMemory', ENTITY_BASES[1] + CHAR_INPUT_DRIVEN,
                        f'{CHAR_INPUT_DRIVEN_AI:02x}')
        m.write_memory('snesMemory', ENTITY_BASES[2] + CHAR_HP, '00')
        pre_clear_hold = u16(m, Spawn_PreClearHoldX)
        load_queue(m, [wait_record(0)], screen_pos_x=300)
        m.run_frames(6)
        m.pause()
        waiting = u8(m, Spawn_Waiting)
        max_x = u16(m, Screen_MaxX)
        pos_x = u16(m, Screen_PosX)
        print(f'after wait triggers: Spawn_Waiting={waiting} Screen_MaxX={max_x} '
              f'Screen_PosX={pos_x} (pre-clear hold was {pre_clear_hold})')
        r.check('wait record sets Spawn_Waiting while an enemy is still alive', waiting == 1)
        r.check('wait installs a real, narrower clamp than the stage-load '
                'hold (proves it froze scroll at ~the trigger point, not '
                'leaving the old wide ceiling in place)', max_x < pre_clear_hold)

        # camera must not exceed the new clamp over several more frames
        # (this IS the scroll-block -- Screen_PosX/BG1 scroll can never
        # exceed Screen_MaxX, same hard-ceiling property phase8.py's own
        # MAX_SCROLL_X clamp check already verifies for the stage-load hold)
        m.run_frames(10)
        m.pause()
        max_x2 = u16(m, Screen_MaxX)
        pos_x2 = u16(m, Screen_PosX)
        print(f'held several more frames: Screen_MaxX={max_x2} Screen_PosX={pos_x2}')
        r.check('stays blocked (Spawn_Waiting still set) while the enemy lives',
                u8(m, Spawn_Waiting) == 1)
        r.check('camera never exceeds the wait clamp (real scroll block, not '
                'just a flag)', pos_x2 <= max_x2)

        # kill the enemy -- wait should release next frame, Screen_MaxX restored
        m.write_memory('snesMemory', ENTITY_BASES[1] + CHAR_HP, '00')
        m.run_frames(6)
        m.pause()
        waiting_after = u8(m, Spawn_Waiting)
        max_x_after = u16(m, Screen_MaxX)
        print(f'after killing the last enemy: Spawn_Waiting={waiting_after} '
              f'Screen_MaxX={max_x_after}')
        r.check('wait releases once zero real enemies remain', waiting_after == 0)
        r.check('Screen_MaxX restored to the cached pre-clear hold value '
                '(the same value Stage_ApplyWinClamp computed, not a new one)',
                max_x_after == pre_clear_hold)

        # ================= BOSS (synthetic -- no buildable pak uses this yet) =================
        m.write_memory('snesMemory', ENTITY_BASES[1] + CHAR_HP, '00')
        load_queue(m, [enemy_record(0, 100, SPAWN_KIND_BOSS)])
        m.run_frames(6)
        m.pause()
        is_boss = u8(m, Entity1_IsBoss)
        boss_hp = u8(m, ENTITY_BASES[1] + CHAR_HP)
        print(f'boss record (synthetic) -> Entity1_IsBoss={is_boss} hp={boss_hp}')
        r.check('boss record spawns as a live AI entity (HP nonzero)', boss_hp != 0)
        r.check('boss record sets EntityN_IsBoss', is_boss == 1)

        # reuse the same slot with a plain enemy record -- boss flag must clear
        m.write_memory('snesMemory', ENTITY_BASES[1] + CHAR_HP, '00')
        load_queue(m, [enemy_record(0, 100, SPAWN_KIND_ENEMY)])
        m.run_frames(6)
        m.pause()
        is_boss_after = u8(m, Entity1_IsBoss)
        print(f'plain enemy reusing the same slot -> Entity1_IsBoss={is_boss_after}')
        r.check('a reused slot does not inherit a stale boss flag from its '
                'previous occupant', is_boss_after == 0)

    r.finish()
    print()
    print('NOTE: the boss checks above use a hand-authored synthetic record, '
          'not a real shipped level -- BOR\'s own two stages have zero `boss` '
          'lines (verified against the real pak). TMNT has 6 real boss spawns '
          'but is not converted/buildable in this repo yet. Real end-to-end '
          'boss coverage needs a TMNT conversion pass, not this gate.')


if __name__ == '__main__':
    main()
