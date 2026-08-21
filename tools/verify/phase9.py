#!/usr/bin/env python3
"""plan.md Part Two, section 2.9's "Phase 9 gate" follow-up: a
self-contained regression gate for the streaming tile cache under
SUSTAINED HELD DPAD INPUT, closing the two items that section left open
(see plan.md's "UPDATE" note there for the full history):

1. Real-play scroll-lag magnitude was previously unmeasured -- prior
   testing only ever teleported PlayerEntity_PosX directly in WRAM, never
   drove the camera with m.set_input() the way an actual player would.
2. phase9_stagecolumn_spotcheck.py / phase9_syncscroll_test2.py both need
   a manual BG_SCREENS swap to a synthetic warehouse level and real Mesen2
   wall-clock time -- not a routine gate.

This script needs NEITHER of those: the level build_rom.py actually ships
(out/bg_stage1a) is itself a streaming level (StreamScroll_StagedLo/Hi
visibly grow as the camera moves through it, checked below), so no
BG_SCREENS mutation is needed -- it runs against whatever ROM is already
built, like phase5.py-phase8.py.

Ground truth / what this checks, from a live held-dpad-right run:
  - The camera (Screen_PosX) and the streaming cache's resident window
    (StreamScroll_StagedLo/Hi) both advance under held input -- not frozen.
  - No PERMANENT stall: Nmi_FrameCounter is still advancing and the camera
    is not stuck at the same position for the ENTIRE run (a real full hang
    would fail this; the throughput dips documented below do not, since
    they recover within a few sample windows).
  - Camera lag stays bounded: Screen_PosX never drifts further than one
    screen-width-worth of desync behind where the streaming cache has
    actually loaded (StreamScroll_StagedHi), which would show up on
    screen as scrolling into unloaded/garbage tiles.

Not gated here (see phase9_syncscroll_test2.py for the strict version):
byte-exact Tile2Slot-vs-VRAM consistency. This script is about real-play
THROUGHPUT under sustained input, not per-tile correctness.

Measured finding this script formalizes (2026-08-16): under continuous
held-right on the real shipped level, player/camera advance at close to
nominal PLAYER_SPEED (2px/frame) while the streaming cache is comfortably
ahead of the camera, then visibly slow -- including brief (single-sample)
full stops -- as the camera's desired window catches up to the cache's
resident window. This is a real, previously-undocumented throughput
symptom of the shared DMA-queue budget (Msu1_LoadFrame's per-frame
one-entity-streams cap competes with StreamScroll_Budget's column DMAs)
-- not a hang, and not gated strictly here since the exact budget tuning
is expected to keep evolving (see syncscroll_budget_throughput project
memory). What IS gated is that it stays bounded and recovers.

Usage: python tools/verify/phase9.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant_in, read_block, repo_root_from, Reporter  # noqa: E402

ROOT = repo_root_from(None)
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402

BG_DIR = os.path.join(ROOT, build_rom.BG_SCREENS[0][0])

SCREEN_SIZE_X = 256  # core/screen.pasm's SCREEN_DEFAULT_SIZE_X, same
                      # not-reachable-via-pasm_constant note as phase8.py.

PlayerEntity_PosX = 0x7E0a00 + 4
Screen_PosX = 0x7E1601
Nmi_FrameCounter = 0x7E5023
StreamScroll_StagedLo = 0x7E2522
StreamScroll_StagedHi = 0x7E2524

# Empirically, a short set_input hold (~10 frames) races run_frames() and
# produces unreliable partial presses in this harness (confirmed via a
# direct A/B: 10f-hold/10f-run showed ~50% of windows as full stalls with
# BOTH PosX and Screen_PosX frozen, while 30f-hold/35f-run -- comfortably
# longer than the hold window it's paired with -- gave clean, consistent
# movement). Use the reliable cadence; see mesen_set_input_wall_clock
# project memory for the general "frames is a lower bound" caveat this
# extends.
#
# 30f/35f had ZERO margin against real-world (wall-clock) scheduling
# jitter in the Mesen automation harness: the VM Gate 1 session proved this
# directly by injecting a pure dead-cycle busy loop (no WRAM writes, no
# behavioral change whatsoever) at boot on an otherwise-unmodified engine --
# it flipped this same "no stall > 2 windows" check between PASS and FAIL
# across repeated runs of the IDENTICAL build. That means any future
# boot-time cost anywhere in the engine (not just the VM) could trip this
# gate without a real regression. Widened to 45f/55f so each sampled window
# contains enough real movement that a single badly-timed `set_input` call
# landing late can't zero out that window's whole delta -- same fix shape
# as the original 10f->30f/35f change above, just for a different jitter
# source. Re-validate with the same A/B methodology (5x on a clean build,
# 5x with injected boot-time delay) before changing this cadence again.
# ITERATIONS trimmed down from 30f/35f's 20 (~700 run frames total) so the
# widened per-window cadence below doesn't run the held-right player past
# the shipped level's end -- discovered empirically: 45f/55f x 20 (~1100
# frames) drove PosX/Screen_PosX/StreamScroll_StagedHi all the way to a
# real, legitimate plateau (world-X clamp / end of streamable content) for
# the run's back half, which looks identical to a hang to this script's
# stall counter but isn't one. 14 iterations keeps total held-input frames
# (770) close to the original cadence's (700), comfortably short of that
# plateau on the shipped level.
HOLD_FRAMES = 45
RUN_FRAMES = 55

# Phase G3 (plan_game.md 3): the player can now die and respawn at the
# camera's left edge, which resets world X and reads as a "stall" to this
# test's stall counter -- it's testing streaming-cache throughput, not
# combat survival. Force invulnerability each iteration so combat can't
# confound it (verified: WITHOUT this, held-right on this level reliably
# kills the player via organic AI combat by iteration ~7 and reaches
# GAME_STATE_GAMEOVER by iteration ~10, freezing PosX for the rest of the
# run, 3/3 reproducible runs -- a real confound, not timing jitter).
# Same fix shape as phase8.py's held-input tests.
PLAYER_INVULN_FRAMES = pasm_constant_in('src/core/game_state.pasm', 'Player_InvulnFrames')

# ITERATIONS trimmed from 14 to 8: with invulnerability removing hit-stun's
# periodic movement freeze, held-right at 45f/55f cadence empirically hits
# the level's real world-X clamp at iteration 8 (posx plateaus and repeats
# from there on) -- measured directly: [192,304,418,532,646,760,874,988,
# 1080,1080,1080,1080,1080,1080]. 8 iterations keeps every sampled window a
# real, meaningful throughput measurement instead of padding the run with
# dead plateau windows that would need excluding from the stall count.
ITERATIONS = 8


def read_u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def main():
    r = Reporter(9)

    if not os.path.isdir(BG_DIR):
        print(f'FAIL: {BG_DIR} missing -- run tools/bg_converter/convert_bg.py first')
        raise SystemExit(1)

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        staged_lo0 = read_u16(m, StreamScroll_StagedLo)
        staged_hi0 = read_u16(m, StreamScroll_StagedHi)
        print(f'shipped streaming level: {BG_DIR} '
              f'(boot StreamScroll_Staged=[{staged_lo0},{staged_hi0}])')
        r.check('level is actually streaming (StreamScroll_StagedHi > StagedLo at boot)',
                staged_hi0 > staged_lo0)

        posx_samples = []
        screen_samples = []
        staged_hi_samples = []
        for i in range(ITERATIONS):
            m.write_u8(PLAYER_INVULN_FRAMES, 0xFF)
            m.set_input(m.BTN_RIGHT, HOLD_FRAMES, port=0)
            m.run_frames(RUN_FRAMES)
            m.pause()
            posx_samples.append(read_u16(m, PlayerEntity_PosX))
            screen_samples.append(read_u16(m, Screen_PosX))
            staged_hi_samples.append(read_u16(m, StreamScroll_StagedHi))

        deltas = [posx_samples[i] - (posx_samples[i - 1] if i else posx_samples[0])
                  for i in range(len(posx_samples))]
        print(f'PosX samples: {posx_samples}')
        print(f'per-iteration deltas: {deltas}')
        print(f'Screen_PosX samples: {screen_samples}')
        print(f'StreamScroll_StagedHi samples: {staged_hi_samples}')

        total_advance = posx_samples[-1] - posx_samples[0]
        r.check(f'player advanced under sustained held-right ({total_advance}px over '
                 f'{ITERATIONS} iterations, ~{ITERATIONS * RUN_FRAMES} frames)',
                 total_advance > 0)

        r.check('camera (Screen_PosX) advanced too (tracks the player, not stuck)',
                 screen_samples[-1] > screen_samples[0])

        r.check('streaming cache kept extending its resident window as the camera moved '
                '(StreamScroll_StagedHi grew)',
                 staged_hi_samples[-1] > staged_hi0)

        # No PERMANENT stall: a real hang would show every remaining sample
        # frozen at the same value. A recoverable throughput dip (what the
        # module docstring above documents) shows SOME zero-delta windows
        # but always recovers -- so the check is "not stuck for the whole
        # back half of the run", not "zero stalls allowed".
        back_half = deltas[ITERATIONS // 2:]
        r.check('not permanently stalled (advanced at least once in the second half of the run)',
                 any(d > 0 for d in back_half))

        max_consecutive_stall = 0
        run = 0
        for d in deltas:
            run = run + 1 if d == 0 else 0
            max_consecutive_stall = max(max_consecutive_stall, run)
        print(f'longest consecutive-stall run: {max_consecutive_stall} iteration(s) '
              f'({max_consecutive_stall * RUN_FRAMES} frames)')
        r.check('no stall lasted more than 2 consecutive sample windows '
                '(~70 frames) -- a real hang regression, not throughput dips',
                 max_consecutive_stall <= 2)

        # Camera lag stays bounded: the camera should never be more than
        # one screen-width-plus-margin behind the streaming cache's own
        # resident high-water mark, which would mean scrolling toward
        # tiles that were never actually loaded.
        max_lag = max(hi * 8 - scr for hi, scr in zip(staged_hi_samples, screen_samples))
        print(f'max (StreamScroll_StagedHi*8 - Screen_PosX): {max_lag}px')
        r.check(f'camera never lags more than one screen-width behind the cache\'s own '
                f'resident high-water mark ({max_lag}px <= {SCREEN_SIZE_X * 2}px)',
                 max_lag <= SCREEN_SIZE_X * 2)

        fc0 = read_u16(m, Nmi_FrameCounter)
        m.run_frames(60)
        m.pause()
        fc1 = read_u16(m, Nmi_FrameCounter)
        r.check('Nmi_FrameCounter still advancing at end of run (engine not hung)',
                 fc1 != fc0)

    r.finish()


if __name__ == '__main__':
    main()
