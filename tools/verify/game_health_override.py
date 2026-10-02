#!/usr/bin/env python3
"""Health-override gate: real level `health` values reach spawned enemies.

Background (see this session's plan file / core/spawn.pasm's own header):
`tools/bg_converter/spawn_parse.py` already parsed BOR's per-spawn `health
<n>` line (verified against the real pak -- stage 1A/1B's own values range
25-100), but `build_spawn_table.py` discarded it entirely: every enemy
spawned at a hardcoded CHAR_HP_MAX regardless of what the level author
actually specified. Fixed by adding a `spawn_hp` byte to the spawn record
(scaled 0-100 -> 0..CHAR_HP_MAX), read by core/spawn.pasm's per-slot enemy
path (Spawn_Play__slotN_enemy) instead of the old `#CHAR_HP_MAX` immediate.
Props (entity_kind == 1) deliberately do NOT read this byte -- a prop's HP
is a fixed engine invariant (CHAR_HP_PER_HIT, exactly one hit kills).

This gate exercises the REAL Spawn_Play routine, not just a direct
CHAR_HP write -- it hand-crafts one 8-byte spawn record straight into
SpawnTable_Wram (same "direct force write to an otherwise-uncontested
cell is safe" reasoning phase11/phase12/game_g2/g8 already rely on) with
Spawn_Count=1/Spawn_Index=0/trigger_x=0 (already reached, since
Screen_PosX only ever increases from 0), forces the target AI slot's own
HP to 0 (free), lets a couple of frames run so Spawn_Play claims it, and
reads back CHAR_HP via direct WRAM -- ground truth, never engine
self-report (CLAUDE.md's standing rule).

Two cases:
  1. entity_kind = SPAWN_KIND_ENEMY, spawn_hp = 20 (a value deliberately
     far from both 0 and CHAR_HP_MAX=64) -- CHAR_HP must land at exactly 20,
     not the old hardcoded CHAR_HP_MAX.
  2. entity_kind = SPAWN_KIND_PROP, spawn_hp = 99 (deliberately absurd --
     larger than CHAR_HP_MAX, proving the byte is truly ignored rather than
     coincidentally clamped) -- CHAR_HP must land at exactly CHAR_HP_PER_HIT
     (4), proving the prop path never reads spawn_hp at all.

Note on naming: this is NOT plan_game.md's own "Phase G9" (bosses, §9) --
it's a level-format-keyword gap fix, a sibling to G8's prop/pickup work,
not a numbered phase in that plan. Named without a phase number for exactly
this reason (avoids colliding with the real G9 once bosses are built).

Usage: python tools/verify/game_health_override.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_HP_PER_HIT = pasm_constant('CHAR_HP_PER_HIT')
ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
CHAR_HP = 35

Spawn_Index = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
Spawn_Count = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
SpawnTable_Wram = pasm_constant_in('src/core/spawn.pasm', 'SpawnTable_Wram')
SPAWN_KIND_ENEMY = pasm_constant_in('src/core/spawn.pasm', 'SPAWN_KIND_ENEMY')
SPAWN_KIND_PROP = pasm_constant_in('src/core/spawn.pasm', 'SPAWN_KIND_PROP')

TARGET_SLOT = 1   # AI entity 1 -- the record lands here since it's the
                   # first slot Spawn_Play__find_slot checks
Entity1_Hp = ENTITY_BASES[TARGET_SLOT] + CHAR_HP


def entity_hp(m, base):
    return read_block(m, base + CHAR_HP, 32)[0]


def force_one_spawn(m, entity_kind, spawn_hp):
    """Craft a single 8-byte record at SpawnTable_Wram record 0, arm the
    queue for exactly one entry, and free entity 1's slot -- then run a
    few frames so Spawn_Play claims it."""
    # roster-growth slice: record grew 8->9 bytes (dedicated +8 roster_idx
    # byte); 0 here, this gate never uses RECORD_KIND_BOSS_IDENTIFIED.
    record = struct.pack('<HHBBBBB', 0, 100, 100, 0, entity_kind, spawn_hp, 0)
    m.write_memory('snesMemory', SpawnTable_Wram, record.hex())
    m.write_memory('snesMemory', Spawn_Count, '01')
    m.write_memory('snesMemory', Spawn_Index, '00')
    m.write_memory('snesMemory', Entity1_Hp, '00')
    m.run_frames(10)
    m.pause()


def main():
    r = Reporter('HEALTH-OVERRIDE', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()

        # --- case 1: enemy record with a mid-range spawn_hp ---
        force_one_spawn(m, SPAWN_KIND_ENEMY, 20)
        hp1 = entity_hp(m, ENTITY_BASES[TARGET_SLOT])
        print(f'enemy record (spawn_hp=20) -> entity {TARGET_SLOT} CHAR_HP = {hp1}')
        r.check('enemy spawn HP matches the record\'s own spawn_hp (20), not CHAR_HP_MAX',
                hp1 == 20)

        # --- case 2: prop record with a deliberately out-of-range spawn_hp ---
        force_one_spawn(m, SPAWN_KIND_PROP, 99)
        hp2 = entity_hp(m, ENTITY_BASES[TARGET_SLOT])
        print(f'prop record (spawn_hp=99) -> entity {TARGET_SLOT} CHAR_HP = {hp2}')
        r.check('prop spawn HP is CHAR_HP_PER_HIT regardless of spawn_hp (proves prop path ignores it)',
                hp2 == CHAR_HP_PER_HIT)

    r.finish()


if __name__ == '__main__':
    main()
