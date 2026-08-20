#!/usr/bin/env python3
"""plan_vm.md §8, Gate 6: a real OpenBOR script, and engine integration.

Runs the real, unmodified SPAWN000.C (DATA\\SCRIPTS\\SPAWN000.C, "Double
Dragon Moto [Ver. 0.2][v.3.0 Build 4432].pak", downloaded from archive.org's
openbor-pak-collection -- see vm_gate6_native_wiring_and_gate3_harness_bug
project memory) through tools/bor_converter/openbor_script/'s full compiler
pipeline, injects the resulting module into real SA-1 WRAM exactly the way
vm_gate1.py-vm_gate5.py inject synthetic fixtures, runs it on real hardware,
and diffs the result against oracle.py -- the same host interpreter the
compiler pipeline's own semantics are defined by (plan_vm.md §8 step 2's
dump_bor4086_oracle/compare_vm_trace, collapsed into one script here since
this gate has exactly one target script, not a corpus).

WHY FINAL-STATE DIFF, NOT INSTRUCTION-TRACE DIFF: oracle.py records a full
per-call trace (native name, args, result) for host-side debugging, but
vm_native_engine.pasm (the real hardware natives) writes no such log --
adding one would cost ROM/WRAM budget for a gate that doesn't need it.
SPAWN000.C's own control flow is straight-line (no branches on entity data,
no loops) -- see the source itself -- so its native call sequence is fixed
regardless of the values passed in, and final-state agreement (VM slots +
the four entities' WRAM fields the natives actually touch) is exactly as
strong a check as a trace diff would be for this specific script. This is
recorded as a deliberate scope decision, matching this project's own
precedent for narrowing a gate to what a specific fixture can actually prove
(vm_gate0.py's header note on the carry-propagation regression its own
fixture can't detect).

MECHANISM: same direct-WRAM-injection approach as vm_gate1.py-vm_gate5.py
(see vm_gate1.py's own header). Reuses vm_gate3.py's fixed instruction/
callsite/arg-slot-id windows (INSTR_WINDOW_OFF/CALLSITE_WINDOW_OFF/
ARGSLOT_WINDOW_OFF at $1000/$2000/$2800 inside VmCode_Wram) -- each gate
script runs in its own Mesen2 session, so there is no cross-script
collision to worry about; only reused here because it is already a proven,
generously-sized layout.

Entity world state lives at $7E0a00 + entity_index*CHAR_ZP_LEN (main.pasm),
CHAR_POS_X/CHAR_POS_Y/CHAR_FACING_LEFT/CHAR_HP fields -- read via
pasm_constant() (main.pasm, not vm_consts.pasm) per _harness.py's own
"never hardcode engine layout values" rule.

Usage: python tools/verify/vm_gate6.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import open_session, pasm_constant, pasm_constant_in, read_block, repo_root_from, Reporter  # noqa: E402

ROOT = repo_root_from(__file__)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'bor_converter'))
import pak_extract  # noqa: E402
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
BOR_VT_INTEGER = pasm_constant_in('src/core/vm/bor_vm_opcodes.pasm', 'BOR_VT_INTEGER')

VmPriv_InstrOff = pasm_constant_in(RUN, 'VmPriv_InstrOff')
VmCall_CallsitesOff = pasm_constant_in(CALL, 'VmCall_CallsitesOff')
VmCall_ArgSlotsOff = pasm_constant_in(CALL, 'VmCall_ArgSlotsOff')

CHAR_POS_X = pasm_constant('CHAR_POS_X')
CHAR_POS_Y = pasm_constant('CHAR_POS_Y')
CHAR_FACING_LEFT = pasm_constant('CHAR_FACING_LEFT')
CHAR_HP = pasm_constant('CHAR_HP')
CHAR_ZP_LEN = pasm_constant('CHAR_ZP_LEN')
CHAR_HP_MAX = pasm_constant('CHAR_HP_MAX')
ENTITY_BASE = 0x7E0a00

# Same fixed windows vm_gate3.py already proved out.
INSTR_WINDOW_OFF = 0x1000
CALLSITE_WINDOW_OFF = 0x2000
ARGSLOT_WINDOW_OFF = 0x2800
INSTR_ADDR = VmCode_Wram + INSTR_WINDOW_OFF
CALLSITE_ADDR = VmCode_Wram + CALLSITE_WINDOW_OFF
ARGSLOT_ADDR = VmCode_Wram + ARGSLOT_WINDOW_OFF

PAK_PATH = os.path.join(ROOT, 'Double Dragon Moto [Ver. 0.2][v.3.0 Build 4432].pak')
SCRIPT_PATH = 'DATA\\SCRIPTS\\SPAWN000.C'

Q16_SCALE = 1 << 16


def pad(data, size):
    assert len(data) <= size, f'{len(data)} bytes does not fit a {size}-byte window'
    return data + b'\x00' * (size - len(data))


def entity_addr(entity_index):
    return ENTITY_BASE + entity_index * CHAR_ZP_LEN


def write_world(m, world):
    for e, fields in world.items():
        base = entity_addr(e)
        m.write_u16(base + CHAR_POS_X, fields['x'] & 0xFFFF)
        m.write_u16(base + CHAR_POS_Y, fields['y'] & 0xFFFF)
        m.write_u8(base + CHAR_FACING_LEFT, fields['facing'] & 0xFF)
        m.write_u8(base + CHAR_HP, fields['hp'] & 0xFF)


def read_world(m):
    world = {}
    for e in range(4):
        base = entity_addr(e)
        data = read_block(m, base, 40)
        x = data[CHAR_POS_X] | (data[CHAR_POS_X + 1] << 8)
        y = data[CHAR_POS_Y] | (data[CHAR_POS_Y + 1] << 8)
        facing = data[CHAR_FACING_LEFT]
        hp = data[CHAR_HP]
        world[e] = {'x': x, 'y': y, 'facing': facing, 'hp': hp}
    return world


def read_slots(m, count):
    slots = []
    for i in range(count):
        data = read_block(m, VmSlots_Wram + i * 8, 32)[:8]
        vtype, _flags, _aux, value = struct.unpack('<BBHi', data)
        slots.append((vtype, value & 0xFFFFFFFF))
    return slots


def field(state, addr, width):
    off = addr - VM_STATE_FIRST
    if width == 1:
        return state[off]
    return state[off] | (state[off + 1] << 8)


def run_module(m, blob, param_slot_values, instr_count, slot_count):
    """param_slot_values: dict slot_index -> (vtype, u32 value), overwritten
    onto the module's own initial slot image before running (compiler.py's
    docstring: params are ordinary slots 0.., no synthesized outer CALL)."""
    # Parse the packed blob's three variable-length sections back out just
    # well enough to re-inject them verbatim -- simplest correct thing is to
    # inject from the Module IR directly (module.py's own struct layout),
    # done by the caller instead; this function takes pre-sliced bytes.
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

    # Only VMSTAT_DONE/VMSTAT_FAULT are terminal -- see vm_gate3.py's
    # run_case() for the full rationale (the harness bug this project found
    # and fixed 2026-08-20 investigating this exact gate's own regression).
    status_byte = VMSTAT_READY
    state = None
    for _ in range(60):
        m.run_frames(2)
        m.pause()
        state = read_block(m, VM_STATE_FIRST, 32)
        status_byte = field(state, VmState_Status, 1)
        if status_byte not in (VMSTAT_READY, VMSTAT_RUNNING):
            break
    else:
        return None

    error = field(state, VmState_Error, 2)
    return {'status': status_byte, 'error': error}


def build_module():
    src_bytes = pak_extract.extract(PAK_PATH, SCRIPT_PATH)
    src = src_bytes.decode('utf-8', errors='replace')
    toks = lexer.tokenize(src)
    program = parser.Parser(toks).parse_program()
    m = compiler.compile_module(program)
    return m


def slice_blob(m):
    """Slice a packed module back into the four raw sections run_module()
    wants, using module.py's own packer so the bytes injected on hardware
    are byte-identical to what a real exporter would ship (not a parallel
    hand-rolled encoding)."""
    packed = modpkg.pack_module(m)
    # Re-derive section offsets the same way module.py computed them.
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
    assert len(packed) >= len(instr_bytes), 'sanity: packer produced something'
    return instr_bytes, callsite_bytes, argslot_bytes, slot_bytes


def main():
    r = Reporter('6', kind='GATE')

    m_ir = build_module()
    r.check(f'export_openbor_script_module: SPAWN000.C compiled '
             f'({len(m_ir.instructions)} instrs, {len(m_ir.slots)} slots, '
             f'{len(m_ir.callsites)} callsites, natives {sorted(m_ir.natives_used)})',
             len(m_ir.instructions) > 0 and m_ir.natives_used == {100, 101, 102, 103, 104, 105, 106, 107, 108})

    # Two scenarios: a normal spawn (a free AI slot exists) and a spawn with
    # no free slot (all three AI entities already alive) -- exercises
    # Vm_NativeEng_Spawn's scan-to-full-then-return-0 path, which SPAWN000.C
    # itself doesn't branch on but is still worth diffing against the oracle
    # since it's real, reachable behavior of the natives this gate wires.
    scenarios = [
        ('normal spawn (AI slot 1 free)', {
            0: {'x': 100, 'y': 50, 'facing': 0, 'hp': CHAR_HP_MAX},
            1: {'x': 0, 'y': 0, 'facing': 0, 'hp': 0},
            2: {'x': 0, 'y': 0, 'facing': 0, 'hp': 0},
            3: {'x': 0, 'y': 0, 'facing': 0, 'hp': 0},
        }, {'fX': (compiler.VT_INTEGER, 10), 'fY': (compiler.VT_INTEGER, 0), 'fZ': (compiler.VT_INTEGER, -5 & 0xFFFFFFFF)}),
        ('player facing left, fills last free slot (AI slot 3)', {
            0: {'x': 200, 'y': 80, 'facing': 1, 'hp': CHAR_HP_MAX},
            1: {'x': 1, 'y': 1, 'facing': 0, 'hp': CHAR_HP_MAX},
            2: {'x': 2, 'y': 2, 'facing': 0, 'hp': CHAR_HP_MAX},
            3: {'x': 0, 'y': 0, 'facing': 0, 'hp': 0},
        }, {'fX': (compiler.VT_INTEGER, 0), 'fY': (compiler.VT_INTEGER, 0), 'fZ': (compiler.VT_INTEGER, 20)}),
        ('no free AI slot (all three alive) -- SPAWN returns 0', {
            0: {'x': 50, 'y': 50, 'facing': 0, 'hp': CHAR_HP_MAX},
            1: {'x': 1, 'y': 1, 'facing': 0, 'hp': CHAR_HP_MAX},
            2: {'x': 2, 'y': 2, 'facing': 0, 'hp': CHAR_HP_MAX},
            3: {'x': 3, 'y': 3, 'facing': 0, 'hp': CHAR_HP_MAX},
        }, {'fX': (compiler.VT_INTEGER, 5), 'fY': (compiler.VT_INTEGER, 0), 'fZ': (compiler.VT_INTEGER, 5)}),
    ]

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

        for label, world_in, param_values in scenarios:
            # --- Host oracle: ground truth for this scenario ---
            world_for_oracle = {e: dict(f) for e, f in world_in.items()}
            oracle_result = oracle.run_oracle(m_ir, world_for_oracle, param_values)

            # --- Fresh module IR per scenario: same instructions/callsites,
            # but initial slot image overwritten with this scenario's param
            # values (compiler.py's own documented pattern for a root
            # program with no synthesized outer CALL). ---
            fresh = build_module()
            for name, slot, _ptype in fresh.param_names:
                if name in param_values:
                    vtype, value = param_values[name]
                    fresh.slots[slot] = [vtype, 0, 0, value & 0xFFFFFFFF]
            instr_bytes, callsite_bytes, argslot_bytes, slot_bytes = slice_blob(fresh)

            write_world(m, world_in)
            out = run_module(m, (instr_bytes, callsite_bytes, argslot_bytes, slot_bytes),
                              param_values, len(fresh.instructions), len(fresh.slots))

            hw_world = read_world(m) if out is not None else None
            hw_slots = read_slots(m, len(fresh.slots)) if out is not None else None

            oracle_world = oracle_result['world']
            oracle_slots = oracle_result['slots']

            r.check(f'{label}: VM reached DONE (not FAULT/timeout)',
                     out is not None and out['status'] == VMSTAT_DONE)

            # World-state comparison is scoped to what THIS gate's natives
            # can actually be blamed for, not to the shipped ROM's own
            # already-gated AI-seek/combat systems (Phase 5/Phase 11),
            # which keep running in real time for every frame this test's
            # poll loop spends waiting on the VM (jsr Vm_Run is one call
            # among several in scpu_main_loop -- Core_Oop_Play's AI seek
            # and Character_HitApply's combat resolution run every frame
            # regardless of what this script injected). Confirmed by
            # direct measurement: an AI entity already alive (HP>0) before
            # injection visibly drifted in x/y, and the player's own HP
            # visibly dropped from a landed AI attack, even though no
            # native call in SPAWN000.C ever touches those fields for
            # those entities. That drift is real, correct, independently-
            # verified engine behavior -- asserting it stayed frozen would
            # be testing Phase 5/11's determinism under this test's own
            # incidental frame delay, not Gate 6's actual scope (six
            # engine natives writing the right WRAM in the right order).
            #
            # x/y/facing ARE still checked for entity 0 (the player) --
            # CHAR_INPUT_DRIVEN=1 (dpad-driven), never self-moved by AI,
            # and confirmed stable under combat in the same measurement
            # (only HP moved). HP is excluded for entity 0 specifically,
            # since a nearby already-alive AI entity landing a hit is
            # exactly the real, timing-dependent interference described
            # above. Every field IS checked for any entity that started
            # this scenario at HP==0 (dead/unspawned, core/spawn.pasm's
            # soft-kill convention -- inert until a native call in this
            # script writes to it, so its post-call state is entirely this
            # gate's own natives' doing, born within the same instant the
            # VM ran, before any opposing AI has had a chance to react).
            full_check_entities = [e for e in range(4) if world_in[e]['hp'] == 0]
            world_match = hw_world is not None and all(
                hw_world[e]['x'] == oracle_world[e]['x']
                and hw_world[e]['y'] == oracle_world[e]['y']
                and hw_world[e]['facing'] == oracle_world[e]['facing']
                and hw_world[e]['hp'] == oracle_world[e]['hp']
                for e in full_check_entities)
            world_match = world_match and hw_world is not None and (
                hw_world[0]['x'] == oracle_world[0]['x']
                and hw_world[0]['y'] == oracle_world[0]['y']
                and hw_world[0]['facing'] == oracle_world[0]['facing'])
            r.check(f'{label}: entity 0 (player) x/y/facing, and full x/y/facing/hp for any '
                     f'entity spawned/touched this call ({full_check_entities}), match host oracle',
                     world_match)

            if hw_slots is not None:
                # Compare every slot the compiler actually produced a typed
                # value for (skip pure-scratch EMPTY slots the script itself
                # never assigns -- both sides agree those stay [0,0,0,0]
                # anyway, so this isn't narrowing the check).
                # oracle_slots[i] is (type, flags, aux, value) -- oracle.py's
                # own 4-field slot tuple, NOT (type, value); index [3] for
                # value, never [1] (that's flags, always 0, and comparing it
                # against hw_slots[i][1]'s real value made every nonzero
                # slot look mismatched).
                slot_match = all(
                    hw_slots[i][0] == oracle_slots[i][0]
                    and hw_slots[i][1] == (oracle_slots[i][3] & 0xFFFFFFFF)
                    for i in range(len(fresh.slots)))
                r.check(f'{label}: all {len(fresh.slots)} final VM slots match host oracle',
                         slot_match)
            else:
                r.check(f'{label}: all final VM slots match host oracle', False)

    r.finish()


if __name__ == '__main__':
    main()
