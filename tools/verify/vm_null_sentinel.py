#!/usr/bin/env python3
"""VM `NULL()` sentinel codegen (plan_vm.md's VM-track, natives-coverage
sub-track -- see openbor_script_coverage_gap_data project memory).

Background: scanning all 21 real Double Dragon Moto .C scripts for what a
minimal real script needs surfaced `NULL()` used as a zero-arg sentinel
compared via ==/!= (COMMON/DODGE.C's `if (Vx != NULL())`, PLAYER.C's
`if (etime == NULL())`) -- not a real engine call. compiler.py had no
handling for it at all (`compile_call` would raise "no native specialization
registered for NULL()").

No native ID and no new opcode: VT_EMPTY is already the VM's own "no value"
slot type (q16_truthy already treats it as falsy, proven since Gate 5), so
`NULL()` compiles to a fresh EMPTY slot the same compile-time link/
materialize way IntLit/FloatLit/StringLit already do -- zero runtime
instructions, matching CONSTINT's own "link/no-op" semantics per
opcode_manifest.csv. See compiler.py's compile_call for the actual fix.

WHY A SYNTHETIC FIXTURE, NOT A REAL PAK SCRIPT: same disclosed-scope
pattern as the for-loop and script-call gates before it -- DODGE.C/
PLAYER.C also need engine natives (getentityproperty("velocity"),
setentityvar, ...) this project's VM doesn't implement yet, so neither
compiles end-to-end regardless of NULL() support.

FIXTURE_SRC exercises: a slot initialized to a real value being compared
`!= NULL()` (must take the true branch), and separately `== NULL()`
against that same nonzero value (must NOT take the true branch) -- so a
mistake that makes NULL() equal to any placeholder nonzero sentinel, or a
mistake that fails to keep it distinct from a real 0-valued VT_INTEGER,
would show up as a wrong final value.

Usage: python tools/verify/vm_null_sentinel.py
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
int main() {
    int etime = 5;
    int flag_ne = 0;
    if (etime != NULL()) {
        flag_ne = 1;
    }
    int flag_eq = 0;
    if (etime == NULL()) {
        flag_eq = 1;
    }
    return flag_ne * 10 + flag_eq;
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
    r = Reporter('VM-NULL-SENTINEL', kind='GATE')

    m_ir = build_module()
    r.check(f'compiler: fixture compiled ({len(m_ir.instructions)} instrs, {len(m_ir.slots)} slots)',
            len(m_ir.instructions) > 0)

    oracle_result = oracle.run_oracle(m_ir, {}, {})
    oracle_slots = oracle_result['slots']

    expected = 10  # flag_ne=1 (etime != NULL() true), flag_eq=0 (etime == NULL() false)
    r.check(f'host oracle computes the expected value ({expected}) somewhere in its slots '
            f'(proves NULL() != a real nonzero value, and != NULL() correctly distinguishes it)',
            any((v & 0xFFFFFFFF) == expected for _t, _f, _a, v in oracle_slots))

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

        r.check('VM reached DONE (not FAULT/timeout) running the real compiled NULL() module',
                out is not None and out['status'] == VMSTAT_DONE)

        hw_slots = read_slots(m, len(m_ir.slots)) if out is not None else None
        if hw_slots is not None:
            slot_match = all(
                hw_slots[i][0] == oracle_slots[i][0]
                and hw_slots[i][1] == (oracle_slots[i][3] & 0xFFFFFFFF)
                for i in range(len(m_ir.slots)))
            r.check(f'all {len(m_ir.slots)} final VM slots match host oracle exactly',
                    slot_match)
            r.check(f'hardware\'s result slot matches the hand-derived expectation ({expected})',
                    any(v == expected for _t, v in hw_slots))
        else:
            r.check('all final VM slots match host oracle', False)
            r.check('hardware result matches expectation', False)

    r.finish()


if __name__ == '__main__':
    main()
