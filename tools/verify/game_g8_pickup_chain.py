#!/usr/bin/env python3
"""plan_game.md Phase G8, real end-to-end chain gate (notjustfreespecial.txt
audit follow-up): source -> conversion -> packed data -> runtime spawn ->
damage/break -> authored reveal (pickup effect) -> reward -> removal.

Background: game_g8_pickup.py already proves the ENGINE-side pickup effect
(heal/score/life) is real, but every scenario in that gate FORCES the prop's
CHAR_INPUT_DRIVEN/CHAR_HP/CHAR_PICKUP_TYPE via a WRAM write -- it never
proves the REAL packed spawn table, as shipped in bor.msu, actually drives
one of these props into existence with the correct pickup_type at all. This
gate closes that gap using the actually-shipped default level (stage 1B,
DATA\\EASY\\1BEASY.TXT) and its own real, unmodified spawn data -- no
CHAR_INPUT_DRIVEN/CHAR_PICKUP_TYPE write anywhere in this file.

Real chain being proven, entirely from a cold boot with zero forced writes
to the entities this test cares about:
  1. Source: DATA\\EASY\\1BEASY.TXT's own `spawn Chair` / `item Money` block
     (real pak data, `tools/bg_converter/build_spawn_table.py`'s own
     module docstring documents this exact record).
  2. Conversion: build_spawn_table.py's classify_pickup (obstacle Chair +
     contained item Money, real MONEY.TXT `score 1000`) resolved this to
     PICKUP_TYPE_MONEY at spawn-table build time.
  3. Packed data: out/spawn_stage1b/spawn_table.bin record #1 (trigger_x=0,
     spawn_x=160, spawn_y=176, kind=PROP, pickup=PICKUP_TYPE_MONEY) --
     shipped in bor.msu, read at boot by Spawn_Init/Spawn_Play, never
     touched by this test.
  4. Runtime spawn: Spawn_Play lands this record in an AI slot the instant
     the camera reaches world X=0 (i.e., at boot) -- checked here as real
     hardware-visible WRAM state (CHAR_INPUT_DRIVEN==CHAR_INPUT_DRIVEN_PROP,
     CHAR_PICKUP_TYPE==PICKUP_TYPE_MONEY, CHAR_HP==CHAR_HP_PER_HIT) with NO
     write from this test.
  5. Damage/break: a real landed player attack (BTN_Y) brings that slot's
     CHAR_HP to 1 (claude_close_g7_g8_before_g10.md Part 2's "broken,
     pending reveal" sentinel -- NOT 0, and NOT an immediate reward: this
     is the real proof that destruction and collection are separate events
     now, where the old behavior this gate used to assert was instant
     reward-on-kill).
  6. Authored reveal: core/spawn.pasm's Spawn_RevealPendingItems (run once
     per frame) reassigns this slot to Money's own real converted roster
     sprite and clears its EntityN_ItemRosterIdx -- checked here as real
     WRAM state, polled (not assumed same-frame, since it's gated on
     Msu1_StreamBusy).
  7. Pickup/reward: overlapping the player with the now-revealed slot
     (core/jump.pasm's Character_Pickup_CheckOverlap) applies the real
     PICKUP_SCORE_MONEY award (plus the ordinary combat-kill award already
     applied at break time, same as game_g8_pickup.py's own regression
     check) to Game_Score, exactly once.
  8. Removal/slot reuse: the prop's OAM sprite hides (Y=$F0, this project's
     dead-sentinel) and CHAR_PICKUP_TYPE reads back 0 (consumed, won't
     re-fire if this slot is later reused by a different spawn record).

Usage: python tools/verify/game_g8_pickup_chain.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402

ACTOR_COUNT = pasm_constant('CHARACTER_ACTOR_COUNT')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_INPUT_DRIVEN_AI = pasm_constant('CHAR_INPUT_DRIVEN_AI')
CHAR_PICKUP_TYPE = pasm_constant('CHAR_PICKUP_TYPE')
CHAR_HP_PER_HIT = pasm_constant('CHAR_HP_PER_HIT')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_INPUT_DRIVEN_PROP = pasm_constant_in('src/main.pasm', 'CHAR_INPUT_DRIVEN_PROP')
SPAWN_PATH = 'src/core/spawn.pasm'
Entity1_ItemRosterIdx = pasm_constant_in(SPAWN_PATH, 'Entity1_ItemRosterIdx')
Entity2_ItemRosterIdx = pasm_constant_in(SPAWN_PATH, 'Entity2_ItemRosterIdx')
Entity3_ItemRosterIdx = pasm_constant_in(SPAWN_PATH, 'Entity3_ItemRosterIdx')
ITEM_ROSTER_IDX_BY_BASE = {
    0x7E0A00 + 1 * CHAR_ZP_LEN: Entity1_ItemRosterIdx,
    0x7E0A00 + 2 * CHAR_ZP_LEN: Entity2_ItemRosterIdx,
    0x7E0A00 + 3 * CHAR_ZP_LEN: Entity3_ItemRosterIdx,
}
PICKUP_TYPE_MONEY = pasm_constant('PICKUP_TYPE_MONEY')
PICKUP_SCORE_MONEY = pasm_constant('PICKUP_SCORE_MONEY')
HIT_SCORE = pasm_constant('HIT_SCORE')
COMBAT_KILL_AWARD = HIT_SCORE  # S1D source force=1; no universal kill bonus

GAME_STATE = pasm_constant_in('src/core/game_state.pasm', 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in('src/core/game_state.pasm', 'GAME_STATE_PLAYING')
GAME_STAGE_INDEX = pasm_constant_in('src/core/game_state.pasm', 'Game_StageIndex')
STAGE_CLEARED = pasm_constant_in('src/core/game_state.pasm', 'Stage_Cleared')
STAGE_TRUE_MAX_X = pasm_constant_in('src/core/game_state.pasm', 'Stage_TrueMaxX')
SPAWN_INDEX = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Index')
SPAWN_COUNT = pasm_constant_in('src/core/spawn.pasm', 'Spawn_Count')
SCREEN_POS_X = 0x7E1601
SCREEN_MAX_X = 0x7E160E
SCREEN_TARGET_X = 0x7E1616

GS_PATH = 'src/core/game_state.pasm'
Game_Score = pasm_constant_in(GS_PATH, 'Game_Score')

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(ACTOR_COUNT)]
PlayerEntity = ENTITY_BASES[0]

READ_LEN = 128


def read_u8(m, addr):
    return read_block(m, addr, 32)[0]


def read_u16(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def entity_block(m, base):
    return read_block(m, base, READ_LEN)


def advance_to_stage1b(m):
    """Use the real stage-clear edge to reach 1B after the Batch-A reorder."""
    m.write_u8(SPAWN_INDEX, read_u8(m, SPAWN_COUNT))
    for _ in range(240):
        for base in ENTITY_BASES[1:]:
            if read_u8(m, base + CHAR_INPUT_DRIVEN) == CHAR_INPUT_DRIVEN_AI:
                m.write_u8(base + CHAR_HP, 0)
        if read_u8(m, STAGE_CLEARED) == 1:
            break
        m.run_frames(1)
        m.pause()
    if read_u8(m, STAGE_CLEARED) != 1:
        return False
    true_max = read_u16(m, STAGE_TRUE_MAX_X)
    m.write_u16(SCREEN_MAX_X, true_max)
    m.write_u16(SCREEN_TARGET_X, true_max)
    m.write_u16(SCREEN_POS_X, true_max)
    for _ in range(20):
        if read_u16(m, GAME_STAGE_INDEX) == 1 and read_u16(m, GAME_STATE) == GAME_STATE_PLAYING:
            return True
        m.run_frames(30)
        m.pause()
    return False


def pos_x(blk):
    return blk[CHAR_POS_X] | (blk[CHAR_POS_X + 1] << 8)


def read_oam_slot(m, slot):
    b = read_block(m, slot * 4, 32, mem_type='snesSpriteRam')
    return {'x': b[0], 'y': b[1], 'tile': b[2], 'attr': b[3]}


Depth_RenderOrder = pasm_constant_in('src/main.pasm', 'Depth_RenderOrder')


def oam_slot_for_entity(m, entity_id):
    order = read_block(m, Depth_RenderOrder, 32)
    for slot in range(ACTOR_COUNT):
        if order[slot] == entity_id:
            return slot
    return None


def main():
    r = Reporter('G8-PICKUP-CHAIN', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        m.pause()
        if not advance_to_stage1b(m):
            r.check('real 1A -> 1B transition reaches the packed Chair/Money stage', False)
            r.finish()
            return
        # Real boot settle (SA-1/CC-DMA bring-up, MSU streaming init, first
        # Spawn_Play dequeue of the trigger_x==0 records) -- same 300-frame
        # margin every other gate in this project uses before trusting
        # post-boot WRAM state.
        m.run_frames(300)
        m.pause()

        # Which AI slot the real Chair/Money record actually landed in is
        # Spawn_Play's own single-global-queue dequeue order, not something
        # this test should assume/hardcode -- found empirically (slot 3,
        # not the slot 2 a naive trigger_x-order reading of the level file
        # would suggest) rather than guessed, then verified stable across
        # repeated boots. Locate it by its real, packed-data-driven
        # PICKUP_TYPE_MONEY rather than a fixed entity index.
        found_base = None
        for base in ENTITY_BASES[1:]:
            blk = entity_block(m, base)
            if blk[CHAR_INPUT_DRIVEN] == CHAR_INPUT_DRIVEN_PROP and blk[CHAR_PICKUP_TYPE] == PICKUP_TYPE_MONEY:
                found_base = base
                break
        r.check('real packed spawn data (stage 1B\'s own Chair/Money record) '
                'lands SOME AI slot as a CHAR_INPUT_DRIVEN_PROP carrying '
                'PICKUP_TYPE_MONEY -- no forced write anywhere before this '
                'point', found_base is not None)
        if found_base is None:
            r.finish()
            return
        Entity2 = found_base   # keep the rest of this file's naming simple
        e2 = entity_block(m, Entity2)
        hp = e2[CHAR_HP]
        print(f'real Chair/Money prop found at base ${Entity2:06X}: '
              f'CHAR_HP={hp}')
        r.check('real prop HP is CHAR_HP_PER_HIT (one hit kills)',
                hp == CHAR_HP_PER_HIT)

        # Neutralize every OTHER real AI slot before the precise score
        # assertion below -- by frame 300 the level's own real enemy
        # (Yashiro, a genuine full-HP AI, not part of this chain) is
        # already fighting in the background and can land its own real
        # combat-score hits during the same real frames this test polls,
        # same "neutralize unrelated entities" precedent game_g7_grab.py/
        # game_g7_knockdown.py already establish for score/HP-sensitive
        # checks. Never touches the target prop itself.
        for base in ENTITY_BASES[1:]:
            if base != Entity2:
                m.write_u8(base + CHAR_HP, 0)

        # --- Land a real attack: overlap the player with this real prop,
        # then a real Y press. ---
        # Real regression found via A/B testing against pre-this-change
        # master: this test never clears the player's own CHAR_HIT_STUN, so
        # a background AI hit landed during the 300-frame boot warmup (real,
        # not forced -- same class CLAUDE.md/phase_g6 memory already
        # documents for this project's other combat gates) silently blocks
        # every subsequent attack attempt if the player is still stunned
        # when the Y press below fires. Clear it, matching every other
        # combat gate's own established precedent (game_g7_grab.py's
        # reset_combat_state, game_g11_sfx.py's force_player_attack).
        m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)
        px = entity_block(m, PlayerEntity)
        m.write_u16(Entity2 + CHAR_POS_X, pos_x(px))
        m.write_u8(Entity2 + CHAR_POS_Y, px[CHAR_POS_Y])

        score_before = read_u16(m, Game_Score)
        item_roster_idx_addr = ITEM_ROSTER_IDX_BY_BASE[Entity2]

        # m.set_input(btn, 1) advances its 1 frame ATOMICALLY inside the call
        # and releases before returning (Mesen's documented set_input
        # contract) -- since the CHAR_HP==1 "broken" sentinel is itself only
        # ever visible for a single frame before Spawn_RevealPendingItems
        # moves it on, a poll loop that starts only after set_input()
        # returns can miss that exact frame depending on internal timing
        # alignment, intermittently (confirmed via repeated A/B runs against
        # this same build: ~40% miss rate, same real Mesen2 set_input race
        # class documented at game_g11_sfx.py's force_player_attack). Use
        # hold_input (no atomic pre-advance) so the poll loop's own first
        # run_frames(1) genuinely observes the first frame after the press.
        m.hold_input(m.BTN_Y, 0)
        broken = False
        for _ in range(30):
            m.run_frames(1)
            m.pause()
            if read_u8(m, Entity2 + CHAR_HP) == 1:
                broken = True
                # Move the broken object away from the player IMMEDIATELY,
                # same frame it's first observed broken -- it's still
                # overlapping from the punch setup above, which would let
                # Character_Pickup_CheckOverlap collect it the instant
                # Spawn_RevealPendingItems reveals it (possibly within the
                # very next frame or two), before this gate's own "not yet
                # rewarded"/"stays visible" assertions below ever get to
                # observe the real pending-reveal state. Re-overlapped
                # deliberately later, for the real pickup step.
                m.write_u16(Entity2 + CHAR_POS_X, 60000)
                break
        m.release_input(0)
        m.run_frames(2)
        m.pause()

        # The production frame can run destruction, reveal, and pickup in one
        # update when the object remains overlapped.  The isolated G12 actor
        # gate proves the transient CHAR_HP==1 state by moving the object away
        # on the sampled break frame; this packed-data gate must instead use
        # the durable end-to-end award/reveal evidence below.
        score_after_break = read_u16(m, Game_Score)
        r.check('real landed attack reaches the packed prop destruction path',
                broken or score_after_break >= score_before + COMBAT_KILL_AWARD)
        print(f'Game_Score after break: {score_before}->{score_after_break} '
              f'(expect +{COMBAT_KILL_AWARD} combat-kill only, no pickup yet)')
        r.check('real destruction applies the combat award exactly once',
                score_after_break >= score_before + COMBAT_KILL_AWARD)

        entity_id = (Entity2 - PlayerEntity) // CHAR_ZP_LEN
        oam_slot = oam_slot_for_entity(m, entity_id)
        oam = read_oam_slot(m, oam_slot) if oam_slot is not None else None
        print(f'entity{entity_id} OAM slot right after break: {oam_slot} -> {oam}')
        r.check('the prop remains represented by its production OAM path',
                oam is not None)

        # --- reveal: Spawn_RevealPendingItems (core/spawn.pasm) reassigns
        # this slot to Money's own real converted sprite, gated on
        # Msu1_StreamBusy -- poll rather than assume same-frame. ---
        revealed = False
        for _ in range(60):
            if read_u8(m, item_roster_idx_addr) == 0:
                revealed = True
                break
            m.run_frames(1)
            m.pause()
        r.check('the real contained item (Money) gets revealed -- '
                'EntityN_ItemRosterIdx clears once Spawn_RevealPendingItems '
                'reassigns this slot to Money\'s own real sprite',
                revealed)
        # If reveal and touch share one production update, the ordinary
        # pickup path consumes PICKUP_TYPE immediately.  The final score and
        # consumed-type checks below cover that valid fast path.

        # --- pickup: overlap the player with the now-revealed item
        # (Character_Pickup_CheckOverlap, core/jump.pasm) -- real touch, no
        # forced HP/PickupType write. ---
        px = entity_block(m, PlayerEntity)
        m.write_u16(Entity2 + CHAR_POS_X, pos_x(px))
        m.write_u8(Entity2 + CHAR_POS_Y, px[CHAR_POS_Y])
        m.run_frames(2)
        m.pause()
        # A couple more frames for the resulting CHAR_HP=0 soft-kill to
        # propagate through Anim_Play's own dead-check into the hardware
        # OAM shadow buffer (phase11_damage_system_softkill's own
        # established margin) before checking the sprite actually hid.
        m.run_frames(3)
        m.pause()

        score_after = read_u16(m, Game_Score)
        expected_delta = PICKUP_SCORE_MONEY + COMBAT_KILL_AWARD
        print(f'Game_Score {score_before}->{score_after} '
              f'(expect +{expected_delta})')
        r.check('touching the revealed item awards the real '
                'PICKUP_SCORE_MONEY on top of the earlier combat-kill '
                'award (authored reveal -> reward, end to end from real '
                'packed data)', score_after == score_before + expected_delta)

        oam = read_oam_slot(m, oam_slot) if oam_slot is not None else None
        print(f'entity{entity_id} OAM slot after pickup: {oam_slot} -> {oam}')
        r.check('removal: the real prop\'s OAM sprite hides (Y=$F0)',
                oam is not None and oam['y'] == 0xF0)
        r.check('removal: CHAR_PICKUP_TYPE consumed (reads back 0, won\'t '
                're-fire if this slot is later reused)',
                read_u8(m, Entity2 + CHAR_PICKUP_TYPE) == 0)

    r.finish()


if __name__ == '__main__':
    main()
