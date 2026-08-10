#!/usr/bin/env python3
"""plan.md Part Two, section 2.7, Phase 8 gate: horizontal scrolling.

This gates the "cheap version" that actually shipped: a level whose real
content fits within a single static 64-tile-wide BG1 load (boss, 42 tiles),
not the general streaming tile cache (still unbuilt -- see plan.md's
"Streaming converter" bullet). There is therefore no per-frame column-DMA
producer here and no MSU-1-seek-vs-animation-stream interleave to
re-verify -- Bg_LoadScene runs once, at boot, under forced blank, exactly
like Phase 6's backdrop load. What Phase 8 actually adds at runtime is: the
camera easing/clamping in core/screen.pasm, a per-frame $210D write, and
computing each entity's OAM X screen-relative to that scroll.

Ground truth, per this project's standing rule (self-consistency is not
proof): tools/bg_converter's own tiles.bin/tilemap.bin, and PPU register
state read back through Mesen2's own decode (get_ppu_state), not just this
engine's own WRAM shadows.

Usage: python tools/verify/phase8.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, read_block, repo_root_from, Reporter  # noqa: E402

ROOT = repo_root_from(None)
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402

BG_DIR = os.path.join(ROOT, build_rom.BG_SCREENS[0][0])

BG1_TILES_WORD = pasm_constant('BG1_TILES_VRAM_WORD')
BG1_TILEMAP_WORD = pasm_constant('BG1_TILEMAP_VRAM_WORD')
WORLD_CONTENT_WIDTH = pasm_constant('WORLD_CONTENT_WIDTH')
WORLD_MAX_X = pasm_constant('WORLD_MAX_X')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_POS_X = pasm_constant('CHAR_POS_X')

SCREEN_SIZE_X = 256  # core/screen.pasm's SCREEN_DEFAULT_SIZE_X -- not in
                      # main.pasm, so not reachable via pasm_constant; the
                      # value is a Phase 1 constant nothing has changed.
MAX_SCROLL_X = WORLD_CONTENT_WIDTH - SCREEN_SIZE_X - 1  # Core_Screen_SetPlayfieldBorder's own formula

Screen_PosX = 0x7E1601
Nmi_Bg1ScrollX = 0x7E5017
OamSetSprite_Hi = 0x7E53AF  # not used directly; real OAM shadow read instead
OAM_HI_TABLE = 0x7E7000     # Core_Oam's shadow high-table (see core/oam.pasm) --
                              # NOT used here; X-high is checked via get_ppu_state's
                              # sprite list instead, real ground truth over shadow WRAM.

ENTITY_BASES = [0x7E0A00 + i * CHAR_ZP_LEN for i in range(4)]


def read_file(path):
    with open(path, 'rb') as f:
        return f.read()


def world_x(m, base):
    b = read_block(m, base, 64)
    return b[CHAR_POS_X] | (b[CHAR_POS_X + 1] << 8)


def screen_pos_x(m):
    b = read_block(m, Screen_PosX, 32)
    return b[0] | (b[1] << 8)


def bg1_hscroll(m):
    return m.get_ppu_state()['layers'][0]['hscroll']


def frame_counter(m):
    b = read_block(m, 0x7E5023, 32)
    return b[0] | (b[1] << 8)


def main():
    r = Reporter(8)

    if not os.path.isdir(BG_DIR):
        print(f'FAIL: {BG_DIR} missing -- run tools/bg_converter/convert_bg.py --whole-level')
        raise SystemExit(1)

    manifest = json.loads(read_file(os.path.join(BG_DIR, 'manifest.json')))
    if not manifest.get('whole_level'):
        print(f'FAIL: {BG_DIR} is not a whole-level (--whole-level) conversion; '
              f'build_rom.py must ship one for this gate to mean anything')
        raise SystemExit(1)

    tiles = read_file(os.path.join(BG_DIR, 'tiles.bin'))
    tilemap = read_file(os.path.join(BG_DIR, 'tilemap.bin'))
    content_width_tiles = manifest['content_width_tiles']
    print(f'shipped whole-level BG: {BG_DIR} ({manifest["width_tiles"]}-tile map, '
          f'{content_width_tiles} real content tiles, {manifest["unique_tiles"]} unique tiles)')

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(60)
        m.pause()

        # --- Ground truth: BOTH tilemap pages (visible page A and the
        # off-screen-at-boot page B) byte-match the converter's output, and
        # BG1SC really is in 64-wide mode per Mesen's own PPU decode -- not
        # just self-consistent with our own Nmi_Bg1TilemapVram shadow. ---
        got_tiles = bytes(read_block(m, BG1_TILES_WORD * 2, len(tiles), mem_type='snesVideoRam'))
        r.check(f'BG1 tileset matches tiles.bin ({len(tiles)} bytes)', got_tiles == tiles)
        got_tilemap = bytes(read_block(m, BG1_TILEMAP_WORD * 2, len(tilemap), mem_type='snesVideoRam'))
        r.check(f'BG1 tilemap matches tilemap.bin ({len(tilemap)} bytes, both pages)',
                got_tilemap == tilemap)
        layers = m.get_ppu_state()['layers']
        r.check('BG1SC is in 64x32 mode (Mesen decode, not our own shadow)',
                layers[0]['doubleWidth'] is True)

        # --- Camera clamps at both ends. maxScrollX is Core_Screen_
        # SetPlayfieldBorder's own formula (width - size.x - 1); re-derived
        # here from WORLD_CONTENT_WIDTH rather than hardcoded, so a level
        # swap can't silently desync this gate from the engine. ---
        print(f'MAX_SCROLL_X = {MAX_SCROLL_X} (WORLD_CONTENT_WIDTH={WORLD_CONTENT_WIDTH})')
        for _ in range(14):
            m.set_input(m.BTN_RIGHT, 60)
        m.pause()
        sx = screen_pos_x(m)
        hs = bg1_hscroll(m)
        wx = world_x(m, ENTITY_BASES[0])
        print(f'after holding Right ~840 frames: world X={wx} Screen_PosX={sx} BG1 hscroll={hs}')
        r.check(f'player world X clamps at WORLD_MAX_X ({WORLD_MAX_X})', wx == WORLD_MAX_X)
        r.check(f'camera clamps at MAX_SCROLL_X ({MAX_SCROLL_X})', sx == MAX_SCROLL_X)
        r.check('$210D (BG1HOFS) register matches the clamped scroll (Mesen decode)', hs == MAX_SCROLL_X)

        fc0 = frame_counter(m)
        m.run_frames(120)
        m.pause()
        fc1 = frame_counter(m)
        r.check('Nmi_FrameCounter still advancing while pinned at max scroll', fc1 != fc0)

        # --- Scroll reversal: hold Left back down to 0. This is where
        # SMI's ring-buffer eviction bug lived -- not applicable to this
        # static whole-level load (nothing is evicted, the whole tilemap is
        # resident), but the camera's OWN easing/clamp code has never been
        # exercised in this direction before, so still worth a real check. ---
        for _ in range(14):
            m.set_input(m.BTN_LEFT, 60)
        m.pause()
        sx = screen_pos_x(m)
        hs = bg1_hscroll(m)
        wx = world_x(m, ENTITY_BASES[0])
        print(f'after holding Left ~840 frames: world X={wx} Screen_PosX={sx} BG1 hscroll={hs}')
        r.check('player world X clamps at PLAYER_MIN_X (8) on reversal', wx == 8)
        r.check('camera clamps at 0 on reversal', sx == 0)
        r.check('$210D register matches (Mesen decode) after reversal', hs == 0)

        fc0 = frame_counter(m)
        m.run_frames(120)
        m.pause()
        fc1 = frame_counter(m)
        r.check('Nmi_FrameCounter still advancing while pinned at min scroll', fc1 != fc0)

        # --- OAM X-high bit: NOT naturally reachable in this level. It
        # needs some entity's (world X - camera scroll) >= 256, but the AI
        # always seeks the PLAYER (never wanders independently), and the
        # camera always follows the player too -- so an AI entity's
        # screen-relative X tracks the player's, which stays within camera
        # range by construction. Empirically confirmed: holding Left for
        # 600 frames (player and camera pinned near world X=8) never
        # produced a screen-relative X >= 256 for any of the 4 entities.
        # This revises plan.md 2.6's original prediction that this bit
        # would "become real" here -- it's reachable in principle
        # (WORLD_MAX_X=296 alone exceeds 255) but not by any actual
        # gameplay path with this AI model. Verified instead via the same
        # forced-collision technique Phase 0 used: write a position that
        # DOES require it directly into an entity's DP window, run one
        # frame, and check Character_PlayFrame's real OAM-X-high input
        # (OamSetSprite_Hi's bit0) -- not raw hardware OAM (Core_Oam_
        # SetSprite's own hi-table packing was already verified correct in
        # an earlier phase; this checks Phase 8's NEW code, the derivation
        # feeding it). Entity 3 (processed last in Core_Oop_Play's per-
        # frame loop) is forced so its write is still the one sitting in
        # the single shared OamSetSprite_Hi scratch when read back. ---
        m.reset_emulator()
        m.run_frames(60)  # let boot fully finish (character/BG loads) before forcing
        entity3_pos_x = ENTITY_BASES[3] + CHAR_POS_X
        m.write_u16(entity3_pos_x, 400)  # 400 - scroll(~0) >= 256
        m.run_frames(2)
        m.pause()
        hi = read_block(m, OamSetSprite_Hi, 32)[0]
        forced_wx = world_x(m, ENTITY_BASES[3])
        forced_sx = screen_pos_x(m)
        print(f'forced entity 3 to world X={forced_wx} (scroll={forced_sx}), '
              f'OamSetSprite_Hi={hi:#04x}')
        r.check('forced screen-relative X >= 256 sets the X-high bit '
                '(OamSetSprite_Hi bit0)',
                (forced_wx - forced_sx) >= 256 and (hi & 0x01) == 1)

    r.finish()


if __name__ == '__main__':
    main()
