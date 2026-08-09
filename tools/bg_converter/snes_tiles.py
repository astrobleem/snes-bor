#!/usr/bin/env python3
"""SNES BG tile encoding: dedup with flip detection, 4bpp/2bpp packing, tilemap words.

`dedup_bgr555`, `dedup_tiles`, `encode_4bpp_tile` and `encode_palette` are
adapted from `snes_room_converter.py` in the sibling SNES-SuperMonkeyIsland
project, which solved this same problem for a SCUMM adventure game. The
SCUMM-specific machinery there (z-planes, object patches, dialog-palette
carving, column-major streaming tilemaps) is deliberately not carried over --
snes-bor's backdrop is a single static screen.

IMPORTANT -- one function was NOT carried over verbatim. That project's
`encode_tilemap_word` emits a *custom WRAM* format (11-bit tile ID, palette at
bits 11-13, no priority bit) which its engine remaps when writing to VRAM.
snes-bor writes tilemap data straight to VRAM, so `encode_tilemap_word` below
emits the real SNES hardware layout instead (10-bit tile ID, palette at bits
10-12, priority at 13). Copying the other version would silently produce a
garbled tilemap.
"""
import struct

import numpy as np

TILE_SIZE = 8
BYTES_PER_4BPP_TILE = 32
BYTES_PER_2BPP_TILE = 16

# Real SNES BG tilemap entries carry a 10-bit tile index.
MAX_TILE_ID = 1024


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def rgb_to_bgr555(r, g, b):
    """8-bit RGB -> SNES BGR555 word."""
    return int(((r >> 3) & 0x1F) | (((g >> 3) & 0x1F) << 5) | (((b >> 3) & 0x1F) << 10))


def rgb_array_to_bgr555(rgb):
    """(H,W,3) uint8 RGB -> (H,W) uint16 BGR555."""
    r = (rgb[:, :, 0].astype(np.uint16) >> 3) & 0x1F
    g = (rgb[:, :, 1].astype(np.uint16) >> 3) & 0x1F
    b = (rgb[:, :, 2].astype(np.uint16) >> 3) & 0x1F
    return (r | (g << 5) | (b << 10)).astype(np.uint16)


def bgr555_to_rgb(word):
    return ((word & 0x1F) << 3, ((word >> 5) & 0x1F) << 3, ((word >> 10) & 0x1F) << 3)


def image_to_tiles(arr):
    """(H,W) array -> (n_tiles, 8, 8), row-major tile order."""
    h, w = arr.shape[:2]
    assert h % TILE_SIZE == 0 and w % TILE_SIZE == 0, f'{w}x{h} not tile-aligned'
    th, tw = h // TILE_SIZE, w // TILE_SIZE
    return (arr.reshape(th, TILE_SIZE, tw, TILE_SIZE)
               .swapaxes(1, 2)
               .reshape(th * tw, TILE_SIZE, TILE_SIZE))


# ---------------------------------------------------------------------------
# Deduplication (adapted from SNES-SuperMonkeyIsland/tools/snes_room_converter.py)
# ---------------------------------------------------------------------------

def _flip_variants(tile):
    return [
        (tile, False, False),
        (tile[:, ::-1], True, False),
        (tile[::-1, :], False, True),
        (tile[::-1, ::-1], True, True),
    ]


def dedup_bgr555(raw_tiles):
    """Collapse identical BGR555 tiles across all 4 flip variants.

    Runs BEFORE palette quantization so the quantizer sees each visual pattern
    exactly once. Skipping this lets the quantizer assign two copies of an
    identical pattern to different sub-palettes; their palette-relative index
    bytes then differ and the later `dedup_tiles` pass can no longer collapse
    them, inflating the unique-tile count against a hard VRAM budget. (This
    failure mode is recorded in the upstream project as having visibly
    corrupted several of its rooms.)

    Returns (unique_raw, position_to_unique, flip_flags).
    """
    unique = []
    lookup = {}
    position_to_unique = []
    flip_flags = []

    for i in range(len(raw_tiles)):
        tile = raw_tiles[i]
        found = False
        for var, hf, vf in _flip_variants(tile):
            key = var.tobytes()
            if key in lookup:
                position_to_unique.append(lookup[key])
                flip_flags.append((hf, vf))
                found = True
                break
        if not found:
            uid = len(unique)
            unique.append(tile.copy())
            lookup[tile.tobytes()] = uid
            position_to_unique.append(uid)
            flip_flags.append((False, False))

    unique_arr = (np.array(unique, dtype=np.uint16) if unique
                  else np.zeros((0, TILE_SIZE, TILE_SIZE), dtype=np.uint16))
    return unique_arr, position_to_unique, flip_flags


def dedup_tiles(indexed_tiles, tile_pal_ids):
    """Deduplicate indexed tiles across all 4 flip variants.

    Returns (unique_tiles, entries) where entries[i] = (tile_id, pal_id, hflip, vflip).
    """
    unique = []
    lookup = {}
    entries = []

    for i in range(len(indexed_tiles)):
        tile = indexed_tiles[i]
        pal_id = int(tile_pal_ids[i])
        found = False
        for var, hf, vf in _flip_variants(tile):
            key = var.tobytes()
            if key in lookup:
                entries.append((lookup[key], pal_id, hf, vf))
                found = True
                break
        if not found:
            tid = len(unique)
            unique.append(tile.copy())
            lookup[tile.tobytes()] = tid
            entries.append((tid, pal_id, False, False))

    return unique, entries


# ---------------------------------------------------------------------------
# Binary encoders
# ---------------------------------------------------------------------------

def encode_4bpp_tile(indexed_tile):
    """8x8 indexed pixels (0-15) -> 32-byte SNES 4bpp planar.

    Planes 0/1 interleaved in bytes 0-15, planes 2/3 in bytes 16-31.
    """
    data = bytearray(BYTES_PER_4BPP_TILE)
    for row in range(TILE_SIZE):
        bp0 = bp1 = bp2 = bp3 = 0
        for col in range(TILE_SIZE):
            idx = int(indexed_tile[row, col]) & 0x0F
            bit = 7 - col
            bp0 |= ((idx >> 0) & 1) << bit
            bp1 |= ((idx >> 1) & 1) << bit
            bp2 |= ((idx >> 2) & 1) << bit
            bp3 |= ((idx >> 3) & 1) << bit
        data[row * 2] = bp0
        data[row * 2 + 1] = bp1
        data[16 + row * 2] = bp2
        data[16 + row * 2 + 1] = bp3
    return bytes(data)


def encode_2bpp_tile(indexed_tile):
    """8x8 indexed pixels (0-3) -> 16-byte SNES 2bpp planar (BG3 in mode 1)."""
    data = bytearray(BYTES_PER_2BPP_TILE)
    for row in range(TILE_SIZE):
        bp0 = bp1 = 0
        for col in range(TILE_SIZE):
            idx = int(indexed_tile[row, col]) & 0x03
            bit = 7 - col
            bp0 |= ((idx >> 0) & 1) << bit
            bp1 |= ((idx >> 1) & 1) << bit
        data[row * 2] = bp0
        data[row * 2 + 1] = bp1
    return bytes(data)


def encode_tilemap_word(tile_id, pal_id, hflip, vflip, priority=False):
    """Real SNES BG tilemap entry: vhopppcc cccccccc.

    Bits 0-9:   tile index (10 bits)
    Bits 10-12: palette
    Bit 13:     priority
    Bit 14:     H flip
    Bit 15:     V flip
    """
    word = tile_id & 0x03FF
    word |= (pal_id & 0x07) << 10
    if priority:
        word |= 1 << 13
    if hflip:
        word |= 1 << 14
    if vflip:
        word |= 1 << 15
    return word


def encode_tileset(unique_tiles, bpp=4):
    enc = encode_4bpp_tile if bpp == 4 else encode_2bpp_tile
    return b''.join(enc(t) for t in unique_tiles)


def encode_tilemap(entries, w_tiles, h_tiles, priority=False):
    """Row-major tilemap binary, matching how the tiles were sliced."""
    data = bytearray()
    for row in range(h_tiles):
        for col in range(w_tiles):
            tid, pal, hf, vf = entries[row * w_tiles + col]
            data += struct.pack('<H', encode_tilemap_word(tid, pal, hf, vf, priority))
    return bytes(data)


def encode_palette(palettes, num_palettes=8, colors_per_palette=16):
    """Sub-palettes -> CGRAM binary (BGR555 little-endian), zero-padded."""
    data = bytearray()
    for pal in palettes:
        for color in pal:
            data += struct.pack('<H', color & 0x7FFF)
    expected = num_palettes * colors_per_palette * 2
    while len(data) < expected:
        data += b'\x00\x00'
    return bytes(data[:expected])


def decode_4bpp_tile(data):
    """Inverse of encode_4bpp_tile -- used to rebuild verification images."""
    tile = np.zeros((TILE_SIZE, TILE_SIZE), dtype=np.uint8)
    for row in range(TILE_SIZE):
        bp0, bp1 = data[row * 2], data[row * 2 + 1]
        bp2, bp3 = data[16 + row * 2], data[16 + row * 2 + 1]
        for col in range(TILE_SIZE):
            bit = 7 - col
            tile[row, col] = (((bp0 >> bit) & 1) | (((bp1 >> bit) & 1) << 1) |
                              (((bp2 >> bit) & 1) << 2) | (((bp3 >> bit) & 1) << 3))
    return tile
