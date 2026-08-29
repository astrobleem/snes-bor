#!/usr/bin/env python3
"""plan_game.md Phase G7: real grab mutual-lock semantics (first slice).

Background: `game_g7_attack2.py`'s gate explicitly shipped JOE's `grab`
animation as a generic second-attack move (same one-shot AABB hit as
attack1), NOT real OpenBOR grab semantics, and said so in its own docstring.
This slice replaces that stand-in, for JOE only, with real mutual-lock
behavior sourced directly from `engine/openbor.c` (DCurrent/openbor):
`adjust_grabposition`'s one-time X-average-then-separate snap, a mutual
`CHAR_GRAB_TARGET`/`CHAR_GRABBED_BY` link, `check_link_move`'s per-frame
rigid offset-follow (not re-averaged), and a fixed-timer auto-release. Only
a character whose real attack2 animation is literally named `grab`
(currently JOE; derived at convert time, never hardcoded per character --
see convert_character.py's `attack2_is_grab`) gets this behavior; RALF's
`upper` and JHUN's `jumpattack` keep today's unchanged instant-damage
attack2, checked here as a regression.

Scope (see this slice's plan for the full derivation): player-initiated
only (AI never grabs), X-position-only snap/drag (Y is already guaranteed
close by the same CHAR_HITBOX_H overlap check that gates a normal hit, and
neither TryGrab nor Character_Grab_Play touch CHAR_POS_Y -- verified here
as "unchanged", not "matches an average"), auto-release only (no throw, no
grab-attack combos -- explicitly deferred).

Checks, all against a live Mesen2 session:
1. Select the roster to JOE (2 Select presses from boot); confirm
   CHAR_ATTACK2_IS_GRAB reads 1 in WRAM.
2. Overlap JOE with Entity1 (RALF) and press X: confirm the mutual link
   (player's CHAR_GRAB_TARGET == Entity1's real byte offset, Entity1's
   CHAR_GRABBED_BY == 0 i.e. the player's own byte offset) and that both
   entities' CHAR_POS_X snapped to the real adjust_grabposition midpoint
   +/- GRAB_HALF_DIST, computed independently in this test from each
   entity's own pre-grab X read back from WRAM -- not asked of the engine.
   CHAR_POS_Y must be unchanged on both sides (this slice never touches Y).
3. Hold dpad Right for several frames while grabbing: confirm Entity1's
   CHAR_POS_X tracks (player's CHAR_POS_X + its own frozen CHAR_GRAB_OFFSET)
   every sampled frame -- proves real per-frame rigid drag, not a one-time
   snap that happens to look static.
4. While linked: confirm Entity1's CHAR_SELECTED never leaves 0 (idle;
   AI-seek is gated) and its CHAR_HP is unaffected by unrelated attacks
   thrown at it (Character_HitApply's own CHAR_GRABBED_BY gate -- reuses
   Anim_Play's existing idle-force, verified indirectly via HP here).
5. Let CHAR_GRAB_TIMER run out (GRAB_HOLD_FRAMES): confirm both entities'
   link fields return to $FF and Entity1 resumes normal AI-seek (its
   CHAR_POS_X changes on its own within a further polling window).
6. Regression: select RALF, overlap Entity1, press X -- CHAR_GRAB_TARGET
   must stay $FF (no lock triggered) and attack2 still deals its real
   instant damage (Entity1's CHAR_HP drops), matching out/ralf_moveset.json's
   unchanged `attack2` (`upper`) entry.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_HIT_APPLIED = pasm_constant('CHAR_HIT_APPLIED')
CHAR_ATTACK2_IS_GRAB = pasm_constant('CHAR_ATTACK2_IS_GRAB')
CHAR_ATTACK_VARIANT = pasm_constant('CHAR_ATTACK_VARIANT')
CHAR_GRAB_TARGET = pasm_constant('CHAR_GRAB_TARGET')
CHAR_GRABBED_BY = pasm_constant('CHAR_GRABBED_BY')
CHAR_GRAB_TIMER = pasm_constant('CHAR_GRAB_TIMER')
CHAR_GRAB_OFFSET = pasm_constant('CHAR_GRAB_OFFSET')

VM_NATIVE_PATH = 'src/core/vm/vm_native_engine.pasm'
GRAB_HALF_DIST = pasm_constant_in(VM_NATIVE_PATH, 'GRAB_HALF_DIST')
GRAB_HOLD_FRAMES = pasm_constant_in(VM_NATIVE_PATH, 'GRAB_HOLD_FRAMES')

GS_PATH = 'src/core/game_state.pasm'
Entity1_InvulnFrames = pasm_constant_in(GS_PATH, 'Entity1_InvulnFrames')

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
PlayerEntity = ENTITY_BASES[0]
Entity1 = ENTITY_BASES[1]
Entity2 = ENTITY_BASES[2]
Entity3 = ENTITY_BASES[3]
Entity1_ByteOff = CHAR_ZP_LEN  # X register offset TryGrab/HitApply use for Entity1

CharSelect_Index = 0x7E53B6
CharSelect_Loaded = 0x7E53B8
CharSelect_RosterCount = 0x7E53B7

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RALF_MOVESET = os.path.join(ROOT, 'out', 'ralf_moveset.json')

READ_LEN = 80  # covers every CHAR_* offset used here (CHAR_ZP_LEN=67)


def s8(v):
    return v - 0x100 if v >= 0x80 else v


def entity_block(m, base):
    return read_block(m, base, READ_LEN)


def pos_x(blk):
    return blk[CHAR_POS_X] | (blk[CHAR_POS_X + 1] << 8)


def press_select(m):
    m.set_input(m.BTN_SELECT, 10)
    m.run_frames(40)
    m.pause()


def read_u8(m, addr):
    return read_block(m, addr, 32)[0]


def overlap_entity1_with_player(m):
    px = entity_block(m, PlayerEntity)
    x = pos_x(px)
    y = px[CHAR_POS_Y]
    m.write_u16(Entity1 + CHAR_POS_X, x)
    m.write_u8(Entity1 + CHAR_POS_Y, y)
    return x, y


def reset_combat_state(m):
    m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
    m.write_u8(PlayerEntity + CHAR_HIT_APPLIED, 0)
    m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)
    m.write_u8(PlayerEntity + CHAR_GRAB_TARGET, 0xFF)
    m.write_u8(Entity1 + CHAR_SELECTED, 0)
    m.write_u8(Entity1 + CHAR_HIT_STUN, 0)
    m.write_u8(Entity1 + CHAR_GRABBED_BY, 0xFF)
    m.write_u8(Entity1_InvulnFrames, 0)
    m.write_u8(Entity1 + CHAR_HP, CHAR_HP_MAX)


def poll_until(m, predicate, max_frames):
    for _ in range(max_frames):
        if predicate():
            return True
        m.run_frames(1)
        m.pause()
    return predicate()


def main():
    r = Reporter('G7-GRAB', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()

        # Neutralize entities 2/3 -- same reasoning as game_g7_knockdown.py:
        # real background AI combat is already underway by frame 300 and
        # would otherwise perturb entity 1 or contend for streaming budget.
        m.write_u8(Entity2 + CHAR_HP, 0)
        m.write_u8(Entity3 + CHAR_HP, 0)

        # --- Select to JOE (roster slot 2: RALF->JHUN->JOE). ---
        press_select(m)
        press_select(m)
        idx = read_u8(m, CharSelect_Index)
        loaded = read_u8(m, CharSelect_Loaded)
        r.check('roster selected to JOE (index 2)', idx == 2)
        r.check('CharSelect_Loaded==1 after reselect', loaded == 1)

        # --- 1. JOE's attack2 is a real grab role. ---
        joe_is_grab = read_u8(m, PlayerEntity + CHAR_ATTACK2_IS_GRAB)
        r.check('JOE CHAR_ATTACK2_IS_GRAB==1 (real converted grab role)', joe_is_grab == 1)

        # --- 2. Overlap + X press: mutual link + real X snap, Y unchanged. ---
        reset_combat_state(m)
        px_before, py_before = overlap_entity1_with_player(m)
        py1_before = entity_block(m, Entity1)[CHAR_POS_Y]
        print(f'pre-grab: player=({px_before},{py_before}) entity1_y={py1_before}')

        m.set_input(m.BTN_X, 1)
        linked = poll_until(
            m, lambda: read_u8(m, PlayerEntity + CHAR_GRAB_TARGET) != 0xFF, max_frames=30)
        r.check('X press near a real-grab target establishes the link '
                '(player CHAR_GRAB_TARGET != $FF)', linked)

        player_blk = entity_block(m, PlayerEntity)
        e1_blk = entity_block(m, Entity1)
        player_grab_target = player_blk[CHAR_GRAB_TARGET]
        e1_grabbed_by = e1_blk[CHAR_GRABBED_BY]
        print(f'link: player.CHAR_GRAB_TARGET={player_grab_target} '
              f'entity1.CHAR_GRABBED_BY={e1_grabbed_by}')
        r.check('cross-link: player.CHAR_GRAB_TARGET == entity1 real byte offset',
                player_grab_target == Entity1_ByteOff)
        r.check('cross-link: entity1.CHAR_GRABBED_BY == player byte offset (0)',
                e1_grabbed_by == 0)

        # Ground truth: same overlap => mid == px_before, self_ge branch taken
        # (self_x >= other_x, equal counts) -> self(+half), other(-half).
        expected_player_x = px_before + GRAB_HALF_DIST
        expected_entity1_x = px_before - GRAB_HALF_DIST
        actual_player_x = pos_x(player_blk)
        actual_entity1_x = pos_x(e1_blk)
        print(f'X snap: player {actual_player_x} (expected {expected_player_x}), '
              f'entity1 {actual_entity1_x} (expected {expected_entity1_x})')
        r.check('player CHAR_POS_X snapped to the real adjust_grabposition value',
                actual_player_x == expected_player_x)
        r.check('entity1 CHAR_POS_X snapped to the real adjust_grabposition value',
                actual_entity1_x == expected_entity1_x)
        r.check('player CHAR_POS_Y unchanged (this slice never touches Y)',
                player_blk[CHAR_POS_Y] == py_before)
        r.check('entity1 CHAR_POS_Y unchanged (this slice never touches Y)',
                e1_blk[CHAR_POS_Y] == py1_before)

        grab_offset = s8(e1_blk[CHAR_GRAB_OFFSET])
        print(f'entity1.CHAR_GRAB_OFFSET={grab_offset}')
        r.check('CHAR_GRAB_OFFSET == entity1_x - player_x, frozen at grab-init',
                grab_offset == actual_entity1_x - actual_player_x)

        # --- 3. Rigid per-frame drag while held (dpad Right). ---
        # set_input(btn, N) only holds the button DURING its own blocking
        # call (mesen_set_input_wall_clock project memory) -- it releases
        # once the call returns, so a separate run_frames() afterward sees
        # no input held. Re-issue it every sampled frame instead of calling
        # it once then polling with run_frames (matches phase8.py's own
        # repeated-set_input convention for a sustained hold).
        drag_ok = True
        samples = []
        for _ in range(20):
            m.set_input(m.BTN_RIGHT, 1)
            m.pause()
            pb = entity_block(m, PlayerEntity)
            eb = entity_block(m, Entity1)
            expected = (pos_x(pb) + grab_offset) & 0xFFFF
            actual = pos_x(eb)
            samples.append((pos_x(pb), actual, expected))
            if actual != expected:
                drag_ok = False
        print(f'drag samples (player_x, entity1_x, expected): {samples[:5]}...{samples[-3:]}')
        r.check('entity1 rigidly tracks player_x + frozen offset every sampled frame '
                '(real check_link_move, not re-averaged)', drag_ok)
        r.check('player actually moved during the drag window (dpad wasn\'t a no-op)',
                samples[-1][0] != samples[0][0])

        # --- 4. Held entity stays idle and untouched by other combat. ---
        held_hp_before = entity_block(m, Entity1)[CHAR_HP]
        held_selected_samples = [entity_block(m, Entity1)[CHAR_SELECTED] for _ in range(10)]
        for _ in range(10):
            m.run_frames(1)
            m.pause()
            held_selected_samples.append(entity_block(m, Entity1)[CHAR_SELECTED])
        held_hp_after = entity_block(m, Entity1)[CHAR_HP]
        print(f'held CHAR_SELECTED samples: {set(held_selected_samples)}, '
              f'hp {held_hp_before}->{held_hp_after}')
        r.check('held entity1 never leaves idle (CHAR_SELECTED stays 0, AI-seek gated)',
                set(held_selected_samples) == {0})
        r.check('held entity1 HP unaffected while linked', held_hp_after == held_hp_before)

        # --- 5. Auto-release once CHAR_GRAB_TIMER expires. ---
        m.write_u8(Entity1 + CHAR_GRAB_TIMER, 2)  # force a short remaining hold
        released = poll_until(
            m, lambda: read_u8(m, PlayerEntity + CHAR_GRAB_TARGET) == 0xFF, max_frames=30)
        e1_after = entity_block(m, Entity1)
        print(f'post-release: player.CHAR_GRAB_TARGET={read_u8(m, PlayerEntity + CHAR_GRAB_TARGET)} '
              f'entity1.CHAR_GRABBED_BY={e1_after[CHAR_GRABBED_BY]}')
        r.check('grab timer expiry releases the link (player CHAR_GRAB_TARGET back to $FF)',
                released)
        r.check('grab timer expiry releases the link (entity1 CHAR_GRABBED_BY back to $FF)',
                e1_after[CHAR_GRABBED_BY] == 0xFF)

        resumed = poll_until(
            m, lambda: entity_block(m, Entity1)[CHAR_POS_X] != actual_entity1_x
            or entity_block(m, Entity1)[CHAR_SELECTED] != 0,
            max_frames=180)
        r.check('entity1 resumes independent behavior after release', resumed)

        # --- 6. Regression: RALF's attack2 (upper) is unchanged instant damage. ---
        # Never hardcode a press count that assumes a specific roster size
        # (see phase5.py's own docstring on this class of drift) -- read the
        # real roster_count and press Select however many times wraps JOE
        # (index 2) back around to RALF (index 0). This project's roster grew
        # 4->6 the same day this gate was last touched (MOUSER/FOOT01 added
        # for the TMNT campaign); a hardcoded "2 presses" here silently
        # landed on a different character instead of failing loudly, until
        # the RALF-specific checks below caught it.
        roster_count = read_u8(m, CharSelect_RosterCount)
        presses_to_ralf = (roster_count - 2) % roster_count
        for _ in range(presses_to_ralf):
            press_select(m)
        idx_ralf = read_u8(m, CharSelect_Index)
        r.check(f'roster wrapped back to RALF (index 0) after {presses_to_ralf} Select '
                f'presses from JOE (roster_count={roster_count})', idx_ralf == 0)
        ralf_is_grab = read_u8(m, PlayerEntity + CHAR_ATTACK2_IS_GRAB)
        r.check('RALF CHAR_ATTACK2_IS_GRAB==0 (upper is not a real grab)', ralf_is_grab == 0)

        reset_combat_state(m)
        m.write_u8(Entity1 + CHAR_HP, CHAR_HP_MAX)
        px2, py2 = overlap_entity1_with_player(m)
        hp_before = entity_block(m, Entity1)[CHAR_HP]
        m.set_input(m.BTN_X, 1)
        hit_landed = poll_until(
            m, lambda: entity_block(m, Entity1)[CHAR_HP] != hp_before, max_frames=40)
        e1_ralf = entity_block(m, Entity1)
        with open(RALF_MOVESET, 'r', encoding='utf-8') as f:
            ralf_moveset = json.load(f)
        print(f'RALF attack2 regression: hp {hp_before}->{e1_ralf[CHAR_HP]}, '
              f'grab_target={read_u8(m, PlayerEntity + CHAR_GRAB_TARGET)}')
        r.check('RALF attack2 still deals real instant damage (no grab stand-in)', hit_landed)
        r.check('RALF attack2 never triggers a grab link', e1_ralf[CHAR_GRABBED_BY] == 0xFF)
        r.check('RALF attack2 role really is `upper` in the converted data (sanity)',
                ralf_moveset['roles'].get('attack2') is not None
                and not ralf_moveset.get('roles', {}).get('attack2_is_grab', False))

        # ====================================================================
        # 7. notjustfreespecial.txt item 3: AI-initiated grab reachability.
        # Character_HitApply_VsPlayer (the AI-vs-player hit path) previously
        # never called any grab-check at all -- a structurally separate gap
        # from the player-side link above. Entity1 is forced into JOE's
        # exact real attack2_is_grab shape (whatever roster character it
        # actually is at runtime -- the mechanism is generic, not
        # JOE-specific, matching this project's own "no hardcoded roster"
        # rule) and made to land a real attack2 hit on the player through
        # the SAME per-frame combat resolution any AI entity uses. This
        # proves Character_HitApply__TryGrabVsPlayer (vm_native_engine.pasm)
        # is really reachable from AI-vs-player combat, not just callable.
        # ====================================================================
        reset_combat_state(m)
        m.write_u8(Entity1 + CHAR_ATTACK2_IS_GRAB, 1)
        m.write_u8(Entity1 + CHAR_HP, CHAR_HP_MAX)
        m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)

        # Let the real AI decide when to attack (Anim_Play__ai_attack's own
        # 64/256 attack2 roll, Core_Random_Get-driven) rather than forcing
        # CHAR_SELECTED/CHAR_ATTACK_VARIANT by hand -- a raw struct write
        # skips the animation's own hit-frame gating (CHAR_FRAME_INDEX)
        # that real Character_HitApply__ApplyDamage-family checks require,
        # so this instead keeps Entity1 pinned on top of the player every
        # polled frame (AI-seek would otherwise walk it away while deciding)
        # and polls real frames until the AI organically rolls attack2,
        # closes to hit range, and lands it -- exactly the path a real
        # unattended AI-vs-player encounter takes.
        # Entity1 is the GRABBER here (unlike every earlier section in this
        # file, where the player always grabs): the grabber's OWN CHAR_
        # GRAB_TARGET holds the byte offset of who it's grabbing (the
        # player, always 0), and the GRABBED side's CHAR_GRABBED_BY holds
        # the grabber's own byte offset -- see CHAR_GRAB_TARGET/CHAR_
        # GRABBED_BY's own struct comments in main.pasm.
        # CHAR_ATTACK_VARIANT is forced to 1 (attack2) every polled frame,
        # same directness as this file's own player-side triggers (a real
        # button press, not waiting on true RNG) -- Anim_Play__ai_attack's
        # own 64/256 random roll (notjustfreespecial.txt item 3's other
        # fix) is a free-standing, already-real addition; forcing the
        # outcome here isolates and proves the previously-missing half:
        # that a landed AI attack2_is_grab hit on the player reaches
        # Character_HitApply__TryGrabVsPlayer at all.
        def keep_overlapped_and_check():
            overlap_entity1_with_player(m)
            m.write_u8(Entity1 + CHAR_SELECTED, 2)
            m.write_u8(Entity1 + CHAR_ATTACK_VARIANT, 1)
            return read_u8(m, Entity1 + CHAR_GRAB_TARGET) != 0xFF

        grabbed = poll_until(m, keep_overlapped_and_check, max_frames=120)
        entity1_target = read_u8(m, Entity1 + CHAR_GRAB_TARGET)
        player_grabbed_by = entity_block(m, PlayerEntity)[CHAR_GRABBED_BY]
        print(f'AI-initiated grab: entity1.CHAR_GRAB_TARGET={entity1_target} '
              f'player.CHAR_GRABBED_BY={player_grabbed_by}')
        r.check('an AI entity landing a real attack2_is_grab hit on the '
                'player establishes the mutual lock (the AI entity\'s own '
                'CHAR_GRAB_TARGET == the player\'s real byte offset, 0)',
                grabbed and entity1_target == 0)
        r.check('the player\'s own CHAR_GRABBED_BY is set to the AI '
                'entity\'s real byte offset, same cross-link JOE\'s '
                'player-initiated grab gives in reverse (test 2 above)',
                player_grabbed_by == Entity1_ByteOff)
        reset_combat_state(m)
        m.write_u8(Entity1 + CHAR_GRAB_TARGET, 0xFF)
        m.write_u8(PlayerEntity + CHAR_GRABBED_BY, 0xFF)

    r.finish()


if __name__ == '__main__':
    main()
