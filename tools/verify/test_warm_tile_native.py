"""Execute the emitted WarmTile_Prepare instruction stream in a tiny 65816 VM.

The row decoder is a separately traced native service spy; all caller logic,
branches, LUT reads, bitplane writes, ABI save/restore and cache reuse execute
from the emitted instruction text. The pixel oracle is independent Python.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
from source_warm_tile_native import emit


CONTROL = 0x7E9400
CACHE = 0x7E8400
TILE = 0x7E9800
LUT = 0xC08000
ROW_DECODER = "WarmRle_DecodeRow"


class WarmTileVM:
    """Small width-aware interpreter for the subset emitted by this helper."""
    def __init__(self, assembly, image, lut, decoder_faults=()):
        self.lines = []
        self.labels = {}
        self.rom = {}
        self.symbols = {}
        self.image = image
        self.lut = list(lut)
        self.decoder_faults = set(decoder_faults)
        self.decoder_trace = []
        self.mem = {}
        self.stack = []
        self.a, self.x, self.y = 0xA55A, 0x1357, 0x2468
        self.dp, self.dbr, self.p = 0x3400, 0x42, 0x34
        self.c = False
        self.z = False
        self.n = False
        self.pc = 0
        self.steps = 0
        self._parse(assembly)

    def _parse(self, assembly):
        pc = 0
        for raw in assembly.splitlines():
            line = raw.split(";", 1)[0].strip()
            if not line or line in (".a16", ".i16"):
                continue
            if line.endswith(":"):
                name = line[:-1].lower()
                self.labels[name] = pc
                self.symbols[name] = 0xF00000 + pc * 2
            elif line.startswith(".dw "):
                for i, token in enumerate(line[4:].split(",")):
                    self.rom[self.symbols[next(reversed(self.labels))] + i * 2] = self._num(token)
                pc += len(line[4:].split(","))
            else:
                self.lines.append(line.lower())
                pc += 1

    @staticmethod
    def _num(token):
        token = token.strip().lower()
        return int(token[1:], 16) if token.startswith("$") else int(token, 0)

    def _addr(self, expr):
        expr = expr.strip().lower()
        indexed = expr.endswith(",x")
        if indexed:
            expr = expr[:-2]
        base = self.symbols[expr] if expr in self.symbols else self._num(expr)
        return (base + (self.x if indexed else 0)) & 0xFFFFFF

    def read16(self, address):
        address &= 0xFFFFFF
        if address in self.rom:
            return self.rom[address]
        if LUT <= address < LUT + 512:
            return self.lut[(address - LUT) // 2]
        return self.mem.get(address, 0) | (self.mem.get((address + 1) & 0xFFFFFF, 0) << 8)

    def write16(self, address, value):
        address &= 0xFFFFFF
        self.mem[address] = value & 255
        self.mem[(address + 1) & 0xFFFFFF] = (value >> 8) & 255

    def poke16(self, address, value):
        self.write16(address, value)

    def _nz(self, value):
        self.z = (value & 0xFFFF) == 0
        self.n = bool(value & 0x8000)
        return value & 0xFFFF

    def _push(self, kind, value, width=2):
        self.stack.append((kind, value & (0xFF if width == 1 else 0xFFFF), width))

    def _pop(self, kind):
        item = self.stack.pop()
        if item[0] != kind:
            raise AssertionError(("stack-kind", item, kind))
        return item[1]

    def _call_decoder(self):
        row, slot = self.a, self.x
        self.decoder_trace.append((row, slot))
        if row in self.decoder_faults or row >= len(self.image):
            self.c = True
            return
        start = CACHE + slot * 512
        for i, value in enumerate(self.image[row]):
            self.mem[start + i] = value
        self.c = False

    def run(self, max_steps=500000):
        self.pc = self.labels["warmtile_prepare"]
        start_sp = len(self.stack)
        while self.pc < len(self.lines):
            if self.steps >= max_steps:
                raise RuntimeError("VM instruction budget")
            self.steps += 1
            line = self.lines[self.pc]
            self.pc += 1
            op, _, arg = line.partition(" ")
            arg = arg.strip()
            if op in ("php",): self._push("p", self.p, 1)
            elif op == "rep": self.p &= ~self._num(arg[1:])
            elif op == "sep": self.p |= self._num(arg[1:])
            elif op == "pha": self._push("a", self.a)
            elif op == "phx": self._push("x", self.x)
            elif op == "phy": self._push("y", self.y)
            elif op == "phd": self._push("dp", self.dp)
            elif op == "phb": self._push("dbr", self.dbr, 1)
            elif op == "pla": self.a = self._nz(self._pop("a"))
            elif op == "plx": self.x = self._nz(self._pop("x"))
            elif op == "ply": self.y = self._nz(self._pop("y"))
            elif op == "pld": self.dp = self._pop("dp")
            elif op == "plb": self.dbr = self._pop("dbr")
            elif op == "plp": self.p = self._pop("p")
            elif op in ("lda", "lda.l", "ldx"):
                if arg.startswith("#"):
                    value = self._num(arg[1:])
                elif op == "lda" and arg.endswith(",x"):
                    value = self.read16(self.dp + self._num(arg[:-2]))
                else:
                    value = self.read16(self._addr(arg)) if ".l" in op else self.read16(self.dp + self._num(arg))
                if op.startswith("lda"): self.a = self._nz(value)
                else: self.x = self._nz(value)
            elif op in ("sta", "sta.l"):
                if op == "sta.l":
                    self.write16(self._addr(arg), self.a)
                elif arg.endswith(",x"):
                    self.write16(self.dp + self._num(arg[:-2]) + self.x, self.a)
                else:
                    self.write16(self.dp + self._num(arg), self.a)
            elif op in ("cmp", "cmp.l"):
                value = self._num(arg[1:]) if arg.startswith("#") else self.read16(self._addr(arg))
                self.c = self.a >= value
                self._nz(self.a - value)
            elif op in ("and", "and.l", "ora", "ora.l", "eor", "eor.l"):
                value = self._num(arg[1:]) if arg.startswith("#") else self.read16(self._addr(arg))
                baseop = op.split(".")[0]
                self.a = self._nz({"and": self.a & value, "ora": self.a | value, "eor": self.a ^ value}[baseop])
            elif op in ("adc", "adc.l", "sbc", "sbc.l"):
                value = self._num(arg[1:]) if arg.startswith("#") else self.read16(self._addr(arg))
                baseop = op.split(".")[0]
                if baseop == "adc":
                    total = self.a + value + int(self.c)
                    self.c = total > 0xFFFF
                    self.a = self._nz(total)
                else:
                    total = self.a - value - (0 if self.c else 1)
                    self.c = total >= 0
                    self.a = self._nz(total)
            elif op == "asl": self.a = self._nz(self.a << 1)
            elif op == "lsr": self.a = self._nz(self.a >> 1)
            elif op == "inc": self.a = self._nz(self.a + 1)
            elif op == "dec": self.a = self._nz(self.a - 1)
            elif op == "tax": self.x = self._nz(self.a)
            elif op == "txa": self.a = self._nz(self.x)
            elif op == "clc": self.c = False; self.p &= ~1
            elif op == "sec": self.c = True; self.p |= 1
            elif op == "jsl":
                if arg.lower() != ROW_DECODER.lower():
                    raise AssertionError(("unknown-service", arg))
                self._call_decoder()
            elif op == "jmp": self.pc = self.labels[arg]
            elif op in ("beq", "bne", "bcc", "bcs"):
                take = {"beq": self.z, "bne": not self.z, "bcc": not self.c, "bcs": self.c}[op]
                if take: self.pc = self.labels[arg]
            elif op == "rtl":
                if len(self.stack) != start_sp:
                    raise AssertionError(("unbalanced", self.stack))
                return
            else:
                raise AssertionError(("unsupported", line))
        raise RuntimeError("execution fell off code")


def reference_tile(image, lut, tile_index, left, top, width, height, direction):
    result = bytearray(96)
    screen_x0 = (tile_index & 31) * 8
    screen_y0 = (tile_index & 0x3E0) >> 2
    for row in range(8):
        source_y = screen_y0 + row - top
        mask = 0
        pairs = [0] * 5
        if not 0 <= source_y < height:
            continue
        for col in range(8):
            source_x = screen_x0 + col - left
            if not 0 <= source_x < width:
                continue
            image_x = width - 1 - source_x if direction == 0 else source_x
            source_index = image[source_y][image_x]
            if source_index == 0:
                continue
            value = lut[source_index]
            if not value:
                continue
            bit = 0x80 >> col
            mask |= bit
            for plane in range(10):
                if value & (1 << plane):
                    pairs[plane // 2] |= bit if plane % 2 == 0 else bit << 8
        base = row * 12
        result[base:base + 2] = mask.to_bytes(1, "little") * 2
        for pair, word in enumerate(pairs):
            result[base + 2 + pair * 2:base + 4 + pair * 2] = word.to_bytes(2, "little")
    return bytes(result)


class WarmTileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lut = [0] * 256
        for i in range(1, 256):
            cls.lut[i] = ((i * 3) & 0xFF) | (0x100 if i & 1 else 0) | (0x200 if i % 3 == 0 else 0)
        cls.asm = emit(LUT)

    def make_vm(self, image, tile_index, left=0, top=0, direction=1, width=None, height=None, faults=()):
        width = width or len(image[0])
        height = height or len(image)
        vm = WarmTileVM(self.asm, image, self.lut, faults)
        vm.poke16(0x3418, tile_index)
        for offset, value in ((0, left & 0xFFFF), (2, top & 0xFFFF), (4, width), (6, height),
                              (8, direction), (0x20, 0x8000), (0x22, 0x00C0),
                              (0x24, 100), (0x28, width), (0x2A, height)):
            vm.poke16(CONTROL + offset, value)
        vm.mem[CONTROL + 0x23] = 0
        vm.mem[CONTROL + 0x0C] = 0
        return vm

    def test_normal_mirror_and_clipped_source_coordinates_match_pixel_oracle(self):
        image = [[((x * 13 + y * 17) % 255) + 1 for x in range(19)] for y in range(11)]
        image[2][4] = 0
        cases = ((0, 0, 0, 1), (0, 0, 0, 0), (1, -5, -3, 1), (32, 8, 2, 0))
        for tile_index, left, top, direction in cases:
            with self.subTest(tile=tile_index, left=left, top=top, direction=direction):
                vm = self.make_vm(image, tile_index, left, top, direction)
                vm.run()
                expected = reference_tile(image, self.lut, tile_index, left, top, len(image[0]), len(image), direction)
                actual = bytes(vm.mem.get(TILE + i, 0) for i in range(96))
                self.assertEqual(actual, expected)
                self.assertFalse(vm.c)
                self.assertEqual(vm.p, 0x34)
                self.assertEqual(vm.read16(0x3408), TILE & 0xFFFF)
                self.assertEqual(vm.read16(0x340A), 0x7E)
                self.assertEqual(vm.read16(0x3448), 12)
                self.assertEqual(vm.read16(0x3446), 8)
                self.assertEqual(vm.read16(0x3456), 0)

    def test_tile_columns_reuse_decoded_source_rows(self):
        image = [[(x + y * 7) & 255 for x in range(24)] for y in range(8)]
        vm = self.make_vm(image, 0, left=0, top=0)
        vm.run()
        self.assertEqual(vm.decoder_trace, [(y, y) for y in range(8)])
        vm.poke16(0x3418, 1)
        vm.run()
        self.assertEqual(vm.decoder_trace, [(y, y) for y in range(8)])
        expected = reference_tile(image, self.lut, 1, 0, 0, 24, 8, 1)
        self.assertEqual(bytes(vm.mem.get(TILE + i, 0) for i in range(96)), expected)

    def test_new_source_row_and_image_invalidation_redo_cache(self):
        image = [[(x + y + 1) & 255 for x in range(16)] for y in range(16)]
        vm = self.make_vm(image, 0)
        vm.run()
        vm.poke16(0x3418, 32)
        vm.run()
        self.assertEqual(vm.decoder_trace, [(y, y) for y in range(8)] + [(y, y - 8) for y in range(8, 16)])
        vm.mem[CONTROL + 0x0C] = 0
        vm.poke16(0x3418, 0)
        vm.run()
        self.assertEqual(len(vm.decoder_trace), 24)

    def test_clipped_rows_are_transparent_and_not_decoded(self):
        image = [[(x + y + 1) & 255 for x in range(12)] for y in range(5)]
        vm = self.make_vm(image, 0, top=-2, left=-2)
        vm.run()
        self.assertEqual(vm.decoder_trace, [(y, y - 2) for y in range(2, 5)])
        expected = reference_tile(image, self.lut, 0, -2, -2, 12, 5, 1)
        self.assertEqual(bytes(vm.mem.get(TILE + i, 0) for i in range(96)), expected)

    def test_bottom_right_viewport_tile_895_and_height_clipping(self):
        image = [[((x + y) % 255) + 1 for x in range(256)] for y in range(220)]
        vm = self.make_vm(image, 895, width=256, height=220)
        vm.run()
        self.assertEqual(vm.decoder_trace, [(216, 0), (217, 1), (218, 2), (219, 3)])
        expected = reference_tile(image, self.lut, 895, 0, 0, 256, 220, 1)
        self.assertEqual(bytes(vm.mem.get(TILE + i, 0) for i in range(96)), expected)
        # The last four rows are outside the image and transparent.
        self.assertEqual(bytes(vm.mem.get(TILE + i, 0) for i in range(48, 96)), bytes(48))

    def test_abi_fault_paths_restore_outer_state_and_do_not_publish(self):
        image = [[1] * 8 for _ in range(8)]
        for mutate in ("decoder", "width", "tile-index", "map"):
            with self.subTest(mutate=mutate):
                vm = self.make_vm(image, 0, faults=(0,) if mutate == "decoder" else ())
                vm.p = 0x34
                vm.a, vm.x, vm.y, vm.dp, vm.dbr = 0xA55A, 0x1357, 0x2468, 0x3400, 0x42
                if mutate == "width":
                    vm.poke16(CONTROL + 4, 512)
                elif mutate == "tile-index":
                    vm.poke16(0x3418, 896)
                elif mutate == "map":
                    vm.lut[1] = 0x4001
                vm.run()
                self.assertTrue(vm.c)
                self.assertEqual((vm.a, vm.x, vm.y, vm.dp, vm.dbr), (0xA55A, 0x1357, 0x2468, 0x3400, 0x42))
                self.assertEqual(vm.p, 0x35)
                self.assertEqual(vm.stack, [])
                self.assertEqual([vm.read16(a) for a in (0x3408, 0x340A, 0x3446, 0x3448, 0x3456)], [0] * 5)

    def test_control_mapping_geometry_and_lut_domains(self):
        with self.assertRaisesRegex(ValueError, "LUT_EXTENT"):
            emit(0xFFFF00)
        with self.assertRaisesRegex(ValueError, "MEMORY_OVERLAP"):
            emit(LUT, control=0x7E8400)
        image = [[1] * 8 for _ in range(8)]
        vm = self.make_vm(image, 0)
        vm.poke16(CONTROL + 0x28, 7)
        vm.run()
        self.assertTrue(vm.c)
        invalid = (
            (0x22, 0x00BF, None),           # source bank outside C0..FF
            (0x20, 0xFF00, 0x0200),         # source extent crosses a 32K half-bank
            (8, 2, None),                   # unsupported direction
            (6, 0, None),                   # empty image
            (0x2A, 7, None),                # expected dimensions disagree
        )
        for offset, value, extent in invalid:
            with self.subTest(offset=offset, value=value, extent=extent):
                vm = self.make_vm(image, 0)
                vm.poke16(CONTROL + offset, value)
                if extent is not None:
                    vm.poke16(CONTROL + 0x24, extent)
                vm.run()
                self.assertTrue(vm.c)
                self.assertEqual(vm.decoder_trace, [])
                self.assertEqual(bytes(vm.mem.get(TILE + i, 0) for i in range(96)), bytes(96))


if __name__ == "__main__":
    unittest.main()
