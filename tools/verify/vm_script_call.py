#!/usr/bin/env python3
"""VM script-to-script CALL/PARAM/JUMPR/RET codegen (plan_vm.md's Gate-7
recommendation: "the real next VM-track work is more content... or fixing
compiler.py's missing script-to-script CALL codegen" -- vm_gate7_measured_
no_action_needed project memory).

Background: the SA-1/S-CPU runtime (src/core/vm/vm_call.pasm) has fully
implemented real call frames -- CALL pushing a frame and jumping to operand
A's script entry, PARAM reading the active frame's next argument, JUMPR
staging a return value, RET popping the frame and resuming the caller --
since Gate 3 (2026-08-20), proven correct there with hand-injected callsite
records. What was missing was entirely on the HOST side:
tools/bor_converter/openbor_script/compiler.py only ever compiled the FIRST
function in a source file (as entry_main) and compile_call() only ever
emitted TARGET_KIND_NATIVE callsites -- there was no codegen path that
called a second script-declared function at all, despite the runtime
already supporting it.

This gate proves the NEW compiler support end-to-end on real hardware: a
small synthetic two-function script (see FIXTURE_SRC below) compiles for
the first time with real CALL/PARAM/JUMPR/RET between its two functions,
runs on real SA-1 hardware via the same direct-WRAM-injection mechanism
vm_gate1.py-vm_gate6.py already use, and its final state is diffed against
oracle.py -- extended this same slice with a Python call-stack so it can
interpret TARGET_KIND_SCRIPT callsites too (previously only vm_gate6.py's
single-function natives-only scripts exercised the oracle).

WHY A SYNTHETIC FIXTURE, NOT A REAL PAK SCRIPT: checked (openbor_script_
coverage_gap_data project memory) -- BOR/TMNT ship zero script content, and
DDM's own real scripts (the only scripted pak available to this project)
never call a second script-declared function; they'd also need `for` loops
and ~30 more natives before they'd compile at all. No real pak content
anywhere available to this project exercises script-to-script CALL. This
fixture is deliberately synthetic, sourced from this project's own
compiler/runtime semantics, not invented pak content.

SCOPE BOUNDARY, stated plainly: this makes script-to-script CALL/PARAM/
RET/JUMPR reachable from real compiled openborscript source. It does NOT
make any real extracted pak script compile.

FIXTURE_SRC is deliberately shaped to catch the two things a naive
implementation would get wrong silently:
  1. Both functions declare params AND locals with the SAME names (x, i,
     total) -- proves each function's local slot-name scope is really
     isolated (compiler.py's compile_program saves/restores self.m.
     slot_names per function). A fixture with distinct names would pass
     even if scoping were broken.
  2. `main` (the entry function, declared FIRST so it stays entry_main at
     IP 0 per the existing single-function convention) calls `helper`,
     which is declared SECOND -- a genuine forward reference, exercising
     the CALL.a backpatch pass (compile_program patches every pending
     script callsite's operand A to the callee's real entry IP only after
     ALL functions have compiled). A backward-reference-only fixture would
     never exercise the backpatch machinery.
  3. `helper` returns from TWO different points -- an early `return` nested
     inside a `while`+`if` (value-carrying, via JUMPR) and a trailing
     `return` at the end of the function -- both funneled through ONE
     epilogue (compile_return's epilogue_patches list), proving the
     multi-return-site-to-one-epilogue design actually works, not just a
     single trailing return.
  4. After the call returns, `main` uses its OWN `i` (999, untouched by
     `helper` having reset ITS OWN `i` to 0 internally) -- proves the
     caller's scope survives a callee that shadows the same names.

Usage: python tools/verify/vm_script_call.py
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

VmPriv_InstrOff = pasm_constant_in(RUN, 'VmPriv_InstrOff')
VmCall_CallsitesOff = pasm_constant_in(CALL, 'VmCall_CallsitesOff')
VmCall_ArgSlotsOff = pasm_constant_in(CALL, 'VmCall_ArgSlotsOff')

# Same fixed windows vm_gate3.py/vm_gate6.py already proved out.
INSTR_WINDOW_OFF = 0x1000
CALLSITE_WINDOW_OFF = 0x2000
ARGSLOT_WINDOW_OFF = 0x2800
INSTR_ADDR = VmCode_Wram + INSTR_WINDOW_OFF
CALLSITE_ADDR = VmCode_Wram + CALLSITE_WINDOW_OFF
ARGSLOT_ADDR = VmCode_Wram + ARGSLOT_WINDOW_OFF

FIXTURE_SRC = """
int main(int x, int i) {
    int total = 0;
    total = helper(x, i);
    total = total + i;
    return total;
}

int helper(int x, int i) {
    int total = 0;
    i = 0;
    while (i < x) {
        total = total + i;
        if (total > 100) {
            return total;
        }
        i = i + 1;
    }
    return total;
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
    frametop_seen_nonzero = False
    state = None
    for _ in range(60):
        m.run_frames(2)
        m.pause()
        state = read_block(m, VM_STATE_FIRST, 32)
        status_byte = field(state, VmState_Status, 1)
        if field(state, VmState_FrameTop, 2) != 0:
            frametop_seen_nonzero = True
        if status_byte not in (VMSTAT_READY, VMSTAT_RUNNING):
            break
    else:
        return None

    error = field(state, VmState_Error, 2)
    return {'status': status_byte, 'error': error, 'frametop_seen_nonzero': frametop_seen_nonzero}


def main():
    r = Reporter('VM-SCRIPT-CALL', kind='GATE')

    m_ir = build_module()
    r.check(f'compiler: two functions compiled ({len(m_ir.instructions)} instrs, '
            f'{len(m_ir.slots)} slots, {len(m_ir.callsites)} callsites)',
            len(m_ir.instructions) > 0 and len(m_ir.callsites) == 1)
    r.check('the one callsite is a real TARGET_KIND_SCRIPT call (main -> helper)',
            len(m_ir.callsites) == 1 and m_ir.callsites[0].target_kind == compiler.TARGET_KIND_SCRIPT)
    call_instr = next((ins for ins in m_ir.instructions if ins.op == compiler.OP_CALL), None)
    r.check("CALL's operand A (helper's entry IP) was backpatched to a nonzero, "
            "in-range instruction index (forward-reference resolved)",
            call_instr is not None and 0 < call_instr.a < len(m_ir.instructions))
    r.check('PARAM opcode present (helper reads its own params via a real prologue)',
            any(ins.op == compiler.OP_PARAM for ins in m_ir.instructions))
    r.check('JUMPR opcode present (helper\'s early return stages a value)',
            any(ins.op == compiler.OP_JUMPR for ins in m_ir.instructions))

    param_values = {'x': (compiler.VT_INTEGER, 20), 'i': (compiler.VT_INTEGER, 999)}
    for name, slot, _ptype in m_ir.param_names:
        if name in param_values:
            vtype, value = param_values[name]
            m_ir.slots[slot] = [vtype, 0, 0, value & 0xFFFFFFFF]

    # --- Host oracle: ground truth. helper(x=20) accumulates 0+1+...+13=91,
    # then adds i=14 -> 105 > 100, early-returns 105 (never reaches i=19/
    # total=190 the trailing-return path would have produced). main then
    # adds its OWN i (999, untouched by helper resetting ITS OWN i to 0):
    # 105 + 999 = 1104. ---
    oracle_result = oracle.run_oracle(m_ir, {}, param_values)
    oracle_slots = oracle_result['slots']
    expected_final = 105 + 999
    # compile_program restores self.m.slot_names to the entry function's
    # (main's) own scope after compiling every other function -- so at this
    # point it names exactly main's own params/locals, not helper's.
    main_total_slot = m_ir.slot_names['total']
    oracle_final = oracle_slots[main_total_slot][3] & 0xFFFFFFFF
    r.check(f"host oracle's own main.total == 105+999={expected_final} "
            f"(helper's early return at i=14 fired, not the trailing return "
            f"at i=20 which would give 190+999) -- got {oracle_final}",
            oracle_final == expected_final)

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

        r.check('VM reached DONE (not FAULT/timeout) running the real compiled two-function module',
                out is not None and out['status'] == VMSTAT_DONE)
        r.check('VmState_FrameTop was observed nonzero mid-run (the PARAM prologue really '
                'executed inside an active call frame, not skipped/faulted silently)',
                out is not None and out['frametop_seen_nonzero'])
        r.check('VmState_FrameTop back to 0 at DONE (RET popped the frame cleanly, no leak)',
                out is not None and
                field(read_block(m, VM_STATE_FIRST, 32), VmState_FrameTop, 2) == 0)

        hw_slots = read_slots(m, len(m_ir.slots)) if out is not None else None
        if hw_slots is not None:
            slot_match = all(
                hw_slots[i][0] == oracle_slots[i][0]
                and hw_slots[i][1] == (oracle_slots[i][3] & 0xFFFFFFFF)
                for i in range(len(m_ir.slots)))
            r.check(f'all {len(m_ir.slots)} final VM slots match host oracle exactly '
                    f'(proves real hardware CALL/PARAM/JUMPR/RET agrees with the oracle\'s '
                    f'call-stack model, not just "didn\'t crash")',
                    slot_match)
        else:
            r.check('all final VM slots match host oracle', False)

    r.finish()


if __name__ == '__main__':
    main()
