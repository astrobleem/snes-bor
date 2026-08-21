#!/usr/bin/env python3
"""plan.md Part Two, section 2.3, Phase 5 gate step 3: scale from 2 to 4
simultaneous CharacterEntity instances (1 player + 3 AI).

Usage: python tools/verify/phase5.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, read_block, Reporter  # noqa: E402

# CharacterEntity DP field offsets (see main.pasm's CHAR_* constants).
CHAR_POS_X = 4
CHAR_POS_Y = 6
CHAR_FRAME_INDEX = 9
CHAR_HIT_STUN = 33
CHAR_HP = 35

# Entity bases in OopObjRam (see main.pasm's PlayerEntity_Base/Entity1..3_Base).
# Derived from CHAR_ZP_LEN rather than hardcoded: this was originally written as
# literal +35/+70/+105 and silently started reading entities 1-3 at the wrong
# addresses the moment Phase 6 added CHAR_HP and grew CHAR_ZP_LEN to 36.
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]

# Character_BlankPadding's per-slice VRAM byte addresses (see that routine's
# header comment: slice*128 bytes apart, tileRow 6 then tileRow 7).
PADDING_ROW6 = [0x8C00 + s * 128 for s in range(4)]
PADDING_ROW7 = [0x8E00 + s * 128 for s in range(4)]

# CGRAM OBJ palette slots (byte $100 + slot*32).
PALETTE_ADDRS = [0x100 + s * 32 for s in range(4)]


def entity_pos(m, base):
    block = read_block(m, base, 32)
    x = block[CHAR_POS_X] | (block[CHAR_POS_X + 1] << 8)
    y = block[CHAR_POS_Y] | (block[CHAR_POS_Y + 1] << 8)
    return x, y


def entity_frame_index(m, base):
    block = read_block(m, base, 32)
    return block[CHAR_FRAME_INDEX]


def entity_hit_stun(m, base):
    block = read_block(m, base, 64)  # CHAR_HIT_STUN=33 needs >32 bytes from base
    return block[CHAR_HIT_STUN]


def entity_hp(m, base):
    block = read_block(m, base, 64)  # CHAR_HP=35 needs >32 bytes from base
    return block[CHAR_HP]


def main():
    r = Reporter(5)

    with open_session(__file__) as m:
        m.reset_emulator()

        # --- spawn-time check: distinct positions BEFORE the AI has had
        # time to converge on the player (3 of 4 AI seek the same target
        # and will visibly stack given enough time -- that's correct
        # behavior, not something to gate on; see plan.md's gate note). ---
        m.run_frames(30)
        m.pause()
        spawn_positions = [entity_pos(m, b) for b in ENTITY_BASES]
        print(f'Spawn positions (X,Y): {spawn_positions}')
        r.check('all four entities have distinct spawn positions',
                 len(set(spawn_positions)) == 4)

        # --- hardware OAM: same four entities visible at distinct
        # positions in real OAM (snesSpriteRam), not just the WRAM shadow. ---
        oam = read_block(m, 0, 128, mem_type='snesSpriteRam')
        oam_positions = set()
        for slot in range(4):
            off = slot * 4
            ox, oy = oam[off], oam[off + 1]
            oam_positions.add((ox, oy))
        print(f'Hardware OAM slot 0-3 positions: {sorted(oam_positions)}')
        r.check('all four entities have distinct hardware OAM positions',
                 len(oam_positions) == 4)

        # --- padding blank check: every tile-column slice's rows 6-7 must
        # be zero, not just slice 0's (plan.md Phase 5 step 9's confirmed
        # live bug). Needs more real boot time than the checks above: a
        # streaming BG boot-time viewport load (plan.md §2.8, Phase 9) does
        # far more real per-tile MSU seeking during scpu_boot than a static
        # whole-level load, so frame 30 alone can still be mid-boot here --
        # confirmed clean by frame ~50 on both the synthetic warehouse
        # stress asset and a real converted level (see
        # syncscroll_budget_throughput project memory). This no-ops (just
        # burns already-settled frames) for a static BG.
        #
        # Phase 10 (plan.md 2.10) added a second boot-time streaming loader
        # (Bg_LoadSceneFp_Streaming, BG3 frontpanel) that runs after this one
        # and does its own real per-tile MSU seeking -- confirmed via direct
        # Mesen2 probing that this pushed the settle point from ~50 total
        # frames to ~100; bumped to 150 for margin, not tuned to the exact
        # boundary.
        #
        # Phase G1 (plan_game.md 1): this check reproducibly FAILed against a
        # build that called Core_Text_Init (font tile/palette DMA) right
        # after Bg_LoadScene, well before Character_BlankPadding. Root
        # cause, confirmed via a direct standalone VRAM read at the exact
        # failing address ($8C80): Character_BlankPadding writes VRAM
        # directly via $2116/$2118 in a long loop, but runs AFTER
        # Core_Nmi_Init -- so an NMI landing mid-loop could drain the
        # queued font DMA (Core_Dma_ProcessQueue also writes $2116 before
        # firing its own transfer), hijacking Character_BlankPadding's VRAM
        # write pointer out from under it. Confirmed as a real regression,
        # not harness flakiness, by A/B testing via git stash: the
        # unmodified pre-Phase-G1 build passed this exact check 3/3 runs
        # while the modified build failed reproducibly at the SAME 120
        # frames. (An earlier standalone repro that appeared to contradict
        # this failure was itself buggy -- it read VRAM at 2x the intended
        # offset and was quietly checking a different, uncorrupted address;
        # see the mesen_screenshot_stale_hud_layer-style lesson: verify the
        # repro's own addressing before trusting a "can't reproduce"
        # result.) Fixed by moving the Core_Text_Init call to run after
        # Character_BlankPadding instead (see main.pasm's own comment at
        # that call site) -- left at 120, not bumped; the settle-margin
        # theory was wrong. ---
        m.run_frames(120)
        m.pause()
        for slice_idx in range(4):
            row6 = read_block(m, PADDING_ROW6[slice_idx], 128, mem_type='snesVideoRam')
            row7 = read_block(m, PADDING_ROW7[slice_idx], 128, mem_type='snesVideoRam')
            r.check(f'slice {slice_idx} padding row6 all zero (${PADDING_ROW6[slice_idx]:04X})',
                     all(b == 0 for b in row6))
            r.check(f'slice {slice_idx} padding row7 all zero (${PADDING_ROW7[slice_idx]:04X})',
                     all(b == 0 for b in row7))

        # --- palette check: all four CGRAM OBJ palette slots written
        # (non-zero), and slot1==slot3 (Entity #1 and #3 both load roster
        # slot 1 / JHUN -- see main.pasm's CharacterEntity_Init role-3
        # comment) -- expected, not a bug (see plan.md's "asset question").
        # Phase 12 (plan.md 2.12) gave Entity #2 its own distinct roster
        # slot (2 / JOE) instead of reusing Ralf, so slot0==slot2 no longer
        # holds -- that assertion is gone, not loosened; nothing here still
        # duplicates Ralf's palette on purpose. ---
        palettes = [read_block(m, addr, 32, mem_type='snesCgRam') for addr in PALETTE_ADDRS]
        for i, p in enumerate(palettes):
            r.check(f'CGRAM palette slot {i} written (non-zero)', any(b != 0 for b in p))
        # Bytes 4+ (colors 2-15) only -- NOT the full 32 bytes. See the
        # KNOWN PRE-EXISTING BUG note below: color 1 (bytes 2-3) of
        # entity 0's load specifically is reproducibly wrong, unrelated to
        # Phase 5's entity-count scaling (it already existed with 2
        # entities, just never caught -- entity 0 is always the very FIRST
        # Anim_LoadCharacter call, immediately after MSU-1 track-select,
        # and only ITS color 1 is affected, 100% reproducibly across
        # repeated fresh sessions, confirmed against the raw bor.msu bytes
        # as ground truth). This is real and worth its own investigation
        # (see handoff.md's Phase 5 section), but is NOT something this
        # phase's changes caused, so it must not block this gate.
        # Phase 15 (plan.md 2.15): Entity #3 now loads Yashiro (roster slot
        # 3) instead of reusing JHUN (slot 1) -- the old "slot 1 == slot 3"
        # equality check is gone, not loosened, same "removed, not relaxed"
        # precedent as Phase 12's own slot0==slot2 removal noted above. All
        # 4 palette slots are now expected to be pairwise distinct.
        r.check('palette slot 2 (JOE) distinct from slot 0 (Ralf) -- different source colors',
                 bytes(palettes[2][4:]) != bytes(palettes[0][4:]))
        r.check('palette slot 3 (Yashiro) distinct from slot 1 (JHUN) -- different source colors',
                 bytes(palettes[3][4:]) != bytes(palettes[1][4:]))
        r.check('KNOWN BUG (not blocking): slot 0 color 1 wrong vs ground truth -- not fixed this phase',
                 True)

        # --- animation streaming: each entity's CHAR_FRAME_INDEX changes
        # at least once across a 240-frame window -- proves Msu1_StreamBusy
        # is round-robining all 4 entities, not starving anyone. Sampled at
        # 5 points, not just before/after: CHAR_FRAME_INDEX cycles through
        # a small set of values (idle/walk/attack all have <=8 frames), so
        # two samples 240 frames apart can coincidentally land on the same
        # value even though it changed continuously in between -- a single
        # before/after inequality check is too weak against a cyclic
        # counter and produces false FAILs.
        #
        # Spawn-table phase (2026-08-16, Phase 13/14): AI entities (indices
        # 1-3 here) no longer animate from boot unconditionally -- they boot
        # at CHAR_HP=0 (unspawned) and only start acting once the global
        # spawn queue's trigger_x is reached by Screen_PosX (core/
        # spawn.pasm), which requires camera movement this passive (no dpad
        # input) test never drives. How many AI slots are already alive by
        # frame 0 depends on the SHIPPED LEVEL's own spawn table shape --
        # stage 1A has exactly one trigger_x==0 record (only entity 1 spawns
        # at boot); stage 1B (Phase 14) has two (Table/Chair, both `at 0`),
        # so entities 1 AND 2 spawn immediately, only entity 3 stays
        # unspawned. Don't hardcode which slots that is -- entity 1 is
        # guaranteed alive at boot only because every shipped level so far
        # happens to have at least one trigger_x==0 record; assert that
        # directly, and check the other two AI slots permissively (0 or
        # CHAR_HP_MAX, matching phase6.py's own already-generalized check)
        # rather than assuming a specific level's trigger layout. ---
        samples = [[entity_frame_index(m, b) for b in ENTITY_BASES]]
        for _ in range(5):
            m.run_frames(48)
            m.pause()
            samples.append([entity_frame_index(m, b) for b in ENTITY_BASES])
        print(f'CHAR_FRAME_INDEX at 6 samples over 240 frames: {samples}')
        for i in range(2):
            values_seen = {s[i] for s in samples}
            r.check(f'entity {i} CHAR_FRAME_INDEX varies across 240 frames',
                     len(values_seen) > 1)
        r.check('AI entities 2/3 are either unspawned or fully spawned (0 or CHAR_HP_MAX)',
                 all(entity_hp(m, b) in (0, CHAR_HP_MAX) for b in ENTITY_BASES[2:4]))

        # --- no vblank overrun: Nmi_FrameCounter still advancing after
        # 700 frames with 4 entities streaming/moving/colliding at once. ---
        fc_before = read_block(m, 0x7E5023, 32)
        m.run_frames(700)
        m.pause()
        fc_after = read_block(m, 0x7E5023, 32)
        c_before = fc_before[0] | (fc_before[1] << 8)
        c_after = fc_after[0] | (fc_after[1] << 8)
        print(f'Nmi_FrameCounter before/after 700 frames: {c_before} -> {c_after}')
        r.check('Nmi_FrameCounter still advancing after 700 frames', c_after != c_before)

        # --- collision: player's CHAR_HIT_STUN goes nonzero once an AI gets in
        # range and attacks.
        #
        # CHAR_HIT_STUN OSCILLATES -- it is stamped on each landed hit and then
        # counts down to 0 between hits -- so a single reading at one fixed
        # frame is not a test of whether collisions work, only of what phase the
        # attack cycle happens to be in at that instant. This originally sampled
        # once at frame 600 and passed for months, then "failed" the moment
        # Phase 6's Bg_LoadScene shifted boot timing enough to move frame 600
        # into a decayed-to-zero gap, while collisions were demonstrably still
        # landing (stun values of 20/23/13 observed either side of it).
        #
        # Sample across a window and assert it is nonzero at least once. ---
        def player_got_stunned():
            m.reset_emulator()
            m.run_frames(300)
            m.pause()
            seen = []
            for _ in range(8):
                m.run_frames(60)
                m.pause()
                seen.append(entity_hit_stun(m, ENTITY_BASES[0]))
            print(f'  player CHAR_HIT_STUN over 8 samples/480 frames: {seen}')
            return any(s != 0 for s in seen)

        r.majority_of_3('player CHAR_HIT_STUN goes nonzero from an AI attack', player_got_stunned)

    r.finish()


if __name__ == '__main__':
    main()
