#!/usr/bin/env python3
"""plan_vm.md §7, Gate 5: Q16.16 decimals.

Implements and gates: INTEGER<->Q16.16 promotion/truncation, DECIMAL-aware
ADD/SUB/MUL/DIV (INTEGER pair, DECIMAL pair, or mixed -- decimal result if
either operand is decimal, per opcode_manifest.csv), INC/DEC/NEG extended
to DECIMAL, VM truthiness extended to DECIMAL, comparisons (GE/LE/LT/GT/EQ/
NE) extended to accept a DECIMAL/INTEGER numeric pairing, and MOD/SHL/SHR/
BIT_OR/XOR/BIT_AND "integer-converting" a DECIMAL operand (opcode_manifest.
csv's own wording -- these six opcodes never produce a DECIMAL result).

Stamps numeric_profile = 0 (Q16.16) at the module header -- already
enforced by Gate 0a's own header validation (vm_load.pasm), not re-tested
here.

ADD's STR+numeric coercion (formatting a number and concatenating it) is
implemented (vm_dec16_heavy.pasm's Vm_Dec_FormatSlot, bank 1) but NOT wired
into ADD's opcode dispatch this gate -- it overflowed the $9000-$AC00 ROM
budget by ~166 bytes; see vm_dec16.pasm's own header for the measurement.
ADD(STR, INTEGER/DECIMAL) still faults VMERR_BAD_TYPE, same as Gate 4 --
not tested as a NEW behavior here, already covered by Gate 4's own
case_mixed_type_add.

MECHANISM: same direct-WRAM-injection approach as vm_gate1.py-vm_gate4.py --
see vm_gate1.py's own header for the full rationale.

ORACLE: pure-integer Python (see the q16_* helpers below) -- plan_vm.md §7's
own warning: "Do not compare Q16.16 output against unquantized binary64
expectations." Every oracle function operates on raw 32-bit two's-complement
bit patterns exactly the way the 65816 code does (abs-then-sign-reapply for
MUL/DIV, truncate-toward-zero, mod-2^32 wrap), never a Python float.

Usage: python tools/verify/vm_gate5.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant_in, read_block, repo_root_from, Reporter  # noqa: E402

ROOT = repo_root_from(__file__)
CONSTS = 'src/core/vm/vm_consts.pasm'
RUN = 'src/core/vm/vm_run.pasm'
OPCODES = 'src/core/vm/bor_vm_opcodes.pasm'

VmCode_Wram = pasm_constant_in(CONSTS, 'VmCode_Wram')
VmSlots_Wram = pasm_constant_in(CONSTS, 'VmSlots_Wram')
VM_STATE_FIRST = pasm_constant_in(CONSTS, 'VM_STATE_FIRST')
VmState_Status = pasm_constant_in(CONSTS, 'VmState_Status')
VmState_Error = pasm_constant_in(CONSTS, 'VmState_Error')
VmState_Ip = pasm_constant_in(CONSTS, 'VmState_Ip')
VmState_InstrCount = pasm_constant_in(CONSTS, 'VmState_InstrCount')
VmState_SlotCount = pasm_constant_in(CONSTS, 'VmState_SlotCount')
VmState_FrameTop = pasm_constant_in(CONSTS, 'VmState_FrameTop')

VMSTAT_DONE = pasm_constant_in(CONSTS, 'VMSTAT_DONE')
VMSTAT_FAULT = pasm_constant_in(CONSTS, 'VMSTAT_FAULT')
VMSTAT_READY = pasm_constant_in(CONSTS, 'VMSTAT_READY')
VMSTAT_YIELDED = pasm_constant_in(CONSTS, 'VMSTAT_YIELDED')
VMERR_NONE = pasm_constant_in(CONSTS, 'VMERR_NONE')
VMERR_BAD_TYPE = pasm_constant_in(CONSTS, 'VMERR_BAD_TYPE')
VMERR_DIV_ZERO = pasm_constant_in(CONSTS, 'VMERR_DIV_ZERO')
VmGuardLo = pasm_constant_in(CONSTS, 'VmGuardLo')
VmGuardHi = pasm_constant_in(CONSTS, 'VmGuardHi')
VM_GUARD_LEN = pasm_constant_in(CONSTS, 'VM_GUARD_LEN')
VM_GUARD_LO_FILL = pasm_constant_in(CONSTS, 'VM_GUARD_LO_FILL')
VM_GUARD_HI_FILL = pasm_constant_in(CONSTS, 'VM_GUARD_HI_FILL')

VmPriv_InstrOff = pasm_constant_in(RUN, 'VmPriv_InstrOff')

BOR_VT_EMPTY = pasm_constant_in(OPCODES, 'BOR_VT_EMPTY')
BOR_VT_INTEGER = pasm_constant_in(OPCODES, 'BOR_VT_INTEGER')
BOR_VT_DECIMAL = pasm_constant_in(OPCODES, 'BOR_VT_DECIMAL')
BOR_OP_ADD = pasm_constant_in(OPCODES, 'BOR_OP_ADD')
BOR_OP_SUB = pasm_constant_in(OPCODES, 'BOR_OP_SUB')
BOR_OP_MUL = pasm_constant_in(OPCODES, 'BOR_OP_MUL')
BOR_OP_DIV = pasm_constant_in(OPCODES, 'BOR_OP_DIV')
BOR_OP_MOD = pasm_constant_in(OPCODES, 'BOR_OP_MOD')
BOR_OP_SHL = pasm_constant_in(OPCODES, 'BOR_OP_SHL')
BOR_OP_SHR = pasm_constant_in(OPCODES, 'BOR_OP_SHR')
BOR_OP_BIT_OR = pasm_constant_in(OPCODES, 'BOR_OP_BIT_OR')
BOR_OP_INC = pasm_constant_in(OPCODES, 'BOR_OP_INC')
BOR_OP_DEC = pasm_constant_in(OPCODES, 'BOR_OP_DEC')
BOR_OP_NEG = pasm_constant_in(OPCODES, 'BOR_OP_NEG')
BOR_OP_NOT = pasm_constant_in(OPCODES, 'BOR_OP_NOT')
BOR_OP_GE = pasm_constant_in(OPCODES, 'BOR_OP_GE')
BOR_OP_LE = pasm_constant_in(OPCODES, 'BOR_OP_LE')
BOR_OP_LT = pasm_constant_in(OPCODES, 'BOR_OP_LT')
BOR_OP_GT = pasm_constant_in(OPCODES, 'BOR_OP_GT')
BOR_OP_EQ = pasm_constant_in(OPCODES, 'BOR_OP_EQ')
BOR_OP_NE = pasm_constant_in(OPCODES, 'BOR_OP_NE')
BOR_OP_RET = pasm_constant_in(OPCODES, 'BOR_OP_RET')

INSTR_WINDOW_OFF = 0x1000
INSTR_ADDR = VmCode_Wram + INSTR_WINDOW_OFF


# =============================================================================
# Pure-integer Q16.16 oracle -- plan_vm.md §7's own warning: never let a
# Python float into this path. Every helper operates on raw 32-bit two's-
# complement bit patterns via Python's arbitrary-precision ints, mirroring
# the 65816 code's own abs-then-sign-reapply / truncate-toward-zero /
# mod-2^32-wrap shape exactly (vm_dec16_heavy.pasm's own comments walk the
# same steps).
# =============================================================================
MASK32 = 0xFFFFFFFF


def s32(v):
    v &= MASK32
    return v - 0x100000000 if v & 0x80000000 else v


def u32(v):
    return v & MASK32


def neg32(v):
    return u32(-s32(v))


def promote(raw_int):
    """INTEGER raw -> Q16.16 raw: newHi=oldLo, newLo=0 (vm_consts.pasm's
    documented promotion rule -- exact only for -32768..32767, wraps
    otherwise, same as everywhere else in this VM)."""
    lo = raw_int & 0xFFFF
    return u32(lo << 16)


def q16(intpart, frac_num, frac_den=10000):
    """Build a Q16.16 raw value from a decimal literal given as
    intpart + frac_num/frac_den (both nonnegative), with `sign` applied to
    the whole value -- avoids ever constructing a Python float."""
    frac_raw = (abs(frac_num) * 65536) // frac_den
    mag = u32((abs(intpart) << 16) + frac_raw)
    return neg32(mag) if intpart < 0 or frac_num < 0 else mag


def q16_add(a, b):
    return u32(s32(a) + s32(b))


def q16_sub(a, b):
    return u32(s32(a) - s32(b))


def q16_mul(a, b):
    a, b = s32(a), s32(b)
    sign_a, sign_b = a < 0, b < 0
    mag_a, mag_b = (u32(-a) if sign_a else u32(a)), (u32(-b) if sign_b else u32(b))
    mag = u32((mag_a * mag_b) >> 16)
    return neg32(mag) if sign_a != sign_b else mag


def q16_div(a, b):
    """Returns None for divisor==0 (EMPTY, historical behavior)."""
    if b == 0:
        return None
    a, b = s32(a), s32(b)
    sign_a, sign_b = a < 0, b < 0
    mag_a, mag_b = (u32(-a) if sign_a else u32(a)), (u32(-b) if sign_b else u32(b))
    q = u32((mag_a << 16) // mag_b)
    return neg32(q) if sign_a != sign_b else q


def q16_to_int(raw):
    """Truncate-toward-zero DECIMAL->INTEGER (MOD/SHL/SHR/BIT_*'s
    'integer-convert' rule)."""
    hi = (raw >> 16) & 0xFFFF
    lo = raw & 0xFFFF
    hi_s = hi - 0x10000 if hi & 0x8000 else hi
    if hi_s < 0 and lo != 0:
        hi_s += 1
    return u32(hi_s)


def q16_inc(raw):
    return u32(raw + 0x10000)


def q16_dec(raw):
    return u32(raw - 0x10000)


def q16_neg(raw):
    return neg32(raw)


def q16_truthy(raw):
    return 0 if raw == 0 else 1


# =============================================================================
# Slot / instruction encoding -- same shapes as vm_gate2.py-vm_gate4.py.
# =============================================================================
def rec(op, a=0, b=0, c=0, flags=0):
    return struct.pack('<BBHHH', op & 0xFF, flags & 0xFF, a & 0xFFFF, b & 0xFFFF, c & 0xFFFF)


def int_slot(value):
    return struct.pack('<BBHi', BOR_VT_INTEGER, 0, 0, value)


def dec_slot(raw):
    return struct.pack('<BBHI', BOR_VT_DECIMAL, 0, 0, raw & MASK32)


def empty_slot():
    return struct.pack('<BBHi', BOR_VT_EMPTY, 0, 0, 0)


def pad(data, size):
    assert len(data) <= size, f'{len(data)} bytes does not fit a {size}-byte window'
    return data + b'\x00' * (size - len(data))


class Case:
    def __init__(self, instrs, slots, entry_ip=0):
        self.instrs = instrs
        self.slots = slots
        self.entry_ip = entry_ip
        self.instr_count = len(instrs) // 8


def run_case(m, case, clear_slots_up_to=32):
    m.write_memory('snesMemory', INSTR_ADDR, pad(case.instrs, 1024).hex())
    m.write_memory('snesMemory', VmSlots_Wram,
                    pad(case.slots, max(len(case.slots), clear_slots_up_to * 8)).hex())

    m.write_u16(VmState_Ip, case.entry_ip)
    m.write_u16(VmState_Error, 0)
    m.write_u16(VmState_InstrCount, case.instr_count)
    m.write_u16(VmState_SlotCount, max(len(case.slots) // 8, clear_slots_up_to))
    m.write_u16(VmState_FrameTop, 0)
    m.write_u8(VmState_Status, VMSTAT_READY)

    def field(state, addr, width):
        off = addr - VM_STATE_FIRST
        if width == 1:
            return state[off]
        return state[off] | (state[off + 1] << 8)

    status_byte = VMSTAT_READY
    state = None
    for _ in range(60):
        m.run_frames(2)
        m.pause()
        state = read_block(m, VM_STATE_FIRST, 32)
        status_byte = field(state, VmState_Status, 1)
        if status_byte >= VMSTAT_YIELDED:
            break
    else:
        return None

    error = field(state, VmState_Error, 2)
    return {'status': status_byte, 'error': error}


def read_slot(m, index):
    data = read_block(m, VmSlots_Wram + index * 8, 32)[:8]
    vtype, flags, aux, value = struct.unpack('<BBHI', data)
    return vtype, flags, aux, value


def guard_intact(m):
    lo = read_block(m, VmGuardLo, 32)[:VM_GUARD_LEN]
    hi = read_block(m, VmGuardHi, 32)[:VM_GUARD_LEN]
    return (lo == bytes([VM_GUARD_LO_FILL]) * VM_GUARD_LEN
            and hi == bytes([VM_GUARD_HI_FILL]) * VM_GUARD_LEN)


# =============================================================================
# Case builders -- one binary op, a=2 (dest), b=0, c=1.
# =============================================================================
def case_binary(op, slot_b, slot_c):
    instrs = rec(op, a=2, b=0, c=1) + rec(BOR_OP_RET)
    slots = bytearray(empty_slot() * 3)
    slots[0 * 8:0 * 8 + 8] = slot_b
    slots[1 * 8:1 * 8 + 8] = slot_c
    return Case(instrs, bytes(slots))


def case_unary(op, slot_a):
    instrs = rec(op, a=0) + rec(BOR_OP_RET)
    slots = bytearray(empty_slot() * 1)
    slots[0 * 8:0 * 8 + 8] = slot_a
    return Case(instrs, bytes(slots))


def main():
    r = Reporter('5', kind='GATE')

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        boot_status = read_block(m, VM_STATE_FIRST, 32)[VmState_Status - VM_STATE_FIRST]
        r.check(f'boot (shipped Gate 0 module) reached a terminal status '
                 f'before injection began (status={boot_status})',
                 boot_status in (VMSTAT_DONE, VMSTAT_FAULT))

        m.write_u16(VmPriv_InstrOff, INSTR_WINDOW_OFF)

        HALF = q16(0, 5000)          # 0.5
        NEG_HALF = q16(-0, -5000)    # -0.5 (intpart 0 can't carry sign -> pass via frac_num)
        THREE = q16(3, 0)            # 3.0
        NEG_TWO_QUARTER = q16(-2, -2500)   # -2.25
        TWO = q16(2, 0)

        # --- ADD: DECIMAL pair, and mixed INTEGER/DECIMAL (promotion) ---
        out = run_case(m, case_binary(BOR_OP_ADD, dec_slot(THREE), dec_slot(HALF)))
        _t, _f, _a, v = read_slot(m, 2)
        expect = q16_add(THREE, HALF)
        r.check(f'ADD(3.0 DEC, 0.5 DEC) -> DECIMAL {expect:#010x} (3.5)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_DECIMAL and v == expect)

        out = run_case(m, case_binary(BOR_OP_ADD, int_slot(3), dec_slot(HALF)))
        _t, _f, _a, v = read_slot(m, 2)
        expect = q16_add(promote(3), HALF)
        r.check('ADD(3 INTEGER, 0.5 DECIMAL) -> DECIMAL 3.5 (INTEGER operand promoted)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_DECIMAL and v == expect)

        out = run_case(m, case_binary(BOR_OP_ADD, dec_slot(HALF), int_slot(3)))
        _t, _f, _a, v = read_slot(m, 2)
        r.check('ADD(0.5 DECIMAL, 3 INTEGER) -> DECIMAL 3.5 (operand order reversed)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_DECIMAL and v == expect)

        out = run_case(m, case_binary(BOR_OP_ADD, int_slot(3), int_slot(4)))
        _t, _f, _a, v = read_slot(m, 2)
        r.check('ADD(3 INTEGER, 4 INTEGER) -> INTEGER 7 (pure-INTEGER path unaffected)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_INTEGER and v == 7)

        # --- SUB ---
        out = run_case(m, case_binary(BOR_OP_SUB, dec_slot(THREE), dec_slot(HALF)))
        _t, _f, _a, v = read_slot(m, 2)
        expect = q16_sub(THREE, HALF)
        r.check('SUB(3.0 DEC, 0.5 DEC) -> DECIMAL 2.5',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_DECIMAL and v == expect)

        # --- MUL: DECIMAL pair (0.5 * -2.25 = -1.125), and overflow wrap ---
        out = run_case(m, case_binary(BOR_OP_MUL, dec_slot(HALF), dec_slot(NEG_TWO_QUARTER)))
        _t, _f, _a, v = read_slot(m, 2)
        expect = q16_mul(HALF, NEG_TWO_QUARTER)
        r.check(f'MUL(0.5 DEC, -2.25 DEC) -> DECIMAL {expect:#010x} (-1.125)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_DECIMAL and v == expect)

        big_a = q16(1000, 0)
        big_b = q16(1000, 0)
        out = run_case(m, case_binary(BOR_OP_MUL, dec_slot(big_a), dec_slot(big_b)))
        _t, _f, _a, v = read_slot(m, 2)
        expect = q16_mul(big_a, big_b)   # 1,000,000.0 overflows 16-bit int part -> wraps
        r.check(f'MUL(1000.0 DEC, 1000.0 DEC) -> DECIMAL {expect:#010x} (mod-2^32 wrap, documented)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_DECIMAL and v == expect)

        out = run_case(m, case_binary(BOR_OP_MUL, int_slot(6), int_slot(7)))
        _t, _f, _a, v = read_slot(m, 2)
        r.check('MUL(6 INTEGER, 7 INTEGER) -> INTEGER 42 (pure-INTEGER path unaffected)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_INTEGER and v == 42)

        # --- DIV: DECIMAL pair, and divisor-zero -> EMPTY (still, regardless of type) ---
        out = run_case(m, case_binary(BOR_OP_DIV, dec_slot(THREE), dec_slot(TWO)))
        _t, _f, _a, v = read_slot(m, 2)
        expect = q16_div(THREE, TWO)
        r.check(f'DIV(3.0 DEC, 2.0 DEC) -> DECIMAL {expect:#010x} (1.5)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_DECIMAL and v == expect)

        out = run_case(m, case_binary(BOR_OP_DIV, dec_slot(NEG_TWO_QUARTER), dec_slot(THREE)))
        _t, _f, _a, v = read_slot(m, 2)
        expect = q16_div(NEG_TWO_QUARTER, THREE)
        r.check(f'DIV(-2.25 DEC, 3.0 DEC) -> DECIMAL {expect:#010x} (truncated toward zero)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_DECIMAL and v == expect)

        out = run_case(m, case_binary(BOR_OP_DIV, dec_slot(THREE), int_slot(0)))
        _t, _f, _a, v = read_slot(m, 2)
        r.check('DIV(3.0 DEC, 0 INTEGER) -> EMPTY, not a fault (unchanged historical behavior)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_EMPTY)

        # --- INC/DEC on DECIMAL: advance only the integer-part word ---
        out = run_case(m, case_unary(BOR_OP_INC, dec_slot(HALF)))
        _t, _f, _a, v = read_slot(m, 0)
        expect = q16_inc(HALF)
        r.check(f'INC(0.5 DECIMAL) -> DECIMAL {expect:#010x} (1.5, not 0.500015...)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_DECIMAL and v == expect)

        out = run_case(m, case_unary(BOR_OP_DEC, dec_slot(HALF)))
        _t, _f, _a, v = read_slot(m, 0)
        expect = q16_dec(HALF)
        r.check(f'DEC(0.5 DECIMAL) -> DECIMAL {expect:#010x} (-0.5)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_DECIMAL and v == expect)

        # --- NEG on DECIMAL ---
        out = run_case(m, case_unary(BOR_OP_NEG, dec_slot(NEG_TWO_QUARTER)))
        _t, _f, _a, v = read_slot(m, 0)
        expect = q16_neg(NEG_TWO_QUARTER)
        r.check(f'NEG(-2.25 DECIMAL) -> DECIMAL {expect:#010x} (2.25)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_DECIMAL and v == expect)

        # --- Truthiness: DECIMAL 0.0 is falsy, any nonzero DECIMAL is truthy ---
        out = run_case(m, case_unary(BOR_OP_NOT, dec_slot(0)))
        _t, _f, _a, v = read_slot(m, 0)
        r.check('NOT(0.0 DECIMAL) -> INTEGER 1 (falsy)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_INTEGER and v == 1)

        out = run_case(m, case_unary(BOR_OP_NOT, dec_slot(q16(0, 1))))
        _t, _f, _a, v = read_slot(m, 0)
        r.check('NOT(0.0001 DECIMAL, nonzero fraction only) -> INTEGER 0 (truthy)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_INTEGER and v == 0)

        # --- Comparisons: mixed INTEGER/DECIMAL, and pure DECIMAL ---
        cmp_cases = [
            (BOR_OP_LT, int_slot(3), dec_slot(THREE), 0),          # 3 < 3.0 -> false
            (BOR_OP_LE, int_slot(3), dec_slot(THREE), 1),          # 3 <= 3.0 -> true
            (BOR_OP_GT, dec_slot(THREE), int_slot(2), 1),          # 3.0 > 2 -> true
            (BOR_OP_GE, dec_slot(NEG_TWO_QUARTER), int_slot(-2), 0),  # -2.25 >= -2 -> false
            (BOR_OP_EQ, int_slot(3), dec_slot(THREE), 1),          # 3 == 3.0 -> true
            (BOR_OP_NE, dec_slot(HALF), dec_slot(NEG_HALF), 1),    # 0.5 != -0.5 -> true
        ]
        for op, sb, sc, expect in cmp_cases:
            out = run_case(m, case_binary(op, sb, sc))
            _t, _f, _a, v = read_slot(m, 2)
            names = {BOR_OP_LT: 'LT', BOR_OP_LE: 'LE', BOR_OP_GT: 'GT',
                     BOR_OP_GE: 'GE', BOR_OP_EQ: 'EQ', BOR_OP_NE: 'NE'}
            r.check(f'{names[op]} mixed/DECIMAL comparison -> INTEGER {expect}',
                    out and out['status'] == VMSTAT_DONE and _t == BOR_VT_INTEGER and v == expect)

        # --- MOD/SHL/SHR/BIT_OR: DECIMAL operand integer-converted, result
        # always INTEGER (opcode_manifest.csv's own wording for these). ---
        seven_and_half = q16(7, 5000)   # 7.5 -> integer-convert -> 7
        out = run_case(m, case_binary(BOR_OP_MOD, dec_slot(seven_and_half), int_slot(3)))
        _t, _f, _a, v = read_slot(m, 2)
        r.check('MOD(7.5 DECIMAL, 3 INTEGER) -> INTEGER 1 (7.5 integer-converts to 7 first)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_INTEGER and v == 1)

        neg_seven_half = q16(-7, -5000)   # -7.5 -> truncate toward zero -> -7
        out = run_case(m, case_binary(BOR_OP_SHL, dec_slot(q16(1, 0)), int_slot(3)))
        _t, _f, _a, v = read_slot(m, 2)
        r.check('SHL(1.0 DECIMAL, 3 INTEGER) -> INTEGER 8 (1.0 integer-converts to 1, then <<3)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_INTEGER and v == 8)

        out = run_case(m, case_binary(BOR_OP_SHR, int_slot(16), dec_slot(TWO)))
        _t, _f, _a, v = read_slot(m, 2)
        r.check('SHR(16 INTEGER, 2.0 DECIMAL) -> INTEGER 4 (right operand integer-converts to 2)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_INTEGER and v == 4)

        out = run_case(m, case_binary(BOR_OP_BIT_OR, dec_slot(q16(5, 0)), int_slot(2)))
        _t, _f, _a, v = read_slot(m, 2)
        r.check('BIT_OR(5.0 DECIMAL, 2 INTEGER) -> INTEGER 7',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_INTEGER and v == 7)

        out = run_case(m, case_binary(BOR_OP_MOD, dec_slot(neg_seven_half), int_slot(3)))
        _t, _f, _a, v = read_slot(m, 2)
        r.check('MOD(-7.5 DECIMAL, 3 INTEGER) -> INTEGER -1 (-7.5 truncates toward zero to -7)',
                out and out['status'] == VMSTAT_DONE and _t == BOR_VT_INTEGER and s32(v) == -1)

        # --- BAD_TYPE: DECIMAL paired with EMPTY still faults (numeric-only op) ---
        out = run_case(m, case_binary(BOR_OP_MUL, dec_slot(THREE), empty_slot()))
        r.check('MUL(3.0 DECIMAL, EMPTY) -> FAULT VMERR_BAD_TYPE',
                out and out['status'] == VMSTAT_FAULT and out['error'] == VMERR_BAD_TYPE)

        r.check('guard regions intact after the full Gate 5 run', guard_intact(m))

    r.finish()


if __name__ == '__main__':
    main()
