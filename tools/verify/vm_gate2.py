#!/usr/bin/env python3
"""plan_vm.md §4, Gate 2: the integer unary/binary family.

Implements and gates: LOAD (3), SAVE (4), INC (5), DEC (6), POS (9),
NEG (10), NOT (11), MUL (12), DIV (13), MOD (14), SUB (17), SHL (18),
SHR (19), GE/LE/LT/GT (22-25), NE (27), OR/AND (28-29),
BIT_OR/XOR/BIT_AND (30-32).

MECHANISM: same direct-WRAM-injection approach as vm_gate1.py (see that
file's own header for the full rationale -- terminal status is sticky per
boot, so each case is injected into the already-booted VM rather than
shipped as a separate ROM). Every case is a 2-instruction program
(operate, then RET), injected with VmState_Status=VMSTAT_READY last so the
existing per-frame `jsr Vm_Run` (scpu_main_loop) is what actually drives
it -- never a second entry point.

ORACLE: `oracle.py`-style pure-Python functions in this file, built
directly from opcode_manifest.csv's semantics and this gate's own
documented decisions (src/core/vm/vm_arith32.pasm's header comment):
  - Integer overflow = two's-complement 32-bit wrap.
  - Shift counts = the right operand's raw 32-bit bit pattern, low 5 bits
    (`count & 31`), independent of the operand's signed value.
  - DIV by zero -> EMPTY, not a fault. MOD by zero -> VMERR_DIV_ZERO.
  - NEG/INC/DEC on a non-INTEGER slot: unchanged, not faulted.
  - OR/AND: VM truthiness (Branch_FALSE/TRUE's rule), never a type fault.
  - Every other binary op in this gate: VT_INTEGER-or-VMERR_BAD_TYPE on
    both operands (ADD/EQ's own precedent from Gate 0/1).

Usage: python tools/verify/vm_gate2.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant_in, read_block, repo_root_from, Reporter  # noqa: E402

ROOT = repo_root_from(__file__)
CONSTS = 'src/core/vm/vm_consts.pasm'
OPCODES = 'src/core/vm/bor_vm_opcodes.pasm'
FIXTURES = os.path.join(ROOT, 'tools', 'verify', 'vm_fixtures')

VmCode_Wram = pasm_constant_in(CONSTS, 'VmCode_Wram')
VmSlots_Wram = pasm_constant_in(CONSTS, 'VmSlots_Wram')
VM_STATE_FIRST = pasm_constant_in(CONSTS, 'VM_STATE_FIRST')
VmState_Status = pasm_constant_in(CONSTS, 'VmState_Status')
VmState_Error = pasm_constant_in(CONSTS, 'VmState_Error')
VmState_Ip = pasm_constant_in(CONSTS, 'VmState_Ip')
VmState_InstrCount = pasm_constant_in(CONSTS, 'VmState_InstrCount')
VmState_SlotCount = pasm_constant_in(CONSTS, 'VmState_SlotCount')

VMSTAT_DONE = pasm_constant_in(CONSTS, 'VMSTAT_DONE')
VMSTAT_FAULT = pasm_constant_in(CONSTS, 'VMSTAT_FAULT')
VMSTAT_READY = pasm_constant_in(CONSTS, 'VMSTAT_READY')
VMERR_NONE = pasm_constant_in(CONSTS, 'VMERR_NONE')
VMERR_BAD_TYPE = pasm_constant_in(CONSTS, 'VMERR_BAD_TYPE')
VMERR_DIV_ZERO = pasm_constant_in(CONSTS, 'VMERR_DIV_ZERO')

OP = {name: pasm_constant_in(OPCODES, f'BOR_OP_{name}')
      for name in ('LOAD', 'SAVE', 'INC', 'DEC', 'POS', 'NEG', 'NOT', 'MUL',
                    'DIV', 'MOD', 'SUB', 'SHL', 'SHR', 'GE', 'LE', 'LT', 'GT',
                    'NE', 'OR', 'AND', 'BIT_OR', 'XOR', 'BIT_AND', 'RET')}
VT_EMPTY = pasm_constant_in(OPCODES, 'BOR_VT_EMPTY')
VT_INTEGER = pasm_constant_in(OPCODES, 'BOR_VT_INTEGER')

with open(os.path.join(FIXTURES, 'gate0_module.bin'), 'rb') as f:
    GATE0_MODULE = f.read()
INSTRUCTIONS_OFFSET = struct.unpack_from('<I', GATE0_MODULE, 0x18)[0]
RECORDS_ADDR = VmCode_Wram + INSTRUCTIONS_OFFSET
RECORDS_BUDGET = 144 - INSTRUCTIONS_OFFSET  # gate0_module.bin's 10-record window

MASK32 = 0xFFFFFFFF
MIN_I32 = -0x80000000
MAX_I32 = 0x7FFFFFFF


def i32(v):
    v &= MASK32
    return v - 0x100000000 if v & 0x80000000 else v


def u32(v):
    return v & MASK32


def rec(op, a=0, b=0, c=0, flags=0):
    return struct.pack('<BBHHH', op & 0xFF, flags & 0xFF, a & 0xFFFF, b & 0xFFFF, c & 0xFFFF)


def slot_bytes(vtype, value=0):
    return struct.pack('<BBHi', vtype, 0, 0, i32(value))


def int_slot(value):
    return slot_bytes(VT_INTEGER, value)


def empty_slot():
    return slot_bytes(VT_EMPTY, 0)


# ---------------------------------------------------------------------------
# Host oracle -- pure Python, built from opcode_manifest.csv plus this
# gate's own documented decisions (see file header and
# src/core/vm/vm_arith32.pasm's own header comment).
# ---------------------------------------------------------------------------

def oracle_shift_count(right):
    return u32(right) & 0x1F


def oracle_mul(left, right):
    return i32(left * right)


def oracle_sub(left, right):
    return i32(left - right)


def oracle_shl(left, right):
    return i32((u32(left) << oracle_shift_count(right)) & MASK32)


def oracle_shr(left, right):
    return i32((u32(left) >> oracle_shift_count(right)) & MASK32)


def oracle_divmod(left, right):
    """Truncate-toward-zero signed division; remainder follows the
    dividend's sign. Returns (quotient, remainder), both i32-wrapped
    (matters only at MIN_I32 / -1)."""
    q_mag = abs(left) // abs(right)
    q = q_mag if (left < 0) == (right < 0) else -q_mag
    r = left - q * right
    return i32(q), i32(r)


def oracle_cmp(op, left, right):
    if op == 'GE':
        return int(left >= right)
    if op == 'LE':
        return int(left <= right)
    if op == 'LT':
        return int(left < right)
    if op == 'GT':
        return int(left > right)
    if op == 'NE':
        return int(left != right)
    raise AssertionError(op)


def oracle_bitwise(op, left, right):
    if op == 'BIT_OR':
        return i32(u32(left) | u32(right))
    if op == 'XOR':
        return i32(u32(left) ^ u32(right))
    if op == 'BIT_AND':
        return i32(u32(left) & u32(right))
    raise AssertionError(op)


EDGE_VALUES = [0, 1, -1, MAX_I32, MIN_I32, 12345, -6789]

BINARY_INT_PAIRS = [
    (0, 0), (1, 1), (-1, 1), (1, -1), (-1, -1),
    (MAX_I32, 1), (MIN_I32, 1), (MAX_I32, MIN_I32), (MIN_I32, MAX_I32),
    (12345, -6789), (0, MAX_I32), (0, MIN_I32), (MAX_I32, MAX_I32), (MIN_I32, MIN_I32),
]

DIVMOD_PAIRS = [
    (10, 0), (1, 0), (0, 0),                         # divisor zero
    (MIN_I32, -1), (MAX_I32, 1), (MIN_I32, 1),
    (7, 2), (-7, 2), (7, -2), (-7, -2),
    (MIN_I32, MIN_I32), (MAX_I32, MAX_I32),
    (0, 5), (0, -5), (100000, 7),
]

SHIFT_COUNTS = [-1, 0, 1, 5, 31, 32, 33, -33]
SHIFT_LEFTS = [1, -1, MAX_I32, MIN_I32]

UNARY_VALUES = [0, 1, -1, MAX_I32, MIN_I32]

TRUTHY_PAIRS = [
    (int_slot(0), int_slot(0)), (int_slot(0), int_slot(1)),
    (int_slot(1), int_slot(0)), (int_slot(1), int_slot(1)),
    (empty_slot(), int_slot(1)), (int_slot(1), empty_slot()),
    (empty_slot(), empty_slot()), (int_slot(-1), int_slot(0)),
]

BINARY_FAULT_OPS = ['MUL', 'DIV', 'MOD', 'SUB', 'SHL', 'SHR',
                     'GE', 'LE', 'LT', 'GT', 'NE', 'BIT_OR', 'XOR', 'BIT_AND']


def build_cases():
    """Yields (label, records, instr_count, slots_bytes, slot_count,
    check_fn(state_bytes) -> bool)."""
    cases = []

    def status_error_of(state):
        status = state[VmState_Status - VM_STATE_FIRST]
        error = state[VmState_Error - VM_STATE_FIRST] | (state[VmState_Error - VM_STATE_FIRST + 1] << 8)
        return status, error

    def slot0_of(state):
        # slot 0 lives at VmSlots_Wram, read separately (see run_case).
        raise AssertionError('use the dedicated slot reader, not VM_STATE')

    # --- Binary INTEGER-or-fault ops: MUL/SUB/GE/LE/LT/GT/NE/BIT_OR/XOR/BIT_AND ---
    for name in ['MUL', 'SUB', 'GE', 'LE', 'LT', 'GT', 'NE', 'BIT_OR', 'XOR', 'BIT_AND']:
        for left, right in BINARY_INT_PAIRS:
            if name == 'MUL':
                want = oracle_mul(left, right)
            elif name == 'SUB':
                want = oracle_sub(left, right)
            elif name in ('GE', 'LE', 'LT', 'GT', 'NE'):
                want = oracle_cmp(name, left, right)
            else:
                want = oracle_bitwise(name, left, right)
            records = rec(OP[name], a=0, b=1, c=2) + rec(OP['RET'])
            slots = empty_slot() + int_slot(left) + int_slot(right)
            cases.append((
                f'{name}({left},{right})', records, 2, slots, 3,
                ('slot0', VT_INTEGER, i32(want))))

    # --- DIV / MOD ---
    for left, right in DIVMOD_PAIRS:
        q, r = oracle_divmod(left, right) if right != 0 else (None, None)
        records = rec(OP['DIV'], a=0, b=1, c=2) + rec(OP['RET'])
        slots = empty_slot() + int_slot(left) + int_slot(right)
        if right == 0:
            cases.append((f'DIV({left},{right})', records, 2, slots, 3,
                           ('slot0', VT_EMPTY, 0)))
        else:
            cases.append((f'DIV({left},{right})', records, 2, slots, 3,
                           ('slot0', VT_INTEGER, q)))

        records = rec(OP['MOD'], a=0, b=1, c=2) + rec(OP['RET'])
        if right == 0:
            cases.append((f'MOD({left},{right})', records, 2, slots, 3,
                           ('fault', VMERR_DIV_ZERO)))
        else:
            cases.append((f'MOD({left},{right})', records, 2, slots, 3,
                           ('slot0', VT_INTEGER, r)))

    # --- SHL / SHR ---
    for left in SHIFT_LEFTS:
        for count in SHIFT_COUNTS:
            records = rec(OP['SHL'], a=0, b=1, c=2) + rec(OP['RET'])
            slots = empty_slot() + int_slot(left) + int_slot(count)
            cases.append((f'SHL({left},{count})', records, 2, slots, 3,
                           ('slot0', VT_INTEGER, oracle_shl(left, count))))

            records = rec(OP['SHR'], a=0, b=1, c=2) + rec(OP['RET'])
            cases.append((f'SHR({left},{count})', records, 2, slots, 3,
                           ('slot0', VT_INTEGER, oracle_shr(left, count))))

    # --- INC / DEC / POS / NEG / NOT (unary, in-place on slot 1) ---
    for value in UNARY_VALUES:
        records = rec(OP['INC'], a=1) + rec(OP['RET'])
        slots = empty_slot() + int_slot(value)
        cases.append((f'INC({value})', records, 2, slots, 2,
                       ('slot1', VT_INTEGER, i32(value + 1))))

        records = rec(OP['DEC'], a=1) + rec(OP['RET'])
        cases.append((f'DEC({value})', records, 2, slots, 2,
                       ('slot1', VT_INTEGER, i32(value - 1))))

        records = rec(OP['NEG'], a=1) + rec(OP['RET'])
        cases.append((f'NEG({value})', records, 2, slots, 2,
                       ('slot1', VT_INTEGER, i32(-value))))

        records = rec(OP['NOT'], a=1) + rec(OP['RET'])
        cases.append((f'NOT({value})', records, 2, slots, 2,
                       ('slot1', VT_INTEGER, int(value == 0))))

        records = rec(OP['POS'], a=1) + rec(OP['RET'])
        cases.append((f'POS({value})', records, 2, slots, 2,
                       ('slot1', VT_INTEGER, i32(value))))

    # INC/DEC/NEG on non-INTEGER: unchanged, not faulted.
    for name in ['INC', 'DEC', 'NEG']:
        records = rec(OP[name], a=1) + rec(OP['RET'])
        slots = empty_slot() + empty_slot()
        cases.append((f'{name}(EMPTY)', records, 2, slots, 2,
                       ('slot1', VT_EMPTY, 0)))
    # POS on non-INTEGER: also unchanged (true no-op).
    records = rec(OP['POS'], a=1) + rec(OP['RET'])
    slots = empty_slot() + empty_slot()
    cases.append(('POS(EMPTY)', records, 2, slots, 2, ('slot1', VT_EMPTY, 0)))
    # NOT on non-INTEGER: falsy -> 1.
    records = rec(OP['NOT'], a=1) + rec(OP['RET'])
    slots = empty_slot() + empty_slot()
    cases.append(('NOT(EMPTY)', records, 2, slots, 2, ('slot1', VT_INTEGER, 1)))

    # --- LOAD / SAVE ---
    for name in ['LOAD', 'SAVE']:
        for value in [5, -1, MAX_I32, MIN_I32]:
            records = rec(OP[name], a=0, b=1) + rec(OP['RET'])
            slots = empty_slot() + int_slot(value)
            cases.append((f'{name}(INTEGER {value})', records, 2, slots, 2,
                           ('slot0', VT_INTEGER, i32(value))))
        records = rec(OP[name], a=0, b=1) + rec(OP['RET'])
        slots = int_slot(999) + empty_slot()
        cases.append((f'{name}(EMPTY)', records, 2, slots, 2,
                       ('slot0', VT_EMPTY, 0)))

    # --- OR / AND (truthiness, never faults) ---
    for name in ['OR', 'AND']:
        for left_bytes, right_bytes in TRUTHY_PAIRS:
            left_truthy = left_bytes[0] == VT_INTEGER and struct.unpack_from('<i', left_bytes, 4)[0] != 0
            right_truthy = right_bytes[0] == VT_INTEGER and struct.unpack_from('<i', right_bytes, 4)[0] != 0
            want = int((left_truthy or right_truthy) if name == 'OR' else (left_truthy and right_truthy))
            records = rec(OP[name], a=0, b=1, c=2) + rec(OP['RET'])
            slots = empty_slot() + left_bytes + right_bytes
            cases.append((f'{name}({left_truthy},{right_truthy})', records, 2, slots, 3,
                           ('slot0', VT_INTEGER, want)))

    # --- Type-mismatch faults: every binary-fault op, left EMPTY / right INTEGER ---
    for name in BINARY_FAULT_OPS:
        records = rec(OP[name], a=0, b=1, c=2) + rec(OP['RET'])
        slots = empty_slot() + empty_slot() + int_slot(2)
        cases.append((f'{name}(EMPTY,INTEGER) type fault', records, 2, slots, 3,
                       ('fault', VMERR_BAD_TYPE)))
        records = rec(OP[name], a=0, b=1, c=2) + rec(OP['RET'])
        slots = empty_slot() + int_slot(2) + empty_slot()
        cases.append((f'{name}(INTEGER,EMPTY) type fault', records, 2, slots, 3,
                       ('fault', VMERR_BAD_TYPE)))

    return cases


def run_case(m, records, instr_count, slots, slot_count):
    assert len(records) <= RECORDS_BUDGET, 'case overflows the shipped module\'s record window'
    assert len(slots) <= 1024 * 8

    m.write_memory('snesMemory', RECORDS_ADDR, records.hex())
    m.write_memory('snesMemory', VmSlots_Wram, slots.hex())
    m.write_u16(VmState_Ip, 0)
    m.write_u16(VmState_Error, 0)
    m.write_u16(VmState_InstrCount, instr_count)
    m.write_u16(VmState_SlotCount, slot_count)
    m.write_u8(VmState_Status, VMSTAT_READY)

    state = None
    for _ in range(30):
        m.run_frames(2)
        m.pause()
        state = read_block(m, VM_STATE_FIRST, 32)
        if state[VmState_Status - VM_STATE_FIRST] != VMSTAT_READY:
            break
    else:
        return None

    status = state[VmState_Status - VM_STATE_FIRST]
    error = state[VmState_Error - VM_STATE_FIRST] | (state[VmState_Error - VM_STATE_FIRST + 1] << 8)
    slots_state = read_block(m, VmSlots_Wram, 32)
    return status, error, slots_state


def check_expectation(status, error, slots_state, expectation):
    kind = expectation[0]
    if kind == 'fault':
        want_error = expectation[1]
        return status == VMSTAT_FAULT and error == want_error
    if status != VMSTAT_DONE or error != VMERR_NONE:
        return False
    _, want_type, want_value = expectation
    slot_index = 0 if kind == 'slot0' else 1
    off = slot_index * 8
    got_type = slots_state[off]
    got_value = struct.unpack_from('<i', slots_state, off + 4)[0]
    return got_type == want_type and got_value == want_value


def main():
    r = Reporter('2', kind='GATE')
    cases = build_cases()

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        boot_status = read_block(m, VM_STATE_FIRST, 32)[VmState_Status - VM_STATE_FIRST]
        r.check(f'boot (shipped Gate 0 module) reached a terminal status '
                 f'before injection began (status={boot_status})',
                 boot_status in (VMSTAT_DONE, VMSTAT_FAULT))

        mismatches = []
        for label, records, instr_count, slots, slot_count, expectation in cases:
            result = run_case(m, records, instr_count, slots, slot_count)
            if result is None:
                mismatches.append(f'{label}: status never left VMSTAT_READY after 30 frames')
                continue
            status, error, slots_state = result
            if not check_expectation(status, error, slots_state, expectation):
                if expectation[0] == 'fault':
                    mismatches.append(f'{label}: got status={status} error=${error:04X}, '
                                       f'want FAULT ${expectation[1]:04X}')
                else:
                    slot_index = 0 if expectation[0] == 'slot0' else 1
                    off = slot_index * 8
                    got_type = slots_state[off]
                    got_value = struct.unpack_from('<i', slots_state, off + 4)[0]
                    mismatches.append(
                        f'{label}: got status={status} error=${error:04X} '
                        f'type={got_type} value={got_value}, '
                        f'want type={expectation[1]} value={expectation[2]}')

        if mismatches:
            print(f'{len(mismatches)} of {len(cases)} cases mismatched:')
            for line in mismatches[:60]:
                print('  ' + line)
            if len(mismatches) > 60:
                print(f'  ... and {len(mismatches) - 60} more')
        r.check(f'all {len(cases)} Gate 2 edge-vector cases match the host oracle',
                not mismatches)

    r.finish()


if __name__ == '__main__':
    main()
