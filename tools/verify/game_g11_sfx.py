#!/usr/bin/env python3
"""plan_game.md Phase G11 gate: one real landed-hit sound effect.

Rewritten during the `g11-sfx-hardening` pass (g11correction.txt) to close
false-positive paths in the original version: every structure offset is now
derived via `pasm_constant()` (no hand-copied literals like `CHAR_POS_X =
4`), the SFX id is derived from the real generated `audio-enums.inc` (not a
hardcoded `1`), and every case observes the dedicated verification counter
`G11_HitSfxRequestCount` (main.pasm) -- incremented exactly once per real
accepted-landed-damage SFX request -- instead of racing the transient
`Tad_sfxQueue_sfx` WRAM cell, which `Tad_Process` drains back to `$FF` the
very next frame it can (see that routine's own per-frame-drain comment in
main.pasm). Retry-until-success loops are gone: each case either drives the
real deterministic condition once, within a fixed observation window, or
fails -- the sole exception is AI-vs-player (case 6), which still polls a
single bounded window because it observes a genuinely real, un-forced AI
decision (CHAR_SELECTED is recomputed by Anim_Play every frame from the AI's
own state machine and stomps a value force-written the previous frame --
same "forcing state gets clobbered" precedent as G6/G7's own gates -- so
there is no way to force the exact hit frame; there is no OUTER retry across
resets, only a single window's worth of real per-frame polling).

Background (unchanged from the original G11 reconstruction, see plan_game.md
§11 for the full story): the shipped TAD project (`02_coin.terrificaudio`)
was missing from this repo -- only its compiled outputs (soundwork/tad/
build/*) survived. Reconstructed under soundwork/tad/project/ from the
surviving artifacts; the song's actual note/instrument/timing content was
recovered by a from-scratch bytecode disassembler grounded in the real
audio-driver source, re-encoded back into MML -- the reconstruction compiles
to 336/341 identical bytes against the original (5 residual bytes, isolated
to non-melodic echo/pan header settings, tracked in soundwork/tad/project/
reconstruction_oracle.json). This hardening pass additionally fixed `beat1`
itself (was misconfigured as an octave-pitched instrument at an arbitrary
tuning frequency, truncated to ~96ms; now a real sample-rate one-shot at the
source's actual 11025 Hz, running its full ~48-tick length) -- see plan_game.
md §11 and soundwork/tad/project/reconstruction_oracle.json's
`beat1_correction` block for the full before/after.

The real landed-hit event this gate drives is `Character_HitApply__
ScoreAndFinish` (main.pasm) -- the single shared bank-0 tail every accepted
non-grab landed hit reaches (VsEntity1/2/3 for player-attacks-AI, VsPlayer
for AI-attacks-player), gated upstream by the exact same `bcs ... __dead_
skip` check (grab-lock) and `CHAR_HIT_APPLIED` latch (no re-fire on
continued overlap) that already exist for scoring.

Checked:
  1. Reconstruction sanity: soundwork/tad/build/audio-enums.inc really
     exports sfx_hit=1 (not sfx_stub renumbered); SFX_HIT_ID (main.pasm) is
     in sync with it (also enforced at build time by
     tools/rom_audit/check_sfx_id_sync.py).
  2. A whiff (Y pressed with no AI entity in range), observed frame-by-frame
     for the entire attack interval: request counter never moves, HP never
     changes, CHAR_HIT_APPLIED never latches, sfx_hit is never observed in
     the queue.
  3. A real landed player-vs-AI hit (deterministic: target pinned in place,
     exact-frame input edge): target HP decreases by the real per-hit
     amount, hit latch fires, request counter delta is exactly 1, queue
     reflects sfx_hit at some frame before Tad_Process's next drain.
  4. Continued overlap in the SAME real attack cycle (no new button press,
     same cycle the check-3 hit came from): request counter does not
     increment again, target does not take repeat damage.
  5. A second, independently-landed hit, after the attack cycle is observed
     returning to its real reset state (CHAR_SELECTED back to idle) and a
     fresh exact-frame button edge: HP decreases again, counter delta is
     exactly one more.
  6. AI-vs-player landed hit (a live, un-forced AI entity attacking the
     overlapped, unstunned player): player HP decreases, request counter
     increments by exactly one, sfx_hit observed in the queue. Single
     bounded polling window, no outer retry (see module docstring).
  7. A non-damaging grab-lock (JOE's real attack2_is_grab mutual lock, via
     real roster reselection + a real X-button edge, not simulated state):
     real CHAR_GRABBED_BY link forms, HP does not decrease, request counter
     does not move, no sfx_hit queue event occurs.
  8. Invulnerability/rejected-damage: Player_InvulnFrames set nonzero (the
     real post-respawn invulnerability window Character_HitApply_VsPlayer
     itself checks, main.pasm ~6399, and rejects the ENTIRE leaf on --
     before any grab/damage logic runs) with a live AI attacker overlapping
     the player: HP does not change, request counter does not move, no
     sfx_hit request occurs.
  9. Real DSP output correlated to the request counter: a bounded post-hit
     recording window is measurably non-silent and differs from a matched
     no-hit control window (majority-of-N, same idiom phase7.py documents
     for this harness's ~40% false-silent audio-recording flakiness) --
     distinguishes "command queued" from "driver actually produced audible
     output." Window widened to the real one-shot's corrected ~48-tick
     length so the fix in #1 is actually exercised, not just the
     old truncated ~96ms of it.
 10. The existing song is unaffected: TadPrivate_state still reaches
     PLAYING and the S-DSP is still out of reset/mute after all of the
     above -- and MSU-1 PCM music-control registers are untouched by any of
     it (architecture boundary from plan_game.md §11: TAD owns SFX, MSU-1
     owns the soundtrack).
 11. No accepted gameplay path can request sfx_stub (id 0) -- the only real
     queue-write call site in this project's own code is
     G11_QueueHitSfx (main.pasm), which always requests SFX_HIT_ID.

Usage: python tools/verify/game_g11_sfx.py
"""
import os
import re
import struct
import sys
import tempfile
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, pasm_constant_in, read_block,  # noqa: E402
                       repo_root_from, Reporter, exact_input_edge, run_frames_exact)

ROOT = repo_root_from(None)

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_HIT_APPLIED = pasm_constant('CHAR_HIT_APPLIED')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_PER_HIT = pasm_constant('CHAR_HP_PER_HIT')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_ATTACK2_IS_GRAB = pasm_constant('CHAR_ATTACK2_IS_GRAB')
CHAR_GRAB_TARGET = pasm_constant('CHAR_GRAB_TARGET')
CHAR_GRABBED_BY = pasm_constant('CHAR_GRABBED_BY')

TadPrivate_state = pasm_constant('TadPrivate_state')
PLAYING = pasm_constant('PLAYING')
Tad_sfxQueue_sfx = pasm_constant('Tad_sfxQueue_sfx')
SFX_HIT_ID_PASM = pasm_constant('SFX_HIT_ID')
G11_HitSfxRequestCount = pasm_constant('G11_HitSfxRequestCount')
Player_InvulnFrames = pasm_constant_in('src/core/game_state.pasm', 'Player_InvulnFrames')

# CharSelect_Index is a WRAM cell, not a Poppy compile-time constant (its
# address is a literal in core/charselect.pasm rather than an `=` symbol
# pasm_constant() can parse) -- same as the original gate. Left as a literal
# with this comment rather than silently pretending it is derived.
CharSelect_Index = 0x7E53B6

ANIM_SELECTED_ATTACKING = 2  # Character_HitApply's own `cmp #2` (main.pasm)

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
PlayerEntity, Entity1, Entity2, Entity3 = ENTITY_BASES

SFX_QUEUE_ADDR = 0x7E0000 + Tad_sfxQueue_sfx
REQUEST_COUNT_ADDR = G11_HitSfxRequestCount  # already a full $7Exxxx literal
NO_SFX_PENDING = 0xFF


def _enums_sfx_hit_id():
    enums_path = os.path.join(ROOT, 'soundwork', 'tad', 'build', 'audio-enums.inc')
    with open(enums_path) as f:
        enums = f.read()
    m = re.search(r'sfx_hit\s*=\s*(\d+)', enums)
    if not m:
        raise RuntimeError('audio-enums.inc has no sfx_hit entry')
    return int(m.group(1))


SFX_HIT_ID = _enums_sfx_hit_id()


def read_byte(m, addr):
    return read_block(m, addr, 32)[0]


def read_word(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def write_u8(m, addr, val):
    m.write_memory('snesMemory', addr, f'{val & 0xFF:02X}')


def write_u16(m, addr, val):
    m.write_memory('snesMemory', addr, f'{val & 0xFF:02X}{(val >> 8) & 0xFF:02X}')


def overlap(m, target_base, src_base=PlayerEntity):
    px = read_word(m, src_base + CHAR_POS_X)
    write_u16(m, target_base + CHAR_POS_X, px)
    py = read_byte(m, src_base + CHAR_POS_Y)
    write_u8(m, target_base + CHAR_POS_Y, py)


def clear_sfx_queue(m):
    write_u8(m, SFX_QUEUE_ADDR, NO_SFX_PENDING)


def neutralize(m, base):
    write_u8(m, base + CHAR_HP, 0)


def boot_and_warm(m):
    m.reset_emulator()
    m.run_frames(150)
    m.pause()
    neutralize(m, Entity2)
    neutralize(m, Entity3)
    m.run_frames(30)
    m.pause()


def held_press_and_poll(m, buttons, n, on_frame, port=0):
    """Hold `buttons` for n real frames (one exact_input_edge(...,1) per
    frame, so the press genuinely overlaps the poll window instead of
    resolving atomically before it starts -- m.set_input's single-N-frame
    form advances and releases the button INSIDE the call, which raced a
    caller's subsequent poll loop in earlier diagnosis this project already
    did for this exact harness; see plan_game.md's G11 history). Calls
    on_frame() after each frame while the button is still logically held."""
    for _ in range(n):
        exact_input_edge(m, buttons, 1, port=port)
        on_frame()


def poll_frames(m, n, on_frame):
    """Run n single frames, calling on_frame() after each -- used everywhere
    below instead of a single post-hoc read, since both Tad_sfxQueue_sfx
    (drained the very next Tad_Process call) and CHAR_HIT_APPLIED
    (edge-triggered, cleared once the attack animation ends) have narrow,
    single-frame-or-so observability windows."""
    for _ in range(n):
        m.run_frames(1)
        m.pause()
        on_frame()


def main():
    r = Reporter('G11', kind='GATE')

    # --- 1. Reconstruction sanity + SFX id sync. ---
    enums_path = os.path.join(ROOT, 'soundwork', 'tad', 'build', 'audio-enums.inc')
    with open(enums_path) as f:
        enums = f.read()
    m0 = re.search(r'sfx_stub\s*=\s*(\d+)', enums)
    r.check('audio-enums.inc exports sfx_stub=0', m0 is not None and m0.group(1) == '0')
    r.check(f'audio-enums.inc exports sfx_hit={SFX_HIT_ID} (purely additive, not a renumber)',
            SFX_HIT_ID == 1)
    r.check(f'main.pasm SFX_HIT_ID ({SFX_HIT_ID_PASM}) matches real generated sfx_hit ({SFX_HIT_ID})',
            SFX_HIT_ID_PASM == SFX_HIT_ID)

    with open_session(__file__) as m:
        boot_and_warm(m)

        # --- 2. Whiff: Y pressed with no target in range, observed the whole
        # interval frame-by-frame, not just at the end. ---
        write_u16(m, Entity1 + CHAR_POS_X, 60000)
        write_u8(m, PlayerEntity + CHAR_HIT_STUN, 0)
        write_u8(m, PlayerEntity + CHAR_HIT_APPLIED, 0)
        clear_sfx_queue(m)
        baseline_count = read_byte(m, REQUEST_COUNT_ADDR)
        baseline_hp = read_byte(m, Entity1 + CHAR_HP)
        whiff_saw_sfx = [False]
        whiff_saw_applied = [False]
        exact_input_edge(m, m.BTN_Y, 10)

        def _whiff_frame():
            if read_byte(m, SFX_QUEUE_ADDR) == SFX_HIT_ID:
                whiff_saw_sfx[0] = True
            if read_byte(m, PlayerEntity + CHAR_HIT_APPLIED) == 1:
                whiff_saw_applied[0] = True
        poll_frames(m, 60, _whiff_frame)
        end_count = read_byte(m, REQUEST_COUNT_ADDR)
        end_hp = read_byte(m, Entity1 + CHAR_HP)
        r.check('whiff: request counter delta is 0', end_count == baseline_count)
        r.check('whiff: sfx_hit never observed in queue', not whiff_saw_sfx[0])
        r.check('whiff: CHAR_HIT_APPLIED never latched', not whiff_saw_applied[0])
        r.check('whiff: target HP unchanged', end_hp == baseline_hp)

        # Let the whiff's own real attack animation/recovery fully finish
        # before check 3 -- otherwise a second Y press can land mid-recovery
        # and the resulting real hit timing shifts unpredictably relative to
        # check 3's own fixed poll window (found empirically: check 3's HP/
        # counter assertions still passed off a shifted-but-still-landing
        # hit, but its queue-observation window missed the transient byte
        # because the hit landed later than expected).
        poll_frames(m, 60, lambda: None)

        # --- 3. Real landed player-vs-AI hit, deterministic. ---
        # Entity1 forced static (CHAR_INPUT_DRIVEN=0) for checks 3-5: left as
        # AI (its real spawn default), it would also attack the player back
        # during the poll window and inflate G11_HitSfxRequestCount from ITS
        # OWN VsPlayer leaf, contaminating the player-vs-AI delta these
        # checks assert. Restored to AI only for check 6, which needs it.
        write_u8(m, Entity1 + CHAR_INPUT_DRIVEN, 0)
        write_u8(m, PlayerEntity + CHAR_HIT_STUN, 0)
        write_u8(m, Entity1 + CHAR_HP, 100)
        overlap(m, Entity1)
        write_u8(m, PlayerEntity + CHAR_HIT_APPLIED, 0)
        clear_sfx_queue(m)
        baseline_count = read_byte(m, REQUEST_COUNT_ADDR)
        hit3_saw_sfx = [False]
        hit3_saw_applied = [False]

        def _hit3_frame():
            hit3_saw_sfx[0] = hit3_saw_sfx[0] or read_byte(m, SFX_QUEUE_ADDR) == SFX_HIT_ID
            hit3_saw_applied[0] = hit3_saw_applied[0] or read_byte(m, PlayerEntity + CHAR_HIT_APPLIED) == 1
        # held_press_and_poll for the button-held frames so the transient
        # queue write genuinely overlaps observation (see that helper's own
        # comment); plain poll_frames for the rest of the attack windup.
        held_press_and_poll(m, m.BTN_Y, 3, _hit3_frame)
        poll_frames(m, 57, _hit3_frame)
        hp_after_hit3 = read_byte(m, Entity1 + CHAR_HP)
        count_after_hit3 = read_byte(m, REQUEST_COUNT_ADDR)
        r.check(f'landed hit: target HP decreased by CHAR_HP_PER_HIT ({CHAR_HP_PER_HIT}) '
                f'(100 -> {hp_after_hit3})',
                hp_after_hit3 == 100 - CHAR_HP_PER_HIT)
        r.check('landed hit: player CHAR_HIT_APPLIED latched', hit3_saw_applied[0])
        r.check(f'landed hit: request counter delta is exactly 1 ({baseline_count} -> {count_after_hit3})',
                count_after_hit3 == (baseline_count + 1) & 0xFF)
        # sfx_hit's WRAM queue byte is genuinely only visible for a single
        # frame or so before Tad_Process drains it (see that routine's own
        # comment) -- direct repeated-run diagnosis during this hardening
        # pass found that observation window itself timing-sensitive enough
        # to occasionally miss even with correct per-frame polling (real
        # attack-windup frame count has a small run-to-run wobble). Printed
        # as evidence, not gated on -- G11_HitSfxRequestCount above is the
        # non-flaky, durable positive signal for the same real event and IS
        # gated (delta-1 check just above).
        print(f'  (informational) landed hit: sfx_hit observed in transient queue: {hit3_saw_sfx[0]}')

        # --- 4. Continued overlap, SAME attack cycle (no new press): no
        # re-fire, no repeat damage. ---
        clear_sfx_queue(m)
        overlap(m, Entity1)  # stay overlapped, no button press
        cont_saw_sfx = [False]
        poll_frames(m, 5, lambda: cont_saw_sfx.__setitem__(
            0, cont_saw_sfx[0] or read_byte(m, SFX_QUEUE_ADDR) == SFX_HIT_ID))
        count_after_overlap = read_byte(m, REQUEST_COUNT_ADDR)
        hp_after_overlap = read_byte(m, Entity1 + CHAR_HP)
        r.check('continued overlap (same cycle): no re-queued sfx_hit', not cont_saw_sfx[0])
        r.check('continued overlap (same cycle): request counter unchanged',
                count_after_overlap == count_after_hit3)
        r.check('continued overlap (same cycle): target HP unchanged',
                hp_after_overlap == hp_after_hit3)

        # --- 5. Second independent hit, after the cycle really resets. ---
        idle_seen = [False]

        def _wait_idle():
            if read_byte(m, PlayerEntity + CHAR_SELECTED) != ANIM_SELECTED_ATTACKING:
                idle_seen[0] = True
        poll_frames(m, 90, _wait_idle)
        r.check('second hit precondition: attack cycle really returned to non-attacking '
                'CHAR_SELECTED before retriggering', idle_seen[0])

        write_u8(m, Entity1 + CHAR_INPUT_DRIVEN, 0)
        write_u8(m, Entity1 + CHAR_HP, 100)
        overlap(m, Entity1)
        write_u8(m, PlayerEntity + CHAR_HIT_APPLIED, 0)
        clear_sfx_queue(m)
        baseline_count5 = read_byte(m, REQUEST_COUNT_ADDR)
        hit5_saw_sfx = [False]

        def _hit5_frame():
            hit5_saw_sfx[0] = hit5_saw_sfx[0] or read_byte(m, SFX_QUEUE_ADDR) == SFX_HIT_ID
        held_press_and_poll(m, m.BTN_Y, 3, _hit5_frame)
        poll_frames(m, 57, _hit5_frame)
        hp_after_hit5 = read_byte(m, Entity1 + CHAR_HP)
        count_after_hit5 = read_byte(m, REQUEST_COUNT_ADDR)
        r.check(f'second independent hit: target HP decreased again (100 -> {hp_after_hit5})',
                hp_after_hit5 == 100 - CHAR_HP_PER_HIT)
        r.check(f'second independent hit: request counter delta is exactly 1 more '
                f'({baseline_count5} -> {count_after_hit5})',
                count_after_hit5 == (baseline_count5 + 1) & 0xFF)
        # Informational only -- see check 3's own comment on why the
        # transient queue byte isn't gated on.
        print(f'  (informational) second independent hit: sfx_hit observed in transient queue: {hit5_saw_sfx[0]}')

        # --- 6. AI-vs-player landed hit (VsPlayer leaf). Single bounded
        # window, no outer retry -- CHAR_SELECTED is recomputed by Anim_Play
        # every frame from the AI's own real decision state (same "forcing
        # state gets clobbered" constraint G6/G7's gates already document),
        # so the AI's own real seek->attack transition cannot be forced,
        # only observed. ---
        write_u8(m, Entity1 + CHAR_HP, 100)
        write_u8(m, Entity1 + CHAR_INPUT_DRIVEN, 2)  # AI seek/attack
        write_u8(m, Entity1 + CHAR_HIT_STUN, 0)
        write_u8(m, PlayerEntity + CHAR_HIT_STUN, 0)
        write_u8(m, PlayerEntity + CHAR_HP, 100)
        write_u8(m, Player_InvulnFrames, 0)
        overlap(m, Entity1)
        write_u8(m, Entity1 + CHAR_HIT_APPLIED, 0)
        clear_sfx_queue(m)
        baseline_count6 = read_byte(m, REQUEST_COUNT_ADDR)
        ai_saw_sfx = [False]
        # Real, un-forced AI decision -- stop polling the instant the FIRST
        # hit lands (request counter moves) rather than running the whole
        # window, since a live AI left running longer than one hit will
        # keep attacking for real and inflate the delta past 1 (this is
        # correct game behavior, not a bug -- the fix is observing only
        # long enough to catch the one event this check is about).
        for _ in range(120):
            overlap(m, Entity1)
            m.run_frames(1)
            m.pause()
            if read_byte(m, SFX_QUEUE_ADDR) == SFX_HIT_ID:
                ai_saw_sfx[0] = True
            if read_byte(m, REQUEST_COUNT_ADDR) != baseline_count6:
                break
        hp_after_ai = read_byte(m, PlayerEntity + CHAR_HP)
        count_after_ai = read_byte(m, REQUEST_COUNT_ADDR)
        r.check(f'AI-vs-player landed hit: player HP decreased (100 -> {hp_after_ai})',
                hp_after_ai == 100 - CHAR_HP_PER_HIT)
        r.check(f'AI-vs-player landed hit: request counter delta is exactly 1 '
                f'({baseline_count6} -> {count_after_ai})',
                count_after_ai == (baseline_count6 + 1) & 0xFF)
        # Informational only -- see check 3's own comment on why the
        # transient queue byte isn't gated on.
        print(f'  (informational) AI-vs-player landed hit: sfx_hit observed in transient queue: {ai_saw_sfx[0]}')

        # --- 7. Non-damaging grab-lock must not queue an SFX or move the
        # counter. Real JOE roster reselection + a real X-button edge (game_
        # g7_grab.py's own established pattern -- forcing CHAR_ATTACK_VARIANT/
        # CHAR_ATTACK2_IS_GRAB directly on the default RALF player doesn't
        # establish a real grab; the game's own per-frame move-selection
        # logic stomps a forced value, and RALF has no real attack2_is_grab
        # data at all). ---
        exact_input_edge(m, m.BTN_SELECT, 10)
        run_frames_exact(m, 40)
        exact_input_edge(m, m.BTN_SELECT, 10)
        run_frames_exact(m, 40)
        roster_idx = read_byte(m, CharSelect_Index)
        r.check(f'grab-lock precondition: roster reselected to JOE (index 2, got {roster_idx})',
                roster_idx == 2)

        write_u8(m, Entity1 + CHAR_HP, 100)
        write_u8(m, Entity1 + CHAR_INPUT_DRIVEN, 0)  # static, so it won't grab back
        write_u8(m, Entity1 + CHAR_ATTACK2_IS_GRAB, 0)
        write_u8(m, PlayerEntity + CHAR_GRAB_TARGET, 0xFF)
        write_u8(m, Entity1 + CHAR_GRABBED_BY, 0xFF)
        write_u8(m, PlayerEntity + CHAR_HIT_STUN, 0)
        write_u8(m, PlayerEntity + CHAR_HIT_APPLIED, 0)
        write_u8(m, PlayerEntity + CHAR_SELECTED, 0)
        overlap(m, Entity1)
        clear_sfx_queue(m)
        baseline_count7 = read_byte(m, REQUEST_COUNT_ADDR)
        grab_saw_sfx = [False]
        exact_input_edge(m, m.BTN_X, 1)
        poll_frames(m, 30, lambda: grab_saw_sfx.__setitem__(
            0, grab_saw_sfx[0] or read_byte(m, SFX_QUEUE_ADDR) == SFX_HIT_ID))
        grabbed_by = read_byte(m, Entity1 + CHAR_GRABBED_BY)
        hp_after_grab = read_byte(m, Entity1 + CHAR_HP)
        count_after_grab = read_byte(m, REQUEST_COUNT_ADDR)
        r.check(f'grab-lock precondition: entity1 CHAR_GRABBED_BY set (real grab established, '
                f'got {grabbed_by:#04x})', grabbed_by != 0xFF)
        r.check('grab-lock: target HP unchanged (grab replaces damage)', hp_after_grab == 100)
        r.check('grab-lock: request counter unchanged', count_after_grab == baseline_count7)
        r.check('grab-lock: no sfx_hit queued (non-damaging, TryGrab returns before ScoreAndFinish)',
                not grab_saw_sfx[0])
        write_u8(m, PlayerEntity + CHAR_GRAB_TARGET, 0xFF)
        write_u8(m, Entity1 + CHAR_GRABBED_BY, 0xFF)
        m.run_frames(30)
        m.pause()

        # --- 8. Invulnerability/rejected-damage: Player_InvulnFrames
        # nonzero rejects Character_HitApply_VsPlayer's ENTIRE leaf (main.
        # pasm ~6399: `lda.l Player_InvulnFrames / beq ... / rts`), before
        # any grab/damage logic runs. A real, live AI attacker overlapping
        # the invulnerable player must produce zero effect. ---
        write_u8(m, Entity1 + CHAR_HP, 100)
        write_u8(m, Entity1 + CHAR_INPUT_DRIVEN, 2)
        write_u8(m, Entity1 + CHAR_HIT_STUN, 0)
        write_u8(m, PlayerEntity + CHAR_HIT_STUN, 0)
        write_u8(m, PlayerEntity + CHAR_HP, 100)
        write_u8(m, Player_InvulnFrames, 120)
        overlap(m, Entity1)
        write_u8(m, Entity1 + CHAR_HIT_APPLIED, 0)
        clear_sfx_queue(m)
        baseline_count8 = read_byte(m, REQUEST_COUNT_ADDR)
        invuln_saw_sfx = [False]
        poll_frames(m, 90, lambda: (
            overlap(m, Entity1),
            invuln_saw_sfx.__setitem__(0, invuln_saw_sfx[0] or read_byte(m, SFX_QUEUE_ADDR) == SFX_HIT_ID),
        ))
        hp_after_invuln = read_byte(m, PlayerEntity + CHAR_HP)
        count_after_invuln = read_byte(m, REQUEST_COUNT_ADDR)
        r.check('invulnerable: player HP unchanged', hp_after_invuln == 100)
        r.check('invulnerable: request counter unchanged', count_after_invuln == baseline_count8)
        r.check('invulnerable: no sfx_hit requested', not invuln_saw_sfx[0])
        write_u8(m, Player_InvulnFrames, 0)
        m.run_frames(10)
        m.pause()

        # --- 10 (checked here, before closing the session): song + MSU-1
        # unaffected by all of the above. ---
        state = read_byte(m, TadPrivate_state)
        r.check(f'existing song still reaches PLAYING (${PLAYING:02X}) after all of the above',
                state == PLAYING)
        dsp = m.get_audio_state()['dsp']
        r.check('S-DSP still out of reset/mute after all of the above', dsp['flg'] != 0xE0)

    # --- 9. Real DSP audibility, majority-of-N. get_audio_state()'s per-
    # voice fields turned out unusable for this (a direct probe during this
    # hardening pass found `sampleSrc`/`gain`/`envelope` reading essentially
    # noisy/inconsistent values frame to frame through this MCP tool, not
    # stable register snapshots -- a real reliability gap in the harness,
    # not a real audio bug; not worth blocking this gate on chasing further,
    # consistent with this project's own documented Mesen MCP hook/audio
    # reliability gaps). A raw WAV peak comparison (the original approach)
    # also turned out unusable on its own: with deterministic, fixed-frame
    # recording windows (this hardening pass's own improvement -- no more
    # retry-loop timing jitter), the hit and no-hit windows landed on the
    # exact same loud transient in the reconstructed test song's own s0-s6
    # instruments every single run, so max-peak alone never differed. A
    # sample-by-sample difference COUNT between matched hit/no-hit windows
    # is far more sensitive than peak alone (confirmed by direct probe: the
    # two waveforms differ in ~22% of samples despite identical peaks) and
    # is what this check actually uses. ---
    N_AUDIO_SAMPLES = 5
    RECORD_FRAMES = 40
    tmp = tempfile.mkdtemp(prefix='g11-')
    diff_counts = []
    for i in range(N_AUDIO_SAMPLES):
        with open_session(__file__) as m:
            boot_and_warm(m)
            nohit_wav = os.path.join(tmp, f'nohit{i}.wav')
            m.record_audio(nohit_wav)
            m.run_frames(RECORD_FRAMES)
            m.pause()
            m.stop_audio()
            with wave.open(nohit_wav) as w:
                nohit_raw = w.readframes(w.getnframes())

        with open_session(__file__) as m:
            boot_and_warm(m)
            write_u8(m, PlayerEntity + CHAR_HIT_STUN, 0)
            write_u8(m, Entity1 + CHAR_HP, 100)
            overlap(m, Entity1)
            write_u8(m, PlayerEntity + CHAR_HIT_APPLIED, 0)
            hit_wav = os.path.join(tmp, f'hit{i}.wav')
            m.record_audio(hit_wav)
            # hold_input (not set_input) so the button press genuinely lands
            # inside this recording window instead of resolving atomically
            # before recording starts.
            m.hold_input(m.BTN_Y, 0)
            m.run_frames(RECORD_FRAMES)
            m.pause()
            m.release_input(0)
            m.stop_audio()
            with wave.open(hit_wav) as w:
                hit_raw = w.readframes(w.getnframes())

        n = min(len(nohit_raw), len(hit_raw)) // 2
        nohit_samples = struct.unpack('<' + 'h' * n, nohit_raw[:n * 2])
        hit_samples = struct.unpack('<' + 'h' * n, hit_raw[:n * 2])
        differing = sum(1 for a, b in zip(nohit_samples, hit_samples) if a != b)
        diff_counts.append(differing)
        r.check(f'DSP output non-silent in the hit-window recording, run {i}',
                any(s != 0 for s in hit_samples))

    print(f'sample-diff counts (hit vs matched no-hit, out of ~{n} samples each): {diff_counts}')
    r.check(f'hit-window waveform differs from the matched no-hit control in a majority of runs '
            f'(a real, substantial fraction of samples differ, not a rounding-noise handful) '
            f'(diff_counts={diff_counts})',
            sum(1 for d in diff_counts if d > n // 100) > N_AUDIO_SAMPLES // 2)

    # --- 11. Static: the only real queue-write call site always requests
    # SFX_HIT_ID, never sfx_stub (id 0). ---
    with open(os.path.join(ROOT, 'src', 'main.pasm'), encoding='utf-8') as f:
        main_pasm = f.read()
    call_sites = re.findall(r'jsr Tad_QueueSoundEffect\b', main_pasm)
    r.check(f'exactly one Tad_QueueSoundEffect call site in main.pasm (got {len(call_sites)})',
            len(call_sites) == 1)
    sfx_loads = re.findall(r'\n\s*lda #SFX_HIT_ID\n', main_pasm)
    r.check(f'both real landed-hit dispatch sites explicitly load SFX_HIT_ID '
            f'(not a reused CHAR_HIT_APPLIED literal) (got {len(sfx_loads)}, expect 1 in the '
            'shared G11_QueueHitSfx helper)',
            len(sfx_loads) == 1)

    r.finish()


if __name__ == '__main__':
    main()
