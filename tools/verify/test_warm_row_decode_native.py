"""Instruction/control-flow VM tests for the emitted WFR1 native row decoder.

The test VM is intentionally small, but it executes each actual emitted
65816 instruction and branch. It is not a second Python row decoder, Poppy or
an SNES emulator. Poppy is not installed in PATH in this workspace.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import pytest
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'bor_compile'))
sys.path.insert(0, str(ROOT / 'tools' / 'verify'))

from source_warm_frame_assets import encode_image
from source_warm_row_decode_native import DEFAULT_CACHE, DEFAULT_CONTROL, emit

CODE = emit()
ROM_PTR = 0xC00000


def parse(code):
    labels, instructions = {}, []
    for raw in code.splitlines():
        line = raw.split(';', 1)[0].strip()
        if not line or line.startswith('.'):
            continue
        if line.endswith(':'):
            labels[line[:-1]] = len(instructions)
        else:
            op, _, arg = line.partition(' ')
            instructions.append((op.lower(), arg.strip()))
    return labels, instructions


class NativeVM:
    """A bounded interpreter for precisely the instruction subset emitted here."""
    def __init__(self, code, *, a, x, y=0xBEEF, d=0x3400, dbr=0x51, p=0xA0):
        self.labels, self.code = parse(code)
        self.mem = {}
        self.a, self.x, self.y, self.d, self.dbr = a, x, y, d, dbr
        self.p = p & 0xff
        self.m8 = bool(self.p & 0x20)
        self.x8 = bool(self.p & 0x10)
        self.c = bool(self.p & 1)
        self.z = bool(self.p & 2)
        self.n = bool(self.p & 0x80)
        self.v = bool(self.p & 0x40)
        self.sp = 0x1ff
        self.pc = self.labels['WarmRle_DecodeRow']
        self.steps = 0
        self.writes = []
        self.indirect_reads = []

    def get8(self, addr):
        return self.mem.get(addr & 0xffffff, 0)

    def put8(self, addr, value):
        addr &= 0xffffff
        self.mem[addr] = value & 0xff
        self.writes.append((addr, value & 0xff))

    def get16(self, addr):
        return self.get8(addr) | (self.get8(addr + 1) << 8)

    def put16(self, addr, value):
        self.put8(addr, value)
        self.put8(addr + 1, value >> 8)

    def push(self, value, width=16):
        if width == 8:
            self.put8(self.sp, value); self.sp = (self.sp - 1) & 0xffff
        else:
            self.put8(self.sp, value >> 8); self.sp = (self.sp - 1) & 0xffff
            self.put8(self.sp, value); self.sp = (self.sp - 1) & 0xffff

    def pop(self, width=16):
        if width == 8:
            self.sp = (self.sp + 1) & 0xffff
            return self.get8(self.sp)
        self.sp = (self.sp + 1) & 0xffff; lo = self.get8(self.sp)
        self.sp = (self.sp + 1) & 0xffff; hi = self.get8(self.sp)
        return lo | (hi << 8)

    def nz(self, value, width=None):
        width = width or (8 if self.m8 else 16)
        mask = (1 << width) - 1
        value &= mask
        self.z = value == 0
        self.n = bool(value & (1 << (width - 1)))
        return value

    def direct(self, token):
        return (self.d + int(token[1:], 16)) & 0xffff

    def operand(self, arg):
        arg = arg.strip()
        if arg.startswith('#'):
            return int(arg[1:].replace('$', '0x'), 0)
        if arg.startswith('['):
            match = re.fullmatch(r'\[\$([0-9A-Fa-f]{2})\],y', arg)
            assert match, arg
            pointer = self.get8(self.d + int(match.group(1), 16))
            pointer |= self.get8(self.d + int(match.group(1), 16) + 1) << 8
            pointer |= self.get8(self.d + int(match.group(1), 16) + 2) << 16
            return (pointer + self.y) & 0xffffff
        if arg.startswith('$') and len(arg) == 3:
            return self.direct(arg)
        indexed = arg.endswith(',x')
        base_token = arg[:-2] if indexed else arg
        base = int(base_token[1:], 16)
        return (base + (self.x if indexed else 0)) & 0xffffff

    def load(self, arg):
        if arg.startswith('#'):
            return int(arg[1:].replace('$', '0x'), 0)
        addr = self.operand(arg)
        if arg.startswith('['):
            self.indirect_reads.extend(range(addr, addr + (1 if self.m8 else 2)))
        return self.get8(addr) if self.m8 else self.get16(addr)

    def store(self, arg, value):
        addr = self.operand(arg)
        if self.m8: self.put8(addr, value)
        else: self.put16(addr, value)

    def step(self):
        op, arg = self.code[self.pc]
        self.pc += 1; self.steps += 1
        assert self.steps < 200_000, 'decoder VM instruction limit'
        if op in ('.a16', '.i16'):
            return
        if op == 'php': self.push(self.p, 8); return
        if op == 'pha': self.push(self.a, 8 if self.m8 else 16); return
        if op == 'phx': self.push(self.x, 8 if self.x8 else 16); return
        if op == 'phy': self.push(self.y, 8 if self.x8 else 16); return
        if op == 'phb': self.push(self.dbr, 8); return
        if op == 'phd': self.push(self.d, 16); return
        if op == 'pla': self.a = self.nz(self.pop(8 if self.m8 else 16)); return
        if op == 'plx': self.x = self.nz(self.pop(8 if self.x8 else 16), 8 if self.x8 else 16); return
        if op == 'ply': self.y = self.nz(self.pop(8 if self.x8 else 16), 8 if self.x8 else 16); return
        if op == 'plb': self.dbr = self.pop(8); return
        if op == 'pld': self.d = self.pop(16); return
        if op == 'plp':
            self.p = self.pop(8); self.m8 = bool(self.p & 0x20); self.x8 = bool(self.p & 0x10)
            self.c = bool(self.p & 1); self.z = bool(self.p & 2); self.n = bool(self.p & 0x80); self.v = bool(self.p & 0x40)
            return
        if op in ('rep', 'sep'):
            mask = int(arg[1:].replace('$', '0x'), 0)
            self.p = self.p & ~mask if op == 'rep' else self.p | mask
            self.m8 = bool(self.p & 0x20); self.x8 = bool(self.p & 0x10); return
        if op == 'tsc': self.a = self.nz(self.sp); return
        if op == 'tcs': self.sp = self.a & 0xffff; return
        if op == 'tcd': self.d = self.a & 0xffff; return
        if op == 'clc': self.c = False; return
        if op == 'sec': self.c = True; return
        if op == 'inc' and arg == 'a': self.a = self.nz(self.a + 1); return
        if op == 'asl' and arg == 'a': self.c = bool(self.a & 0x8000); self.a = self.nz(self.a << 1); return
        if op == 'iny': self.y = self.nz(self.y + 1, 16); return
        if op == 'tay': self.y = self.nz(self.a, 8 if self.x8 else 16); return
        if op == 'tax': self.x = self.nz(self.a, 8 if self.x8 else 16); return
        if op in ('lda', 'lda.l', 'ldx', 'ldy'):
            value = self.load(arg)
            if op in ('lda', 'lda.l'): self.a = self.nz(value)
            elif op == 'ldx': self.x = self.nz(value, 8 if self.x8 else 16)
            else: self.y = self.nz(value, 8 if self.x8 else 16)
            return
        if op in ('sta', 'sta.l'): self.store(arg, self.a); return
        if op == 'stx': self.store(arg, self.x); return
        if op in ('cmp', 'cpx', 'and', 'adc', 'sbc'):
            value = self.get16(self.direct(arg)) if arg.startswith('$') and len(arg) == 3 else self.operand(arg)
            width = 8 if (self.m8 if op != 'cpx' else self.x8) else 16
            mask = (1 << width) - 1
            lhs = self.x if op == 'cpx' else self.a
            value &= mask
            if op in ('cmp', 'cpx'):
                self.c = lhs >= value; self.nz(lhs - value, width)
            elif op == 'and': self.a = self.nz(self.a & value)
            elif op == 'adc':
                total = (self.a & mask) + value + int(self.c); self.c = total > mask; self.a = self.nz(total, width)
            else:
                diff = (self.a & mask) - value - int(not self.c); self.c = diff >= 0; self.a = self.nz(diff, width)
            return
        if op in ('inc', 'dec'):
            addr = self.operand(arg); value = self.get16(addr)
            self.put16(addr, self.nz(value + (1 if op == 'inc' else -1), 16)); return
        if op == 'jmp': self.pc = self.labels[arg]; return
        if op in ('bne','beq','bcc','bcs','bcs','bne','bra'):
            take = {'bne':not self.z, 'beq':self.z, 'bcc':not self.c, 'bcs':self.c, 'bra':True}[op]
            if take: self.pc = self.labels[arg]
            return
        if op == 'rtl': return
        raise AssertionError(f'unsupported emitted instruction {op} {arg}')

    def run(self):
        for _ in range(200_000):
            if self.code[self.pc][0] == 'rtl':
                self.pc += 1
                return
            self.step()
        raise AssertionError('no RTL')


def u16(memory, address, value):
    memory[address] = value & 255
    memory[address + 1] = value >> 8


def make_case(image, row, slot=3, *, ptr=ROM_PTR, extent=None,
              width=None, height=None, control_updates=None):
    vm = NativeVM(CODE, a=row, x=slot)
    blob = bytearray(image)
    declared = len(blob) if extent is None else extent
    for i, value in enumerate(blob): vm.put8(ptr + i, value)
    vm.put16(DEFAULT_CONTROL + 0x20, ptr & 0xffff)
    vm.put16(DEFAULT_CONTROL + 0x22, (ptr >> 16) & 0xff)
    vm.put16(DEFAULT_CONTROL + 0x24, declared)
    image_width = int.from_bytes(blob[4:6], 'little')
    image_height = int.from_bytes(blob[6:8], 'little')
    vm.put16(DEFAULT_CONTROL + 0x28, image_width if width is None else width)
    vm.put16(DEFAULT_CONTROL + 0x2a, image_height if height is None else height)
    if control_updates:
        for address, value in control_updates.items(): vm.put8(DEFAULT_CONTROL + address, value)
    vm.declared_source_extent = declared
    for i in range(4096): vm.put8(DEFAULT_CACHE + i, 0xa5)
    source_before = bytes(vm.get8(ptr + i) for i in range(len(blob)))
    controls_before = bytes(vm.get8(DEFAULT_CONTROL + i) for i in range(0x40))
    vm.run()
    return vm, source_before, controls_before, image_width, image_height


def source_rows(indices):
    return encode_image(indices)


def test_emitted_rows_match_exact_index_data_and_preserve_entry_context():
    # Include zero transparency, split 255-count run, alternating pixels, and
    # an irregular final run. This executes the emitted branches/instructions.
    rows = [bytes([0] * 511), bytes([7] * 255 + [0] * 256),
            bytes((i * 13 + i // 5) & 255 for i in range(511)),
            bytes([3, 3, 3, 1, 0, 4, 4, 9] + [0] * 503)]
    pixels = np.asarray([list(r) for r in rows], dtype=np.uint8)
    blob = source_rows(pixels)
    width, height = 511, 4
    for row in range(height):
        vm, source_before, controls_before, _, _ = make_case(blob, row, slot=row)
        assert not vm.c
        assert vm.a == row and vm.x == row and vm.y == 0xbeef
        assert vm.d == 0x3400 and vm.dbr == 0x51 and vm.sp == 0x1ff
        assert vm.p & 0xfe == 0xa0
        output = bytes(vm.get8(DEFAULT_CACHE + row * 512 + col) for col in range(width))
        assert output == rows[row]
        untouched = [vm.get8(DEFAULT_CACHE + row * 512 + width),
                     vm.get8(DEFAULT_CACHE + ((row + 1) % 8) * 512)]
        assert untouched == [0xa5, 0xa5]
        assert bytes(vm.get8(ROM_PTR + i) for i in range(len(source_before))) == source_before
        assert bytes(vm.get8(DEFAULT_CONTROL + i) for i in range(0x40)) == controls_before
        assert not any(0x3400 <= addr < 0x3500 for addr, _ in vm.writes)
        assert all(ROM_PTR <= addr < ROM_PTR + len(blob) for addr in vm.indirect_reads)


def test_varied_width_short_image_rows_and_all_cache_slots():
    for width, height in ((1, 1), (17, 3), (257, 2), (510, 1)):
        pixels = np.asarray([[(x * 7 + y) & 255 for x in range(width)] for y in range(height)], dtype=np.uint8)
        blob = encode_image(pixels)
        for row in range(height):
            for slot in range(8):
                vm, *_ = make_case(blob, row, slot=slot)
                assert not vm.c
                assert bytes(vm.get8(DEFAULT_CACHE + slot * 512 + x) for x in range(width)) == bytes(pixels[row])


@pytest.mark.parametrize('case', [
    'bad-magic', 'width-mismatch', 'height-mismatch', 'zero-extent',
    'wrong-extent', 'bad-pointer-high', 'nonrom-bank', 'wram-bank-7e',
    'wram-bank-7f', 'slot-crossing', 'row-outside', 'slot-outside',
    'first-offset', 'last-offset', 'row-start-outside', 'row-end-outside', 'row-reversed',
    'row-odd-extent', 'zero-run', 'run-overflow', 'row-underfill',
])
def test_malformed_inputs_fault_without_touching_source_or_caller_state(case):
    base = bytearray(encode_image(np.asarray([[4, 4, 0, 9], [2, 3, 2, 3]], dtype=np.uint8)))
    ptr = ROM_PTR; extent = len(base); row = 0; slot = 3; width = height = None; updates = {}
    payload = 10 + 2 * (2 + 1)
    if case in ('row-start-outside', 'row-end-outside', 'row-reversed'):
        base = bytearray(encode_image(np.asarray([[1] * 4, [2] * 4, [3] * 4], dtype=np.uint8)))
        row = 1
        payload = 10 + 2 * (3 + 1)
    if case == 'bad-magic': base[0] ^= 1
    elif case == 'width-mismatch': width = 5
    elif case == 'height-mismatch': height = 3
    elif case == 'zero-extent': extent = 0
    elif case == 'wrong-extent': extent -= 1
    elif case == 'bad-pointer-high': updates[0x23] = 1
    elif case == 'nonrom-bank': ptr = 0x408000
    elif case == 'wram-bank-7e': ptr = 0x7e8000
    elif case == 'wram-bank-7f': ptr = 0x7f8000
    elif case == 'slot-crossing': ptr = 0xC07ff1
    elif case == 'row-outside': row = 2
    elif case == 'slot-outside': slot = 8
    elif case == 'first-offset': base[10:12] = (1).to_bytes(2, 'little')
    elif case == 'last-offset': base[14:16] = (1).to_bytes(2, 'little')
    elif case == 'row-start-outside': base[12:14] = (7).to_bytes(2, 'little')
    elif case == 'row-end-outside': base[14:16] = (7).to_bytes(2, 'little')
    elif case == 'row-reversed': base[12:14] = (4).to_bytes(2, 'little'); base[14:16] = (2).to_bytes(2, 'little')
    elif case == 'row-odd-extent': base[12:14] = (3).to_bytes(2, 'little')
    elif case == 'zero-run': base[payload] = 0
    elif case == 'run-overflow': base[payload] = 5
    elif case == 'row-underfill': base[12:14] = (2).to_bytes(2, 'little')
    vm, source_before, controls_before, *_ = make_case(base, row, slot=slot, ptr=ptr,
                                                       extent=extent, width=width, height=height,
                                                       control_updates=updates)
    assert vm.c, case
    assert vm.a == row and vm.x == slot and vm.y == 0xbeef
    assert vm.d == 0x3400 and vm.dbr == 0x51 and vm.sp == 0x1ff
    assert vm.p & 0xfe == 0xa0
    assert bytes(vm.get8(ptr + i) for i in range(len(base))) == source_before
    assert bytes(vm.get8(DEFAULT_CONTROL + i) for i in range(0x40)) == controls_before
    assert not any(0x3400 <= addr < 0x3500 for addr, _ in vm.writes)
    if ptr == ROM_PTR and 0 <= extent <= len(base):
        assert all(ptr <= addr < ptr + extent for addr in vm.indirect_reads)


def test_emitted_routine_contract_and_evidence_hash():
    assert 'WarmRle_DecodeRow:' in CODE and 'WarmRle_Bad:' in CODE
    assert 'lda [$00],y' in CODE
    assert 'sta.l $7E8400,x' in CODE
    assert 'plp\n sec\n rtl' in CODE
    assert hashlib.sha256(CODE.encode()).hexdigest()


@pytest.mark.parametrize('p,entry_a,entry_x,entry_y', [
    (0xa0, 0, 5, 0xbeef),  # A8 mode on entry, I16; REP region is temporary
    (0xb0, 0, 3, 0x0042),  # A8/I8 mode with valid zero-extended indexes
    (0xa1, 0, 7, 0x1234),  # entry carry is replaced by routine result only
    (0xa8, 0, 1, 0x4321),  # decimal mode is cleared for internal arithmetic
    (0xb8, 0, 2, 0x4567),  # decimal plus 8-bit index mode is restored
])
def test_success_restores_all_noncarry_status_and_registers(p, entry_a, entry_x, entry_y):
    blob = encode_image(np.asarray([[0, 1, 2, 3]], dtype=np.uint8))
    vm = NativeVM(CODE, a=entry_a, x=entry_x, y=entry_y, d=0x3400, dbr=0x51, p=p)
    for i, value in enumerate(blob): vm.put8(ROM_PTR + i, value)
    vm.put16(DEFAULT_CONTROL + 0x20, ROM_PTR & 0xffff)
    vm.put16(DEFAULT_CONTROL + 0x22, (ROM_PTR >> 16) & 0xff)
    vm.put16(DEFAULT_CONTROL + 0x24, len(blob))
    vm.put16(DEFAULT_CONTROL + 0x28, 4); vm.put16(DEFAULT_CONTROL + 0x2a, 1)
    vm.run()
    assert not vm.c
    assert vm.a == entry_a and vm.x == entry_x and vm.y == entry_y
    assert vm.d == 0x3400 and vm.dbr == 0x51 and vm.sp == 0x1ff
    assert vm.p & 0xfe == p & 0xfe


@pytest.mark.parametrize('ptr', [
    0xC00000, 0xC07FF0, 0xC08000, 0xC0FFF0,
    0xFF8000, 0xFFFFF0,
])
def test_full_bank_hirom_alias_accepts_both_half_slots_without_crossing(ptr):
    # A 1x1 WFR1 image is exactly 16 bytes, so low=7ff0 and fff0 end at
    # the corresponding 32KiB half-slot boundary without crossing it.
    blob = encode_image(np.asarray([[0x5a]], dtype=np.uint8))
    assert len(blob) == 16
    vm, *_ = make_case(blob, 0, slot=6, ptr=ptr)
    assert not vm.c
    assert vm.get8(DEFAULT_CACHE + 6 * 512) == 0x5a


def test_hirom_half_slot_crossing_is_rejected():
    blob = encode_image(np.asarray([[0x5a]], dtype=np.uint8))
    vm, *_ = make_case(blob, 0, ptr=0xC07FF1)
    assert vm.c
    assert not vm.indirect_reads
