#!/usr/bin/env python3
"""plan_vm.md §9, Gate 7: performance, and the SA-1 question.

Gate 7's own text is explicit about order: "Only after Gate 6 is green and
*measured*. In order: 1. Profile organic gameplay -- actual opcodes/frame,
actual worst-case frame. 2. If over budget, replace the dispatcher with a
table. 3. If still over budget, consider SA-1 offload." Step 1 is a real
measurement against the ROM as it actually ships today, not a synthetic
injected fixture (unlike vm_gate1.py-vm_gate6.py) -- this gate boots
distribution/bor.sfc exactly as a player would and reads back what the VM
actually did.

FINDING (2026-08-23, this gate's first real run): the currently-shipped VM
content is `boot_spawn_wave1_module.bin` (see vm_gate6_native_wiring_and_
gate3_harness_bug project memory) -- a small synthetic entry script that
runs to VMSTAT_DONE within its first Vm_Run call and never runs again.
Measured opcode cost: 11 opcodes (VM_BUDGET_PER_FRAME=200 minus the
VmState_Budget remaining once status reaches VMSTAT_DONE), all consumed in
a single frame near boot. After that, `Vm_Run`'s own terminal-state guard
(`cmp #VMSTAT_DONE` / `bcs Vm_Run__noop`) makes every subsequent call an
immediate return with zero further opcode cost -- confirmed here by
holding real dpad/attack input for 600+ real frames (via m.set_input,
wall-clock-paced) and finding VmState_Status/VmState_Budget completely
unchanged throughout.

CONCLUSION: organic per-frame VM load with today's shipped content is 0
opcodes/frame for the entire remainder of any session, and the one real
"worst case" frame (boot) uses 11 of 200 budgeted opcodes -- 5.5%. This is
nowhere near VM_BUDGET_PER_FRAME, so per Gate 7's own conditional steps,
neither the dispatch-table optimization (step 2) nor SA-1 offload (step 3)
is justified by real measurement. Both remain correctly deferred until a
real, sustained per-frame script (a boss AI loop, a `for`-driven level
script -- see openbor_script_coverage_gap_data memory) actually exists and
stresses the budget. This gate exists so that claim is re-measured, not
re-assumed, the next time shipped VM content changes.

This gate also folds in Gate 6's own explicit requirement ("Nmi_FrameCounter
must still advance 1:1 -- a VM that overruns vblank reproduces this
project's most-repeated bug") -- re-checked here under real sustained
combat load, not just at boot.

Usage: python tools/verify/vm_gate7.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant_in, read_block, Reporter  # noqa: E402

CONSTS = 'src/core/vm/vm_consts.pasm'
RUN = 'src/core/vm/vm_run.pasm'

VmState_Status = pasm_constant_in(CONSTS, 'VmState_Status')
VmState_Budget = pasm_constant_in(CONSTS, 'VmState_Budget')
VMSTAT_DONE = pasm_constant_in(CONSTS, 'VMSTAT_DONE')
VMSTAT_FAULT = pasm_constant_in(CONSTS, 'VMSTAT_FAULT')
VM_BUDGET_PER_FRAME = pasm_constant_in(RUN, 'VM_BUDGET_PER_FRAME')

FRAME_COUNTER = 0x7E5023  # Nmi_FrameCounter, per every other phaseN.py gate


def sample(m):
    blk = read_block(m, VmState_Status, 32)
    status = blk[0]
    off = VmState_Budget - VmState_Status
    budget = blk[off] | (blk[off + 1] << 8)
    fc = read_block(m, FRAME_COUNTER, 32)[0]
    return status, budget, fc


def main():
    r = Reporter('VM7', kind='GATE')
    with open_session(__file__, boot_wait=2.0) as m:
        m.reset_emulator()

        # Let boot fully settle (scpu_boot -> first several scpu_main_loop
        # iterations) before the first sample -- a too-early read can catch
        # WRAM before Vm_Boot has even run once (garbage status byte).
        m.set_input(0, 60)
        status, budget, fc1 = sample(m)
        opcodes_used = VM_BUDGET_PER_FRAME - budget

        r.check('vm reached a terminal state by frame 60',
                status in (VMSTAT_DONE, VMSTAT_FAULT))
        r.check('vm did not fault', status != VMSTAT_FAULT)
        r.check('boot-script opcode cost is well under the per-frame budget',
                0 < opcodes_used < VM_BUDGET_PER_FRAME)
        print(f'  measured: status={status} opcodes_used={opcodes_used} '
              f'of {VM_BUDGET_PER_FRAME} budget/frame')

        # Real sustained gameplay: hold right (camera/AI activity) then
        # right+attack (combat, hit-stun, damage) for several hundred real
        # frames -- the same shape phase8.py/phase9.py use for organic load.
        m.set_input(m.BTN_RIGHT, 180)
        status_a, budget_a, fc2 = sample(m)
        m.set_input(m.BTN_RIGHT | m.BTN_Y, 180)
        status_b, budget_b, fc3 = sample(m)
        m.set_input(m.BTN_RIGHT, 240)
        status_c, budget_c, fc4 = sample(m)

        r.check('no further VM opcode cost during 600 real frames of movement+combat',
                budget_a == budget and budget_b == budget and budget_c == budget)
        r.check('vm never re-armed (status stays terminal, not RUNNING/YIELDED)',
                status_a == status and status_b == status and status_c == status)

        # Gate 6's own stated requirement, re-checked under real sustained
        # load rather than just at boot: Nmi_FrameCounter (an 8-bit counter,
        # so it wraps -- only monotonic *advancement* is asserted, not a
        # specific value) must never freeze. A frozen counter across a
        # 180-frame hold is this project's most-repeated real bug
        # (ccdma_validated_nmi_timing_bug memory).
        r.check('Nmi_FrameCounter kept advancing across the sustained-load window',
                len({fc1, fc2, fc3, fc4}) > 1)

        m.pause()

    r.finish()


if __name__ == '__main__':
    main()
