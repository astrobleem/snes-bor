#!/usr/bin/env python3
"""plan.md Part Two, section 2.11, Phase 11 gate: the damage system --
an AI entity (CHAR_INPUT_DRIVEN==2) that reaches CHAR_HP==0 stops acting,
stops taking/dealing further hits, and its OAM sprite hides, all WITHOUT
ever calling core/oop.pasm's generic Core_Oop_Destroy/garbage-collect path
(which would compact OopObjRam and rewrite surviving entities' OopDp
pointers -- fatal to this codebase's fixed-address Entity1_Base/Entity2_Base/
Entity3_Base scheme, hardcoded throughout Character_HitApply_VsEntityN and
elsewhere; see CLAUDE.md's "player is always slot 0" note). CHAR_HP==0 is
the sticky dead flag itself -- no new struct field.

Scope: AI entities only. The player (CHAR_INPUT_DRIVEN==1) is deliberately
exempt -- player death/game-over is out of scope (plan.md "Explicitly out
of scope").

Checks, all against a live Mesen2 session (ground truth: hardware OAM,
WRAM, and the frame counter -- not self-consistency):
1. Force Entity #1's CHAR_HP to 0 directly (safe to write directly, unlike
   PosX in Phase 10's test -- nothing else ever writes Hp except the
   HitApply leaves' own clamp-at-0, so there's no other writer to race).
2. Over 600 real frames: CHAR_POS_X must stay frozen (AI stopped acting/
   moving), Entity1_HitStun must read 0 (dead entity takes no further hits),
   hardware OAM slot 1's Y byte must read $F0 (hidden, matching the
   documented "clean OAM" idiom -- see ccdma_validated_nmi_timing_bug
   project memory), and Nmi_FrameCounter must keep advancing (no vblank
   overrun introduced by the new branches).
3. Entities 0 (player), 2, and 3 are unaffected controls: their OAM Y must
   not read $F0, their CHAR_HP must be untouched by entity 1's death, and
   they must still be animating (CHAR_FRAME_INDEX varies over time) --
   NOT position, since a living AI entity holds position once within
   ANIM_AI_ATTACK_RANGE of the player (Character_PlayFrame__ai_x's own
   documented behavior), so a frozen X for a converged, still-attacking AI
   is expected and not evidence of the new dead-check misfiring on it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]

CHAR_POS_X = 4
CHAR_FRAME_INDEX = 9
CHAR_HIT_STUN = 33
CHAR_HP = 35

Entity1_Hp = ENTITY_BASES[1] + CHAR_HP
Entity1_HitStun = ENTITY_BASES[1] + CHAR_HIT_STUN
Nmi_FrameCounter = 0x7E5023

DEAD_OAM_Y = 0xF0


def entity_posx(m, base):
    block = read_block(m, base, 32)
    return block[CHAR_POS_X] | (block[CHAR_POS_X + 1] << 8)


def entity_hp_and_frame(m, base):
    block = read_block(m, base, 64)  # CHAR_HP is offset 35 -- past a 32-byte read
    return block[CHAR_HP], block[CHAR_FRAME_INDEX]


def oam_slot(m, slot):
    block = read_block(m, 0, 32, mem_type='snesSpriteRam')
    off = slot * 4
    return block[off], block[off + 1]  # X, Y


def main():
    r = Reporter(11)

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()

        hp_before = read_block(m, Entity1_Hp, 32)[0]
        print(f'Entity1_Hp before kill: {hp_before}')

        # Spawn-table phase (2026-08-16): entities 2/3 no longer stand alive
        # from boot -- they start CHAR_HP=0 (unspawned, see core/spawn.pasm)
        # and only reach CHAR_HP_MAX once the level's spawn queue trigger_x
        # is reached, which needs camera movement this test never drives.
        # This test needs them ALIVE as controls (to prove the dead-check is
        # scoped to entity 1 only, not freezing everyone) -- same "direct
        # WRAM write is safe here, nothing else races CHAR_HP" reasoning as
        # entity 1's own kill write below, just setting HP up instead of
        # down.
        for i in (2, 3):
            m.write_memory('snesMemory', ENTITY_BASES[i] + CHAR_HP, f'{CHAR_HP_MAX:02X}')
        m.run_frames(5)
        m.pause()

        posx_before = {i: entity_posx(m, b) for i, b in enumerate(ENTITY_BASES)}

        # Kill entity 1: direct WRAM write is safe here -- nothing else
        # writes CHAR_HP except the HitApply leaves' own clamp-at-0 (unlike
        # Phase 10's PosX, which AI-collision perturbs every frame).
        m.write_memory('snesMemory', Entity1_Hp, '00')

        fc_before = read_block(m, Nmi_FrameCounter, 32)
        fc_before = fc_before[0] | (fc_before[1] << 8)

        m.run_frames(600)
        m.pause()

        hp_after = read_block(m, Entity1_Hp, 32)[0]
        r.check('Entity1_Hp stays 0 after kill', hp_after == 0)

        posx_after = {i: entity_posx(m, b) for i, b in enumerate(ENTITY_BASES)}
        print(f'PosX before/after 600f: {[(posx_before[i], posx_after[i]) for i in range(4)]}')
        r.check('dead entity 1 X position frozen', posx_after[1] == posx_before[1])

        hitstun_after = read_block(m, Entity1_HitStun, 32)[0]
        r.check('dead entity 1 takes no further hit stun', hitstun_after == 0)

        ox, oy = oam_slot(m, 1)
        print(f'OAM slot1 (entity1): X={ox} Y={oy}')
        r.check('dead entity 1 hardware OAM sprite hidden (Y=$F0)', oy == DEAD_OAM_Y)

        fc_after = read_block(m, Nmi_FrameCounter, 32)
        fc_after = fc_after[0] | (fc_after[1] << 8)
        print(f'Nmi_FrameCounter: {fc_before} -> {fc_after}')
        r.check('Nmi_FrameCounter still advancing (no vblank overrun)', fc_after != fc_before)

        # --- controls: entities 0/2/3 unaffected ---
        for i in (0, 2, 3):
            ox, oy = oam_slot(m, i)
            r.check(f'live entity {i} OAM not hidden', oy != DEAD_OAM_Y)
        # HP-untouched-by-entity-1-dying is only meaningful for the OTHER AI
        # (2, 3) -- the player's own HP is expected to keep dropping over
        # 600+ frames from entities 2/3's own ongoing (correct, pre-existing
        # Phase 6) attacks, unrelated to this feature.
        for i in (2, 3):
            hp, _ = entity_hp_and_frame(m, ENTITY_BASES[i])
            r.check(f'live entity {i} CHAR_HP untouched by entity 1 dying', hp > 0)

        # Sample CHAR_FRAME_INDEX across several ticks for entities 2/3 --
        # position alone can't distinguish "still animating/attacking" from
        # "the new dead-check is wrongly freezing it too", since a live AI
        # holding attack range also stops moving (see module docstring).
        #
        # Stride must NOT be a "round" frame count -- Phase 15 (plan.md
        # 2.15) found a real false FAIL here: Yashiro's (entity 3's own
        # roster character) attack-animation cycle period evenly divides 40,
        # so a fixed 40-frame stride always samples the exact same phase --
        # a strobe/aliasing artifact indistinguishable from a genuine freeze
        # by this check alone. Single-frame-stepping and a 37-frame (prime)
        # stride both showed it animating normally; JOE (entity 2) never
        # exhibited this because its own cycle period doesn't happen to
        # divide 40. 37 is prime, so it can't alias against any small-integer
        # cycle length the way 40 (2^3*5) can. See phase12_roster memory /
        # this phase's own project memory for the full investigation.
        frame_samples = {2: [], 3: []}
        for _ in range(6):
            m.run_frames(37)
            m.pause()
            for i in (2, 3):
                _, fi = entity_hp_and_frame(m, ENTITY_BASES[i])
                frame_samples[i].append(fi)
        print(f'CHAR_FRAME_INDEX samples: entity2={frame_samples[2]} entity3={frame_samples[3]}')
        r.check('living entity 2 still animating', len(set(frame_samples[2])) > 1)
        r.check('living entity 3 still animating', len(set(frame_samples[3])) > 1)

    r.finish()


if __name__ == '__main__':
    main()
