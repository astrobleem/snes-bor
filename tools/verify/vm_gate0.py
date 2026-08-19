#!/usr/bin/env python3
"""plan_vm.md §2, Gate 0: fetch, dispatch, integer slots, branch, root RET.

Scope is exactly tools/verify/vm_fixtures/gate0_program.json: 10 instructions,
8 of them executed (JUMP skips the unreachable ERR at IP 8), covering
CONSTINT/ADD/EQ/Branch_FALSE/JUMP/RET.

GROUND TRUTH (§0.7's rule, and §2's own "run the host oracle first" order):
  1. The host reference VM (run_gate0_reference.py) must independently agree
     with gate0_program.json's `expected` block before the engine is even
     booted -- if that disagrees, the FIXTURE is wrong, not the interpreter.
  2. validate_fixtures.py must confirm gate0_module.bin, gate0_program.json
     and gate0_expected_slots.bin are all mutually consistent.
  3. Only then does this script assert the real ROM against
     gate0_expected_slots.bin (the file, not a checksum) and the fixture's
     own `executed_trace`.

Assertion order matters (§2's "Gate" section): status/error first (cheap,
catches a hang or a completely wrong run immediately), then the full 40-byte
slot region byte-compared with the first differing offset reported on
mismatch, then the trace ring reconstructed from VmState_TraceHead and
compared entry-by-entry against the fixture's executed_trace, then both guard
regions.

Two failure signatures §2 calls out by name, so a real hit reads as
recognition instead of a fresh investigation:
  - Slots right, trace wrong: the IP exit contract (a handler both assigning
    IP and falling through to Vm_Next).
  - One slot's high word wrong, low word right: carry propagation in the
    32-bit ADD.

Usage: python tools/verify/vm_gate0.py
"""
import json
import os
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant_in, read_block,  # noqa: E402
                      repo_root_from, Reporter)

ROOT = repo_root_from(__file__)
CONSTS = 'src/core/vm/vm_consts.pasm'
FIXTURES = os.path.join(ROOT, 'tools', 'verify', 'vm_fixtures')

VmSlots_Wram = pasm_constant_in(CONSTS, 'VmSlots_Wram')
VmGuardLo = pasm_constant_in(CONSTS, 'VmGuardLo')
VmGuardHi = pasm_constant_in(CONSTS, 'VmGuardHi')
VM_GUARD_LEN = pasm_constant_in(CONSTS, 'VM_GUARD_LEN')
VM_GUARD_LO_FILL = pasm_constant_in(CONSTS, 'VM_GUARD_LO_FILL')
VM_GUARD_HI_FILL = pasm_constant_in(CONSTS, 'VM_GUARD_HI_FILL')
VM_STATE_FIRST = pasm_constant_in(CONSTS, 'VM_STATE_FIRST')
VmState_Status = pasm_constant_in(CONSTS, 'VmState_Status')
VmState_Error = pasm_constant_in(CONSTS, 'VmState_Error')
VmState_TraceHead = pasm_constant_in(CONSTS, 'VmState_TraceHead')
VmTrace_Wram = pasm_constant_in(CONSTS, 'VmTrace_Wram')
VMSTAT_DONE = pasm_constant_in(CONSTS, 'VMSTAT_DONE')
VMSTAT_RUNNING = pasm_constant_in(CONSTS, 'VMSTAT_RUNNING')
VMERR_NONE = pasm_constant_in(CONSTS, 'VMERR_NONE')

SLOT_SIZE = 8
TRACE_ENTRY_SIZE = 4
TRACE_RING_LEN = 32

Nmi_FrameCounter = 0x7E5023


def run(cmd):
    r = subprocess.run([sys.executable, cmd], capture_output=True, text=True)
    print(r.stdout, end='')
    if r.stderr:
        print(r.stderr, end='', file=sys.stderr)
    return r.returncode == 0


def describe_slot_mismatch(got, want, program):
    names = {s['a']: s.get('name', '') for s in program['instructions']}
    for i in range(0, len(want), SLOT_SIZE):
        if got[i:i + SLOT_SIZE] != want[i:i + SLOT_SIZE]:
            slot_id = i // SLOT_SIZE
            gtype, gval = got[i], struct.unpack_from('<i', got, i + 4)[0]
            wtype, wval = want[i], struct.unpack_from('<i', want, i + 4)[0]
            return (f'first mismatch at slot {slot_id} (WRAM ${VmSlots_Wram + i:06X}): '
                    f'got type={gtype} value={gval}, want type={wtype} value={wval}')
    return 'identical'


def frame_counter(m):
    b = read_block(m, Nmi_FrameCounter, 32)
    return b[0] | (b[1] << 8)


def main():
    r = Reporter('0', kind='GATE')

    print('--- host oracle, then fixture self-consistency (must both pass '
          'before the engine is trusted) ---')
    if not run(os.path.join(FIXTURES, 'run_gate0_reference.py')):
        print('FAIL: the host reference VM does not agree with its own fixture. '
              'The FIXTURE is wrong -- fix that before touching the interpreter.')
        raise SystemExit(1)
    if not run(os.path.join(FIXTURES, 'validate_fixtures.py')):
        print('FAIL: gate0_module.bin / gate0_program.json / '
              'gate0_expected_slots.bin disagree with each other.')
        raise SystemExit(1)
    print()

    with open(os.path.join(FIXTURES, 'gate0_program.json'), encoding='utf-8') as f:
        program = json.load(f)
    with open(os.path.join(FIXTURES, 'gate0_expected_slots.bin'), 'rb') as f:
        want_slots = f.read()

    expected = program['expected']
    expected_trace = expected['executed_trace']
    slot_count = program['slot_count']
    assert len(want_slots) == slot_count * SLOT_SIZE

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

        # Status/error first, cheap and immediately distinguishing a hang or
        # a badly-wrong run from a real mismatch.
        status = 0
        for _ in range(180):
            m.pause()
            state = read_block(m, VM_STATE_FIRST, 32)
            status = state[VmState_Status - VM_STATE_FIRST]
            if status != VMSTAT_RUNNING:
                break
            m.run_frames(1)
        else:
            print('  NOTE: status never left VMSTAT_RUNNING after 180 frames -- '
                  'a real hang, or Vm_Run is not being called (check the '
                  'jsr Vm_Boot / jsr Vm_Run call sites in main.pasm).')

        state = read_block(m, VM_STATE_FIRST, 32)
        status = state[VmState_Status - VM_STATE_FIRST]
        error = state[VmState_Error - VM_STATE_FIRST] | (state[VmState_Error - VM_STATE_FIRST + 1] << 8)
        print(f'VmState: status={status} error=${error:04X}')
        r.check(f'VmState_Status == VMSTAT_DONE ({VMSTAT_DONE})', status == VMSTAT_DONE)
        r.check(f'VmState_Error == VMERR_NONE (${VMERR_NONE:04X})', error == VMERR_NONE)

        # Slots: the gate. All 40 bytes, byte-compared against the fixture
        # file, never a spot-check of one slot.
        got_slots = bytes(read_block(m, VmSlots_Wram, max(32, len(want_slots))))[:len(want_slots)]
        same_slots = got_slots == want_slots
        if not same_slots:
            print('  ' + describe_slot_mismatch(got_slots, want_slots, program))
        r.check(f'{len(want_slots)} bytes at ${VmSlots_Wram:06X} byte-match '
                f'gate0_expected_slots.bin', same_slots)

        # Trace ring: reconstruct execution order from TraceHead, since the
        # ring wraps (not exercised at 8 entries into a 32-entry ring, but
        # written correctly regardless -- Gate 1's fault fixtures use it).
        head = state[VmState_TraceHead - VM_STATE_FIRST]
        n_executed = len(expected_trace)
        ring = bytes(read_block(m, VmTrace_Wram, TRACE_RING_LEN * TRACE_ENTRY_SIZE))
        start = (head - n_executed) % TRACE_RING_LEN
        got_trace = []
        for i in range(n_executed):
            off = ((start + i) % TRACE_RING_LEN) * TRACE_ENTRY_SIZE
            ip = ring[off] | (ring[off + 1] << 8)
            opcode = ring[off + 2]
            got_trace.append([ip, opcode])
        print(f'trace (TraceHead={head}): {got_trace}')
        trace_ok = got_trace == expected_trace
        if not trace_ok:
            print(f'  expected: {expected_trace}')
            print('  NOTE: if the slots check above passed but this did not, see '
                  'plan_vm.md 2\'s "Slots right, trace wrong" -- a handler is '
                  'both assigning IP and falling through to Vm_Next.')
        r.check(f'executed trace matches fixture ({n_executed} entries)', trace_ok)

        # Guards, last (cheap, and a corrupted guard after a real run is its
        # own finding regardless of what else passed or failed).
        lo = read_block(m, VmGuardLo, 32)[:VM_GUARD_LEN]
        hi = read_block(m, VmGuardHi, 32)[:VM_GUARD_LEN]
        r.check(f'VmGuardLo still {VM_GUARD_LEN} x ${VM_GUARD_LO_FILL:02X}',
                list(lo) == [VM_GUARD_LO_FILL] * VM_GUARD_LEN)
        r.check(f'VmGuardHi still {VM_GUARD_LEN} x ${VM_GUARD_HI_FILL:02X}',
                list(hi) == [VM_GUARD_HI_FILL] * VM_GUARD_LEN)

        fc0 = frame_counter(m)
        m.run_frames(60)
        m.pause()
        fc1 = frame_counter(m)
        r.check('Nmi_FrameCounter still advancing after the run', fc1 != fc0)

    r.finish()


if __name__ == '__main__':
    main()
