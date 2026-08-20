#!/usr/bin/env python3
"""plan_vm.md §2, Gate 0: fetch, dispatch, integer slots, branch, root RET.

HOST-SIDE HALF (unchanged since Gate 0/2): tools/verify/vm_fixtures/
gate0_module.bin, gate0_program.json and gate0_expected_slots.bin are a
fixed 10-instruction fixture (8 executed; JUMP skips an unreachable ERR at
IP 8) covering CONSTINT/ADD/EQ/Branch_FALSE/JUMP/RET. run_gate0_reference.py
(a from-scratch host VM, independent of oracle.py/the compiler pipeline)
must agree with the fixture's own `expected` block, and validate_fixtures.py
must confirm gate0_module.bin/gate0_program.json/gate0_expected_slots.bin
are mutually consistent, BEFORE the engine is even booted (plan_vm.md 0.7's
"the fixture is wrong, not the interpreter" rule). This is pure dispatch
coverage and has nothing to do with what actually ships at boot.

HARDWARE HALF (Task #13, 2026-08-20 -- rewritten, was previously also
pinned to gate0_module.bin). Once build_rom.py's VM_MODULE stopped being
the Gate 0 fixture (repointed at a real compiled script,
boot_spawn_wave1_module.bin, so a real openborscript module ships through
the normal MSU/Vm_Load boot path instead of only ever being WRAM-injected
by gates 1-6), asserting gate0_expected_slots.bin against real hardware
would no longer be testing what's true -- it would be asserting stale
content. Gate 0's OWN non-duplicated coverage is the boot-transport path
(MSU->WRAM, Vm_ValidateHeader, initial-slot-image copy, execution reaching
VMSTAT_DONE without fault) -- gates 1-6 already prove dispatch/opcode
correctness against arbitrary programs via direct WRAM injection, so this
half is now content-agnostic: it recompiles fixtures/boot_spawn_wave1.c
fresh (the same source-of-truth build_rom.py's packed VM_MODULE came from),
byte-compares the fresh pack against the actual VM_MODULE file on disk
(catching drift between the two independent of hardware), computes expected
final VM slots and entity-world state via oracle.py (same host interpreter
vm_gate6.py already validated against real natives), then boots the real
ROM with NO wram injection -- this is the one gate that exercises the real
MSU load, not a shortcut around it -- and diffs against the oracle.

Usage: python tools/verify/vm_gate0.py
"""
import json
import os
import re
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import (open_session, pasm_constant, pasm_constant_in, read_block,  # noqa: E402
                      repo_root_from, Reporter)

ROOT = repo_root_from(__file__)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'bor_converter'))
from openbor_script import lexer, parser, compiler, module as modpkg, oracle  # noqa: E402

CONSTS = 'src/core/vm/vm_consts.pasm'
FIXTURES = os.path.join(ROOT, 'tools', 'verify', 'vm_fixtures')
FIXTURE_SCRIPT = os.path.join(ROOT, 'tools', 'bor_converter', 'openbor_script',
                               'fixtures', 'boot_spawn_wave1.c')

VmSlots_Wram = pasm_constant_in(CONSTS, 'VmSlots_Wram')
VmGuardLo = pasm_constant_in(CONSTS, 'VmGuardLo')
VmGuardHi = pasm_constant_in(CONSTS, 'VmGuardHi')
VM_GUARD_LEN = pasm_constant_in(CONSTS, 'VM_GUARD_LEN')
VM_GUARD_LO_FILL = pasm_constant_in(CONSTS, 'VM_GUARD_LO_FILL')
VM_GUARD_HI_FILL = pasm_constant_in(CONSTS, 'VM_GUARD_HI_FILL')
VM_STATE_FIRST = pasm_constant_in(CONSTS, 'VM_STATE_FIRST')
VmState_Status = pasm_constant_in(CONSTS, 'VmState_Status')
VmState_Error = pasm_constant_in(CONSTS, 'VmState_Error')
VMSTAT_DONE = pasm_constant_in(CONSTS, 'VMSTAT_DONE')
VMSTAT_RUNNING = pasm_constant_in(CONSTS, 'VMSTAT_RUNNING')
VMERR_NONE = pasm_constant_in(CONSTS, 'VMERR_NONE')

CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_FACING_LEFT = pasm_constant('CHAR_FACING_LEFT')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
ENTITY_BASE = 0x7E0a00

# Boot defaults (main.pasm's CharacterEntity_Init__player/__role1-3): player
# spawns at (120, 150) facing right (0); all 3 AI roles boot HP=0 -- ground
# truth for the world oracle.run_oracle() needs, re-derived from source, not
# assumed.
BOOT_WORLD = {
    0: {'x': 120, 'y': 150, 'facing': 0, 'hp': 64},
    1: {'x': 0, 'y': 0, 'facing': 0, 'hp': 0},
    2: {'x': 0, 'y': 0, 'facing': 0, 'hp': 0},
    3: {'x': 0, 'y': 0, 'facing': 0, 'hp': 0},
}

SLOT_SIZE = 8
Nmi_FrameCounter = 0x7E5023


def run(cmd):
    r = subprocess.run([sys.executable, cmd], capture_output=True, text=True)
    print(r.stdout, end='')
    if r.stderr:
        print(r.stderr, end='', file=sys.stderr)
    return r.returncode == 0


def frame_counter(m):
    b = read_block(m, Nmi_FrameCounter, 32)
    return b[0] | (b[1] << 8)


def get_vm_module_path():
    with open(os.path.join(ROOT, 'build_rom.py'), encoding='utf-8') as f:
        m = re.search(r'^VM_MODULE\s*=\s*"([^"]+)"', f.read(), re.MULTILINE)
    if not m:
        print('FAIL: could not find VM_MODULE = "..." in build_rom.py')
        raise SystemExit(1)
    return os.path.join(ROOT, m.group(1))


def build_module():
    with open(FIXTURE_SCRIPT, encoding='utf-8') as f:
        src = f.read()
    toks = lexer.tokenize(src)
    program = parser.Parser(toks).parse_program()
    return compiler.compile_module(program)


def describe_slot_mismatch(got, want):
    for i in range(0, len(want), SLOT_SIZE):
        if got[i:i + SLOT_SIZE] != want[i:i + SLOT_SIZE]:
            slot_id = i // SLOT_SIZE
            gtype, gval = got[i], struct.unpack_from('<i', got, i + 4)[0]
            wtype, wval = want[i], struct.unpack_from('<i', want, i + 4)[0]
            return (f'first mismatch at slot {slot_id} (WRAM ${VmSlots_Wram + i:06X}): '
                    f'got type={gtype} value={gval}, want type={wtype} value={wval}')
    return 'identical'


def entity_addr(e):
    return ENTITY_BASE + e * CHAR_ZP_LEN


def read_world(m):
    world = {}
    for e in range(4):
        data = read_block(m, entity_addr(e), 40)
        x = data[CHAR_POS_X] | (data[CHAR_POS_X + 1] << 8)
        y = data[CHAR_POS_Y] | (data[CHAR_POS_Y + 1] << 8)
        world[e] = {'x': x, 'y': y, 'facing': data[CHAR_FACING_LEFT], 'hp': data[CHAR_HP]}
    return world


def main():
    r = Reporter('0', kind='GATE')

    print('--- host-side dispatch fixture (unchanged): reference VM, then '
          'mutual fixture consistency ---')
    if not run(os.path.join(FIXTURES, 'run_gate0_reference.py')):
        print('FAIL: the host reference VM does not agree with its own fixture. '
              'The FIXTURE is wrong -- fix that before touching the interpreter.')
        raise SystemExit(1)
    if not run(os.path.join(FIXTURES, 'validate_fixtures.py')):
        print('FAIL: gate0_module.bin / gate0_program.json / '
              'gate0_expected_slots.bin disagree with each other.')
        raise SystemExit(1)
    print()

    print('--- hardware boot-transport half: whatever module build_rom.py '
          'actually ships ---')
    vm_module_path = get_vm_module_path()
    print(f'VM_MODULE: {os.path.relpath(vm_module_path, ROOT)}')
    with open(vm_module_path, 'rb') as f:
        shipped_blob = f.read()

    fresh = build_module()
    fresh_blob = modpkg.pack_module(fresh)
    if fresh_blob != shipped_blob:
        print('FAIL: recompiling fixtures/boot_spawn_wave1.c does not '
              'byte-match the module build_rom.py actually packed -- '
              're-export it (see export_openbor_script_module.py) before '
              'trusting this gate.')
        raise SystemExit(1)
    print(f'module: {len(shipped_blob)} bytes, {fresh.entry_main} entry, '
          f'{len(fresh.instructions)} instructions, {len(fresh.slots)} slots '
          '-- fresh compile matches shipped bytes')

    oracle_result = oracle.run_oracle(fresh, {e: dict(v) for e, v in BOOT_WORLD.items()}, {})
    oracle_slots = oracle_result['slots']
    want_slots = b''.join(
        struct.pack('<BBHI', s[0], s[1] & 0xFF, s[2] & 0xFFFF, s[3] & 0xFFFFFFFF)
        for s in oracle_slots)

    with open_session(__file__) as m:
        m.reset_emulator()
        m.run_frames(120)
        m.pause()

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

        got_slots = bytes(read_block(m, VmSlots_Wram, max(32, len(want_slots))))[:len(want_slots)]
        same_slots = got_slots == want_slots
        if not same_slots:
            print('  ' + describe_slot_mismatch(got_slots, want_slots))
        r.check(f'{len(want_slots)} bytes at ${VmSlots_Wram:06X} byte-match '
                'oracle-computed final slots', same_slots)

        hw_world = read_world(m)
        # NOT the same scoping vm_gate6.py used -- that gate samples right
        # after its own injected module reaches VMSTAT_DONE, with nothing
        # else having run yet. This gate's harness convention (m.run_frames
        # (120) before ANY sampling, matching vm_gate0a.py/every other
        # gate's boot-settle pattern) means Phase 13's real spawn-table wave
        # queue and Phase 5/11's AI-seek/combat have ALSO run for real by
        # the time we read anything -- confirmed empirically (2026-08-20):
        # entities 2/3 come up alive with real spawn-table positions
        # unrelated to this module, and the player's HP drops from combat,
        # all before this gate ever samples. That's real, already-verified
        # engine behavior (Phase 5/11/13's own gates), not something Gate 0
        # should re-assert or be confused by. The one fact this gate can
        # actually attribute to the VM's own SPAWN call, robust to that
        # contamination, is that entity 1 -- Vm_NativeEng_Spawn's scan
        # starts at index 1, and it runs to VMSTAT_DONE within the first
        # frame, before Spawn_Play's own same-order scan could reach index
        # 1 -- ended up alive. Exact position is NOT re-asserted here:
        # vm_gate6.py's WRAM-injection scenario 1 already proves the SPAWN/
        # CHANGEENTITYPROP_POSITION natives place it correctly in isolation.
        vm_spawned = hw_world[1]['hp'] != 0
        if not vm_spawned:
            print(f'  hw world: {hw_world}')
        r.check('entity 1 alive (VMs own SPAWN call claimed the slot)', vm_spawned)

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
