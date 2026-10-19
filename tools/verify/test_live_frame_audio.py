"""Execute the emitted captured-frame audio admission in a small 65816 VM."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_compile"))
sys.path.insert(0, str(ROOT / "tools" / "verify"))
from actor_s5_entity_fixture import symbols as read_symbols
from source_live_frame_audio_native import (CHANNELS, CONTROL, REQUEST, TABLE,
                                           emit)


class AudioAdmissionVM:
    """Interpreter for the emitted 65816 subset; only three APIs are spies."""
    C, Z, V, N, M, X = 1, 2, 0x40, 0x80, 0x20, 0x10

    def __init__(self, asm, sy):
        self.labels, self.ops = {}, []
        for raw in asm.splitlines():
            line = raw.split(";", 1)[0].strip().lower()
            if not line or line.startswith(".") or "=" in line:
                continue
            if line.endswith(":"):
                self.labels[line[:-1]] = len(self.ops)
            else:
                self.ops.append(line)
        self.sy = sy
        self.mem = {}
        self.writes = []
        self.a, self.x, self.y = 0x6B3C, 0x127A, 0x43D1
        self.dp, self.dbr, self.sp, self.p = 0x8E32, 0x6F, 0x1FF0, 0xFD
        self.pc = self.labels["liveframeaudio_admit"]
        self.stack = []
        self.calls = []
        self.foreign_checks = 0
        self.offers = 0
        self.offer_selections = []
        self.physical_requests = []
        self.external_by_address = {
            sy["SourceForeignWork_Check"]: "foreign",
            sy["SourceSoundChannels4086_Offer"]: "offer",
            sy["SourceAudio_StartPreparedNear"]: "start",
        }

    @staticmethod
    def num(text):
        text = text.strip().removeprefix("#")
        return int(text[1:], 16) if text.startswith("$") else int(text, 10)

    def address(self, operand, *, long=False):
        operand = operand.strip().lower()
        if operand.endswith(",s"):
            offset = self.num(operand[:-2])
            return 0x100 | ((self.sp + offset) & 0xFF)
        index = 0
        if ",x" in operand:
            operand, _ = operand.rsplit(",x", 1)
            index = self.x
        elif ",y" in operand:
            operand, _ = operand.rsplit(",y", 1)
            index = self.y
        base = sum(self.num(piece) for piece in operand.split("+") if piece)
        if not long:
            base = (self.dbr << 16) | (base & 0xFFFF)
        return (base + index) & 0xFFFFFF

    def read8(self, address):
        return self.mem.get(address & 0xFFFFFF, 0)

    def write8(self, address, value):
        address &= 0xFFFFFF
        self.mem[address] = value & 0xFF
        self.writes.append(address)

    def read(self, address, width):
        out = 0
        for i in range(width // 8):
            out |= self.read8(address + i) << (8 * i)
        return out

    def write(self, address, value, width):
        for i in range(width // 8):
            self.write8(address + i, value >> (8 * i))

    def width(self):
        return 8 if self.p & self.M else 16

    def nz(self, value, width=None):
        width = self.width() if width is None else width
        mask = (1 << width) - 1
        self.p = (self.p & ~(self.N | self.Z)) | (
            self.N if value & (1 << (width - 1)) else 0) | (self.Z if not (value & mask) else 0)

    def push(self, value, size):
        self.stack.append((value, size))
        for i in range(size):
            self.write8(0x100 | ((self.sp - i) & 0xFF), value >> (8 * (size - 1 - i)))
        self.sp = (self.sp - size) & 0xFFFF

    def pop(self):
        value, size = self.stack.pop()
        self.sp = (self.sp + size) & 0xFFFF
        return value

    def external(self, address):
        name = self.external_by_address.get(address)
        if name == "foreign":
            self.foreign_checks += 1
            self.a = 0
            self.p &= ~self.C
        elif name == "offer":
            self.offers += 1
            self.write(self.sy["SourceSoundChannels4086_Status"], 0, 16)
            # Independent oracle for vm_source_sound_channels.pasm: free rows
            # overwrite Selected while scanning 0..11, so the last free row wins.
            selected = [i for i in range(12)
                        if self.read(0x7EFF88 + i * 8 + 6, 16) == 0]
            channel = max(selected) if selected else 0xFFFF
            self.offer_selections.append(channel)
            if channel == 0xFFFF:
                self.write(self.sy["SourceSoundChannels4086_Status"], 1, 16)
            self.write(self.sy["SourceSoundChannels4086_Selected"], channel, 16)
            self.a = 0
            self.p &= ~self.C
        elif name == "start":
            self.physical_requests.append({
                "sample_id": self.read(CONTROL + 16, 16),
                "source_id": self.read(self.sy["AudioStream_SourceId"], 8),
                "brr_pointer": self.read(self.sy["SourceAudio_BaseLo"], 16),
                "brr_bank": self.read(self.sy["SourceAudio_BaseBank"], 8),
                "brr_bytes": self.read(self.sy["AudioStream_SourceLength"], 16),
                "brr_bytes_high": self.read(self.sy["SourceAudio_LengthHi"], 8),
                "chunks": self.read(self.sy["AudioStream_SourceChunks"], 16),
                "source_index": self.read(self.sy["SourceAudio_Index"], 16),
                "phase_q12": self.read(CHANNELS + 11 * 40 + 32, 32),
                "period_q12": self.read(CHANNELS + 11 * 40 + 36, 32),
            })
            self.a = 0
            self.p &= ~self.C
        else:
            raise AssertionError(f"unexpected external JSL ${address:06X}")

    def run(self):
        for _ in range(25000):
            op = self.ops[self.pc]
            self.pc += 1
            pair = op.split(None, 1)
            ins, arg = pair[0], pair[1] if len(pair) > 1 else ""
            if ins in ("php", "phb", "phd", "phx", "phy", "pha"):
                reg = {"php": self.p, "phb": self.dbr, "phd": self.dp,
                       "phx": self.x, "phy": self.y, "pha": self.a}[ins]
                size = 1 if ins in ("php", "phb") or (ins == "pha" and self.width() == 8) else 2
                self.push(reg, size)
            elif ins in ("plp", "plb", "pld", "plx", "ply", "pla"):
                value = self.pop()
                target = {"plp": "p", "plb": "dbr", "pld": "dp", "plx": "x", "ply": "y", "pla": "a"}[ins]
                setattr(self, target, value)
                if ins in ("plb", "pld", "plx", "ply", "pla"):
                    self.nz(value, 8 if ins == "plb" else (self.width() if ins == "pla" else 16))
            elif ins in ("rep", "sep"):
                mask = self.num(arg)
                self.p = self.p & ~mask if ins == "rep" else self.p | mask
            elif ins in ("lda", "lda.l", "lda.w", "ldx", "ldx.l", "ldy"):
                width = self.width() if ins.startswith("lda") else 16
                if arg.startswith("#"):
                    value = self.num(arg)
                else:
                    long = ins.endswith(".l")
                    value = self.read(self.address(arg, long=long), width)
                setattr(self, "a" if ins.startswith("lda") else ("x" if ins.startswith("ldx") else "y"), value)
                self.nz(value, width)
            elif ins in ("sta", "sta.l", "sta.w", "stx", "sty", "stz", "stz.l"):
                width = self.width() if ins.startswith("sta") or ins.startswith("stz") else 16
                value = 0 if ins.startswith("stz") else (self.a if ins.startswith("sta") else (self.x if ins == "stx" else self.y))
                self.write(self.address(arg, long=ins.endswith(".l")), value, width)
            elif ins in ("cmp", "cmp.l", "cmp.w", "cpx", "cpx.l"):
                width = self.width() if ins.startswith("cmp") else 16
                left = self.a if ins.startswith("cmp") else self.x
                right = self.num(arg) if arg.startswith("#") else self.read(self.address(arg, long=ins.endswith(".l")), width)
                mask = (1 << width) - 1
                diff = (left - right) & mask
                self.p = (self.p & ~(self.C | self.Z | self.N)) | (self.C if left >= right else 0) | (self.Z if diff == 0 else 0) | (self.N if diff & (1 << (width - 1)) else 0)
            elif ins in ("and", "and.l", "ora", "ora.l", "eor", "eor.l"):
                right = self.num(arg) if arg.startswith("#") else self.read(self.address(arg, long=ins.endswith(".l")), self.width())
                base = ins.split(".")[0]
                self.a = {"and": self.a & right, "ora": self.a | right, "eor": self.a ^ right}[base] & ((1 << self.width()) - 1)
                self.nz(self.a)
            elif ins in ("adc", "adc.l", "sbc", "sbc.l"):
                right = self.num(arg) if arg.startswith("#") else self.read(self.address(arg, long=ins.endswith(".l")), self.width())
                width = self.width(); mask = (1 << width) - 1; carry = int(bool(self.p & self.C))
                raw = self.a + right + carry if ins.startswith("adc") else self.a - right - (1 - carry)
                self.a = raw & mask
                self.p = (self.p & ~self.C) | (self.C if (raw > mask if ins.startswith("adc") else raw >= 0) else 0)
                self.nz(self.a, width)
            elif ins in ("asl", "lsr", "inc", "dec"):
                width = self.width(); mask = (1 << width) - 1
                if ins in ("asl", "lsr"):
                    self.p = (self.p & ~self.C) | (self.C if (self.a & (1 << (width - 1)) if ins == "asl" else self.a & 1) else 0)
                    self.a = ((self.a << 1) if ins == "asl" else (self.a >> 1)) & mask
                else:
                    self.a = (self.a + (1 if ins == "inc" else -1)) & mask
                self.nz(self.a, width)
            elif ins == "ldx":
                self.x = self.num(arg); self.nz(self.x, 16)
            elif ins == "tax":
                self.x = self.a & 0xFFFF; self.nz(self.x, 16)
            elif ins == "tay":
                self.y = self.a & 0xFFFF; self.nz(self.y, 16)
            elif ins == "txa":
                self.a = self.x & ((1 << self.width()) - 1); self.nz(self.a)
            elif ins == "tya":
                self.a = self.y & ((1 << self.width()) - 1); self.nz(self.a)
            elif ins == "inx":
                self.x = (self.x + 1) & 0xFFFF; self.nz(self.x, 16)
            elif ins == "dex":
                self.x = (self.x - 1) & 0xFFFF; self.nz(self.x, 16)
            elif ins == "clc": self.p &= ~self.C
            elif ins == "sec": self.p |= self.C
            elif ins in ("beq", "bne", "bcc", "bcs", "bmi", "bpl", "bvs", "bvc"):
                cond = {"beq": bool(self.p & self.Z), "bne": not self.p & self.Z,
                        "bcc": not self.p & self.C, "bcs": bool(self.p & self.C),
                        "bmi": bool(self.p & self.N), "bpl": not self.p & self.N,
                        "bvs": bool(self.p & self.V), "bvc": not self.p & self.V}[ins]
                if cond: self.pc = self.labels[arg]
            elif ins in ("jmp", "bra"):
                self.pc = self.labels[arg]
            elif ins == "jsl":
                target = arg.strip().lower()
                if target in self.labels:
                    self.calls.append(self.pc)
                    self.pc = self.labels[target]
                else:
                    address = self.address(arg, long=True)
                    if address in self.external_by_address:
                        self.external(address)
                    else:
                        raise AssertionError(f"unexpected JSL {arg} -> ${address:06X}")
            elif ins == "rtl":
                if self.calls:
                    self.pc = self.calls.pop()
                else:
                    return self.a, bool(self.p & self.C)
            elif ins == "nop": pass
            else:
                raise AssertionError(f"unsupported emitted opcode: {op}")
        raise AssertionError("live frame audio instruction bound")


def put16(vm, at, value): vm.write(at, value, 16)
def put32(vm, at, value): vm.write(at, value, 32)


def make_vm(**overrides):
    sy = read_symbols(ROOT / "src/main.sym")
    asm = emit(sy)
    vm = AudioAdmissionVM(asm, sy)
    # Valid captured phase-1 SOUND (service 9), source slot 7, ticket index 9.
    for address, value in ((CONTROL, 0xB6D9), (CONTROL + 2, 0), (CONTROL + 28, 100),
                           (sy["SourceUpdateFrame4086_Ready"], 0xB4E3),
                           (sy["SourceUpdateFrame4086_State"], 1),
                           (sy["SourceUpdateFrame4086_Pending"], 2),
                           (sy["SourceUpdateFrame4086_Slot"], 7),
                           (sy["SourceUpdateFrame4086_Handle"], 0x4100),
                           (sy["SourceUpdateFrame4086_Request"], 0x44),
                           (sy["SourceUpdateFrame4086_Bank"], 60),
                           (sy["SourceUpdateFrame4086_FrameData"], 0x8840),
                           (sy["SourceUpdateFrame4086_TableEnd"], 0xFAF7),
                           (sy["SourceFrameEffectPlan4086_Ready"], 0xB4F2),
                           (sy["SourceFrameEffectPlan4086_State"], 1),
                           (sy["SourceFrameEffectPlan4086_Service"], 9),
                           (sy["SourceFrameEffectPlan4086_Acknowledged"], 0),
                           (sy["SourceFrameEffectPlan4086_Slot"], 7),
                           (sy["SourceFrameEffectPlan4086_Handle"], 0x4100),
                           (sy["SourceFrameEffectPlan4086_Frame"], 0x44),
                           (sy["SourceFrameEffectPlan4086_Index"], 9),
                           (sy["SourceForeignWork_Generation"], 0x1234),
                           (sy["SourceForeignWork_Generation"] + 2, 0x5678),
                           (sy["AudioSemantic_FootDieStreamActive"], 0),
                           (sy["AudioSemantic_StreamRequestCount"], 0),
                           (sy["SourceAudio_Status"], 0)):
        put16(vm, address, value)
    # Frame sound count/index 0, sound ID 0 in the actual frame-data bank.
    frame = (60 << 16) | 0x8840
    put16(vm, frame + 16, 0)
    put16(vm, frame + 18, 0)
    # Exact LVA1/version/count/stride/raw-volume compiler table.
    for off, value in ((0, 0x564C), (2, 0x3141), (4, 1), (6, 30), (8, 32), (10, 100)):
        put16(vm, TABLE + off, value)
    row = TABLE + 12
    put32(vm, row + 0, 272007)
    put32(vm, row + 4, 22050)
    put32(vm, row + 8, 2048)
    put32(vm, row + 12, 44 << 12)
    put32(vm, row + 16, 272007 << 12)
    vm.write(row + 20, 0xE00000, 24)
    vm.write8(row + 23, 1)  # admitted source row
    vm.write(row + 24, 8192, 24)
    vm.write8(row + 27, 0)
    put16(vm, row + 28, 57)
    vm.write8(row + 30, 8)
    vm.write8(row + 31, 1)
    for name, value in overrides.items():
        if name == "plan_handle": put16(vm, sy["SourceFrameEffectPlan4086_Handle"], value)
        elif name == "stream_active": put16(vm, sy["AudioSemantic_FootDieStreamActive"], value)
        elif name == "metadata_flags": vm.write8(row + 23, value)
        elif name == "metadata_channels": vm.write8(row + 31, value)
        elif name == "active_channel": put16(vm, CHANNELS + value * 40, 1)
        elif name == "physical_active": put16(vm, sy["AudioSemantic_FootDieStreamActive"], value)
        else: raise ValueError(name)
    return vm, sy


def call(vm):
    before = (vm.a, vm.x, vm.y, vm.dp, vm.dbr, vm.sp, vm.p)
    vm.pc = vm.labels["liveframeaudio_admit"]
    result = vm.run()
    after = (vm.a, vm.x, vm.y, vm.dp, vm.dbr, vm.sp, vm.p & ~vm.C)
    # A is the documented status result; X/Y/DP/DBR/SP are preserved, while
    # carry alone reports the fault bit.
    assert after[1:6] == before[1:6] and after[6] == (before[6] & ~vm.C), (before, after)
    assert vm.stack == [] and not vm.calls
    return result


class LiveFrameAudioTests(unittest.TestCase):
    def test_captured_sound9_admits_source_phase_and_prepared_audio_once(self):
        vm, sy = make_vm()
        self.assertEqual(call(vm), (0, False))
        self.assertEqual(vm.offers, 1)
        self.assertEqual(len(vm.physical_requests), 1)
        channel = CHANNELS + 11 * 40
        self.assertEqual(vm.read(channel, 16), 1)  # active
        self.assertEqual(vm.read(channel + 8, 16), 0)  # source sound id
        self.assertEqual(vm.read(channel + 16, 32), 1)  # first play id
        self.assertEqual(vm.read(channel + 20, 16), 64)
        self.assertEqual(vm.read(channel + 24, 16), 64)
        self.assertEqual(vm.read(channel + 32, 32), 44 << 12)
        self.assertEqual(vm.read(channel + 36, 32), 2048)
        self.assertEqual(vm.read(TABLE + 10, 16), 100)  # captured raw volume
        self.assertEqual(vm.read(CONTROL + 28, 16), 100)
        self.assertEqual(vm.offer_selections, [11])
        self.assertEqual(vm.physical_requests[0]["phase_q12"], 44 << 12)
        self.assertEqual(vm.physical_requests[0]["period_q12"], 2048)
        self.assertEqual(vm.physical_requests[0]["source_id"], 0xFF)
        self.assertEqual(vm.physical_requests[0]["brr_pointer"], 0)
        self.assertEqual(vm.physical_requests[0]["brr_bank"], 0xE0)
        self.assertEqual(vm.physical_requests[0]["brr_bytes"], 8192)
        self.assertEqual(vm.physical_requests[0]["chunks"], 57)
        self.assertEqual(vm.read(sy["AudioSemantic_StreamRequestCount"], 16), 1)
        self.assertEqual(vm.read(CONTROL + 2, 16), 1)

    def test_identical_ticket_replay_does_not_offer_or_restart(self):
        vm, _ = make_vm()
        self.assertEqual(call(vm), (0, False))
        before_rows = bytes(vm.read8(CHANNELS + i) for i in range(480))
        before_play = vm.read(0x7EFF88 + 11 * 8 + 4, 16)
        self.assertEqual(call(vm), (0, False))
        self.assertEqual(vm.offers, 1)
        self.assertEqual(len(vm.physical_requests), 1)
        self.assertEqual(bytes(vm.read8(CHANNELS + i) for i in range(480)), before_rows)
        self.assertEqual(vm.read(0x7EFF88 + 11 * 8 + 4, 16), before_play)

    def test_busy_physical_stream_or_active_channel_stays_pending_atomically(self):
        for overrides in ({"stream_active": 1}, {"active_channel": 4}):
            with self.subTest(overrides=overrides):
                vm, sy = make_vm(**overrides)
                before = bytes(vm.read8(CHANNELS + i) for i in range(480))
                before_play = bytes(vm.read8(0x7EFF88 + i) for i in range(96))
                self.assertEqual(call(vm), (1, False))
                self.assertEqual(bytes(vm.read8(CHANNELS + i) for i in range(480)), before)
                self.assertEqual(bytes(vm.read8(0x7EFF88 + i) for i in range(96)), before_play)
                self.assertEqual(vm.read(sy["AudioSemantic_StreamRequestCount"], 16), 0)
                self.assertEqual(vm.physical_requests, [])

    def test_unsupported_metadata_stays_pending_before_source_channel_mutation(self):
        for overrides in ({"metadata_flags": 0}, {"metadata_channels": 2}):
            with self.subTest(overrides=overrides):
                vm, sy = make_vm(**overrides)
                before = bytes(vm.read8(CHANNELS + i) for i in range(480))
                before_play = bytes(vm.read8(0x7EFF88 + i) for i in range(96))
                self.assertEqual(call(vm), (1, False))
                self.assertEqual(bytes(vm.read8(CHANNELS + i) for i in range(480)), before)
                self.assertEqual(bytes(vm.read8(0x7EFF88 + i) for i in range(96)), before_play)
                self.assertEqual(vm.physical_requests, [])
                self.assertEqual(vm.read(sy["AudioSemantic_StreamRequestCount"], 16), 0)

    def test_mismatched_captured_sound_identity_faults_before_writes(self):
        vm, sy = make_vm(plan_handle=0x4102)
        before_channels = bytes(vm.read8(CHANNELS + i) for i in range(480))
        before_play = bytes(vm.read8(0x7EFF88 + i) for i in range(96))
        before_count = vm.read(sy["AudioSemantic_StreamRequestCount"], 16)
        self.assertTrue(call(vm)[1])
        self.assertEqual(bytes(vm.read8(CHANNELS + i) for i in range(480)), before_channels)
        self.assertEqual(bytes(vm.read8(0x7EFF88 + i) for i in range(96)), before_play)
        self.assertEqual(vm.read(sy["AudioSemantic_StreamRequestCount"], 16), before_count)
        self.assertEqual(vm.physical_requests, [])


if __name__ == "__main__":
    unittest.main()
