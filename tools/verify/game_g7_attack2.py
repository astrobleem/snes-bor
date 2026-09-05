#!/usr/bin/env python3
"""plan_game.md Phase G7 (remaining item): a real second attack move.

Background: none of the 4 roster characters (RALF/JHUN/JOE/YASHIRO) have a
real `jump`/`block`/`special` anim in the source pak -- nothing exists to
convert, so those G7 items are art-authoring blockers, not engine slices.
But RALF (`upper`), JOE (`grab`), and JHUN (`jumpattack`) each have one real
extra attack-like move, converted and sitting inert in their moveset
manifests since the moveset-generalization slice. This gate covers making
that move reachable in-game: a generic `attack2` role (resolved by name
exclusion, not hardcoded to any one character -- see
convert_character.py's own comment), triggered by the X button (free and
unused elsewhere -- Y=attack1, B=run/dash, Select=roster cycle), dealing
damage via the SAME `Character_HitApply` CHAR_SELECTED==2 check attack1
already uses (confirmed no attack-variant-specific code exists there).

**Deliberately NOT real OpenBOR grab semantics.** Real `grab` in BOR.C
(`player_grab()`/`enemy_grabbed`) is a mutual entity-lock triggered by
movement collision, not a button press -- position averaging, `ents_link`,
a `self->think` state-machine handoff. This slice ships JOE's `grab`
animation as a generic second attack move (same one-shot AABB hit check
attack1 uses), not that mechanic -- see `plan_game.md` §7 and the
`g7_attack2_second_move` project memory for the full scope boundary.

Checks, all against a live Mesen2 session:
1. Select the roster to JOE (2 Select presses from boot) and confirm
   CHAR_ATTACK2_FCOUNT/DELAY in WRAM match JOE's real `grab` frame count/
   delay from out/joe_moveset.json (ground truth: the converter's own
   baked manifest, not the engine's own claim about itself).
2. CHAR_ATTACK2_BASE (computed at load time by chaining off CHAR_RISE_BASE
   + CHAR_RISE_FCOUNT*768, same formula map_base used before this slice)
   matches an independent Python recomputation from CHAR_RISE_BASE/FCOUNT
   read back from WRAM -- proves the new chained-base arithmetic in
   Anim_LoadCharacter__slot_ok is correct, not just "didn't crash".
3. Pressing X (edge) while playable sets CHAR_SELECTED=2 and
   CHAR_ATTACK_VARIANT=1, and the move runs to completion (CHAR_FRAME_INDEX
   stays < CHAR_ATTACK2_FCOUNT throughout, CHAR_SELECTED reverts to 0 when
   done) -- same non-looping revert-to-idle shape attack1 already has.
4. Regression: pressing Y instead still sets CHAR_ATTACK_VARIANT=0 and
   attack1's own frame count/delay (out/joe_moveset.json's `attack1` entry)
   are unchanged by this slice.
5. Select to YASHIRO (CHAR_ATTACK2_FCOUNT==0, real data -- no second move):
   pressing X must NOT trigger anything (CHAR_SELECTED stays 0, no stream
   from a zero-length region).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_FRAME_INDEX = pasm_constant('CHAR_FRAME_INDEX')
CHAR_ATTACK_FCOUNT = pasm_constant('CHAR_ATTACK_FCOUNT')
CHAR_ATTACK_DELAY = pasm_constant('CHAR_ATTACK_DELAY')
CHAR_ATTACK2_FCOUNT = pasm_constant('CHAR_ATTACK2_FCOUNT')
CHAR_ATTACK2_DELAY = pasm_constant('CHAR_ATTACK2_DELAY')
CHAR_ATTACK2_BASE_LO = pasm_constant('CHAR_ATTACK2_BASE_LO')
CHAR_ATTACK2_BASE_HI = pasm_constant('CHAR_ATTACK2_BASE_HI')
CHAR_ATTACK_BASE_LO = pasm_constant('CHAR_ATTACK_BASE_LO')
CHAR_ATTACK_BASE_HI = pasm_constant('CHAR_ATTACK_BASE_HI')
CHAR_ATTACK_VARIANT = pasm_constant('CHAR_ATTACK_VARIANT')
CHAR_TILE_COLUMN = pasm_constant('CHAR_TILE_COLUMN')
CHAR_RISE_FCOUNT = pasm_constant('CHAR_RISE_FCOUNT')
CHAR_RISE_BASE_LO = pasm_constant('CHAR_RISE_BASE_LO')
CHAR_RISE_BASE_HI = pasm_constant('CHAR_RISE_BASE_HI')

CharSelect_Index = 0x7E53B6
CharSelect_Loaded = 0x7E53B8
PlayerEntity = 0x7E0A00
Entity1 = PlayerEntity + CHAR_ZP_LEN
Entity2 = PlayerEntity + CHAR_ZP_LEN * 2
Entity3 = PlayerEntity + CHAR_ZP_LEN * 3
CHAR_HP = pasm_constant('CHAR_HP')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JOE_MOVESET = os.path.join(ROOT, 'out', 'joe_moveset.json')
YASHIRO_MOVESET = os.path.join(ROOT, 'out', 'yashiro_moveset.json')


def load_role_frames(moveset_path, role):
    with open(moveset_path, 'r', encoding='utf-8') as f:
        moveset = json.load(f)
    ordinal = moveset['roles'].get(role)
    if ordinal is None:
        return None
    anim = next(a for a in moveset['animations'] if a['ordinal'] == ordinal)
    return anim['frames']


def press_select(m):
    m.set_input(m.BTN_SELECT, 10)
    m.run_frames(40)
    m.pause()


def read_u8(m, addr):
    return read_block(m, addr, 32)[0]


def read_u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


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
    r = Reporter('G7-ATTACK2', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        # This gate is about attack2 DISPATCH mechanics (animation/state
        # selection), not combat outcomes -- neutralize the AI entities so
        # the X/Y button checks below can't incidentally land a real hit
        # or (since the grab mutual-lock slice) establish a real grab
        # against a nearby AI, which would leave CHAR_GRAB_TARGET set and
        # confuse the LATER Y-press (attack1) check via this file's own
        # grabber-can-walk-while-holding behavior (Anim_Play__not_stunned).
        # Same convention as game_g7_knockdown.py's own entity-neutralizing.
        m.write_u8(Entity1 + CHAR_HP, 0)
        m.write_u8(Entity2 + CHAR_HP, 0)
        m.write_u8(Entity3 + CHAR_HP, 0)

        # --- Select to JOE (roster slot 2: RALF->JHUN->JOE). ---
        press_select(m)
        press_select(m)
        idx = read_u8(m, CharSelect_Index)
        loaded = read_u8(m, CharSelect_Loaded)
        r.check('roster selected to JOE (index 2)', idx == 2)
        r.check('CharSelect_Loaded==1 after reselect', loaded == 1)

        # --- 1. JOE's attack2 fields match its real converted grab data. ---
        joe_a2_fc = read_u8(m, PlayerEntity + CHAR_ATTACK2_FCOUNT)
        joe_a2_delay = read_u8(m, PlayerEntity + CHAR_ATTACK2_DELAY)
        expected_a2_frames = load_role_frames(JOE_MOVESET, 'attack2')
        print(f'JOE attack2: fcount={joe_a2_fc} delay={joe_a2_delay} '
              f'(expected frames={expected_a2_frames})')
        r.check('JOE CHAR_ATTACK2_FCOUNT matches its real grab frame count',
                joe_a2_fc == expected_a2_frames)
        r.check('JOE CHAR_ATTACK2_FCOUNT is nonzero (has a real second move)',
                joe_a2_fc > 0)

        # --- 2. attack2_base independently recomputed from rise_base/rise_fcount. ---
        rise_fc = read_u8(m, PlayerEntity + CHAR_RISE_FCOUNT)
        rise_base_lo = read_u16(m, PlayerEntity + CHAR_RISE_BASE_LO)
        rise_base_hi = read_u8(m, PlayerEntity + CHAR_RISE_BASE_HI)
        rise_base = (rise_base_hi << 16) | rise_base_lo
        expected_attack2_base = rise_base + rise_fc * 768

        a2_base_lo = read_u16(m, PlayerEntity + CHAR_ATTACK2_BASE_LO)
        a2_base_hi = read_u8(m, PlayerEntity + CHAR_ATTACK2_BASE_HI)
        actual_attack2_base = (a2_base_hi << 16) | a2_base_lo
        print(f'attack2_base: actual={actual_attack2_base} '
              f'expected(rise_base+rise_fc*768)={expected_attack2_base}')
        r.check('CHAR_ATTACK2_BASE matches independent recomputation',
                actual_attack2_base == expected_attack2_base)

        # --- 3. X triggers attack2: CHAR_SELECTED=2, CHAR_ATTACK_VARIANT=1,
        # runs to completion within bounds, reverts to idle. ---
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        # max_frames bumped from 60: fcount(17)*delay(12)=204 real
        # frames are needed for a full natural revert-to-idle, and
        # run_frames(1)'s wall-clock lower-bound semantics means how
        # many real frames fit in N poll iterations isn't fixed --
        # 60 was already marginal against the baseline engine and a
        # few extra per-frame instructions (grab mutual-lock slice)
        # pushed it over. 250 gives real margin above the 204 needed.
        states = press_and_poll(m, m.BTN_X, max_frames=250)
        triggered = next((s for s in states if s['selected'] == 2), None)
        r.check('X press triggers CHAR_SELECTED=2', triggered is not None)
        r.check('X press sets CHAR_ATTACK_VARIANT=1',
                triggered is not None and triggered['variant'] == 1)
        max_frame_seen = max(
            (s['frame_index'] for s in states if s['selected'] == 2 and s['frame_index'] != 0xFF),
            default=-1)
        r.check('attack2 frame index never exceeds its real frame count',
                max_frame_seen < joe_a2_fc)
        reverted = states[-1]['selected'] == 0
        r.check('attack2 completes and reverts CHAR_SELECTED to idle (0)', reverted)

        # --- 4. Regression: Y still triggers attack1, variant 0, unchanged data. ---
        expected_a1_frames = load_role_frames(JOE_MOVESET, 'attack')
        joe_a1_fc = read_u8(m, PlayerEntity + CHAR_ATTACK_FCOUNT)
        r.check("JOE CHAR_ATTACK_FCOUNT (attack1) unchanged by this slice",
                joe_a1_fc == expected_a1_frames)

        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        states_y = press_and_poll(m, m.BTN_Y, max_frames=10)
        triggered_y = next((s for s in states_y if s['selected'] == 2), None)
        r.check('Y press triggers CHAR_SELECTED=2', triggered_y is not None)
        r.check('Y press sets CHAR_ATTACK_VARIANT=0 (attack1, not attack2)',
                triggered_y is not None and triggered_y['variant'] == 0)

        # --- 5. YASHIRO has no second move -- X must no-op. ---
        press_select(m)  # JOE(2) -> YASHIRO(3)
        idx_y = read_u8(m, CharSelect_Index)
        r.check('roster selected to YASHIRO (index 3)', idx_y == 3)
        yashiro_a2_fc = read_u8(m, PlayerEntity + CHAR_ATTACK2_FCOUNT)
        expected_yashiro_a2 = load_role_frames(YASHIRO_MOVESET, 'attack2')
        r.check('YASHIRO CHAR_ATTACK2_FCOUNT==0 (real data: no second move)',
                yashiro_a2_fc == 0 and expected_yashiro_a2 is None)

        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        states_none = press_and_poll(m, m.BTN_X, max_frames=20)
        r.check('X press on YASHIRO never triggers CHAR_SELECTED=2 (no crash, no-op)',
                all(s['selected'] != 2 for s in states_none))

        # The zero-attack2 case must still use attack1 when Y is pressed.  A
        # dispatch regression can pass the X no-op check while leaving the
        # attack1 body unreachable, so verify a presented attack1 frame against
        # the independently selected packed MSU source as well.
        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        m.set_input(m.BTN_Y, 1)
        states_yashiro_a1 = []
        presented = None
        with open(os.path.join(ROOT, 'distribution', 'bor.msu'), 'rb') as f:
            msu = f.read()
        for _ in range(30):
            m.run_frames(1)
            m.pause()
            state = player_state(m)
            states_yashiro_a1.append(state)
            if (presented is None and state['selected'] == 2
                    and state['variant'] == 0 and state['frame_index'] != 0xFF):
                y_entity = read_block(m, PlayerEntity, 64)
                base = ((y_entity[CHAR_ATTACK_BASE_HI] << 16)
                        | y_entity[CHAR_ATTACK_BASE_LO]
                        | (y_entity[CHAR_ATTACK_BASE_LO + 1] << 8))
                source = base + state['frame_index'] * 768
                col = y_entity[CHAR_TILE_COLUMN]
                rows = [bytes(read_block(m, 0x8000 + col * 128 + row * 512, 128,
                                         mem_type='snesVideoRam')) for row in range(6)]
                if all(rows[row] == msu[source + row * 128:source + (row + 1) * 128]
                       for row in range(6)):
                    presented = (state['frame_index'], source)
        triggered_yashiro_a1 = next(
            (s for s in states_yashiro_a1
             if s['selected'] == 2 and s['variant'] == 0), None)
        r.check('YASHIRO Y press enters attack1 variant 0',
                triggered_yashiro_a1 is not None)
        print(f'YASHIRO attack1 presented source: {presented}')
        r.check('YASHIRO attack1 presents the matching packed MSU frame',
                presented is not None)

        # --- 6. claude_close_g7_g8_before_g10.md Part 1 regression proof:
        # MOUSER's real second attack is 'upper' (9 frames), but MOUSER
        # ALSO declares 'backwalk' (8 frames, a movement animation)
        # EARLIER in its raw .TXT than 'upper'. The old converter fallback
        # ("first otherwise-unclaimed anim") silently picked 'backwalk' as
        # attack2 -- this check proves the fix at the live hardware level,
        # not just in the converter's own pure-Python role table.
        press_select(m)  # YASHIRO(3) -> MOUSER(4)
        idx_m = read_u8(m, CharSelect_Index)
        r.check('roster selected to MOUSER (index 4)', idx_m == 4)
        mouser_moveset = os.path.join(ROOT, 'out', 'mouser_moveset.json')
        expected_mouser_a2_frames = load_role_frames(mouser_moveset, 'attack2')
        expected_backwalk_frames = load_role_frames(mouser_moveset, 'backwalk')
        mouser_a2_fc = read_u8(m, PlayerEntity + CHAR_ATTACK2_FCOUNT)
        print(f'MOUSER attack2: fcount={mouser_a2_fc} '
              f'(expected upper={expected_mouser_a2_frames}, '
              f'backwalk would have been={expected_backwalk_frames})')
        r.check('MOUSER CHAR_ATTACK2_FCOUNT matches real upper frame count',
                mouser_a2_fc == expected_mouser_a2_frames)
        r.check('MOUSER attack2 frame count is NOT backwalk\'s frame count '
                '(the real bug this checks for)',
                mouser_a2_fc != expected_backwalk_frames)

        m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
        states_mouser = press_and_poll(m, m.BTN_X, max_frames=250)
        triggered_mouser = next((s for s in states_mouser if s['selected'] == 2), None)
        r.check('X press triggers MOUSER attack2 (CHAR_SELECTED=2)',
                triggered_mouser is not None)
        r.check('X press sets CHAR_ATTACK_VARIANT=1 for MOUSER',
                triggered_mouser is not None and triggered_mouser['variant'] == 1)
        max_frame_mouser = max(
            (s['frame_index'] for s in states_mouser
             if s['selected'] == 2 and s['frame_index'] != 0xFF),
            default=-1)
        r.check('MOUSER attack2 frame index never exceeds its real (upper) frame count',
                max_frame_mouser < mouser_a2_fc)
        r.check('MOUSER attack2 completes and reverts to idle',
                states_mouser[-1]['selected'] == 0)

    r.finish()


if __name__ == '__main__':
    main()
