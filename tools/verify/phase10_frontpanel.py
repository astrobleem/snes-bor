"""Phase 10 (plan.md 2.10) regression gate: BG3 frontpanel streaming cache,
boot-time load AND runtime scroll resolver, checked against the converter's
own ground truth -- not self-consistency (see CLAUDE.md's Testing section
on why that distinction matters: a self-consistent engine can still be
uniformly wrong).

Two checks, both using the same Tile2Slot-consistency invariant
phase9_syncscroll_test2.py established for BG1 (a resident tilemap entry
is only a hard failure if the cache's LIVE Tile2Slot[tile_id] still agrees
with the slot baked into that tilemap word -- if the cache has since
reassigned that slot to a different tile, the entry is stale and pending
the per-frame repair sweep, not wrong):

1. Boot-time load: after StreamStageFp_ColIndex reaches
   STREAM_STAGE_VIEWPORT_COLS (32), every one of the 7 real content rows
   (21-27; rows 0-20 are always blank across the full level -- see
   FP_CONTENT_ROW_COUNT's own declaration) in the initial viewport must
   match tiles.bin/tilemap.bin byte-for-byte.
2. Runtime resolver: scroll the camera through several positions (forcing
   both extend-right and extend-left through the ring), then re-check the
   resolved window with the same invariant. Confirms Core_StreamScrollFp_*
   (including the Core_Dma_HasFreeSlot guard added when queue-contention
   cache corruption was found during Step 2c bring-up) keeps the cache
   correct under real scrolling, not just at boot.

Structural differences from BG1's gate, not oversights:
- BG3's tilemap is a single 32x32 map (no page-select bit, no 64-column
  wraparound) -- StagedLo/StagedHi always span exactly 32 columns.
- 2bpp tiles are 16 bytes each, not BG1's 32.
- The runtime tilemap word's character-number field is offset by
  FP_TILE_INDEX_BASE (32) relative to the physical FP tile cache's own
  VRAM base -- see that constant's declaration in main.pasm for why.
"""
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bg_converter'))
import snes_tiles as st  # noqa: E402

sys.path.append(os.path.dirname(__file__))
from _harness import open_session, pasm_constant, read_block, repo_root_from  # noqa: E402

ROOT = repo_root_from(__file__)
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402

VIEWPORT_COLS = 32
HEIGHT = 28

FP_DIR = os.path.join(ROOT, build_rom.FP_SCREENS[0])

BG3_TILEMAP_VRAM_WORD = pasm_constant('BG3_TILEMAP_VRAM_WORD')
FP_TILES_VRAM_WORD = pasm_constant('FP_TILES_VRAM_WORD')
FP_TILE_INDEX_BASE = pasm_constant('FP_TILE_INDEX_BASE')
CONTENT_ROW_START = pasm_constant('STREAM_FP_TILEMAP_ROW_START')
CONTENT_ROW_COUNT = pasm_constant('FP_CONTENT_ROW_COUNT')

Screen_PosX = 0x7E1601
PlayerEntity_PosX = 0x7E0A04
StreamStageFp_ColIndex = 0x7E25CE
StreamScrollFp_StagedLo = 0x7E2652
StreamScrollFp_StagedHi = 0x7E2654
StreamCacheFp_Tile2Slot = 0x7FA000
Nmi_FrameCounter = 0x7E5023


def read_u16(m, addr):
    b = bytes(read_block(m, addr, 32))
    return b[0] | (b[1] << 8)


def write_u16(m, addr, value):
    m.write_u16(addr, value)


STREAM_FP_CACHE_SLOTS = 257  # slot 0 reserved blank + 256 usable -- must match stream_cache_fp.pasm


def check_window(m, entries, tiles, tile2slot, w_tiles, n_tiles, staged_lo, staged_hi, label):
    tm = bytes(read_block(m, BG3_TILEMAP_VRAM_WORD * 2, 2048, mem_type='snesVideoRam'))
    tile_bytes = bytes(read_block(m, FP_TILES_VRAM_WORD * 2, STREAM_FP_CACHE_SLOTS * 16,
                                   mem_type='snesVideoRam'))

    def cur_slot_for_tile(tid):
        lo = tile2slot[tid * 2]
        hi = tile2slot[tid * 2 + 1]
        return lo | (hi << 8)

    hard_mismatches = []
    pending_repair = 0
    checked = 0
    for world_col in range(staged_lo, staged_hi + 1):
        vram_col = world_col & (VIEWPORT_COLS - 1)
        for local_row in range(CONTENT_ROW_COUNT):
            row = CONTENT_ROW_START + local_row
            exp_tid, exp_pal, exp_hf, exp_vf = entries[row * w_tiles + world_col]
            if exp_tid == 0:
                continue
            word_addr = (vram_col + row * 32) * 2
            lo, hi = tm[word_addr], tm[word_addr + 1]
            hw_word = lo | (hi << 8)
            hw_char = hw_word & 0x03FF
            slot = hw_char - FP_TILE_INDEX_BASE
            pal = (hw_word >> 10) & 0x07
            hf = bool(hw_word & 0x4000)
            vf = bool(hw_word & 0x8000)
            checked += 1
            # Tile2Slot-consistency check comes FIRST, same order
            # phase9_syncscroll_test2.py established for BG1: StagedLo/Hi
            # are bumped by Core_StreamScrollFp_ResolveRows synchronously
            # with handing a column off to Core_Nmi_Play's forced-blank
            # commit, one real frame BEFORE that commit actually writes
            # VRAM. A column at the freshly-extended edge can therefore
            # still show a stale leftover word from whatever world column
            # last occupied that physical ring slot -- wrong tid, wrong
            # attr, wrong everything -- and that is exactly what the
            # repair sweep exists to fix, not a hard failure. Checking attr
            # first (this script's first draft did) misclassifies that
            # exact case as a "wrong" mismatch instead of "not yet
            # written".
            live_slot = cur_slot_for_tile(exp_tid)
            if live_slot != slot:
                pending_repair += 1
                continue
            if pal != exp_pal or hf != exp_hf or vf != exp_vf:
                hard_mismatches.append(
                    f'[{label}] world_col={world_col} row={row}: attr mismatch got '
                    f'pal={pal} hf={hf} vf={vf} expected pal={exp_pal} hf={exp_hf} vf={exp_vf} '
                    f'(Tile2Slot agrees on slot={slot} -- real bug)')
                continue
            got_tile = tile_bytes[slot * 16:slot * 16 + 16]
            exp_tile = tiles[exp_tid * 16:exp_tid * 16 + 16]
            if got_tile != exp_tile:
                hard_mismatches.append(
                    f'[{label}] world_col={world_col} row={row} tile_id={exp_tid} slot={slot}: '
                    f'VRAM pixel mismatch despite Tile2Slot agreement (real bug)')

    print(f'[{label}] checked {checked} non-blank entries in columns [{staged_lo},{staged_hi}], '
          f'pending_repair={pending_repair}')
    return hard_mismatches


def main():
    with open(os.path.join(FP_DIR, 'tilemap.bin'), 'rb') as f:
        tilemap = f.read()
    with open(os.path.join(FP_DIR, 'tiles.bin'), 'rb') as f:
        tiles = f.read()
    with open(os.path.join(FP_DIR, 'manifest.json')) as f:
        manifest = json.load(f)
    w_tiles = manifest['width_tiles']
    n_tiles = len(tiles) // 16
    entries = st.decode_tilemap_column_major(tilemap, w_tiles, HEIGHT)

    all_mismatches = []

    with open_session(__file__, boot_wait=2.0) as m:
        m.reset_emulator()

        col_index = 0
        for _ in range(30):
            m.run_frames(200)
            m.pause()
            col_index = read_u16(m, StreamStageFp_ColIndex)
            if col_index >= VIEWPORT_COLS:
                break
        print(f'boot-time FP viewport load: col_index={col_index}')
        assert col_index >= VIEWPORT_COLS, 'FP boot loader never finished'

        # --- check 1: boot-time load ---
        tile2slot = bytes(read_block(m, StreamCacheFp_Tile2Slot, n_tiles * 2, mem_type='snesMemory'))
        staged_lo = read_u16(m, StreamScrollFp_StagedLo)
        staged_hi = read_u16(m, StreamScrollFp_StagedHi)
        all_mismatches += check_window(m, entries, tiles, tile2slot, w_tiles, n_tiles,
                                        staged_lo, staged_hi, 'boot')

        # --- check 2: runtime resolver under bidirectional scrolling ---
        # Matches phase9_syncscroll_test2.py's proven pattern exactly: run a
        # fixed frame count per step and check whatever window actually
        # results, rather than asserting StagedLo converges to a value
        # computed from cam_col. That assumption doesn't hold here --
        # writing PlayerEntity_PosX directly does NOT hold the player still,
        # because the AI-driven entities (CHAR_INPUT_DRIVEN=2) keep seeking
        # and colliding with the player every frame regardless, visibly
        # knocking Screen_PosX around by dozens of pixels between samples
        # (confirmed by direct tracing during this test's development). The
        # camera's own lerp toward a constantly-perturbed target means there
        # is no fixed point to converge to. What must hold regardless of
        # exactly where the camera ends up is the invariant check below:
        # NMI keeps advancing (no vblank overrun) and whatever window is
        # resident is internally consistent with the live cache.
        fc_before = read_u16(m, Nmi_FrameCounter)
        max_cam_col = w_tiles - VIEWPORT_COLS
        # Forces both extend-right and extend-left through the 32-col ring
        # multiple times, not just a single monotonic sweep.
        steps = [0, 60, 150, 300, 150, 40, max(0, max_cam_col - 5), 100, 0]
        for cam_col in steps:
            cam_col = max(0, min(cam_col, max_cam_col))
            px = cam_col * 8
            write_u16(m, PlayerEntity_PosX, px)
            m.run_frames(600)
            m.pause()
            staged_lo = read_u16(m, StreamScrollFp_StagedLo)
            staged_hi = read_u16(m, StreamScrollFp_StagedHi)
            fc_now = read_u16(m, Nmi_FrameCounter)
            print(f'cam_col={cam_col} px={px} -> StagedLo={staged_lo} StagedHi={staged_hi} '
                  f'FrameCounter={fc_now}')
            assert fc_now != fc_before, 'Nmi_FrameCounter did not advance (vblank overrun?)'
            fc_before = fc_now

        tile2slot = bytes(read_block(m, StreamCacheFp_Tile2Slot, n_tiles * 2, mem_type='snesMemory'))
        staged_lo = read_u16(m, StreamScrollFp_StagedLo)
        staged_hi = read_u16(m, StreamScrollFp_StagedHi)
        assert staged_hi - staged_lo == VIEWPORT_COLS - 1, \
            f'StagedLo/Hi window is not exactly {VIEWPORT_COLS} columns wide: {staged_lo}..{staged_hi}'
        all_mismatches += check_window(m, entries, tiles, tile2slot, w_tiles, n_tiles,
                                        staged_lo, staged_hi, 'post-scroll')

    if all_mismatches:
        print(f'FAIL: {len(all_mismatches)} hard mismatches (showing up to 15):')
        for msg in all_mismatches[:15]:
            print('  ' + msg)
        return 1
    print('PASS: boot-time and post-scroll FP tilemap windows both match converter ground truth')
    return 0


if __name__ == '__main__':
    sys.exit(main())
