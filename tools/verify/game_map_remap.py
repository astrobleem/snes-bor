#!/usr/bin/env python3
"""`map` (per-spawn colormap/palette variant) gate -- plan_game.md 8a row 3.

Background (see `map_keyword_palette_data_done_runtime_hang` project memory
for the full story, including an earlier boot-hang scare that turned out to
be a contaminated bisection, not a real bug): OpenBOR's `remap <base.gif>
<alt.gif>` is a pure per-pixel-index recolor of the identical pose --
`tools/bor_converter/convert_character.py`'s `_derive_remap_palettes`
derives one real 16-color BGR555 palette per remap pair (mode-voted against
idle frame 0's own quantized index grid), and `pack_msu_roster.py` appends
0-3 of them (32 bytes each) after each character's rise frames. The spawn's
own `map` value (0-3) is packed into `record_kind`'s spare high bits (bits
3-4, mask/shift below) by `build_spawn_table.py`, same spare-bits technique
`group`'s min/max already used -- record size stays 8 bytes.

At spawn time, `core/spawn.pasm`'s slot1/2/3 dispatch decodes the map value
and calls `Anim_ApplyMapPalette` (main.pasm) via `jsl` -- a structural
mirror of `Anim_LoadCharacter`'s own palette-load section, seeking to either
the character's base palette (map==0) or its packed alt-palette table
(`CHAR_MAP_BASE + (map-1)*32`, map 1-3) and DMA'ing the 32 bytes into the
entity's own CGRAM OBJ palette slot.

This gate uses the same "direct force write to SpawnTable_Wram, then let
Spawn_Play claim it" technique `game_health_override.py`/
`game_g9_wait_group_boss.py` already established as safe. Every assertion
compares against REAL ground truth the engine did not produce -- the
converter's own `<char>_moveset.json` `remap_palettes` -- read back from
live CGRAM, never engine self-report (CLAUDE.md's standing rule; see also
`mesen_screenshot_stale_hud_layer` project memory on why screenshots don't
count as ground truth here).

Note on naming: like `game_health_override.py`, this is a level-format-
keyword gap fix (plan_game.md 8a), not a numbered "Phase G_" slice -- named
without a phase number for the same reason that file's own docstring gives.

Usage: python tools/verify/game_map_remap.py
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, pasm_constant_in,  # noqa: E402
                       read_block, repo_root_from, Reporter)

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_INPUT_DRIVEN_AI = pasm_constant('CHAR_INPUT_DRIVEN_AI')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_PALETTE_SLOT = pasm_constant('CHAR_PALETTE_SLOT')
ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]

Spawn_Index = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
Spawn_Count = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
SpawnTable_Wram = pasm_constant_in('src/core/spawn.pasm', 'SpawnTable_Wram')
Spawn_GroupMin = pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMin')
Spawn_GroupMax = pasm_constant_in('src/core/spawn.pasm', 'Spawn_GroupMax')
Spawn_Waiting = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Waiting')
Spawn_ScratchMap = pasm_constant_in('src/core/spawn.pasm', 'Spawn_ScratchMap')
SPAWN_KIND_ENEMY = pasm_constant_in('src/core/spawn.pasm', 'SPAWN_KIND_ENEMY')
SPAWN_KIND_WAIT = pasm_constant_in('src/core/spawn.pasm', 'SPAWN_KIND_WAIT')
SPAWN_KIND_BOSS = pasm_constant_in('src/core/spawn.pasm', 'SPAWN_KIND_BOSS')
SPAWN_MAP_SHIFT = pasm_constant_in('src/core/spawn.pasm', 'SPAWN_MAP_SHIFT')

Entity1_IsBoss = pasm_constant_in('src/core/spawn.pasm', 'Entity1_IsBoss')

# core/screen.pasm's `.enum $7E1600` struct field, hardcoded the same way
# phase8.py/game_g9_wait_group_boss.py already do (pasm_constant can't
# parse .enum fields).
Screen_PosX = 0x7E1601

# entity index (1-3) -> (WRAM base, roster character this slot loads at
# boot). Matches phase12_roster.py's own ENTITY_ROSTER_SLOTS -- must be
# kept in sync with main.pasm's Core_Oop_Create init params the same way
# that file's own comment explains.
ENTITY_ROSTER = {
    1: (ENTITY_BASES[1], 'jhun'),
    2: (ENTITY_BASES[2], 'joe'),
    3: (ENTITY_BASES[3], 'yashiro'),
}

CGRAM_OBJ_BASE = 0x100  # byte $100 = OBJ palette 0 base, same as phase5/12


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def cgram_palette(m, palette_slot):
    return read_block(m, CGRAM_OBJ_BASE + palette_slot * 32, 32, mem_type='snesCgRam')


def moveset_remap_bytes(char_name):
    path = os.path.join(repo_root_from(None), 'out', f'{char_name}_moveset.json')
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [b''.join(struct.pack('<H', v) for v in pal) for pal in data['remap_palettes']]


def record(trigger_x, spawn_x, kind, map_value, spawn_hp=64):
    record_kind = (kind & 0x07) | ((map_value & 0x03) << SPAWN_MAP_SHIFT)
    return struct.pack('<HHBBBB', trigger_x, spawn_x, 100, 0, record_kind, spawn_hp)


def load_one_record(m, rec):
    m.write_memory('snesMemory', SpawnTable_Wram, rec.hex())
    m.write_memory('snesMemory', Spawn_Count, '01')
    m.write_memory('snesMemory', Spawn_Index, '00')
    m.write_memory('snesMemory', Screen_PosX, '0000')
    m.write_memory('snesMemory', Spawn_GroupMin, '64')  # 100, Spawn_Init's own default
    m.write_memory('snesMemory', Spawn_GroupMax, '64')
    m.write_memory('snesMemory', Spawn_Waiting, '00')


def force_free(m, entity_base):
    m.write_memory('snesMemory', entity_base + CHAR_HP, '00')
    m.write_memory('snesMemory', entity_base + CHAR_INPUT_DRIVEN, f'{CHAR_INPUT_DRIVEN_AI:02x}')


def main():
    r = Reporter('MAP-REMAP', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        m.pause()

        # --- capture each roster character's own BOOT-time base palette
        # (loaded by Anim_LoadCharacter at CharacterEntity_Init, before any
        # Spawn_Play override) -- this is the ground truth a map==0 spawn
        # must reproduce exactly, since Anim_ApplyMapPalette's map==0 path
        # seeks to the same CHAR_PALETTE_BASE address the boot load itself
        # used. ---
        boot_palettes = {}
        for eid, (base, name) in ENTITY_ROSTER.items():
            pal_slot = u8(m, base + CHAR_PALETTE_SLOT)
            boot_palettes[eid] = cgram_palette(m, pal_slot)
        print('captured boot-time base palettes for entities '
              f'{sorted(boot_palettes)}')

        # ================= per-character remap correctness =================
        # JHUN (entity1, 2 remaps): map=1 and map=2 must each match the
        # converter's own derived remap_palettes[0]/[1] byte-for-byte.
        jhun_base, jhun_name = ENTITY_ROSTER[1]
        jhun_remaps = moveset_remap_bytes(jhun_name)
        r.check(f'{jhun_name} moveset has 2 real remap palettes (matches pak data)',
                len(jhun_remaps) == 2)
        for map_value in (1, 2):
            force_free(m, jhun_base)
            load_one_record(m, record(0, 100, SPAWN_KIND_ENEMY, map_value))
            m.run_frames(6)
            m.pause()
            pal_slot = u8(m, jhun_base + CHAR_PALETTE_SLOT)
            cgram = cgram_palette(m, pal_slot)
            expected = jhun_remaps[map_value - 1]
            r.check(f'{jhun_name} map={map_value}: live CGRAM matches converter '
                     f'remap_palettes[{map_value - 1}] byte-for-byte',
                    cgram == expected)

        # JOE (entity2, 3 remaps): exercises the highest index (map=3 ->
        # alt-table offset (3-1)*32=64 bytes), a real multiplication/offset
        # boundary the JHUN-only case above can't reach.
        joe_base, joe_name = ENTITY_ROSTER[2]
        joe_remaps = moveset_remap_bytes(joe_name)
        r.check(f'{joe_name} moveset has 3 real remap palettes (matches pak data)',
                len(joe_remaps) == 3)
        force_free(m, joe_base)
        load_one_record(m, record(0, 100, SPAWN_KIND_ENEMY, 3))
        m.run_frames(6)
        m.pause()
        pal_slot = u8(m, joe_base + CHAR_PALETTE_SLOT)
        cgram = cgram_palette(m, pal_slot)
        r.check(f'{joe_name} map=3 (highest index): live CGRAM matches converter '
                 'remap_palettes[2] byte-for-byte', cgram == joe_remaps[2])

        # ================= map==0 reproduces the boot base palette =================
        # after having just loaded an alt palette above, re-spawn the same
        # slot with map==0 -- must restore the EXACT boot-time base palette,
        # proving CHAR_PALETTE_BASE (not some stale alt-table leftover) is
        # what map==0 actually seeks to.
        force_free(m, jhun_base)
        load_one_record(m, record(0, 100, SPAWN_KIND_ENEMY, 0))
        m.run_frames(6)
        m.pause()
        pal_slot = u8(m, jhun_base + CHAR_PALETTE_SLOT)
        cgram = cgram_palette(m, pal_slot)
        r.check('map=0 after a prior alt-palette load restores the exact '
                'boot-time base palette (not a stale alt-table leftover)',
                cgram == boot_palettes[1])

        # ================= decode: map bits coexist with SPAWN_KIND_BOSS =================
        # record_kind = SPAWN_KIND_BOSS | (map<<3) must decode BOTH fields
        # correctly -- proves the mask/shift didn't regress the wait/group/
        # boss slice's own kind dispatch.
        force_free(m, jhun_base)
        load_one_record(m, record(0, 100, SPAWN_KIND_BOSS, 2))
        m.run_frames(6)
        m.pause()
        is_boss = u8(m, Entity1_IsBoss)
        pal_slot = u8(m, jhun_base + CHAR_PALETTE_SLOT)
        cgram = cgram_palette(m, pal_slot)
        r.check('SPAWN_KIND_BOSS|map=2 record still sets EntityN_IsBoss '
                '(kind decode unaffected by the map bits)', is_boss == 1)
        r.check('SPAWN_KIND_BOSS|map=2 record also applies the correct remap '
                'palette (map decode unaffected by the kind bits)',
                cgram == jhun_remaps[1])
        r.check('Spawn_ScratchMap itself decoded to 2 (direct decode check, '
                'not just the downstream CGRAM effect)',
                u8(m, Spawn_ScratchMap) == 2)

        # ================= decode: wait dispatch unaffected =================
        # SPAWN_KIND_WAIT with zero map bits must still dispatch as a wait
        # marker (existing game_g9_wait_group_boss.py behavior) -- smoke
        # test that SPAWN_KIND_MASK didn't change kind decode for non-spawn
        # records.
        force_free(m, jhun_base)
        wait_rec = struct.pack('<HHBBBB', 0, 0, 0, 0, SPAWN_KIND_WAIT, 0)
        load_one_record(m, wait_rec)
        m.run_frames(6)
        m.pause()
        r.check('SPAWN_KIND_WAIT (map bits zero) still dispatches as a wait '
                'marker, not a spawn', u8(m, Spawn_Waiting) == 1)

    r.finish()


if __name__ == '__main__':
    main()
