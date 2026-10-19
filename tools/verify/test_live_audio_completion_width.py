"""Execute the live-audio pump's completion join with real 65816 M width."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
sys.path.insert(0, str(ROOT / "tools" / "verify"))
from actor_s5_entity_fixture import symbols
from source_live_audio_transport import LEASE_ADDRESS, LEASE_MAGIC, READY_MAGIC, emit

CONTROL = 0x7E7700
ACTIVE = 0x7E281A
PENDING = 0x7E28B0
STATUS = 0x7E28F0
AUDIO_CONTROL = 0x7E8120
CHANNELS = 0x7E8140


class ImmediateWidthFault(AssertionError):
    """An assembled immediate operand width disagrees with runtime M."""


class TrackedStack(list):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def append(self, item):
        super().append(item)
        self.owner.sp = (self.owner.sp - item[0] // 8) & 0xFFFF

    def pop(self, *args):
        item = super().pop(*args)
        self.owner.sp = (self.owner.sp + item[0] // 8) & 0xFFFF
        return item


class PumpWidthVm:
    """Small control-flow VM for the emitted LiveAudio_Pump path.

    `.a8`/`.a16` directives determine encoded immediate widths. CPU M is
    tracked separately from SEP/REP. A mismatch fails at the instruction,
    reproducing the extra encoded byte becoming the next fetched opcode.
    """

    def __init__(self, asm, *, active):
        self.ops = []
        self.labels = {}
        self.assembler_a_width = 16
        for raw in asm.splitlines():
            line = raw.split(";", 1)[0].strip()
            if not line: continue
            lower = line.lower()
            if lower == ".a8":
                self.assembler_a_width = 8
                continue
            if lower == ".a16":
                self.assembler_a_width = 16
                continue
            if lower.startswith(".") or lower == ".i8" or lower == ".i16":
                continue
            if line.endswith(":"):
                self.labels[lower[:-1]] = len(self.ops)
            else:
                self.ops.append((lower, self.assembler_a_width))
        self.pc = self.labels["liveaudio_pump"]
        self.a, self.x, self.y = 0xA1C3, 0x007E, 0x00D1
        self.dp, self.dbr, self.p = 0x8844, 0x57, 0x003D
        self.c, self.z = True, False
        self.sp = 0x1FF0
        self.stack = TrackedStack(self)
        self.memory = {}
        self.write_control(LEASE_ADDRESS, LEASE_MAGIC)
        self.write_control(CONTROL, READY_MAGIC)
        self.write_control(CONTROL + 2, 1)
        self.write_control(STATUS, 4)
        self.write_control(AUDIO_CONTROL, 0xB6D9)
        self.write_control(ACTIVE, int(active))
        self.write_control(PENDING, 0)
        self.write_control(CHANNELS + 11 * 40, 0)
        self.write_control(CHANNELS + 11 * 40 + 2, 0)

    @staticmethod
    def number(value):
        value = value.removeprefix("#")
        if value.startswith("$"):
            return int(value[1:], 16)
        return int(value, 10)

    def read(self, address, width):
        return sum(self.memory.get(address + i, 0) << (i * 8) for i in range(width // 8))

    def write(self, address, value, width):
        for i in range(width // 8):
            self.memory[address + i] = (value >> (i * 8)) & 0xFF

    def read_arg(self, arg, width):
        if arg.startswith("#"):
            return self.number(arg) & ((1 << width) - 1)
        return self.read(self.number(arg), width)

    def write_control(self, address, value):
        self.write(address, value, 16)

    def execute(self, limit=2000):
        while limit:
            limit -= 1
            op, assembled_width = self.ops[self.pc]
            self.pc += 1
            fields = op.split()
            ins = fields[0]
            arg = fields[1] if len(fields) > 1 else ""
            if ins.endswith(".l"):
                ins = ins[:-2]
            width = 8 if self.p & 0x20 else 16

            if ins == "php": self.stack.append((8, self.p | int(self.c)))
            elif ins == "pha": self.stack.append((width, self.a))
            elif ins == "phx": self.stack.append((8 if self.p & 0x10 else 16, self.x))
            elif ins == "phy": self.stack.append((8 if self.p & 0x10 else 16, self.y))
            elif ins == "phd": self.stack.append((16, self.dp))
            elif ins == "phb": self.stack.append((8, self.dbr))
            elif ins in ("plp", "pla", "plx", "ply", "pld", "plb"):
                _, value = self.stack.pop()
                if ins == "plp": self.p, self.c = value, bool(value & 1)
                elif ins == "pla": self.a = value
                elif ins == "plx": self.x = value
                elif ins == "ply": self.y = value
                elif ins == "pld": self.dp = value
                else: self.dbr = value & 0xFF
            elif ins in ("rep", "sep"):
                mask = self.number(arg)
                self.p = self.p & ~mask if ins == "rep" else self.p | mask
            elif ins == "lda":
                if arg.startswith("#") and width != assembled_width:
                    raise ImmediateWidthFault((self.labels["liveaudio_pump"], op,
                                               assembled_width, width))
                self.a = self.read_arg(arg, width)
                self.z = self.a == 0
            elif ins == "sta":
                self.write(self.number(arg), self.a, width)
            elif ins == "cmp":
                if arg.startswith("#") and width != assembled_width:
                    raise ImmediateWidthFault((op, assembled_width, width,
                                               "high immediate byte is next fetched opcode"))
                value = self.read_arg(arg, width)
                self.c, self.z = self.a >= value, self.a == value
            elif ins == "ora":
                self.a |= self.read_arg(arg, width)
                self.a &= (1 << width) - 1
                self.z = self.a == 0
            elif ins in ("beq", "bne", "bcc", "bcs"):
                take = {"beq": self.z, "bne": not self.z,
                        "bcc": not self.c, "bcs": self.c}[ins]
                if take: self.pc = self.labels[arg]
            elif ins in ("bra", "brl", "jmp"):
                self.pc = self.labels[arg]
            elif ins == "tcd": self.dp = self.a
            elif ins == "jsl":
                # Prefill and the external TAD pump are leaf calls. This
                # bounded VM treats their register-preserving ABI as a stub.
                pass
            elif ins == "rtl": return self.a, self.c
            else: raise AssertionError(("unsupported pump instruction", op))
        raise AssertionError("pump did not return")


class LiveAudioCompletionWidthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sy = symbols(ROOT / "src" / "main.sym")
        cls.asm = emit(sy, CONTROL, include_pump=True, metadata_samples=17)

    def run_case(self, *, active):
        vm = PumpWidthVm(self.asm, active=active)
        before = (vm.a, vm.x, vm.y, vm.dp, vm.dbr, vm.p, vm.c, vm.sp)
        result = vm.execute()
        after = (vm.a, vm.x, vm.y, vm.dp, vm.dbr, vm.p, vm.c, vm.sp)
        return vm, result, before, after

    def test_inactive_completion_branch_reaches_status_check_at_matching_width(self):
        vm, _, before, after = self.run_case(active=False)
        self.assertEqual(after, before)
        self.assertEqual(vm.stack, [])
        self.assertEqual(vm.read(STATUS, 16), 4)
        self.assertEqual(vm.read(AUDIO_CONTROL, 16), 0xB6D9)

    def test_active_stream_completion_branch_restores_context(self):
        vm, _, before, after = self.run_case(active=True)
        self.assertEqual(after, before)
        self.assertEqual(vm.stack, [])

    def test_historical_inactive_edge_exposes_the_extra_immediate_byte(self):
        prefix, join = self.asm.split("LiveAudio_PumpCheckCompletion:", 1)
        historical = prefix + "LiveAudio_PumpCheckCompletion:" + join.replace(
            "    rep #$20\n.a16\n", "", 1)
        with self.assertRaises(ImmediateWidthFault):
            PumpWidthVm(historical, active=False).execute()


if __name__ == "__main__":
    unittest.main()
