#!/usr/bin/env python3
"""plan_game.md Phase G9 gate: the boss health bar (core/hud_boss.pasm's
Hud_Play__boss_bar).

See core/hud_boss.pasm's own header for the corrected premise this phase
now runs on: real OpenBOR (engine/openbor.c drawstatus()) has no boss-
exclusive AI and no boss-exclusive health bar -- `boss` only triggers
bossmusic on spawn and feeds `level->bossescount` for the win condition
(this project's own G4 win condition -- all AI dead + queue exhausted --
already covers the same ground generically, so "stage-gating" needed no
new code). The one real, buildable, previously-missing piece is a health
bar for whichever entity is flagged EntityN_IsBoss (real, sourced data
from the wait/group/boss slice), gated directly on that flag rather than
building real OpenBOR's generic "current opponent" tracking this project
has no other use for.

Like game_g9_wait_group_boss.py's own `boss` checks, this is exercised via
a hand-authored synthetic flag/HP force, NOT a real shipped level -- BOR's
own two stages have zero `boss` lines; only TMNT's pak (not converted in
this repo) uses it for real. Ground truth throughout is the BG3 tilemap
itself (decoded the same tile-id way phase5.py/game_g6_hud.py already do),
never a screenshot (mesen_screenshot_stale_hud_layer) or an engine self-
report.

Checks:
  1. No boss flagged -- HUD_ROW_BOSS reads fully blank (word 0 at every
     column), and HudBossCachedHp reads the $FF "no boss" sentinel.
  2. Entity1_IsBoss=1, HP=CHAR_HP_MAX -- the row shows a real bar: left
     cap, all 8 body tiles at max fill, right cap (same tile-id encoding
     Hud_DrawBar produces for the player's own row 0 bar).
  3. Dropping that entity's HP to a partial value redraws the bar with
     fewer filled columns (byte-exact against the same fill-per-tile
     arithmetic Hud_DrawBar's own header documents: 8 HP per body tile).
  4. Killing that entity (HP=0) hides the bar again (back to $FF/blank),
     even though EntityN_IsBoss stays sticky at 1 -- "boss with 0 HP" must
     not still show a health bar.
  5. Entity1 dead/not-boss, Entity2_IsBoss=1 with real HP -- the bar
     follows the lowest-numbered LIVING boss, not just the lowest-numbered
     IsBoss-flagged one.
  6. Both Entity1 and Entity2 flagged boss and alive -- the bar shows
     Entity1's HP (lowest-numbered wins), confirming the priority order.

Usage: python tools/verify/game_g9_boss_bar.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, Reporter  # noqa: E402

CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
CHAR_HP = 35

HUD_ROW_BOSS = pasm_constant('HUD_ROW_BOSS')
HUD_TILE_CAP_LEFT = pasm_constant('HUD_TILE_CAP_LEFT')
HUD_TILE_CAP_RIGHT = pasm_constant('HUD_TILE_CAP_RIGHT')
HUD_TILE_FILL_BASE = pasm_constant('HUD_TILE_FILL_BASE')
HUD_BAR_TILES = pasm_constant('HUD_BAR_TILES')
HUD_ENTRY_HIGH = pasm_constant('HUD_ENTRY_HIGH')
BG3_TILEMAP_WORD = pasm_constant('BG3_TILEMAP_VRAM_WORD')

HudBossCachedHp = pasm_constant('HudBossCachedHp')
Entity1_IsBoss = pasm_constant_in('src/core/spawn.pasm', 'Entity1_IsBoss')
Entity2_IsBoss = pasm_constant_in('src/core/spawn.pasm', 'Entity2_IsBoss')
Entity3_IsBoss = pasm_constant_in('src/core/spawn.pasm', 'Entity3_IsBoss')

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]
Entity1 = ENTITY_BASES[1]
Entity2 = ENTITY_BASES[2]
Entity3 = ENTITY_BASES[3]


def u8(m, addr):
    return read_block(m, addr, 32)[0]


def w8(m, addr, value):
    m.write_memory('snesMemory', addr, f'{value & 0xFF:02X}')


def row_words(m, row, count=32):
    raw = read_block(m, (BG3_TILEMAP_WORD + row * 32) * 2, max(32, count * 2),
                      mem_type='snesVideoRam')
    return [raw[i * 2] | (raw[i * 2 + 1] << 8) for i in range(count)]


def expected_bar_words(hp):
    """Same fill arithmetic as main.pasm's Hud_DrawBar: column 0 blank,
    column 1 left cap, columns 2-9 the eight body tiles (min(hp-i*8, 8)
    filled each), column 10 right cap."""
    words = [0]
    words.append(HUD_TILE_CAP_LEFT | (HUD_ENTRY_HIGH << 8))
    remaining = hp
    for _ in range(HUD_BAR_TILES):
        filled = min(remaining, 8) if remaining > 0 else 0
        remaining = max(remaining - 8, 0)
        words.append((HUD_TILE_FILL_BASE + filled) | (HUD_ENTRY_HIGH << 8))
    words.append(HUD_TILE_CAP_RIGHT | (HUD_ENTRY_HIGH << 8))
    words += [0] * (32 - len(words))
    return words


def main():
    r = Reporter('G9-BOSSBAR', kind='GATE')
    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        # --- no boss anywhere yet (real level data): row blank, sentinel set ---
        words = row_words(m, HUD_ROW_BOSS)
        cached = u8(m, HudBossCachedHp)
        print(f'no boss: row words[:3]={words[:3]} HudBossCachedHp={cached:#x}')
        r.check('boss row fully blank with no boss flagged', all(w == 0 for w in words))
        r.check('HudBossCachedHp reads the $FF "no boss" sentinel', cached == 0xFF)

        # --- Entity1 becomes the boss, full HP ---
        w8(m, Entity1_IsBoss, 1)
        w8(m, Entity1 + CHAR_HP, CHAR_HP_MAX)
        m.run_frames(10)
        m.pause()
        words = row_words(m, HUD_ROW_BOSS)
        expect = expected_bar_words(CHAR_HP_MAX)
        print(f'full-hp boss: row words={words}')
        r.check('boss row shows a full bar for Entity1 at CHAR_HP_MAX', words == expect)

        # --- partial HP redraws with fewer filled columns ---
        partial_hp = CHAR_HP_MAX // 2
        w8(m, Entity1 + CHAR_HP, partial_hp)
        m.run_frames(10)
        m.pause()
        words = row_words(m, HUD_ROW_BOSS)
        expect = expected_bar_words(partial_hp)
        print(f'partial-hp boss ({partial_hp}): row words={words}')
        r.check('boss row redraws with exactly the partial fill amount', words == expect)

        # --- HP 0: bar hides even though IsBoss stays sticky ---
        w8(m, Entity1 + CHAR_HP, 0)
        m.run_frames(10)
        m.pause()
        words = row_words(m, HUD_ROW_BOSS)
        still_boss = u8(m, Entity1_IsBoss)
        print(f'dead boss: row words[:3]={words[:3]} Entity1_IsBoss={still_boss}')
        r.check('Entity1_IsBoss stays sticky at 1 after death', still_boss == 1)
        r.check('boss row goes blank again once the boss entity is dead',
                all(w == 0 for w in words))

        # --- lowest-numbered LIVING boss wins: Entity1 dead, Entity2 alive ---
        w8(m, Entity2_IsBoss, 1)
        w8(m, Entity2 + CHAR_HP, CHAR_HP_MAX)
        m.run_frames(10)
        m.pause()
        words = row_words(m, HUD_ROW_BOSS)
        expect = expected_bar_words(CHAR_HP_MAX)
        print(f'entity2 boss (entity1 dead): row words={words}')
        r.check('bar follows Entity2 once Entity1 (also flagged) is dead', words == expect)

        # --- both Entity1 and Entity2 alive+boss: Entity1 (lower-numbered) wins ---
        entity1_hp = 24
        w8(m, Entity1 + CHAR_HP, entity1_hp)
        m.run_frames(10)
        m.pause()
        words = row_words(m, HUD_ROW_BOSS)
        expect = expected_bar_words(entity1_hp)
        print(f'both entity1+entity2 boss, both alive: row words={words}')
        r.check('bar prefers the lowest-numbered living boss (Entity1 over Entity2)',
                words == expect)

    r.finish()


if __name__ == '__main__':
    main()
