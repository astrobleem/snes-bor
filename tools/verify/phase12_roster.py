#!/usr/bin/env python3
"""plan.md Part Two, section 2.12, Phase 12 gate: roster expansion past 2
characters. `tools/bor_converter/convert_character.py` converted a real
third character (JOE, from the BOR pak) into `out/joe`, added to
`ROSTER_PREFIXES` in build_rom.py as roster slot 2. No engine code needed
to change for the roster count itself -- `CharSelect_RosterCount` is read
from the packed .msu file's own header byte every load (main.pasm), not a
main.pasm constant -- but `CharacterEntity_Init`'s Entity #2 now loads
roster slot 2 (JOE) instead of reusing Ralf a second time (see that
routine's own comment in main.pasm).

Checks, all against a live Mesen2 session:
1. `CharSelect_RosterCount` reads 3 (the real packed header value, not a
   hardcoded expectation -- if a future session adds/removes a roster
   entry without updating this gate, this assertion is what catches it).
2. The player's (Entity #0, `CHAR_PALETTE_SLOT` fixed at CGRAM $100)
   Select-button reselect cycles distinctly through all 3 roster slots and
   wraps back to the start: pressing Select (edge-triggered) three times
   from boot must produce four DIFFERENT CGRAM palette snapshots at
   indices [0,1,2,0] where the 4th matches the 1st (wrapped back to Ralf)
   and no two of the three distinct ones match each other. `CharSelect_
   Loaded` must stay 1 after every reselect (no failed load).
3. Entity #2's own CGRAM palette slot (CHAR_PALETTE_SLOT=2, CGRAM $140)
   matches the player's slot-2 (JOE) snapshot from check 2 -- confirms
   Entity #2 really loaded roster slot 2 at boot, not just that Select
   cycling works for the player.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, read_block, Reporter  # noqa: E402

CharSelect_Index = 0x7E53B6
CharSelect_RosterCount = 0x7E53B7
CharSelect_Loaded = 0x7E53B8

# CGRAM OBJ palette slots (byte $100 + slot*32) -- same layout phase5.py uses.
PLAYER_PALETTE_ADDR = 0x100          # CHAR_PALETTE_SLOT=0, Entity #0
ENTITY2_PALETTE_ADDR = 0x100 + 2 * 32  # CHAR_PALETTE_SLOT=2, Entity #2 (JOE)

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
Entity2_Base = 0x7E0A00 + 2 * CHAR_ZP_LEN
CHAR_PALETTE_SLOT = pasm_constant('CHAR_PALETTE_SLOT')


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
        r.check('roster count reads 3 (Ralf/JHUN/JOE)', roster_count == 3)

        palette_snapshots = []
        index_snapshots = []
        for step in range(4):
            if step > 0:
                press_select(m)
            idx = read_block(m, CharSelect_Index, 32)[0]
            loaded = read_block(m, CharSelect_Loaded, 32)[0]
            pal = bytes(read_block(m, PLAYER_PALETTE_ADDR, 32, mem_type='snesCgRam'))
            index_snapshots.append(idx)
            palette_snapshots.append(pal)
            r.check(f'CharSelect_Loaded==1 after step {step} (index={idx})', loaded == 1)

        print(f'CharSelect_Index across 4 steps (boot + 3 Select presses): {index_snapshots}')
        r.check('index sequence is [0,1,2,0] (cycles through all 3 slots, wraps)',
                 index_snapshots == [0, 1, 2, 0])

        r.check('palette at index 0 == palette at wrapped index 0 (same character reloads identically)',
                 palette_snapshots[0] == palette_snapshots[3])
        r.check('palette at index 0 != index 1 (distinct character loaded)',
                 palette_snapshots[0] != palette_snapshots[1])
        r.check('palette at index 1 != index 2 (distinct character loaded)',
                 palette_snapshots[1] != palette_snapshots[2])
        r.check('palette at index 0 != index 2 (distinct character loaded)',
                 palette_snapshots[0] != palette_snapshots[2])

        # --- Entity #2 loaded roster slot 2 (JOE) at boot -- its own CGRAM
        # slot should match the player's own slot-2 (JOE) snapshot from the
        # cycle above (same source character, two independent CGRAM
        # writes of the same colors -- same convention phase5.py already
        # established for JHUN's slot1==slot3 duplication). ---
        entity2_palette_slot = read_block(m, Entity2_Base + CHAR_PALETTE_SLOT, 32)[0]
        r.check('Entity #2 CHAR_PALETTE_SLOT == 2', entity2_palette_slot == 2)
        entity2_pal = bytes(read_block(m, ENTITY2_PALETTE_ADDR, 32, mem_type='snesCgRam'))
        r.check("Entity #2's CGRAM palette matches the player's slot-2 (JOE) snapshot",
                 entity2_pal == palette_snapshots[2])

    r.finish()


if __name__ == '__main__':
    main()
