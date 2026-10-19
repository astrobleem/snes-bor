"""Pack the warm source-color LUT into five SNES planar pair tables."""
from __future__ import annotations

import struct

SOURCE_INDEX_COUNT = 256
PLANES_PER_PIXEL = 10
PAIR_COUNT = PLANES_PER_PIXEL // 2
PIXEL_COLUMNS = 8
WORD_BYTES = 2
ENTRY_BYTES = PIXEL_COLUMNS * WORD_BYTES
TABLE_BYTES = SOURCE_INDEX_COUNT * ENTRY_BYTES
PACKED_BYTES = PAIR_COUNT * TABLE_BYTES


def decode_source_lut(source_lut):
    """Return 256 checked 10-bit draw codes from the existing 512-byte LUT."""
    if isinstance(source_lut, (bytes, bytearray, memoryview)):
        raw = bytes(source_lut)
        if len(raw) != SOURCE_INDEX_COUNT * WORD_BYTES:
            raise ValueError("WARM_COLOR_LUT_EXTENT")
        codes = struct.unpack("<256H", raw)
    else:
        try:
            codes = tuple(source_lut)
        except TypeError as exc:
            raise ValueError("WARM_COLOR_LUT_EXTENT") from exc
        if len(codes) != SOURCE_INDEX_COUNT:
            raise ValueError("WARM_COLOR_LUT_EXTENT")
    for index, code in enumerate(codes):
        if not isinstance(code, int) or not 0 <= code < (1 << PLANES_PER_PIXEL):
            raise ValueError("WARM_COLOR_LUT_CODE")
        if index == 0 and code != 0:
            raise ValueError("WARM_COLOR_LUT_TRANSPARENT")
    return tuple(codes)


def build_pair_tables(source_lut):
    """Build five 4096-byte tables of one-pixel contributions to plane pairs.

    Each word at ``index * 16 + column * 2`` places the even plane bit in
    the low byte and the odd plane bit in the high byte. The source index zero
    remains transparent because its required source LUT code is zero.
    """
    codes = decode_source_lut(source_lut)
    tables = [bytearray(TABLE_BYTES) for _ in range(PAIR_COUNT)]
    for source_index, code in enumerate(codes):
        base = source_index * ENTRY_BYTES
        for column in range(PIXEL_COLUMNS):
            pixel_bit = 0x80 >> column
            offset = base + column * WORD_BYTES
            for pair in range(PAIR_COUNT):
                low = pixel_bit if code & (1 << (pair * 2)) else 0
                high = pixel_bit if code & (1 << (pair * 2 + 1)) else 0
                word = low | (high << 8)
                tables[pair][offset] = word & 0xFF
                tables[pair][offset + 1] = word >> 8
    result = tuple(bytes(table) for table in tables)
    if len(result) * TABLE_BYTES != PACKED_BYTES:
        raise AssertionError("WARM_COLOR_LUT_PACKED_EXTENT")
    return result


def decode_tables_pixel(tables, source_index, column):
    """Reconstruct a pixel's 10-bit draw code by ORing its five table words."""
    if not isinstance(source_index, int) or not 0 <= source_index < SOURCE_INDEX_COUNT:
        raise ValueError("WARM_COLOR_LUT_INDEX")
    if not isinstance(column, int) or not 0 <= column < PIXEL_COLUMNS:
        raise ValueError("WARM_COLOR_LUT_COLUMN")
    if not isinstance(tables, (tuple, list)) or len(tables) != PAIR_COUNT:
        raise ValueError("WARM_COLOR_LUT_TABLE_COUNT")
    offset = source_index * ENTRY_BYTES + column * WORD_BYTES
    code = 0
    for pair, table in enumerate(tables):
        if len(table) != TABLE_BYTES:
            raise ValueError("WARM_COLOR_LUT_TABLE_EXTENT")
        word = table[offset] | (table[offset + 1] << 8)
        pixel_bit = 0x80 >> column
        if word & pixel_bit:
            code |= 1 << (pair * 2)
        if word & (pixel_bit << 8):
            code |= 1 << (pair * 2 + 1)
    return code
