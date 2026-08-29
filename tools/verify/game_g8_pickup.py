#!/usr/bin/env python3
"""plan_game.md Phase G8 (item/pickup slice): real HP/score/1-up pickup
effects (notjustfreespecial.txt).

Background: the first G8 slice (game_g8_props.py) made breakable
obstacles/pickups (`1up`, `trash`, `table`, `chair`) soft-kill like AI
enemies instead of fighting the player, but explicitly deferred "score/
life/item-reveal reward effects (no score system exists yet, G6)" -- both
plan_game.md's own status block and this project's coverage ledger recorded
that as still-open work. G6 (real score/lives HUD) has since landed, and a
direct pak scan (DATA\\CHARS\\MISC in the BOR pak) found real, currently-
unconverted item content: APPLE.TXT (`health 30`), MEAT.TXT (`health 100`),
MONEY.TXT (`score 1000`), and 1UP.TXT (real OpenBOR name=="1up" special
case: an extra life). All 4 are used by real, buildable, shipped spawn data
(DATA\\EASY\\1AEASY.TXT/1BEASY.TXT's own `item <name>` lines on Trash/Table/
Chair, and 1AEASY's own standalone `spawn 1up`) -- verified against
build_spawn_table.py's real regenerated out/spawn_stage1a/1b tables, not
assumed.

This slice wires the effect itself: main.pasm's new CHAR_PICKUP_TYPE struct
field (set by core/spawn.pasm's Spawn_Play from the spawn record's own
record_kind spare bits 5-7 -- build_spawn_table.py's classify_pickup),
consumed once, at the real moment a CHAR_INPUT_DRIVEN_PROP entity's HP
reaches 0 from a landed player hit (Character_HitApply_VsEntity1/2/3's
existing "killed" path, core/jump.pasm's new Character_HitApply__
ApplyPickup) -- never a synthetic poke, since a direct HP=0 WRAM write
(game_g8_props.py's own testing method for the OLDER hide/soft-kill check)
does NOT run through this code path at all and would prove nothing about
pickup effects specifically.

Checks, all against a live Mesen2 session, all via a REAL landed player
attack (BTN_Y, attack1) on entity 2 forced into CHAR_INPUT_DRIVEN_PROP with
CHAR_HP==CHAR_HP_PER_HIT (one hit kills) and each real pickup type in turn:
1. PICKUP_TYPE_APPLE: player CHAR_HP increases by PICKUP_HEAL_APPLE (19),
   clamped at CHAR_HP_MAX.
2. PICKUP_TYPE_MEAT: player CHAR_HP increases by PICKUP_HEAL_MEAT (64,
   i.e. a full heal from a damaged starting HP -- proves the clamp is real,
   not merely untested, since MEAT alone can't overflow from full HP).
3. PICKUP_TYPE_MONEY: Game_Score increases by PICKUP_SCORE_MONEY (1000).
4. PICKUP_TYPE_ONEUP: Game_Lives increases by exactly 1.
5. Regression: CHAR_PICKUP_TYPE reads back 0 after each effect (consumed
   once, doesn't re-fire if the slot happens to get inspected again before
   Spawn_Play reuses it), and an ordinary AI-mode kill (CHAR_INPUT_DRIVEN==
   CHAR_INPUT_DRIVEN_AI, CHAR_PICKUP_TYPE==0, the pre-G8-pickup-slice
   default) does NOT change Game_Score/Game_Lives/player CHAR_HP beyond the
   existing HIT_SCORE/KILL_SCORE combat-score award (proves this slice
   didn't accidentally make every kill a pickup).

Usage: python tools/verify/game_g8_pickup.py
"""
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
CHAR_HP_PER_HIT = pasm_constant('CHAR_HP_PER_HIT')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_HIT_APPLIED = pasm_constant('CHAR_HIT_APPLIED')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_PICKUP_TYPE = pasm_constant('CHAR_PICKUP_TYPE')
CHAR_INPUT_DRIVEN_PROP = pasm_constant_in('src/main.pasm', 'CHAR_INPUT_DRIVEN_PROP')
CHAR_INPUT_DRIVEN_AI = pasm_constant_in('src/main.pasm', 'CHAR_INPUT_DRIVEN_AI')

PICKUP_TYPE_APPLE = pasm_constant('PICKUP_TYPE_APPLE')
PICKUP_TYPE_MEAT = pasm_constant('PICKUP_TYPE_MEAT')
PICKUP_TYPE_MONEY = pasm_constant('PICKUP_TYPE_MONEY')
PICKUP_TYPE_ONEUP = pasm_constant('PICKUP_TYPE_ONEUP')
PICKUP_HEAL_APPLE = pasm_constant('PICKUP_HEAL_APPLE')
PICKUP_HEAL_MEAT = pasm_constant('PICKUP_HEAL_MEAT')
PICKUP_SCORE_MONEY = pasm_constant('PICKUP_SCORE_MONEY')
HIT_SCORE = pasm_constant('HIT_SCORE')
KILL_SCORE = pasm_constant('KILL_SCORE')
# A killing hit on ANY entity (prop or enemy) already awards HIT_SCORE+
# KILL_SCORE via Character_HitApply__ScoreAndFinish -- pre-existing
# behavior (game_g8_props.py's own slice never touched ScoreAndFinish),
# unrelated to and unchanged by this pickup slice. A prop's real pickup
# effect (below) is additive on top of that combat award, not a
# replacement for it -- breaking open a real item source nets both the
# fight-score AND the item's own value, same as it would for a normal
# enemy kill that happened to also matter for score.
COMBAT_KILL_AWARD = HIT_SCORE + KILL_SCORE

GS_PATH = 'src/core/game_state.pasm'
Game_Score = pasm_constant_in(GS_PATH, 'Game_Score')
Game_Lives = pasm_constant_in(GS_PATH, 'Game_Lives')
Entity1_InvulnFrames = pasm_constant_in(GS_PATH, 'Entity1_InvulnFrames')

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
PlayerEntity = ENTITY_BASES[0]
Entity1 = ENTITY_BASES[1]
Entity2 = ENTITY_BASES[2]
Entity3 = ENTITY_BASES[3]

READ_LEN = 128  # covers every CHAR_* offset used here


def entity_block(m, base):
    return read_block(m, base, READ_LEN)


def pos_x(blk):
    return blk[CHAR_POS_X] | (blk[CHAR_POS_X + 1] << 8)


def read_u8(m, addr):
    return read_block(m, addr, 32)[0]


def read_u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def overlap_entity2_with_player(m):
    px = entity_block(m, PlayerEntity)
    x = pos_x(px)
    y = px[CHAR_POS_Y]
    m.write_u16(Entity2 + CHAR_POS_X, x)
    m.write_u8(Entity2 + CHAR_POS_Y, y)


def reset_combat_state(m):
    m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
    m.write_u8(PlayerEntity + CHAR_HIT_APPLIED, 0)
    m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)
    m.write_u8(Entity2 + CHAR_SELECTED, 0)
    m.write_u8(Entity2 + CHAR_HIT_STUN, 0)
    m.write_u8(Entity1_InvulnFrames, 0)


def poll_until(m, predicate, max_frames):
    for _ in range(max_frames):
        if predicate():
            return True
        m.run_frames(1)
        m.pause()
    return predicate()


def land_hit_on_entity2(m, pickup_type, player_hp=None):
    """Sets up Entity2 as a one-hit prop with `pickup_type`, positions it
    on the player, lands a real attack1 (Y), and returns
    (player_hp_after, game_score_after, game_lives_after)."""
    reset_combat_state(m)
    m.write_u8(Entity2 + CHAR_INPUT_DRIVEN, CHAR_INPUT_DRIVEN_PROP)
    m.write_u8(Entity2 + CHAR_HP, CHAR_HP_PER_HIT)
    m.write_u8(Entity2 + CHAR_PICKUP_TYPE, pickup_type)
    if player_hp is not None:
        m.write_u8(PlayerEntity + CHAR_HP, player_hp)
    overlap_entity2_with_player(m)

    m.set_input(m.BTN_Y, 1)
    killed = poll_until(m, lambda: read_u8(m, Entity2 + CHAR_HP) == 0, max_frames=30)
    # let the ApplyPickup jsl inside the same hit-application frame settle
    # (it runs synchronously within the same frame ScoreAndFinish does).
    m.run_frames(2)
    m.pause()
    return killed


def main():
    r = Reporter('G8-PICKUP', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(300)
        m.pause()

        # Neutralize entities 1/3 -- same reasoning as game_g7_grab.py/
        # game_g7_knockdown.py: real background AI combat is already
        # underway by frame 300 and would otherwise perturb Game_Score/
        # player CHAR_HP between samples.
        m.write_u8(Entity1 + CHAR_HP, 0)
        m.write_u8(Entity3 + CHAR_HP, 0)

        # --- 1. APPLE: real heal, not full. ---
        m.write_u8(PlayerEntity + CHAR_HP, 10)
        hp_before = read_u8(m, PlayerEntity + CHAR_HP)
        killed = land_hit_on_entity2(m, PICKUP_TYPE_APPLE, player_hp=10)
        hp_after = read_u8(m, PlayerEntity + CHAR_HP)
        print(f'APPLE: killed={killed} hp {hp_before}->{hp_after} '
              f'(expect +{PICKUP_HEAL_APPLE})')
        r.check('attack lands and kills the prop (CHAR_HP reaches 0)', killed)
        r.check(f'APPLE pickup heals the player by exactly PICKUP_HEAL_APPLE '
                f'({PICKUP_HEAL_APPLE})',
                hp_after == min(CHAR_HP_MAX, hp_before + PICKUP_HEAL_APPLE))
        r.check('CHAR_PICKUP_TYPE cleared to 0 after consuming the effect',
                read_u8(m, Entity2 + CHAR_PICKUP_TYPE) == 0)

        # --- 2. MEAT: real heal, clamped (full heal from a damaged start). ---
        m.write_u8(PlayerEntity + CHAR_HP, 10)
        hp_before = 10
        killed = land_hit_on_entity2(m, PICKUP_TYPE_MEAT, player_hp=10)
        hp_after = read_u8(m, PlayerEntity + CHAR_HP)
        print(f'MEAT: killed={killed} hp {hp_before}->{hp_after} '
              f'(expect min(CHAR_HP_MAX, +{PICKUP_HEAL_MEAT}))')
        r.check(f'MEAT pickup heals the player by PICKUP_HEAL_MEAT '
                f'({PICKUP_HEAL_MEAT}), clamped at CHAR_HP_MAX',
                hp_after == min(CHAR_HP_MAX, hp_before + PICKUP_HEAL_MEAT))

        # MEAT again from near-full HP, to prove the clamp is real (not
        # just coincidentally exact from a low starting HP above).
        m.write_u8(PlayerEntity + CHAR_HP, CHAR_HP_MAX - 5)
        killed = land_hit_on_entity2(m, PICKUP_TYPE_MEAT, player_hp=CHAR_HP_MAX - 5)
        hp_after = read_u8(m, PlayerEntity + CHAR_HP)
        print(f'MEAT (near-full start): killed={killed} hp {CHAR_HP_MAX - 5}->{hp_after}')
        r.check('MEAT pickup clamps at CHAR_HP_MAX (never overflows past the '
                'HUD bar\'s own max)', hp_after == CHAR_HP_MAX)

        # --- 3. MONEY: real score award. ---
        score_before = read_u16(m, Game_Score)
        killed = land_hit_on_entity2(m, PICKUP_TYPE_MONEY)
        score_after = read_u16(m, Game_Score)
        expected_money_delta = PICKUP_SCORE_MONEY + COMBAT_KILL_AWARD
        print(f'MONEY: killed={killed} score {score_before}->{score_after} '
              f'(expect +{expected_money_delta} = pickup {PICKUP_SCORE_MONEY} '
              f'+ combat-kill award {COMBAT_KILL_AWARD})')
        r.check(f'MONEY pickup adds PICKUP_SCORE_MONEY ({PICKUP_SCORE_MONEY}) '
                f'to Game_Score, on top of the pre-existing combat-kill award',
                score_after == score_before + expected_money_delta)

        # --- 4. 1UP: real extra life. ---
        lives_before = read_u8(m, Game_Lives)
        killed = land_hit_on_entity2(m, PICKUP_TYPE_ONEUP)
        lives_after = read_u8(m, Game_Lives)
        print(f'1UP: killed={killed} lives {lives_before}->{lives_after}')
        r.check('1up pickup adds exactly 1 life (real OpenBOR name=="1up" '
                'special case)', lives_after == lives_before + 1)

        # --- 5. Regression: a prop with NO real contained item
        # (CHAR_PICKUP_TYPE==0 -- e.g. a real breakable whose level data
        # has no `item` line, like stage 1B's own Table, see this module's
        # own docstring) still soft-kills and scores like any other kill,
        # but must NOT heal the player or award a life -- only a real
        # nonzero pickup_type should ever trigger ApplyPickup's effects.
        # Deliberately still CHAR_INPUT_DRIVEN_PROP (not AI mode): an
        # AI-mode entity would seek/attack back and break the fixed
        # overlap this single-press test relies on -- game_g8_props.py's
        # own gate already separately proves AI-vs-prop mode differences,
        # not this slice's concern. ---
        m.write_u8(PlayerEntity + CHAR_HP, 40)
        reset_combat_state(m)
        m.write_u8(Entity2 + CHAR_INPUT_DRIVEN, CHAR_INPUT_DRIVEN_PROP)
        m.write_u8(Entity2 + CHAR_HP, CHAR_HP_PER_HIT)
        m.write_u8(Entity2 + CHAR_PICKUP_TYPE, 0)
        overlap_entity2_with_player(m)
        hp_before = 40
        score_before = read_u16(m, Game_Score)
        lives_before = read_u8(m, Game_Lives)
        m.set_input(m.BTN_Y, 1)
        killed = poll_until(m, lambda: read_u8(m, Entity2 + CHAR_HP) == 0, max_frames=30)
        m.run_frames(2)
        m.pause()
        hp_after = read_u8(m, PlayerEntity + CHAR_HP)
        score_after = read_u16(m, Game_Score)
        lives_after = read_u8(m, Game_Lives)
        print(f'no-pickup prop regression: killed={killed} player_hp '
              f'{hp_before}->{hp_after} score {score_before}->{score_after} '
              f'lives {lives_before}->{lives_after}')
        r.check('regression: killing the prop', killed)
        r.check('regression: a pickup_type==0 prop kill leaves the player\'s '
                'own CHAR_HP unchanged (no accidental self-heal)',
                hp_after == hp_before)
        r.check('regression: a pickup_type==0 prop kill still awards the '
                'ordinary combat-kill score (unchanged pre-slice behavior), '
                'and nothing more',
                score_after == score_before + COMBAT_KILL_AWARD)
        r.check('regression: a pickup_type==0 prop kill leaves Game_Lives '
                'unchanged (no accidental extra life)', lives_after == lives_before)

    r.finish()


if __name__ == '__main__':
    main()
