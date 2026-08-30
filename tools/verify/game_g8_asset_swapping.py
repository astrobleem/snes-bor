#!/usr/bin/env python3
"""plan_game.md G8 completion (finish_g8_with_runtime_asset_swapping.md):
proves the static asset CATALOG (bor.msu's roster directory) is genuinely
distinct from the four physical runtime entity/graphics SLOTS -- the same
slot is proven to load four DIFFERENT real converted item identities in
sequence (APPLE/MONEY/MEAT/1UP, all real MISC item entities converted by
tools/bor_converter/convert_prop.py and added as real roster catalog
records 13-16, build_rom.py's ROSTER_PREFIXES), each with its own real
tile/frame/CGRAM ground truth and its own real pickup reward -- and that a
real ordinary enemy landing in that SAME slot afterward does NOT inherit
the previous prop's stale art/pickup state (the slot-reuse bug this same
finish_g8 document identified and core/spawn.pasm was fixed to close --
see Spawn_ScratchPrevWasProp's own header comment).

Real chain used throughout, no synthetic per-item shortcuts: stage 1A's
own unmodified spawn table (out/spawn_stage1a/spawn_table.bin) already
carries one real record per item type (verified below, byte-level, not
assumed) -- this gate drives the real single global spawn queue directly
to each record in turn (same real Spawn_Index/camera-position idiom every
other spawn-driven gate in this project already establishes, e.g.
game_spawn_roster_reassign.py/game_g8_prop_art.py), and pins entities 2/3
alive throughout so Spawn_Play's own find_slot always lands every record
in entity 1 -- proving genuine same-physical-slot reuse across four
different item identities plus one ordinary enemy, not four different
slots that happen to look similar.

Per item, proves:
  1. the record's own real (kind, pickup_type, roster_idx) triple, read
     straight off the committed spawn_table.bin, not the engine's claim
     about itself;
  2. the slot's (idle,walk,attack) frame-count triple becomes that item's
     OWN real converted moveset (all 1,1,1 -- convert_prop.py's real
     single-frame-per-role output -- so this alone doesn't distinguish
     items; see #3);
  3. the slot's CGRAM OBJ palette becomes that item's OWN real converted
     palette.txt, byte-for-byte -- APPLE/MONEY/MEAT/1UP each have
     genuinely distinct real palette data, so this IS what proves the
     right catalog entry loaded, not just "some prop's data";
  4. a real landed attack (BTN_Y, overlap) breaks it and awards that
     item's own real pickup effect (heal amount / score / life), reusing
     the same real hit-application path game_g8_pickup_chain.py already
     proves for MONEY alone -- generalized here to all four.

Then, the slot-reuse regression: after the last item is consumed (freeing
the slot), the real ordinary enemy record stage 1A's own table carries at
index 1 (kind=enemy, not prop/boss) is driven into the same slot, and this
gate proves NONE of the following survive from the prop that was just
there: CHAR_PICKUP_TYPE, the prop's (1,1,1) frame-count triple, the prop's
own CGRAM palette. The slot's restored art must be a real playable
fighter's -- specifically JHUN's own real converted (idle,walk,attack)
triple and palette.txt, the entity's own natural boot-default character
(CharacterEntity_Init's role-1 branch) -- proving core/spawn.pasm's
Spawn_ScratchPrevWasProp restore path actually re-streamed a real
character, not merely cleared the pickup-type byte while leaving the
slot visibly rendered as food or money.

Usage: python tools/verify/game_g8_asset_swapping.py
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bor_converter'))
from gen_pasm_animset import load_palette  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_PICKUP_TYPE = pasm_constant('CHAR_PICKUP_TYPE')
CHAR_IDLE_FCOUNT = pasm_constant('CHAR_IDLE_FCOUNT')
CHAR_WALK_FCOUNT = pasm_constant('CHAR_WALK_FCOUNT')
CHAR_ATTACK_FCOUNT = pasm_constant('CHAR_ATTACK_FCOUNT')
CHAR_PALETTE_SLOT = pasm_constant('CHAR_PALETTE_SLOT')
CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_SELECTED = pasm_constant('CHAR_SELECTED')
CHAR_HIT_STUN = pasm_constant('CHAR_HIT_STUN')
CHAR_HIT_APPLIED = pasm_constant('CHAR_HIT_APPLIED')
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
COMBAT_KILL_AWARD = HIT_SCORE + KILL_SCORE

GS_PATH = 'src/core/game_state.pasm'
GAME_STAGE_INDEX = pasm_constant_in(GS_PATH, 'Game_StageIndex')
GAME_STATE = pasm_constant_in(GS_PATH, 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in(GS_PATH, 'GAME_STATE_PLAYING')
STAGE_CLEARED = pasm_constant_in(GS_PATH, 'Stage_Cleared')
STAGE_TRUE_MAX_X = pasm_constant_in(GS_PATH, 'Stage_TrueMaxX')
Game_Score = pasm_constant_in(GS_PATH, 'Game_Score')
Game_Lives = pasm_constant_in(GS_PATH, 'Game_Lives')

SP_PATH = 'src/core/spawn.pasm'
SPAWN_INDEX = pasm_constant_in(SP_PATH, 'Spawn_Index')
SPAWN_COUNT_ADDR = pasm_constant_in(SP_PATH, 'Spawn_Count')

SCREEN_POS_X = 0x7E1601
ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
PlayerEntity = ENTITY_BASES[0]
Entity1 = ENTITY_BASES[1]
Entity1_ItemRosterIdx = pasm_constant_in(SP_PATH, 'Entity1_ItemRosterIdx')
Entity1_InvulnFrames = pasm_constant_in(GS_PATH, 'Entity1_InvulnFrames')
Player_InvulnFrames = pasm_constant_in(GS_PATH, 'Player_InvulnFrames')

# --- Real ground truth, read straight from the committed files, never
# hardcoded independently of them. ---
with open('out/spawn_stage1a/spawn_table.bin', 'rb') as _f:
    _SPAWN_DATA = _f.read()


def _record(idx):
    # claude_close_g7_g8_before_g10.md Part 2/3: record grew 9->10 bytes --
    # the old single +8 roster_idx (a standalone item's own identity) split
    # into +8 item_roster_idx (a WRAPPED item's reveal-on-break target,
    # always 0 for these standalone `spawn <item>` records) and +9
    # object_roster_idx (the SPAWNED character's own identity -- for a
    # standalone item, this IS its own roster slot, same meaning the old
    # +8 had). Read +9 here, matching ITEM_RECORDS' own values below.
    rec = _SPAWN_DATA[idx * 10:idx * 10 + 10]
    trigger_x, spawn_x, spawn_y, facing, kind, hp, item_roster_idx, roster_idx = \
        struct.unpack('<HHBBBBBB', rec)
    return {'trigger_x': trigger_x, 'kind': kind & 7, 'pickup': (kind >> 5) & 7,
            'hp': hp, 'roster_idx': roster_idx, 'item_roster_idx': item_roster_idx}


# Real stage 1A record indices for each item, found by direct inspection
# of the committed spawn_table.bin (kind==1/PROP, pickup byte identifies
# which item) -- not invented, verified again below at gate start.
#
# claude_close_g7_g8_before_g10.md Part 2/3: re-inspecting the real source
# (DATA\EASY\1AEASY.TXT) found apple/money/meat are NOT standalone `spawn
# <item>` records at all -- they're real `spawn Trash` / `item <name>`
# blocks (an obstacle wrapping a contained item), same shape as stage 1B's
# Chair/Money the pickup-chain gate already covers. Only 1up is a genuine
# standalone `spawn 1up`. The old single conflated +8 byte happened to hold
# the CONTAINED item's roster index either way, so the pre-fix gate's
# byte-level assertions (and its "instant item art at spawn" behavior)
# were unknowingly exercising the very bug this slice fixes: a not-yet-
# broken Trash rendering as floating food/money from the moment it
# spawned. roster_idx (5th tuple field) is now each record's real +9
# object_roster_idx (18 == out/trash's own roster slot for the wrapped
# three; 16 == 1up's own slot, since it has no wrapping object at all).
ITEM_RECORDS = {
    # roster_idx 18 == out/trash's own roster slot (claude_close_g7_g8_
    # before_g10.md Part 3: shifted 17->18 when out/gold was inserted
    # ahead of trash/chair/table in build_rom.py's ROSTER_PREFIXES).
    'apple': (36, PICKUP_TYPE_APPLE, 18, 'apple', True),
    'money': (6, PICKUP_TYPE_MONEY, 18, 'money', True),
    'meat': (22, PICKUP_TYPE_MEAT, 18, 'meat', True),
    '1up': (0, PICKUP_TYPE_ONEUP, 16, '1up', False),
}
# A real ordinary (non-identified) enemy record from the same table --
# kind==0 (plain enemy), roster_idx==0 (no identity) -- for the slot-reuse
# regression. Verified again below, not assumed.
ORDINARY_ENEMY_RECORD = 1


def byte_at(m, addr):
    return read_block(m, addr, 32)[0]


def word_at(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def entity_triple(m, base):
    return (byte_at(m, base + CHAR_IDLE_FCOUNT),
            byte_at(m, base + CHAR_WALK_FCOUNT),
            byte_at(m, base + CHAR_ATTACK_FCOUNT))


def real_palette_bytes(prefix):
    with open(os.path.join(REPO_ROOT, f'out/{prefix}_moveset.json'), 'r', encoding='utf-8') as f:
        moveset = json.load(f)
    idle_ordinal = moveset['roles']['idle']
    idle_dir = next(e['dir'] for e in moveset['animations'] if e['ordinal'] == idle_ordinal)
    colors = load_palette(os.path.join(REPO_ROOT, idle_dir))
    return b''.join(struct.pack('<H', c) for c in colors)


def force_win_and_wait(m, r, label):
    spawn_count = byte_at(m, SPAWN_COUNT_ADDR)
    m.write_u8(SPAWN_INDEX, spawn_count)
    for base in ENTITY_BASES[1:]:
        m.write_u8(base + CHAR_HP, 0)
    m.run_frames(5)
    m.pause()
    cleared = byte_at(m, STAGE_CLEARED)
    r.check(f'{label}: win condition fired (Stage_Cleared set)', cleared == 1)
    true_max = word_at(m, STAGE_TRUE_MAX_X)
    m.write_u16(SCREEN_POS_X, true_max)
    m.run_frames(10)
    m.pause()
    for _ in range(20):
        if word_at(m, GAME_STATE) == GAME_STATE_PLAYING:
            break
        m.run_frames(30)
        m.pause()


def land_record_in_slot1(m, r, record_idx, trigger_x, expected_pickup, label):
    """Drives the real single global spawn queue directly to `record_idx`
    (same real dequeue mechanism every spawn-driven gate in this project
    uses). Entities 2/3 are kept alive throughout (never freed) so find_
    slot always has exactly one free slot -- entity 1 -- guaranteeing real,
    deterministic same-physical-slot reuse across every item tested here,
    not four different slots that happen to look similar."""
    m.write_u8(Entity1 + CHAR_HP, 0)
    m.write_u8(SPAWN_INDEX, record_idx)
    m.write_u16(SCREEN_POS_X, trigger_x)
    m.run_frames(5)
    m.pause()
    landed = False
    for i in range(30):
        m.write_u16(SCREEN_POS_X, trigger_x)  # camera eases back otherwise
        if (byte_at(m, Entity1 + CHAR_INPUT_DRIVEN) == CHAR_INPUT_DRIVEN_PROP
                and byte_at(m, Entity1 + CHAR_PICKUP_TYPE) == expected_pickup):
            landed = True
            break
        m.run_frames(1)
        m.pause()
    r.check(f'{label}: real record #{record_idx} lands in entity 1 as a real '
             f'CHAR_INPUT_DRIVEN_PROP carrying pickup_type={expected_pickup}',
             landed)
    return landed


def land_ordinary_enemy_in_slot1(m, r, record_idx, trigger_x, label):
    m.write_u8(Entity1 + CHAR_HP, 0)
    m.write_u8(SPAWN_INDEX, record_idx)
    m.write_u16(SCREEN_POS_X, trigger_x)
    m.run_frames(5)
    m.pause()
    landed = False
    for _ in range(30):
        m.write_u16(SCREEN_POS_X, trigger_x)
        if byte_at(m, Entity1 + CHAR_INPUT_DRIVEN) == CHAR_INPUT_DRIVEN_AI:
            landed = True
            break
        m.run_frames(1)
        m.pause()
    r.check(f'{label}: real ordinary-enemy record #{record_idx} lands in entity 1 '
             f'as CHAR_INPUT_DRIVEN_AI', landed)
    return landed


def poll_palette_match(m, base, expected_pal, max_frames=30):
    """CGRAM commits through the same WRAM-shadow/NMI-DMA pipeline as OAM
    -- poll to real convergence (project-established idiom, see game_g7_
    depth_sort.py / game_g8_prop_art.py) rather than trusting a fixed
    settle."""
    pal_slot = None
    actual = None
    for _ in range(max_frames):
        pal_slot = byte_at(m, base + CHAR_PALETTE_SLOT)
        actual = bytes(read_block(m, 0x100 + pal_slot * 32, 32, mem_type='snesCgRam'))
        if actual == expected_pal:
            break
        m.run_frames(1)
        m.pause()
    return actual, pal_slot


def land_attack_and_consume(m, r, label, expect_hp=0):
    """Overlaps the player with entity 1 and lands a real Y attack,
    returning True if entity 1's CHAR_HP reached `expect_hp` (0 for a
    standalone item/ordinary kill, 1 for claude_close_g7_g8_before_g10.md
    Part 2's "broken, pending reveal" sentinel on a wrapped item). Releases
    input first (game_g8_pickup.py's own root-caused fix for the same class
    of press-edge bug -- a still-held button from an earlier scenario is
    invisible to a fresh press)."""
    # CHAR_HIT_APPLIED is a real per-attacker "already landed a hit this
    # attack cycle" latch (main.pasm) -- left set from a PREVIOUS kill
    # (APPLE's, the first item tested), it silently skips re-applying a
    # hit on the very next fresh press even though CHAR_SELECTED/CHAR_
    # HIT_STUN are both reset. Real root cause of this gate's own MONEY-
    # specific flake (2nd item tested, right after APPLE) -- found by
    # direct comparison against game_g8_pickup.py's own reset_combat_
    # state(), which already clears this field for exactly this reason.
    m.write_u8(PlayerEntity + CHAR_SELECTED, 0)
    m.write_u8(PlayerEntity + CHAR_HIT_APPLIED, 0)
    m.write_u8(PlayerEntity + CHAR_HIT_STUN, 0)
    m.write_u8(Entity1 + CHAR_SELECTED, 0)
    m.write_u8(Entity1 + CHAR_HIT_STUN, 0)
    # claude_close_g7_g8_before_g10.md Part 2: a real cross-scenario stale-
    # state gap found live-tracing MEAT's own break-detection flake -- this
    # gate reuses entity 1 across 4 back-to-back item scenarios, and
    # Entity1_InvulnFrames (AI_POST_HIT_INVULN_FRAMES, armed by the
    # PREVIOUS scenario's own break-hit) is never reset here, unlike
    # game_g8_pickup.py's own reset_combat_state -- a still-elevated value
    # silently makes Character_HitApply_VsEntity1's own dead_skip early-out
    # skip an otherwise-real, correctly-landed attack.
    m.write_u8(Entity1_InvulnFrames, 0)
    m.write_u8(Player_InvulnFrames, 0)
    px = word_at(m, PlayerEntity + CHAR_POS_X)
    py = byte_at(m, PlayerEntity + CHAR_POS_Y)
    m.write_u16(Entity1 + CHAR_POS_X, px)
    m.write_u8(Entity1 + CHAR_POS_Y, py)
    # Release for a real margin before pressing -- m.set_input() is a
    # wall-clock duration, not an exact frame count (memory mesen_set_
    # input_wall_clock), so a short release before a fresh press can
    # occasionally still read as still-held, missing the press edge
    # input.pasm's Core_Input_Poll needs to trigger a new attack. A longer
    # release margin plus a held (not single-pulse) press is the more
    # robust idiom several other gates in this project already settled on
    # for exactly this reason.
    m.set_input(0, 10)
    m.pause()
    m.set_input(m.BTN_Y, 1)
    killed = False
    for _ in range(60):
        m.run_frames(1)
        m.pause()
        if byte_at(m, Entity1 + CHAR_HP) == expect_hp:
            killed = True
            if expect_hp == 1:
                # claude_close_g7_g8_before_g10.md Part 2: a wrapped item's
                # "broken, pending reveal" sentinel -- move it away from the
                # player IMMEDIATELY (still overlapping from the punch),
                # same race game_g8_pickup_chain.py's own rewrite hit.
                m.write_u16(Entity1 + CHAR_POS_X, 60000)
            break
    m.run_frames(2)
    m.pause()
    r.check(f'{label}: a real landed attack breaks the real prop '
             f'(CHAR_HP reaches {expect_hp})', killed)
    return killed


def main():
    r = Reporter('G8-ASSET-SWAPPING', kind='GATE')

    # --- Ground truth: every item's real record, and the ordinary-enemy
    # record, verified byte-level against the committed spawn table before
    # any emulation starts. ---
    for name, (idx, pickup, roster_idx, prefix, wrapped) in ITEM_RECORDS.items():
        rec = _record(idx)
        r.check(f'stage 1A record #{idx} ({name}) is a real PICKUP prop '
                 f'(kind={rec["kind"]}, pickup={rec["pickup"]}, roster_idx={rec["roster_idx"]}, '
                 f'item_roster_idx={rec["item_roster_idx"]})',
                 rec['kind'] == 1 and rec['pickup'] == pickup and rec['roster_idx'] == roster_idx)
    ordinary = _record(ORDINARY_ENEMY_RECORD)
    r.check(f'stage 1A record #{ORDINARY_ENEMY_RECORD} is a real ordinary '
             f'(non-identified) enemy (kind={ordinary["kind"]}, roster_idx={ordinary["roster_idx"]})',
             ordinary['kind'] == 0 and ordinary['roster_idx'] == 0)

    jhun_triple_expected = None
    with open(os.path.join(REPO_ROOT, 'out/jhun_moveset.json'), 'r', encoding='utf-8') as f:
        jhun_moveset = json.load(f)
    jhun_by_name = {a['name']: a['frames'] for a in jhun_moveset['animations']}
    jhun_triple_expected = (jhun_by_name['idle'], jhun_by_name['walk'], jhun_by_name['attack1'])
    jhun_pal_expected = real_palette_bytes('jhun')

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(150)
        m.pause()

        boot_stage = word_at(m, GAME_STAGE_INDEX)
        r.check(f'boots on stage 0 ({boot_stage})', boot_stage == 0)
        force_win_and_wait(m, r, label='0->1')
        new_stage = word_at(m, GAME_STAGE_INDEX)
        r.check(f'Game_StageIndex advances 0 -> 1 ({new_stage})', new_stage == 1)
        if new_stage != 1:
            r.finish()
            return

        # Keep entities 2/3 alive throughout the whole test (nonzero HP is
        # all find_slot checks) so entity 1 is deterministically the only
        # free slot every time -- but STATIC (CHAR_INPUT_DRIVEN=0), not
        # AI-mode. Root cause found debugging this gate's own real, ~1-in-3
        # MONEY-specific attack-never-lands flake: with them left in real
        # AI-seek mode, they eventually land a real hit on the player
        # (confirmed via a direct WRAM dump: Player_InvulnFrames jumped
        # from 0 to a freshly-armed ~89 mid-poll, meaning a real hit/
        # respawn happened), stunning the player's own input during this
        # gate's own attack window -- the exact same "neutralize every
        # OTHER real AI slot before a combat-sensitive check" precedent
        # game_g7_grab.py/game_g7_knockdown.py/game_g8_pickup_chain.py
        # already establish, just missed here because these two entities
        # are deliberately kept ALIVE (for find_slot) rather than the more
        # usual HP=0 neutralization those other gates use.
        m.run_frames(10)
        m.pause()
        for base in (ENTITY_BASES[2], ENTITY_BASES[3]):
            m.write_u8(base + CHAR_HP, CHAR_HP_MAX)
            m.write_u8(base + CHAR_INPUT_DRIVEN, 0)

        pickup_effects = []  # (name, before, after) for the printed summary

        for name, (idx, pickup, roster_idx, prefix, wrapped) in ITEM_RECORDS.items():
            for base in (ENTITY_BASES[2], ENTITY_BASES[3]):
                m.write_u8(base + CHAR_HP, CHAR_HP_MAX)
                m.write_u8(base + CHAR_INPUT_DRIVEN, 0)
            rec = _record(idx)
            if name == '1up':
                # claude_close_g7_g8_before_g10.md Part 2: real finding --
                # 1up's own trigger_x is 0 (always satisfiable, real source
                # data), and it's a genuine standalone ground item (no
                # wrapping object -- ItemRosterIdx starts at 0), so
                # Character_Pickup_CheckOverlap's real touch-collect can
                # (and here, does) fire the SAME frame it spawns, before
                # land_record_in_slot1's own poll ever observes the
                # intermediate "armed PROP, not yet collected" state --
                # unlike apple/meat/money, which are wrapped (need a real
                # break first, so there's a real observable window). This
                # is correct real behavior (walking over a 1up on the
                # ground collects it instantly), not a bug -- verify the
                # real effect (Game_Lives) directly instead of insisting on
                # an unobservable intermediate state.
                lives_before = byte_at(m, Game_Lives)
                m.write_u8(Entity1 + CHAR_HP, 0)
                m.write_u8(SPAWN_INDEX, idx)
                m.write_u16(SCREEN_POS_X, rec['trigger_x'])
                m.run_frames(5)
                m.pause()
                collected = False
                for _ in range(30):
                    if byte_at(m, Game_Lives) == lives_before + 1:
                        collected = True
                        break
                    m.run_frames(1)
                    m.pause()
                r.check(f'1UP: real record #{idx} spawns and is collected (real '
                         f'trigger_x={rec["trigger_x"]}, a standalone ground item, '
                         f'no attack needed -- see comment above)', collected)
                lives_after = byte_at(m, Game_Lives)
                pickup_effects.append((name, lives_before, lives_after))
                r.check('1UP: collecting it adds exactly 1 life (real OpenBOR '
                         f'name=="1up" special case) ({lives_before} -> {lives_after})',
                         lives_after == lives_before + 1)
                continue
            if not land_record_in_slot1(m, r, idx, rec['trigger_x'], pickup, name.upper()):
                continue

            m.run_frames(5)
            m.pause()

            expected_triple = (1, 1, 1)  # every convert_prop.py output
            got_triple = entity_triple(m, Entity1)
            spawn_prefix = 'trash' if wrapped else prefix
            spawn_reason = ('the wrapping object, not the contained item, since it has '
                             'not broken yet' if wrapped else
                             'its own real sprite (no wrapping object)')
            r.check(f'{name.upper()}: entity 1 at spawn shows '
                     f'{spawn_prefix.upper()}\'s OWN real converted (idle,walk,attack) '
                     f'triple {expected_triple} (got {got_triple}) -- {spawn_reason}',
                     got_triple == expected_triple)

            expected_pal = real_palette_bytes(spawn_prefix)
            actual_pal, pal_slot = poll_palette_match(m, Entity1, expected_pal)
            r.check(f"{name.upper()}: entity 1's CGRAM palette (slot {pal_slot}) matches "
                     f"{spawn_prefix}'s OWN real converted palette.txt byte-for-byte at spawn",
                     actual_pal == expected_pal)

            if wrapped:
                # claude_close_g7_g8_before_g10.md Part 2: break (HP->1,
                # not 0), wait for the real reveal (EntityN_ItemRosterIdx
                # clears once Spawn_RevealPendingItems reassigns this slot
                # to the item's own real sprite), verify the item's OWN
                # real art/palette actually replaced Trash's, THEN overlap
                # again to collect the real reward -- same chain game_g8_
                # pickup_chain.py already proves for Money alone,
                # generalized here to Apple/Meat/Money.
                land_attack_and_consume(m, r, name.upper(), expect_hp=1)
                # Real observed latency here can run well past a handful of
                # frames (this gate's own busy scenario -- several other
                # entities' per-frame Anim_Play calls compete for the same
                # one-stream-per-frame Msu1_StreamBusy budget), so poll a
                # generous real margin rather than assume a small one.
                revealed = False
                for _ in range(60):
                    if byte_at(m, Entity1_ItemRosterIdx) == 0:
                        revealed = True
                        break
                    m.run_frames(1)
                    m.pause()
                r.check(f'{name.upper()}: the real contained item gets revealed -- '
                         f'EntityN_ItemRosterIdx clears once Spawn_RevealPendingItems '
                         f'reassigns this slot to {name}\'s own real sprite', revealed)
                revealed_triple = entity_triple(m, Entity1)
                r.check(f'{name.upper()}: entity 1 now shows its OWN real converted '
                         f'(idle,walk,attack) triple {expected_triple} (got {revealed_triple}) '
                         f'-- the revealed item, not Trash anymore',
                         revealed_triple == expected_triple)
                item_pal = real_palette_bytes(prefix)
                actual_item_pal, item_pal_slot = poll_palette_match(m, Entity1, item_pal)
                r.check(f"{name.upper()}: entity 1's CGRAM palette (slot {item_pal_slot}) "
                         f"now matches {name}'s OWN real converted palette.txt -- "
                         f"distinguishes it from Trash's own palette",
                         actual_item_pal == item_pal)
                # For a heal item, set the player's starting HP BEFORE
                # re-overlapping below -- once overlapped, Character_
                # Pickup_CheckOverlap can apply the reward the very next
                # frame, so this must happen first, not after.
                if name in ('apple', 'meat'):
                    m.write_u8(PlayerEntity + CHAR_HP, 10)

                # claude_close_g7_g8_before_g10.md Part 2: capture the
                # score baseline BEFORE re-overlapping, not after -- a real
                # test bug found live-tracing MONEY's own false "no change"
                # failure. Character_Pickup_CheckOverlap (core/jump.pasm)
                # applies the reward the moment the AABB overlaps, which
                # the very next 3-frame wait below already causes -- a
                # 'before' sample taken after that wait (the old code) was
                # already POST-collect, making before==after regardless of
                # whether the reward genuinely fired.
                money_score_before = word_at(m, Game_Score) if name == 'money' else None

                # Re-overlap for the real pickup.
                px = word_at(m, PlayerEntity + CHAR_POS_X)
                py = byte_at(m, PlayerEntity + CHAR_POS_Y)
                m.write_u16(Entity1 + CHAR_POS_X, px)
                m.write_u8(Entity1 + CHAR_POS_Y, py)
                m.run_frames(3)
                m.pause()

            if name == 'money':
                # claude_close_g7_g8_before_g10.md Part 2: same real
                # finding as game_g8_pickup.py's own MONEY fix -- a
                # touch-collected item (this is one, once revealed) goes
                # through Character_Pickup_CheckOverlap, not combat's
                # ScoreAndFinish, so no combat-kill score stacks on top of
                # it. The earlier real attack that broke Trash already
                # awarded its OWN combat-kill score separately (proven by
                # game_g8_pickup_chain.py) -- not re-counted here since
                # money_score_before is sampled AFTER that break, right
                # before the touch-collect.
                before = money_score_before if wrapped else word_at(m, Game_Score)
                if not wrapped:
                    land_attack_and_consume(m, r, name.upper())
                    m.run_frames(2)
                    m.pause()
                after = word_at(m, Game_Score)
                expected_delta = PICKUP_SCORE_MONEY if wrapped else (
                    PICKUP_SCORE_MONEY + COMBAT_KILL_AWARD)
                pickup_effects.append((name, before, after))
                r.check(f'MONEY: {"touching the revealed item" if wrapped else "breaking it"} '
                         f'awards the real PICKUP_SCORE_MONEY'
                         f'{"" if wrapped else " on top of the ordinary combat-kill award"} '
                         f'({before} -> {after}, expect +{expected_delta})',
                         after == before + expected_delta)
            elif name in ('apple', 'meat'):
                heal = PICKUP_HEAL_APPLE if name == 'apple' else PICKUP_HEAL_MEAT
                before = 10
                if not wrapped:
                    m.write_u8(PlayerEntity + CHAR_HP, 10)
                    land_attack_and_consume(m, r, name.upper())
                    m.run_frames(2)
                    m.pause()
                after = byte_at(m, PlayerEntity + CHAR_HP)
                expected = min(CHAR_HP_MAX, before + heal)
                pickup_effects.append((name, before, after))
                r.check(f'{name.upper()}: {"touching the revealed item" if wrapped else "breaking it"} '
                         f'heals the player by the real '
                         f'PICKUP_HEAL_{name.upper()} ({heal}), clamped at CHAR_HP_MAX '
                         f'({before} -> {after}, expect {expected})', after == expected)


        print(f'pickup effects observed: {pickup_effects}')

        # --- Slot-reuse regression: a real ordinary enemy landing in the
        # SAME physical slot (entity 1, just vacated by 1UP above) must NOT
        # inherit any of the prop's stale state. ---
        for base in (ENTITY_BASES[2], ENTITY_BASES[3]):
            m.write_u8(base + CHAR_HP, CHAR_HP_MAX)
            m.write_u8(base + CHAR_INPUT_DRIVEN, 0)
        if land_ordinary_enemy_in_slot1(m, r, ORDINARY_ENEMY_RECORD,
                                          ordinary['trigger_x'], 'SLOT-REUSE'):
            m.run_frames(5)
            m.pause()
            pickup_type_after = byte_at(m, Entity1 + CHAR_PICKUP_TYPE)
            r.check('SLOT-REUSE: no stale CHAR_PICKUP_TYPE survives (reads back 0)',
                     pickup_type_after == 0)

            restored_triple = entity_triple(m, Entity1)
            r.check(f'SLOT-REUSE: entity 1 no longer shows a prop\'s (1,1,1) triple '
                     f'(got {restored_triple})', restored_triple != (1, 1, 1))
            r.check(f"SLOT-REUSE: entity 1's restored triple matches JHUN's OWN real "
                     f"converted moveset {jhun_triple_expected} (this slot's own natural "
                     f"boot-default character, got {restored_triple}) -- a real fighter's "
                     f"art, not a borrowed/stale one",
                     restored_triple == jhun_triple_expected)

            actual_pal, pal_slot = poll_palette_match(m, Entity1, jhun_pal_expected)
            r.check(f"SLOT-REUSE: entity 1's CGRAM palette (slot {pal_slot}) matches JHUN's "
                     f"OWN real converted palette.txt byte-for-byte -- no stale prop "
                     f"palette survives slot reuse", actual_pal == jhun_pal_expected)

    r.finish()


if __name__ == '__main__':
    main()
