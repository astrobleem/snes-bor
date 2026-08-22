#!/usr/bin/env python3
"""plan_game.md Phase G7 (second slice) gate: post-hit invulnerability
frames for AI entities.

Background: the player has had a "briefly can't be re-hit" mechanism since
G3 (Player_InvulnFrames, core/game_state.pasm), armed only on respawn. AI
entities had nothing analogous -- Character_HitApply_VsEntity1/2/3 only
skipped a dead target (HP==0), never a target that just got hit a moment
ago. This slice adds a parallel, AI-only mechanism: three standalone WRAM
cells, Entity1/2/3_InvulnFrames (core/game_state.pasm), armed to
AI_POST_HIT_INVULN_FRAMES alongside CHAR_HIT_STUN whenever a hit lands, and
decremented once per PLAYING frame (Game_State_Play__playing, same site
Player_InvulnFrames decrements at). The player's OWN Player_InvulnFrames
mechanism is deliberately untouched by this slice -- not tested here (see
game_g3_death.py for that).

**Not a CharacterEntity struct field.** An earlier version of this slice
tried CHAR_INVULN as struct offset 36 (CHAR_ZP_LEN 36->37). That broke
phase5.py/phase6.py: growing CHAR_ZP_LEN shifts every entity's absolute WRAM
address, which flipped which physical slot the boot-time spawn table landed
an AI in. Standalone cells avoid any WRAM layout shift for anything else.

**Timing note (mesen_set_input_wall_clock project memory)**: `set_input`
sleeps a wall-clock duration scaled from its `frames` argument, so
`set_input(BTN_Y, 10)` can burn 25-35+ real emulated frames, not 10 -- far
more than the 24/36-frame stun/invuln windows this gate needs to observe
mid-decay. `run_frames(N)`, by contrast, is exact (every other phaseN.py
gate relies on this for `Nmi_FrameCounter` deltas). So attacks here are
thrown with a single minimal `set_input(BTN_Y, 1)` (just enough to register
one edge-triggered press) followed by frame-exact `run_frames(1)` polling
that reads state every single frame until the hit visibly lands (Entity1's
invuln cell goes nonzero) or a generous timeout is hit.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_HP_PER_HIT = pasm_constant('CHAR_HP_PER_HIT')
CHAR_HIT_STUN_FRAMES = pasm_constant('CHAR_HIT_STUN_FRAMES')
# AI_POST_HIT_INVULN_FRAMES itself is an expression (CHAR_HIT_STUN_FRAMES +
# 12), not a bare integer/hex literal, so pasm_constant() can't parse it --
# not needed here anyway; every check below only asserts nonzero/zero/
# relative-magnitude, never the exact arm value.

GS_PATH = 'src/core/game_state.pasm'
Entity1_InvulnFrames = pasm_constant_in(GS_PATH, 'Entity1_InvulnFrames')
Entity2_InvulnFrames = pasm_constant_in(GS_PATH, 'Entity2_InvulnFrames')
Entity3_InvulnFrames = pasm_constant_in(GS_PATH, 'Entity3_InvulnFrames')

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
PlayerEntity = ENTITY_BASES[0]
Entity1 = ENTITY_BASES[1]
Entity2 = ENTITY_BASES[2]
Entity3 = ENTITY_BASES[3]


def read_byte(m, addr):
    return read_block(m, addr, 32)[0]


def read_word(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def overlap_entity1_with_player(m):
    px = read_word(m, PlayerEntity + CHAR_POS_X)
    m.write_u16(Entity1 + CHAR_POS_X, px)
    py = read_byte(m, PlayerEntity + CHAR_POS_Y)
    m.write_u8(Entity1 + CHAR_POS_Y, py)


def entity1_state(m):
    hp = read_byte(m, Entity1 + CHAR_HP)
    stun = read_byte(m, Entity1 + CHAR_HIT_STUN)
    invuln = read_byte(m, Entity1_InvulnFrames)
    return hp, stun, invuln


def press_and_poll_until_landed(m, max_frames=40):
    """Throw one real attack (minimal-overrun single-frame set_input) and
    frame-step until the hit visibly lands (invuln cell goes nonzero) or
    max_frames elapses. Returns the state at the landing frame (or the last
    polled state on timeout)."""
    m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)
    overlap_entity1_with_player(m)
    m.set_input(m.BTN_Y, 1)
    state = entity1_state(m)
    for _ in range(max_frames):
        m.run_frames(1)
        m.pause()
        state = entity1_state(m)
        if state[2] > 0:  # invuln armed -- hit just landed
            return state
    return state


def poll_unchanged(m, frames, expect_hp, expect_stun):
    """Throw one real attack the same way, but here the hit is expected to
    be SUPPRESSED -- poll every frame for `frames` frames and assert HP/stun
    never move away from their forced starting values at any sampled frame."""
    m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)
    overlap_entity1_with_player(m)
    m.set_input(m.BTN_Y, 1)
    ok = True
    last = (expect_hp, expect_stun, None)
    for _ in range(frames):
        m.run_frames(1)
        m.pause()
        hp, stun, invuln = entity1_state(m)
        last = (hp, stun, invuln)
        if hp != expect_hp or stun != expect_stun:
            ok = False
    return ok, last


def main():
    r = Reporter('G7-INVULN', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()

        # Neutralize entities 2/3 -- same reasoning as game_g6_hud.py: real
        # background AI combat is already underway by frame 300, and a live
        # entity 2/3 attacking the player between calls would re-stun it.
        m.write_u8(Entity2 + CHAR_HP, 0)
        m.write_u8(Entity3 + CHAR_HP, 0)

        # --- 1. A real hit ARMS both CHAR_HIT_STUN and Entity1_InvulnFrames,
        # observed at the exact frame it lands. ---
        m.write_u8(Entity1 + CHAR_HP, CHAR_HP_MAX)
        m.write_u8(Entity1 + CHAR_HIT_STUN, 0)
        m.write_u8(Entity1_InvulnFrames, 0)
        hp1, stun1, invuln1 = press_and_poll_until_landed(m)
        print(f'after 1st hit: hp={hp1} stun={stun1} invuln={invuln1}')
        r.check('1st hit dropped HP by CHAR_HP_PER_HIT', hp1 == CHAR_HP_MAX - CHAR_HP_PER_HIT)
        r.check('1st hit armed CHAR_HIT_STUN (nonzero)', stun1 > 0)
        r.check('1st hit armed Entity1_InvulnFrames (nonzero)', invuln1 > 0)

        # --- 2. Stun expired, invuln still active -> a second hit must be
        # SUPPRESSED entirely (no HP loss, no HitStun re-arm) for as long as
        # the forced invuln value holds. This is the check this slice exists
        # to add. Poll well under the forced value so it can't decay to 0
        # mid-window and let a late hit land legitimately. ---
        m.write_u8(Entity1 + CHAR_HP, CHAR_HP_MAX)
        m.write_u8(Entity1 + CHAR_HIT_STUN, 0)          # stun already expired
        m.write_u8(Entity1_InvulnFrames, 20)            # still mid-grace-window
        ok2, (hp2, stun2, invuln2) = poll_unchanged(m, 12, CHAR_HP_MAX, 0)
        print(f'2nd hit (mid-invuln), last sample: hp={hp2} stun={stun2} invuln={invuln2}')
        r.check('2nd hit during invuln window never reduced HP or re-armed CHAR_HIT_STUN', ok2)

        # --- 3. Once the invuln cell has fully decayed, a hit lands normally
        # again -- proves the window is temporary, not a permanent lock. ---
        m.write_u8(Entity1 + CHAR_HP, CHAR_HP_MAX)
        m.write_u8(Entity1 + CHAR_HIT_STUN, 0)
        m.write_u8(Entity1_InvulnFrames, 0)             # window fully expired
        hp3, stun3, invuln3 = press_and_poll_until_landed(m)
        print(f'3rd hit (post-expiry): hp={hp3} stun={stun3} invuln={invuln3}')
        r.check('3rd hit after expiry DID reduce HP', hp3 == CHAR_HP_MAX - CHAR_HP_PER_HIT)
        r.check('3rd hit after expiry DID re-arm CHAR_HIT_STUN', stun3 > 0)
        r.check('3rd hit after expiry DID re-arm Entity1_InvulnFrames', invuln3 > 0)

        # --- 4. No cross-entity bleed: entities 2/3 stayed neutralized. ---
        hp2_final = read_byte(m, Entity2 + CHAR_HP)
        hp3_final = read_byte(m, Entity3 + CHAR_HP)
        print(f'entities 2/3 HP: {hp2_final}, {hp3_final} (expected 0, 0)')
        r.check('entity 2 unaffected by entity 1 invuln state', hp2_final == 0)
        r.check('entity 3 unaffected by entity 1 invuln state', hp3_final == 0)

        # --- 5. Entity1_InvulnFrames actually decrements over real frames
        # (tests the new Game_State_Play decrement code directly, independent
        # of the arm/check paths above). ---
        m.write_u8(Entity1_InvulnFrames, 30)
        m.run_frames(50)  # well past 30 -- should fully decay to 0
        m.pause()
        invuln_decayed = read_byte(m, Entity1_InvulnFrames)
        print(f'Entity1_InvulnFrames forced to 30, after 50 real frames: {invuln_decayed}')
        r.check('Entity1_InvulnFrames decays to 0 over real frames', invuln_decayed == 0)

    r.finish()


if __name__ == '__main__':
    main()
