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

Rewritten 2026-08-29 (claude_fix_four_flaky_gates_targeted.md) to use exact
arithmetic instead of a fuzzy ratio band. The original version compared a
run-hold distance to a walk-hold distance and only asserted the RATIO was
"roughly 2", tolerated 1.5-2.5x, because Mesen's old set_input() was a
wall-clock sleep -- the actual frame count delivered under a given nominal
hold was itself uncertain, so per-frame arithmetic looked fragile. Mesen's
set_input (and the new hold_input/release_input pair used here) are now
frame-exact (McpTools.cs polls the real frame counter to the target,
verified via framesAdvanced -- see _harness.py's exact_input_edge/
run_frames_exact). With exact frame delivery, the movement rate is
completely deterministic: empirically measured (see the git history for
this file) at EXACTLY PLAYER_SPEED px/frame walking and 2*PLAYER_SPEED
px/frame running, zero variance, once a short post-latch settle window has
elapsed. That settle window (real, reproducible, ~10-12 frames from a
freshly-forced invulnerability write) is NOT this feature -- it's
Character_PlayFrame's own walk-start behavior -- so this gate explicitly
skips it (SETTLE_FRAMES) rather than either measuring across it (which
would silently undercount steady-state speed) or hiding it inside a fuzzy
tolerance band (which is exactly the kind of "not obviously wrong" laundering
the corrective instructions for this slice rule out).

Usage: python tools/verify/game_g7_run.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, run_frames_exact, Reporter  # noqa: E402

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

# Real, reproducible post-latch settle: the first ~10-12 frames after a
# fresh invulnerability write + input hold show zero net movement (measured
# directly, not assumed) before the walk animation reaches its moving
# phase. Skip it explicitly rather than let it dilute a per-frame rate
# measurement. Generous margin over the measured ~10-11 frame minimum.
SETTLE_FRAMES = 15
MEASURE_FRAMES_X = 20
MEASURE_FRAMES_Y = 8  # small: PLAYER_MAX_Y - Y_START headroom is only
                       # ~100px and run moves 2*PLAYER_SPEED*frame


def entity_pos(m, base):
    b = m.read_memory('snesMemory', base, 64)
    x = b[CHAR_POS_X] | (b[CHAR_POS_X + 1] << 8)
    y = b[CHAR_POS_Y] | (b[CHAR_POS_Y + 1] << 8)
    return x, y


def player_pos(m):
    return entity_pos(m, PLAYER_BASE)


def measure_steady_rate(m, buttons, axis, settle_frames=SETTLE_FRAMES, measure_frames=MEASURE_FRAMES_X):
    """Force invulnerability (so an AI hit's stun can't freeze movement and
    confound the measurement), hold `buttons` for `settle_frames` (skipped,
    not measured), then measure the exact position delta over the next
    `measure_frames`. Every frame advance is verified exact
    (run_frames_exact) -- a short/long delivery raises instead of silently
    producing a wrong rate."""
    m.write_u8(PLAYER_INVULN_FRAMES, 0xFF)
    m.hold_input(buttons)
    try:
        run_frames_exact(m, settle_frames)
        x0, y0 = player_pos(m)
        run_frames_exact(m, measure_frames)
        x1, y1 = player_pos(m)
    finally:
        m.release_input()
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
        # --- X axis: exact walk vs. run rate, fresh boot each so neither
        # run's held invuln window or position drift can bleed into the
        # other. ---
        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        walk_dx = measure_steady_rate(m, m.BTN_RIGHT, 'x')
        expected_walk_dx = MEASURE_FRAMES_X * PLAYER_SPEED

        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        run_dx = measure_steady_rate(m, m.BTN_RIGHT | m.BTN_B, 'x')
        expected_run_dx = MEASURE_FRAMES_X * PLAYER_SPEED * 2

        print(f'X: walk dx={walk_dx} (expected {expected_walk_dx}), '
              f'run dx={run_dx} (expected {expected_run_dx})')
        r.check(f'walk moves exactly PLAYER_SPEED*frames (X): {walk_dx} == {expected_walk_dx}',
                walk_dx == expected_walk_dx)
        r.check(f'run moves exactly 2*PLAYER_SPEED*frames (X): {run_dx} == {expected_run_dx}',
                run_dx == expected_run_dx)

        # --- Y axis: same pair, small measurement window -- PLAYER_MAX_Y -
        # PLAYER_MIN_Y is only 200px of total headroom and run covers
        # 2*PLAYER_SPEED per frame, so keep well clear of either clamp. ---
        Y_START = (PLAYER_MIN_Y + PLAYER_MAX_Y) // 2

        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        m.write_u16(PLAYER_BASE + CHAR_POS_Y, Y_START)
        walk_dy = measure_steady_rate(m, m.BTN_DOWN, 'y', measure_frames=MEASURE_FRAMES_Y)
        expected_walk_dy = MEASURE_FRAMES_Y * PLAYER_SPEED

        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        m.write_u16(PLAYER_BASE + CHAR_POS_Y, Y_START)
        run_dy = measure_steady_rate(m, m.BTN_DOWN | m.BTN_B, 'y', measure_frames=MEASURE_FRAMES_Y)
        expected_run_dy = MEASURE_FRAMES_Y * PLAYER_SPEED * 2

        print(f'Y: walk dy={walk_dy} (expected {expected_walk_dy}), '
              f'run dy={run_dy} (expected {expected_run_dy}) '
              f'(Y_START={Y_START}, headroom to PLAYER_MAX_Y={PLAYER_MAX_Y - Y_START})')
        r.check('walk did not hit PLAYER_MAX_Y clamp (Y)', Y_START + walk_dy < PLAYER_MAX_Y)
        r.check('run did not hit PLAYER_MAX_Y clamp (Y)', Y_START + run_dy < PLAYER_MAX_Y)
        r.check(f'walk moves exactly PLAYER_SPEED*frames (Y): {walk_dy} == {expected_walk_dy}',
                walk_dy == expected_walk_dy)
        r.check(f'run moves exactly 2*PLAYER_SPEED*frames (Y): {run_dy} == {expected_run_dy}',
                run_dy == expected_run_dy)

        # --- Regression: B alone (no dpad) must not move the player, over
        # an exact-verified window. ---
        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        x0, y0 = player_pos(m)
        m.write_u8(PLAYER_INVULN_FRAMES, 0xFF)
        m.hold_input(m.BTN_B)
        run_frames_exact(m, 30)
        m.release_input()
        x1, y1 = player_pos(m)
        print(f'B alone: player pos {(x0, y0)} -> {(x1, y1)}')
        r.check('holding B alone does not move the player', (x0, y0) == (x1, y1))

        # --- Regression: an AI entity's movement rate must be UNCHANGED
        # whether or not the player holds B. This is the check that would
        # have caught the real bug found in review -- __right/__left/__up/
        # __down are shared by __ai_x/__ai_y, and Input_press has no entity
        # context, so an ungated B-doubling silently sped up every AI
        # entity too. Force entity 1 into a live, unstunned, actively-
        # seeking AI state far from the player on X, then compare its exact
        # X movement (over an exact-verified frame window, past the same
        # settle period) with and without the player holding B. ---
        entity1 = ENTITY_BASES[1]

        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        force_ai_seeking(m, entity1, 8)  # PLAYER_MIN_X -- far below the
                                          # player's boot-default X, well
                                          # outside ANIM_AI_ATTACK_RANGE
        run_frames_exact(m, SETTLE_FRAMES)
        ax0, _ = entity_pos(m, entity1)
        run_frames_exact(m, MEASURE_FRAMES_X)
        ax1, _ = entity_pos(m, entity1)
        ai_dx_noinput = ax1 - ax0
        print(f'AI entity 1, no player input, {MEASURE_FRAMES_X}f (post-settle): dx={ai_dx_noinput}')

        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        force_ai_seeking(m, entity1, 8)
        m.hold_input(m.BTN_B)  # player holds B, no direction -- must not
                                # affect AI speed at all
        run_frames_exact(m, SETTLE_FRAMES)
        ax0, _ = entity_pos(m, entity1)
        run_frames_exact(m, MEASURE_FRAMES_X)
        ax1, _ = entity_pos(m, entity1)
        m.release_input()
        ai_dx_withb = ax1 - ax0
        print(f'AI entity 1, player holding B, {MEASURE_FRAMES_X}f (post-settle): dx={ai_dx_withb}')

        r.check('AI entity moved while seeking (sanity)', ai_dx_noinput > 0)
        r.check('AI entity speed unaffected by player holding B '
                '(the real bug this gate exists to catch): '
                f'{ai_dx_withb} == {ai_dx_noinput}',
                ai_dx_withb == ai_dx_noinput)

    r.finish()


if __name__ == '__main__':
    main()
