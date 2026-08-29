#!/usr/bin/env python3
"""plan.md Part Two, section 2.12, Phase 12 gate: roster expansion past 2
characters. `tools/bor_converter/convert_character.py` converted a real
third character (JOE, from the BOR pak) into `out/joe`, added to
`ROSTER_PREFIXES` in build_rom.py as roster slot 2. No engine code needed
to change for the roster count itself -- `CharSelect_RosterCount` is read
from the packed .msu file's own header byte every load (main.pasm), not a
main.pasm constant -- but `CharacterEntity_Init`'s Entity #2 now loads
roster slot 2 (JOE) instead of reusing Ralf a second time (see that
routine's own comment in main.pasm). Phase 15 (plan.md 2.15) added a real
fourth roster entry (Yashiro, slot 3) the same way, and this gate was
generalized (not just re-hardcoded to 4) so a future 5th/6th/... entry
doesn't need this file touched again.

Checks, all against a live Mesen2 session:
1. `CharSelect_RosterCount` reads whatever the packed header actually says
   (read dynamically, not hardcoded -- this IS the check that a roster
   entry was added/removed without anyone noticing).
2. The player's (Entity #0, `CHAR_PALETTE_SLOT` fixed at CGRAM $100)
   Select-button reselect cycles distinctly through all `roster_count`
   slots and wraps back to the start: pressing Select (edge-triggered)
   `roster_count` times from boot must produce `roster_count`+1 CGRAM
   palette snapshots where the last matches the first (wrapped back to
   Ralf) and every pair among the first `roster_count` is distinct.
   `CharSelect_Loaded` must stay 1 after every reselect (no failed load).
3. Every non-player entity's own CGRAM palette slot matches the player's
   own snapshot at that same roster index -- confirms each entity really
   loaded its assigned roster slot at boot, not just that Select cycling
   works for the player. `ENTITY_ROSTER_SLOTS` below must be kept in sync
   with main.pasm's actual `Core_Oop_Create` init params for Entity #1/2/3
   (see main.pasm's own comment there) -- there's no way to derive this
   from the ROM automatically, same accepted-risk hand-sync pattern as
   other build-time-computed-but-hand-copied constants in this project.

**Fixed (roster-growth slice, real bug in this GATE, not the engine):**
this used to assert every pair of roster slots has a DISTINCT CGRAM
palette, as a proxy for "loading slot N really loaded slot N's own data."
That proxy broke once the roster grew to include TMNT's own FOOT01-04 --
real, separately-converted characters, but literal mechanical clones in
the source pak (same sprite, same recolor), so several of them really do
share byte-identical palettes. That is correct converted content, not a
bug. Replaced with the actually-meaningful check: each snapshot must match
that slot's OWN real converted `palette.txt` (ground truth this project
did not compute at test time), not merely differ from its neighbors --
this still catches a real "wrong slot loaded" bug (the snapshot would
match a DIFFERENT prefix's ground truth, not just "look the same as
another slot") while tolerating real duplicate content.
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, read_block, Reporter  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools', 'bor_converter'))
import build_rom  # noqa: E402 -- real ROSTER_PREFIXES, not re-typed here
from gen_pasm_animset import load_palette  # noqa: E402
from pack_msu_roster import MAX_CHARACTERS  # noqa: E402

CharSelect_Index = 0x7E53B6
CharSelect_RosterCount = 0x7E53B7
CharSelect_Loaded = 0x7E53B8


def real_palette_bytes(prefix):
    """Ground truth: this roster slot's own real converted palette, read
    straight from convert_character.py's own output -- never a value this
    test computed. Every real character has an `idle` role (see
    moveset_pipeline_generalization); its palette.txt is shared across all
    of that character's anims by construction (convert_character.py quantizes
    every animation together), so `idle` is as good as any other role here."""
    with open(os.path.join(REPO_ROOT, f'{prefix}_moveset.json'), 'r', encoding='utf-8') as f:
        moveset = json.load(f)
    idle_ordinal = moveset['roles']['idle']
    idle_dir = next(e['dir'] for e in moveset['animations'] if e['ordinal'] == idle_ordinal)
    colors = load_palette(os.path.join(REPO_ROOT, idle_dir))
    return b''.join(struct.pack('<H', c) for c in colors)

# CGRAM OBJ palette slots (byte $100 + slot*32) -- same layout phase5.py uses.
PLAYER_PALETTE_ADDR = 0x100          # CHAR_PALETTE_SLOT=0, Entity #0

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_PALETTE_SLOT = pasm_constant('CHAR_PALETTE_SLOT')

# entity index (1-3) -> (WRAM base, roster slot it loads at boot). See
# main.pasm's Entity #1/2/3 Core_Oop_Create calls -- init param low byte.
ENTITY_ROSTER_SLOTS = {
    1: (0x7E0A00 + 1 * CHAR_ZP_LEN, 1),  # JHUN
    2: (0x7E0A00 + 2 * CHAR_ZP_LEN, 2),  # JOE
    3: (0x7E0A00 + 3 * CHAR_ZP_LEN, 3),  # Yashiro
}


def press_select(m):
    # Select is edge-triggered (Input_trigger, not Input_press) -- a short
    # press is enough, matching phase8.py's own dpad set_input pattern.
    m.set_input(m.BTN_SELECT, 10)
    m.run_frames(40)
    m.pause()


def main():
    r = Reporter(12)

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        roster_count = read_block(m, CharSelect_RosterCount, 32)[0]
        print(f'CharSelect_RosterCount: {roster_count}')
        r.check(f'roster count reads a sane value (1-{MAX_CHARACTERS})',
                 1 <= roster_count <= MAX_CHARACTERS)
        # CharSelect_RosterCount is the file header's playable_count (see
        # pack_msu_roster.py's own header-byte comment) -- the player-
        # selectable subset, not the full ROSTER_PREFIXES length. Real props
        # (out/apple, appended after PLAYABLE_ROSTER_COUNT for Spawn_
        # DoRosterReassign's purposes only) are real roster members but
        # deliberately excluded from char-select's own wrap bound.
        expected_playable = getattr(build_rom, 'PLAYABLE_ROSTER_COUNT', len(build_rom.ROSTER_PREFIXES))
        r.check(f'roster count matches build_rom.py\'s real PLAYABLE_ROSTER_COUNT ({expected_playable})',
                 roster_count == expected_playable)

        palette_snapshots = []
        index_snapshots = []
        for step in range(roster_count + 1):
            if step > 0:
                press_select(m)
            idx = read_block(m, CharSelect_Index, 32)[0]
            loaded = read_block(m, CharSelect_Loaded, 32)[0]
            pal = bytes(read_block(m, PLAYER_PALETTE_ADDR, 32, mem_type='snesCgRam'))
            index_snapshots.append(idx)
            palette_snapshots.append(pal)
            r.check(f'CharSelect_Loaded==1 after step {step} (index={idx})', loaded == 1)

        print(f'CharSelect_Index across {roster_count + 1} steps '
              f'(boot + {roster_count} Select presses): {index_snapshots}')
        expected_indices = list(range(roster_count)) + [0]
        r.check(f'index sequence is {expected_indices} (cycles through all '
                 f'{roster_count} slots, wraps)',
                 index_snapshots == expected_indices)

        r.check('palette at index 0 == palette at wrapped index 0 (same character reloads identically)',
                 palette_snapshots[0] == palette_snapshots[roster_count])
        for i in range(roster_count):
            prefix = build_rom.ROSTER_PREFIXES[i]
            ground_truth = real_palette_bytes(prefix)
            r.check(f'palette at index {i} ({prefix}) matches its own real converted palette.txt',
                     palette_snapshots[i] == ground_truth)

        # --- Every non-player entity loaded its assigned roster slot at
        # boot -- its own CGRAM slot should match the player's own
        # snapshot from that same index in the cycle above (same source
        # character, two independent CGRAM writes of the same colors). ---
        for entity_num, (base, roster_slot) in ENTITY_ROSTER_SLOTS.items():
            if roster_slot >= roster_count:
                continue
            palette_addr = 0x100 + entity_num * 32  # CHAR_PALETTE_SLOT == entity_num, this project's convention
            entity_palette_slot = read_block(m, base + CHAR_PALETTE_SLOT, 32)[0]
            r.check(f'Entity #{entity_num} CHAR_PALETTE_SLOT == {entity_num}',
                     entity_palette_slot == entity_num)
            entity_pal = bytes(read_block(m, palette_addr, 32, mem_type='snesCgRam'))
            r.check(f"Entity #{entity_num}'s CGRAM palette matches the player's "
                     f"slot-{roster_slot} snapshot",
                     entity_pal == palette_snapshots[roster_slot])

    r.finish()


if __name__ == '__main__':
    main()
