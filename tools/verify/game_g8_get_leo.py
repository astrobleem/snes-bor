#!/usr/bin/env python3
"""claude_close_g7_g8_before_g10.md Part 2: LEO's real converted `get`
pickup animation, end to end.

Background: the ledger classified LEO's `get` animation as partial/
unhandled despite LEO having real converted content for it (TMNT pak,
data\\CHARS\\LEO\\LEO.TXT: `anim get / loop 0 / offset 70 195 / delay 1 /
frame data/chars/leo/still01.gif`). Real OpenBOR source (engine/openbor.c)
traced end to end for this slice:
- player_test_pickable()/player_test_touch() (~line 34631-34719): an item
  WITHOUT `subtype touch` (APPLE.TXT/MEAT.TXT/MONEY.TXT/1UP.TXT all lack
  a `subtype` line -- confirmed by direct pak extraction) is collected via
  overlap; a character with a real ANI_GET plays a cosmetic pickup pose,
  one lacking it just silently collects (same instant path as before this
  slice).
- didfind_item() (~line 44753): the reward (health/score/1up) is applied
  INSTANTLY at pickup detection, never gated on the GET animation
  completing -- the animation is cosmetic (stop movement, play the pose),
  not a delay on the reward.

This slice (src/core/jump.pasm's Character_Pickup_CheckOverlap__TriggerGet
+ Jump_PlayGetAdvance, src/main.pasm's CHAR_GET_FCOUNT/DELAY/BASE_LO/HI
fields + GET_MOVE_VARIANT=10) wires exactly that: on touch-collect, if the
player's own converted character has PlayerEntity_GetFcount != 0 and is
currently idle (PlayerEntity_Selected == 0), enter CHAR_SELECTED=2 /
CHAR_ATTACK_VARIANT=GET_MOVE_VARIANT and play the real GET frames to
completion before reverting to idle; a character with no real GET data
(GetFcount==0) just collects with no animation, unchanged from before.

Checks, all against a live Mesen2 session, using LEO (roster slot 12, the
only roster member with real `get` data) and a real shipped item type
(PICKUP_TYPE_APPLE, forced onto entity 2 the same way game_g8_pickup.py's
own gate does -- APPLE.TXT is real, shipped, buildable pak content):
1. LEO's PlayerEntity_GetFcount is nonzero (real converted data reached
   WRAM, not still 0/unhandled).
2. Touching a real item while idle enters CHAR_SELECTED=2 with
   CHAR_ATTACK_VARIANT==GET_MOVE_VARIANT (the real pickup/get state, not
   ordinary attack1/attack2).
3. Movement is constrained during the pose: player CHAR_POS_X does not
   change while the GET animation is playing, even with dpad held.
4. The reward (APPLE heal) is already applied at the moment the animation
   starts (real didfind_item() timing -- cosmetic-only animation), not
   deferred until it completes.
5. CHAR_PICKUP_TYPE is cleared immediately (item consumed exactly once).
6. The animation runs to real completion (CHAR_FRAME_INDEX stays within
   CHAR_GET_FCOUNT) and CHAR_SELECTED reverts to a valid idle/walk state
   (0 or 1), not stuck.
7. Fallback: RALF (GetFcount==0, no real `get` anim) collects the same
   real item instantly with NO state transition (CHAR_SELECTED stays 0
   throughout) -- the source-defined fallback for a character lacking
   ANI_GET, not a fabricated animation.

Usage: python tools/verify/game_g8_get_leo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_ATTACK_VARIANT = pasm_constant('CHAR_ATTACK_VARIANT')
CHAR_FRAME_INDEX = pasm_constant('CHAR_FRAME_INDEX')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_HIT_APPLIED = pasm_constant('CHAR_HIT_APPLIED')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_PICKUP_TYPE = pasm_constant('CHAR_PICKUP_TYPE')
CHAR_GET_FCOUNT = pasm_constant('CHAR_GET_FCOUNT')
CHAR_INPUT_DRIVEN_PROP = pasm_constant_in('src/main.pasm', 'CHAR_INPUT_DRIVEN_PROP')

PICKUP_TYPE_APPLE = pasm_constant('PICKUP_TYPE_APPLE')
PICKUP_HEAL_APPLE = pasm_constant('PICKUP_HEAL_APPLE')
GET_MOVE_VARIANT = pasm_constant('GET_MOVE_VARIANT')

SPAWN_PATH = 'src/core/spawn.pasm'
Entity2_ItemRosterIdx = pasm_constant_in(SPAWN_PATH, 'Entity2_ItemRosterIdx')

GS_PATH = 'src/core/game_state.pasm'
Entity1_InvulnFrames = pasm_constant_in(GS_PATH, 'Entity1_InvulnFrames')

CharSelect_Index = 0x7E53B6

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
PlayerEntity = ENTITY_BASES[0]
Entity1 = ENTITY_BASES[1]
Entity2 = ENTITY_BASES[2]
Entity3 = ENTITY_BASES[3]

READ_LEN = 160


def read_u8(m, addr):
    return read_block(m, addr, 32)[0]


def read_u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def entity_block(m, base):
    return read_block(m, base, READ_LEN)


def pos_x(blk):
    return blk[CHAR_POS_X] | (blk[CHAR_POS_X + 1] << 8)


def press_select(m):
    m.set_input(m.BTN_SELECT, 10)
    m.run_frames(20)
    m.pause()


def load_char_onto_player(m, index, max_presses=20):
    """Real in-game character-select reselect, same live path game_g7_
    jump.py/game_g7_special.py/phase12_roster.py already use -- not a
    synthetic write of animation data."""
    for _ in range(max_presses):
        idx = read_u8(m, CharSelect_Index)
        if idx == index:
            return
        press_select(m)
    raise AssertionError(f'CharSelect_Index never reached {index} after '
                          f'{max_presses} Select presses (stuck at '
                          f'{read_u8(m, CharSelect_Index)})')


def neutralize_ai(m):
    m.write_u8(Entity1 + CHAR_HP, 0)
    m.write_u8(Entity3 + CHAR_HP, 0)
    m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)


def overlap_entity2_with_player(m):
    px = entity_block(m, PlayerEntity)
    x = pos_x(px)
    y = px[CHAR_POS_Y]
    m.write_u16(Entity2 + CHAR_POS_X, x)
    m.write_u8(Entity2 + CHAR_POS_Y, y)


def poll_until(m, predicate, max_frames):
    for _ in range(max_frames):
        if predicate():
            return True
        m.run_frames(1)
        m.pause()
    return predicate()


def arm_apple_item(m, player_hp):
    m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
    m.write_u8(PlayerEntity + CHAR_HIT_APPLIED, 0)
    m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)
    m.write_u8(PlayerEntity + CHAR_HP, player_hp)
    m.write_u8(Entity2 + CHAR_INPUT_DRIVEN, CHAR_INPUT_DRIVEN_PROP)
    m.write_u8(Entity2 + CHAR_HP, 1)
    m.write_u8(Entity2 + CHAR_PICKUP_TYPE, PICKUP_TYPE_APPLE)
    m.write_u8(Entity2_ItemRosterIdx, 0)
    # Keep entity 2 well clear of the player until the exact moment each
    # scenario wants the touch-collect to fire.
    m.write_u16(Entity2 + CHAR_POS_X, 4000)


def main():
    r = Reporter('G8-GET-LEO', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()

        load_char_onto_player(m, 12)  # LEO
        neutralize_ai(m)
        m.write_u8(Entity1_InvulnFrames, 0)

        leo_get_fc = read_u8(m, PlayerEntity + CHAR_GET_FCOUNT)
        print(f'LEO PlayerEntity_GetFcount={leo_get_fc}')
        r.check('LEO has real converted `get` animation data in WRAM '
                '(PlayerEntity_GetFcount != 0)', leo_get_fc != 0)

        # --- 1/2. Touching a real item while idle enters the real GET
        # state, not ordinary attack. ---
        arm_apple_item(m, player_hp=10)
        neutralize_ai(m)
        overlap_entity2_with_player(m)
        entered = poll_until(
            m, lambda: read_u8(m, PlayerEntity + CHAR_SELECTED) == 2,
            max_frames=10)
        sel = read_u8(m, PlayerEntity + CHAR_SELECTED)
        variant = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
        print(f'after touch: CHAR_SELECTED={sel} CHAR_ATTACK_VARIANT={variant}')
        r.check('touching a real item while idle enters CHAR_SELECTED==2 '
                '(the get/attack dispatch value)', entered)
        r.check('CHAR_ATTACK_VARIANT==GET_MOVE_VARIANT (the real, dedicated '
                'get pose, not attack1/attack2)', variant == GET_MOVE_VARIANT)

        # --- 3. Movement constrained: CHAR_POS_X doesn't move even with
        # dpad held while the pose plays. ---
        pos_before = read_u16(m, PlayerEntity + CHAR_POS_X)
        m.set_input(m.BTN_RIGHT, 3)
        m.run_frames(1)
        m.pause()
        pos_after = read_u16(m, PlayerEntity + CHAR_POS_X)
        sel_mid = read_u8(m, PlayerEntity + CHAR_SELECTED)
        print(f'during get pose (still selected={sel_mid}): pos_x '
              f'{pos_before}->{pos_after} with dpad held')
        r.check('player CHAR_POS_X does not move during the get pose even '
                'with the dpad held (movement constrained, real Character_'
                'PlayFrame gating on CHAR_SELECTED!=0)',
                sel_mid != 2 or pos_after == pos_before)

        # --- 4/5. Reward already applied + item consumed, at trigger time
        # (real didfind_item() cosmetic-only-animation timing). ---
        hp_now = read_u8(m, PlayerEntity + CHAR_HP)
        pickup_type_now = read_u8(m, Entity2 + CHAR_PICKUP_TYPE)
        print(f'mid-pose: player CHAR_HP={hp_now} (expect '
              f'{min(CHAR_HP_MAX, 10 + PICKUP_HEAL_APPLE)}), '
              f'Entity2 CHAR_PICKUP_TYPE={pickup_type_now}')
        r.check('APPLE reward is already applied to CHAR_HP before the get '
                'pose finishes (reward is instant, animation is cosmetic)',
                hp_now == min(CHAR_HP_MAX, 10 + PICKUP_HEAL_APPLE))
        r.check('CHAR_PICKUP_TYPE cleared immediately (item consumed '
                'exactly once)', pickup_type_now == 0)

        # --- 6. Real completion: frame index stays in range, reverts to a
        # valid idle/walk state. ---
        frames_seen = []
        completed = False
        for _ in range(30):
            neutralize_ai(m)
            fi = read_u8(m, PlayerEntity + CHAR_FRAME_INDEX)
            sel_now = read_u8(m, PlayerEntity + CHAR_SELECTED)
            frames_seen.append(fi)
            if sel_now != 2:
                completed = True
                break
            m.run_frames(1)
            m.pause()
        sel_final = read_u8(m, PlayerEntity + CHAR_SELECTED)
        print(f'get pose frames observed: {frames_seen[:8]} '
              f'(CHAR_GET_FCOUNT={leo_get_fc}) completed={completed} '
              f'final CHAR_SELECTED={sel_final}')
        r.check('get pose completes within a bounded frame count (not '
                'stuck)', completed)
        r.check('every observed frame index stayed within CHAR_GET_FCOUNT',
                all(fi < leo_get_fc for fi in frames_seen if fi != 0xFF))
        r.check('CHAR_SELECTED reverts to a valid idle/walk state (0 or 1) '
                'once the get pose completes', sel_final in (0, 1))

        # --- 7. Fallback: RALF (no real get data) collects the same real
        # item instantly, no state transition. ---
        load_char_onto_player(m, 0)  # RALF
        neutralize_ai(m)
        ralf_get_fc = read_u8(m, PlayerEntity + CHAR_GET_FCOUNT)
        print(f'RALF PlayerEntity_GetFcount={ralf_get_fc}')
        r.check('RALF has no real converted `get` animation data '
                '(the source-defined-fallback scenario)', ralf_get_fc == 0)

        arm_apple_item(m, player_hp=10)
        neutralize_ai(m)
        overlap_entity2_with_player(m)
        sel_seen = set()
        for _ in range(10):
            neutralize_ai(m)
            sel_seen.add(read_u8(m, PlayerEntity + CHAR_SELECTED))
            m.run_frames(1)
            m.pause()
        hp_ralf = read_u8(m, PlayerEntity + CHAR_HP)
        pickup_type_ralf = read_u8(m, Entity2 + CHAR_PICKUP_TYPE)
        print(f'RALF touch-collect: CHAR_SELECTED samples={sel_seen} '
              f'hp={hp_ralf} pickup_type={pickup_type_ralf}')
        r.check('RALF collects the same real item with the effect still '
                'applied (fallback still functions, just cosmetically bare)',
                hp_ralf == min(CHAR_HP_MAX, 10 + PICKUP_HEAL_APPLE)
                and pickup_type_ralf == 0)
        r.check('RALF never enters CHAR_SELECTED==2 for the pickup (no '
                'fabricated animation for a character with no real get '
                'data -- the correct source-defined fallback)',
                2 not in sel_seen)

    r.finish()


if __name__ == '__main__':
    main()
