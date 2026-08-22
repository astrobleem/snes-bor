#!/usr/bin/env python3
"""plan_game.md Phase G7 knockdown slice gate: fall/rise (knockdown/getting
up), wired to reproduce OpenBOR's real checkdamagedrop()/set_fall()/
common_lie()/set_rise() state machine (see this slice's plan for the full
sourced derivation from rofl0r/openbor-legacy's openbor.c/openbor.h, and
this project's own real BOR pak data confirming attack1's attack_drop=0 for
all 4 roster characters).

Three checks, matching the plan's own Verification section:

  1. FATAL path -- reachable today with zero forcing (health<=0 alone enters
     the fall branch in real OpenBOR, independent of accumulated knockdown
     force). A killing blow must play the real fall animation (not the old
     instant-freeze), blink during the death window, then park permanently
     -- and Character_HitApply must stay a no-op against it afterward.

  2. NON-FATAL path -- real gameplay can't reach this today (attack1's own
     real attack_drop is 0 for every roster character, confirmed against
     the source pak this session), so CHAR_KNOCKDOWN_COUNT is forced
     negative directly via WRAM write, mirroring game_g7_invuln.py's own
     precedent of forcing Entity1_InvulnFrames the same way -- not an
     in-game trigger, never reachable through real combat as it ships.
     Must fall, then RECOVER via the rise animation back to idle, with HP
     reduced only by the hit's own damage, not by the knockdown itself.

  3. REGRESSION -- ordinary real combat (today's only move, attack_drop=0)
     must never accumulate CHAR_KNOCKDOWN_COUNT negative and must never
     enter the fall reaction on a non-fatal hit.

Entity 1 (RALF) is the target throughout; entities 2/3 are neutralized
(HP=0) to avoid unrelated background AI combat perturbing the target or the
streaming budget, same reasoning as game_g6_hud.py/game_g7_invuln.py.

**Timing note (mesen_set_input_wall_clock project memory)**: attacks are
thrown with a single minimal `set_input(BTN_Y, 1)` (one edge-triggered
press) followed by frame-exact `run_frames(1)` polling, same shape
game_g7_invuln.py already established -- `set_input`'s own `frames` argument
is wall-clock, not frame-exact, and would blow through short windows.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_FRAME_INDEX = pasm_constant('CHAR_FRAME_INDEX')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_HP_PER_HIT = pasm_constant('CHAR_HP_PER_HIT')
CHAR_KNOCKDOWN_COUNT = pasm_constant('CHAR_KNOCKDOWN_COUNT')
CHAR_KNOCKDOWN_TIMER = pasm_constant('CHAR_KNOCKDOWN_TIMER')
CHAR_FALL_STATE_TIMER = pasm_constant('CHAR_FALL_STATE_TIMER')
CHAR_SELECTED_FALL = pasm_constant('CHAR_SELECTED_FALL')
CHAR_SELECTED_RISE = pasm_constant('CHAR_SELECTED_RISE')
KNOCKDOWN_REGEN_FRAMES = pasm_constant('KNOCKDOWN_REGEN_FRAMES')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')

GS_PATH = 'src/core/game_state.pasm'
Entity1_InvulnFrames = pasm_constant_in(GS_PATH, 'Entity1_InvulnFrames')

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
PlayerEntity = ENTITY_BASES[0]
Entity1 = ENTITY_BASES[1]
Entity2 = ENTITY_BASES[2]
Entity3 = ENTITY_BASES[3]

READ_LEN = 64  # covers every CHAR_* offset used here (CHAR_ZP_LEN=49)
DEAD_OAM_Y = 0xF0


def entity_block(m, base):
    return read_block(m, base, READ_LEN)


def entity1_state(m):
    blk = entity_block(m, Entity1)
    hp = blk[CHAR_HP]
    selected = blk[CHAR_SELECTED]
    frame_idx = blk[CHAR_FRAME_INDEX]
    fall_timer = blk[CHAR_FALL_STATE_TIMER]
    kd_count = blk[CHAR_KNOCKDOWN_COUNT]
    if kd_count >= 0x80:
        kd_count -= 0x100  # signed
    return hp, selected, frame_idx, fall_timer, kd_count


def oam_slot(m, slot):
    block = read_block(m, 0, 32, mem_type='snesSpriteRam')
    off = slot * 4
    return block[off], block[off + 1]  # X, Y


def overlap_entity1_with_player(m):
    px = entity_block(m, PlayerEntity)
    x = px[CHAR_POS_X] | (px[CHAR_POS_X + 1] << 8)
    y = px[CHAR_POS_Y]
    m.write_u16(Entity1 + CHAR_POS_X, x)
    m.write_u8(Entity1 + CHAR_POS_Y, y)


def throw_one_hit(m):
    # Same reset-before-throw as game_g7_invuln.py's press_and_poll_until_
    # landed: without clearing these, a still-decaying post-hit invuln
    # window from earlier combat (the 300-frame warm-up, or this gate's own
    # prior checks) silently swallows the hit via Character_HitApply_
    # VsEntity1's own invuln early-out -- HP/CHAR_SELECTED then never move
    # and every downstream assertion times out looking like a real bug.
    m.write_u8(Entity1 + CHAR_HIT_STUN, 0)
    m.write_u8(Entity1_InvulnFrames, 0)
    # Found by direct diagnostic: the PLAYER itself can still be mid-
    # hitstun from real background AI combat during the 300-frame warm-up
    # (entities 2/3 aren't neutralized until after it) -- a stunned player
    # can't act, so a single-frame set_input(BTN_Y) edge is silently lost
    # if it lands mid-stun, and every downstream poll then times out with
    # nothing having moved. Clear the player's own stun too, immediately
    # before every throw.
    m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)
    overlap_entity1_with_player(m)
    m.set_input(m.BTN_Y, 1)


def poll_until(m, predicate, max_frames):
    """Frame-step until predicate(entity1_state(m)) is true or max_frames
    elapses. Returns (ok, last_state)."""
    state = entity1_state(m)
    for _ in range(max_frames):
        if predicate(state):
            return True, state
        m.run_frames(1)
        m.pause()
        state = entity1_state(m)
    return predicate(state), state


def main():
    r = Reporter('G7-KNOCKDOWN', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()

        # Neutralize entities 2/3 -- same reasoning as game_g6_hud.py/
        # game_g7_invuln.py: real background AI combat is already underway
        # by frame 300 and would otherwise perturb entity 1 or contend for
        # the shared streaming budget.
        m.write_u8(Entity2 + CHAR_HP, 0)
        m.write_u8(Entity3 + CHAR_HP, 0)

        # ================================================================
        # 1. FATAL path -- reachable today, zero forcing.
        # ================================================================
        m.write_u8(Entity1 + CHAR_SELECTED, 0)
        m.write_u8(Entity1 + CHAR_FALL_STATE_TIMER, 0)
        m.write_u8(Entity1 + CHAR_KNOCKDOWN_COUNT, 0)
        m.write_u8(Entity1 + CHAR_KNOCKDOWN_TIMER, 0)
        m.write_u8(Entity1 + CHAR_HP, CHAR_HP_PER_HIT)  # one hit kills it
        throw_one_hit(m)

        ok, (hp, selected, frame_idx, fall_timer, kd_count) = poll_until(
            m, lambda s: s[0] == 0, max_frames=40)
        print(f'fatal hit landed: hp={hp} selected={selected} frame_idx={frame_idx}')
        r.check('fatal hit actually landed (HP reached 0)', ok and hp == 0)
        r.check('fatal hit entered the real fall animation (CHAR_SELECTED==FALL), '
                'not an instant freeze', selected == CHAR_SELECTED_FALL)

        # Fall animation must actually progress (CHAR_FRAME_INDEX advances)
        # before settling into the hold/blink sub-phase (CHAR_FALL_STATE_
        # TIMER goes nonzero). Sample a few frames to see movement.
        frame_samples = []
        for _ in range(8):
            m.run_frames(3)
            m.pause()
            frame_samples.append(entity1_state(m)[2])
        print(f'fall CHAR_FRAME_INDEX samples: {frame_samples}')
        r.check('fall animation frame index actually advances (not parked from frame 1)',
                len(set(frame_samples)) > 1)

        # Wait for the hold/blink sub-phase to start (CHAR_FALL_STATE_TIMER
        # goes nonzero -- entered DEATH_BLINK_FRAMES countdown since HP==0).
        ok, (hp, selected, frame_idx, fall_timer, kd_count) = poll_until(
            m, lambda s: s[3] != 0, max_frames=120)
        print(f'entered hold/blink phase: fall_timer={fall_timer}')
        r.check('fall animation finished and entered the death-blink hold '
                '(CHAR_FALL_STATE_TIMER nonzero)', ok)

        # Sample OAM Y across the blink window -- must see BOTH hidden
        # ($F0) and visible values, proving it's actually blinking rather
        # than being stuck hidden or stuck visible.
        blink_ys = []
        for _ in range(30):
            m.run_frames(2)
            m.pause()
            _, y = oam_slot(m, 1)
            blink_ys.append(y)
        hidden_seen = any(y == DEAD_OAM_Y for y in blink_ys)
        visible_seen = any(y != DEAD_OAM_Y for y in blink_ys)
        print(f'blink-window OAM Y samples: {blink_ys}')
        r.check('death blink actually toggles OAM visibility (both hidden and visible seen)',
                hidden_seen and visible_seen)

        # Wait for the terminal parked state (CHAR_FALL_STATE_TIMER == $FF).
        ok, (hp, selected, frame_idx, fall_timer, kd_count) = poll_until(
            m, lambda s: s[3] == 0xFF, max_frames=140)
        print(f'reached terminal state: fall_timer={fall_timer} selected={selected}')
        r.check('death-blink window ends in the terminal parked state '
                '(CHAR_FALL_STATE_TIMER==$FF)', ok)

        frame_idx_before = entity1_state(m)[2]
        m.run_frames(30)
        m.pause()
        _, oy_terminal = oam_slot(m, 1)
        frame_idx_after = entity1_state(m)[2]
        print(f'terminal hold: OAM Y={oy_terminal}, frame_idx {frame_idx_before} -> {frame_idx_after}')
        r.check('terminal state stays permanently hidden (OAM Y==$F0)', oy_terminal == DEAD_OAM_Y)
        r.check('terminal state stops streaming (CHAR_FRAME_INDEX no longer advances)',
                frame_idx_after == frame_idx_before)

        # Character_HitApply must stay a no-op against a dead, parked
        # entity -- throw another real hit and confirm nothing changes.
        throw_one_hit(m)
        m.run_frames(10)
        m.pause()
        hp_after, selected_after, _, fall_timer_after, _ = entity1_state(m)
        print(f'post-mortem hit: hp={hp_after} selected={selected_after} fall_timer={fall_timer_after}')
        r.check('Character_HitApply is a no-op against a dead, parked entity',
                hp_after == 0 and selected_after == CHAR_SELECTED_FALL and fall_timer_after == 0xFF)

        # ================================================================
        # 2. NON-FATAL path -- test-forced (real combat can't reach this;
        # attack1's own attack_drop is authored 0 for every roster
        # character -- see this slice's plan). Force CHAR_KNOCKDOWN_TIMER
        # nonzero too, so ApplyDamage's own regen-if-expired step doesn't
        # reset the forced count back to CHAR_KNOCKDOWN_MAX before the hit
        # that's supposed to observe it lands.
        # ================================================================
        m.write_u8(Entity1 + CHAR_SELECTED, 0)
        m.write_u8(Entity1 + CHAR_FALL_STATE_TIMER, 0)
        m.write_u8(Entity1 + CHAR_HP, CHAR_HP_MAX)
        m.write_u8(Entity1 + CHAR_KNOCKDOWN_COUNT, 0xFF)  # -1, test-forced
        m.write_u8(Entity1 + CHAR_KNOCKDOWN_TIMER, 30)    # not expired
        throw_one_hit(m)

        ok, (hp, selected, frame_idx, fall_timer, kd_count) = poll_until(
            m, lambda s: s[1] == CHAR_SELECTED_FALL, max_frames=40)
        print(f'non-fatal knockdown: hp={hp} selected={selected} kd_count={kd_count}')
        r.check('test-forced negative knockdown count enters the fall reaction '
                'on a non-fatal hit', ok)
        hp_after_hit = hp
        r.check('non-fatal knockdown HP loss is exactly one hit worth (CHAR_HP_PER_HIT)',
                hp_after_hit == CHAR_HP_MAX - CHAR_HP_PER_HIT)

        ok, (hp, selected, frame_idx, fall_timer, kd_count) = poll_until(
            m, lambda s: s[1] == CHAR_SELECTED_RISE, max_frames=120)
        print(f'transitioned to rise: selected={selected} hp={hp}')
        r.check('a non-fatal knockdown RECOVERS -- transitions to the rise animation, '
                'not a permanent park', ok)
        r.check('HP unaffected by the fall/rise transition itself', hp == hp_after_hit)

        ok, (hp, selected, frame_idx, fall_timer, kd_count) = poll_until(
            m, lambda s: s[1] == 0, max_frames=120)
        print(f'rise finished, back to idle: selected={selected} hp={hp}')
        r.check('rise animation completes and returns to normal idle control (CHAR_SELECTED==0)',
                ok)
        r.check('HP still unaffected after the full fall->rise recovery cycle',
                hp == hp_after_hit)

        # ================================================================
        # 3. REGRESSION -- ordinary real combat (attack_drop=0, authored
        # data) must never accumulate knockdown or trigger a non-fatal
        # fall via accumulation.
        # ================================================================
        m.write_u8(Entity1 + CHAR_SELECTED, 0)
        m.write_u8(Entity1 + CHAR_FALL_STATE_TIMER, 0)
        m.write_u8(Entity1 + CHAR_HP, CHAR_HP_MAX)
        m.write_u8(Entity1 + CHAR_KNOCKDOWN_COUNT, 0)
        m.write_u8(Entity1 + CHAR_KNOCKDOWN_TIMER, 0)

        selected_during = []
        kd_during = []
        for _ in range(3):
            throw_one_hit(m)
            hp_before = entity1_state(m)[0]
            ok, (hp, selected, frame_idx, fall_timer, kd_count) = poll_until(
                m, lambda s, hb=hp_before: s[0] != hb, max_frames=40)
            selected_during.append(selected)
            kd_during.append(kd_count)
            # let CHAR_HIT_STUN/InvulnFrames clear before the next attempt
            m.run_frames(40)
            m.pause()

        print(f'regression: CHAR_SELECTED samples={selected_during} kd_count samples={kd_during}')
        r.check('ordinary real combat (attack_drop=0) never enters the fall reaction',
                all(s != CHAR_SELECTED_FALL for s in selected_during))
        r.check('ordinary real combat never drives CHAR_KNOCKDOWN_COUNT negative',
                all(k >= 0 for k in kd_during))

        # No cross-entity bleed.
        hp2 = read_block(m, Entity2 + CHAR_HP, 32)[0]
        hp3 = read_block(m, Entity3 + CHAR_HP, 32)[0]
        print(f'entities 2/3 HP: {hp2}, {hp3} (expected 0, 0)')
        r.check('entity 2 unaffected by entity 1 knockdown testing', hp2 == 0)
        r.check('entity 3 unaffected by entity 1 knockdown testing', hp3 == 0)

    r.finish()


if __name__ == '__main__':
    main()
