#!/usr/bin/env python3
"""VM `for`/`break`/`continue` codegen (plan_vm.md's VM-track next step after
script-to-script CALL -- see vm_script_to_script_call_codegen project memory).

Background: openbor_script_coverage_gap_data project memory scanned all 21
real .C scripts in the only locally-present scripted pak (Double Dragon
Moto) and found `for` loops used in 8/21 (38%) -- the single most common
missing construct after script-to-script CALL (shipped in the prior
slice). tools/bor_converter/openbor_script/'s lexer already tokenized
`for`/`break`/`continue` as keywords, but nothing downstream (parser,
compiler) handled them -- `compile_stmt` would raise CompileError on any
of the three.

No new VM opcode was needed: `for`, `break`, and `continue` all desugar
entirely into the same BRANCH_FALSE-on-a-constant-false-slot "unconditional
jump" idiom `compile_if`/`compile_while` already used, plus forward-patched
targets exactly like compile_if's/compile_program's existing patch lists
(a `loop_stack` of pending break/continue patches per active loop, so
nested loops target the correct INNERMOST loop -- see compile_for/
compile_while). `while` previously had NO break/continue support at all;
this slice added it there too, not just to the new `for` path.

WHY A SYNTHETIC FIXTURE, NOT A REAL PAK SCRIPT: DDM's own `for`-using
scripts also call ~30 engine natives this project's VM doesn't implement
yet (getentityproperty/changeentityproperty/findtarget/performattack/...),
so none of them compile end-to-end today regardless of `for` support --
confirmed by the same coverage-gap scan. This fixture is synthetic,
sourced from this project's own compiler/runtime semantics, same
disclosed-scope pattern as the script-to-script CALL gate before it.

FIXTURE_SRC exercises, deliberately:
  1. A real `for (i=0; i<n; i=i+1)` loop whose `continue` must still run the
     post-expression before re-checking the condition (real C semantics,
     the one place `for`'s continue target genuinely differs from
     `while`'s) -- proven by an accumulator that would read differently if
     `continue` skipped the increment (an infinite loop) or ran it twice.
  2. `while`'s OWN break/continue (previously entirely unsupported) inside
     the SAME function, proving both loop kinds share loop_stack correctly
     without cross-contaminating each other's patch targets.
  3. A `for` loop NESTED inside a `while` loop, each with their own
     break/continue -- proves the innermost-loop targeting in loop_stack
     is correct (a naive single-flat-target implementation would send an
     inner `continue`/`break` to the OUTER loop's target instead).

Usage: python tools/verify/vm_for_loops.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant_in, read_block, repo_root_from, Reporter  # noqa: E402

ROOT = repo_root_from(__file__)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'bor_converter'))
from openbor_script import lexer, parser, compiler, module as modpkg, oracle  # noqa: E402

CONSTS = 'src/core/vm/vm_consts.pasm'
RUN = 'src/core/vm/vm_run.pasm'
CALL = 'src/core/vm/vm_call.pasm'

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
VMSTAT_RUNNING = pasm_constant_in(CONSTS, 'VMSTAT_RUNNING')
VMSTAT_YIELDED = pasm_constant_in(CONSTS, 'VMSTAT_YIELDED')

VmPriv_InstrOff = pasm_constant_in(RUN, 'VmPriv_InstrOff')
VmCall_CallsitesOff = pasm_constant_in(CALL, 'VmCall_CallsitesOff')
VmCall_ArgSlotsOff = pasm_constant_in(CALL, 'VmCall_ArgSlotsOff')

INSTR_WINDOW_OFF = 0x1000
CALLSITE_WINDOW_OFF = 0x2000
ARGSLOT_WINDOW_OFF = 0x2800
INSTR_ADDR = VmCode_Wram + INSTR_WINDOW_OFF
CALLSITE_ADDR = VmCode_Wram + CALLSITE_WINDOW_OFF
ARGSLOT_ADDR = VmCode_Wram + ARGSLOT_WINDOW_OFF

FIXTURE_SRC = """
int main(int n) {
    int for_sum = 0;
    int i;
    for (i = 0; i < n; i = i + 1) {
        if (i == 3) { continue; }
        if (i == 7) { break; }
        for_sum = for_sum + i;
    }

    int while_sum = 0;
    int j = 0;
    while (j < n) {
        j = j + 1;
        if (j == 2) { continue; }
        if (j >= 6) { break; }
        while_sum = while_sum + j;
    }

    int nested = 0;
    int k = 0;
    while (k < 3) {
        int m = 0;
        for (m = 0; m < n; m = m + 1) {
            if (m == 2) { continue; }
            if (m >= 4) { break; }
            nested = nested + 1;
        }
        k = k + 1;
    }

    return for_sum + while_sum * 100 + nested * 10000;
}
"""


def pad(data, size):
    assert len(data) <= size, f'{len(data)} bytes does not fit a {size}-byte window'
    return data + b'\x00' * (size - len(data))


def field(state, addr, width):
    off = addr - VM_STATE_FIRST
    if width == 1:
        return state[off]
    return state[off] | (state[off + 1] << 8)


def build_module():
    toks = lexer.tokenize(FIXTURE_SRC)
    program = parser.Parser(toks).parse_program()
    return compiler.compile_module(program)


def slice_blob(m):
    packed = modpkg.pack_module(m)
    instr_bytes = b''.join(
        struct.pack('<BBHHH', ins.op & 0xFF, ins.flags & 0xFF, ins.a, ins.b, ins.c)
        for ins in m.instructions)
    slot_bytes = b''.join(
        struct.pack('<BBHI', vtype & 0xFF, flags & 0xFF, aux & 0xFFFF, value & 0xFFFFFFFF)
        for vtype, flags, aux, value in m.slots)
    callsite_bytes = b''.join(
        struct.pack('<BBHHHHH', cs.target_kind & 0xFF, cs.argc & 0xFF, cs.target_id & 0xFFFF,
                     cs.result_slot & 0xFFFF, cs.arg_list_index & 0xFFFF, cs.flags & 0xFFFF,
                     cs.debug_name_id & 0xFFFF)
        for cs in m.callsites)
    arg_slot_flat = []
    for cs in m.callsites:
        arg_slot_flat.extend(cs.arg_slot_ids)
    argslot_bytes = b''.join(struct.pack('<H', s & 0xFFFF) for s in arg_slot_flat)
    assert len(packed) >= len(instr_bytes)
    return instr_bytes, callsite_bytes, argslot_bytes, slot_bytes


def read_slots(m, count):
    slots = []
    for i in range(count):
        data = read_block(m, VmSlots_Wram + i * 8, 32)[:8]
        vtype, _flags, _aux, value = struct.unpack('<BBHi', data)
        slots.append((vtype, value & 0xFFFFFFFF))
    return slots


def run_module(m, blob, instr_count, slot_count):
    instr_bytes, callsite_bytes, argslot_bytes, slot_bytes = blob
    m.write_memory('snesMemory', INSTR_ADDR, pad(instr_bytes, 512).hex())
    m.write_memory('snesMemory', CALLSITE_ADDR, pad(callsite_bytes, 240).hex())
    m.write_memory('snesMemory', ARGSLOT_ADDR, pad(argslot_bytes, 128).hex())
    m.write_memory('snesMemory', VmSlots_Wram, pad(slot_bytes, 8192).hex())

    m.write_u16(VmState_Ip, 0)
    m.write_u16(VmState_Error, 0)
    m.write_u16(VmState_InstrCount, instr_count)
    m.write_u16(VmState_SlotCount, slot_count)
    m.write_u16(VmState_FrameTop, 0)
    m.write_u8(VmState_Status, VMSTAT_READY)

    # This fixture's real nested loops are long enough to exceed
    # VM_BUDGET_PER_FRAME (200 opcodes) within one frame -- VMSTAT_YIELDED
    # is a real, non-terminal, EXPECTED state here (Vm_Run resumes next
    # frame from where it left off), not something vm_gate3/6's shorter
    # single-frame fixtures ever produced. Only DONE/FAULT are terminal.
    status_byte = VMSTAT_READY
    state = None
    for _ in range(60):
        m.run_frames(2)
        m.pause()
        state = read_block(m, VM_STATE_FIRST, 32)
        status_byte = field(state, VmState_Status, 1)
        if status_byte not in (VMSTAT_READY, VMSTAT_RUNNING, VMSTAT_YIELDED):
            break
    else:
        return None

    error = field(state, VmState_Error, 2)
    return {'status': status_byte, 'error': error}


def main():
    r = Reporter('VM-FOR-LOOPS', kind='GATE')

    m_ir = build_module()
    r.check(f'compiler: fixture compiled ({len(m_ir.instructions)} instrs, {len(m_ir.slots)} slots)',
            len(m_ir.instructions) > 0)

    n_value = 10
    param_values = {'n': (compiler.VT_INTEGER, n_value)}
    for name, slot, _ptype in m_ir.param_names:
        if name in param_values:
            vtype, value = param_values[name]
            m_ir.slots[slot] = [vtype, 0, 0, value & 0xFFFFFFFF]

    oracle_result = oracle.run_oracle(m_ir, {}, param_values)
    oracle_slots = oracle_result['slots']

    # Hand-derived expected values (n=10), independent of the oracle:
    # for_sum: i=0..9, skip i==3, break at i==7 -> sums i=0,1,2,4,5,6 = 18
    for_sum = sum(i for i in [0, 1, 2, 4, 5, 6])
    # while_sum: j increments first each iter (1..10), skip j==2, break at j>=6
    # -> j=1,3,4,5 counted (j==2 skipped, j==6 breaks before adding)
    while_sum = 1 + 3 + 4 + 5
    # nested: outer runs k=0,1,2 (3 times); each inner for(m=0..9) skips m==2,
    # breaks at m>=4 -> counts m=0,1,3 = 3 increments per outer iter
    nested = 3 * 3
    expected_total = for_sum + while_sum * 100 + nested * 10000
    # Robust check: don't guess a specific slot -- scan for ANY oracle slot
    # holding the expected total (the return expression's own anonymous
    # result slot isn't named). This still fails loudly if the arithmetic
    # is wrong anywhere -- see the hw-vs-oracle full-slot diff below for the
    # real, exhaustive check.
    r.check(f'host oracle computes the expected combined total somewhere in its slots '
            f'(for_sum={for_sum} + while_sum({while_sum})*100 + nested({nested})*10000 = {expected_total})',
            any((v & 0xFFFFFFFF) == expected_total for _t, _f, _a, v in oracle_slots))

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        boot_status = read_block(m, VM_STATE_FIRST, 32)[VmState_Status - VM_STATE_FIRST]
        r.check(f'boot (shipped Gate 0 module) reached a terminal status before injection (status={boot_status})',
                boot_status in (VMSTAT_DONE, VMSTAT_FAULT))

        m.write_u16(VmPriv_InstrOff, INSTR_WINDOW_OFF)
        m.write_u16(VmCall_CallsitesOff, CALLSITE_WINDOW_OFF)
        m.write_u16(VmCall_ArgSlotsOff, ARGSLOT_WINDOW_OFF)

        blob = slice_blob(m_ir)
        out = run_module(m, blob, len(m_ir.instructions), len(m_ir.slots))

        r.check('VM reached DONE (not FAULT/timeout) running the real compiled for/while/break/continue module',
                out is not None and out['status'] == VMSTAT_DONE)

        hw_slots = read_slots(m, len(m_ir.slots)) if out is not None else None
        if hw_slots is not None:
            slot_match = all(
                hw_slots[i][0] == oracle_slots[i][0]
                and hw_slots[i][1] == (oracle_slots[i][3] & 0xFFFFFFFF)
                for i in range(len(m_ir.slots)))
            r.check(f'all {len(m_ir.slots)} final VM slots match host oracle exactly '
                    f'(proves real hardware for/while/break/continue agrees with the oracle, '
                    f'not just "didn\'t crash" or "didn\'t hang forever")',
                    slot_match)
            r.check(f'hardware\'s combined total slot matches the hand-derived expectation ({expected_total})',
                    any(v == expected_total for _t, v in hw_slots))
        else:
            r.check('all final VM slots match host oracle', False)
            r.check('hardware combined total matches expectation', False)

    r.finish()


if __name__ == '__main__':
    main()
