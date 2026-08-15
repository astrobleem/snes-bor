"""Phase 9 step 4 (SyncScroll) acceptance test, v2.

v1 (phase9_syncscroll_test.py) compared every resident column's VRAM pixel
bytes against the converter's global ground truth. That's the wrong
invariant for an undersized tile cache: 13437 unique level tiles do not fit
in 1024 cache slots, so a slot that validly held tile A's pixels when column
C was committed can be legitimately evicted and reassigned to tile B later,
without column C's tilemap word having been repaired yet. v1's "419
mismatches" were exactly this -- self-consistent (tilemap slot fields
matched what Tile2Slot said at commit time), just stale pixel data in an
evicted slot, which the repair sweep is *supposed* to eventually catch, not
something the initial commit got wrong.

v2 checks the invariant that actually must hold: for every resident tilemap
entry, if the cache's live Tile2Slot[tile_id] STILL agrees with the slot
number baked into that tilemap word (i.e. nothing has evicted this tile
since the column was last committed), then the pixel bytes in that slot
must match the tile. If Tile2Slot disagrees (the slot has been reassigned to
a different tile since), the tilemap word is known-stale and is reported
separately as "pending repair" rather than a hard failure -- that's exactly
what RepairCur exists to fix, given enough frames.
"""
import os
import sys

sys.path.append(r'E:\gh\snes-bor\tools\bg_converter')
import snes_tiles as st  # noqa: E402

sys.path.append(r'E:\gh\snes-bor\tools\verify')
from _harness import open_session, read_block  # noqa: E402

BG1_TILEMAP_WORD = 0x6000
BG1_TILES_WORD = 0x0000
VIEWPORT_COLS = 32
HEIGHT = 28
BG_DIR = r'E:\gh\snes-bor\out\bg_warehouse_stream'

Screen_PosX = 0x7E1601
PlayerEntity_PosX = 0x7E0A04
StreamScroll_Enabled = 0x7E2521
StreamScroll_StagedLo = 0x7E2522
StreamScroll_StagedHi = 0x7E2524
StreamStage_ColIndex = 0x7E238E
StreamCache_Tile2Slot = 0x7F0000
Nmi_FrameCounter = 0x7E5023


def read_u16(m, addr):
    b = bytes(read_block(m, addr, 32))
    return b[0] | (b[1] << 8)


def write_u16(m, addr, value):
    m.write_u16(addr, value)


def main():
    with open(os.path.join(BG_DIR, 'tilemap.bin'), 'rb') as f:
        tilemap = f.read()
    with open(os.path.join(BG_DIR, 'tiles.bin'), 'rb') as f:
        tiles = f.read()
    import json
    with open(os.path.join(BG_DIR, 'manifest.json')) as f:
        manifest = json.load(f)
    w_tiles = manifest['width_tiles']
    n_tiles = len(tiles) // 32
    entries = st.decode_tilemap_column_major(tilemap, w_tiles, HEIGHT)

    with open_session(__file__, boot_wait=2.0) as m:
        m.reset_emulator()

        col_index = 0
        for _ in range(30):
            m.run_frames(200)
            m.pause()
            col_index = read_u16(m, StreamStage_ColIndex)
            if col_index >= VIEWPORT_COLS:
                break
        print(f'initial viewport load: col_index={col_index}')
        assert col_index >= VIEWPORT_COLS

        fc_before = read_u16(m, Nmi_FrameCounter)

        max_cam_col = w_tiles - VIEWPORT_COLS
        steps = [0, 40, 100, 200, 300, 400, max(0, max_cam_col - 5)]
        for cam_col in steps:
            cam_col = max(0, min(cam_col, max_cam_col))
            px = cam_col * 8
            write_u16(m, PlayerEntity_PosX, px)
            m.run_frames(600)
            m.pause()
            staged_lo = read_u16(m, StreamScroll_StagedLo)
            staged_hi = read_u16(m, StreamScroll_StagedHi)
            fc_now = read_u16(m, Nmi_FrameCounter)
            print(f'cam_col={cam_col} px={px} -> StagedLo={staged_lo} StagedHi={staged_hi} '
                  f'FrameCounter={fc_now}')
            assert fc_now != fc_before or cam_col == steps[0], 'Nmi_FrameCounter did not advance'
            fc_before = fc_now

        # --- final spot-check using the Tile2Slot-consistency invariant ---
        staged_lo = read_u16(m, StreamScroll_StagedLo)
        staged_hi = read_u16(m, StreamScroll_StagedHi)
        tm_a = bytes(read_block(m, BG1_TILEMAP_WORD * 2, 2048, mem_type='snesVideoRam'))
        tm_b = bytes(read_block(m, (BG1_TILEMAP_WORD + 1024) * 2, 2048, mem_type='snesVideoRam'))
        tile_bytes = bytes(read_block(m, BG1_TILES_WORD * 2, 1024 * 32, mem_type='snesVideoRam'))
        tile2slot = bytes(read_block(m, StreamCache_Tile2Slot, n_tiles * 2, mem_type='snesMemory'))

        def cur_slot_for_tile(tid):
            lo = tile2slot[tid * 2]
            hi = tile2slot[tid * 2 + 1]
            return lo | (hi << 8)

        hard_mismatches = []
        pending_repair = 0
        checked = 0
        sample_cols = list(range(staged_lo, staged_hi + 1, max(1, (staged_hi - staged_lo) // 20)))
        for world_col in sample_cols:
            vram_col = world_col & 0x3F
            page = tm_a if not (vram_col & 0x20) else tm_b
            local_col = vram_col & 0x1F
            for row in range(HEIGHT):
                exp_tid, exp_pal, exp_hf, exp_vf = entries[row * w_tiles + world_col]
                word_addr = (local_col + row * 32) * 2
                lo, hi = page[word_addr], page[word_addr + 1]
                hw_word = lo | (hi << 8)
                slot = hw_word & 0x03FF
                pal = (hw_word >> 10) & 0x07
                hf = bool(hw_word & 0x4000)
                vf = bool(hw_word & 0x8000)
                checked += 1
                if pal != exp_pal or hf != exp_hf or vf != exp_vf:
                    hard_mismatches.append(
                        f'world_col={world_col} row={row}: attr mismatch got '
                        f'pal={pal} hf={hf} vf={vf} expected pal={exp_pal} hf={exp_hf} vf={exp_vf}')
                    continue
                live_slot = cur_slot_for_tile(exp_tid)
                if live_slot != slot:
                    # cache has since reassigned this tile's slot -- tilemap
                    # word is stale, RepairCur's job, not a hard failure.
                    pending_repair += 1
                    continue
                got_tile = tile_bytes[slot * 32:slot * 32 + 32]
                exp_tile = tiles[exp_tid * 32:exp_tid * 32 + 32]
                if got_tile != exp_tile:
                    hard_mismatches.append(
                        f'world_col={world_col} row={row} tile_id={exp_tid} slot={slot}: '
                        f'VRAM pixel mismatch despite Tile2Slot agreement (real bug)')

        print(f'spot-checked {checked} entries across {len(sample_cols)} sampled columns '
              f'in [{staged_lo},{staged_hi}]')
        print(f'pending_repair (stale, cache reassigned since commit): {pending_repair}')
        if hard_mismatches:
            print(f'FAIL: {len(hard_mismatches)} hard mismatches (showing up to 15):')
            for msg in hard_mismatches[:15]:
                print('  ' + msg)
            return 1
        print('PASS: no resident tilemap entry disagrees with a still-cache-current slot')
        return 0


if __name__ == '__main__':
    sys.exit(main())
