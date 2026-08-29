#!/usr/bin/env python3
"""plan_game.md G7 content-audit slice ("Reopen G7").

Background: the prior "G7 fully exhausted" claim (commit 8c3fa69) was wrong
-- a source-content audit against real BOR/TMNT character data (DCurrent/
openbor engine/openbor.c, and the roster's own converted moveset JSON)
found real, already-converted, still-inert gameplay animations: LEO's real
atchain combo (attack1-4), a separate `grab` role, `slide`, `grabattack`;
BEBOP/ROCK/LEATHER's real `riseattack`. This gate covers everything this
slice newly wired:

1. atchain combo (perform_atchain(), engine/openbor.c): a single Y-button
   press cycles LEO's real declared sequence (`atchain 1 2 3 1 2 4` ->
   local variants 0,1,3,0,1,4) -- verified against out/leo_moveset.json's
   own `atchain` array (ground truth from the raw pak, not the engine's
   claim about itself), WRAM CHAR_COMBOSTEP/CHAR_ATTACK_VARIANT state, and
   real mid-swing chaining (repeated presses DURING the swing advance the
   step, not just after it finishes -- the actual point of a combo chain).
2. Generic `grab` role (R button) and `grabattack` (R+Y): LEO-only, real
   converted frame data, verified via WRAM dispatch state AND real damage
   dealt to a target entity (Character_HitApply's existing CHAR_SELECTED==2
   hit check, reused unmodified).
3. `slide` (A+Down): LEO-only, real converted frame data.
4. `riseattack` (UP+Y while lying, player_lie_check()): split into its own
   standalone gate, game_g7_riseattack.py (see that file's own docstring --
   BEBOP/ROCK/LEATHER all independently covered there, plus guard/damage/
   AI-reachability checks notjustfreespecial.txt item 6 added).
5. Regression: a non-chain character (RALF) still dispatches plain Y/X
   attack1/attack2 exactly as before this slice (chain gate is a true
   no-op for CHAR_CHAINLENGTH==0).
6. Base-chain ground truth: every new slot's CHAR_*_FCOUNT matches its
   real frame count from the converted moveset JSON (independent of the
   engine's own claim), for every roster member with real data in ANY new
   slot (LEO, BEBOP, ROCK, LEATHER, FOOT01, FOOT02).

8. `freespecial` (G7 reopened-again slice): the prior "AI-exclusive,
   content-inapplicable" classification was WRONG -- it only checked
   check_special()/player_check_special() (the ANI_SPECIAL path) and missed
   the real, separate model_init_defaultreadme() default-command mechanism
   (openbor.c ~line 21039) consumed via player_preinput()->check_combo()
   (player_think(), BEFORE player_check_special()), which IS player-
   reachable via a double-tap-forward-then-attack sequence. LEO is the only
   roster member with real freespecial data. Verified via real converted
   frame-count ground truth AND real WRAM dispatch state from an actual
   double-tap-forward+Y input sequence, AND a lapsed-window regression (a
   single forward tap that lapses must NOT trigger on a later lone attack
   press), AND that RALF (CHAR_FREESPECIAL_FCOUNT==0) never triggers it
   regardless of input.

Content classified INAPPLICABLE or OUT OF SCOPE (not gated here -- no
runtime code exists for them, confirmed absent by this slice's own audit):
  - `land`/ANI_LAND: CORRECTED, no longer inapplicable -- see
    notjustfreespecial.txt item 7 / game_g7_land_audit.py /
    game_g7_throw.py section 9. LEO ships real, uncommented `anim land`
    data, reachable via the real player-only player_fall_check() UP+JUMP-
    while-falling mechanic (separate from the BLAST_TOSS/attack_force gate
    doland() normally needs). Implemented as Character_Throw_Play__land.
    JHUN's `#anim land` remains genuinely disabled/commented data.
  - `waiting`/ANI_SELECT: real char-select portrait pose, G5 scope.
  - `get`: real item-pickup pose, G8 scope (matches the reopening
    instruction's own explicit example).
  - `alias`: real cosmetic no-op (see alias_keyword_is_cosmetic_not_identity
    project memory, sourced from BOR.C) -- not an animation at all.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_ATTACK_VARIANT = pasm_constant('CHAR_ATTACK_VARIANT')
CHAR_FRAME_INDEX = pasm_constant('CHAR_FRAME_INDEX')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_FALL_STATE_TIMER = pasm_constant('CHAR_FALL_STATE_TIMER')
CHAR_COMBOSTEP = pasm_constant('CHAR_COMBOSTEP')
CHAR_COMBOTIMER = pasm_constant('CHAR_COMBOTIMER')
CHAR_CHAINLENGTH = pasm_constant('CHAR_CHAINLENGTH')
CHAR_ATTACK2_FCOUNT = pasm_constant('CHAR_ATTACK2_FCOUNT')
CHAR_ATTACK3_FCOUNT = pasm_constant('CHAR_ATTACK3_FCOUNT')
CHAR_ATTACK4_FCOUNT = pasm_constant('CHAR_ATTACK4_FCOUNT')
CHAR_GRABMOVE_FCOUNT = pasm_constant('CHAR_GRABMOVE_FCOUNT')
CHAR_SLIDE_FCOUNT = pasm_constant('CHAR_SLIDE_FCOUNT')
CHAR_RISEATTACK_FCOUNT = pasm_constant('CHAR_RISEATTACK_FCOUNT')
CHAR_GRABATTACK_FCOUNT = pasm_constant('CHAR_GRABATTACK_FCOUNT')
CHAR_FREESPECIAL_FCOUNT = pasm_constant('CHAR_FREESPECIAL_FCOUNT')
CHAR_FREESPECIAL_STEP = pasm_constant('CHAR_FREESPECIAL_STEP')
CHAR_FREESPECIAL_TIMER = pasm_constant('CHAR_FREESPECIAL_TIMER')
CHAR_GRAB_TARGET = pasm_constant('CHAR_GRAB_TARGET')
CHAR_GRABBED_BY = pasm_constant('CHAR_GRABBED_BY')
CHAR_GRAB_TIMER = pasm_constant('CHAR_GRAB_TIMER')

CharSelect_Index = 0x7E53B6
CharSelect_Loaded = 0x7E53B8
PlayerEntity = 0x7E0A00
Entity1 = PlayerEntity + CHAR_ZP_LEN
Entity2 = PlayerEntity + CHAR_ZP_LEN * 2
Entity3 = PlayerEntity + CHAR_ZP_LEN * 3

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEO_MOVESET = os.path.join(ROOT, 'out', 'leo_moveset.json')
BEBOP_MOVESET = os.path.join(ROOT, 'out', 'bebop_moveset.json')

# build_rom.py's own printed roster slot order.
ROSTER = ['ralf', 'jhun', 'joe', 'yashiro', 'mouser', 'foot01', 'rock',
          'leather', 'bebop', 'foot02', 'foot03', 'foot04', 'leo']
LEO_INDEX = ROSTER.index('leo')
BEBOP_INDEX = ROSTER.index('bebop')
RALF_INDEX = ROSTER.index('ralf')


def load_role_frames(prefix, role):
    with open(os.path.join(ROOT, 'out', f'{prefix}_moveset.json'), 'r', encoding='utf-8') as f:
        moveset = json.load(f)
    ordinal = moveset['roles'].get(role)
    if ordinal is None:
        return None
    anim = next(a for a in moveset['animations'] if a['ordinal'] == ordinal)
    return anim['frames']


def load_atchain(prefix):
    with open(os.path.join(ROOT, 'out', f'{prefix}_moveset.json'), 'r', encoding='utf-8') as f:
        return json.load(f).get('atchain', [])


def read_u8(m, addr):
    return read_block(m, addr, 32)[0]


def select_to(m, index):
    for _ in range(index):
        m.set_input(m.BTN_SELECT, 10)
        m.run_frames(40)
        m.pause()


def clear_stun(m, entity):
    m.write_u8(entity + CHAR_HIT_STUN, 0)


ATCHAIN_RAW_TO_VARIANT = {1: 0, 2: 1, 3: 3, 4: 4}


def drive_atchain_and_check_damage(m, r, prefix, char_label):
    """notjustfreespecial.txt item 5: real, live, end-to-end chain coverage
    for a non-LEO chain-bearing character (FOOT01/FOOT02 both ship real
    atchain data too) -- previously only LEO's chain was actually driven;
    every other chain-bearing character only had its CHAR_CHAINLENGTH/
    CHAR_ATTACK3_FCOUNT ground-truth checked statically, never a real
    button-press sequence. Mirrors the LEO section's own technique (mid-
    swing presses, real damage check on the final step) at whatever length
    this character's own real atchain actually is."""
    real_atchain = load_atchain(prefix)
    expected_variants = [ATCHAIN_RAW_TO_VARIANT[step] for step in real_atchain]
    chainlength = read_u8(m, PlayerEntity + CHAR_CHAINLENGTH)
    r.check(f'{char_label} CHAR_CHAINLENGTH matches its real atchain length',
            chainlength == len(real_atchain))

    clear_stun(m, PlayerEntity)
    m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
    m.write_u8(PlayerEntity + CHAR_COMBOSTEP, 0)
    m.write_u8(PlayerEntity + CHAR_COMBOTIMER, 0)

    # Entity1 is kept overlapped with the player for the ENTIRE chain (not
    # just snapped in after the final press) -- a real fix found running
    # this for FOOT01: its own attack3 frame count (5) is short enough that
    # the hit-active window can pass before a post-loop overlap ever lands,
    # timing-dependent per character's own real frame counts rather than a
    # fixed constant every roster member happens to share.
    m.write_u8(Entity1 + CHAR_HP, 64)
    clear_stun(m, Entity1)
    hp_before = 64

    observed_variants = []
    for _ in real_atchain:
        pos = read_block(m, PlayerEntity + 4, 32)
        world_x = pos[0] | (pos[1] << 8)
        world_y = pos[2]
        m.write_u16(Entity1 + 4, world_x)
        m.write_u8(Entity1 + 6, world_y)
        m.set_input(m.BTN_Y, 1)
        m.run_frames(1)
        m.pause()
        observed_variants.append(read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT))
        m.run_frames(3)
        m.pause()
    print(f'{char_label} atchain observed variants={observed_variants} '
          f'expected={expected_variants}')
    r.check(f'{char_label}\'s own real atchain ({real_atchain}) is actually '
            f'driven live through every step, not just checked statically',
            observed_variants == expected_variants)

    # Real damage somewhere across the chain -- same technique as LEO's
    # attack4 check above, generalized to whatever this character's own
    # frame counts actually allow within a bounded poll.
    for _ in range(20):
        m.run_frames(1)
        m.pause()
        if read_u8(m, Entity1 + CHAR_HP) < hp_before:
            break
    hp_after = read_u8(m, Entity1 + CHAR_HP)
    print(f'{char_label} entity1 hp after chain window: {hp_after} '
          f'(was {hp_before})')
    r.check(f'{char_label}\'s real chain deals real damage via the shared '
            f'hit check', hp_after < hp_before)
    m.write_u8(Entity1 + CHAR_HP, 0)
    clear_stun(m, PlayerEntity)
    m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
    m.write_u8(PlayerEntity + CHAR_FALL_STATE_TIMER, 0)
    m.run_frames(60)
    m.pause()


def main():
    r = Reporter('G7-CONTENT-AUDIT', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        # Neutralize AI entities so nothing else perturbs these dispatch
        # checks, same convention as game_g7_attack2.py/game_g7_special.py.
        m.write_u8(Entity1 + CHAR_HP, 0)
        m.write_u8(Entity2 + CHAR_HP, 0)
        m.write_u8(Entity3 + CHAR_HP, 0)

        # ================================================================
        # 1. atchain combo -- LEO.
        # ================================================================
        select_to(m, LEO_INDEX)
        idx = read_u8(m, CharSelect_Index)
        r.check(f'roster selected to LEO (index {LEO_INDEX})', idx == LEO_INDEX)

        real_atchain = load_atchain('leo')
        r.check('LEO has real atchain data in the converted pak',
                real_atchain == [1, 2, 3, 1, 2, 4])
        chainlength = read_u8(m, PlayerEntity + CHAR_CHAINLENGTH)
        r.check('LEO CHAR_CHAINLENGTH matches real atchain length',
                chainlength == len(real_atchain))

        clear_stun(m, PlayerEntity)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        m.write_u8(PlayerEntity + CHAR_COMBOSTEP, 0)
        m.write_u8(PlayerEntity + CHAR_COMBOTIMER, 0)

        # Real translated sequence: raw 1,2,3,1,2,4 -> local variant
        # 0,1,3,0,1,4 (pack_msu_roster.py's ATCHAIN_RAW_TO_VARIANT). Press Y
        # six times in quick succession (mid-swing, well inside the combo
        # window) -- the FULL declared chain, not just its first 3 steps --
        # and confirm every step's variant advances for real, not just
        # repeats step 0. notjustfreespecial.txt item 5, explicit: prior
        # coverage stopped after 3 presses and never proved the repeated
        # `4` (attack4, the chain's actual final step) is reachable at all;
        # the coverage-ledger generator's own verifier caught this exact
        # gap (leo/attack4: partial with a real runtime_handler but no
        # owning gate cited) before this fix.
        expected_variants = [0, 1, 3, 0, 1, 4]
        observed_variants = []
        for step in range(6):
            m.set_input(m.BTN_Y, 1)
            m.run_frames(1)
            m.pause()
            observed_variants.append(read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT))
            m.run_frames(3)
            m.pause()
        print(f'atchain observed variants={observed_variants} expected={expected_variants}')
        r.check('atchain combo cycles the real, FULL translated attack1->2->3'
                '->1->2->4 sequence (mid-swing presses advance the step, not just '
                'repeat step 0)', observed_variants == expected_variants)

        # Real damage on the attack4 step specifically -- neither attack3
        # nor attack4 had ever been proven to deal damage before this fix
        # (only slide got its own dedicated damage check). Overlap entity 1
        # with the player (still mid-swing on step 6/attack4 from the loop
        # above) and confirm the shared CHAR_SELECTED==2 hit check fires.
        pos = read_block(m, PlayerEntity + 4, 32)
        world_x = pos[0] | (pos[1] << 8)
        world_y = pos[2]
        m.write_u16(Entity1 + 4, world_x)
        m.write_u8(Entity1 + 6, world_y)
        m.write_u8(Entity1 + CHAR_HP, 64)
        clear_stun(m, Entity1)
        hp_before_a4 = 64
        for _ in range(20):
            m.run_frames(1)
            m.pause()
            if read_u8(m, Entity1 + CHAR_HP) < hp_before_a4:
                break
        hp_after_a4 = read_u8(m, Entity1 + CHAR_HP)
        print(f'entity1 hp after attack4 window: {hp_after_a4} (was {hp_before_a4})')
        r.check('attack4 (the atchain\'s final step) deals real damage via the '
                'shared hit check, not just an animation with no effect',
                hp_after_a4 < hp_before_a4)
        # Entity1 was given real HP/no-stun for this check, unlike every
        # other section in this gate -- it can genuinely counter-attack the
        # player during the run_frames window above. Fully neutralize BOTH
        # sides afterward (not just entity1's HP) so a real knockdown/stun
        # the player took here can't silently carry into later sections.
        m.write_u8(Entity1 + CHAR_HP, 0)
        clear_stun(m, PlayerEntity)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        m.write_u8(PlayerEntity + CHAR_FALL_STATE_TIMER, 0)
        m.run_frames(60)
        m.pause()

        # Let the window lapse and confirm it resets to step 0 on the next
        # fresh press (real perform_atchain(): a lapsed window resets).
        m.run_frames(80)
        m.pause()
        m.set_input(m.BTN_Y, 1)
        m.run_frames(1)
        m.pause()
        reset_variant = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
        r.check('a lapsed combo window resets to step 0 (attack1) on the '
                'next press', reset_variant == 0)
        m.run_frames(60)
        m.pause()

        # ================================================================
        # 2. Generic grab (R) -- LEO's real, separate `grab` role.
        # ================================================================
        clear_stun(m, PlayerEntity)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        real_grab_frames = load_role_frames('leo', 'grab')
        grabmove_fc = read_u8(m, PlayerEntity + CHAR_GRABMOVE_FCOUNT)
        r.check('LEO CHAR_GRABMOVE_FCOUNT matches its real converted `grab` '
                'frame count', grabmove_fc == real_grab_frames and grabmove_fc > 0)

        m.set_input(m.BTN_R, 1)
        m.run_frames(2)
        m.pause()
        sel = read_u8(m, PlayerEntity + CHAR_SELECTED)
        var = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
        print(f'R press: selected={sel} variant={var}')
        r.check('R press triggers the grab move (CHAR_SELECTED=2, '
                'CHAR_ATTACK_VARIANT=5)', sel == 2 and var == 5)
        m.run_frames(60)
        m.pause()

        # ================================================================
        # 3. grabattack (R+Y) -- LEO-only. notjustfreespecial.txt item 2:
        #    now that LEO's `grab` lands through the same real CHAR_GRAB_
        #    TARGET mutual lock JOE already has (see vm_native_engine.pasm's
        #    TryGrab condition widening), grabattack has a real BOR.C-
        #    sourced precondition -- it only fires while ALREADY holding a
        #    live grab (real dograb()/grabattack() semantics). Plain R+Y
        #    with no active hold is meaningless and now falls through to a
        #    no-op (neither grab nor grabattack starts, since R+Y != a
        #    plain-R press) rather than the old always-fires stand-in.
        # ================================================================
        clear_stun(m, PlayerEntity)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        m.write_u8(PlayerEntity + CHAR_GRAB_TARGET, 0xFF)
        real_grabattack_frames = load_role_frames('leo', 'grabattack')
        grabattack_fc = read_u8(m, PlayerEntity + CHAR_GRABATTACK_FCOUNT)
        r.check('LEO CHAR_GRABATTACK_FCOUNT matches its real converted '
                '`grabattack` frame count',
                grabattack_fc == real_grabattack_frames and grabattack_fc > 0)

        m.set_input(m.BTN_R | m.BTN_Y, 1)
        m.run_frames(2)
        m.pause()
        sel = read_u8(m, PlayerEntity + CHAR_SELECTED)
        var = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
        print(f'R+Y with no active hold: selected={sel} variant={var}')
        r.check('R+Y with no active hold falls through to a plain grab '
                'attempt (CHAR_ATTACK_VARIANT=5), same as R alone -- real '
                'grabattack requires an active hold, not shipped as an '
                'always-fires stand-in)', sel == 2 and var == 5)
        m.run_frames(60)
        m.pause()

        # Now establish a real hold (JOE, roster slot 2) and confirm R+Y
        # triggers real grabattack (variant 8) only while holding. Also set
        # a live CHAR_GRAB_TIMER -- Character_Grab_Play's own per-frame
        # auto-release check runs before Jump_PlayerInputGate this same
        # frame, and would otherwise immediately release a hold whose timer
        # is still 0 from the manual write below.
        clear_stun(m, PlayerEntity)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        joe_off = Entity1 - PlayerEntity  # roster-relative offset, reused below
        m.write_u8(PlayerEntity + CHAR_GRAB_TARGET, joe_off)
        m.write_u8(Entity1 + CHAR_GRABBED_BY, 0)
        m.write_u8(Entity1 + CHAR_GRAB_TIMER, 240)  # timer lives on the
                                                      # GRABBED entity, not
                                                      # the grabber (matches
                                                      # real BOR.C's
                                                      # target->stalltime)
        m.set_input(m.BTN_R | m.BTN_Y, 1)
        m.run_frames(1)     # sample on the trigger frame itself -- while
                             # holding, Anim_Play__not_attacking deliberately
                             # bypasses the normal "already attacking, hold
                             # the latch" lock for the grabber side (see its
                             # own comment: lets the grabber's dpad drive
                             # walk/idle immediately, same as real BOR.C), so
                             # a triggered swing here is only guaranteed live
                             # for the one frame it was set -- matches this
                             # file's own R-press-while-not-holding check,
                             # which instead relies on the ordinary
                             # already-attacking latch (only active when
                             # CHAR_GRAB_TARGET==$FF) to still see it 1 frame
                             # later.
        m.pause()
        sel = read_u8(m, PlayerEntity + CHAR_SELECTED)
        var = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
        print(f'R+Y while holding: selected={sel} variant={var}')
        # CHAR_SELECTED itself is NOT asserted here -- set_input is wall-
        # clock/sleep-based (mesen_set_input_wall_clock project memory), so
        # "run_frames(1)" is a lower bound, not an exact single frame; if a
        # second real frame slips in before this read, the trigger edge is
        # already consumed and the grabber-side "let dpad drive it"
        # fallthrough (this file's own Anim_Play__not_attacking comment)
        # can legitimately fall back to ordinary ground dispatch before the
        # read lands. CHAR_ATTACK_VARIANT==8 alone is what actually proves
        # the already_holding branch (not grab_trigger, which would leave
        # variant=5) fired -- confirmed reproducible across runs.
        r.check('R+Y while already holding a real grab triggers '
                'grabattack, not plain grab (CHAR_ATTACK_VARIANT=8)',
                var == 8)
        m.write_u8(PlayerEntity + CHAR_GRAB_TARGET, 0xFF)
        m.write_u8(Entity1 + CHAR_GRABBED_BY, 0xFF)
        m.run_frames(60)
        m.pause()

        # ================================================================
        # 4. slide (A+Down) -- LEO-only, deals real damage to prove it uses
        #    the same live hit-check path as every other attack (not a
        #    cosmetic-only animation).
        # ================================================================
        clear_stun(m, PlayerEntity)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        real_slide_frames = load_role_frames('leo', 'slide')
        slide_fc = read_u8(m, PlayerEntity + CHAR_SLIDE_FCOUNT)
        r.check('LEO CHAR_SLIDE_FCOUNT matches its real converted `slide` '
                'frame count', slide_fc == real_slide_frames and slide_fc > 0)

        # Overlap entity 1 with the player and give it HP so slide's real
        # hit check can land on it.
        pos = read_block(m, PlayerEntity + 4, 32)
        world_x = pos[0] | (pos[1] << 8)
        world_y = pos[2]
        m.write_u16(Entity1 + 4, world_x)
        m.write_u8(Entity1 + 6, world_y)
        m.write_u8(Entity1 + CHAR_HP, 64)
        clear_stun(m, Entity1)

        # CHAR_SLIDE_FCOUNT is 1 for LEO (a single-frame swing) -- sampling
        # several frames after the press can land after it has already run
        # to completion and reverted CHAR_SELECTED back to idle (found by
        # this slice's own debugging: a clean pre-state plus a FAIL here
        # with no other explanation, root-caused to sampling too late, not
        # a dispatch bug). Poll every single frame from the press itself so
        # the trigger is caught on the frame it actually happens, matching
        # this file's own atchain-loop convention above.
        # Real harness gap (mesen_set_input_wall_clock project memory, this
        # slice's own re-confirmation): after enough prior set_input calls
        # in one long session, an individual set_input can silently fail to
        # deliver ANY real button state at all -- confirmed here by reading
        # the real Input_press/Input_trigger WRAM cells directly and seeing
        # $0000 across 8 full sampled frames despite a clean, correct game
        # state otherwise (roster/loaded/slide_fc all verified correct at
        # this exact point). Not an engine bug -- retry the press itself
        # (this project's own established pattern for harness flakiness,
        # see Reporter.majority_of_3) rather than trusting one call.
        sel, var = 0, 0
        for attempt in range(3):
            m.set_input(m.BTN_DOWN | m.BTN_A, 5)
            for fi in range(8):
                m.run_frames(1)
                m.pause()
                sel = read_u8(m, PlayerEntity + CHAR_SELECTED)
                var = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
                if sel == 2:
                    break
            if sel == 2:
                break
            print(f'  slide input attempt {attempt+1} did not register '
                  f'(Input_press stayed $0000) -- retrying')
            sel = read_u8(m, PlayerEntity + CHAR_SELECTED)
            var = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
            if sel == 2:
                break
        print(f'Down+A press: selected={sel} variant={var}')
        r.check('Down+A triggers slide (CHAR_SELECTED=2, '
                'CHAR_ATTACK_VARIANT=6)', sel == 2 and var == 6)

        hp_before = 64
        for _ in range(30):
            m.run_frames(1)
            m.pause()
            if read_u8(m, Entity1 + CHAR_HP) < hp_before:
                break
        hp_after = read_u8(m, Entity1 + CHAR_HP)
        print(f'entity1 hp after slide window: {hp_after} (was {hp_before})')
        r.check('slide deals real damage via the existing CHAR_SELECTED==2 '
                'hit check (not a cosmetic-only animation)', hp_after < hp_before)
        m.write_u8(Entity1 + CHAR_HP, 0)
        m.run_frames(60)
        m.pause()

        # riseattack (UP+Y while lying) split into its own standalone gate,
        # game_g7_riseattack.py -- notjustfreespecial.txt item 6's full
        # BEBOP/ROCK/LEATHER coverage deterministically starved on this
        # gate's own already-long chain of set_input calls (mesen_set_
        # input_wall_clock harness gap), not a per-character bug. See that
        # file's own docstring for the full coverage list and AI-
        # reachability sourcing.

        # ================================================================
        # 6. Regression -- a non-chain character (RALF) still dispatches
        #    plain Y/X attack1/attack2 exactly as before this slice.
        # ================================================================
        idx = read_u8(m, CharSelect_Index)
        roster_count = len(ROSTER)
        steps = (RALF_INDEX - idx) % roster_count
        select_to(m, steps)
        idx = read_u8(m, CharSelect_Index)
        r.check(f'roster selected to RALF (index {RALF_INDEX})', idx == RALF_INDEX)

        chainlength_ralf = read_u8(m, PlayerEntity + CHAR_CHAINLENGTH)
        r.check('RALF CHAR_CHAINLENGTH==0 (real data: no atchain)',
                chainlength_ralf == 0)

        clear_stun(m, PlayerEntity)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        m.set_input(m.BTN_Y, 1)
        m.run_frames(2)
        m.pause()
        sel = read_u8(m, PlayerEntity + CHAR_SELECTED)
        var = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
        r.check('RALF (no chain): Y still triggers plain attack1 '
                '(CHAR_ATTACK_VARIANT=0), unaffected by the atchain gate',
                sel == 2 and var == 0)
        m.run_frames(60)
        m.pause()

        clear_stun(m, PlayerEntity)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        m.set_input(m.BTN_X, 1)
        m.run_frames(2)
        m.pause()
        sel = read_u8(m, PlayerEntity + CHAR_SELECTED)
        var = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
        real_attack2_frames = load_role_frames('ralf', 'attack2')
        attack2_fc = read_u8(m, PlayerEntity + CHAR_ATTACK2_FCOUNT)
        r.check('RALF (no chain): X still triggers plain attack2 '
                '(CHAR_ATTACK_VARIANT=1), unaffected by the atchain gate',
                sel == 2 and var == 1)
        r.check('RALF CHAR_ATTACK2_FCOUNT still matches its real `upper` '
                'frame count (unchanged by this slice)',
                attack2_fc == real_attack2_frames)

        # ================================================================
        # 8. freespecial (double-tap-forward + Y) -- LEO-only, real
        #    player-reachable trigger (reopened-again slice; see this
        #    file's own module docstring for the sourcing correction).
        # ================================================================
        idx = read_u8(m, CharSelect_Index)
        steps = (LEO_INDEX - idx) % roster_count
        select_to(m, steps)
        idx = read_u8(m, CharSelect_Index)
        r.check(f'roster selected to LEO (index {LEO_INDEX})', idx == LEO_INDEX)

        real_freespecial_frames = load_role_frames('leo', 'freespecial')
        freespecial_fc = read_u8(m, PlayerEntity + CHAR_FREESPECIAL_FCOUNT)
        r.check('LEO CHAR_FREESPECIAL_FCOUNT matches its real converted '
                '`freespecial` frame count',
                freespecial_fc == real_freespecial_frames and freespecial_fc > 0)

        clear_stun(m, PlayerEntity)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        m.write_u8(PlayerEntity + CHAR_FREESPECIAL_STEP, 0)
        m.write_u8(PlayerEntity + CHAR_FREESPECIAL_TIMER, 0)

        # Double-tap forward (Right -- LEO faces right by default at boot,
        # matching phase8.py's own convention), each tap a discrete
        # trigger-edge press well inside the FSM's grace window, then a
        # separate attack press.
        m.set_input(m.BTN_RIGHT, 1)
        m.run_frames(3)
        m.pause()
        step1 = read_u8(m, PlayerEntity + CHAR_FREESPECIAL_STEP)
        m.set_input(m.BTN_RIGHT, 1)
        m.run_frames(3)
        m.pause()
        step2 = read_u8(m, PlayerEntity + CHAR_FREESPECIAL_STEP)
        print(f'freespecial FSM steps: {step1} -> {step2}')
        r.check('double-tap-forward advances the freespecial FSM to step 2 '
                '(ready)', step1 == 1 and step2 == 2)

        m.set_input(m.BTN_Y, 1)
        m.run_frames(2)
        m.pause()
        sel = read_u8(m, PlayerEntity + CHAR_SELECTED)
        var = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
        print(f'double-tap-forward+Y: selected={sel} variant={var}')
        r.check('double-tap-forward then Y triggers freespecial '
                '(CHAR_SELECTED=2, CHAR_ATTACK_VARIANT=9)',
                sel == 2 and var == 9)
        m.run_frames(60)
        m.pause()

        # Regression: a single forward tap that lapses (no second tap
        # within the grace window) must NOT leave the FSM ready to fire on
        # a later, unrelated attack press.
        clear_stun(m, PlayerEntity)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        m.write_u8(PlayerEntity + CHAR_FREESPECIAL_STEP, 0)
        m.write_u8(PlayerEntity + CHAR_FREESPECIAL_TIMER, 0)
        m.set_input(m.BTN_RIGHT, 1)
        m.run_frames(3)
        m.pause()
        m.run_frames(80)  # let the tap window lapse
        m.pause()
        lapsed_step = read_u8(m, PlayerEntity + CHAR_FREESPECIAL_STEP)
        m.set_input(m.BTN_Y, 1)
        m.run_frames(2)
        m.pause()
        sel_after_lapse = read_u8(m, PlayerEntity + CHAR_SELECTED)
        var_after_lapse = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
        print(f'lapsed single-tap then Y: fsm_step={lapsed_step} '
              f'selected={sel_after_lapse} variant={var_after_lapse}')
        r.check('a lapsed single forward-tap resets the FSM (step back to 0)',
                lapsed_step == 0)
        r.check('a lone attack press after a lapsed tap plays ordinary '
                'attack1, NOT freespecial (CHAR_ATTACK_VARIANT=0)',
                sel_after_lapse == 2 and var_after_lapse == 0)
        m.run_frames(60)
        m.pause()

        # Regression: RALF (no real freespecial data) never triggers it
        # regardless of the same double-tap-forward+Y input sequence.
        idx = read_u8(m, CharSelect_Index)
        steps = (RALF_INDEX - idx) % roster_count
        select_to(m, steps)
        idx = read_u8(m, CharSelect_Index)
        r.check(f'roster selected to RALF (index {RALF_INDEX})', idx == RALF_INDEX)
        ralf_freespecial_fc = read_u8(m, PlayerEntity + CHAR_FREESPECIAL_FCOUNT)
        r.check('RALF has no real freespecial data (CHAR_FREESPECIAL_FCOUNT==0)',
                ralf_freespecial_fc == 0)

        clear_stun(m, PlayerEntity)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        m.write_u8(PlayerEntity + CHAR_FREESPECIAL_STEP, 0)
        m.write_u8(PlayerEntity + CHAR_FREESPECIAL_TIMER, 0)
        m.set_input(m.BTN_RIGHT, 1)
        m.run_frames(3)
        m.pause()
        m.set_input(m.BTN_RIGHT, 1)
        m.run_frames(3)
        m.pause()
        m.set_input(m.BTN_Y, 1)
        m.run_frames(2)
        m.pause()
        ralf_sel = read_u8(m, PlayerEntity + CHAR_SELECTED)
        ralf_var = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
        print(f'RALF double-tap-forward+Y: selected={ralf_sel} variant={ralf_var}')
        r.check('RALF (CHAR_FREESPECIAL_FCOUNT==0): double-tap-forward+Y '
                'still plays ordinary attack1 (CHAR_ATTACK_VARIANT=0), '
                'freespecial gate is a true no-op for this character',
                ralf_sel == 2 and ralf_var == 0)
        m.run_frames(60)
        m.pause()

        # ================================================================
        # 9. Base-chain ground truth -- FOOT01's real atchain (attack1-3,
        #    no attack4/grab/slide/riseattack/grabattack) matches its
        #    converted moveset.
        # ================================================================
        idx = read_u8(m, CharSelect_Index)
        foot01_index = ROSTER.index('foot01')
        steps = (foot01_index - idx) % roster_count
        select_to(m, steps)
        idx = read_u8(m, CharSelect_Index)
        r.check(f'roster selected to FOOT01 (index {foot01_index})',
                idx == foot01_index)
        real_foot01_atchain = load_atchain('foot01')
        foot01_chainlength = read_u8(m, PlayerEntity + CHAR_CHAINLENGTH)
        real_foot01_attack3 = load_role_frames('foot01', 'attack3')
        foot01_attack3_fc = read_u8(m, PlayerEntity + CHAR_ATTACK3_FCOUNT)
        foot01_attack4_fc = read_u8(m, PlayerEntity + CHAR_ATTACK4_FCOUNT)
        print(f'FOOT01 atchain={real_foot01_atchain} chainlength={foot01_chainlength} '
              f'attack3_fc={foot01_attack3_fc} (expected {real_foot01_attack3}) '
              f'attack4_fc={foot01_attack4_fc}')
        r.check('FOOT01 CHAR_CHAINLENGTH matches its real atchain length',
                foot01_chainlength == len(real_foot01_atchain))
        r.check('FOOT01 CHAR_ATTACK3_FCOUNT matches its real converted '
                '`attack3` frame count',
                foot01_attack3_fc == real_foot01_attack3 and foot01_attack3_fc > 0)
        r.check('FOOT01 has no real attack4 data (CHAR_ATTACK4_FCOUNT==0)',
                foot01_attack4_fc == 0)

        drive_atchain_and_check_damage(m, r, 'foot01', 'FOOT01')

        # ================================================================
        # 10. FOOT02's own real atchain, driven live -- the other real
        #    chain-bearing character besides LEO/FOOT01, same generalization
        #    as item 5 requires (no hardcoded single-character coverage).
        # ================================================================
        idx = read_u8(m, CharSelect_Index)
        foot02_index = ROSTER.index('foot02')
        steps = (foot02_index - idx) % roster_count
        select_to(m, steps)
        idx = read_u8(m, CharSelect_Index)
        r.check(f'roster selected to FOOT02 (index {foot02_index})',
                idx == foot02_index)
        drive_atchain_and_check_damage(m, r, 'foot02', 'FOOT02')

    r.finish()


if __name__ == '__main__':
    main()
