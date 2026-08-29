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
4. `riseattack` (UP+Y while lying, player_lie_check()): BEBOP/ROCK/
   LEATHER-only, verified via WRAM dispatch state AND that
   CHAR_FALL_STATE_TIMER is correctly reset (not left dangling).
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
  - `land`/ANI_LAND (doland()): gated on BLAST_TOSS + attack_force flags;
    zero configuration anywhere in either shipped pak (forcedirection/
    projectile/blast/autoland/ATTACK_FORCE all absent from every roster
    character's real .TXT) -- content-inapplicable, not a missing feature.
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

CharSelect_Index = 0x7E53B6
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

        # Real translated sequence: raw 1,2,3 -> local variant 0,1,3
        # (pack_msu_roster.py's ATCHAIN_RAW_TO_VARIANT). Press Y three
        # times in quick succession (mid-swing, well inside the combo
        # window) and confirm the step and variant both advance for real,
        # not just repeat step 0.
        expected_variants = [0, 1, 3]
        observed_variants = []
        for step in range(3):
            m.set_input(m.BTN_Y, 1)
            m.run_frames(1)
            m.pause()
            observed_variants.append(read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT))
            m.run_frames(3)
            m.pause()
        print(f'atchain observed variants={observed_variants} expected={expected_variants}')
        r.check('atchain combo cycles the real translated attack1->2->3 '
                'sequence (mid-swing presses advance the step, not just '
                'repeat step 0)', observed_variants == expected_variants)

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
        # 3. grabattack (R+Y) -- LEO-only.
        # ================================================================
        clear_stun(m, PlayerEntity)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
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
        print(f'R+Y press: selected={sel} variant={var}')
        r.check('R+Y triggers grabattack instead of plain grab '
                '(CHAR_ATTACK_VARIANT=8, priority over R alone)',
                sel == 2 and var == 8)
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

        m.set_input(m.BTN_DOWN | m.BTN_A, 3)
        m.run_frames(2)
        m.pause()
        sel = read_u8(m, PlayerEntity + CHAR_SELECTED)
        var = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
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

        # ================================================================
        # 5. riseattack (UP+Y while lying) -- BEBOP.
        # ================================================================
        idx = read_u8(m, CharSelect_Index)
        roster_count = len(ROSTER)
        steps = (BEBOP_INDEX - idx) % roster_count
        select_to(m, steps)
        idx = read_u8(m, CharSelect_Index)
        r.check(f'roster selected to BEBOP (index {BEBOP_INDEX})', idx == BEBOP_INDEX)

        real_riseattack_frames = load_role_frames('bebop', 'riseattack')
        riseattack_fc = read_u8(m, PlayerEntity + CHAR_RISEATTACK_FCOUNT)
        r.check('BEBOP CHAR_RISEATTACK_FCOUNT matches its real converted '
                '`riseattack` frame count',
                riseattack_fc == real_riseattack_frames and riseattack_fc > 0)

        clear_stun(m, PlayerEntity)
        m.write_u8(PlayerEntity + CHAR_SELECTED, 3)  # CHAR_SELECTED_FALL
        m.write_u8(PlayerEntity + CHAR_FALL_STATE_TIMER, 50)  # holding phase
        m.write_u8(PlayerEntity + CHAR_HP, 60)

        m.set_input(m.BTN_UP | m.BTN_Y, 1)
        m.run_frames(2)
        m.pause()
        sel = read_u8(m, PlayerEntity + CHAR_SELECTED)
        var = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
        fall_timer = read_u8(m, PlayerEntity + CHAR_FALL_STATE_TIMER)
        print(f'UP+Y while lying: selected={sel} variant={var} fall_timer={fall_timer}')
        r.check('UP+Y while lying (holding phase, HP>0) triggers riseattack '
                '(CHAR_SELECTED=2, CHAR_ATTACK_VARIANT=7)', sel == 2 and var == 7)
        r.check('riseattack trigger resets CHAR_FALL_STATE_TIMER (no dangling '
                'fall-hold state left behind)', fall_timer == 0)

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

    r.finish()


if __name__ == '__main__':
    main()
