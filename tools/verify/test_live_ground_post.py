"""Grounded phase-11 native provider and source-oracle contract tests."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
from source_live_ground_post_native import GroundPostFault, emit, ground_post


SYMBOLS = {name: 0x7FF000 + i * 2 for i, name in enumerate((
    "SourceWorldTick4086_Ready", "SourceWorldTick4086_State",
    "SourceWorldTick4086_Phase", "SourceWorldTick4086_Pending",
    "SourceWorldTick4086_Fault", "SourceWorldTick4086_Slot",
    "SourceWorldTick4086_TimeLo", "VmSourceWorld_Ready",
    "VmSourceWorld_Time", "VmSourceWorld_Count", "VmSourceWorld_PoolBase",
    "VmSourceWorld_SideBase", "SourceSelf4086_Ready", "SourceSelf4086_Active",
    "SourceSelf4086_Fault", "SourceSelf4086_GlobalLow", "SourceSelf4086_GlobalHigh",
    "SourceEmptyInitEnvironment4086_Models", "SourceAdjustBaseEmpty4086_RunPost",
    "SourceAdjustBaseEmpty4086_Status", "SourceCheckMove4086_Execute",
    "SourceFreeze4086_Query", "SourceFreeze4086_Ready",
    "SourceEmptyInitEnvironment4086_Query", "SourceModelEntityCopy4086_Ready",
    "SourceModelEntityCopy4086_Entities", "SourceAnimationPhysics4086_Ready",
    "SourceAnimationPhysics4086_Query", "SourceToss4086_Ready",
    "SourcePhysicsState4086_Ready", "SourceLifecycle4086_Ready",
    "SourceUpdateFrame4086_Ready", "SourcePostStationary4086_Ready",
    "SourcePostStationary4086_Status", "SourcePostStationary4086_Slot",
    "SourceGravityIdle4086_Ready", "SourceGravityIdle4086_Status",
    "SourceCheckMove4086_Status", "SOURCE_WORLD_POOL", "SOURCE_WORLD_SIDES",
    "SOURCE_WORLD_FREEZE", "SOURCE_WORLD_TOSS_TIMES", "SOURCE_ENTITY_PHYSICS",
))}


def frame(**overrides):
    values = dict(ready=True, state=2, phase=11, pending=1, fault=0,
                  world_time=20, tick_time=20, slot=7, slot_live=True,
                  binding_ent=0, falling=0, velocity_y=0, altitude=100,
                  base=100, toss_time=20, update_mark=0, frozen=False,
                  empty_geometry=True, no_adjust_base=0)
    values.update(overrides)
    return values


def run_emitted_active_predicate(*, active_falling=False, toss_time=20):
    """Execute emitted native predicate through its real post-join branch."""
    asm = emit(SYMBOLS)
    labels = {}
    aliases = {}
    code = []
    for raw in asm.splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line or line.startswith("."):
            continue
        if " = " in line:
            name, value = line.split(" = ", 1)
            if value.startswith("$"):
                aliases[name] = int(value[1:], 16)
            continue
        if line.endswith(":"):
            labels[line[:-1]] = len(code)
        else:
            code.append(line)

    # The emitted code addresses these rows at the supplied linker addresses.
    memory = {}
    slot = 7
    def memaddr(name):
        return SYMBOLS[name]
    memory[SYMBOLS["SourceWorldTick4086_Slot"]] = slot
    physics = memaddr("SOURCE_ENTITY_PHYSICS") + slot * 16
    memory[physics] = 1 if active_falling else 0
    memory[physics + 2] = memory[physics + 4] = memory[physics + 6] = 0
    pool_index = 0  # GlobalLow is $4000, so the predicate's subtraction is 0.
    memory[memaddr("SOURCE_WORLD_POOL") + pool_index + 12] = 100
    memory[memaddr("SOURCE_WORLD_POOL") + pool_index + 14] = 0
    side_index = slot * 160
    sides = memaddr("SOURCE_WORLD_SIDES") + side_index
    memory[sides + 44] = memory[sides + 46] = 0
    memory[sides + 48] = 100
    memory[sides + 50] = 0
    memory[memaddr("SOURCE_WORLD_TOSS_TIMES") + slot * 4] = toss_time & 0xFFFF
    memory[memaddr("SOURCE_WORLD_TOSS_TIMES") + slot * 4 + 2] = toss_time >> 16
    memory[SYMBOLS["VmSourceWorld_Time"]] = 20
    memory[SYMBOLS["VmSourceWorld_Time"] + 2] = 0
    memory[SYMBOLS["SourceSelf4086_GlobalLow"]] = 0x4000

    a = x = 0
    carry = zero = negative = False
    pc = labels["LiveGroundPost_AdjustBaseOK"]
    outcome = None
    steps = 0

    def operand_value(token, indexed=False):
        token = token.strip()
        if token.startswith("#"):
            return int(token[1:].replace("$", "0x"), 0)
        alias_match = __import__("re").fullmatch(r"([A-Za-z_]\w*)(?:\+([0-9]+))?", token)
        if alias_match and alias_match.group(1) in aliases:
            return memory.get(aliases[alias_match.group(1)] + int(alias_match.group(2) or 0), 0)
        match = __import__("re").fullmatch(r"\$([0-9A-Fa-f]+)(?:\+([0-9]+))?(?:\s*,x)?", token)
        if not match:
            raise AssertionError("unhandled emitted operand: " + token)
        address = int(match.group(1), 16) + int(match.group(2) or 0) + (x if indexed or token.lower().endswith(",x") else 0)
        return memory.get(address, 0)

    while steps < 200:
        steps += 1
        if pc >= len(code):
            raise AssertionError("predicate ran past emitted body")
        ins = code[pc]
        pc += 1
        op, _, arg = ins.partition(" ")
        op = op.lower()
        if op.endswith(".l"):
            op = op[:-2]
        arg = arg.strip()
        if op == "jsl":
            if "SourceAdjustBaseEmpty" in arg or "LiveGroundPost_AdjustBase" in arg:
                carry = False
            elif "SourceFreeze4086_Query" in arg or f"${SYMBOLS['SourceFreeze4086_Query']:06X}" in arg:
                a, carry = 0, False
            elif "LiveGroundPost_Gravity_Execute" in arg:
                outcome = "gravity"
                break
            else:
                raise AssertionError("unexpected external call in predicate: " + ins)
        elif op == "lda":
            a = operand_value(arg, arg.endswith(",x")) & 0xFFFF
            zero, negative = a == 0, bool(a & 0x8000)
        elif op == "sta":
            match = __import__("re").fullmatch(r"\$([0-9A-Fa-f]+)(?:\+([0-9]+))?(?:,x)?", arg)
            if match:
                address = int(match.group(1), 16) + int(match.group(2) or 0) + (x if arg.lower().endswith(",x") else 0)
            else:
                alias_match = __import__("re").fullmatch(r"([A-Za-z_]\w*)(?:\+([0-9]+))?", arg)
                if alias_match and alias_match.group(1) in aliases:
                    address = aliases[alias_match.group(1)] + int(alias_match.group(2) or 0)
                else:
                    raise AssertionError("unhandled store: " + ins)
            memory[address] = a
        elif op == "ora":
            a = (a | operand_value(arg, arg.endswith(",x"))) & 0xFFFF
            zero, negative = a == 0, bool(a & 0x8000)
        elif op == "cmp":
            value = operand_value(arg, arg.endswith(",x")) & 0xFFFF
            carry = a >= value
            zero = a == value
            negative = bool((a - value) & 0x8000)
        elif op == "sec":
            carry = True
        elif op == "clc":
            carry = False
        elif op == "sbc":
            value = operand_value(arg) & 0xFFFF
            difference = a - value - (0 if carry else 1)
            a = difference & 0xFFFF
            carry = difference >= 0
            zero, negative = a == 0, bool(a & 0x8000)
        elif op == "asl":
            carry = bool(a & 0x8000)
            a = (a << 1) & 0xFFFF
            zero, negative = a == 0, bool(a & 0x8000)
        elif op == "adc":
            value = operand_value(arg) & 0xFFFF
            total = a + value + int(carry)
            a, carry = total & 0xFFFF, total > 0xFFFF
            zero, negative = a == 0, bool(a & 0x8000)
        elif op == "tax":
            x = a
        elif op in ("bne", "beq", "bcc", "bcs", "bra", "jmp"):
            take = {"bne": not zero, "beq": zero, "bcc": not carry,
                    "bcs": carry, "bra": True, "jmp": True}[op]
            if take:
                if arg == "LiveGroundPost_ActivePending":
                    outcome = "pending"
                    break
                if arg == "LiveGroundPost_RestoreBad":
                    outcome = "bad"
                    break
                pc = labels[arg]
        elif op in (".a16", ".i16"):
            continue
        else:
            raise AssertionError("unhandled emitted instruction: " + ins)
    else:
        raise AssertionError("predicate did not terminate")
    return outcome


class LiveGroundPostTests(unittest.TestCase):
    def test_pinned_source_behavior_and_post_order(self):
        gravity = (ROOT / "src/core/vm/vm_source_gravity_idle.pasm").read_text()
        adjust = (ROOT / "src/core/vm/vm_source_adjust_base_empty.pasm").read_text()
        move = (ROOT / "src/core/vm/vm_source_check_move.pasm").read_text()
        c_gravity = (ROOT / "out/byor-motu-live-world-v1/check_gravity.c").read_text()
        c_post = (ROOT / "out/byor-motu-live-world-v1/ent_post_update.c").read_text()
        self.assertIn("if(self->toss_time <= time)", c_gravity)
        self.assertIn("self->update_mark |= 8", c_gravity)
        self.assertIn("check_gravity(e)", c_post)
        self.assertIn("check_move(e)", c_post)
        self.assertIn("adjust_base(self, &plat)", c_gravity)
        self.assertIn("SourceAdjustBaseEmpty4086_RunPost:", adjust)
        self.assertIn("SourceCheckMove4086_Execute:", move)
        self.assertIn("SourceGravityIdle4086_MarkChecked:", gravity)

    def test_grounded_inactive_frame_marks_and_updates_due_toss_even_at_no_adjust_zero(self):
        result = ground_post(**frame())
        self.assertEqual(result.status, "complete")
        self.assertEqual(set(result.writes), {"toss_time", "update_mark.bit3"})

    def test_freeze_skips_toss_update_but_source_still_marks_gravity_checked(self):
        result = ground_post(**frame(frozen=True))
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.writes, ("update_mark.bit3",))

    def test_marked_frame_is_idempotent_and_future_toss_is_preserved(self):
        result = ground_post(**frame(update_mark=8, toss_time=21))
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.writes, ())

    def test_active_air_and_landing_remain_pending_without_claiming_mark(self):
        for active in (dict(falling=1), dict(velocity_y=1), dict(altitude=99)):
            with self.subTest(active=active):
                result = ground_post(**frame(**active))
                self.assertEqual(result.status, "pending")
                self.assertEqual(result.writes, ())
                self.assertEqual(result.reason, "ACTIVE_AIR_OR_LANDING")

    def test_frozen_or_future_toss_frames_follow_source_mark_path(self):
        self.assertEqual(ground_post(**frame(velocity_y=1, frozen=True)).status,
                         "complete")
        future = ground_post(**frame(velocity_y=1, toss_time=21))
        self.assertEqual(future.status, "complete")
        self.assertEqual(future.writes, ("update_mark.bit3",))

    def test_nonnull_binding_stays_pending_and_nonempty_geometry_faults_closed(self):
        pending = ground_post(**frame(binding_ent=0x414000))
        self.assertEqual(pending.status, "pending")
        self.assertEqual(pending.reason, "BINDING_ADJUST_PROVIDER_REQUIRED")
        self.assertEqual(pending.writes, ())
        for kwargs, reason in ((dict(empty_geometry=False), "GEOMETRY_UNADMITTED"),):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(GroundPostFault, reason):
                ground_post(**frame(**kwargs))

    def test_world_phase_time_and_slot_guards(self):
        for kwargs in (dict(ready=False), dict(state=1), dict(phase=10),
                       dict(pending=0), dict(fault=1), dict(tick_time=19),
                       dict(slot=128), dict(slot_live=False)):
            with self.subTest(kwargs=kwargs), self.assertRaises(GroundPostFault):
                ground_post(**frame(**kwargs))

    def test_emitter_composes_real_operators_and_publishes_status_after_them(self):
        asm = emit(SYMBOLS)
        self.assertIn("LiveGroundPost_Run:", asm)
        self.assertIn("LiveGroundPost_Gravity_Execute:", asm)
        self.assertIn(f"jsl ${SYMBOLS['SourceAdjustBaseEmpty4086_RunPost']:06X}", asm)
        self.assertIn("jsl LiveGroundPost_Gravity_Execute", asm)
        self.assertIn(f"jsl ${SYMBOLS['SourceCheckMove4086_Execute']:06X}", asm)
        self.assertIn("lda.l $7E7A00,x", asm)
        self.assertIn("ora.l $7E7A02,x", asm)
        self.assertIn("cmp #2", asm)
        self.assertNotIn("sta.l SourceWorldTick4086_Pending", asm)
        ops = (asm.index(f"jsl ${SYMBOLS['SourceAdjustBaseEmpty4086_RunPost']:06X}"),
               asm.index("jsl LiveGroundPost_Gravity_Execute"),
               asm.index(f"jsl ${SYMBOLS['SourceCheckMove4086_Execute']:06X}"),
               asm.index("sta.l LiveGroundPost_Status"))
        self.assertEqual(ops, tuple(sorted(ops)))

    def test_emitted_ground_predicate_clears_compare_carry_before_gravity(self):
        # Every grounded equality comparison sets carry. The native success
        # join must clear that carry before the unchanged wrapper's BCS guard.
        self.assertEqual(run_emitted_active_predicate(), "gravity")

    def test_emitted_active_air_predicate_stays_pending_before_gravity_ack(self):
        self.assertEqual(run_emitted_active_predicate(active_falling=True), "pending")

    def test_real_player_callback_trymove_can_be_bound_without_faking_null(self):
        asm = emit(SYMBOLS, check_move_label="CallbackCheckMove_Execute")
        self.assertIn("jsl CallbackCheckMove_Execute", asm)
        self.assertIn("CallbackCheckMove_Execute", asm)
        with self.assertRaisesRegex(ValueError, "CHECK_MOVE_LABEL"):
            emit(SYMBOLS, check_move_label="bad label")

    def test_binding_extension_bounds_are_checked(self):
        with self.assertRaisesRegex(ValueError, "BINDING_BASE"):
            emit(SYMBOLS, binding_base=0xFFFFF0)


if __name__ == "__main__":
    unittest.main()
