#!/usr/bin/env python3
"""VM `openborconstant()` codegen (plan_vm.md's VM-track, natives-coverage
sub-track -- see vm_null_sentinel_and_natives_scoping project memory).

Background: DDM's real scripts call `openborconstant("ATK_NORMAL7")`,
`openborconstant("ANI_WALKOFF")`, etc. -- a runtime string lookup in real
OpenBOR (engine/source/openborscript/constants.c) against the engine's own
compiled-in enum/bitflag values. This project sourced the real values
directly from DCurrent/openbor (the current OpenBOR engine repo -- ANI_*/
ATK_*/TYPE_* enum orderings are a long-standing engine ABI mod authors
depend on, not expected to drift across versions) into
tools/bor_converter/openbor_script/openbor_constants_table.py, then folds
`openborconstant(name)` to a compile-time VT_INTEGER literal for any name
in that table -- exact, not an approximation, since the source values are
real fixed enum members/bitflags, not guesses.

Real per-model DYNAMIC names (ANI_FOLLOW57, ATK_NORMAL11+, etc. -- see the
constants table's own docstring) and mutable runtime globals
(PLAYER_MIN_Z/MAX_Z) are deliberately NOT in the table and compile_call()
raises CompileError for them rather than silently returning a wrong
number -- proven separately by a plain unit check in this project's dev
loop, not a hardware gate (there's no VM behavior to verify for a
compile-time rejection).

WHY A SYNTHETIC FIXTURE, NOT A REAL PAK SCRIPT: same disclosed-scope
pattern as every other slice of this track -- DDM's own openborconstant()
callsites live in scripts (STORY.C, KUNIO.C, ...) that also need engine
natives/state (velocity, entity vars, globals) this VM doesn't implement,
so none compile end-to-end yet regardless of this slice.

FIXTURE_SRC sums three real, distinct constants from three different
source enums (ATK_NORMAL7=11 from e_attack_types, TYPE_ENEMY=8 from the
e_entity_type bitflags, ANI_WALKOFF=171 from e_animations) into one
result -- a wrong value in any one of the three tables, or the wrong enum
member being folded, shows up as a wrong total, not silently.

Usage: python tools/verify/vm_openbor_constant.py
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
    int a = openborconstant("ATK_NORMAL7");
    int b = openborconstant("TYPE_ENEMY");
    int c = openborconstant("ANI_WALKOFF");
    return a + b + c;
}
"""

EXPECTED = 11 + 8 + 171  # ATK_NORMAL7=11 (e_attack_types), TYPE_ENEMY=8 (bitflag), ANI_WALKOFF=171 (e_animations)


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
    r = Reporter('VM-OPENBORCONSTANT', kind='GATE')

    m_ir = build_module()
    r.check(f'compiler: fixture compiled ({len(m_ir.instructions)} instrs, {len(m_ir.slots)} slots)',
            len(m_ir.instructions) > 0)
    r.check('compiler emitted ZERO runtime instructions for the 3 openborconstant() calls '
            '(pure compile-time literal fold, no native ID / CALL opcode)',
            len(m_ir.callsites) == 0)

    oracle_result = oracle.run_oracle(m_ir, {}, {})
    oracle_slots = oracle_result['slots']
    r.check(f'host oracle computes the expected sourced total ({EXPECTED} = ATK_NORMAL7(11) + '
            f'TYPE_ENEMY(8) + ANI_WALKOFF(171)) somewhere in its slots',
            any((v & 0xFFFFFFFF) == EXPECTED for _t, _f, _a, v in oracle_slots))

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

        r.check('VM reached DONE (not FAULT/timeout) running the real compiled openborconstant() module',
                out is not None and out['status'] == VMSTAT_DONE)

        hw_slots = read_slots(m, len(m_ir.slots)) if out is not None else None
        if hw_slots is not None:
            slot_match = all(
                hw_slots[i][0] == oracle_slots[i][0]
                and hw_slots[i][1] == (oracle_slots[i][3] & 0xFFFFFFFF)
                for i in range(len(m_ir.slots)))
            r.check(f'all {len(m_ir.slots)} final VM slots match host oracle exactly',
                    slot_match)
            r.check(f'hardware\'s result slot matches the sourced expectation ({EXPECTED})',
                    any(v == EXPECTED for _t, v in hw_slots))
        else:
            r.check('all final VM slots match host oracle', False)
            r.check('hardware result matches expectation', False)

    r.finish()


if __name__ == '__main__':
    main()
