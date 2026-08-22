#!/usr/bin/env python3
"""plan_game.md Part Two, Phase G7 (first slice) gate: player run/dash.

Holding B doubles the player's per-frame movement speed on top of the
existing dpad walk (Character_PlayFrame__right/__left/__down/__up in
main.pasm) -- no new animation, no Z axis, no struct change.

IMPORTANT, found by review before this gate first shipped: __right/__left/
__up/__down are NOT reached only by the player. __ai_x/__ai_y deliberately
reuse these same blocks for AI-driven entities (only the DPAD DISPATCH,
__dpad_x/__dpad_y, is gated on CHAR_INPUT_DRIVEN==1 -- Input_press itself is
a global controller read with no entity context). The run modifier therefore
has its own explicit CHAR_INPUT_DRIVEN==1 check inside each movement block,
independent of the dpad gate. This gate directly tests that: forcing an AI
entity into the movement blocks while the player holds B must NOT double
that entity's speed.

Ground truth here is NOT an exact-arithmetic prediction from elapsed frame
count. An earlier version of this gate tried comparing the position delta
against elapsed_frames (from Nmi_FrameCounter) * PLAYER_SPEED and found the
walk ratio itself never hit exactly PLAYER_SPEED px/frame (observed ~1.7-1.9,
not 2.0) even though the run-vs-walk RATIO was consistently ~2x (256/128
exactly 2.0 on one X run). That matches this project's own recorded lesson
(mesen_set_input_wall_clock.md): set_input's frame count is a wall-clock
lower bound, not an exact count, and some held frames land as partial
presses at the edges of the hold window -- so per-frame arithmetic against a
nominal or even a measured frame count is fragile. What IS reliable and
deterministic (both measurements share the same edge-effect bias, since they
use the same nominal hold length) is the RATIO between a run hold and a walk
hold of identical nominal length: run distance should be ~2x walk distance,
tolerated generously rather than asserted exactly.

Usage: python tools/verify/game_g7_run.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
PLAYER_SPEED = pasm_constant('PLAYER_SPEED')
PLAYER_MIN_Y = pasm_constant('PLAYER_MIN_Y')
PLAYER_MAX_Y = pasm_constant('PLAYER_MAX_Y')
ANIM_AI_ATTACK_RANGE = pasm_constant('ANIM_AI_ATTACK_RANGE')
PLAYER_INVULN_FRAMES = pasm_constant_in('src/core/game_state.pasm', 'Player_InvulnFrames')

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
PLAYER_BASE = ENTITY_BASES[0]  # "the player is always slot 0"
CHAR_INPUT_DRIVEN_AI = 2

# Expected ratio is exactly 2 (run = walk speed applied twice -- see
# Character_PlayFrame__right/__down's G7 run/dash comment in main.pasm).
# Tolerated band is generous (1.5-2.5x) to absorb the set_input edge-effect
# bias described in the module docstring above -- this is a "does the
# feature work at all" gate, not a cycle-exact timing gate.
RATIO_MIN = 1.5
RATIO_MAX = 2.5

# AI regression band: with the fix, an AI entity's speed under held-B must
# be indistinguishable from its speed with no input at all (B is not a
# direction -- it should never move ANY entity by itself, AI included). A
# tight band (not a ratio) is appropriate here since both figures should be
# ~0 or, if AI seek movement is in progress, identical single-speed steps.
AI_DELTA_TOLERANCE = PLAYER_SPEED


def entity_pos(m, base):
    b = read_block(m, base, 64)
    x = b[CHAR_POS_X] | (b[CHAR_POS_X + 1] << 8)
    y = b[CHAR_POS_Y] | (b[CHAR_POS_Y + 1] << 8)
    return x, y


def player_pos(m):
    return entity_pos(m, PLAYER_BASE)


def hold_and_measure(m, buttons, hold_frames, axis):
    """Force invulnerability (so an AI hit's stun can't freeze movement and
    confound the measurement -- same trick phase8.py uses), hold `buttons`,
    and return the position delta on the given axis."""
    m.write_u8(PLAYER_INVULN_FRAMES, 0xFF)
    x0, y0 = player_pos(m)
    m.set_input(buttons, hold_frames)
    m.pause()
    x1, y1 = player_pos(m)
    return (x1 - x0) if axis == 'x' else (y1 - y0)


def force_ai_seeking(m, base, world_x):
    """Set up entity 1 as a live, unstunned AI entity, far enough from the
    player (world X 8, PLAYER_MIN_X) on X that __ai_x won't already consider
    it in attack range and hold it still -- it should be actively stepping
    toward the player every frame this is true, which is exactly the
    movement rate the bug would have doubled."""
    m.write_u8(base + CHAR_INPUT_DRIVEN, CHAR_INPUT_DRIVEN_AI)
    m.write_u8(base + CHAR_HP, CHAR_HP_MAX)
    m.write_u8(base + CHAR_HIT_STUN, 0)
    m.write_u16(base + CHAR_POS_X, world_x)


def main():
    r = Reporter('G7-RUN', kind='GATE')

    with open_session(__file__) as m:
        # --- X axis: walk vs. run, fresh boot each so neither run's held
        # invuln window or position drift can bleed into the other. ---
        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        walk_dx = hold_and_measure(m, m.BTN_RIGHT, 60, 'x')

        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        run_dx = hold_and_measure(m, m.BTN_RIGHT | m.BTN_B, 60, 'x')

        ratio_x = run_dx / walk_dx if walk_dx else 0
        print(f'X: walk dx={walk_dx}, run dx={run_dx}, ratio={ratio_x:.2f}')
        r.check('walk moved (X)', walk_dx > 0)
        r.check(f'run/walk ratio in [{RATIO_MIN}, {RATIO_MAX}] (X)',
                RATIO_MIN <= ratio_x <= RATIO_MAX)

        # --- Y axis: same pair. PLAYER_MAX_Y - PLAYER_MIN_Y is only 200px
        # (far less headroom than X's 1080), and an earlier version of this
        # gate silently measured the CLAMP instead of run speed (walk from
        # boot-default Y=150 had only 58px of headroom to PLAYER_MAX_Y=208,
        # which is exactly what run_dy=58 turned out to be). Force CHAR_POS_Y
        # to a safe mid-range value before each measurement so a short hold
        # can't reach either clamp.
        Y_START = (PLAYER_MIN_Y + PLAYER_MAX_Y) // 2
        Y_HOLD_FRAMES = 12  # worst case run: 12 * PLAYER_SPEED * 2 px, must
                             # stay well under min(Y_START - PLAYER_MIN_Y,
                             # PLAYER_MAX_Y - Y_START)

        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        m.write_u16(PLAYER_BASE + CHAR_POS_Y, Y_START)
        walk_dy = hold_and_measure(m, m.BTN_DOWN, Y_HOLD_FRAMES, 'y')

        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        m.write_u16(PLAYER_BASE + CHAR_POS_Y, Y_START)
        run_dy = hold_and_measure(m, m.BTN_DOWN | m.BTN_B, Y_HOLD_FRAMES, 'y')

        ratio_y = run_dy / walk_dy if walk_dy else 0
        print(f'Y: walk dy={walk_dy}, run dy={run_dy}, ratio={ratio_y:.2f} '
              f'(Y_START={Y_START}, headroom to PLAYER_MAX_Y={PLAYER_MAX_Y - Y_START})')
        r.check('walk moved (Y)', walk_dy > 0)
        r.check('walk did not hit PLAYER_MAX_Y clamp (Y)', Y_START + walk_dy < PLAYER_MAX_Y)
        r.check('run did not hit PLAYER_MAX_Y clamp (Y)', Y_START + run_dy < PLAYER_MAX_Y)
        r.check(f'run/walk ratio in [{RATIO_MIN}, {RATIO_MAX}] (Y)',
                RATIO_MIN <= ratio_y <= RATIO_MAX)

        # --- Regression: B alone (no dpad) must not move the player. ---
        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        x0, y0 = player_pos(m)
        m.write_u8(PLAYER_INVULN_FRAMES, 0xFF)
        m.set_input(m.BTN_B, 30)
        m.pause()
        x1, y1 = player_pos(m)
        print(f'B alone: player pos {(x0, y0)} -> {(x1, y1)}')
        r.check('holding B alone does not move the player', (x0, y0) == (x1, y1))

        # --- Regression: an AI entity's movement rate must be UNCHANGED
        # whether or not the player holds B. This is the check that would
        # have caught the real bug found in review -- __right/__left/__up/
        # __down are shared by __ai_x/__ai_y, and Input_press has no entity
        # context, so an ungated B-doubling silently sped up every AI
        # entity too. Force entity 1 into a live, unstunned, actively-
        # seeking AI state far from the player on X, then compare its X
        # movement with and without the player holding B. ---
        entity1 = ENTITY_BASES[1]

        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        force_ai_seeking(m, entity1, 8)  # PLAYER_MIN_X -- far below the
                                          # player's boot-default X, well
                                          # outside ANIM_AI_ATTACK_RANGE
        ax0, _ = entity_pos(m, entity1)
        # Deliberately m.set_input(0, ...), NOT m.run_frames() -- the two
        # helpers advance the emulator through different code paths
        # (set_input is wall-clock/sleep-based per mesen_set_input_wall_clock
        # project memory) and were observed to let a different ACTUAL frame
        # count elapse for the same nominal 30, which alone produced a false
        # "AI sped up" reading here with no B involved. Both arms of this
        # comparison must go through the identical call shape so only the
        # button state differs.
        m.set_input(0, 30)
        m.pause()
        ax1, _ = entity_pos(m, entity1)
        ai_dx_noinput = ax1 - ax0
        print(f'AI entity 1, no player input, 30f: dx={ai_dx_noinput}')

        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        force_ai_seeking(m, entity1, 8)
        ax0, _ = entity_pos(m, entity1)
        m.set_input(m.BTN_B, 30)  # player holds B, no direction -- must not
                                   # affect AI speed at all
        m.pause()
        ax1, _ = entity_pos(m, entity1)
        ai_dx_withb = ax1 - ax0
        print(f'AI entity 1, player holding B, 30f: dx={ai_dx_withb}')

        r.check('AI entity moved while seeking (sanity)', ai_dx_noinput > 0)
        r.check('AI entity speed unaffected by player holding B '
                '(the real bug this gate exists to catch)',
                abs(ai_dx_withb - ai_dx_noinput) <= AI_DELTA_TOLERANCE)

    r.finish()


if __name__ == '__main__':
    main()
