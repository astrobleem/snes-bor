"""Execute the emitted dispatcher in a small 65816 instruction VM with spies."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
from source_live_world_dispatch_native import emit


SYMBOLS = {
    "SourceWorldTick4086_Poll": 0x9000,
    "SourceWorldTick4086_Ack": 0x9003,
    "SourceWorldTick4086_Phase": 0x7FFA_F2,
}


class WorldSpy:
    def __init__(self, phases, outcomes=None, mutations=None, mode_mutations=None):
        self.phases = list(phases)
        self.index = 0
        self.outcomes = {k: list(v) for k, v in (outcomes or {}).items()}
        self.mutations = dict(mutations or {})
        self.mode_mutations = dict(mode_mutations or {})
        self.phase_override = None
        self.trace = []
        self.phase = self.phases[0] if self.phases else 0

    def poll(self, vm):
        self.phase = self.phase_override if self.phase_override is not None else (
            self.phases[self.index] if self.index < len(self.phases) else 0)
        self.trace.append(("poll", self.phase))
        return self.phase, False

    def ack(self, vm, phase):
        self.trace.append(("ack", phase))
        current = self.phase_override if self.phase_override is not None else (
            self.phases[self.index] if self.index < len(self.phases) else 0)
        if self.index >= len(self.phases) or phase != current:
            return 1, True
        self.index += 1
        self.phase_override = None
        return 0, False

    def provider(self, vm, phase):
        outcome = self.outcomes.get(phase, [0])
        result = outcome.pop(0) if outcome else 0
        self.trace.append(("provider", phase, vm.x, vm.y))
        # Deliberately destroy the volatile context to verify wrapper restoration.
        vm.x, vm.y, vm.dbr, vm.dp = 0xEEEE, 0xDDDD, 0xAA, 0xBBBB
        # Native providers preserve M/X and return a 16-bit A status; C alone
        # reports fault. Optional mode mutation injects an ABI violation.
        vm.p = (vm.p & ~1) | int(result == "fault")
        if self.mode_mutations.get(phase) == "m8":
            vm.p |= 0x20
        if phase in self.mutations:
            self.phase_override = self.mutations[phase]
            self.trace.append(("mutate-phase", phase, self.phase_override))
        return (0, True) if result == "fault" else (result, False)


class Tiny65816:
    """Execute the emitted branch/call subset, with native services as spies."""
    def __init__(self, asm, world, provider_phases):
        self.world = world
        self.provider_phases = provider_phases
        self.pc = 0
        self.a, self.x, self.y = 0, 0x1357, 0x2468
        self.dbr, self.dp, self.p = 0x42, 0xBEEF, 0x0134
        self.stack = []
        self.carry = False
        self.phase_mem = 0
        self.pop_widths = []
        self.ops = []
        self.labels = {}
        for raw in asm.splitlines():
            line = raw.split(";", 1)[0].strip()
            if not line or line.startswith("."):
                continue
            if line.endswith(":"):
                self.labels[line[:-1].lower()] = len(self.ops)
            else:
                self.ops.append(line.lower())
        self.external = {SYMBOLS["SourceWorldTick4086_Poll"]: "poll",
                         SYMBOLS["SourceWorldTick4086_Ack"]: "ack"}
        self.external.update({label.lower(): phase for phase, label in provider_phases.items()})

    def _stack_word(self, byte_offset):
        offset = 0
        for item in reversed(self.stack):
            size = 2 if item[0] in ("word", "dp") else 1
            if offset <= byte_offset < offset + size:
                return item[1]
            offset += size
        raise AssertionError(("bad stack offset", byte_offset, self.stack))

    @staticmethod
    def _number(text):
        text = text.removeprefix("#")
        return int(text[1:], 16) if text.startswith("$") else int(text)

    def run(self, limit=1000):
        while self.pc < len(self.ops) and limit:
            limit -= 1
            op = self.ops[self.pc]
            self.pc += 1
            parts = op.split()
            ins = parts[0]
            arg = parts[1] if len(parts) > 1 else ""
            if ins in ("php", "phb", "phd", "phx", "phy"):
                value = {"php": self.p, "phb": self.dbr, "phd": self.dp,
                         "phx": self.x, "phy": self.y}[ins]
                byte_sized = ins in ("php", "phb") or (ins in ("phx", "phy") and self.p & 0x10)
                self.stack.append(("byte" if byte_sized else "dp" if ins == "phd" else "word", value))
            elif ins in ("plp", "plb", "pld", "plx", "ply"):
                item, value = self.stack.pop()
                expected_byte = ins in ("plp", "plb") or (ins in ("plx", "ply") and self.p & 0x10)
                actual_byte = item == "byte"
                self.pop_widths.append(1 if actual_byte else 2)
                if expected_byte != actual_byte:
                    raise AssertionError(("stack width mismatch", ins, expected_byte, item))
                if ins == "plp": self.p = value
                elif ins == "plb": self.dbr = value
                elif ins == "pld": self.dp = value
                elif ins == "plx": self.x = value
                else: self.y = value
            elif ins == "rep":
                self.p &= ~self._number(arg)
            elif ins == "sep":
                self.p |= self._number(arg)
            elif ins == "lda":
                if arg.endswith(",s"):
                    self.a = self._stack_word(int(arg[:-2]) - 1)
                elif arg.startswith("#"):
                    self.a = self._number(arg)
                elif arg.startswith("$") or arg.isdigit() or arg.startswith("$"):
                    addr = self._number(arg)
                    self.a = self.phase_mem if addr == SYMBOLS["SourceWorldTick4086_Phase"] else 0
                else:
                    self.a = self.phase_mem
            elif ins == "lda.l":
                addr = self._number(arg)
                self.a = self.phase_mem if addr == SYMBOLS["SourceWorldTick4086_Phase"] else 0
            elif ins == "cmp":
                v = self._number(arg)
                self.carry = self.a >= v
                self.equal = self.a == v
            elif ins == "and":
                self.a &= self._number(arg)
                self.equal = self.a == 0
            elif ins in ("tax", "tay"):
                if ins == "tax": self.x = self.a
                else: self.y = self.a
            elif ins == "txa":
                self.a = self.x
            elif ins == "pla":
                item, value = self.stack.pop()
                if item != "byte":
                    raise AssertionError(("PLA width mismatch", item))
                self.pop_widths.append(1)
                self.a = (self.a & 0xFF00) | (value & 0xFF)
            elif ins in ("beq", "bne", "bcs", "bcc"):
                take = {"beq": self.equal, "bne": not self.equal,
                        "bcs": self.carry, "bcc": not self.carry}[ins]
                if take: self.pc = self.labels[arg]
            elif ins == "jmp":
                self.pc = self.labels[arg]
            elif ins == "jsl":
                target = self._number(arg) if arg.startswith("$") or arg.isdigit() else arg
                service = self.external.get(target, self.external.get(arg))
                if service == "poll":
                    self.a, self.carry = self.world.poll(self)
                    self.phase_mem = self.a
                elif service == "ack":
                    self.a, self.carry = self.world.ack(self, self.a)
                elif isinstance(service, int):
                    self.a, self.carry = self.world.provider(self, service)
                else:
                    raise AssertionError(("unknown service", arg))
                self.equal = self.a == 0
            elif ins == "rtl":
                return self.a, self.carry
            elif ins == "clc":
                self.carry = False
            elif ins == "sec":
                self.carry = True
            else:
                raise AssertionError(("unsupported instruction", op))
        raise AssertionError("dispatcher did not return")


def run_dispatch(phases, providers, outcomes=None):
    spy = WorldSpy(phases, outcomes)
    asm = emit(SYMBOLS, providers)
    vm = Tiny65816(asm, spy, providers)
    before = (vm.x, vm.y, vm.dbr, vm.dp, vm.p, len(vm.stack))
    a, carry = vm.run()
    after = (vm.x, vm.y, vm.dbr, vm.dp, vm.p & 0xFFFE, len(vm.stack))
    expected = (before[0], before[1], before[2], before[3], before[4] & 0xFFFE, before[5])
    return spy, a, carry, after == expected


class LiveWorldDispatchTests(unittest.TestCase):
    def test_completed_services_ack_in_source_order_then_return_without_commit(self):
        providers = {1: "Mark", 8: "Attack", 12: "ClearMove"}
        spy, result, carry, preserved = run_dispatch([1, 8, 12], providers)
        self.assertEqual((result, carry), (0, False))
        self.assertTrue(preserved)
        self.assertEqual([x for x in spy.trace if x[0] != "poll"], [
            ("provider", 1, 0x1357, 0x2468), ("ack", 1),
            ("provider", 8, 0x1357, 0x2468), ("ack", 8),
            ("provider", 12, 0x1357, 0x2468), ("ack", 12),
        ])
        self.assertEqual(spy.index, 3)
        self.assertEqual(spy.trace[-1], ("poll", 0))

    def test_unbound_phase_returns_pending_without_ack(self):
        spy, result, carry, preserved = run_dispatch([4], {1: "Mark"})
        self.assertEqual((result, carry, preserved), (4, False, True))
        self.assertEqual(spy.trace, [("poll", 4)])

    def test_phase_mutation_is_rejected_by_ack_of_original_dispatched_phase(self):
        spy = WorldSpy([1], mutations={1: 2})
        providers = {1: "Mark", 2: "Lost"}
        vm = Tiny65816(emit(SYMBOLS, providers), spy, providers)
        result, carry = vm.run()
        self.assertEqual(result, 1)
        self.assertTrue(carry)
        self.assertEqual(spy.trace, [("poll", 1), ("provider", 1, 0x1357, 0x2468),
                                     ("mutate-phase", 1, 2), ("ack", 1)])
        self.assertEqual(spy.index, 0)

    def test_poll_phase_above_contract_faults_instead_of_returning_unbound(self):
        spy, result, carry, preserved = run_dispatch([13], {1: "Mark"})
        self.assertEqual((result, carry, preserved), (13, True, True))
        self.assertEqual(spy.trace, [("poll", 13)])

    def test_provider_pending_can_resume_and_then_ack_exactly_once(self):
        providers = {7: "Animation"}
        spy = WorldSpy([7], {7: [1, 0]})
        asm = emit(SYMBOLS, providers)
        for expected in ((7, False), (0, False)):
            vm = Tiny65816(asm, spy, providers)
            before = (vm.x, vm.y, vm.dbr, vm.dp, vm.p, len(vm.stack))
            self.assertEqual(vm.run(), expected)
            self.assertEqual((vm.x, vm.y, vm.dbr, vm.dp, vm.p & 0xFFFE, len(vm.stack)),
                             (before[0], before[1], before[2], before[3], before[4] & 0xFFFE, before[5]))
        self.assertEqual(spy.trace, [("poll", 7), ("provider", 7, 0x1357, 0x2468),
                                     ("poll", 7), ("provider", 7, 0x1357, 0x2468),
                                     ("ack", 7), ("poll", 0)])
        self.assertEqual(spy.index, 1)

    def test_provider_fault_or_invalid_result_rejects_without_ack(self):
        for outcome in ("fault", 2, 0x100):
            with self.subTest(outcome=outcome):
                spy, result, carry, preserved = run_dispatch([5], {5: "Script"}, {5: [outcome]})
                self.assertTrue(carry)
                self.assertTrue(preserved)
                self.assertEqual([x[0] for x in spy.trace], ["poll", "provider"])

    def test_faulting_8bit_provider_restores_outer_stack_with_word_pops(self):
        spy = WorldSpy([5], {5: [0x100]}, mode_mutations={5: "m8"})
        providers = {5: "Script"}
        vm = Tiny65816(emit(SYMBOLS, providers), spy, providers)
        result, carry = vm.run()
        self.assertTrue(carry)
        self.assertEqual([x[0] for x in spy.trace], ["poll", "provider"])
        self.assertEqual(vm.pop_widths, [1, 2, 2, 2, 1, 1])
        self.assertEqual(vm.stack, [])

    def test_invalid_bindings_rejected(self):
        for providers in ({0: "Zero"}, {13: "High"}, {True: "Bool"}, {1: "bad label"}, {1: "3"}):
            with self.subTest(providers=providers), self.assertRaises(ValueError):
                emit(SYMBOLS, providers)
        with self.assertRaises(ValueError):
            emit({}, {})


if __name__ == "__main__":
    unittest.main()
