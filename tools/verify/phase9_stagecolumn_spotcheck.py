"""Phase 9 step 3 spot-check (NOT a committed regression gate -- ad hoc,
run manually against a temporary build with BG_SCREENS pointed at
out/bg_warehouse_stream). Confirms Bg_LoadScene_Streaming's initial
32-column viewport load produced VRAM content that matches the converter's
own ground truth: for every (row, col) in the loaded viewport, decode the
expected tile_id/attribute from tilemap.bin (column-major cache format),
read the actual hardware tilemap word Bg_LoadScene_Streaming wrote, extract
its VRAM slot, and byte-compare that slot's VRAM tile pixel data against
tiles.bin[tile_id].
"""
import os
import struct
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bg_converter'))
import snes_tiles as st  # noqa: E402

sys.path.append(os.path.dirname(__file__))
from _harness import open_session, read_block, repo_root_from  # noqa: E402

BG1_TILEMAP_WORD = 0x6000
BG1_TILES_WORD = 0x0000
VIEWPORT_COLS = 32
HEIGHT = 28
BG_DIR = os.path.join(repo_root_from(__file__), 'out', 'bg_warehouse_stream')


def main():
    with open(os.path.join(BG_DIR, 'tilemap.bin'), 'rb') as f:
        tilemap = f.read()
    with open(os.path.join(BG_DIR, 'tiles.bin'), 'rb') as f:
        tiles = f.read()
    with open(os.path.join(BG_DIR, 'manifest.json')) as f:
        import json
        manifest = json.load(f)
    w_tiles = manifest['width_tiles']
    entries = st.decode_tilemap_column_major(tilemap, w_tiles, HEIGHT)

    with open_session(__file__, boot_wait=2.0) as m:
        m.reset_emulator()
        # A streaming level's initial-viewport load does up to ~900 individual
        # MSU-1 seeks (one busy-wait per cache-miss tile fetch, unlike the
        # static path's single sequential burst) -- empirically needs several
        # hundred frames of wall-clock time to finish, and a fixed frame
        # count was observed to be borderline/nondeterministic. Poll
        # StreamStage_ColIndex (a real WRAM counter, not a hook -- this
        # harness's hooks have a documented reliability gap) until it
        # reaches STREAM_STAGE_VIEWPORT_COLS (32) or a generous cap.
        for _ in range(30):
            m.run_frames(200)
            m.pause()
            col_bytes = bytes(read_block(m, 0x7E238E, 32))
            col_index = col_bytes[0] | (col_bytes[1] << 8)
            if col_index >= VIEWPORT_COLS:
                break
        else:
            print(f'WARNING: StreamStage_ColIndex only reached {col_index} after 6000 frames')

        # Read the full 32x28 tilemap viewport (page A: words $6000-$63FF).
        tm_bytes = bytes(read_block(m, BG1_TILEMAP_WORD * 2, 2048, mem_type='snesVideoRam'))
        # BG1 tiles VRAM region: 1024 slots * 32 bytes = 32768 bytes.
        tile_bytes = bytes(read_block(m, BG1_TILES_WORD * 2, 1024 * 32, mem_type='snesVideoRam'))

        mismatches = []
        checked = 0
        for row in range(HEIGHT):
            for col in range(VIEWPORT_COLS):
                exp_tid, exp_pal, exp_hf, exp_vf = entries[row * w_tiles + col]
                word_addr = (col + row * 32) * 2
                lo, hi = tm_bytes[word_addr], tm_bytes[word_addr + 1]
                hw_word = lo | (hi << 8)
                slot = hw_word & 0x03FF
                pal = (hw_word >> 10) & 0x07
                hf = bool(hw_word & 0x4000)
                vf = bool(hw_word & 0x8000)
                checked += 1
                if pal != exp_pal or hf != exp_hf or vf != exp_vf:
                    mismatches.append(f'(row={row},col={col}) attr mismatch: '
                                       f'got pal={pal} hf={hf} vf={vf}, expected pal={exp_pal} hf={exp_hf} vf={exp_vf}')
                    continue
                got_tile = tile_bytes[slot * 32:slot * 32 + 32]
                exp_tile = tiles[exp_tid * 32:exp_tid * 32 + 32]
                if got_tile != exp_tile:
                    mismatches.append(f'(row={row},col={col}) tile_id={exp_tid} slot={slot}: '
                                       f'VRAM pixel bytes do not match tiles.bin')

        print(f'checked {checked} tilemap entries across {VIEWPORT_COLS}x{HEIGHT} viewport')
        if mismatches:
            print(f'FAIL: {len(mismatches)} mismatches (showing up to 10):')
            for msg in mismatches[:10]:
                print('  ' + msg)
            return 1
        print('PASS: all viewport tiles match converter ground truth')
        return 0


if __name__ == '__main__':
    sys.exit(main())
