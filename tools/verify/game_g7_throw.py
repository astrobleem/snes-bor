#!/usr/bin/env python3
"""plan_game.md Phase G7: real throw (second slice after grab mutual-lock).

Background: game_g7_grab.py's own docstring explicitly deferred throw
("auto-release only -- no throw"). This slice adds it, sourced from real
OpenBOR (DCurrent/openbor, engine/openbor.c): common_throw releases the
mutual link and calls toss(), which sets the victim's airborne velocity
directly (IDENTICAL Q8.8 physics to the real jump slice's own tryjump()/
check_gravity() -- see core/jump.pasm's header) and always results in an
airborne launch, never a mere stun, regardless of the knockdown counter an
ordinary hit would consult. Landing enters the SAME fall/rise knockdown
reaction a landed hit produces (no distinct "thrown" art in any roster pak
-- reuses the existing Anim_Play_Fall pipeline unchanged).

Grabber is always the player (JOE, the only roster member with a real
`grab` role -- same restriction game_g7_grab.py's own gate already
establishes and checks). Victim is always an AI slot (entity 1 here, same
choice game_g7_grab.py makes).

Every check below inspects real hardware state (WRAM struct fields, real
OAM via snesSpriteRam) per CLAUDE.md's standing rule -- never a bare
"ThrowState == 1"-shaped internal-flag check:

1. Altitude/gravity: CHAR_THROW_ZPOS/ZVEL sampled every real frame while
   airborne are compared against a from-scratch simulation of the SAME
   integration formula game_g7_jump.py already verifies for the player
   (JUMP_INITIAL_VEL/JUMP_GRAVITY, position+=velocity/velocity+=gravity) --
   proving the victim's airborne motion is the real jump model, not a
   parallel invented one.
2. Landing: victim's CHAR_SELECTED reaches CHAR_SELECTED_FALL (the real
   knockdown/rise path, not a synthetic "thrown-done" state) within a
   bounded frame count, and its Z cells reset to 0.
3. Attacker (player) returns to a valid controllable state: CHAR_SELECTED
   settles at idle/walk (not stuck in an attack/throw-only state), and a
   held dpad genuinely moves it afterward -- proves real control, not just
   a flag flip.
4. Neither entity retains a stale grab link: both CHAR_GRAB_TARGET (player)
   and CHAR_GRABBED_BY (victim) read back $FF immediately after the throw.
5. Killing via throw: a separate low-HP victim, thrown with damage enough
   to reach HP==0, hides (real OAM Y==$F0 dead-hide sentinel) instead of
   getting an airborne launch -- and does NOT crash/corrupt any other
   entity's state (checked directly, not inferred).
6. Depth sort stays ground-based during the throw: CHAR_POS_Y (the real
   depth-sort key, core/depth_sort.pasm) is read every sampled airborne
   frame and asserted UNCHANGED throughout -- same technique game_g7_
   depth_sort.py's own jump-vs-depth-sort section already uses, extended
   to throw instead of voluntary jump.
7. All 4 entity slots remain valid throughout: no OOP kill/GC compaction
   occurs (this project's fixed-address EntityN_Base scheme would break
   under real GC -- see phase11_damage_system_softkill project memory) --
   checked by confirming entities 0/2/3's own struct fields stay sane
   (readable, no wraparound/corruption) across the whole sequence.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_SELECTED_FALL = pasm_constant('CHAR_SELECTED_FALL')
CHAR_SELECTED_THROWN = pasm_constant('CHAR_SELECTED_THROWN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_HP_PER_HIT = pasm_constant('CHAR_HP_PER_HIT')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_HIT_APPLIED = pasm_constant('CHAR_HIT_APPLIED')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_ATTACK2_IS_GRAB = pasm_constant('CHAR_ATTACK2_IS_GRAB')
CHAR_GRAB_TARGET = pasm_constant('CHAR_GRAB_TARGET')
CHAR_GRABBED_BY = pasm_constant('CHAR_GRABBED_BY')
CHAR_GRAB_TIMER = pasm_constant('CHAR_GRAB_TIMER')
CHAR_THROW_ZPOS = pasm_constant('CHAR_THROW_ZPOS')
CHAR_THROW_ZVEL = pasm_constant('CHAR_THROW_ZVEL')
CHAR_FRAME_INDEX = pasm_constant('CHAR_FRAME_INDEX')
CHAR_FALL_STATE_TIMER = pasm_constant('CHAR_FALL_STATE_TIMER')

JUMP_INITIAL_VEL = pasm_constant('JUMP_INITIAL_VEL')
JUMP_GRAVITY_RAW = pasm_constant('JUMP_GRAVITY')
JUMP_GRAVITY = JUMP_GRAVITY_RAW - 0x10000 if JUMP_GRAVITY_RAW & 0x8000 else JUMP_GRAVITY_RAW

GS_PATH = 'src/core/game_state.pasm'
Entity1_InvulnFrames = pasm_constant_in(GS_PATH, 'Entity1_InvulnFrames')
Entity2_InvulnFrames = pasm_constant_in(GS_PATH, 'Entity2_InvulnFrames')
Entity3_InvulnFrames = pasm_constant_in(GS_PATH, 'Entity3_InvulnFrames')

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
PlayerEntity = ENTITY_BASES[0]
Entity1 = ENTITY_BASES[1]
Entity2 = ENTITY_BASES[2]
Entity3 = ENTITY_BASES[3]
Entity1_ByteOff = CHAR_ZP_LEN

CharSelect_Index = 0x7E53B6
CharSelect_Loaded = 0x7E53B8
Screen_PosX = 0x7E1601

READ_LEN = 80  # covers every CHAR_* offset used here (CHAR_ZP_LEN=71)


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def entity_block(m, base):
    return read_block(m, base, READ_LEN)


def pos_x(blk):
    return blk[CHAR_POS_X] | (blk[CHAR_POS_X + 1] << 8)


def throw_zpos(blk):
    return s16(blk[CHAR_THROW_ZPOS] | (blk[CHAR_THROW_ZPOS + 1] << 8))


def throw_zvel(blk):
    return s16(blk[CHAR_THROW_ZVEL] | (blk[CHAR_THROW_ZVEL + 1] << 8))


def read_u8(m, addr):
    return read_block(m, addr, 32)[0]


def read_i16(m, addr):
    b = read_block(m, addr, 32)
    v = b[0] | (b[1] << 8)
    return v - 0x10000 if v & 0x8000 else v


def press_select(m):
    m.set_input(m.BTN_SELECT, 10)
    m.run_frames(40)
    m.pause()


def overlap_entity_with_player(m, entity_base, x=None, y=None):
    px = entity_block(m, PlayerEntity)
    x = pos_x(px) if x is None else x
    y = px[CHAR_POS_Y] if y is None else y
    m.write_u16(entity_base + CHAR_POS_X, x)
    m.write_u8(entity_base + CHAR_POS_Y, y)
    return x, y


def reset_combat_state(m):
    m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
    m.write_u8(PlayerEntity + CHAR_HIT_APPLIED, 0)
    m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)
    m.write_u8(PlayerEntity + CHAR_GRAB_TARGET, 0xFF)
    for base, invuln in ((Entity1, Entity1_InvulnFrames),
                         (Entity2, Entity2_InvulnFrames),
                         (Entity3, Entity3_InvulnFrames)):
        m.write_u8(base + CHAR_SELECTED, 0)
        m.write_u8(base + CHAR_HIT_STUN, 0)
        m.write_u8(base + CHAR_GRABBED_BY, 0xFF)
        m.write_u8(invuln, 0)
        m.write_u8(base + CHAR_HP, CHAR_HP_MAX)
        m.write_u16(base + CHAR_THROW_ZPOS, 0)
        m.write_u16(base + CHAR_THROW_ZVEL, 0)


def poll_until(m, predicate, max_frames):
    for _ in range(max_frames):
        if predicate():
            return True
        m.run_frames(1)
        m.pause()
    return predicate()


def release_gap(m, frames=10):
    """m.set_input(btn, N) is wall-clock/lower-bound, not frame-exact
    (memory mesen_set_input_wall_clock) -- two back-to-back set_input calls
    for the SAME button with no gap between them were observed to produce
    only ONE real edge-trigger event (the emulator never sees the button
    genuinely release in between), silently swallowing a second, distinct
    press meant to trigger throw right after the press that established the
    grab. A few real frames with no input forces a genuine release first."""
    m.run_frames(frames)
    m.pause()


def establish_grab(m, victim_base):
    """Real X-press grab-init, same technique game_g7_grab.py already
    verifies -- not a synthetic WRAM write of the link fields.

    Freezes the victim's own CHAR_INPUT_DRIVEN to 0 (static) for the
    duration of the attempt -- TryGrab's real conditions (Character_
    HitApply__TryGrab, vm_native_engine.pasm) never check the victim's
    own input mode, only the attacker's CHAR_ATTACK2_IS_GRAB/ATTACK_
    VARIANT and both sides' link fields, so this doesn't change what's
    under test. Needed because a SECOND grab attempt (e.g. after a prior
    throw's fall/rise/AI-resume cycle already ran) can land with the
    victim's own AI-seek already primed to attack the instant it's
    snapped onto the player -- its own attack can land on the PLAYER
    first and interrupt the intended grab-establishing swing. Restored to
    AI (2) by the caller wherever it matters after the attempt."""
    m.write_u8(victim_base + CHAR_INPUT_DRIVEN, 0)
    overlap_entity_with_player(m, victim_base)
    m.set_input(m.BTN_X, 1)
    linked = poll_until(
        m, lambda: read_u8(m, PlayerEntity + CHAR_GRAB_TARGET) != 0xFF, max_frames=30)
    return linked


def screen_pos_x(m):
    return read_i16(m, Screen_PosX) & 0xFFFF


def oam_slot_for_entity(m, world_x, cam):
    """Actor depth-sort slice: identify a real OAM sprite by its expected
    on-screen X (same technique every post-depth-sort gate in this project
    now uses -- never assume OAM slot N == entity N)."""
    expected_x = (world_x - cam) & 0xFF
    oam = read_block(m, 0, 32, mem_type='snesSpriteRam')
    for slot in range(4):
        if oam[slot * 4] == expected_x:
            return slot, oam[slot * 4 + 1]
    return None, None


def main():
    r = Reporter('G7-THROW', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()

        m.write_u8(Entity2 + CHAR_HP, 0)
        m.write_u8(Entity3 + CHAR_HP, 0)

        # --- Select to JOE (roster slot 2), same as game_g7_grab.py. ---
        press_select(m)
        press_select(m)
        idx = read_u8(m, CharSelect_Index)
        loaded = read_u8(m, CharSelect_Loaded)
        r.check('roster selected to JOE (index 2)', idx == 2)
        r.check('CharSelect_Loaded==1 after reselect', loaded == 1)
        joe_is_grab = read_u8(m, PlayerEntity + CHAR_ATTACK2_IS_GRAB)
        r.check('JOE CHAR_ATTACK2_IS_GRAB==1 (real converted grab role)', joe_is_grab == 1)

        # ====================================================================
        # Non-lethal throw: establish grab on entity1, then throw it.
        # ====================================================================
        reset_combat_state(m)
        px_before, py_before = overlap_entity_with_player(m, Entity1)
        linked = establish_grab(m, Entity1)
        r.check('grab established on entity1 before throw test', linked)
        # Restore real AI mode now that the link is confirmed -- TryGrab
        # itself never depended on it (see establish_grab's own comment),
        # but the LANDING transition (real fall/rise pipeline) and the
        # dead-hide gate both key off CHAR_INPUT_DRIVEN>=2.
        m.write_u8(Entity1 + CHAR_INPUT_DRIVEN, 2)

        hp_before_throw = entity_block(m, Entity1)[CHAR_HP]
        cam = screen_pos_x(m)

        # Throw: same X press that would re-trigger attack2 normally, but
        # while grabbing -- Jump_PlayerInputGate routes it to
        # Character_Grab_Throw instead (real common_throw semantics).
        release_gap(m)
        m.set_input(m.BTN_X, 1)
        thrown = poll_until(
            m, lambda: entity_block(m, Entity1)[CHAR_SELECTED] == CHAR_SELECTED_THROWN,
            max_frames=30)
        r.check('X press while grabbing launches the victim into CHAR_SELECTED_THROWN',
                thrown)

        # --- 4. Neither side retains a stale grab link, immediately. ---
        player_grab_target = read_u8(m, PlayerEntity + CHAR_GRAB_TARGET)
        victim_grabbed_by = entity_block(m, Entity1)[CHAR_GRABBED_BY]
        print(f'post-throw links: player.CHAR_GRAB_TARGET={player_grab_target} '
              f'entity1.CHAR_GRABBED_BY={victim_grabbed_by}')
        r.check('player CHAR_GRAB_TARGET released ($FF) immediately after throw',
                player_grab_target == 0xFF)
        r.check('entity1 CHAR_GRABBED_BY released ($FF) immediately after throw',
                victim_grabbed_by == 0xFF)

        # --- 3. Attacker (player) returned to a valid controllable state
        # immediately -- CHAR_SELECTED settled at idle, not stuck. ---
        player_selected = read_u8(m, PlayerEntity + CHAR_SELECTED)
        r.check('player CHAR_SELECTED is idle(0) right after throwing (no unique throw-swing state)',
                player_selected == 0)

        # --- 1. Altitude/gravity: real toss()-sourced Q8.8 integration,
        # sampled every frame while airborne, compared against a from-
        # scratch simulation of the SAME formula (position+=velocity,
        # velocity+=gravity), starting from the real observed arm values
        # (not assumed -- set_input's wall-clock sleep makes the literal
        # arm frame unobservable, same reasoning game_g7_jump.py's own
        # gate documents for the player's jump). Also re-pins entities 2/3
        # and confirms CHAR_POS_Y (ground/depth key) never changes for
        # ANY entity while sampling -- satisfies criterion 6 (depth sort
        # stays ground-based) across the whole airborne window.
        zpos_samples = []
        zvel_samples = []
        ground_y_baseline = [entity_block(m, b)[CHAR_POS_Y] for b in ENTITY_BASES]
        depth_orders = []
        max_zpos = 0
        for _ in range(60):
            blk = entity_block(m, Entity1)
            sel = blk[CHAR_SELECTED]
            if sel != CHAR_SELECTED_THROWN:
                break
            zp, zv = throw_zpos(blk), throw_zvel(blk)
            zpos_samples.append(zp)
            zvel_samples.append(zv)
            max_zpos = max(max_zpos, zp)

            ground_y_now = [entity_block(m, b)[CHAR_POS_Y] for b in ENTITY_BASES]
            if ground_y_now != ground_y_baseline:
                raise AssertionError(
                    f'CHAR_POS_Y (depth key) perturbed during throw: '
                    f'{ground_y_now} != {ground_y_baseline}')

            if zp > 0:
                world_xs = [entity_block(m, b)[CHAR_POS_X] | (entity_block(m, b)[CHAR_POS_X + 1] << 8)
                            for b in ENTITY_BASES]
                cam_now = screen_pos_x(m)
                slot1, oamy1 = oam_slot_for_entity(m, world_xs[1], cam_now)
                if slot1 is not None:
                    depth_orders.append((oamy1, slot1))

            m.run_frames(1)
            m.pause()

        print(f'zpos samples: {zpos_samples[:10]}')
        r.check('victim actually left the ground during the throw (ZPos > 0 observed)',
                max_zpos > 0)
        r.check('CHAR_POS_Y (depth-sort ground key) never changed for any entity while airborne',
                True)  # the loop above raises on any violation

        if len(zpos_samples) >= 2:
            # Reconstruct the arm tick count from the first observed sample
            # against the real formula, then verify every subsequent sample
            # matches the same simulation continued -- same technique
            # game_g7_jump.py's own gate already uses for the player.
            def simulate(n):
                zp, zv = 0, JUMP_INITIAL_VEL
                for _ in range(n):
                    zp = s16((zp + zv) & 0xFFFF)
                    zv = s16((zv + JUMP_GRAVITY) & 0xFFFF)
                return zp, zv

            found_tick = None
            for tick in range(200):
                zp, zv = simulate(tick)
                if zp == zpos_samples[0] and zv == zvel_samples[0]:
                    found_tick = tick
                    break
            r.check('first sampled (ZPos, ZVel) exactly matches the real toss()/check_gravity() '
                    'integration at some tick count (identical formula to jump.pasm)',
                    found_tick is not None)
            if found_tick is not None:
                # m.run_frames(1) is a wall-clock lower bound, not an exact
                # frame count (memory mesen_set_input_wall_clock) -- a
                # sampled tick can occasionally repeat (the same real frame
                # read twice) rather than always advancing by exactly 1.
                # Search forward from the last matched tick, allowing a
                # small skip either way, rather than assuming a rigid
                # tick-per-sample lockstep -- still requires an EXACT match
                # against the real formula at every sample, just not a
                # fixed stride.
                all_match = True
                tick = found_tick
                for zp_obs, zv_obs in zip(zpos_samples, zvel_samples):
                    match = None
                    for candidate in range(tick, tick + 4):
                        if simulate(candidate) == (zp_obs, zv_obs):
                            match = candidate
                            break
                    if match is None:
                        all_match = False
                        break
                    tick = match
                r.check('every subsequent sample continues to match the same simulation '
                        '(real gravity integration, not a different/invented curve)', all_match)

        # --- 2. Landing: victim's CHAR_SELECTED reaches FALL, Z cells 0. ---
        landed = poll_until(
            m, lambda: entity_block(m, Entity1)[CHAR_SELECTED] == CHAR_SELECTED_FALL,
            max_frames=120)
        blk = entity_block(m, Entity1)
        print(f'post-landing: CHAR_SELECTED={blk[CHAR_SELECTED]} '
              f'ZPos={throw_zpos(blk)} ZVel={throw_zvel(blk)}')
        r.check('victim lands into CHAR_SELECTED_FALL (real knockdown/rise path) '
                'within a bounded frame count', landed)
        r.check('CHAR_THROW_ZPOS resets to 0 on landing', throw_zpos(blk) == 0)
        r.check('CHAR_THROW_ZVEL resets to 0 on landing', throw_zvel(blk) == 0)

        # Let the existing fall/rise pipeline (already gated by
        # game_g7_knockdown.py) run to completion -- confirm it actually
        # advances (CHAR_FALL_STATE_TIMER changes), proving the landing
        # transition wired into a REAL, live state machine, not a dead end.
        # game_g7_knockdown.py's own gate polls up to 120 frames for this
        # same transition (frames 0..CHAR_FALL_FCOUNT-1 play first, at the
        # normal per-entity Msu1 streaming budget, before the timer itself
        # goes nonzero) -- match that budget rather than a short fixed
        # sample window.
        timer_samples = []
        advanced = poll_until(
            m, lambda: (timer_samples.append(entity_block(m, Entity1)[CHAR_FALL_STATE_TIMER])
                        or len(set(timer_samples)) > 1),
            max_frames=120)
        print(f'CHAR_FALL_STATE_TIMER samples: {timer_samples[:15]}...')
        r.check('CHAR_FALL_STATE_TIMER genuinely advances after landing (real fall pipeline, not stuck)',
                advanced)

        # --- 3 (continued). Attacker remains controllable after the fact --
        # a held dpad genuinely moves it, not just a flag reading idle.
        # LEFT, not RIGHT -- this level's spawn table triggers new waves on
        # forward (rightward) world-X progress; walking left keeps this
        # check from wandering into a new spawn trigger, which was observed
        # to respawn a fresh full-HP enemy into entity1's slot (its own
        # fall pipeline had already reached the terminal dead-hide state by
        # this point) and corrupt the lethal-throw section further below --
        # unrelated to throw itself, a pre-existing background system this
        # gate must stay clear of, same reasoning phase11_damage.py/
        # game_g7_grab.py already apply elsewhere in this project. ---
        reset_combat_state(m)
        px_pre_walk = pos_x(entity_block(m, PlayerEntity))
        for _ in range(10):
            m.set_input(m.BTN_LEFT, 1)
            m.pause()
        px_post_walk = pos_x(entity_block(m, PlayerEntity))
        print(f'player walk after throw: {px_pre_walk} -> {px_post_walk}')
        r.check('player genuinely moves under dpad control after throwing (real control, not stuck)',
                px_post_walk != px_pre_walk)

        # --- 7. All 4 entity slots remain valid (no OOP kill/GC compaction
        # -- fixed-address EntityN_Base scheme intact) throughout the whole
        # sequence above. ---
        for i, base in enumerate(ENTITY_BASES):
            blk = entity_block(m, base)
            hp = blk[CHAR_HP]
            indriven = blk[CHAR_INPUT_DRIVEN]
            r.check(f'entity {i} struct still readable/sane after throw sequence '
                     f'(HP={hp} <= {CHAR_HP_MAX}, CHAR_INPUT_DRIVEN={indriven} <= 3)',
                    hp <= CHAR_HP_MAX and indriven <= 3)

        # ====================================================================
        # 5. Killing via throw: entity1's HP set low enough that the throw's
        # own damage step brings it to exactly 0 -- must hide (real OAM
        # dead-hide), release links, and NOT corrupt any other entity.
        # ====================================================================
        reset_combat_state(m)
        m.write_u8(Entity1 + CHAR_HP, CHAR_HP_PER_HIT)  # exactly one hit from 0
        overlap_entity_with_player(m, Entity1)
        linked2 = establish_grab(m, Entity1)
        r.check('grab re-established for the lethal-throw test', linked2)
        m.write_u8(Entity1 + CHAR_INPUT_DRIVEN, 2)  # restore AI mode -- dead-hide gate needs it

        release_gap(m)
        # Re-pin HP and position immediately after the gap, right before
        # pressing the throw button -- the first (non-lethal) throw above
        # ran its victim's real fall/rise pipeline all the way to its
        # terminal blink-hide state earlier in this same session, and
        # core/spawn.pasm's own per-frame Spawn_Play can respawn a fresh
        # full-HP enemy into that now-"empty" slot during release_gap's
        # idle frames -- observed the hard way as CHAR_HP reading back
        # CHAR_HP_MAX (a real new spawn) instead of the low value this
        # section just wrote, unrelated to throw itself. Re-asserting both
        # right before the press keeps this section's own precondition
        # solid regardless of what the level's spawn system did meanwhile.
        m.write_u8(Entity1 + CHAR_HP, CHAR_HP_PER_HIT)
        overlap_entity_with_player(m, Entity1)

        m.set_input(m.BTN_X, 1)
        killed = poll_until(
            m, lambda: entity_block(m, Entity1)[CHAR_HP] == 0, max_frames=30)
        r.check('lethal throw brings victim CHAR_HP to exactly 0', killed)

        m.run_frames(5)
        m.pause()
        blk_dead = entity_block(m, Entity1)
        print(f'post-lethal-throw: HP={blk_dead[CHAR_HP]} CHAR_SELECTED={blk_dead[CHAR_SELECTED]} '
              f'CHAR_GRABBED_BY={blk_dead[CHAR_GRABBED_BY]} '
              f'player.CHAR_GRAB_TARGET={read_u8(m, PlayerEntity + CHAR_GRAB_TARGET)}')
        r.check('killed victim never entered CHAR_SELECTED_THROWN (no airborne launch for a kill)',
                blk_dead[CHAR_SELECTED] != CHAR_SELECTED_THROWN)
        r.check('killed victim CHAR_GRABBED_BY released ($FF)', blk_dead[CHAR_GRABBED_BY] == 0xFF)
        r.check('player CHAR_GRAB_TARGET released ($FF) after a killing throw',
                read_u8(m, PlayerEntity + CHAR_GRAB_TARGET) == 0xFF)

        # A killing hit still runs the real fall sequence to completion
        # before the dead-hide blink gate takes over (Anim_Play__not_dead's
        # own comment: "a freshly-killed entity must still run its fall
        # sequence instead of freezing instantly") -- wait for the terminal
        # parked state (CHAR_FALL_STATE_TIMER==$FF), same budget game_g7_
        # knockdown.py's own gate already uses for this exact transition,
        # before expecting the real OAM hide to have taken effect.
        poll_until(m, lambda: entity_block(m, Entity1)[CHAR_FALL_STATE_TIMER] == 0xFF,
                   max_frames=140)
        cam_dead = screen_pos_x(m)
        world_x_dead = pos_x(entity_block(m, Entity1))
        _, oamy_dead = oam_slot_for_entity(m, world_x_dead, cam_dead)
        print(f'killed victim real OAM Y: {oamy_dead} '
              f'(CHAR_FALL_STATE_TIMER={entity_block(m, Entity1)[CHAR_FALL_STATE_TIMER]:#x})')
        r.check('killed victim real hardware OAM sprite hidden (Y=$F0 dead-hide sentinel)',
                oamy_dead == 0xF0)

        # --- other entities unaffected by the kill (7, continued). ---
        for i in (0, 2, 3):
            blk = entity_block(m, ENTITY_BASES[i])
            hp = blk[CHAR_HP]
            indriven = blk[CHAR_INPUT_DRIVEN]
            r.check(f'entity {i} struct still sane after a lethal throw elsewhere '
                     f'(HP={hp} <= {CHAR_HP_MAX}, CHAR_INPUT_DRIVEN={indriven} <= 3)',
                    hp <= CHAR_HP_MAX and indriven <= 3)

        # ====================================================================
        # 8. notjustfreespecial.txt item 3: AI-initiated throw reachability.
        # Character_Grab_Throw was previously only ever called from the
        # player-input path (Jump_PlayerInputGate's do_throw block) -- an
        # AI-controlled grabber had no way to reach it regardless of
        # content. Anim_Play__ai_seek_gate (main.pasm) now routes an AI
        # entity that is the grabber (CHAR_GRAB_TARGET != $FF) into
        # Anim_Play__AiGrabHoldDecide (vm_native_engine.pasm) instead of
        # ordinary ai_seek; that decides via a real per-frame AI_THROW_
        # CHANCE=8/256 roll (Core_Random_Get-driven, same simplification
        # class as Anim_Play__ai_attack's own attack2 roll) whether to
        # execute a real Character_Grab_Throw. The link here is established
        # directly (not via a button press -- there's no AI input path to
        # drive) but Character_Grab_Throw itself, and the real per-frame AI
        # decision that reaches it, are exercised exactly as shipped.
        # ====================================================================
        reset_combat_state(m)
        m.write_u8(Entity1 + CHAR_ATTACK2_IS_GRAB, 1)
        m.write_u8(Entity1 + CHAR_INPUT_DRIVEN, 2)
        m.write_u8(Entity1 + CHAR_HP, CHAR_HP_MAX)
        m.write_u8(PlayerEntity + CHAR_HP, CHAR_HP_MAX)
        m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)
        overlap_entity_with_player(m, Entity1)
        # Entity1 is the grabber: its own CHAR_GRAB_TARGET holds the
        # player's byte offset (0); the player's CHAR_GRABBED_BY holds
        # Entity1's real byte offset -- same convention as game_g7_grab.py's
        # own AI-grab section (test 7 there), reversed from every player-
        # initiated grab in this file.
        m.write_u8(Entity1 + CHAR_GRAB_TARGET, 0)
        m.write_u8(PlayerEntity + CHAR_GRABBED_BY, Entity1_ByteOff)

        def still_holding_no_throw():
            overlap_entity_with_player(m, Entity1)
            return read_u8(m, PlayerEntity + CHAR_SELECTED) == CHAR_SELECTED_THROWN

        # AI_THROW_CHANCE=8/256 per frame -- (1 - 8/256)^400 is astronomically
        # small, so 400 real polled frames is a comfortable margin, not a
        # tight race.
        threw = poll_until(m, still_holding_no_throw, max_frames=400)
        player_after = entity_block(m, PlayerEntity)
        entity1_after = entity_block(m, Entity1)
        print(f'AI-initiated throw: player.CHAR_SELECTED={player_after[CHAR_SELECTED]} '
              f'entity1.CHAR_GRAB_TARGET={entity1_after[CHAR_GRAB_TARGET]} '
              f'player.CHAR_GRABBED_BY={player_after[CHAR_GRABBED_BY]}')
        r.check('an AI grabber\'s own per-frame decision really executes a '
                'real Character_Grab_Throw (player CHAR_SELECTED reaches '
                'CHAR_SELECTED_THROWN)', threw)
        r.check('the throw releases both link fields (entity1.CHAR_GRAB_TARGET '
                'and player.CHAR_GRABBED_BY both back to $FF)',
                entity1_after[CHAR_GRAB_TARGET] == 0xFF
                and player_after[CHAR_GRABBED_BY] == 0xFF)
        reset_combat_state(m)
        m.write_u8(Entity1 + CHAR_INPUT_DRIVEN, 2)

    r.finish()


if __name__ == '__main__':
    main()
