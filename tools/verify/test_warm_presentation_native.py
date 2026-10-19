"""Instruction-VM coverage for the warm publisher's frozen render pin."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
sys.path.insert(0, str(ROOT / "tools" / "verify"))

from source_warm_presentation_assets import CONTROL, DISPLAY_PIN, RENDER_PIN, TILE_ROWS
from source_warm_presentation_native import helper
from test_live_tick_service import Runtime

LATEST = 0x7E7800
SNAPSHOT_SIZE = 148
VISUAL_FIELDS = (0x50, 0x54, 0x56, 0x1C, 0x1E, 0x36, 0x3E, 0x0C, 0x0E)
GUARD_RANGES = ((0x003400, 0x003600), (0x003600, 0x003680),
                (0x003680, 0x0036E0), (0x003480, 0x003500),
                (0x7E3000, 0x7E3400), (0x7E3480, 0x7E3500),
                (0x7E8000, 0x7E8340))


class TrackedStack(list):
    """Track the 65C816 stack pointer while reusing the live-tick VM."""

    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def append(self, item):
        super().append(item)
        self.owner.sp = (self.owner.sp - (1 if item[0] == "b" else 2)) & 0xFFFF

    def pop(self, *args):
        item = super().pop(*args)
        self.owner.sp = (self.owner.sp + (1 if item[0] == "b" else 2)) & 0xFFFF
        return item


class WarmRuntime(Runtime):
    """Execute the emitted helper with a modeled native renderer JSL."""

    def __init__(self, *, source_carry=False, source_fault=0, entry="warmtrypublish",
                 yield_corrupt=()):
        asm = "LiveTick_Service:\n rtl\n" + helper({}, {})
        self.write_trace = []
        super().__init__(asm)
        self.sp = 0x1FF0
        self.stack = TrackedStack(self)
        self.pc = self.labels[entry]
        # The physical source clock starts one field ahead of the helper's
        # zeroed last-serviced watermark.
        self.w16(0x7FFA02, 1)
        self.w16(0x7FFA04, 0)
        self.w16(CONTROL + 0x110, 0)
        self.w16(CONTROL + 0x112, 0)
        self.source_carry = source_carry
        self.source_fault = source_fault
        self.yield_corrupt = tuple(yield_corrupt)
        self.renderer_calls = 0
        self.pin_seen = None
        self.latest_seen = None
        self.context_seen = None
        self.yield_context_seen = None
        self.latch_context_before = None
        self.latch_context_after = None
        self.source_calls = 0

    def w8(self, a, v):
        self.write_trace.append((a & 0xFFFFFF, v & 255))
        super().w8(a, v)

    def run(self, limit=12000, stop_at=None):
        while limit:
            limit -= 1
            if stop_at is not None and self.pc == self.labels[stop_at]:
                return self.a, self.c
            op = self.ops[self.pc]
            self.pc += 1
            parts = op.split()
            ins = parts[0]
            arg = parts[1] if len(parts) > 1 else ""
            if ins.endswith(".l"):
                ins = ins[:-2]
            if ins == "ora":
                self.a = (self.a | self.r16(self.memarg(arg))) & 0xFFFF
                self.z = self.a == 0
            elif ins == "and":
                value = self.num(arg) if arg.startswith("#") else self.r16(self.memarg(arg))
                self.a &= value
                self.z = self.a == 0
            elif ins == "nop":
                pass
            elif ins == "php": self.stack.append(("b", self.p | int(self.c)))
            elif ins == "phb": self.stack.append(("b", self.dbr))
            elif ins == "phd": self.stack.append(("w", self.dp))
            elif ins in ("phx", "phy"):
                self.stack.append(("w" if not self.p & 0x10 else "b",
                                   self.x if ins == "phx" else self.y))
            elif ins == "pha": self.stack.append(("b" if self.p & 0x20 else "w", self.a))
            elif ins in ("plp", "plb", "pld", "plx", "ply"):
                _, value = self.stack.pop()
                if ins == "plp": self.p, self.c = value, bool(value & 1)
                elif ins == "plb": self.dbr = value & 255
                elif ins == "pld": self.dp = value
                elif ins == "plx": self.x = value
                else: self.y = value
            elif ins == "pla":
                _, value = self.stack.pop()
                self.a = ((self.a & 0xFF00) | (value & 255)) if self.p & 0x20 else value
                self.z = self.a == 0
            elif ins == "rep": self.p &= ~self.num(arg)
            elif ins == "sep": self.p |= self.num(arg)
            elif ins == "lda":
                self.a = self.num(arg) if arg.startswith("#") else self.r16(self.memarg(arg))
                self.z = self.a == 0
            elif ins == "sta": self.w16(self.memarg(arg), self.a)
            elif ins == "cmp":
                value = self.num(arg) if arg.startswith("#") else self.r16(self.memarg(arg))
                self.c, self.z = self.a >= value, self.a == value
            elif ins == "inc": self.a = (self.a + 1) & 0xFFFF; self.z = self.a == 0
            elif ins == "inx": self.x = (self.x + 1) & 0xFFFF; self.z = self.x == 0
            elif ins == "ldx":
                self.x = self.num(arg) if arg.startswith("#") else self.r16(self.memarg(arg))
                self.z = self.x == 0
            elif ins == "cpx":
                value = self.num(arg) if arg.startswith("#") else self.r16(self.memarg(arg))
                self.c, self.z = self.x >= value, self.x == value
            elif ins in ("beq", "bne", "bcs", "bcc"):
                take = {"beq": self.z, "bne": not self.z,
                        "bcs": self.c, "bcc": not self.c}[ins]
                if take: self.pc = self.labels[arg]
            elif ins == "jmp": self.pc = self.labels[arg]
            elif ins == "jsl": self.call(arg)
            elif ins == "tcd": self.dp = self.a
            elif ins == "clc": self.c = False
            elif ins == "sec": self.c = True
            elif ins == "rtl": return self.a, self.c
            else: raise AssertionError(("unsupported instruction", op))
        raise AssertionError("warm publish did not return")

    def call(self, arg):
        target = Runtime.num(arg) if arg.startswith("$") else arg.lower()
        if target == "livetick_service":
            self.source_calls += 1
            self.yield_context_seen = (self.dp, self.dbr, self.p & 0x38, self.sp)
            self.pin_seen = bytes(self.r8(RENDER_PIN + i) for i in range(SNAPSHOT_SIZE))
            # Model a committed source tick advancing the latest snapshot.
            for i in range(SNAPSHOT_SIZE):
                self.w8(LATEST + i, (self.r8(LATEST + i) + 0x31) & 255)
            for address in self.yield_corrupt:
                self.w8(address, self.r8(address) ^ 0xFF)
            field = (self.r16(0x7FFA04) << 16) | self.r16(0x7FFA02)
            field = (field + 3) & 0xFFFFFFFF
            self.w16(0x7FFA02, field & 0xFFFF)
            self.w16(0x7FFA04, field >> 16)
            self.a, self.x, self.y, self.dp, self.dbr = 0x7777, 0x8888, 0x9999, 0x3480, 0x55
            self.c = False
            return
        if target != 0x2E8000:
            raise AssertionError(("unexpected native call", arg))
        self.renderer_calls += 1
        self.pin_seen = bytes(self.r8(RENDER_PIN + i) for i in range(SNAPSHOT_SIZE))
        self.latest_seen = bytes(self.r8(LATEST + i) for i in range(SNAPSHOT_SIZE))
        self.context_seen = (self.dp, self.dbr, self.p & 0x38, self.sp)
        # Renderer carry or a sticky source fault aborts before NbMapsComplete,
        # so neither path is permitted to run the display latch.
        if self.source_carry:
            self.c = True
            return
        if self.source_fault:
            self.w16(CONTROL + 0x102, self.source_fault)
            self.c = False
            return

        # Model the publisher's actual post-map-completion leaf call. Preserve
        # the native-renderer's continuation while executing emitted latch code.
        return_pc = self.pc
        self.latch_context_before = call_context(self)
        self.pc = self.labels["warmdisplaylatch"]
        self.run()
        self.pc = return_pc
        self.latch_context_after = call_context(self)

        # Nonvisual reference collection may continue after map publication;
        # the display must remain pinned to the latched immutable picture.
        for i in range(SNAPSHOT_SIZE): self.w8(LATEST + i, (self.r8(LATEST + i) + 0x31) & 255)
        for i in range(96): self.w8(TILE_ROWS + i, (i * 13 + 7) & 255)
        self.w16(CONTROL + 0x102, self.source_fault)
        self.c = False

def fill(vm, address, payload):
    for offset, value in enumerate(payload):
        vm.w8(address + offset, value)


def set_pin_sentinels(vm):
    sentinels = {
        RENDER_PIN + SNAPSHOT_SIZE: 0xA5,
        RENDER_PIN + SNAPSHOT_SIZE + 1: 0x5A,
        DISPLAY_PIN + SNAPSHOT_SIZE: 0x3C,
        DISPLAY_PIN + SNAPSHOT_SIZE + 1: 0xC3,
    }
    for address, value in sentinels.items(): vm.w8(address, value)
    return sentinels


def assert_sentinels(test, vm, sentinels):
    for address, value in sentinels.items(): test.assertEqual(vm.r8(address), value)


def snapshot(seed, epoch=1):
    data = bytearray(((seed + i * 17) & 255) for i in range(SNAPSHOT_SIZE))
    data[144:146] = epoch.to_bytes(2, "little")
    data[146:148] = b"\0\0"
    return bytes(data)


def seed_guard_ranges(vm):
    for start, end in GUARD_RANGES:
        for address in range(start, end): vm.w8(address, (address * 29 + 0x53) & 255)
    return {start: bytes(vm.r8(a) for a in range(start, end))
            for start, end in GUARD_RANGES}


def assert_guards(test, vm, guards):
    for start, expected in guards.items():
        test.assertEqual(bytes(vm.r8(a) for a in range(start, start + len(expected))), expected)


def call_context(vm):
    return (vm.a, vm.x, vm.y, vm.dp, vm.dbr, vm.p & ~1, vm.sp, len(vm.stack))


class WarmPresentationNativeTests(unittest.TestCase):
    def changed_vm(self, **kwargs):
        vm = WarmRuntime(**kwargs)
        old = snapshot(0x12, epoch=1)
        new = bytearray(snapshot(0xA4, epoch=2))
        # Keep the live epoch nonzero to request a source publication.
        new[144:146] = (2).to_bytes(2, "little")
        fill(vm, DISPLAY_PIN, old)
        fill(vm, LATEST, new)
        sentinels = set_pin_sentinels(vm)
        vm.w16(CONTROL + 0x100, 0)
        guards = seed_guard_ranges(vm)
        vm.write_trace.clear()
        return vm, old, bytes(new), guards, sentinels

    def test_success_renders_frozen_pin_and_copies_that_exact_picture(self):
        vm, old, latest, guards, sentinels = self.changed_vm()
        before_context = call_context(vm)
        result = vm.run()
        self.assertEqual(result[1], False)
        self.assertEqual(vm.renderer_calls, 1)
        self.assertEqual(vm.pin_seen, latest)
        self.assertEqual(vm.latest_seen, latest)
        self.assertEqual(vm.context_seen[:3], (0, 0, 0))
        self.assertEqual(vm.context_seen[3], before_context[6] - 10)
        self.assertEqual(vm.latch_context_after, vm.latch_context_before)
        self.assertEqual(bytes(vm.r8(DISPLAY_PIN + i) for i in range(SNAPSHOT_SIZE)), latest)
        self.assertNotEqual(bytes(vm.r8(LATEST + i) for i in range(SNAPSHOT_SIZE)), latest)
        self.assertEqual(vm.r16(CONTROL + 0x100), 2)
        self.assertEqual(vm.r16(CONTROL + 0x102), 0)
        self.assertEqual(call_context(vm), (*before_context[:5], before_context[5], before_context[6], 0))
        self.assertEqual(vm.sp, before_context[6])
        assert_guards(self, vm, guards)
        assert_sentinels(self, vm, sentinels)

    def test_native_rejection_keeps_previous_display_pin(self):
        vm, old, latest, guards, sentinels = self.changed_vm(source_carry=True)
        before = call_context(vm)
        result = vm.run()
        self.assertEqual(result[1], True)
        self.assertEqual(vm.renderer_calls, 1)
        self.assertEqual(vm.pin_seen, latest)
        self.assertEqual(bytes(vm.r8(DISPLAY_PIN + i) for i in range(SNAPSHOT_SIZE)), old)
        self.assertEqual(vm.r16(CONTROL + 0x100), 4)
        self.assertIsNone(vm.latch_context_before)
        self.assertEqual(call_context(vm), before)
        assert_guards(self, vm, guards)
        assert_sentinels(self, vm, sentinels)

    def test_source_fault_flag_keeps_previous_display_pin(self):
        vm, old, latest, guards, sentinels = self.changed_vm(source_fault=0x0001)
        before = call_context(vm)
        result = vm.run()
        self.assertEqual(result[1], True)
        self.assertEqual(vm.renderer_calls, 1)
        self.assertEqual(vm.pin_seen, latest)
        self.assertEqual(bytes(vm.r8(DISPLAY_PIN + i) for i in range(SNAPSHOT_SIZE)), old)
        self.assertEqual(vm.r16(CONTROL + 0x102), 1)
        self.assertEqual(vm.r16(CONTROL + 0x100), 4)
        self.assertIsNone(vm.latch_context_before)
        self.assertEqual(call_context(vm), before)
        assert_guards(self, vm, guards)
        assert_sentinels(self, vm, sentinels)

    def test_advanced_epoch_with_same_visual_tuple_skips_renderer(self):
        vm = WarmRuntime()
        displayed = bytearray(snapshot(0x21, epoch=1))
        latest = bytearray(displayed)
        latest[144:146] = (2).to_bytes(2, "little")
        # Nonvisual source state can evolve while the listed visual anchors
        # remain identical.
        latest[0x70] ^= 0x55
        fill(vm, DISPLAY_PIN, displayed)
        fill(vm, LATEST, latest)
        guards = seed_guard_ranges(vm)
        vm.write_trace.clear()
        before = call_context(vm)
        result = vm.run()
        self.assertEqual(result[1], False)
        self.assertEqual(vm.r16(LATEST + 144), 2)
        self.assertEqual(vm.r16(DISPLAY_PIN + 144), 1)
        self.assertEqual(vm.renderer_calls, 0)
        self.assertEqual(bytes(vm.r8(DISPLAY_PIN + i) for i in range(SNAPSHOT_SIZE)), bytes(displayed))
        self.assertEqual(call_context(vm), (*before[:5], before[5], before[6], 0))
        assert_guards(self, vm, guards)

    def test_yield_calls_source_at_dp_zero_without_aliasing_render_pin_or_maps(self):
        vm = WarmRuntime(entry="warmyield")
        pin = snapshot(0x61, epoch=3)
        live = snapshot(0xA2, epoch=4)
        fill(vm, RENDER_PIN, pin)
        fill(vm, LATEST, live)
        guards = seed_guard_ranges(vm)
        vm.write_trace.clear()
        before = call_context(vm)
        result = vm.run()
        self.assertEqual(result[1], False)
        self.assertEqual(vm.source_calls, 1)
        self.assertEqual(vm.renderer_calls, 0)
        self.assertEqual(vm.yield_context_seen[:3], (0, 0, 0))
        self.assertEqual(vm.yield_context_seen[3], before[6] - 10)
        self.assertEqual(vm.pin_seen, pin)
        self.assertEqual(bytes(vm.r8(RENDER_PIN + i) for i in range(SNAPSHOT_SIZE)), pin)
        self.assertNotEqual(bytes(vm.r8(LATEST + i) for i in range(SNAPSHOT_SIZE)), live)
        self.assertEqual(call_context(vm), (*before[:5], before[5], before[6], 0))
        assert_guards(self, vm, guards)

    def test_yield_skips_until_new_physical_field_then_remembers_postservice_field(self):
        vm = WarmRuntime(entry="warmyield")
        pin = snapshot(0x58, epoch=8)
        live = snapshot(0x9B, epoch=9)
        fill(vm, RENDER_PIN, pin)
        fill(vm, LATEST, live)
        guards = seed_guard_ranges(vm)

        self.assertEqual((vm.r16(0x7FFA02), vm.r16(0x7FFA04),
                          vm.r16(CONTROL + 0x110), vm.r16(CONTROL + 0x112)), (1, 0, 0, 0))
        vm.run()
        self.assertEqual(vm.source_calls, 1)
        self.assertEqual(vm.r16(0x7FFA02), 4)
        self.assertEqual((vm.r16(CONTROL + 0x110), vm.r16(CONTROL + 0x112)), (4, 0))
        self.assertEqual(vm.r16(CONTROL + 0x11A), 1)

        after_first = bytes(vm.r8(LATEST + i) for i in range(SNAPSHOT_SIZE))
        vm.pc = vm.labels["warmyield"]
        before_skip = call_context(vm)
        vm.run()
        self.assertEqual(vm.source_calls, 1)
        self.assertEqual(bytes(vm.r8(LATEST + i) for i in range(SNAPSHOT_SIZE)), after_first)
        self.assertEqual(vm.r16(CONTROL + 0x11A), 1)
        self.assertEqual(call_context(vm), (*before_skip[:5], before_skip[5], before_skip[6], 0))

        # Advance the actual physical field. The service itself then consumes
        # three fields; the next watermark must capture that post-service value.
        vm.w16(0x7FFA02, 5)
        vm.pc = vm.labels["warmyield"]
        vm.run()
        self.assertEqual(vm.source_calls, 2)
        self.assertEqual(vm.r16(0x7FFA02), 8)
        self.assertEqual((vm.r16(CONTROL + 0x110), vm.r16(CONTROL + 0x112)), (8, 0))
        self.assertEqual(vm.r16(CONTROL + 0x11A), 2)
        self.assertEqual(bytes(vm.r8(RENDER_PIN + i) for i in range(SNAPSHOT_SIZE)), pin)
        assert_guards(self, vm, guards)

    def test_yield_guard_detects_and_restores_all_736_bytes_after_normal_commit(self):
        corrupt_addresses = (0x003400, 0x0034FF, 0x003500, 0x0035FF,
                            0x003600, 0x00367F, 0x003680, 0x0036DF)
        for address in corrupt_addresses:
            with self.subTest(corrupt_address=f"${address:06X}"):
                vm = WarmRuntime(entry="warmyield", yield_corrupt=(address,))
                render_pin = snapshot(0x36, epoch=5)
                display_pin = snapshot(0x74, epoch=6)
                fill(vm, RENDER_PIN, render_pin)
                fill(vm, DISPLAY_PIN, display_pin)
                guards = seed_guard_ranges(vm)
                vm.write_trace.clear()
                before = call_context(vm)
                result = vm.run()
                self.assertEqual(result[1], False)
                self.assertEqual(vm.source_calls, 1)
                self.assertEqual(vm.renderer_calls, 0)
                self.assertEqual(vm.r16(CONTROL + 0x102), 1)
                self.assertEqual(vm.r16(CONTROL + 0x106), 1)
                self.assertEqual(vm.r16(CONTROL + 0x104), 0)
                for start, end in ((0x003400, 0x003600), (0x003600, 0x003680),
                                   (0x003680, 0x0036E0)):
                    self.assertEqual(bytes(vm.r8(a) for a in range(start, end)),
                                     guards[start])
                self.assertEqual(bytes(vm.r8(RENDER_PIN + i) for i in range(SNAPSHOT_SIZE)),
                                 render_pin)
                self.assertEqual(bytes(vm.r8(DISPLAY_PIN + i) for i in range(SNAPSHOT_SIZE)),
                                 display_pin)
                self.assertEqual(call_context(vm), (*before[:5], before[5], before[6], 0))
                assert_guards(self, vm, guards)

    def test_warm_main_clears_cold_counters_and_respects_pin_boundaries(self):
        vm = WarmRuntime(entry="warmmain")
        for address in range(0x7E7710, 0x7E7718, 2): vm.w16(address, 0xA55A)
        cold = bytes((i * 19 + 0x27) & 255 for i in range(146))
        fill(vm, 0x7FBA00, cold)
        sentinel = set_pin_sentinels(vm)
        vm.write_trace.clear()
        vm.run(stop_at="warmmain_ready")
        self.assertEqual([vm.r16(a) for a in range(0x7E7710, 0x7E7718, 2)], [0, 0, 0, 0])
        self.assertEqual(bytes(vm.r8(DISPLAY_PIN + i) for i in range(146)), cold)
        self.assertEqual(vm.r16(DISPLAY_PIN + 146), 0)
        assert_sentinels(self, vm, sentinel)

    def test_display_latch_leaf_preserves_context_and_copies_exact_148_bytes(self):
        vm = WarmRuntime(entry="warmdisplaylatch")
        render_pin = snapshot(0xB2, epoch=7)
        prior_display = snapshot(0x27, epoch=6)
        fill(vm, RENDER_PIN, render_pin)
        fill(vm, DISPLAY_PIN, prior_display)
        sentinels = set_pin_sentinels(vm)
        before = call_context(vm)
        result = vm.run()
        self.assertEqual(result[1], False)
        self.assertEqual(bytes(vm.r8(DISPLAY_PIN + i) for i in range(SNAPSHOT_SIZE)), render_pin)
        self.assertEqual(call_context(vm), before)
        assert_sentinels(self, vm, sentinels)


if __name__ == "__main__":
    unittest.main()
