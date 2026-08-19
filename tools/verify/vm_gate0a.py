#!/usr/bin/env python3
"""plan_vm.md §1, Gate 0a: script-VM module transport.

Proves the VM's bytecode module actually travels bor.msu -> WRAM at boot and
that its header validates. Nothing here interprets anything; Gate 0 (§2) is the
first interpreter code. Transport is gated first on purpose -- an interpreter
debugged against a module that never loaded is unfalsifiable.

GROUND TRUTH (plan_vm.md §0.7's rule). The module bytes are compared against
tools/verify/vm_fixtures/gate0_module.bin read from disk -- the very same file
build_rom.py packs into bor.msu, deliberately one file rather than a copy so the
packed bytes and the compared-against bytes cannot drift apart. The engine's own
status byte is checked too, but only AFTER the byte comparison, and it is never
the sole evidence: phase7 is the cautionary tale, where TAD reported PLAYING at
full volume for as long as it was faithfully loading pure zeros and every
engine-visible byte read perfect.

ASSERTION ORDER IS DELIBERATE (§1 step 5):
  1. Guards first. If the harness cannot see $7E/$7F at all, it fails HERE,
     distinguishably, instead of masquerading as a loader bug two assertions
     later.
  2. Module bytes, with the first differing offset printed -- "arrays differ"
     is not a usable failure message at 4am.
  3. Status/error.
  4. Liveness: the loader runs at boot under forced blank, so a hang or a vblank
     overrun introduced here is real and this is where it shows up.

Every address and constant is read from source via pasm_constant_in(); nothing
here is hardcoded. Usage: python tools/verify/vm_gate0a.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, pasm_constant_in,  # noqa: E402
                      read_block, repo_root_from, Reporter)

ROOT = repo_root_from(__file__)
CONSTS = 'src/core/vm/vm_consts.pasm'
LOADER = 'src/core/vm/vm_load.pasm'

VmCode_Wram = pasm_constant_in(CONSTS, 'VmCode_Wram')
VmGuardLo = pasm_constant_in(CONSTS, 'VmGuardLo')
VmGuardHi = pasm_constant_in(CONSTS, 'VmGuardHi')
VM_GUARD_LEN = pasm_constant_in(CONSTS, 'VM_GUARD_LEN')
VM_GUARD_LO_FILL = pasm_constant_in(CONSTS, 'VM_GUARD_LO_FILL')
VM_GUARD_HI_FILL = pasm_constant_in(CONSTS, 'VM_GUARD_HI_FILL')
VM_STATE_FIRST = pasm_constant_in(CONSTS, 'VM_STATE_FIRST')
VmState_Status = pasm_constant_in(CONSTS, 'VmState_Status')
VmState_Error = pasm_constant_in(CONSTS, 'VmState_Error')
VmState_InstrCount = pasm_constant_in(CONSTS, 'VmState_InstrCount')
VmState_SlotCount = pasm_constant_in(CONSTS, 'VmState_SlotCount')
VMSTAT_READY = pasm_constant_in(CONSTS, 'VMSTAT_READY')
VMSTAT_UNINIT = pasm_constant_in(CONSTS, 'VMSTAT_UNINIT')
VMERR_NONE = pasm_constant_in(CONSTS, 'VMERR_NONE')
VM_MODULE_SIZE = pasm_constant_in(LOADER, 'VM_MODULE_SIZE')

# build_rom.py packs this exact file; see its VM_MODULE constant.
FIXTURE = os.path.join(ROOT, 'tools', 'verify', 'vm_fixtures', 'gate0_module.bin')

Nmi_FrameCounter = 0x7E5023  # same cell phase6.py/phase8.py read


def u16(block, base, addr):
    off = addr - base
    return block[off] | (block[off + 1] << 8)


def frame_counter(m):
    b = read_block(m, Nmi_FrameCounter, 32)
    return b[0] | (b[1] << 8)


def describe_mismatch(got, want):
    """First differing offset plus both bytes, and a little context. A gate that
    only says the arrays differ makes the next person re-derive this by hand."""
    for i, (g, w) in enumerate(zip(got, want)):
        if g != w:
            lo = max(0, i - 4)
            hi = min(len(want), i + 4)
            return (f'first difference at module offset 0x{i:04X} (WRAM '
                    f'${VmCode_Wram + i:06X}): got 0x{g:02X}, want 0x{w:02X}\n'
                    f'    got  [{lo:04X}..]: ' + ' '.join(f'{b:02X}' for b in got[lo:hi]) + '\n'
                    f'    want [{lo:04X}..]: ' + ' '.join(f'{b:02X}' for b in want[lo:hi]))
    if len(got) != len(want):
        return f'lengths differ: read {len(got)}, fixture {len(want)}'
    return 'identical'


def main():
    r = Reporter('0a', kind='GATE')

    if not os.path.exists(FIXTURE):
        print(f'FAIL: fixture missing: {FIXTURE}')
        raise SystemExit(1)
    with open(FIXTURE, 'rb') as f:
        want = f.read()
    if len(want) != VM_MODULE_SIZE:
        print(f'FAIL: {FIXTURE} is {len(want)} bytes but {LOADER} says '
              f'VM_MODULE_SIZE={VM_MODULE_SIZE}. Re-sync before running this gate.')
        raise SystemExit(1)
    print(f'fixture: {os.path.relpath(FIXTURE, ROOT)} ({len(want)} bytes), '
          f'loaded to ${VmCode_Wram:06X}')

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        # --- 1. Guards. First on purpose: a harness that cannot see $7E/$7F
        # fails here rather than looking like a loader bug later. ---
        lo = read_block(m, VmGuardLo, 32)[:VM_GUARD_LEN]
        hi = read_block(m, VmGuardHi, 32)[:VM_GUARD_LEN]
        r.check(f'VmGuardLo (${VmGuardLo:06X}) is {VM_GUARD_LEN} x '
                f'${VM_GUARD_LO_FILL:02X} -- {list(lo[:4])}...',
                list(lo) == [VM_GUARD_LO_FILL] * VM_GUARD_LEN)
        r.check(f'VmGuardHi (${VmGuardHi:06X}) is {VM_GUARD_LEN} x '
                f'${VM_GUARD_HI_FILL:02X} -- {list(hi[:4])}...',
                list(hi) == [VM_GUARD_HI_FILL] * VM_GUARD_LEN)

        # --- 2. The module bytes, against the fixture on disk. ---
        got = bytes(read_block(m, VmCode_Wram, max(32, VM_MODULE_SIZE)))[:VM_MODULE_SIZE]
        same = got == want
        if not same:
            print('  ' + describe_mismatch(got, want))
        r.check(f'{VM_MODULE_SIZE} bytes at ${VmCode_Wram:06X} byte-match '
                f'gate0_module.bin', same)

        # --- 3. Status. Read as a 32-byte block and sliced: VmState_Status is
        # one byte, exactly the size the harness's stale-small-read gap applies
        # to (build.md, "Known harness gaps"). ---
        state = read_block(m, VM_STATE_FIRST, 32)
        status = state[VmState_Status - VM_STATE_FIRST]
        error = u16(state, VM_STATE_FIRST, VmState_Error)
        instr = u16(state, VM_STATE_FIRST, VmState_InstrCount)
        slots = u16(state, VM_STATE_FIRST, VmState_SlotCount)
        print(f'VmState: status={status} error=${error:04X} '
              f'instr_count={instr} slot_count={slots}')
        if status == VMSTAT_UNINIT:
            print('  NOTE: status is still VMSTAT_UNINIT, which means Vm_Load '
                  'never ran at all -- check the jsr Vm_Load call site in '
                  'scpu_boot, not the header checks.')
        r.check(f'VmState_Status == VMSTAT_READY ({VMSTAT_READY})', status == VMSTAT_READY)
        r.check(f'VmState_Error == VMERR_NONE (${VMERR_NONE:04X})', error == VMERR_NONE)

        # The two header fields Vm_ValidateHeader copies out. Ground truth is
        # the fixture's own header, not the engine's report of it.
        want_instr = want[8] | (want[9] << 8)
        want_slots = want[10] | (want[11] << 8)
        r.check(f'VmState_InstrCount == header instruction_count ({want_instr})',
                instr == want_instr)
        r.check(f'VmState_SlotCount == header slot_count ({want_slots})',
                slots == want_slots)

        # --- 4. Liveness. The load is a blocking boot-time read under forced
        # blank; a hang or a vblank overrun introduced here is real. ---
        fc0 = frame_counter(m)
        m.run_frames(120)
        m.pause()
        fc1 = frame_counter(m)
        print(f'Nmi_FrameCounter across 120 frames: {fc0} -> {fc1}')
        r.check('Nmi_FrameCounter still advancing after the boot-time VM load',
                fc1 != fc0)

    r.finish()


if __name__ == '__main__':
    main()
