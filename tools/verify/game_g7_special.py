#!/usr/bin/env python3
"""plan_game.md Phase G7 (remaining item): a real special move.

Background: real BOR.C `check_special()`/`player_check_special()`
(DCurrent/openbor, engine/openbor.c, fetched and read this slice):
validanim + check_energy(HP or MP) gate a special move; on trigger it
releases the player's active grab link (dograb-release, before toss()/
anim-set), then plays the special animation, and deducts
energy_cost.cost from HP/MP AFTER triggering ONLY if that cost is
nonzero. Normally bound to a single dedicated button (FLAG_SPECIAL)
unless a model declares a custom multi-step input-sequence command --
LEO's real model does NOT declare one, so the simple single-button case
applies.

Of the full roster, only LEO (TMNT pak, DATA\\CHARS\\LEO\\LEO.TXT,
PAK-verified) has a real `special` anim: 6 frames, a real `attack`
hitbox line, no `energycost` line at all -- genuinely free per real
check_energy() (a zero cost is a no-op deduction, not "this project
skipped the cost", matching source). Bound to L (the other genuinely
free button in this project's existing map, per core/jump.pasm's own
Jump_PlayerTick header comment: B=run, Y=attack1, X=attack2, A=jump).

Damage is applied via the SAME Character_HitApply CHAR_SELECTED==2 check
attack1/attack2 already use (CHAR_ATTACK_VARIANT==2 just picks a third
frame-data source, same shape as attack2's own variant==1) -- confirmed
no attack-variant-specific code exists in Character_HitApply.

notjustfreespecial.txt item 8 correction: an earlier slice of this audit
claimed "no roster character has both real grab data AND real special
data" and tested grab-release-on-trigger as a synthetic/forced-WRAM
plumbing check. That claim was WRONG -- LEO's real moveset has BOTH a
`special` role (17) AND a `grab` role (12), and G7 items 2/3 already
widened Character_HitApply__TryGrab to treat LEO's own R-triggered grab
swing (CHAR_GRABMOVE_FCOUNT, variant 5) as a real grab-establishing hit,
the same mutual-lock path JOE's attack2_is_grab uses. Grab-release-on-
special-trigger is therefore verified organically below: LEO's own R
press lands a real mutual lock, then L's release path is checked against
that real link, not a forced one.

Checks, all against a live Mesen2 session:
1. Select the roster to LEO (12 Select presses from boot) and confirm
   CHAR_SPECIAL_FCOUNT/DELAY in WRAM match LEO's real `special` frame
   count/delay from out/leo_moveset.json (ground truth: the converter's
   own baked manifest, not the engine's own claim about itself).
2. CHAR_SPECIAL_BASE (computed at load time by chaining off
   CHAR_ATTACK2_BASE + (attack2+jump+jumpattack+jumpattack2 frame_count)
   *768) matches an independent Python recomputation from those same
   fields read back from WRAM.
3. CHAR_MAP_BASE now chains one hop further, off CHAR_SPECIAL_BASE +
   special_frame_count*768 -- verified against an independent
   recomputation too (proves the map_base ripple didn't silently break).
4. Pressing L (edge) while playable sets CHAR_SELECTED=2 and
   CHAR_ATTACK_VARIANT=2, and the move runs to completion (CHAR_FRAME_
   INDEX stays < CHAR_SPECIAL_FCOUNT throughout, CHAR_SELECTED reverts to
   0 when done) -- same non-looping revert-to-idle shape attack1/attack2
   already have.
5. Free (no HP cost): player CHAR_HP is unchanged by using special (real
   BOR source: energy_cost.cost==0 for LEO -- a genuine no-op deduction,
   not an unimplemented feature).
6. Grab-release-on-trigger (structural/plumbing check, see scope note
   above): forcing CHAR_GRAB_TARGET nonzero on the player before pressing
   L clears it back to $FF, and the forced "victim"'s own CHAR_GRABBED_BY
   is cleared too, as part of the same trigger.
7. Regression: pressing Y still triggers attack1, variant 0, with LEO's
   real attack1 frame count unchanged by this slice.
8. A roster member with no real special data (RALF, index 0):
   pressing L must NOT trigger anything (CHAR_SELECTED stays 0, no
   stream from a zero-length region).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, read_block, Reporter, roster  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_FRAME_INDEX = pasm_constant('CHAR_FRAME_INDEX')
CHAR_ATTACK_FCOUNT = pasm_constant('CHAR_ATTACK_FCOUNT')
CHAR_ATTACK_VARIANT = pasm_constant('CHAR_ATTACK_VARIANT')
CHAR_ATTACK2_FCOUNT = pasm_constant('CHAR_ATTACK2_FCOUNT')
CHAR_ATTACK2_BASE_LO = pasm_constant('CHAR_ATTACK2_BASE_LO')
CHAR_ATTACK2_BASE_HI = pasm_constant('CHAR_ATTACK2_BASE_HI')
CHAR_SPECIAL_FCOUNT = pasm_constant('CHAR_SPECIAL_FCOUNT')
CHAR_SPECIAL_DELAY = pasm_constant('CHAR_SPECIAL_DELAY')
CHAR_SPECIAL_BASE_LO = pasm_constant('CHAR_SPECIAL_BASE_LO')
CHAR_SPECIAL_BASE_HI = pasm_constant('CHAR_SPECIAL_BASE_HI')
CHAR_MAP_BASE_LO = pasm_constant('CHAR_MAP_BASE_LO')
CHAR_MAP_BASE_HI = pasm_constant('CHAR_MAP_BASE_HI')
# G7 content-audit slice: map_base now chains 6 more hops past special_base
# (NEW_MOVE_SLOT_NAMES order) before landing on its final value.
CHAR_ATTACK3_FCOUNT = pasm_constant('CHAR_ATTACK3_FCOUNT')
CHAR_ATTACK4_FCOUNT = pasm_constant('CHAR_ATTACK4_FCOUNT')
CHAR_GRABMOVE_FCOUNT = pasm_constant('CHAR_GRABMOVE_FCOUNT')
CHAR_SLIDE_FCOUNT = pasm_constant('CHAR_SLIDE_FCOUNT')
CHAR_RISEATTACK_FCOUNT = pasm_constant('CHAR_RISEATTACK_FCOUNT')
CHAR_GRABATTACK_FCOUNT = pasm_constant('CHAR_GRABATTACK_FCOUNT')
CHAR_FREESPECIAL_FCOUNT = pasm_constant('CHAR_FREESPECIAL_FCOUNT')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_GRAB_TARGET = pasm_constant('CHAR_GRAB_TARGET')
CHAR_GRABBED_BY = pasm_constant('CHAR_GRABBED_BY')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')

# Player-only jump-family transient fields (see core/jump.pasm) that feed
# the special_base chain -- absolute WRAM cells, not CHAR_ZP_LEN struct
# offsets.
Player_JumpFCount = pasm_constant('Player_JumpFCount')
Player_JumpAttackFCount = pasm_constant('Player_JumpAttackFCount')
Player_JumpAttack2FCount = pasm_constant('Player_JumpAttack2FCount')

CharSelect_Index = 0x7E53B6
CharSelect_Loaded = 0x7E53B8
PlayerEntity = 0x7E0A00
Entity1 = PlayerEntity + CHAR_ZP_LEN
Entity2 = PlayerEntity + CHAR_ZP_LEN * 2
Entity3 = PlayerEntity + CHAR_ZP_LEN * 3

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEO_MOVESET = os.path.join(ROOT, 'out', 'leo_moveset.json')
RALF_MOVESET = os.path.join(ROOT, 'out', 'ralf_moveset.json')

LEO_ROSTER_INDEX = roster().index('leo')  # derived, not hand-copied.


def load_role_frames(moveset_path, role):
    with open(moveset_path, 'r', encoding='utf-8') as f:
        moveset = json.load(f)
    ordinal = moveset['roles'].get(role)
    if ordinal is None:
        return None
    anim = next(a for a in moveset['animations'] if a['ordinal'] == ordinal)
    return anim['frames']


def overlap_entity1_with_player(m):
    px = read_block(m, PlayerEntity + CHAR_POS_X, 32)
    x = px[0] | (px[1] << 8)
    y = read_u8(m, PlayerEntity + CHAR_POS_Y)
    m.write_u16(Entity1 + CHAR_POS_X, x)
    m.write_u8(Entity1 + CHAR_POS_Y, y)


def press_select(m):
    m.set_input(m.BTN_SELECT, 10)
    m.run_frames(40)
    m.pause()


def read_u8(m, addr):
    return read_block(m, addr, 32)[0]


def read_u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def read_u24(m, lo_addr, hi_addr):
    return (read_u8(m, hi_addr) << 16) | read_u16(m, lo_addr)


def player_state(m):
    return {
        'selected': read_u8(m, PlayerEntity + CHAR_SELECTED),
        'variant': read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT),
        'frame_index': read_u8(m, PlayerEntity + CHAR_FRAME_INDEX),
    }


def press_and_poll(m, button, max_frames=40):
    m.set_input(button, 1)
    states = []
    for _ in range(max_frames):
        m.run_frames(1)
        m.pause()
        states.append(player_state(m))
    return states


def main():
    r = Reporter('G7-SPECIAL', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        # This gate is about special DISPATCH mechanics, not combat
        # outcomes -- neutralize the AI entities so the button checks
        # below can't incidentally land a real hit. Same convention as
        # game_g7_attack2.py's own entity-neutralizing.
        m.write_u8(Entity1 + CHAR_HP, 0)
        m.write_u8(Entity2 + CHAR_HP, 0)
        m.write_u8(Entity3 + CHAR_HP, 0)

        # --- Select to LEO (roster slot 12). ---
        for _ in range(LEO_ROSTER_INDEX):
            press_select(m)
        idx = read_u8(m, CharSelect_Index)
        loaded = read_u8(m, CharSelect_Loaded)
        r.check(f'roster selected to LEO (index {LEO_ROSTER_INDEX})',
                idx == LEO_ROSTER_INDEX)
        r.check('CharSelect_Loaded==1 after reselect', loaded == 1)

        # --- 1. LEO's special fields match its real converted data. ---
        leo_sp_fc = read_u8(m, PlayerEntity + CHAR_SPECIAL_FCOUNT)
        leo_sp_delay = read_u8(m, PlayerEntity + CHAR_SPECIAL_DELAY)
        expected_sp_frames = load_role_frames(LEO_MOVESET, 'special')
        print(f'LEO special: fcount={leo_sp_fc} delay={leo_sp_delay} '
              f'(expected frames={expected_sp_frames})')
        r.check('LEO CHAR_SPECIAL_FCOUNT matches its real special frame count',
                leo_sp_fc == expected_sp_frames)
        r.check('LEO CHAR_SPECIAL_FCOUNT is nonzero (has a real special move)',
                leo_sp_fc > 0)

        # --- 2. special_base independently recomputed from attack2_base +
        # (attack2+jump+jumpattack+jumpattack2 fcount)*768. ---
        attack2_base = read_u24(m, PlayerEntity + CHAR_ATTACK2_BASE_LO,
                                 PlayerEntity + CHAR_ATTACK2_BASE_HI)
        attack2_fc = read_u8(m, PlayerEntity + CHAR_ATTACK2_FCOUNT)
        jump_fc = read_u8(m, Player_JumpFCount)
        jumpattack_fc = read_u8(m, Player_JumpAttackFCount)
        jumpattack2_fc = read_u8(m, Player_JumpAttack2FCount)
        expected_special_base = attack2_base + (
            attack2_fc + jump_fc + jumpattack_fc + jumpattack2_fc) * 768

        actual_special_base = read_u24(m, PlayerEntity + CHAR_SPECIAL_BASE_LO,
                                        PlayerEntity + CHAR_SPECIAL_BASE_HI)
        print(f'special_base: actual={actual_special_base} '
              f'expected(attack2_base+sum(fcounts)*768)={expected_special_base} '
              f'(attack2_fc={attack2_fc} jump_fc={jump_fc} '
              f'jumpattack_fc={jumpattack_fc} jumpattack2_fc={jumpattack2_fc})')
        r.check('CHAR_SPECIAL_BASE matches independent recomputation',
                actual_special_base == expected_special_base)

        # --- 3. map_base now chains 8 hops total off special_base: the 6
        # G7 content-audit slice's new generic move slots (NEW_MOVE_SLOT_
        # NAMES order) plus this reopened-again slice's freespecial, then
        # map_base itself. LEO is the only roster member with real data in
        # every new slot but riseattack (that's BEBOP/ROCK/LEATHER's), so
        # this independent recomputation exercises the full real chain.
        leo_a3_fc = read_u8(m, PlayerEntity + CHAR_ATTACK3_FCOUNT)
        leo_a4_fc = read_u8(m, PlayerEntity + CHAR_ATTACK4_FCOUNT)
        leo_gm_fc = read_u8(m, PlayerEntity + CHAR_GRABMOVE_FCOUNT)
        leo_sl_fc = read_u8(m, PlayerEntity + CHAR_SLIDE_FCOUNT)
        leo_ra_fc = read_u8(m, PlayerEntity + CHAR_RISEATTACK_FCOUNT)
        leo_ga_fc = read_u8(m, PlayerEntity + CHAR_GRABATTACK_FCOUNT)
        leo_fs_fc = read_u8(m, PlayerEntity + CHAR_FREESPECIAL_FCOUNT)
        expected_map_base = actual_special_base + (
            leo_sp_fc + leo_a3_fc + leo_a4_fc + leo_gm_fc + leo_sl_fc
            + leo_ra_fc + leo_ga_fc + leo_fs_fc) * 768
        actual_map_base = read_u24(m, PlayerEntity + CHAR_MAP_BASE_LO,
                                    PlayerEntity + CHAR_MAP_BASE_HI)
        print(f'map_base: actual={actual_map_base} expected='
              f'(special_base+sum(special/attack3/attack4/grab/slide/'
              f'riseattack/grabattack/freespecial fc)*768)={expected_map_base} '
              f'(fcounts sp={leo_sp_fc} a3={leo_a3_fc} a4={leo_a4_fc} '
              f'gm={leo_gm_fc} sl={leo_sl_fc} ra={leo_ra_fc} ga={leo_ga_fc} '
              f'fs={leo_fs_fc})')
        r.check('LEO has real content in every new move slot but riseattack',
                leo_a3_fc > 0 and leo_a4_fc > 0 and leo_gm_fc > 0
                and leo_sl_fc > 0 and leo_ga_fc > 0 and leo_fs_fc > 0
                and leo_ra_fc == 0)
        r.check('CHAR_MAP_BASE matches independent recomputation (8-hop chain)',
                actual_map_base == expected_map_base)

        # --- 4. L triggers special: CHAR_SELECTED=2, CHAR_ATTACK_VARIANT=2,
        # runs to completion within bounds, reverts to idle. ---
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        hp_before = read_u8(m, PlayerEntity + CHAR_HP)
        states = press_and_poll(m, m.BTN_L, max_frames=250)
        triggered = next((s for s in states if s['selected'] == 2), None)
        r.check('L press triggers CHAR_SELECTED=2', triggered is not None)
        r.check('L press sets CHAR_ATTACK_VARIANT=2',
                triggered is not None and triggered['variant'] == 2)
        max_frame_seen = max(
            (s['frame_index'] for s in states if s['selected'] == 2 and s['frame_index'] != 0xFF),
            default=-1)
        r.check('special frame index never exceeds its real frame count',
                max_frame_seen < leo_sp_fc)
        reverted = states[-1]['selected'] == 0
        r.check('special completes and reverts CHAR_SELECTED to idle (0)', reverted)

        # --- 5. Free: no HP cost (LEO's real data has no energycost line). ---
        hp_after = read_u8(m, PlayerEntity + CHAR_HP)
        print(f'player HP before/after special: {hp_before} -> {hp_after}')
        r.check('using special deducts no HP (real data: no energycost for LEO)',
                hp_after == hp_before)

        # --- 6. Grab-release-on-trigger, ORGANIC (notjustfreespecial.txt
        # item 8): LEO's real moveset DOES have a `grab` role (12) --
        # Character_HitApply__TryGrab was widened (G7 item 2/3) to accept
        # LEO's CHAR_GRABMOVE_FCOUNT variant (5), not just JOE's attack2_
        # is_grab, so LEO's own R-triggered grab swing lands a REAL
        # mutual-lock hit when it connects, exactly like JOE's. Drive it
        # organically: overlap Entity1 with the player, press R until the
        # link actually establishes (CHAR_GRAB_TARGET != $FF), THEN press
        # L and confirm the special's own grab-release path clears it --
        # no forced WRAM link setup, unlike the prior synthetic version of
        # this check. ---
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)
        m.write_u8(PlayerEntity + CHAR_GRAB_TARGET, 0xFF)
        m.write_u8(Entity1 + CHAR_HIT_STUN, 0)
        m.write_u8(Entity1 + CHAR_GRABBED_BY, 0xFF)
        m.write_u8(Entity1 + CHAR_HP, CHAR_HP_MAX)
        overlap_entity1_with_player(m)
        m.run_frames(4)
        m.pause()

        grab_target = 0xFF
        for attempt in range(5):
            m.set_input(m.BTN_R, 1)
            m.run_frames(1)
            m.pause()
            overlap_entity1_with_player(m)
            grab_target = read_u8(m, PlayerEntity + CHAR_GRAB_TARGET)
            if grab_target != 0xFF:
                break
            m.run_frames(10)
            m.pause()
        grabbed_by = read_u8(m, Entity1 + CHAR_GRABBED_BY)
        print(f'organic R grab attempt {attempt + 1}/5: player.CHAR_GRAB_TARGET='
              f'{grab_target} entity1.CHAR_GRABBED_BY={grabbed_by}')
        r.check("LEO's own R-triggered `grab` swing organically establishes a "
                'real mutual-lock (player.CHAR_GRAB_TARGET != $FF) via the '
                'same Character_HitApply__TryGrab path JOE uses',
                grab_target != 0xFF)

        press_and_poll(m, m.BTN_L, max_frames=30)
        grab_target_after = read_u8(m, PlayerEntity + CHAR_GRAB_TARGET)
        grabbed_by_after = read_u8(m, Entity1 + CHAR_GRABBED_BY)
        print(f'after L with a real, organically-established grab link: '
              f'CHAR_GRAB_TARGET={grab_target_after} '
              f'Entity1.CHAR_GRABBED_BY={grabbed_by_after}')
        r.check('special trigger releases self.CHAR_GRAB_TARGET ($FF)',
                grab_target_after == 0xFF)
        r.check("special trigger releases the victim's own CHAR_GRABBED_BY ($FF)",
                grabbed_by_after == 0xFF)
        m.write_u8(Entity1 + CHAR_HP, 0)

        # --- 7. Regression: Y still triggers attack1, variant 0, unchanged
        # data. ---
        expected_a1_frames = load_role_frames(LEO_MOVESET, 'attack')
        leo_a1_fc = read_u8(m, PlayerEntity + CHAR_ATTACK_FCOUNT)
        r.check("LEO CHAR_ATTACK_FCOUNT (attack1) unchanged by this slice",
                leo_a1_fc == expected_a1_frames)

        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        states_y = press_and_poll(m, m.BTN_Y, max_frames=10)
        triggered_y = next((s for s in states_y if s['selected'] == 2), None)
        r.check('Y press triggers CHAR_SELECTED=2', triggered_y is not None)
        r.check('Y press sets CHAR_ATTACK_VARIANT=0 (attack1, not special)',
                triggered_y is not None and triggered_y['variant'] == 0)

        # --- 8. RALF has no special move -- L must no-op. ---
        press_select(m)  # LEO(12) -> wrap -> RALF(0)
        idx_ralf = read_u8(m, CharSelect_Index)
        r.check('roster selected to RALF (index 0)', idx_ralf == 0)
        ralf_sp_fc = read_u8(m, PlayerEntity + CHAR_SPECIAL_FCOUNT)
        expected_ralf_sp = load_role_frames(RALF_MOVESET, 'special')
        r.check('RALF CHAR_SPECIAL_FCOUNT==0 (real data: no special move)',
                ralf_sp_fc == 0 and expected_ralf_sp is None)

        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        states_none = press_and_poll(m, m.BTN_L, max_frames=20)
        r.check('L press on RALF never triggers CHAR_SELECTED=2 (no crash, no-op)',
                all(s['selected'] != 2 for s in states_none))

    r.finish()


if __name__ == '__main__':
    main()
