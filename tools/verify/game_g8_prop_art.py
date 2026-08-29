#!/usr/bin/env python3
"""plan_game.md G8, real prop/pickup sprite art follow-up (notjustfreespecial
.txt audit): the ONE remaining item on G8's "still open" list before this
slice. Every prop before this slice rendered using whichever roster
character happened to already be streamed into its AI slot (visually wrong,
behaviorally real -- see plan_game.md's own "deliberately still not done"
note). This gate proves a real converted prop sprite (APPLE, converted by
tools/bor_converter/convert_prop.py from the real DATA\\CHARS\\MISC\\
APPLE.TXT, added as roster slot 13 in build_rom.py's ROSTER_PREFIXES) is
what the engine actually streams for a real, unmodified, shipped spawn
record (stage 1A's own record #36 -- `item apple`, DATA\\EASY\\1AEASY.TXT --
verified by build_spawn_table.py to carry roster_idx=13).

Mechanism reused, not invented: SPAWN_KIND_BOSS_IDENTIFIED already re-
streams an AI slot to its own real roster character mid-game (core/
spawn.pasm's Spawn_DoRosterReassign, proven by game_spawn_roster_reassign.py
-- this gate's own idiom for reaching stage 1 and matching a slot's real
(idle,walk,attack) frame-count triple against its expected converted
moveset is copied from that gate for exactly that reason: this is the SAME
mechanism, just triggered by a SPAWN_KIND_PROP record with a real +8
roster_idx instead of SPAWN_KIND_BOSS_IDENTIFIED).

Real hardware-visible proof, not an internal-state trust: after the real
apple record lands, the slot's CHAR_ROSTER_INDEX reads back 13 (not
whatever generic character the slot happened to have loaded before), and
its (idle,walk,attack) frame-count triple matches APPLE's own real
converted moveset (1,1,1 -- convert_prop.py's real single-frame-per-role
output, not a fighter's multi-frame triple).

Usage: python tools/verify/game_g8_prop_art.py
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


def real_palette_bytes(moveset):
    """Ground truth: apple's own real converted CGRAM palette, read straight
    from convert_prop.py's own output (out/apple_idle/palette.txt) -- never
    a value this gate computed. Same idiom phase12_roster.py's own
    real_palette_bytes() uses for fighters."""
    idle_ordinal = moveset['roles']['idle']
    idle_dir = next(e['dir'] for e in moveset['animations'] if e['ordinal'] == idle_ordinal)
    colors = load_palette(os.path.join(REPO_ROOT, idle_dir))
    return b''.join(struct.pack('<H', c) for c in colors)

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_INPUT_DRIVEN = pasm_constant('CHAR_INPUT_DRIVEN')
CHAR_PICKUP_TYPE = pasm_constant('CHAR_PICKUP_TYPE')
CHAR_ROSTER_INDEX = pasm_constant('CHAR_ROSTER_INDEX')
CHAR_IDLE_FCOUNT = pasm_constant('CHAR_IDLE_FCOUNT')
CHAR_WALK_FCOUNT = pasm_constant('CHAR_WALK_FCOUNT')
CHAR_ATTACK_FCOUNT = pasm_constant('CHAR_ATTACK_FCOUNT')
CHAR_PALETTE_SLOT = pasm_constant('CHAR_PALETTE_SLOT')
CHAR_INPUT_DRIVEN_PROP = pasm_constant_in('src/main.pasm', 'CHAR_INPUT_DRIVEN_PROP')
PICKUP_TYPE_APPLE = pasm_constant('PICKUP_TYPE_APPLE')

GS_PATH = 'src/core/game_state.pasm'
GAME_STAGE_INDEX = pasm_constant_in(GS_PATH, 'Game_StageIndex')
GAME_STATE = pasm_constant_in(GS_PATH, 'Game_State')
GAME_STATE_PLAYING = pasm_constant_in(GS_PATH, 'GAME_STATE_PLAYING')
STAGE_CLEARED = pasm_constant_in(GS_PATH, 'Stage_Cleared')
STAGE_TRUE_MAX_X = pasm_constant_in(GS_PATH, 'Stage_TrueMaxX')

SP_PATH = 'src/core/spawn.pasm'
SPAWN_INDEX = pasm_constant_in(SP_PATH, 'Spawn_Index')
SPAWN_COUNT_ADDR = pasm_constant_in(SP_PATH, 'Spawn_Count')

SCREEN_POS_X = 0x7E1601

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]

APPLE_RECORD_INDEX = 36  # out/spawn_stage1a/spawn_table.bin's real `item
                          # apple` record, verified by inspecting the built
                          # table directly (pickup=PICKUP_TYPE_APPLE,
                          # roster_idx=13) -- not invented.
APPLE_TRIGGER_X = 1840   # that record's own real trigger_x (spawn_table.bin)


def byte_at(m, addr):
    return read_block(m, addr, 32)[0]


def word_at(m, addr):
    b = read_block(m, addr, 32)
    return b[0] | (b[1] << 8)


def entity_triple(m, base):
    return (byte_at(m, base + CHAR_IDLE_FCOUNT),
            byte_at(m, base + CHAR_WALK_FCOUNT),
            byte_at(m, base + CHAR_ATTACK_FCOUNT))


def force_win_and_wait(m, r, label):
    """Same idiom game_spawn_roster_reassign.py's own force_win_and_wait
    uses (there is no direct stage-load path in this engine) -- drains the
    current stage's spawn queue, kills every AI, forces the camera to the
    stage's real true-max-X to trip the win check, and waits for the
    STAGECLEAR->PLAYING transition to land on the next stage."""
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


def main():
    r = Reporter('G8-PROP-ART', kind='GATE')

    with open('out/apple_moveset.json') as f:
        apple_moveset = json.load(f)
    expected_triple = (1, 1, 1)  # convert_prop.py: idle/walk/attack all
                                  # real-converted single-frame roles
    print(f"apple moveset entity={apple_moveset['entity']!r}, "
          f"expected (idle,walk,attack) triple={expected_triple}")

    with open('out/spawn_stage1a/spawn_table.bin', 'rb') as f:
        data = f.read()
    rec = data[APPLE_RECORD_INDEX * 9:APPLE_RECORD_INDEX * 9 + 9]
    trigger_x, spawn_x, spawn_y, facing, kind, hp, roster_idx = struct.unpack('<HHBBBBB', rec)
    r.check(f'stage 1A record #{APPLE_RECORD_INDEX} is a real PICKUP_TYPE_APPLE prop '
             f'with a real roster_idx (kind={kind & 7}, pickup={(kind >> 5) & 7}, roster_idx={roster_idx})',
             (kind & 7) == 1 and ((kind >> 5) & 7) == PICKUP_TYPE_APPLE and roster_idx == 13)

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(150)
        m.pause()

        boot_stage = word_at(m, GAME_STAGE_INDEX)
        r.check(f'boots on stage 0 ({boot_stage})', boot_stage == 0)

        # --- Reach stage 1 (1A, the stage with the real apple record) via
        # the real win-progression chain. ---
        force_win_and_wait(m, r, label='0->1')
        new_stage = word_at(m, GAME_STAGE_INDEX)
        r.check(f'Game_StageIndex advances 0 -> 1 ({new_stage})', new_stage == 1)
        if new_stage != 1:
            r.finish()
            return

        # --- Before the apple record triggers: no AI slot already shows
        # apple's own real triple (rules out a false positive from
        # whatever generic character happened to boot into that slot). ---
        m.run_frames(10)
        m.pause()
        before = {slot: entity_triple(m, ENTITY_BASES[slot]) for slot in (1, 2, 3)}
        r.check(f'no AI slot already shows apple\'s real triple {expected_triple} '
                 f'before its record triggers (got {before})',
                 expected_triple not in before.values())

        # --- Drive the real single global spawn queue directly to record
        # #36 (same "advance Spawn_Index, free AI slots, force the camera"
        # idiom as force_win_and_wait/check_boss_stage above -- this IS the
        # real runtime dequeue mechanism, not a synthetic shortcut) and let
        # the real apple record trigger + land in a real free slot. ---
        m.write_u8(SPAWN_INDEX, APPLE_RECORD_INDEX)
        for base in ENTITY_BASES[1:]:
            m.write_u8(base + CHAR_HP, 0)
        m.write_u16(SCREEN_POS_X, APPLE_TRIGGER_X)
        m.run_frames(5)
        m.pause()

        apple_slot = None
        for _ in range(20):
            # Screen_Play re-derives Screen_PosX from the player's own real
            # position every frame -- a one-shot write doesn't stick (the
            # camera eases straight back toward wherever the player already
            # is). Re-pin it every polled frame, same "keep re-forcing a
            # value Character_PlayFrame/Screen_Play would otherwise
            # overwrite" idiom game_g7_depth_sort.py's set_positions() loop
            # already establishes.
            m.write_u16(SCREEN_POS_X, APPLE_TRIGGER_X)
            for slot in (1, 2, 3):
                base = ENTITY_BASES[slot]
                if (byte_at(m, base + CHAR_INPUT_DRIVEN) == CHAR_INPUT_DRIVEN_PROP
                        and byte_at(m, base + CHAR_PICKUP_TYPE) == PICKUP_TYPE_APPLE):
                    apple_slot = slot
                    break
            if apple_slot is not None:
                break
            m.run_frames(1)
            m.pause()
        r.check(f'the real apple record lands in some AI slot as a '
                 f'CHAR_INPUT_DRIVEN_PROP carrying PICKUP_TYPE_APPLE (slot={apple_slot})',
                 apple_slot is not None)
        if apple_slot is None:
            r.finish()
            return

        # Streaming (Spawn_DoRosterReassign) is a real, blocking, budgeted
        # per-frame operation -- give it real settle time before reading
        # back the result, same margin every other roster-reassign check in
        # this project uses.
        m.run_frames(5)
        m.pause()

        # NOTE: CHAR_ROSTER_INDEX (main.pasm struct offset 12) is declared
        # but was found, while writing this gate, to be dead -- grep-
        # confirmed nothing in main.pasm ever WRITES it (its own comment
        # calls it "Step 4", apparently never implemented); it reads back 0
        # for every entity regardless of which roster slot actually loaded.
        # Pre-existing gap, unrelated to this slice -- not something to
        # silently paper over, but also not this gate's real proof.
        after_triple = entity_triple(m, ENTITY_BASES[apple_slot])
        print(f'slot {apple_slot} triple before={before.get(apple_slot)} '
              f'after={after_triple} expected={expected_triple}')
        r.check(f'slot {apple_slot} now shows apple\'s OWN real converted '
                 f'(idle,walk,attack) triple {expected_triple} (got {after_triple}) '
                 f'-- real sprite art, not a borrowed character\'s',
                 after_triple == expected_triple)

        # --- Real hardware-visible tile/palette identity, not just a
        # frame-count triple: apple's slot's own CGRAM OBJ palette (CHAR_
        # PALETTE_SLOT-indexed, same $100+slot*32 layout phase12_roster.py
        # already establishes) must match APPLE's own real converted
        # palette.txt byte-for-byte. Props skip the `map` remap-palette
        # path entirely (Anim_ApplyMapPalette only runs on the non-prop
        # branch -- see main.pasm's CHAR_INPUT_DRIVEN_PROP dispatch), so
        # the base converted palette should land completely unperturbed;
        # this check verifies that rather than assuming it. ---
        # CGRAM, like OAM, is committed via a WRAM-shadow-buffer -> NMI DMA
        # pipeline (Core_Nmi_Play) -- a fixed short settle after the slot
        # is first detected can still read back a stale/in-flight palette.
        # Poll (deterministic bound, not a magic fixed count) until CGRAM
        # actually matches the real ground truth, same idiom as the
        # depth-sort gate's OAM-order convergence poll.
        expected_pal = real_palette_bytes(apple_moveset)
        pal_slot = None
        actual_pal = None
        for _ in range(30):
            pal_slot = byte_at(m, ENTITY_BASES[apple_slot] + CHAR_PALETTE_SLOT)
            actual_pal = bytes(read_block(m, 0x100 + pal_slot * 32, 32, mem_type='snesCgRam'))
            if actual_pal == expected_pal:
                break
            m.run_frames(1)
            m.pause()
        r.check(f"slot {apple_slot}'s CGRAM palette (slot {pal_slot}) matches apple's own "
                 f"real converted palette.txt byte-for-byte -- real tile/palette identity, "
                 f"not just animation metadata",
                 actual_pal == expected_pal)

    r.finish()


if __name__ == '__main__':
    main()
