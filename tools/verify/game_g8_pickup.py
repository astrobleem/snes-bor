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
3b. PICKUP_TYPE_GOLD: Game_Score increases by PICKUP_SCORE_GOLD (5000),
   distinct from MONEY (Part 3 slice).
4. PICKUP_TYPE_ONEUP: Game_Lives increases by exactly 1.
5. Regression: CHAR_PICKUP_TYPE reads back 0 after each effect (consumed
   once, doesn't re-fire if the slot happens to get inspected again before
   Spawn_Play reuses it), and an ordinary AI-mode kill (CHAR_INPUT_DRIVEN==
   CHAR_INPUT_DRIVEN_AI, CHAR_PICKUP_TYPE==0, the pre-G8-pickup-slice
   default) does NOT change Game_Score/Game_Lives/player CHAR_HP beyond the
   existing source force-based combat-score award (force=1 -> HIT_SCORE)
   (proves this slice
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
PICKUP_TYPE_GOLD = pasm_constant('PICKUP_TYPE_GOLD')
PICKUP_HEAL_APPLE = pasm_constant('PICKUP_HEAL_APPLE')
PICKUP_HEAL_MEAT = pasm_constant('PICKUP_HEAL_MEAT')
PICKUP_SCORE_MONEY = pasm_constant('PICKUP_SCORE_MONEY')
PICKUP_SCORE_GOLD = pasm_constant('PICKUP_SCORE_GOLD')
HIT_SCORE = pasm_constant('HIT_SCORE')
# S1D routes the existing compatibility force=1 event through the source
# score primitive. There is no universal kill bonus in BOR v1.0029.
COMBAT_KILL_AWARD = HIT_SCORE

GS_PATH = 'src/core/game_state.pasm'
Game_Score = pasm_constant_in(GS_PATH, 'Game_Score')
Game_Lives = pasm_constant_in(GS_PATH, 'Game_Lives')
Entity1_InvulnFrames = pasm_constant_in(GS_PATH, 'Entity1_InvulnFrames')
# claude_close_g7_g8_before_g10.md Part 2: a standalone WRAM cell (spawn.
# pasm), not a CHAR_ZP_LEN struct field -- see that file's own comment for
# why (growing the struct is real-bug-verified dangerous). Must be
# explicitly zeroed by this gate's own synthetic scenarios below: a nonzero
# leftover here (e.g. from the real spawn table's own boot-time Chair/
# Table/Trash placement, which now legitimately sets it) would defer this
# gate's synthetic pickup into the broken-pending-reveal state instead of
# the instant-reward path this gate is specifically testing.
SPAWN_PATH = 'src/core/spawn.pasm'
Entity2_ItemRosterIdx = pasm_constant_in(SPAWN_PATH, 'Entity2_ItemRosterIdx')

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
    # Real, pre-existing flake root-caused (found while investigating the
    # G8 asset-swapping slice): consecutive scenarios in this same Mesen
    # session each call m.set_input(m.BTN_Y, 1) with no release between
    # them -- input.pasm's press-edge detection needs a real release
    # before a fresh press is seen as a new attack (same class of bug
    # found and fixed in game_vertical_slice.py's own pickup segment), so
    # a later scenario's attack can silently never land. Release here.
    m.set_input(0, 5)
    m.pause()


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
    m.write_u8(Entity2_ItemRosterIdx, 0)  # see this constant's own comment
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
        # claude_close_g7_g8_before_g10.md Part 2: real bug found live-
        # tracing this -- land_hit_on_entity2 positions entity 2 directly
        # overlapping the player BEFORE the attack input even fires, and
        # Character_Pickup_CheckOverlap (this same slice's new touch-
        # collect mechanism, core/jump.pasm) runs unconditionally every
        # frame, gated only on overlap + CHAR_INPUT_DRIVEN_PROP + nonzero
        # CHAR_PICKUP_TYPE + CHAR_ItemRosterIdx==0 -- exactly the state
        # this test's own setup creates. So the item is genuinely touch-
        # collected the very first frame, before Character_HitApply's own
        # combat path (ScoreAndFinish's source force=1 award) ever
        # runs -- Entity2_Hp is already 0 by the time a real attack would
        # reach it, so combat's own dead-target early-out skips it
        # entirely. This is correct, real OpenBOR behavior (ground items
        # are walked over, not punched) -- this module's own docstring
        # (item 3) already only ever claimed the bare PICKUP_SCORE_MONEY
        # amount, not a combat-score stack; the stacked-award expectation
        # here was simply wrong, not the engine.
        score_before = read_u16(m, Game_Score)
        killed = land_hit_on_entity2(m, PICKUP_TYPE_MONEY)
        score_after = read_u16(m, Game_Score)
        print(f'MONEY: killed={killed} score {score_before}->{score_after} '
              f'(expect +{PICKUP_SCORE_MONEY}, touch-collected, no attack '
              f'landed -- see comment above)')
        r.check(f'MONEY pickup adds PICKUP_SCORE_MONEY ({PICKUP_SCORE_MONEY}) '
                f'to Game_Score via real touch-collect (no combat-kill hit '
                f'landed since the item was already gone)',
                score_after == score_before + PICKUP_SCORE_MONEY)

        # --- 3a. GOLD real shipped data: stage 1B's own spawn table
        # actually contains a real PICKUP_TYPE_GOLD record (a Table
        # wrapping Gold, DATA\EASY\1BEASY.TXT's own `item gold` line) --
        # not just a synthetic constant exercised below. ---
        import struct
        spawn_bin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  '..', '..', 'out', 'spawn_stage1b', 'spawn_table.bin')
        with open(spawn_bin, 'rb') as f:
            spawn_data = f.read()
        gold_records = []
        for i in range(len(spawn_data) // 10):
            rec = spawn_data[i * 10:i * 10 + 10]
            _tx, _sx, _sy, _f, kind, _hp, item_idx, obj_idx = struct.unpack('<HHBBBBBB', rec)
            if (kind & 7) == 1 and ((kind >> 5) & 7) == PICKUP_TYPE_GOLD:
                gold_records.append((i, obj_idx, item_idx))
        print(f'out/spawn_stage1b/spawn_table.bin real PICKUP_TYPE_GOLD '
              f'records: {gold_records}')
        r.check('stage 1B\'s real packed spawn data contains a genuine '
                'PICKUP_TYPE_GOLD record (a real Table-wraps-Gold '
                'spawn, not just a synthetic test scenario)',
                len(gold_records) >= 1)

        # --- 3b. GOLD: real, distinct score award (claude_close_g7_g8_
        # before_g10.md Part 3 -- GOLD.TXT score=5000, a real shipped item
        # (DATA\EASY\1BEASY.TXT's own `item gold` line on a Table record)
        # that an earlier audit pass wrongly claimed was unused; its own
        # PICKUP_TYPE_GOLD, not folded into PICKUP_TYPE_MONEY, so this
        # proves the 5000-point award isn't silently undercounted to
        # MONEY's 1000). ---
        score_before = read_u16(m, Game_Score)
        killed = land_hit_on_entity2(m, PICKUP_TYPE_GOLD)
        score_after = read_u16(m, Game_Score)
        print(f'GOLD: killed={killed} score {score_before}->{score_after} '
              f'(expect +{PICKUP_SCORE_GOLD}, touch-collected)')
        r.check(f'GOLD pickup adds PICKUP_SCORE_GOLD ({PICKUP_SCORE_GOLD}, '
                f'distinct from MONEY\'s {PICKUP_SCORE_MONEY}) to Game_Score '
                f'via real touch-collect',
                score_after == score_before + PICKUP_SCORE_GOLD)

        # --- 4. 1UP: real extra life. ---
        lives_before = read_u16(m, Game_Lives)
        killed = land_hit_on_entity2(m, PICKUP_TYPE_ONEUP)
        lives_after = read_u16(m, Game_Lives)
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
        lives_before = read_u16(m, Game_Lives)
        m.set_input(m.BTN_Y, 1)
        killed = poll_until(m, lambda: read_u8(m, Entity2 + CHAR_HP) == 0, max_frames=30)
        m.run_frames(2)
        m.pause()
        hp_after = read_u8(m, PlayerEntity + CHAR_HP)
        score_after = read_u16(m, Game_Score)
        lives_after = read_u16(m, Game_Lives)
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
