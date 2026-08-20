#!/usr/bin/env python3
"""plan_vm.md §3, Gate 1: complete the control/no-op family and the fault
model.

Pass condition (quoted from the plan): "every ABI value 0..47 reaches either
its intended handler or an explicit, deterministic fault. No value is
silently a no-op."

Scope landed alongside this gate:
  - PJUMP (21), Branch_TRUE (37), Branch_EQUAL (38) -- real control-transfer
    handlers, not stubs.
  - The link/no-op family the host linker consumes and the runtime ignores:
    CONSTSTR (0), CONSTDBL (1), PUSH (34), POP (35), DATA (39), IMMEDIATE
    (41), DEFERRED (42), CHECKARG (44), CLEAN (45), FUNCDECL (47).
  - Module CRC32 validation (deferred from Gate 0a) -- vm_gate0a.py and this
    script's own fixture-consistency check already exercise that path
    indirectly, since it now runs on every boot.
  - Full fault capture (VmState_ErrorA/B/C, alongside the ErrorIp/ErrorOpcode
    Gate 0 already had) -- checked directly below for one fault case.

THE EXPECTED-OUTCOME TABLE BELOW IS BUILT FROM opcode_manifest.csv'S CLASSES
PLUS plan_vm.md's OWN GATE 0 (§2), GATE 1 (§3), GATE 2 (§4), AND (as of Gate 3
landing) GATE 3 (§5) IMPLEMENT LISTS -- never from vm_run.pasm's dispatch
table. That is deliberate (plan_vm.md §3's own instruction) and it matters:
§0.8 of the plan claims Gate 1 is where VMERR_UNIMPLEMENTED ($0010) "stops
being reachable for values 0..47", but that was stale even at Gate 1 -- §3's
own implement list only covered 14 of the 48 values, and Gate 0 covered 9
more. Gate 2 (plan_vm.md §4) then implemented 23 more (everything but CALL,
whose own numeric slot sits inside its range but which was genuinely still
Gate 3's job), and Gate 3 (plan_vm.md §5) finally implemented the last three
-- CALL (8), PARAM (40), JUMPR (46) -- so VMERR_UNIMPLEMENTED is at last
genuinely unreachable for every value 0..47 (see GATE3_FAULT below: this
file's own generic single-record fixture still faults all three, just with
gate-appropriate errors -- VMERR_CALL_DEPTH/VMERR_NO_CALL_FRAME -- never
VMERR_UNIMPLEMENTED again). A table built from "implemented so far" rather
than the stale §0.8 sentence is the one that is actually correct -- if you
see this script assert all 48 values reach DONE/0, that is the bug, not a
passing run. (Real per-opcode *correctness* for Gate 2's opcodes -- edge
values, wrap, div/mod-by-zero, shift normalization -- is vm_gate2.py's job,
and Gate 3's call-frame semantics -- nesting, missing arguments, return
values, natives -- is vm_gate3.py's job; this file only checks that dispatch
reaches the right handler and finishes cleanly (or faults exactly as
expected) on its own minimal fixture, its original Gate 0/1
scope, unchanged.)

MECHANISM: this project cannot cheaply rebuild+reload 50 separate ROMs, and
"run each in isolation" (the plan's own words) rules out chaining faulting
cases in one VM run anyway -- Vm_Run__noop makes any terminal status
(DONE/FAULT) permanent for the rest of that boot. So each of the 50 cases is
injected directly into the already-booted VM's WRAM (m.write_memory, while
paused) rather than shipped as 50 module builds:
  - Instruction records overwrite VmCode_Wram + instructions_offset (read
    from gate0_module.bin's own header, ground truth per §0.7 -- never
    hardcoded, never re-derived from the engine). The shipped Gate 0 module
    has 10 record slots there; every case here uses at most 2.
  - A fixed 3-slot image overwrites VmSlots_Wram every case (slot 0 EMPTY
    scratch, slots 1/2 INTEGER 2) -- ADD/EQ/Branch_EQUAL only need type-
    correct, unfaulting operands, and Branch_EQUAL's own test case never
    depends on the comparison actually landing true or false (see below).
  - VmState_Ip/Error/InstrCount/SlotCount are written, then VmState_Status
    is written LAST (READY) so the next frame's automatic `jsr Vm_Run` call
    (scpu_main_loop, once per frame regardless of this script) is what
    actually starts the case running -- matching the real per-frame contract
    instead of inventing a second entry point.

PROGRAM SHAPE PER CASE (plan_vm.md 3's advisor note, so every case is
terminal and deterministic in isolation):
  - RET (43) alone: it is already terminal.
  - JUMP/PJUMP (20/21): [op(target=1)][RET] -- unconditional, only one path.
  - Branch_FALSE/TRUE (36/37): [op(target=1, cond=slot1)][RET] -- target
    equals the fallthrough index, so the case reaches RET whichever way the
    branch resolves; the condition's actual truth value is irrelevant to
    THIS gate's pass condition (dispatch reached its handler and finished
    cleanly), and is exercised properly by Gate 0's own Branch_FALSE fixture.
  - Branch_EQUAL (38): [op(target=1, left=slot1, right=slot2)][RET] -- same
    target-equals-fallthrough trick.
  - ADD/EQ (16/26): [op(dest=0, left=slot1, right=slot2)][RET] -- needs real
    INTEGER operands to avoid VMERR_BAD_TYPE, which is why the slot image is
    fixed rather than empty.
  - Every other no-op-family opcode (0,1,2,33,34,35,39,41,42,44,45,47):
    [op][RET] -- a bare single record would fall off the end of a 1-record
    program into VMERR_BAD_JUMP, which is not what these cases test.
  - FIELD (7), ERR (15), every VMERR_UNIMPLEMENTED opcode, and the two
    out-of-ABI-range probes (48, 255): a single record. All of these fault
    immediately, so no second record ever executes.

STALE-READ GUARD: 50 sequential inject/run/read cycles in one session is
exactly the shape this project's harness has been bitten by before (a small
read returning the PREVIOUS case's value). Every read here is the full
32-byte VM_STATE_FIRST block (never a narrower read). On top of that, each
case is injected with VmState_Status = VMSTAT_READY (1) -- neither DONE (4)
nor FAULT (5), the only two values a real run of this case can end at -- and
then polled (bounded, like vm_gate0.py) until status actually leaves READY.
A stale read that kept returning the previous case's terminal status would
never observe READY in the first place and this loop would simply run out
its bound, which is reported as its own distinguishable failure rather than
silently reusing old data.

Usage: python tools/verify/vm_gate1.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant_in, read_block, repo_root_from, Reporter  # noqa: E402

ROOT = repo_root_from(__file__)
CONSTS = 'src/core/vm/vm_consts.pasm'
FIXTURES = os.path.join(ROOT, 'tools', 'verify', 'vm_fixtures')

VmCode_Wram = pasm_constant_in(CONSTS, 'VmCode_Wram')
VmSlots_Wram = pasm_constant_in(CONSTS, 'VmSlots_Wram')
VM_STATE_FIRST = pasm_constant_in(CONSTS, 'VM_STATE_FIRST')
VmState_Status = pasm_constant_in(CONSTS, 'VmState_Status')
VmState_Error = pasm_constant_in(CONSTS, 'VmState_Error')
VmState_Ip = pasm_constant_in(CONSTS, 'VmState_Ip')
VmState_InstrCount = pasm_constant_in(CONSTS, 'VmState_InstrCount')
VmState_SlotCount = pasm_constant_in(CONSTS, 'VmState_SlotCount')
VmState_ErrorA = pasm_constant_in(CONSTS, 'VmState_ErrorA')
VmState_ErrorB = pasm_constant_in(CONSTS, 'VmState_ErrorB')
VmState_ErrorC = pasm_constant_in(CONSTS, 'VmState_ErrorC')

VMSTAT_DONE = pasm_constant_in(CONSTS, 'VMSTAT_DONE')
VMSTAT_FAULT = pasm_constant_in(CONSTS, 'VMSTAT_FAULT')
VMSTAT_READY = pasm_constant_in(CONSTS, 'VMSTAT_READY')
VMERR_NONE = pasm_constant_in(CONSTS, 'VMERR_NONE')
VMERR_BAD_OPCODE = pasm_constant_in(CONSTS, 'VMERR_BAD_OPCODE')
VMERR_FIELD_OPCODE = pasm_constant_in(CONSTS, 'VMERR_FIELD_OPCODE')
VMERR_EXPLICIT_ERR = pasm_constant_in(CONSTS, 'VMERR_EXPLICIT_ERR')
VMERR_UNIMPLEMENTED = pasm_constant_in(CONSTS, 'VMERR_UNIMPLEMENTED')
VMERR_CALL_DEPTH = pasm_constant_in(CONSTS, 'VMERR_CALL_DEPTH')
VMERR_NO_CALL_FRAME = pasm_constant_in(CONSTS, 'VMERR_NO_CALL_FRAME')

with open(os.path.join(FIXTURES, 'gate0_module.bin'), 'rb') as f:
    GATE0_MODULE = f.read()
INSTRUCTIONS_OFFSET = struct.unpack_from('<I', GATE0_MODULE, 0x18)[0]
RECORDS_ADDR = VmCode_Wram + INSTRUCTIONS_OFFSET

RET = 0x2B  # BOR_OP_RET -- opcode_manifest.csv


def rec(op, a=0, b=0, c=0, flags=0):
    return struct.pack('<BBHHH', op & 0xFF, flags & 0xFF, a & 0xFFFF, b & 0xFFFF, c & 0xFFFF)


def slot(vtype, value=0):
    return struct.pack('<BBHi', vtype, 0, 0, value)


# Fixed 3-slot image for every case: 0 is ADD/EQ's scratch destination
# (overwritten by those two opcodes, ignored otherwise), 1 and 2 are
# INTEGER operands for ADD/EQ/Branch_EQUAL and a condition slot for
# Branch_FALSE/TRUE.
SLOTS = slot(0x00, 0) + slot(0x01, 2) + slot(0x01, 2)  # VT_EMPTY, VT_INTEGER x2
SLOT_COUNT = 3

# --- Gate 0 (plan_vm.md §2) implement list -- already real handlers. ---
GATE0_DONE = {2, 16, 20, 26, 33, 36, 43}  # CONSTINT ADD JUMP EQ NOOP Branch_FALSE RET
GATE0_FAULT = {7: VMERR_FIELD_OPCODE, 15: VMERR_EXPLICIT_ERR}  # FIELD ERR

# --- Gate 1 (plan_vm.md §3) implement list. ---
GATE1_CONTROL_DONE = {21, 37, 38}  # PJUMP Branch_TRUE Branch_EQUAL
GATE1_NOOP_DONE = {0, 1, 34, 35, 39, 41, 42, 44, 45, 47}
# CONSTSTR CONSTDBL PUSH POP DATA IMMEDIATE DEFERRED CHECKARG CLEAN FUNCDECL

# --- Gate 2 (plan_vm.md §4) implement list -- landed after this gate; kept
# here (not re-derived from vm_run.pasm's dispatch table, same rule as
# everything else in this file) so this script stays a valid regression
# check instead of going stale the moment Gate 2's own opcodes stopped
# faulting VMERR_UNIMPLEMENTED. CALL (8) is the one opcode in this numeric
# range Gate 2 deliberately left alone -- it's Gate 3 (plan_vm.md §5). Real
# per-opcode correctness (edge values, overflow, div/mod-by-zero, shift
# normalization, etc.) is vm_gate2.py's job, not this file's -- this file
# only needs each of these to reach DONE/VMERR_NONE with type-correct,
# non-faulting operands, matching its own "dispatch reached its handler
# and finished cleanly" pass condition.
GATE2_UNARY_INPLACE_DONE = {5, 6, 9, 10, 11}        # INC DEC POS NEG NOT: a=operand slot
GATE2_LOAD_SAVE_DONE = {3, 4}                        # LOAD SAVE: a=dest, b=source
GATE2_BINARY_INT_DONE = {12, 13, 14, 17, 18, 19,     # MUL DIV MOD SUB SHL SHR
                          22, 23, 24, 25, 27,          # GE LE LT GT NE
                          28, 29, 30, 31, 32}           # OR AND BIT_OR XOR BIT_AND

# --- Gate 3 (plan_vm.md §5) implement list -- landed after this gate,
# same "keep the historical categorization current" rule as Gate 2's own
# comment above. CALL/PARAM/JUMPR are real handlers now, but this file's
# generic per-opcode fixture (a=b=c=0, single record, no companion RET --
# see build_case's fallback branch below) was never designed to build a
# type-correct call program for them, and doesn't need to: it still reaches
# a deterministic, gate-appropriate fault, just not VMERR_UNIMPLEMENTED
# anymore.
#   - CALL(8): target=instruction 0, which is CALL itself -- a direct
#     self-recursive script call. Each pass through the loop pushes another
#     frame and jumps straight back to the same CALL record, so this
#     deterministically walks the frame stack to VM_FRAME_MAX and faults
#     VMERR_CALL_DEPTH -- a real exercise of the overflow guard, not a
#     placeholder.
#   - PARAM(40)/JUMPR(46): both require an active call frame
#     (VmState_FrameTop > 0); the root program here never called into
#     anything, so both deterministically fault VMERR_NO_CALL_FRAME.
# Real per-opcode correctness (nested/recursive frames, missing arguments,
# return values, the native table) is vm_gate3.py's job, not this file's --
# same division of labor Gate 2's own comment above already established.
GATE3_FAULT = {8: VMERR_CALL_DEPTH, 40: VMERR_NO_CALL_FRAME, 46: VMERR_NO_CALL_FRAME}

DONE_OPCODES = (GATE0_DONE | GATE1_CONTROL_DONE | GATE1_NOOP_DONE
                | GATE2_UNARY_INPLACE_DONE | GATE2_LOAD_SAVE_DONE | GATE2_BINARY_INT_DONE)
assert len(DONE_OPCODES) == 7 + 3 + 10 + 5 + 2 + 16 == 43

ALL_OPCODES = set(range(48))
UNIMPLEMENTED_OPCODES = ALL_OPCODES - DONE_OPCODES - set(GATE0_FAULT) - set(GATE3_FAULT)
assert len(UNIMPLEMENTED_OPCODES) == 48 - 43 - 2 - 3 == 0  # nothing left unimplemented

CONTROL_TARGET_1 = {20, 21}       # JUMP/PJUMP: a=target
BRANCH_COND = {36, 37}            # Branch_FALSE/TRUE: a=target, b=cond slot
BRANCH_EQUAL = {38}               # a=target, b=left slot, c=right slot
BINARY_INT = {16, 26} | GATE2_BINARY_INT_DONE  # ADD/EQ and Gate 2's binary family: a=dest, b=left, c=right


def build_case(opcode):
    """Returns (records_bytes, instr_count)."""
    if opcode == RET:
        return rec(RET), 1
    if opcode in CONTROL_TARGET_1:
        return rec(opcode, a=1) + rec(RET), 2
    if opcode in BRANCH_COND:
        return rec(opcode, a=1, b=1) + rec(RET), 2
    if opcode in BRANCH_EQUAL:
        return rec(opcode, a=1, b=1, c=2) + rec(RET), 2
    if opcode in BINARY_INT:
        return rec(opcode, a=0, b=1, c=2) + rec(RET), 2
    if opcode in GATE2_UNARY_INPLACE_DONE:
        return rec(opcode, a=1) + rec(RET), 2
    if opcode in GATE2_LOAD_SAVE_DONE:
        return rec(opcode, a=0, b=1) + rec(RET), 2
    if opcode in DONE_OPCODES:  # remaining no-op-family DONE cases
        return rec(opcode) + rec(RET), 2
    # FIELD, ERR, every VMERR_UNIMPLEMENTED opcode, and >=48 probes: a
    # single record faults immediately, no follow-up record ever runs.
    return rec(opcode), 1


def expected_outcome(opcode):
    """Returns (status_name, error) -- built from the manifest/plan lists
    above, never from vm_run.pasm."""
    if opcode in DONE_OPCODES:
        return 'DONE', VMERR_NONE
    if opcode in GATE0_FAULT:
        return 'FAULT', GATE0_FAULT[opcode]
    if opcode in GATE3_FAULT:
        return 'FAULT', GATE3_FAULT[opcode]
    if opcode in UNIMPLEMENTED_OPCODES:
        return 'FAULT', VMERR_UNIMPLEMENTED
    if opcode >= 48:
        return 'FAULT', VMERR_BAD_OPCODE
    raise AssertionError(f'opcode {opcode} not categorized')


CASES = list(range(48)) + [48, 255]
assert len(CASES) == 50


def run_case(m, opcode):
    records, instr_count = build_case(opcode)
    assert len(records) <= (144 - INSTRUCTIONS_OFFSET), \
        'case overflows the shipped module\'s 10-record instruction window'

    m.write_memory('snesMemory', RECORDS_ADDR, records.hex())
    m.write_memory('snesMemory', VmSlots_Wram, SLOTS.hex())
    m.write_u16(VmState_Ip, 0)
    m.write_u16(VmState_Error, 0)
    m.write_u16(VmState_InstrCount, instr_count)
    m.write_u16(VmState_SlotCount, SLOT_COUNT)
    # Status written LAST, and to READY (not RUNNING/DONE): the existing
    # per-frame `jsr Vm_Run` in scpu_main_loop is what actually drives this
    # case, exactly like a normal boot -- no second entry point invented.
    m.write_u8(VmState_Status, VMSTAT_READY)

    def field(state, addr, width):
        off = addr - VM_STATE_FIRST
        if width == 1:
            return state[off]
        return state[off] | (state[off + 1] << 8)

    status_byte = VMSTAT_READY
    for _ in range(30):
        m.run_frames(2)
        m.pause()
        state = read_block(m, VM_STATE_FIRST, 32)
        status_byte = field(state, VmState_Status, 1)
        if status_byte != VMSTAT_READY:
            break
    else:
        return None, None  # never left READY -- reported as its own failure

    error = field(state, VmState_Error, 2)
    return status_byte, error


def main():
    r = Reporter('1', kind='GATE')

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        boot_status = read_block(m, VM_STATE_FIRST, 32)[VmState_Status - VM_STATE_FIRST]
        r.check(f'boot (shipped Gate 0 module) reached a terminal status '
                 f'before injection began (status={boot_status})',
                 boot_status in (VMSTAT_DONE, VMSTAT_FAULT))

        mismatches = []
        for opcode in CASES:
            want_status_name, want_error = expected_outcome(opcode)
            want_status = VMSTAT_DONE if want_status_name == 'DONE' else VMSTAT_FAULT

            got_status, got_error = run_case(m, opcode)
            if got_status is None:
                mismatches.append(f'opcode {opcode}: status never left VMSTAT_READY '
                                   f'after 30 frames -- Vm_Run not being called, or a hang')
                continue
            if got_status != want_status or got_error != want_error:
                mismatches.append(
                    f'opcode {opcode}: got status={got_status} error=${got_error:04X}, '
                    f'want status={want_status} ({want_status_name}) error=${want_error:04X}')

        if mismatches:
            print(f'{len(mismatches)} of {len(CASES)} cases mismatched:')
            for line in mismatches:
                print('  ' + line)
        r.check(f'all {len(CASES)} opcode cases (0..47, 48, 255) reach their '
                f'expected (status, error) pair', not mismatches)

        # Full fault capture (plan_vm.md §3): one direct check that
        # VmState_ErrorA/B/C actually captured the faulting record's
        # operands, using ERR (15) with distinctive, unmistakable operands.
        sentinel_records = rec(15, a=0x1111, b=0x2222, c=0x3333)
        m.write_memory('snesMemory', RECORDS_ADDR, sentinel_records.hex())
        m.write_memory('snesMemory', VmSlots_Wram, SLOTS.hex())
        m.write_u16(VmState_Ip, 0)
        m.write_u16(VmState_Error, 0)
        m.write_u16(VmState_InstrCount, 1)
        m.write_u16(VmState_SlotCount, SLOT_COUNT)
        m.write_u8(VmState_Status, VMSTAT_READY)

        state = None
        for _ in range(30):
            m.run_frames(2)
            m.pause()
            state = read_block(m, VM_STATE_FIRST, 32)
            if state[VmState_Status - VM_STATE_FIRST] != VMSTAT_READY:
                break
        r.check('sentinel ERR case reached VMSTAT_FAULT before checking ErrorA/B/C',
                state is not None and state[VmState_Status - VM_STATE_FIRST] == VMSTAT_FAULT)

        def field16(addr):
            off = addr - VM_STATE_FIRST
            return state[off] | (state[off + 1] << 8)

        r.check('VmState_ErrorA captured 0x1111 at fault',
                field16(VmState_ErrorA) == 0x1111)
        r.check('VmState_ErrorB captured 0x2222 at fault',
                field16(VmState_ErrorB) == 0x2222)
        r.check('VmState_ErrorC captured 0x3333 at fault',
                field16(VmState_ErrorC) == 0x3333)

    r.finish()


if __name__ == '__main__':
    main()
