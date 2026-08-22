#!/usr/bin/env python3
"""plan_game.md Phase G8 (first slice) gate: prop/pickup entity kind.

Background (see this session's plan file / core/spawn.pasm's own "CORRECTION"
comment): plan_game.md and core/spawn.pasm's header both used to claim BOR's
`1up` pickup and `trash`/`table`/`chair` props were "silently discarded" by
the spawn-table converter. Verified false against the real, previously-
shipped `out/spawn_stage1a/spawn_table.bin` (byte-identical to a fresh
regeneration from the pak): those spawns were landing as ordinary full-HP,
AI-seeking, attacking enemies. This phase adds a real third entity kind
(CHAR_INPUT_DRIVEN_PROP, mode 3) instead, and build_spawn_table.py now
classifies `1up`/`trash`/`table`/`chair` as props when packing a level's
spawn table (both out/spawn_stage1a and out/spawn_stage1b were regenerated
as part of this change -- this gate itself only exercises the engine-side
mode, not the Python classifier, which has its own direct unit-level check
in build_spawn_table.py's own module).

A prop must be behaviorally distinct from an AI enemy in the ways that
matter, all checked against real hardware state, never engine-self-report
(CLAUDE.md's standing rule):
  1. Never seeks the player -- CHAR_POS_X must NOT drift toward
     PlayerEntity_PosX over many real frames (mode 2's AI-seek would move
     it; mode 3 must not, since Anim_Play__check_attack_trigger's dispatch
     chain treats anything that isn't mode 1/2 as "always idle" already).
  2. Never attacks -- CHAR_SELECTED must never read 2 (attack) across the
     same run (Character_HitApply__attacking's dispatch chain likewise
     treats anything that isn't mode 1/2 as "no attack dispatch").
  3. DOES get the same soft-kill/hide-at-HP==0 treatment an AI enemy has --
     this is the one place plan_game.md G8 had to actually widen existing
     code (Anim_Play's and Character_PlayFrame's dead-checks, both changed
     from `CHAR_INPUT_DRIVEN==2` to `>=2`). Forcing CHAR_HP to 0 directly
     (same safe-to-write reasoning phase11_damage.py already uses -- nothing
     else races CHAR_HP for an entity that's stopped acting) must hide its
     hardware OAM sprite (Y=$F0) exactly like a dead AI enemy's.

Entity 2 (JOE) is repurposed as the prop for this gate -- forced directly to
CHAR_INPUT_DRIVEN_PROP/a small HP via WRAM write, same "direct write is safe,
nothing else races these cells at boot" reasoning phase11/phase12/game_g2
already rely on. Entity 3 stays a normal AI control (forced alive) to prove
the widened dead-check gate didn't accidentally start hiding/freezing every
entity regardless of mode.

Usage: python tools/verify/game_g8_props.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_HP_PER_HIT = pasm_constant('CHAR_HP_PER_HIT')
CHAR_INPUT_DRIVEN_PROP = pasm_constant_in('src/main.pasm', 'CHAR_INPUT_DRIVEN_PROP')
ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]

CHAR_POS_X = 4
CHAR_SELECTED = 11
CHAR_INPUT_DRIVEN = 15
CHAR_HP = 35

PROP_ENTITY = 2       # JOE's slot, repurposed as the prop under test
CONTROL_ENTITY = 3    # a normal AI, forced alive, proves the widened gate
                       # didn't start affecting every mode

Entity_InputDriven = {i: ENTITY_BASES[i] + CHAR_INPUT_DRIVEN for i in range(4)}
Entity_Hp = {i: ENTITY_BASES[i] + CHAR_HP for i in range(4)}
PlayerEntity_PosX = ENTITY_BASES[0] + CHAR_POS_X

DEAD_OAM_Y = 0xF0


def entity_posx(m, base):
    block = read_block(m, base, 32)
    return block[CHAR_POS_X] | (block[CHAR_POS_X + 1] << 8)


def entity_selected(m, base):
    block = read_block(m, base, 32)
    return block[CHAR_SELECTED]


def oam_slot(m, slot):
    block = read_block(m, 0, 32, mem_type='snesSpriteRam')
    off = slot * 4
    return block[off], block[off + 1]  # X, Y


def main():
    r = Reporter('G8', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()

        # --- force entity 2 into prop mode, positioned away from the
        # player so it would visibly drift if (and only if) it were still
        # seeking -- and force entity 3 alive as a normal-AI control. ---
        m.write_memory('snesMemory', Entity_InputDriven[PROP_ENTITY], f'{CHAR_INPUT_DRIVEN_PROP:02X}')
        m.write_memory('snesMemory', Entity_Hp[PROP_ENTITY], f'{CHAR_HP_PER_HIT:02X}')
        m.write_memory('snesMemory', Entity_Hp[CONTROL_ENTITY], f'{CHAR_HP_MAX:02X}')
        m.run_frames(5)
        m.pause()

        prop_posx_before = entity_posx(m, ENTITY_BASES[PROP_ENTITY])
        player_posx = entity_posx(m, ENTITY_BASES[0])
        print(f'prop entity {PROP_ENTITY} PosX before: {prop_posx_before}, player PosX: {player_posx}')

        selected_samples = []
        posx_samples = []
        for _ in range(8):
            m.run_frames(37)   # prime stride, same anti-aliasing reasoning
                                 # as phase11_damage/phase15 (see their own
                                 # comments) -- not needed for a value that
                                 # should never change, but cheap insurance
            m.pause()
            selected_samples.append(entity_selected(m, ENTITY_BASES[PROP_ENTITY]))
            posx_samples.append(entity_posx(m, ENTITY_BASES[PROP_ENTITY]))

        print(f'prop entity {PROP_ENTITY} CHAR_SELECTED samples: {selected_samples}')
        r.check('prop entity never attacks (CHAR_SELECTED never reaches 2)',
                all(s != 2 for s in selected_samples))

        print(f'prop entity {PROP_ENTITY} PosX samples: {posx_samples}')
        r.check('prop entity never seeks the player (PosX never moves)',
                all(p == prop_posx_before for p in posx_samples))

        # --- dead-check widening: force HP to 0 (safe direct write, same
        # reasoning as phase11_damage.py -- nothing else races CHAR_HP for
        # an entity that's stopped acting) and confirm the sprite hides. ---
        m.write_memory('snesMemory', Entity_Hp[PROP_ENTITY], '00')
        m.run_frames(10)
        m.pause()

        hp_after = read_block(m, Entity_Hp[PROP_ENTITY], 32)[0]
        r.check('prop entity CHAR_HP stays 0', hp_after == 0)

        ox, oy = oam_slot(m, PROP_ENTITY)
        print(f'prop entity {PROP_ENTITY} OAM: X={ox} Y={oy}')
        r.check('prop entity hardware OAM sprite hidden (Y=$F0) at HP==0',
                oy == DEAD_OAM_Y)

        # --- control: a normal AI entity (mode 2) must be unaffected by the
        # widened `cmp #2 / bcs` gate -- still alive, sprite visible. ---
        control_ox, control_oy = oam_slot(m, CONTROL_ENTITY)
        r.check(f'control entity {CONTROL_ENTITY} (AI) OAM not hidden',
                control_oy != DEAD_OAM_Y)
        control_hp = read_block(m, Entity_Hp[CONTROL_ENTITY], 32)[0]
        r.check(f'control entity {CONTROL_ENTITY} (AI) CHAR_HP unaffected by prop entity dying',
                control_hp > 0)

    r.finish()


if __name__ == '__main__':
    main()
