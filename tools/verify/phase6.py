#!/usr/bin/env python3
"""plan.md Part Two, section 2.4, Phase 6 gate: BG1 static backdrop + BG3 HUD.

Every VRAM/CGRAM assertion here compares against tools/bg_converter's own
emitted .bin files read off disk -- ground truth the engine did not produce.
This project's standing rule is that self-consistency is not proof: a check
that only asked "does VRAM look non-zero and plausible" would have passed
happily while Bg_LoadScene sheared every upload by one byte (which is exactly
what $2115 being unset did before it was fixed).

Usage: python tools/verify/phase6.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, read_block,  # noqa: E402
                      repo_root_from, Reporter)

ROOT = repo_root_from(None)
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402

# Ground truth is whichever BG build_rom.py actually ships -- hardcoding
# 'out/bg_boss' here used to be correct, then silently became a check
# against the WRONG level's tiles/tilemap the moment build_rom.py's
# BG_SCREENS switched to a different directory (Phase 8: out/bg_boss_level).
# Reading it from build_rom.py's own config means this gate always tracks
# whatever ROM it's actually pointed at, the same standing rule this file's
# other checks already apply to VRAM/CGRAM (compare against ground truth
# the engine did not produce, not a value baked into the test).
_bg_dir, _hud_dir = build_rom.BG_SCREENS[0]
BG_DIR = os.path.join(ROOT, _bg_dir)
HUD_DIR = os.path.join(ROOT, _hud_dir)
_fp_dir = build_rom.FP_SCREENS[0]
FP_DIR = os.path.join(ROOT, _fp_dir) if _fp_dir else None

# Engine layout, parsed from source so it cannot drift (see pasm_constant).
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
BG1_TILES_WORD = pasm_constant('BG1_TILES_VRAM_WORD')
BG1_TILEMAP_WORD = pasm_constant('BG1_TILEMAP_VRAM_WORD')
BG3_TILES_WORD = pasm_constant('BG3_TILES_VRAM_WORD')
BG3_TILEMAP_WORD = pasm_constant('BG3_TILEMAP_VRAM_WORD')
HUD_TILE_CAP_LEFT = pasm_constant('HUD_TILE_CAP_LEFT')
HUD_TILE_CAP_RIGHT = pasm_constant('HUD_TILE_CAP_RIGHT')
HUD_TILE_FILL_BASE = pasm_constant('HUD_TILE_FILL_BASE')
HUD_BAR_TILES = pasm_constant('HUD_BAR_TILES')

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]


def read_file(path):
    with open(path, 'rb') as f:
        return f.read()


def entity_hp(m, base):
    return read_block(m, base, 64)[CHAR_HP]


def main():
    r = Reporter(6)

    if not os.path.isdir(BG_DIR):
        print(f'FAIL: {BG_DIR} missing -- run tools/bg_converter/convert_bg.py')
        raise SystemExit(1)

    tiles = read_file(os.path.join(BG_DIR, 'tiles.bin'))
    tilemap = read_file(os.path.join(BG_DIR, 'tilemap.bin'))
    palette = bytearray(read_file(os.path.join(BG_DIR, 'palette.bin')))
    palette[:32] = read_file(os.path.join(HUD_DIR, 'hud_palette.bin'))
    # Phase 10 (plan.md 2.10): Bg_LoadSceneFp_Streaming also writes BG3
    # sub-palettes 1-3 (CGRAM colors 4-15, bytes 8-31) from the frontpanel's
    # own palette.bin (its first 8 bytes are a zero dummy for sub-palette 0,
    # which the HUD already owns -- see that routine's header comment).
    if FP_DIR:
        fp_palette = read_file(os.path.join(FP_DIR, 'palette.bin'))
        palette[8:32] = fp_palette[8:32]
    hud_tiles = read_file(os.path.join(HUD_DIR, 'hud_tiles.bin'))
    manifest = json.loads(read_file(os.path.join(BG_DIR, 'manifest.json')))

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        # --- BG1 tiles/tilemap: byte-exact against tiles.bin/tilemap.bin. ---
        # Only meaningful for a STATIC whole-level load, where the converter's
        # entire tileset sits resident in VRAM. A streaming level (plan.md
        # §2.8, Phase 9) never holds more than the cache's ~1022-slot subset
        # resident at once -- comparing VRAM to the full tiles.bin/tilemap.bin
        # would be comparing against the wrong invariant, not a real bug
        # surface. Ground truth for a streaming BG's correctness is
        # tools/verify/phase9_syncscroll_test2.py's Tile2Slot-consistency
        # check instead (see plan.md §2.8's gate section) -- run that
        # against whatever BG_SCREENS currently ships if you need to verify
        # streaming-mode tile/tilemap correctness.
        if manifest.get('streaming'):
            print(f'BG1 is streaming-mode ({manifest["unique_tiles"]} unique tiles level-wide) '
                  f'-- skipping whole-tileset/whole-tilemap byte-exact checks, not applicable. '
                  f'See tools/verify/phase9_syncscroll_test2.py for the real ground-truth check.')
        else:
            n = len(tiles)
            got = bytes(read_block(m, BG1_TILES_WORD * 2, n, mem_type='snesVideoRam'))
            r.check(f'BG1 tileset matches tiles.bin ({n} bytes, {manifest["unique_tiles"]} tiles)',
                    got == tiles)
            r.check('BG1 tileset is not blank (real backdrop, not the old zero fill)',
                    any(b != 0 for b in got))

            gotm = bytes(read_block(m, BG1_TILEMAP_WORD * 2, len(tilemap), mem_type='snesVideoRam'))
            r.check(f'BG1 tilemap matches tilemap.bin ({len(tilemap)} bytes) '
                    f'at word ${BG1_TILEMAP_WORD:04X}', gotm == tilemap)

        # --- BG3 HUD tileset ---
        goth = bytes(read_block(m, BG3_TILES_WORD * 2, len(hud_tiles), mem_type='snesVideoRam'))
        r.check(f'BG3 HUD tileset matches hud_tiles.bin ({len(hud_tiles)} bytes) '
                f'at word ${BG3_TILES_WORD:04X}', goth == hud_tiles)

        # --- CGRAM: backdrop palettes 1-7 plus the HUD's merged sub-palette 0 ---
        gotp = bytes(read_block(m, 0x000, 256, mem_type='snesCgRam'))
        r.check('CGRAM colors 0-127 match palette.bin + merged HUD sub-palette',
                gotp == bytes(palette))
        r.check('CGRAM sub-palette 0 (HUD) is non-zero', any(b != 0 for b in gotp[:32]))

        # --- Regression guard: the backdrop upload must not touch OBJ palettes.
        # A stray CGRAM write landing on OBJ palette 0 is exactly the bug that
        # corrupted entity 0's color 1 for several phases (TestSprite_Init), so
        # assert the character palettes are still real. ---
        obj = bytes(read_block(m, 0x100, 32, mem_type='snesCgRam'))
        r.check('OBJ palette 0 still populated (backdrop did not clobber it)',
                any(b != 0 for b in obj))
        r.check('OBJ palette 0 color 1 == $537F (ground truth from bor.msu)',
                obj[2] == 0x7F and obj[3] == 0x53)

        # --- PPU registers actually committed through the NMI shadows ---
        ppu = m.get_ppu_state()
        layers = ppu['layers']
        r.check(f'BG1 tilemap register = word ${BG1_TILEMAP_WORD:04X}',
                layers[0]['tilemapAddr'] == BG1_TILEMAP_WORD)
        r.check('BG1 char base = word $0000', layers[0]['chrAddr'] == BG1_TILES_WORD)
        r.check(f'BG3 tilemap register = word ${BG3_TILEMAP_WORD:04X}',
                layers[2]['tilemapAddr'] == BG3_TILEMAP_WORD)
        r.check(f'BG3 char base = word ${BG3_TILES_WORD:04X} (needs the new $210C shadow)',
                layers[2]['chrAddr'] == BG3_TILES_WORD)
        r.check('TM = BG1 + BG3 + OBJ ($15)', ppu['mainScreenLayers'] == 0x15)
        # Streaming mode always uses the full 64-col hardware tilemap as its
        # ring buffer, regardless of the level's logical width_tiles (that's
        # the SOFTWARE cache's column count, e.g. 192 for a 1920px level --
        # unrelated to the HARDWARE BG1SC register, which only ever has a
        # 32- or 64-wide mode to choose from).
        expect_wide = True if manifest.get('streaming') else manifest.get('width_tiles') == 64
        r.check(f'BG1SC width mode matches manifest (streaming={manifest.get("streaming", False)}, '
                f'width_tiles={manifest.get("width_tiles")})',
                layers[0]['doubleWidth'] == expect_wide)

        # --- HUD: bars drawn, and they track CHAR_HP. ---
        # Row 0 is the player's bar: blank, cap-left, 8 body tiles, cap-right.
        def hud_row0():
            row = bytes(read_block(m, BG3_TILEMAP_WORD * 2, 64, mem_type='snesVideoRam'))
            return [row[i] | (row[i + 1] << 8) for i in range(0, 64, 2)]

        words = hud_row0()
        r.check('HUD row 0 col 1 is the left cap',
                (words[1] & 0x03FF) == HUD_TILE_CAP_LEFT)
        r.check('HUD row 0 col 10 is the right cap',
                (words[10] & 0x03FF) == HUD_TILE_CAP_RIGHT)
        r.check('HUD entries carry the BG3 priority bit (bit 13)',
                all((w & 0x2000) != 0 for w in words[1:11]))
        r.check('HUD entries use CGRAM sub-palette 0',
                all(((w >> 10) & 0x07) == 0 for w in words[1:11]))

        # The eight body tiles must encode exactly the player's current HP:
        # tile id = HUD_TILE_FILL_BASE + filled, one HP per filled pixel.
        hp = entity_hp(m, ENTITY_BASES[0])
        filled = sum((words[2 + i] & 0x03FF) - HUD_TILE_FILL_BASE
                     for i in range(HUD_BAR_TILES))
        print(f'player CHAR_HP={hp}, HUD bar shows {filled} filled pixels')
        r.check('HUD bar pixel count equals player CHAR_HP', filled == hp)

        # --- HP starts full and actually depletes, clamped at 0 (never wraps). ---
        m.reset_emulator()
        m.run_frames(20)
        m.pause()
        start = [entity_hp(m, b) for b in ENTITY_BASES]
        print(f'HP at frame 20: {start}')
        r.check(f'all four entities start at CHAR_HP_MAX ({CHAR_HP_MAX})',
                all(h == CHAR_HP_MAX for h in start))

        m.run_frames(900)
        m.pause()
        later = [entity_hp(m, b) for b in ENTITY_BASES]
        print(f'HP at frame 920: {later}')
        r.check('player HP decreased from AI hits', later[0] < start[0])
        r.check('no HP underflowed past 0 (clamped, not wrapped)',
                all(0 <= h <= CHAR_HP_MAX for h in later))

        # HUD followed the change rather than staying at its boot draw.
        words = hud_row0()
        filled = sum((words[2 + i] & 0x03FF) - HUD_TILE_FILL_BASE
                     for i in range(HUD_BAR_TILES))
        print(f'player CHAR_HP={later[0]}, HUD bar shows {filled} filled pixels')
        r.check('HUD bar tracked the HP change', filled == later[0])

        # --- No vblank overrun with BG1 + BG3 + OBJ all live and the HUD
        # redrawing on every landed hit. ---
        before = read_block(m, 0x7E5023, 32)
        m.run_frames(700)
        m.pause()
        after = read_block(m, 0x7E5023, 32)
        c0 = before[0] | (before[1] << 8)
        c1 = after[0] | (after[1] << 8)
        print(f'Nmi_FrameCounter before/after 700 frames: {c0} -> {c1}')
        r.check('Nmi_FrameCounter still advancing (no vblank overrun)', c1 != c0)

    r.finish()


if __name__ == '__main__':
    main()
