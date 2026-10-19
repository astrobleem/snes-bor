"""Instruction-level checks for the prepacked-color WarmTile path."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFY = Path(__file__).resolve().parent
sys.path.insert(0, str(VERIFY))
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))

from test_warm_tile_native import (  # the existing instruction VM and independent tile oracle
    CACHE, CONTROL, LUT, TILE, WarmTileVM, reference_tile,
)
from source_warm_tile_native import emit
from source_warm_color_lut import build_pair_tables, decode_tables_pixel


PLANES = 0xD48000


class PackedColorVM(WarmTileVM):
    def __init__(self, assembly, image, lut, tables, planes_cpu=PLANES, **kwargs):
        super().__init__(assembly, image, lut, **kwargs)
        self.tables = tables
        self.planes_cpu = planes_cpu

    def read16(self, address):
        address &= 0xFFFFFF
        for pair, table in enumerate(self.tables):
            base = self.planes_cpu + pair * len(table)
            offset = address - base
            if 0 <= offset and offset + 1 < len(table):
                return table[offset] | table[offset + 1] << 8
        return super().read16(address)


def presence_reference(image, tile_index, left, top, width, height):
    """Index-driven masks for presence-only mode; all color planes stay zero."""
    result = bytearray(96)
    sx0 = (tile_index & 31) * 8
    sy0 = (tile_index & 0x3E0) >> 2
    for row in range(8):
        sy = sy0 + row - top
        mask = 0
        if 0 <= sy < height:
            for col in range(8):
                sx = sx0 + col - left
                if 0 <= sx < width and image[sy][sx] != 0:
                    mask |= 0x80 >> col
        off = row * 12
        result[off:off + 2] = bytes((mask, mask))
    return bytes(result)


class WarmTileFastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_lut = [0] * 256
        for i in range(1, 256):
            cls.base_lut[i] = ((i * 3) & 0xFF) | ((i & 1) << 8) | ((i % 3 == 0) << 9)
        cls.tables = build_pair_tables(cls.base_lut)

    def make_vm(self, image, lut, *, mode=0, tile_index=0, left=0, top=0,
                direction=1, width=None, height=None, tile_fill=0):
        width = len(image[0]) if width is None else width
        height = len(image) if height is None else height
        asm = emit(LUT, planes_cpu=PLANES)
        vm = PackedColorVM(asm, image, lut, self.tables)
        for i in range(96):
            vm.mem[TILE + i] = tile_fill
        vm.poke16(0x3418, tile_index)
        for offset, value in ((0, left & 0xFFFF), (2, top & 0xFFFF), (4, width),
                              (6, height), (8, direction), (0x0E, mode),
                              (0x20, 0x8000), (0x22, 0x00C0), (0x24, 100),
                              (0x28, width), (0x2A, height)):
            vm.poke16(CONTROL + offset, value)
        vm.mem[CONTROL + 0x23] = 0
        vm.mem[CONTROL + 0x0C] = 0
        return vm

    def output(self, vm):
        return bytes(vm.mem.get(TILE + i, 0) for i in range(96))

    def assert_success_abi(self, vm):
        self.assertFalse(vm.c)
        self.assertEqual((vm.a, vm.x, vm.y, vm.dp, vm.dbr),
                         (0xA55A, 0x1357, 0x2468, 0x3400, 0x42))
        self.assertEqual(vm.p, 0x34)
        self.assertEqual(vm.stack, [])
        self.assertEqual((vm.read16(0x3408), vm.read16(0x340A)), (TILE & 0xFFFF, 0x7E))

    def test_normal_mirror_clipping_cache_and_tile_895_match_reference(self):
        image = [[(1 + x + y * 31) & 255 for x in range(256)] for y in range(220)]
        image[4][3] = 0
        cases = ((0, 0, 0, 1, 19, 11),
                 (1, 0, 0, 0, 19, 11),
                 (1, -5, -3, 1, 19, 11),
                 (895, 0, 0, 1, 256, 220))
        for tile, left, top, direction, width, height in cases:
            with self.subTest(tile=tile, left=left, top=top, direction=direction):
                vm = self.make_vm(image, self.base_lut, tile_index=tile, left=left,
                                  top=top, direction=direction, width=width, height=height)
                vm.run()
                expected = reference_tile(image, self.base_lut, tile, left, top,
                                          width, height, direction)
                self.assertEqual(self.output(vm), expected)
                self.assert_success_abi(vm)

    def test_adjacent_tiles_reuse_decoded_rows_on_fast_path(self):
        image = [[(x + y * 9) & 255 for x in range(32)] for y in range(8)]
        vm = self.make_vm(image, self.base_lut, tile_index=0)
        vm.run()
        first_trace = list(vm.decoder_trace)
        self.assertEqual(len(first_trace), 8)
        first = self.output(vm)
        vm.poke16(0x3418, 1)
        vm.run()
        self.assertEqual(vm.decoder_trace, first_trace)
        self.assertNotEqual(self.output(vm), first)
        self.assertEqual(self.output(vm), reference_tile(image, self.base_lut, 1, 0, 0, 32, 8, 1))

    def test_fast_path_reduces_emitted_instruction_steps_on_same_tile(self):
        image = [[((x * 13 + y * 19) % 255) + 1 for x in range(32)] for y in range(8)]

        def prepare(vm):
            vm.poke16(0x3418, 0)
            for offset, value in ((0, 0), (2, 0), (4, 32), (6, 8), (8, 1),
                                  (0x20, 0x8000), (0x22, 0x00C0), (0x24, 100),
                                  (0x28, 32), (0x2A, 8)):
                vm.poke16(CONTROL + offset, value)
            vm.mem[CONTROL + 0x23] = 0
            vm.mem[CONTROL + 0x0C] = 0
            vm.run()

        generic = WarmTileVM(emit(LUT), image, self.base_lut)
        fast = self.make_vm(image, self.base_lut)
        prepare(generic)
        prepare(fast)
        self.assertEqual(self.output(fast), self.output(generic))
        self.assertLess(fast.steps, generic.steps)
        self.assertGreater(generic.steps - fast.steps, 1000)
        # This compares VM instruction dispatch counts only; it is not a
        # native CPU-cycle or presentation-speed measurement.

    def test_prepacked_tables_cover_all_1024_codes_and_columns(self):
        # Rotate every 10-bit code through source indices 1..255. Index zero
        # remains the source's required transparent entry.
        for group in range(4):
            lut = [0] + [group * 256 + i for i in range(1, 256)]
            tables = build_pair_tables(lut)
            for index in range(1, 256):
                code = lut[index]
                for col in range(8):
                    self.assertEqual(decode_tables_pixel(tables, index, col), code)
        # Check the emitted leaf against the independent tile oracle on each
        # rotated table, including zero-code nontransparent indices.
        image = [[index for index in range(1, 9)] for _ in range(8)]
        for group in range(4):
            lut = [0] + [group * 256 + i for i in range(1, 256)]
            tables = build_pair_tables(lut)
            vm = self.make_vm(image, lut)
            vm.tables = tables
            vm.run()
            self.assertEqual(self.output(vm), reference_tile(image, lut, 0, 0, 0, 8, 8, 1))
            self.assert_success_abi(vm)

    def test_presence_only_mode_uses_indices_even_when_lut_code_is_zero(self):
        lut = [0] * 256
        lut[2] = 0
        lut[3] = 0x155
        image = [[2, 0, 3, 0, 2, 3, 0, 2] for _ in range(8)]
        vm = self.make_vm(image, lut, mode=1)
        vm.run()
        expected = presence_reference(image, 0, 0, 0, 8, 8)
        actual = self.output(vm)
        self.assertEqual(actual, expected)
        for row in range(8):
            self.assertEqual(actual[row * 12 + 2:row * 12 + 12], bytes(10))
        self.assert_success_abi(vm)

    def test_invalid_mode_faults_before_publishing_or_decoding(self):
        image = [[1] * 8 for _ in range(8)]
        original_image = tuple(tuple(row) for row in image)
        sentinel = 0xA7
        vm = self.make_vm(image, self.base_lut, mode=2, tile_fill=sentinel)
        before_cache = bytes(vm.mem.get(CACHE + i, 0) for i in range(4096))
        vm.run()
        self.assertTrue(vm.c)
        self.assertEqual(self.output(vm), bytes([sentinel]) * 96)
        self.assertEqual(bytes(vm.mem.get(CACHE + i, 0) for i in range(4096)), before_cache)
        self.assertEqual(vm.decoder_trace, [])
        self.assertEqual(tuple(tuple(row) for row in vm.image), original_image)
        self.assertEqual((vm.a, vm.x, vm.y, vm.dp, vm.dbr),
                         (0xA55A, 0x1357, 0x2468, 0x3400, 0x42))
        self.assertEqual(vm.p, 0x35)
        self.assertEqual(vm.stack, [])

    def test_bad_packed_table_base_is_rejected_by_emitter(self):
        for address in (PLANES + 1, 0xFFB001):
            with self.subTest(address=address):
                with self.assertRaises(ValueError):
                    emit(LUT, planes_cpu=address)


if __name__ == "__main__":
    unittest.main()
