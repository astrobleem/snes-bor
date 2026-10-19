"""Independent checks for packed source-index planar contribution tables."""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))

from source_warm_color_lut import (
    PACKED_BYTES,
    PAIR_COUNT,
    TABLE_BYTES,
    build_pair_tables,
    decode_source_lut,
    decode_tables_pixel,
)
from source_warm_presentation_assets import palette_extension


def planar_oracle_words(code, column):
    """Encode one source pixel in an otherwise transparent 10-plane row."""
    row = [0] * 8
    row[column] = code
    plane_bytes = []
    for plane in range(10):
        value = 0
        for pixel_column, draw_code in enumerate(row):
            if draw_code & (1 << plane):
                value |= 0x80 >> pixel_column
        plane_bytes.append(value)
    return tuple(plane_bytes[pair * 2] | (plane_bytes[pair * 2 + 1] << 8)
                 for pair in range(5))


def tables_code_from_words(words, column):
    code = 0
    pixel_bit = 0x80 >> column
    for pair, word in enumerate(words):
        if word & pixel_bit: code |= 1 << (pair * 2)
        if word & (pixel_bit << 8): code |= 1 << (pair * 2 + 1)
    return code


class WarmColorLutTests(unittest.TestCase):
    def test_every_ten_bit_code_and_column_matches_planar_row_oracle(self):
        all_codes = set()
        pending = iter(range(1, 1024))
        while True:
            codes = [0] * 256
            assigned = {}
            for source_index in range(1, 256):
                try:
                    code = next(pending)
                except StopIteration:
                    break
                codes[source_index] = code
                assigned[source_index] = code
            if not assigned:
                break

            tables = build_pair_tables(codes)
            self.assertEqual(len(tables), PAIR_COUNT)
            self.assertTrue(all(len(table) == TABLE_BYTES for table in tables))
            self.assertEqual(sum(map(len, tables)), PACKED_BYTES)
            all_codes.update(assigned.values())
            all_codes.add(0)
            for source_index, code in ((0, 0), *assigned.items()):
                for column in range(8):
                    expected_words = planar_oracle_words(code, column)
                    actual_words = tuple(
                        table[source_index * 16 + column * 2] |
                        (table[source_index * 16 + column * 2 + 1] << 8)
                        for table in tables
                    )
                    self.assertEqual(actual_words, expected_words,
                                     (source_index, code, column))
                    self.assertEqual(decode_tables_pixel(tables, source_index, column), code,
                                     (source_index, code, column))
                    self.assertEqual(tables_code_from_words(actual_words, column), code)
        self.assertEqual(all_codes, set(range(1024)))

    def test_existing_source_index_lut_and_all_rgb555_colors_round_trip(self):
        initial = [None] * 236
        source_palette = [0] * 256
        source_colors = (0x001F, 0x03E0, 0x7C00, 0x4210, 0x2529, 0x1234, 0x55AA & 0x7FFF)
        for index in range(1, 256):
            source_palette[index] = source_colors[index % len(source_colors)]
        colors, lut, changes = palette_extension(initial, source_palette, range(1, 256))
        codes = decode_source_lut(lut)
        self.assertEqual(len(lut), 512)
        self.assertEqual(codes[0], 0)
        self.assertTrue(changes)
        self.assertEqual(len(colors), 236)
        tables = build_pair_tables(lut)
        self.assertTrue(all(decode_tables_pixel(tables, 0, column) == 0 for column in range(8)))

        for index in range(1, 256):
            code = codes[index]
            palette_slot = (code & 0xFF) - 4
            reconstructed = (colors[palette_slot] + (((code >> 8) & 1) << 5) +
                             (((code >> 9) & 1) << 10))
            self.assertEqual(reconstructed, source_palette[index], index)
            for column in range(8):
                self.assertEqual(decode_tables_pixel(tables, index, column), code,
                                 (index, column))

    def test_rejects_bad_extent_codes_transparency_and_lookup_coordinates(self):
        with self.assertRaisesRegex(ValueError, "WARM_COLOR_LUT_EXTENT"):
            decode_source_lut(bytes(511))
        with self.assertRaisesRegex(ValueError, "WARM_COLOR_LUT_EXTENT"):
            build_pair_tables([0] * 255)

        too_large = bytearray(512)
        struct.pack_into("<H", too_large, 2 * 7, 1024)
        with self.assertRaisesRegex(ValueError, "WARM_COLOR_LUT_CODE"):
            build_pair_tables(too_large)
        nontransparent_zero = bytearray(512)
        struct.pack_into("<H", nontransparent_zero, 0, 1)
        with self.assertRaisesRegex(ValueError, "WARM_COLOR_LUT_TRANSPARENT"):
            build_pair_tables(nontransparent_zero)
        with self.assertRaisesRegex(ValueError, "WARM_COLOR_LUT_INDEX"):
            decode_tables_pixel(build_pair_tables(bytes(512)), 256, 0)
        with self.assertRaisesRegex(ValueError, "WARM_COLOR_LUT_COLUMN"):
            decode_tables_pixel(build_pair_tables(bytes(512)), 0, 8)
        with self.assertRaisesRegex(ValueError, "WARM_COLOR_LUT_TABLE_COUNT"):
            decode_tables_pixel((), 0, 0)
        with self.assertRaisesRegex(ValueError, "WARM_COLOR_LUT_TABLE_EXTENT"):
            decode_tables_pixel((bytes(TABLE_BYTES - 1),) + (bytes(TABLE_BYTES),) * 4, 0, 0)


if __name__ == "__main__":
    unittest.main()
