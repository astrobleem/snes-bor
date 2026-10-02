#!/usr/bin/env python3
"""plan_vm.md §6, Gate 4: strings and typed pointers.

Implements and gates: interned ROM strings (materialized inertly by
CONSTSTR at module-load time -- nothing new to test there beyond "the
prelinked slot image round-trips", already covered by Gate 0's own module
load), a bounded 64-object dynamic string pool at VmStrPool_Wram
(src/core/vm/vm_string.pasm), refcount-on-copy via LOAD/SAVE (Vm_SlotCopy,
vm_arith32.pasm), release-on-overwrite, ADD string concatenation, VM
truthiness extended to STR (empty = false), and lexicographic comparison
shared by EQ/NE/GE/LE/LT/GT (Vm_LoadAndCompare, vm_string.pasm).

MECHANISM: same direct-WRAM-injection approach as vm_gate1.py/vm_gate2.py/
vm_gate3.py -- see vm_gate1.py's own header for the full rationale. Every
case writes its own instruction records into a fixed window inside
VmCode_Wram, and this file ADDITIONALLY writes a fixed interned-string table
(FORMAT.md "Interned strings") into its own window, pointed at once via
VmStr_StringsOff -- the same "poke the cached header-derived offset once,
then only rewrite window CONTENTS per case" trick vm_gate3.py already uses
for VmCall_CallsitesOff/VmCall_ArgSlotsOff.

VmStrPool_Wram is explicitly zeroed once at the top of main() (all 64
objects' refcount bytes become 0 = free) -- unlike VmSlots_Wram, which every
run_case() call rewrites wholesale, the pool is DELIBERATELY left to persist
across cases within a phase of this script, since refcount leak/exhaustion
behavior can only be observed as state that accumulates across many
operations. Cases that need a clean 64-object budget (pool exhaustion) zero
it again immediately before running.

ORACLE: hand-computed per case (see each case's own comment), same style as
vm_gate3.py's small deliberately-shaped programs.

Usage: python tools/verify/vm_gate4.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant_in, read_block, repo_root_from, Reporter  # noqa: E402

ROOT = repo_root_from(__file__)
CONSTS = 'src/core/vm/vm_consts.pasm'
RUN = 'src/core/vm/vm_run.pasm'
STRING = 'src/core/vm/vm_string.pasm'
OPCODES = 'src/core/vm/bor_vm_opcodes.pasm'

VmCode_Wram = pasm_constant_in(CONSTS, 'VmCode_Wram')
VmSlots_Wram = pasm_constant_in(CONSTS, 'VmSlots_Wram')
VmStrPool_Wram = pasm_constant_in(CONSTS, 'VmStrPool_Wram')
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
VMERR_STRING_POOL = pasm_constant_in(CONSTS, 'VMERR_STRING_POOL')
VMERR_STRING_OVERFLOW = pasm_constant_in(CONSTS, 'VMERR_STRING_OVERFLOW')
VmGuardLo = pasm_constant_in(CONSTS, 'VmGuardLo')
VmGuardHi = pasm_constant_in(CONSTS, 'VmGuardHi')
VM_GUARD_LEN = pasm_constant_in(CONSTS, 'VM_GUARD_LEN')
VM_GUARD_LO_FILL = pasm_constant_in(CONSTS, 'VM_GUARD_LO_FILL')
VM_GUARD_HI_FILL = pasm_constant_in(CONSTS, 'VM_GUARD_HI_FILL')
VMSTRPOOL_OBJ_SIZE = pasm_constant_in(CONSTS, 'VMSTRPOOL_OBJ_SIZE')
VMSTRPOOL_OBJ_COUNT = pasm_constant_in(CONSTS, 'VMSTRPOOL_OBJ_COUNT')
VMSTRPOOL_MAX_LEN = pasm_constant_in(CONSTS, 'VMSTRPOOL_MAX_LEN')
VMSTR_DYNAMIC_HI = pasm_constant_in(CONSTS, 'VMSTR_DYNAMIC_HI')

VmPriv_InstrOff = pasm_constant_in(RUN, 'VmPriv_InstrOff')
VmStr_StringsOff = pasm_constant_in(STRING, 'VmStr_StringsOff')

BOR_OP_ADD = pasm_constant_in(OPCODES, 'BOR_OP_ADD')
BOR_OP_SAVE = pasm_constant_in(OPCODES, 'BOR_OP_SAVE')
BOR_OP_NOT = pasm_constant_in(OPCODES, 'BOR_OP_NOT')
BOR_OP_EQ = pasm_constant_in(OPCODES, 'BOR_OP_EQ')
BOR_OP_NE = pasm_constant_in(OPCODES, 'BOR_OP_NE')
BOR_OP_LT = pasm_constant_in(OPCODES, 'BOR_OP_LT')
BOR_OP_GT = pasm_constant_in(OPCODES, 'BOR_OP_GT')
BOR_OP_RET = pasm_constant_in(OPCODES, 'BOR_OP_RET')
BOR_VT_EMPTY = pasm_constant_in(OPCODES, 'BOR_VT_EMPTY')
BOR_VT_INTEGER = pasm_constant_in(OPCODES, 'BOR_VT_INTEGER')
BOR_VT_STR = pasm_constant_in(OPCODES, 'BOR_VT_STR')

# --- Fixed windows this gate's cases rewrite every case. ---
INSTR_WINDOW_OFF = 0x1000     # 1024 B -- 128 instruction records
STRINGS_WINDOW_OFF = 0x3000   # interned-string table (written once)

INSTR_ADDR = VmCode_Wram + INSTR_WINDOW_OFF
STRINGS_ADDR = VmCode_Wram + STRINGS_WINDOW_OFF


def rec(op, a=0, b=0, c=0, flags=0):
    return struct.pack('<BBHHH', op & 0xFF, flags & 0xFF, a & 0xFFFF, b & 0xFFFF, c & 0xFFFF)


def int_slot(value):
    return struct.pack('<BBHi', BOR_VT_INTEGER, 0, 0, value)


def empty_slot():
    return struct.pack('<BBHi', BOR_VT_EMPTY, 0, 0, 0)


def rom_str_slot(index, length):
    return struct.pack('<BBHI', BOR_VT_STR, 0, length, index)


def pad(data, size):
    assert len(data) <= size, f'{len(data)} bytes does not fit a {size}-byte window'
    return data + b'\x00' * (size - len(data))


def build_string_table(strings):
    """FORMAT.md 'Interned strings': u16 count, u16 offset[count+1], bytes[]."""
    offsets = [0]
    for s in strings:
        offsets.append(offsets[-1] + len(s))
    header = struct.pack('<H', len(strings)) + b''.join(struct.pack('<H', o) for o in offsets)
    return header + b''.join(strings)


# Shared string table for every case in this file. Indices are stable --
# every case references these by position.
STRINGS = [
    b'hi',          # 0
    b'',             # 1  -- empty, for truthiness
    b'foo',          # 2
    b'bar',          # 3
    b'foobar',       # 4  -- expected concat(foo, bar)
    b'foobas',       # 5  -- one byte greater than foobar, for ordering
    b'A' * 61,       # 6  -- 61 bytes: 61+1=62 fits exactly
    b'B',            # 7  -- 1 byte: pairs with 6 for the exact-fit case
    b'C',            # 8  -- 1 byte
    b'D' * 2,        # 9  -- 2 bytes: pairs with 6 for 61+2=63, over the limit
]
STRING_TABLE_BYTES = build_string_table(STRINGS)


class Case:
    def __init__(self, instrs, slots, entry_ip=0):
        self.instrs = instrs
        self.slots = slots
        self.entry_ip = entry_ip
        self.instr_count = len(instrs) // 8


def run_case(m, case, clear_slots_up_to=64):
    m.write_memory('snesMemory', INSTR_ADDR, pad(case.instrs, 1024).hex())
    m.write_memory('snesMemory', VmSlots_Wram, pad(case.slots, max(len(case.slots), clear_slots_up_to * 8)).hex())

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
    for _ in range(120):
        m.run_frames(2)
        m.pause()
        state = read_block(m, VM_STATE_FIRST, 32)
        status_byte = field(state, VmState_Status, 1)
        # RUNNING is not a stopping point -- Vm_Run is a single synchronous
        # jsr that does not return control to the main loop until DONE/
        # FAULT/YIELDED; NMI can still interrupt-and-resume it across many
        # real Mesen "frames" while it stays mid-execution the whole time
        # (heavy Gate 4 string ops, unlike Gate 0-3's cheap integer ops, can
        # genuinely span several frames of real 65816 cycles inside ONE
        # Vm_Run call). Stopping at the first non-READY status here would
        # wrongly treat a still-in-progress RUNNING snapshot as finished.
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


def pool_object(m, index):
    data = read_block(m, VmStrPool_Wram + index * VMSTRPOOL_OBJ_SIZE, 64)[:VMSTRPOOL_OBJ_SIZE]
    refcount = data[0]
    length = data[1]
    return refcount, length, data[2:2 + length]


def guard_intact(m):
    lo = read_block(m, VmGuardLo, 32)[:VM_GUARD_LEN]
    hi = read_block(m, VmGuardHi, 32)[:VM_GUARD_LEN]
    return (lo == bytes([VM_GUARD_LO_FILL]) * VM_GUARD_LEN
            and hi == bytes([VM_GUARD_HI_FILL]) * VM_GUARD_LEN)


def clear_pool(m):
    m.write_memory('snesMemory', VmStrPool_Wram, ('00' * (VMSTRPOOL_OBJ_COUNT * VMSTRPOOL_OBJ_SIZE)))


def dynamic_handle_index(vtype, aux, value):
    assert vtype == BOR_VT_STR
    assert (value >> 16) & 0x8000 == VMSTR_DYNAMIC_HI, 'expected a dynamic (pool) handle'
    return value & 0xFFFF


# =============================================================================
# Case builders
# =============================================================================

def case_truthy(str_index, str_len, expect_not_result):
    """NOT a=0 -- NOT is in-place (opcode_manifest.csv: "a=operand slot"),
    the operand slot is ALSO the destination. slot0 starts as a ROM string
    handle; expect_not_result is the INTEGER NOT should leave in slot0
    afterward (VM truthiness eor 1)."""
    instrs = rec(BOR_OP_NOT, a=0) + rec(BOR_OP_RET)
    slots = bytearray(empty_slot() * 1)
    slots[0 * 8:0 * 8 + 8] = rom_str_slot(str_index, str_len)
    return Case(instrs, bytes(slots)), expect_not_result


def case_concat():
    """slot2 = slot0("foo") + slot1("bar")."""
    instrs = rec(BOR_OP_ADD, a=2, b=0, c=1) + rec(BOR_OP_RET)
    slots = bytearray(empty_slot() * 3)
    slots[0 * 8:0 * 8 + 8] = rom_str_slot(2, 3)   # "foo"
    slots[1 * 8:1 * 8 + 8] = rom_str_slot(3, 3)   # "bar"
    return Case(instrs, bytes(slots))


def case_concat_boundary_ok():
    """61-byte + 1-byte = exactly VMSTRPOOL_MAX_LEN (62) -- must NOT fault."""
    instrs = rec(BOR_OP_ADD, a=2, b=0, c=1) + rec(BOR_OP_RET)
    slots = bytearray(empty_slot() * 3)
    slots[0 * 8:0 * 8 + 8] = rom_str_slot(6, 61)   # "A"*61
    slots[1 * 8:1 * 8 + 8] = rom_str_slot(7, 1)    # "B"
    return Case(instrs, bytes(slots))


def case_concat_overflow():
    """61-byte + 2-byte = 63, over VMSTRPOOL_MAX_LEN -- must fault."""
    instrs = rec(BOR_OP_ADD, a=2, b=0, c=1) + rec(BOR_OP_RET)
    slots = bytearray(empty_slot() * 3)
    slots[0 * 8:0 * 8 + 8] = rom_str_slot(6, 61)   # "A"*61
    slots[1 * 8:1 * 8 + 8] = rom_str_slot(9, 2)    # "DD"
    return Case(instrs, bytes(slots))


def case_mixed_type_add():
    """One STR operand, one INTEGER operand -- must fault VMERR_BAD_TYPE
    (documented Gate 4 scope decision: no int->string coercion this gate)."""
    instrs = rec(BOR_OP_ADD, a=2, b=0, c=1) + rec(BOR_OP_RET)
    slots = bytearray(empty_slot() * 3)
    slots[0 * 8:0 * 8 + 8] = rom_str_slot(2, 3)   # "foo"
    slots[1 * 8:1 * 8 + 8] = int_slot(5)
    return Case(instrs, bytes(slots))


def case_eq_dynamic_vs_rom():
    """slot4 = concat(foo,bar); EQ against ROM "foobar" (slot2) -> slot5=1.
    NE against ROM "foobas" (slot3) -> slot6=1."""
    instrs = (rec(BOR_OP_ADD, a=4, b=0, c=1)      # slot4 = foo+bar
              + rec(BOR_OP_EQ, a=5, b=4, c=2)      # slot5 = (slot4 == "foobar")
              + rec(BOR_OP_NE, a=6, b=4, c=3)      # slot6 = (slot4 != "foobas")
              + rec(BOR_OP_LT, a=7, b=4, c=3)      # slot7 = ("foobar" < "foobas")
              + rec(BOR_OP_GT, a=8, b=3, c=4)      # slot8 = ("foobas" > "foobar")
              + rec(BOR_OP_RET))
    slots = bytearray(empty_slot() * 9)
    slots[0 * 8:0 * 8 + 8] = rom_str_slot(2, 3)    # "foo"
    slots[1 * 8:1 * 8 + 8] = rom_str_slot(3, 3)    # "bar"
    slots[2 * 8:2 * 8 + 8] = rom_str_slot(4, 6)    # "foobar"
    slots[3 * 8:3 * 8 + 8] = rom_str_slot(5, 6)    # "foobas"
    return Case(instrs, bytes(slots))


def case_load_save_refcount():
    """slot2 = concat(foo,bar) [pool refcount 1]. SAVE a=3,b=2 [refcount 2].
    SAVE a=2,b=0 (overwrite slot2 with an unrelated ROM string) [refcount 1,
    since only slot3 still references the object]. SAVE a=3,b=1 (overwrite
    slot3 too) [refcount 0, object freed]."""
    instrs = (rec(BOR_OP_ADD, a=2, b=0, c=1)     # slot2 = foo+bar
              + rec(BOR_OP_SAVE, a=3, b=2)        # slot3 = slot2 (retain)
              + rec(BOR_OP_SAVE, a=2, b=0)        # slot2 = "foo" (release old slot2)
              + rec(BOR_OP_SAVE, a=3, b=0)        # slot3 = "foo" (release old slot3)
              + rec(BOR_OP_RET))
    slots = bytearray(empty_slot() * 4)
    slots[0 * 8:0 * 8 + 8] = rom_str_slot(2, 3)   # "foo"
    slots[1 * 8:1 * 8 + 8] = rom_str_slot(3, 3)   # "bar"
    return Case(instrs, bytes(slots))


def case_self_copy_no_free():
    """slot2 = concat(foo,bar). SAVE a=2,b=2 (self-copy) must NOT free the
    object out from under itself (retain-before-release, see Vm_SlotCopy's
    own header note)."""
    instrs = (rec(BOR_OP_ADD, a=2, b=0, c=1)
              + rec(BOR_OP_SAVE, a=2, b=2)
              + rec(BOR_OP_RET))
    slots = bytearray(empty_slot() * 3)
    slots[0 * 8:0 * 8 + 8] = rom_str_slot(2, 3)
    slots[1 * 8:1 * 8 + 8] = rom_str_slot(3, 3)
    return Case(instrs, bytes(slots))


def case_pool_exhaustion(n):
    """n independent ADD concats, each into its OWN destination slot, none
    ever released -- the pool has VMSTRPOOL_OBJ_COUNT objects, so the
    (VMSTRPOOL_OBJ_COUNT+1)th allocation must fault VMERR_STRING_POOL."""
    src_b, src_c = 100, 101
    instrs = b''.join(rec(BOR_OP_ADD, a=i, b=src_b, c=src_c) for i in range(n)) + rec(BOR_OP_RET)
    slots = bytearray(empty_slot() * (max(n, src_c + 1)))
    slots[src_b * 8:src_b * 8 + 8] = rom_str_slot(2, 3)   # "foo"
    slots[src_c * 8:src_c * 8 + 8] = rom_str_slot(3, 3)   # "bar"
    return Case(instrs, bytes(slots))


def main():
    r = Reporter('4', kind='GATE')

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        boot_status = read_block(m, VM_STATE_FIRST, 32)[VmState_Status - VM_STATE_FIRST]
        r.check(f'boot (shipped Gate 0 module) reached a terminal status '
                 f'before injection began (status={boot_status})',
                 boot_status in (VMSTAT_DONE, VMSTAT_FAULT))

        m.write_u16(VmPriv_InstrOff, INSTR_WINDOW_OFF)
        m.write_u16(VmStr_StringsOff, STRINGS_WINDOW_OFF)
        m.write_memory('snesMemory', STRINGS_ADDR, STRING_TABLE_BYTES.hex())
        clear_pool(m)

        # --- Truthiness: ROM string, nonempty vs. empty ---
        case, expect = case_truthy(0, 2, expect_not_result=0)   # "hi" -> truthy -> NOT -> 0
        out = run_case(m, case)
        vtype, _f, _aux, value = read_slot(m, 0)
        r.check('NOT on nonempty ROM string "hi" -> INTEGER 0 (truthy)',
                out is not None and out['status'] == VMSTAT_DONE
                and vtype == BOR_VT_INTEGER and value == expect)

        case, expect = case_truthy(1, 0, expect_not_result=1)   # "" -> falsy -> NOT -> 1
        out = run_case(m, case)
        vtype, _f, _aux, value = read_slot(m, 0)
        r.check('NOT on empty ROM string "" -> INTEGER 1 (falsy)',
                out is not None and out['status'] == VMSTAT_DONE
                and vtype == BOR_VT_INTEGER and value == expect)

        # --- Concatenation ---
        out = run_case(m, case_concat())
        vtype, flags, aux, value = read_slot(m, 2)
        pool_ok = False
        if vtype == BOR_VT_STR and (value >> 16) & 0x8000:
            idx = dynamic_handle_index(vtype, aux, value)
            refcount, length, data = pool_object(m, idx)
            pool_ok = refcount == 1 and length == 6 and bytes(data) == b'foobar'
        r.check('ADD("foo","bar") -> DONE, dest = dynamic STR aux=6, pool object '
                '= refcount 1, "foobar"',
                out is not None and out['status'] == VMSTAT_DONE
                and vtype == BOR_VT_STR and aux == 6 and pool_ok)

        out = run_case(m, case_concat_boundary_ok())
        r.check(f'concat exactly at VMSTRPOOL_MAX_LEN ({VMSTRPOOL_MAX_LEN}) -> DONE, not a fault',
                out is not None and out['status'] == VMSTAT_DONE)

        out = run_case(m, case_concat_overflow())
        r.check('concat one byte over VMSTRPOOL_MAX_LEN -> FAULT VMERR_STRING_OVERFLOW',
                out is not None and out['status'] == VMSTAT_FAULT and out['error'] == VMERR_STRING_OVERFLOW)

        out = run_case(m, case_mixed_type_add())
        r.check('ADD(STR, INTEGER) mixed pair -> FAULT VMERR_BAD_TYPE',
                out is not None and out['status'] == VMSTAT_FAULT and out['error'] == VMERR_BAD_TYPE)

        # --- Comparisons: dynamic string vs. ROM strings, lexicographic ---
        results = []
        for _ in range(3):
            out = run_case(m, case_eq_dynamic_vs_rom())
            eq_v = read_slot(m, 5)[3]
            ne_v = read_slot(m, 6)[3]
            lt_v = read_slot(m, 7)[3]
            gt_v = read_slot(m, 8)[3]
            results.append((out['status'], out['error'], eq_v, ne_v, lt_v, gt_v))
        determinism_ok = len(set(results)) == 1
        expected = (VMSTAT_DONE, VMERR_NONE, 1, 1, 1, 1)
        r.check('EQ/NE/LT/GT across dynamic-vs-ROM strings match expected booleans, '
                 'identical across 3 repeated runs (determinism)',
                 determinism_ok and results[0] == expected)

        # --- LOAD/SAVE refcounting: retain on copy, release on overwrite ---
        out = run_case(m, case_load_save_refcount())
        vtype2, _f2, _aux2, value2 = read_slot(m, 3)
        r.check('after two overwrites, both slots left the dynamic string -- it is not '
                'reachable from any slot any more (final slot3 is the ROM string "foo")',
                out is not None and out['status'] == VMSTAT_DONE
                and vtype2 == BOR_VT_STR and (value2 >> 16) & 0x8000 == 0)

        # Re-run the same concat but inspect the pool object's refcount at
        # each intermediate step (only the final state is directly
        # observable in one run_case call -- rebuild a truncated instruction
        # stream per step). Pool is cleared before EACH of these two runs so
        # both allocate the identical object index (0) -- otherwise step2's
        # ADD would land on a different, still-live object than step1's,
        # since step1's object is never released.
        clear_pool(m)
        step1 = Case(rec(BOR_OP_ADD, a=2, b=0, c=1) + rec(BOR_OP_RET),
                     rom_str_slot(2, 3) + rom_str_slot(3, 3) + empty_slot())
        out = run_case(m, step1)
        _t, _f, _aux, v1 = read_slot(m, 2)
        idx = dynamic_handle_index(BOR_VT_STR, 6, v1)
        rc_after_concat, _len, _data = pool_object(m, idx)

        clear_pool(m)
        step2 = Case(rec(BOR_OP_ADD, a=2, b=0, c=1) + rec(BOR_OP_SAVE, a=3, b=2) + rec(BOR_OP_RET),
                     rom_str_slot(2, 3) + rom_str_slot(3, 3) + empty_slot() + empty_slot())
        out = run_case(m, step2)
        _t2, _f2, _aux2, v2 = read_slot(m, 2)
        idx2 = dynamic_handle_index(BOR_VT_STR, 6, v2)
        rc_after_save, _len, _data = pool_object(m, idx2)
        r.check('refcount is 1 right after ADD, 2 right after a SAVE (LOAD/SAVE retain '
                 'the source before touching the destination)',
                rc_after_concat == 1 and rc_after_save == 2)

        out = run_case(m, case_self_copy_no_free())
        vtype3, _f3, aux3, value3 = read_slot(m, 2)
        self_idx = dynamic_handle_index(BOR_VT_STR, aux3, value3) if vtype3 == BOR_VT_STR else None
        self_rc = pool_object(m, self_idx)[0] if self_idx is not None else -1
        r.check('SAVE a slot onto itself (self-copy of a dynamic string) leaves refcount '
                'at 1, not 0 -- retain-before-release must not free the object it is '
                'about to keep',
                out is not None and out['status'] == VMSTAT_DONE
                and vtype3 == BOR_VT_STR and self_rc == 1)

        # --- Pool exhaustion: exactly VMSTRPOOL_OBJ_COUNT succeed, the next faults ---
        clear_pool(m)
        out = run_case(m, case_pool_exhaustion(VMSTRPOOL_OBJ_COUNT), clear_slots_up_to=VMSTRPOOL_OBJ_COUNT + 8)
        r.check(f'{VMSTRPOOL_OBJ_COUNT} independent concats (never released) all succeed -> DONE',
                out is not None and out['status'] == VMSTAT_DONE)

        clear_pool(m)
        out = run_case(m, case_pool_exhaustion(VMSTRPOOL_OBJ_COUNT + 1), clear_slots_up_to=VMSTRPOOL_OBJ_COUNT + 8)
        r.check(f'{VMSTRPOOL_OBJ_COUNT + 1}th independent concat (pool exhausted) -> '
                 'FAULT VMERR_STRING_POOL',
                out is not None and out['status'] == VMSTAT_FAULT and out['error'] == VMERR_STRING_POOL)

        r.check('guard regions intact after the full Gate 4 run', guard_intact(m))

    r.finish()


if __name__ == '__main__':
    main()
