#!/usr/bin/env python3
"""plan_game.md G7 (notjustfreespecial.txt item 6): full riseattack coverage.

Background: game_g7_content_audit.py originally only exercised BEBOP's real
`riseattack` (UP+Y while lying, real player_lie_check(), engine/openbor.c).
ROCK and LEATHER both ship real riseattack data too (same converted-pak
ground truth as BEBOP) and were never independently driven. Split into its
own standalone gate (not folded back into game_g7_content_audit.py) because
that file's own long chain of set_input calls by the time it would reach a
6th/7th roster reselect deterministically starved this section's own
set_input calls -- a real instance of the documented
mesen_set_input_wall_clock harness gap (set_input can silently stop
delivering an edge at all after enough prior calls in one long session), not
a per-character animation bug. A fresh session for just this section
sidesteps it entirely.

Covers, for BEBOP, ROCK, and LEATHER independently:
1. Real CHAR_RISEATTACK_FCOUNT ground truth against the converted moveset.
2. Rejection outside the lie window: UP+Y while NOT CHAR_SELECTED_FALL never
   lands on riseattack's own move-slot variant (7).
3. Rejection during the terminal dead-blink fall state
   (CHAR_FALL_STATE_TIMER==$FF, even though CHAR_SELECTED is still FALL).
4. Real trigger during the holding phase (HP>0, FALL_STATE_TIMER mid-range):
   CHAR_ATTACK_VARIANT reaches 7, CHAR_FALL_STATE_TIMER resets to 0 (no
   dangling fall-hold state left behind).
5. Real damage: riseattack's swing deals damage via the shared CHAR_
   SELECTED==2 hit check, same as every other attack in this project.

AI reachability (BEBOP/ROCK/LEATHER are primarily AI-driven bosses/enemies
in real shipped content): Jump_RiseattackTrigger is gated on CHAR_INPUT_
DRIVEN==1 (player only) by explicit, sourced design -- real BOR.C's
player_lie_check() is called from the player's own think()/playerframe()
path only, never from any AI think function (aithink()/candeal()-family);
there is no real "AI decides to rise-attack" mechanism in the source to
port. This is a content-inapplicable classification for the AI side, not an
unbuilt feature -- matching this project's own established `land`/`block`
precedent of only building what real source actually specifies.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, read_block, Reporter, roster  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_ATTACK_VARIANT = pasm_constant('CHAR_ATTACK_VARIANT')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_FALL_STATE_TIMER = pasm_constant('CHAR_FALL_STATE_TIMER')
CHAR_RISEATTACK_FCOUNT = pasm_constant('CHAR_RISEATTACK_FCOUNT')

CharSelect_Index = 0x7E53B6
PlayerEntity = 0x7E0A00
Entity1 = PlayerEntity + CHAR_ZP_LEN

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Gate/test hygiene (notjustfreespecial.txt): derived from build_rom.py's
# own ROSTER_PREFIXES, not a hand-copied literal.
ROSTER = roster()


def load_role_frames(prefix, role):
    import json
    with open(os.path.join(ROOT, 'out', f'{prefix}_moveset.json'), 'r', encoding='utf-8') as f:
        moveset = json.load(f)
    ordinal = moveset['roles'].get(role)
    if ordinal is None:
        return None
    anim = next(a for a in moveset['animations'] if a['ordinal'] == ordinal)
    return anim['frames']


def read_u8(m, addr):
    return read_block(m, addr, 32)[0]


def select_to(m, count):
    for _ in range(count):
        m.set_input(m.BTN_SELECT, 10)
        m.run_frames(40)
        m.pause()


def clear_stun(m, entity):
    m.write_u8(entity + CHAR_HIT_STUN, 0)


def main():
    r = Reporter('G7-RISEATTACK', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()
        m.write_u8(Entity1 + CHAR_HP, 0)  # neutralize background AI combat

        for riseattack_char in ('bebop', 'rock', 'leather'):
            idx = read_u8(m, CharSelect_Index)
            roster_count = len(ROSTER)
            char_index = ROSTER.index(riseattack_char)
            steps = (char_index - idx) % roster_count
            select_to(m, steps)
            idx = read_u8(m, CharSelect_Index)
            r.check(f'roster selected to {riseattack_char.upper()} (index {char_index})',
                    idx == char_index)

            real_riseattack_frames = load_role_frames(riseattack_char, 'riseattack')
            riseattack_fc = read_u8(m, PlayerEntity + CHAR_RISEATTACK_FCOUNT)
            r.check(f'{riseattack_char.upper()} CHAR_RISEATTACK_FCOUNT matches its '
                    f'real converted `riseattack` frame count',
                    riseattack_fc == real_riseattack_frames and riseattack_fc > 0)

            # --- rejection outside the lie window: NOT currently FALL. ---
            clear_stun(m, PlayerEntity)
            m.write_u8(PlayerEntity + CHAR_SELECTED, 0)  # idle, not lying
            m.write_u8(PlayerEntity + CHAR_FALL_STATE_TIMER, 50)
            m.write_u8(PlayerEntity + CHAR_HP, 60)
            m.run_frames(20)
            m.pause()
            m.set_input(m.BTN_UP | m.BTN_Y, 1)
            m.run_frames(2)
            m.pause()
            var_not_lying = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
            r.check(f'{riseattack_char.upper()}: UP+Y while NOT lying never '
                    f'triggers riseattack specifically (CHAR_ATTACK_VARIANT != 7)',
                    var_not_lying != 7)

            # --- rejection: terminal dead-blink state (CHAR_FALL_STATE_TIMER
            #     == $FF), even though CHAR_SELECTED==FALL. ---
            clear_stun(m, PlayerEntity)
            m.write_u8(PlayerEntity + CHAR_SELECTED, 3)  # CHAR_SELECTED_FALL
            m.write_u8(PlayerEntity + CHAR_FALL_STATE_TIMER, 0xFF)
            m.write_u8(PlayerEntity + CHAR_HP, 60)
            m.run_frames(20)
            m.pause()
            m.set_input(m.BTN_UP | m.BTN_Y, 1)
            m.run_frames(2)
            m.pause()
            sel_terminal = read_u8(m, PlayerEntity + CHAR_SELECTED)
            r.check(f'{riseattack_char.upper()}: UP+Y during the terminal dead-blink '
                    f'fall state (CHAR_FALL_STATE_TIMER=$FF) never triggers '
                    f'riseattack', sel_terminal == 3)

            # --- real trigger + damage, holding phase, HP>0. ---
            clear_stun(m, PlayerEntity)
            m.write_u8(PlayerEntity + CHAR_SELECTED, 3)  # CHAR_SELECTED_FALL
            m.write_u8(PlayerEntity + CHAR_FALL_STATE_TIMER, 50)  # holding phase
            m.write_u8(PlayerEntity + CHAR_HP, 60)
            pos = read_block(m, PlayerEntity + 4, 32)
            world_x = pos[0] | (pos[1] << 8)
            world_y = pos[2]
            m.write_u16(Entity1 + 4, world_x)
            m.write_u8(Entity1 + 6, world_y)
            m.write_u8(Entity1 + CHAR_HP, 64)
            clear_stun(m, Entity1)

            m.run_frames(20)
            m.pause()
            var = 0
            fall_timer = 50
            for attempt in range(3):
                m.set_input(m.BTN_UP | m.BTN_Y, 1)
                m.run_frames(1)
                m.pause()
                var = read_u8(m, PlayerEntity + CHAR_ATTACK_VARIANT)
                fall_timer = read_u8(m, PlayerEntity + CHAR_FALL_STATE_TIMER)
                if var == 7:
                    break
                print(f'  {riseattack_char.upper()} riseattack input attempt '
                      f'{attempt + 1}/3 did not register -- retrying')
                m.write_u8(PlayerEntity + CHAR_SELECTED, 3)
                m.write_u8(PlayerEntity + CHAR_FALL_STATE_TIMER, 50)
                m.run_frames(20)
                m.pause()
            sel = read_u8(m, PlayerEntity + CHAR_SELECTED)
            print(f'{riseattack_char.upper()} UP+Y while lying: selected={sel} '
                  f'variant={var} fall_timer={fall_timer}')
            r.check(f'{riseattack_char.upper()}: UP+Y while lying (holding phase, '
                    f'HP>0) triggers riseattack (CHAR_ATTACK_VARIANT=7)', var == 7)
            r.check(f'{riseattack_char.upper()}: riseattack trigger resets '
                    f'CHAR_FALL_STATE_TIMER (no dangling fall-hold state left '
                    f'behind)', fall_timer == 0)

            hp_before = 64
            for _ in range(30):
                m.run_frames(1)
                m.pause()
                if read_u8(m, Entity1 + CHAR_HP) < hp_before:
                    break
            hp_after = read_u8(m, Entity1 + CHAR_HP)
            print(f'{riseattack_char.upper()} entity1 hp after riseattack window: '
                  f'{hp_after} (was {hp_before})')
            r.check(f'{riseattack_char.upper()}: riseattack deals real damage via '
                    f'the shared hit check', hp_after < hp_before)
            m.write_u8(Entity1 + CHAR_HP, 0)
            clear_stun(m, PlayerEntity)
            m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
            m.write_u8(PlayerEntity + CHAR_FALL_STATE_TIMER, 0)
            m.run_frames(60)
            m.pause()

    r.finish()


if __name__ == '__main__':
    main()
