#!/usr/bin/env python3
"""plan_vm.md §5, Gate 3: calls, frames, and the native ABI.

Implements and gates: CALL (8), PARAM (40), JUMPR (46), RET (43) with real
64-deep call frames (src/core/vm/vm_call.pasm), plus a minimal native
function table (abs/min/max/log, stable IDs 1-4).

MECHANISM: same direct-WRAM-injection approach as vm_gate1.py/vm_gate2.py
(see vm_gate1.py's own header for the full rationale). Every case here
additionally writes its own instruction records, callsite table, and
arg-slot-id table into fixed, generously-sized windows inside VmCode_Wram
FAR past the tiny shipped Gate 0 fixture (which has no callsite table at
all) -- 512 B of instructions at +$1000, 240 B of callsites at +$2000, 128 B
of arg-slot IDs at +$2800, all well inside VmCode_Wram's 32 KB and far from
the 184-byte window vm_gate1.py/vm_gate2.py reuse. VmPriv_InstrOff/
VmCall_CallsitesOff/VmCall_ArgSlotsOff are pointed at these windows ONCE,
directly (the same "just poke the cached WRAM cell" trick this project's
verify scripts already use for other cached header fields), then every case
overwrites the window CONTENTS only.

VmState_FrameTop is explicitly reset to 0 before every case. This is not
optional bookkeeping: vm_gate1.py's own Gate 3 cases (opcode 8, a self-
recursive CALL with default operands) were originally written expecting
VMERR_UNIMPLEMENTED and instead produced VMERR_CALL_DEPTH the first time
this gate's real CALL landed -- caused by exactly this, frame depth leaking
across cases that share one booted VM instance. That was harmless there
(it's still a deterministic fault, just a different one, and vm_gate1.py's
expected-outcome table was corrected to match), but every case in THIS file
is testing frame-stack behavior directly, so leakage here would silently
invalidate the case that follows it.

ORACLE: hand-computed per case (see each case's own comment) -- these are
small, deliberately-shaped programs, not a generated edge-vector sweep like
vm_gate2.py's.

Usage: python tools/verify/vm_gate3.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant_in, read_block, repo_root_from, Reporter  # noqa: E402

ROOT = repo_root_from(__file__)
CONSTS = 'src/core/vm/vm_consts.pasm'
RUN = 'src/core/vm/vm_run.pasm'
CALL = 'src/core/vm/vm_call.pasm'
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
VMERR_NONE = pasm_constant_in(CONSTS, 'VMERR_NONE')
VMERR_BAD_TYPE = pasm_constant_in(CONSTS, 'VMERR_BAD_TYPE')
VMERR_BAD_NATIVE = pasm_constant_in(CONSTS, 'VMERR_BAD_NATIVE')
VMERR_CALL_DEPTH = pasm_constant_in(CONSTS, 'VMERR_CALL_DEPTH')
VMERR_NO_CALL_FRAME = pasm_constant_in(CONSTS, 'VMERR_NO_CALL_FRAME')
VM_FRAME_MAX = pasm_constant_in(CONSTS, 'VM_FRAME_MAX')
VM_NATIVE_ABS = pasm_constant_in(CONSTS, 'VM_NATIVE_ABS')
VM_NATIVE_MIN = pasm_constant_in(CONSTS, 'VM_NATIVE_MIN')
VM_NATIVE_MAX = pasm_constant_in(CONSTS, 'VM_NATIVE_MAX')
VM_NATIVE_LOG = pasm_constant_in(CONSTS, 'VM_NATIVE_LOG')
VM_TARGET_KIND_SCRIPT = pasm_constant_in(CONSTS, 'VM_TARGET_KIND_SCRIPT')
VM_TARGET_KIND_NATIVE = pasm_constant_in(CONSTS, 'VM_TARGET_KIND_NATIVE')
VmGuardLo = pasm_constant_in(CONSTS, 'VmGuardLo')
VmGuardHi = pasm_constant_in(CONSTS, 'VmGuardHi')
VM_GUARD_LEN = pasm_constant_in(CONSTS, 'VM_GUARD_LEN')
VM_GUARD_LO_FILL = pasm_constant_in(CONSTS, 'VM_GUARD_LO_FILL')
VM_GUARD_HI_FILL = pasm_constant_in(CONSTS, 'VM_GUARD_HI_FILL')

VmPriv_InstrOff = pasm_constant_in(RUN, 'VmPriv_InstrOff')

VmCall_CallsitesOff = pasm_constant_in(CALL, 'VmCall_CallsitesOff')
VmCall_ArgSlotsOff = pasm_constant_in(CALL, 'VmCall_ArgSlotsOff')
VmNative_LogLastLo = pasm_constant_in(CALL, 'VmNative_LogLastLo')
VmNative_LogLastHi = pasm_constant_in(CALL, 'VmNative_LogLastHi')

BOR_OP_CALL = pasm_constant_in(OPCODES, 'BOR_OP_CALL')
BOR_OP_PARAM = pasm_constant_in(OPCODES, 'BOR_OP_PARAM')
BOR_OP_JUMPR = pasm_constant_in(OPCODES, 'BOR_OP_JUMPR')
BOR_OP_RET = pasm_constant_in(OPCODES, 'BOR_OP_RET')
BOR_OP_LE = pasm_constant_in(OPCODES, 'BOR_OP_LE')
BOR_OP_SUB = pasm_constant_in(OPCODES, 'BOR_OP_SUB')
BOR_OP_ADD = pasm_constant_in(OPCODES, 'BOR_OP_ADD')
BOR_OP_BRANCH_TRUE = pasm_constant_in(OPCODES, 'BOR_OP_BRANCH_TRUE')
BOR_VT_EMPTY = pasm_constant_in(OPCODES, 'BOR_VT_EMPTY')
BOR_VT_INTEGER = pasm_constant_in(OPCODES, 'BOR_VT_INTEGER')

# --- Fixed windows this gate's cases rewrite every case, far past the tiny
# shipped Gate 0 fixture's own 184-byte module image. ---
INSTR_WINDOW_OFF = 0x1000    # 512 B -- 64 instruction records
CALLSITE_WINDOW_OFF = 0x2000  # 240 B -- 20 callsite records
ARGSLOT_WINDOW_OFF = 0x2800   # 128 B -- 64 u16 arg-slot IDs

INSTR_ADDR = VmCode_Wram + INSTR_WINDOW_OFF
CALLSITE_ADDR = VmCode_Wram + CALLSITE_WINDOW_OFF
ARGSLOT_ADDR = VmCode_Wram + ARGSLOT_WINDOW_OFF


def rec(op, a=0, b=0, c=0, flags=0):
    return struct.pack('<BBHHH', op & 0xFF, flags & 0xFF, a & 0xFFFF, b & 0xFFFF, c & 0xFFFF)


def callsite(target_kind, argc, target_id, arg_list_index, result_slot=0, flags=0, debug_name_id=0xFFFF):
    return struct.pack('<BBHHHHH', target_kind & 0xFF, argc & 0xFF, target_id & 0xFFFF,
                        result_slot & 0xFFFF, arg_list_index & 0xFFFF, flags & 0xFFFF,
                        debug_name_id & 0xFFFF)


def int_slot(value):
    return struct.pack('<BBHi', BOR_VT_INTEGER, 0, 0, value)


def empty_slot():
    return struct.pack('<BBHi', BOR_VT_EMPTY, 0, 0, 0)


def pad(data, size):
    assert len(data) <= size, f'{len(data)} bytes does not fit a {size}-byte window'
    return data + b'\x00' * (size - len(data))


class Case:
    """One Gate 3 program: instructions, callsites, arg-slot IDs, and an
    initial slot image, all pre-baked into the fixed windows above."""

    def __init__(self, instrs, callsites=b'', arg_slots=b'', slots=b'', entry_ip=0):
        self.instrs = instrs
        self.callsites = callsites
        self.arg_slots = arg_slots
        self.slots = slots
        self.entry_ip = entry_ip
        self.instr_count = len(instrs) // 8


def run_case(m, case):
    m.write_memory('snesMemory', INSTR_ADDR, pad(case.instrs, 512).hex())
    m.write_memory('snesMemory', CALLSITE_ADDR, pad(case.callsites, 240).hex())
    m.write_memory('snesMemory', ARGSLOT_ADDR, pad(case.arg_slots, 128).hex())
    m.write_memory('snesMemory', VmSlots_Wram, pad(case.slots, 8192).hex())

    m.write_u16(VmState_Ip, case.entry_ip)
    m.write_u16(VmState_Error, 0)
    m.write_u16(VmState_InstrCount, case.instr_count)
    m.write_u16(VmState_SlotCount, len(case.slots) // 8)
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
        if status_byte != VMSTAT_READY:
            break
    else:
        return None

    error = field(state, VmState_Error, 2)
    frame_top = field(state, VmState_FrameTop, 2)
    return {'status': status_byte, 'error': error, 'frame_top': frame_top}


def read_slot(m, index):
    data = read_block(m, VmSlots_Wram + index * 8, 32)[:8]
    vtype, _flags, _aux, value = struct.unpack('<BBHi', data)
    return vtype, value


def guard_intact(m):
    lo = read_block(m, VmGuardLo, 32)[:VM_GUARD_LEN]
    hi = read_block(m, VmGuardHi, 32)[:VM_GUARD_LEN]
    return (lo == bytes([VM_GUARD_LO_FILL]) * VM_GUARD_LEN
            and hi == bytes([VM_GUARD_HI_FILL]) * VM_GUARD_LEN)


# =============================================================================
# Case builders
# =============================================================================

def case_native(target_id, argc, arg_slot_indices, slot_setup, result_slot=0):
    """Root program: CALL a single native, then RET. slot_setup is a list of
    (index, VT/value-bytes) written into the slot image; arg_slot_indices
    names which of those slots the callsite's arg list points at."""
    cs = callsite(VM_TARGET_KIND_NATIVE, argc, target_id, arg_list_index=0, result_slot=result_slot)
    arg_slots = b''.join(struct.pack('<H', i) for i in arg_slot_indices)
    slot_count = max([result_slot] + [i for i, _ in slot_setup]) + 1
    slots = bytearray(empty_slot() * slot_count)
    for i, data in slot_setup:
        slots[i * 8:i * 8 + 8] = data
    instrs = rec(BOR_OP_CALL, a=0, b=result_slot, c=0) + rec(BOR_OP_RET)
    return Case(instrs, cs, arg_slots, bytes(slots))


NATIVE_ABS_CASE = case_native(VM_NATIVE_ABS, 1, [1], [(1, int_slot(-12345))], result_slot=0)
NATIVE_ABS_INT_MIN_CASE = case_native(VM_NATIVE_ABS, 1, [1], [(1, int_slot(-0x80000000))], result_slot=0)
NATIVE_MIN_CASE = case_native(VM_NATIVE_MIN, 2, [1, 2], [(1, int_slot(7)), (2, int_slot(-3))], result_slot=0)
NATIVE_MAX_CASE = case_native(VM_NATIVE_MAX, 2, [1, 2], [(1, int_slot(7)), (2, int_slot(-3))], result_slot=0)
NATIVE_LOG_CASE = case_native(VM_NATIVE_LOG, 1, [1], [(1, int_slot(4242))], result_slot=0)
NATIVE_BAD_TYPE_CASE = case_native(VM_NATIVE_ABS, 1, [1], [(1, empty_slot())], result_slot=0)
NATIVE_BAD_ARGC_CASE = case_native(VM_NATIVE_ABS, 2, [1, 1], [(1, int_slot(5))], result_slot=0)
NATIVE_UNKNOWN_ID_CASE = case_native(99, 1, [1], [(1, int_slot(5))], result_slot=0)


def case_simple_call():
    """MAIN calls DOUBLE(21) -> 42, one level of nesting.
      MAIN  [0] CALL(a=2, b=3[result], c=0)
            [1] RET
      DOUBLE(entry 2):
            [2] PARAM a=5
            [3] ADD  a=5, b=5, c=5      -- slot5 = slot5+slot5
            [4] JUMPR a=5, b=5
            [5] RET
    """
    instrs = (rec(BOR_OP_CALL, a=2, b=3, c=0) + rec(BOR_OP_RET)
              + rec(BOR_OP_PARAM, a=5) + rec(BOR_OP_ADD, a=5, b=5, c=5)
              + rec(BOR_OP_JUMPR, a=5, b=5) + rec(BOR_OP_RET))
    cs = callsite(VM_TARGET_KIND_SCRIPT, 1, target_id=0, arg_list_index=0)
    arg_slots = struct.pack('<H', 1)   # slot1 holds the initial argument
    slots = bytearray(empty_slot() * 6)
    slots[1 * 8:1 * 8 + 8] = int_slot(21)
    return Case(instrs, cs, arg_slots, bytes(slots))


def case_nested_call():
    """MAIN calls A(7); A forwards to B, which doubles; A returns B's
    result unchanged -- exercises 2 levels of nesting. Expected result: 14.
      MAIN  [0] CALL(a=2, b=6[result], c=0[callsite: arg=slot1=7])
            [1] RET
      A(entry 2):
            [2] PARAM a=5              -- slot5 = A's own param
            [3] CALL(a=6, b=5[reuse], c=1[callsite: arg=slot5])
            [4] JUMPR a=5, b=5
            [5] RET
      B(entry 6):
            [6] PARAM a=9
            [7] ADD  a=9, b=9, c=9
            [8] JUMPR a=9, b=9
            [9] RET
    """
    instrs = (rec(BOR_OP_CALL, a=2, b=6, c=0) + rec(BOR_OP_RET)
              + rec(BOR_OP_PARAM, a=5) + rec(BOR_OP_CALL, a=6, b=5, c=1)
              + rec(BOR_OP_JUMPR, a=5, b=5) + rec(BOR_OP_RET)
              + rec(BOR_OP_PARAM, a=9) + rec(BOR_OP_ADD, a=9, b=9, c=9)
              + rec(BOR_OP_JUMPR, a=9, b=9) + rec(BOR_OP_RET))
    cs = (callsite(VM_TARGET_KIND_SCRIPT, 1, target_id=0, arg_list_index=0)   # MAIN -> A
          + callsite(VM_TARGET_KIND_SCRIPT, 1, target_id=0, arg_list_index=1))  # A -> B
    arg_slots = struct.pack('<H', 1) + struct.pack('<H', 5)
    slots = bytearray(empty_slot() * 10)
    slots[1 * 8:1 * 8 + 8] = int_slot(7)
    return Case(instrs, cs, arg_slots, bytes(slots))


def case_recursive_countdown(n):
    """COUNTDOWN(n) = 0 if n<=0, else 1+COUNTDOWN(n-1) -- telescopes to n.
    Slots: 10=n (this depth's param, later reused for the child's result),
    11=n-1 (this depth's own argument to the recursive call), 12=const 1,
    13=const 0, 14=condition scratch, 15=MAIN's own result slot,
    16=const n (MAIN's own argument to COUNTDOWN).
      MAIN   [0] CALL(a=E, b=15, c=0[callsite: arg=slot16])
             [1] RET
      COUNTDOWN(entry E=2):
             [E+0] PARAM a=10
             [E+1] LE a=14, b=10, c=13        -- cond = (n <= 0)
             [E+2] BRANCH_TRUE a=(E+7), b=14
             [E+3] SUB a=11, b=10, c=12       -- slot11 = n-1
             [E+4] CALL a=E, b=10, c=1[callsite: arg=slot11]
             [E+5] ADD a=10, b=10, c=12       -- slot10 = child_result + 1
             [E+6] JUMPR a=(E+8), b=10
             [E+7](BASE) JUMPR a=(E+8), b=13  -- return 0
             [E+8] RET
    """
    E = 2
    instrs = (rec(BOR_OP_CALL, a=E, b=15, c=0) + rec(BOR_OP_RET)
              + rec(BOR_OP_PARAM, a=10)
              + rec(BOR_OP_LE, a=14, b=10, c=13)
              + rec(BOR_OP_BRANCH_TRUE, a=E + 7, b=14)
              + rec(BOR_OP_SUB, a=11, b=10, c=12)
              + rec(BOR_OP_CALL, a=E, b=10, c=1)
              + rec(BOR_OP_ADD, a=10, b=10, c=12)
              + rec(BOR_OP_JUMPR, a=E + 8, b=10)
              + rec(BOR_OP_JUMPR, a=E + 8, b=13)
              + rec(BOR_OP_RET))
    cs = (callsite(VM_TARGET_KIND_SCRIPT, 1, target_id=0, arg_list_index=0)    # MAIN -> COUNTDOWN
          + callsite(VM_TARGET_KIND_SCRIPT, 1, target_id=0, arg_list_index=1))  # COUNTDOWN -> COUNTDOWN
    arg_slots = struct.pack('<H', 16) + struct.pack('<H', 11)
    slots = bytearray(empty_slot() * 17)
    slots[12 * 8:12 * 8 + 8] = int_slot(1)
    slots[13 * 8:13 * 8 + 8] = int_slot(0)
    slots[16 * 8:16 * 8 + 8] = int_slot(n)
    return Case(instrs, cs, arg_slots, bytes(slots))


def case_depth_overflow():
    """Unconditional self-recursion with no base case: instruction 0 calls
    itself forever. Must fault VMERR_CALL_DEPTH at exactly FrameTop==64,
    never actually writing a 65th frame (the guard check happens before any
    frame write -- see vm_call.pasm's Vm_Op_Call__script_ok)."""
    instrs = rec(BOR_OP_CALL, a=0, b=0, c=0) + rec(BOR_OP_RET)
    cs = callsite(VM_TARGET_KIND_SCRIPT, 0, target_id=0, arg_list_index=0)
    slots = empty_slot()
    return Case(instrs, cs, b'', slots)


def case_missing_param():
    """Callsite declares argc=1, but the callee issues 2 PARAMs. The first
    gets the real argument; the second must clear to EMPTY, not fault.
      MAIN  [0] CALL(a=2, b=0[unused], c=0[callsite: argc=1, arg=slot1])
            [1] RET
      FUNC(entry 2):
            [2] PARAM a=2
            [3] PARAM a=3
            [4] RET
    """
    instrs = (rec(BOR_OP_CALL, a=2, b=0, c=0) + rec(BOR_OP_RET)
              + rec(BOR_OP_PARAM, a=2) + rec(BOR_OP_PARAM, a=3) + rec(BOR_OP_RET))
    cs = callsite(VM_TARGET_KIND_SCRIPT, 1, target_id=0, arg_list_index=0)
    arg_slots = struct.pack('<H', 1)
    slots = bytearray(empty_slot() * 4)
    slots[1 * 8:1 * 8 + 8] = int_slot(99)
    return Case(instrs, cs, arg_slots, bytes(slots))


def main():
    r = Reporter('3', kind='GATE')

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        boot_status = read_block(m, VM_STATE_FIRST, 32)[VmState_Status - VM_STATE_FIRST]
        r.check(f'boot (shipped Gate 0 module) reached a terminal status '
                 f'before injection began (status={boot_status})',
                 boot_status in (VMSTAT_DONE, VMSTAT_FAULT))

        # Point the cached header-derived offsets at this gate's own fixed
        # windows, once -- every case below only rewrites window CONTENTS.
        m.write_u16(VmPriv_InstrOff, INSTR_WINDOW_OFF)
        m.write_u16(VmCall_CallsitesOff, CALLSITE_WINDOW_OFF)
        m.write_u16(VmCall_ArgSlotsOff, ARGSLOT_WINDOW_OFF)

        # --- Natives ---
        out = run_case(m, NATIVE_ABS_CASE)
        vtype, value = read_slot(m, 0)
        r.check('native abs(-12345) -> DONE, slot0 = INTEGER 12345',
                out is not None and out['status'] == VMSTAT_DONE
                and vtype == BOR_VT_INTEGER and value == 12345)

        out = run_case(m, NATIVE_ABS_INT_MIN_CASE)
        vtype, value = read_slot(m, 0)
        r.check('native abs(INT_MIN) -> DONE, slot0 = INTEGER INT_MIN (wrap, not fault)',
                out is not None and out['status'] == VMSTAT_DONE
                and vtype == BOR_VT_INTEGER and value == -0x80000000)

        out = run_case(m, NATIVE_MIN_CASE)
        vtype, value = read_slot(m, 0)
        r.check('native min(7, -3) -> DONE, slot0 = INTEGER -3',
                out is not None and out['status'] == VMSTAT_DONE
                and vtype == BOR_VT_INTEGER and value == -3)

        out = run_case(m, NATIVE_MAX_CASE)
        vtype, value = read_slot(m, 0)
        r.check('native max(7, -3) -> DONE, slot0 = INTEGER 7',
                out is not None and out['status'] == VMSTAT_DONE
                and vtype == BOR_VT_INTEGER and value == 7)

        out = run_case(m, NATIVE_LOG_CASE)
        vtype, value = read_slot(m, 0)
        log_last = read_block(m, VmNative_LogLastLo, 32)
        log_value = struct.unpack_from('<i', log_last, 0)[0]
        r.check('native log(4242) -> DONE, slot0 = INTEGER 4242, logged value = 4242',
                out is not None and out['status'] == VMSTAT_DONE
                and vtype == BOR_VT_INTEGER and value == 4242 and log_value == 4242)

        out = run_case(m, NATIVE_BAD_TYPE_CASE)
        r.check('native abs(EMPTY) -> FAULT VMERR_BAD_TYPE',
                out is not None and out['status'] == VMSTAT_FAULT and out['error'] == VMERR_BAD_TYPE)

        out = run_case(m, NATIVE_BAD_ARGC_CASE)
        r.check('native abs called with argc=2 -> FAULT VMERR_BAD_NATIVE',
                out is not None and out['status'] == VMSTAT_FAULT and out['error'] == VMERR_BAD_NATIVE)

        out = run_case(m, NATIVE_UNKNOWN_ID_CASE)
        r.check('native call to an unknown stable ID -> FAULT VMERR_BAD_NATIVE',
                out is not None and out['status'] == VMSTAT_FAULT and out['error'] == VMERR_BAD_NATIVE)

        # --- Script calls: simple, nested, return values ---
        out = run_case(m, case_simple_call())
        vtype, value = read_slot(m, 3)
        r.check('DOUBLE(21) via one CALL/PARAM/JUMPR/RET -> DONE, result slot = INTEGER 42, '
                'frames unwound to 0',
                out is not None and out['status'] == VMSTAT_DONE and out['frame_top'] == 0
                and vtype == BOR_VT_INTEGER and value == 42)

        out = run_case(m, case_nested_call())
        vtype, value = read_slot(m, 6)
        r.check('nested MAIN->A->B call (2 levels) -> DONE, result slot = INTEGER 14, '
                'frames unwound to 0',
                out is not None and out['status'] == VMSTAT_DONE and out['frame_top'] == 0
                and vtype == BOR_VT_INTEGER and value == 14)

        # --- Recursion + guard-region integrity ---
        N = 10
        out = run_case(m, case_recursive_countdown(N))
        vtype, value = read_slot(m, 15)
        r.check(f'recursive COUNTDOWN({N}) telescopes to {N} across {N} nested frames -> DONE, '
                 'frames unwound to 0',
                out is not None and out['status'] == VMSTAT_DONE and out['frame_top'] == 0
                and vtype == BOR_VT_INTEGER and value == N)
        r.check('guard regions intact after 10-deep recursion', guard_intact(m))

        # --- Missing parameter ---
        out = run_case(m, case_missing_param())
        vtype1, value1 = read_slot(m, 2)
        vtype2, _value2 = read_slot(m, 3)
        r.check('missing PARAM (argc=1, callee issues 2 PARAMs) -> DONE, '
                'slot2 = INTEGER 99 (supplied), slot3 = EMPTY (missing, not faulted)',
                out is not None and out['status'] == VMSTAT_DONE
                and vtype1 == BOR_VT_INTEGER and value1 == 99 and vtype2 == BOR_VT_EMPTY)

        # --- Depth overflow ---
        out = run_case(m, case_depth_overflow())
        r.check(f'unconditional self-recursion -> FAULT VMERR_CALL_DEPTH at FrameTop=={VM_FRAME_MAX} '
                 '(never writes a 65th frame)',
                out is not None and out['status'] == VMSTAT_FAULT and out['error'] == VMERR_CALL_DEPTH
                and out['frame_top'] == VM_FRAME_MAX)
        r.check('guard regions intact after call-depth overflow', guard_intact(m))

    r.finish()


if __name__ == '__main__':
    main()
