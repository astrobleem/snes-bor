"""Control-flow execution tests for the emitted live tick service."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
from source_live_tick_service import emit
from source_foreign_state_layout import layout

WORK = 0x7E7700
LATEST = 0x7E7800
INPUT = next(r["address"] for r in layout(0x7FA000, 6400)["regions"]
             if r["name"] == "input_snapshot")
SY = {
    "SourceClock4086_Ready": 0x7FFA00,
    "SourceClock4086_Due": 0x7FFA02,
    "SourceClock4086_TimeLo": 0x7FFA04,
    "SourceClock4086_TimeHi": 0x7FFA06,
    "SourceClock4086_Observe": 0x9000,
    "SourceWorldTick4086_Ready": 0x7FFAEC,
    "SourceWorldTick4086_State": 0x7FFAEE,
    "SourceWorldTick4086_Pending": 0x7FFAF0,
    "SourceWorldTick4086_Begin": 0x9010,
    "SourceWorldTick4086_Commit": 0x9020,
    "SourceInputController_Refresh": 0x9030,
    "VmSourceInput_Ready": 0x7FF8D0,
}
PLAYER = {"PlayerHistory_Refresh": 0x9040, "input_snapshot": INPUT}


class Runtime:
    def __init__(self, asm, *, due=0, observed_due=1, dispatch="complete", state=0,
                 pending=0, commit_fault=False, observe_fault=False,
                 input_fault=False, history_fault=False, begin_fault=False):
        self.ops, self.labels = [], {}
        for raw in asm.splitlines():
            line = raw.split(";", 1)[0].strip()
            if not line or line.startswith("."):
                continue
            if line.endswith(":"):
                self.labels[line[:-1].lower()] = len(self.ops)
            else:
                self.ops.append(line.lower())
        self.m = {}
        self.a, self.x, self.y = 0x99AA, 0x1357, 0x2468
        self.dp, self.dbr, self.p = 0x3400, 0x42, 0x013C
        self.stack, self.pc, self.z, self.c = [], self.labels["livetick_service"], False, False
        self.calls = {"observe": 0, "input": 0, "history": 0, "begin": 0,
                      "dispatch": 0, "commit": 0}
        self.native_decimal = []
        self.observed_due, self.dispatch = observed_due, dispatch
        self.faults = dict(commit=commit_fault, observe=observe_fault, input=input_fault,
                           history=history_fault, begin=begin_fault)
        self.w16(SY["SourceClock4086_Ready"], 0xB4C5)
        self.w16(SY["SourceClock4086_Due"], due)
        self.w32(SY["SourceClock4086_TimeLo"], 17)
        self.w16(SY["SourceWorldTick4086_Ready"], 0xB4D5)
        self.w16(SY["SourceWorldTick4086_State"], state)
        self.w16(SY["SourceWorldTick4086_Pending"], pending)
        self.w16(WORK, 0xB6D0); self.w16(WORK + 2, 2 if state else 1)
        self.w32(WORK + 4, 1); self.w32(WORK + 8, 0)
        self.w16(WORK + 16, 0); self.w16(WORK + 18, 0); self.w16(WORK + 20, 0)
        self.w16(SY["VmSourceInput_Ready"], 0)
        self.actor = bytes((i * 7 + 3) & 255 for i in range(80))
        self.side = bytes((i * 11 + 5) & 255 for i in range(64))
        for i in range(0, 80, 2): self.w16(0x414000 + i, self.actor[i] | self.actor[i+1] << 8)
        for i in range(0, 64, 2): self.w16(0x416800 + i, self.side[i] | self.side[i+1] << 8)
        for i in range(0, 168, 2): self.w16(LATEST + i, 0xCDEF)

    def r8(self, a): return self.m.get(a & 0xFFFFFF, 0)
    def w8(self, a, v): self.m[a & 0xFFFFFF] = v & 255
    def r16(self, a): return self.r8(a) | self.r8(a + 1) << 8
    def w16(self, a, v): self.w8(a, v); self.w8(a + 1, v >> 8)
    def w32(self, a, v): self.w16(a, v); self.w16(a + 2, v >> 16)
    def r32(self, a): return self.r16(a) | self.r16(a + 2) << 16
    @staticmethod
    def num(s):
        s = s.removeprefix("#")
        return int(s[1:], 16) if s.startswith("$") else int(s, 10)

    def memarg(self, arg):
        indexed = arg.endswith(",x")
        text = arg[:-2] if indexed else arg
        addr = self.num(text)
        return addr + (self.x if indexed else 0)

    def run(self, limit=5000):
        while limit:
            limit -= 1
            op = self.ops[self.pc]; self.pc += 1
            p = op.split(); ins = p[0]; arg = p[1] if len(p) > 1 else ""
            if ins.endswith(".l"):
                ins = ins[:-2]
            if ins == "php": self.stack.append(("b", self.p))
            elif ins in ("phb",): self.stack.append(("b", self.dbr))
            elif ins == "phd": self.stack.append(("w", self.dp))
            elif ins in ("phx", "phy"): self.stack.append(("w" if not self.p & 0x10 else "b", self.x if ins == "phx" else self.y))
            elif ins == "pha": self.stack.append(("b" if self.p & 0x20 else "w", self.a))
            elif ins in ("plp", "plb", "pld", "plx", "ply"):
                kind, v = self.stack.pop()
                if ins == "plp": self.p = v
                elif ins == "plb": self.dbr = v & 255
                elif ins == "pld": self.dp = v
                elif ins == "plx": self.x = v
                else: self.y = v
            elif ins == "pla":
                _, v = self.stack.pop()
                if self.p & 0x20: self.a = (self.a & 0xFF00) | (v & 255)
                else: self.a = v
                self.z = self.a == 0
            elif ins == "rep": self.p &= ~self.num(arg)
            elif ins == "sep": self.p |= self.num(arg)
            elif ins == "lda":
                self.a = self.num(arg) if arg.startswith("#") else self.r16(self.memarg(arg))
                self.z = self.a == 0
            elif ins == "sta": self.w16(self.memarg(arg), self.a)
            elif ins == "cmp":
                v = self.num(arg) if arg.startswith("#") else self.r16(self.memarg(arg))
                self.c = self.a >= v
                self.z = self.a == v
            elif ins == "inc": self.a = (self.a + 1) & 65535; self.z = self.a == 0
            elif ins == "inx": self.x = (self.x + 1) & 65535; self.z = self.x == 0
            elif ins == "ldx":
                self.x = self.num(arg) if arg.startswith("#") else self.r16(self.memarg(arg))
                self.z = self.x == 0
            elif ins == "ldy":
                self.y = self.num(arg) if arg.startswith("#") else self.r16(self.memarg(arg))
                self.z = self.y == 0
            elif ins == "tax": self.x = self.a; self.z = self.x == 0
            elif ins == "tay": self.y = self.a; self.z = self.y == 0
            elif ins == "cpx":
                v = self.num(arg) if arg.startswith("#") else self.r16(self.memarg(arg))
                self.c = self.x >= v; self.z = self.x == v
            elif ins == "tcd": self.dp = self.a
            elif ins in ("beq", "bne", "bcs", "bcc"):
                take = {"beq": self.z, "bne": not self.z, "bcs": self.c, "bcc": not self.c}[ins]
                if take: self.pc = self.labels[arg]
            elif ins == "jmp": self.pc = self.labels[arg]
            elif ins == "jsl": self.call(arg)
            elif ins == "clc": self.c = False
            elif ins == "sec": self.c = True
            elif ins == "rtl": return self.a, self.c
            else: raise AssertionError(("unsupported instruction", op))
        raise AssertionError("service did not return")

    def call(self, arg):
        self.native_decimal.append(bool(self.p & 0x08))
        addr = self.num(arg) if arg.startswith("$") else arg
        if addr == SY["SourceClock4086_Observe"]:
            self.calls["observe"] += 1
            self.a, self.c = self.observed_due, self.faults["observe"]
            if not self.c:
                self.w16(SY["SourceClock4086_Due"], self.observed_due)
        elif addr == SY["SourceInputController_Refresh"]:
            self.calls["input"] += 1
            self.c = self.faults["input"]
            if not self.c:
                for i in range(0, 20, 2): self.w16(SY["VmSourceInput_Ready"] + i, 0xA000 + i)
        elif addr == PLAYER["PlayerHistory_Refresh"]:
            self.calls["history"] += 1; self.c = self.faults["history"]
        elif addr == SY["SourceWorldTick4086_Begin"]:
            self.calls["begin"] += 1; self.c = self.faults["begin"]
            if not self.c:
                self.c = (self.r16(SY["SourceClock4086_Due"]) == 0 or
                          self.r16(SY["SourceWorldTick4086_State"]) != 0)
                if not self.c: self.w16(SY["SourceWorldTick4086_State"], 1)
        elif addr == "liveworlddispatch_run":
            self.calls["dispatch"] += 1
            if self.dispatch == "fault": self.a, self.c = 0, True
            elif isinstance(self.dispatch, int):
                self.a, self.c = self.dispatch, False
                self.w16(SY["SourceWorldTick4086_State"], 1)
                self.w16(SY["SourceWorldTick4086_Pending"], 1)
            else:
                self.w16(SY["SourceWorldTick4086_State"], 4)
                self.w16(SY["SourceWorldTick4086_Pending"], 0)
                self.a, self.c = 0, False
        elif addr == SY["SourceWorldTick4086_Commit"]:
            self.calls["commit"] += 1; self.c = self.faults["commit"]
            self.c = self.c or self.r16(SY["SourceClock4086_Due"]) == 0
            self.c = self.c or self.r16(SY["SourceWorldTick4086_State"]) != 4
            self.c = self.c or self.r16(SY["SourceWorldTick4086_Pending"]) != 0
            if not self.c:
                due = self.r16(SY["SourceClock4086_Due"])
                self.w16(SY["SourceClock4086_Due"], max(0, due - 1))
                time = (self.r32(SY["SourceClock4086_TimeLo"]) + 1) & 0xFFFFFFFF
                self.w32(SY["SourceClock4086_TimeLo"], time)
                self.w16(SY["SourceWorldTick4086_State"], 0)
        else: raise AssertionError(("unknown native call", arg))


def run_runtime(**kwargs):
    asm = emit(SY, PLAYER, WORK, LATEST)
    vm = Runtime(asm, **kwargs)
    before = (vm.x, vm.y, vm.dp, vm.dbr, vm.p, len(vm.stack))
    result = vm.run()
    after = (vm.x, vm.y, vm.dp, vm.dbr, vm.p, len(vm.stack))
    return vm, result, before == after


class LiveTickServiceTests(unittest.TestCase):
    def test_player_history_can_be_a_linked_local_label(self):
        asm = emit(SY, {"PlayerHistory_Refresh": "LivePlayerHistory_Refresh"}, WORK, LATEST)
        self.assertIn(" jsl LivePlayerHistory_Refresh", asm)

    def test_no_due_observes_but_does_not_refresh_begin_or_commit(self):
        vm, result, preserved = run_runtime(observed_due=0)
        self.assertEqual(result, (0, False)); self.assertTrue(preserved)
        self.assertEqual(vm.calls, dict(observe=1, input=0, history=0, begin=0, dispatch=0, commit=0))
        self.assertEqual(vm.r16(WORK + 2), 1)
        self.assertEqual(vm.r16(WORK + 16), 0)
        self.assertTrue(all(vm.r16(LATEST + i) == 0xCDEF for i in range(0, 168, 2)))

    def test_pending_uses_real_phase_and_does_not_commit_or_seal(self):
        vm, result, preserved = run_runtime(observed_due=1, dispatch=7)
        self.assertEqual(result, (1, False)); self.assertTrue(preserved)
        self.assertEqual((vm.calls["observe"], vm.calls["input"], vm.calls["history"],
                          vm.calls["begin"], vm.calls["dispatch"], vm.calls["commit"]), (1, 1, 1, 1, 1, 0))
        self.assertEqual((vm.r16(WORK + 2), vm.r16(WORK + 6), vm.r16(WORK + 12),
                          vm.r32(WORK + 8)), (2, 0, 7, 0))
        self.assertTrue(all(vm.r16(LATEST + i) == 0xCDEF for i in range(0, 168, 2)))
        self.assertEqual(vm.r16(INPUT), 0xA000)

    def test_completed_new_sample_commits_once_then_seals_actor_and_side(self):
        vm, result, preserved = run_runtime(observed_due=1, dispatch="complete")
        self.assertEqual(result, (2, False)); self.assertTrue(preserved)
        self.assertEqual(vm.calls["commit"], 1)
        self.assertEqual((vm.r32(WORK + 8), vm.r16(WORK + 2), vm.r32(LATEST + 144)), (1, 1, 1))
        self.assertEqual(bytes(vm.r8(LATEST + i) for i in range(80)), vm.actor)
        self.assertEqual(bytes(vm.r8(LATEST + 80 + i) for i in range(64)), vm.side)

    def test_catch_up_reuses_sample_and_resumes_only_one_tick_per_call(self):
        asm = emit(SY, PLAYER, WORK, LATEST)
        vm = Runtime(asm, due=2, observed_due=9, dispatch="complete")
        before = (vm.x, vm.y, vm.dp, vm.dbr, vm.p, len(vm.stack))
        first = vm.run()
        self.assertEqual(first, (2, False))
        self.assertEqual(vm.r16(SY["SourceClock4086_Due"]), 1)
        self.assertEqual((vm.calls["observe"], vm.calls["input"], vm.calls["history"]), (0, 0, 0))
        vm.pc = vm.labels["livetick_service"]
        vm.a, vm.x, vm.y, vm.dp, vm.dbr, vm.p = 0x99AA, 0x1357, 0x2468, 0x3400, 0x42, 0x013C
        second = vm.run()
        self.assertEqual(second, (2, False))
        self.assertEqual(vm.calls["commit"], 2)
        self.assertEqual((vm.calls["observe"], vm.calls["input"], vm.calls["history"]), (0, 0, 0))
        self.assertEqual(vm.r32(WORK + 8), 2)
        self.assertEqual((vm.x, vm.y, vm.dp, vm.dbr, vm.p, len(vm.stack)), before)

    def test_existing_state_resumes_without_begin_or_new_sample(self):
        vm, result, preserved = run_runtime(due=1, state=1, dispatch=4)
        self.assertEqual((result, preserved), ((1, False), True))
        self.assertEqual((vm.calls["observe"], vm.calls["input"], vm.calls["history"], vm.calls["begin"]), (0, 0, 0, 0))
        self.assertEqual(vm.r16(WORK + 12), 4)
        self.assertEqual(vm.r16(WORK + 6), 0)

    def test_pending_call_resumes_with_immutable_generation_and_debt(self):
        vm = Runtime(emit(SY, PLAYER, WORK, LATEST), observed_due=1, dispatch=7)
        self.assertEqual(vm.run(), (1, False))
        self.assertEqual((vm.r16(WORK + 6), vm.r16(WORK + 12),
                          vm.r16(WORK + 2), vm.r16(SY["SourceClock4086_Due"])), (0, 7, 2, 1))
        vm.dispatch = "complete"
        vm.pc = vm.labels["livetick_service"]
        vm.a, vm.x, vm.y, vm.dp, vm.dbr, vm.p = 0x99AA, 0x1357, 0x2468, 0x3400, 0x42, 0x013C
        self.assertEqual(vm.run(), (2, False))
        self.assertEqual((vm.r16(WORK + 6), vm.r16(WORK + 12), vm.r16(WORK + 2),
                          vm.r32(WORK + 8)), (0, 0, 1, 1))
        self.assertEqual((vm.calls["observe"], vm.calls["input"], vm.calls["history"],
                          vm.calls["begin"], vm.calls["dispatch"], vm.calls["commit"]), (1, 1, 1, 1, 2, 1))
        self.assertTrue(vm.native_decimal and not any(vm.native_decimal))

    def test_provider_fault_is_sticky_and_has_no_commit_or_snapshot(self):
        vm, result, preserved = run_runtime(observed_due=1, dispatch="fault")
        self.assertEqual((result, preserved), ((0, True), True))
        self.assertEqual(vm.r16(WORK + 2), 3)
        self.assertEqual(vm.calls["commit"], 0)
        self.assertEqual(vm.r32(WORK + 8), 0)
        self.assertTrue(all(vm.r16(LATEST + i) == 0xCDEF for i in range(0, 168, 2)))

    def test_commit_fault_does_not_increment_or_publish_partial_snapshot(self):
        vm, result, preserved = run_runtime(observed_due=1, dispatch="complete", commit_fault=True)
        self.assertEqual((result, preserved), ((0, True), True))
        self.assertEqual((vm.r16(WORK + 2), vm.r32(WORK + 8)), (3, 0))
        self.assertTrue(all(vm.r16(LATEST + i) == 0xCDEF for i in range(0, 168, 2)))

    def test_sticky_fault_is_preserved_and_reentry_does_not_touch_work(self):
        vm, result, preserved = run_runtime()
        vm.w16(WORK + 2, 3); vm.w16(WORK + 16, 0)
        vm.pc = vm.labels["livetick_service"]
        result = vm.run()
        self.assertEqual(result, (0, True)); self.assertEqual(vm.r16(WORK + 2), 3)
        vm.w16(WORK + 2, 1); vm.w16(WORK + 16, 1)
        before_work = bytes(vm.r8(WORK + i) for i in range(24))
        vm.pc = vm.labels["livetick_service"]
        vm.a, vm.x, vm.y, vm.dp, vm.dbr, vm.p = 0x99AA, 0x1357, 0x2468, 0x3400, 0x42, 0x013C
        result = vm.run()
        self.assertEqual(result, (0, True))
        self.assertEqual(bytes(vm.r8(WORK + i) for i in range(24)), before_work)
        self.assertEqual((vm.x, vm.y, vm.dp, vm.dbr, vm.p, len(vm.stack)), (0x1357, 0x2468, 0x3400, 0x42, 0x013C, 0))


if __name__ == "__main__":
    unittest.main()
