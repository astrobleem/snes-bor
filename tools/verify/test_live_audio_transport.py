"""Assembly and ABI checks for private live TAD interrupt transport leaves.

These tests do not launch an emulator and do not claim live audio admission,
SPC acknowledgment, or source-clock integration. Set DOTNET and POPPY_DLL to
assemble the emitted 65816 leaves with the configured Poppy toolchain.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from actor_s5_entity_fixture import symbols
from source_live_audio_transport import CONTROL_BYTES, READY_MAGIC, emit


ROOT = Path(__file__).resolve().parents[2]
CONTROL = 0x7E7700
SAMPLE_ROWS = 17


class LiveAudioTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sy = symbols(ROOT / "src" / "main.sym")
        cls.asm = emit(cls.sy, CONTROL)
        cls.pump_asm = emit(cls.sy, CONTROL, include_pump=True,
                            metadata_samples=SAMPLE_ROWS)

    def test_control_abi_and_interrupt_paths_are_explicit(self):
        self.assertEqual(CONTROL_BYTES, 32)
        self.assertIn(f"LiveAudio_ControlReady = ${CONTROL:06X}", self.asm)
        self.assertIn(f"cmp #${READY_MAGIC:04X}", self.asm)
        self.assertIn("LiveAudio_PhysicalEnabled = $7E7702", self.asm)
        self.assertIn("LiveAudio_IrqStage = $7E7704", self.asm)
        self.assertIn("LiveAudio_IrqCount = $7E7706", self.asm)
        self.assertIn("LiveAudio_HdmaMaskFault = $7E7708", self.asm)
        self.assertIn("cmp #$B6D0", self.asm)
        self.assertIn("cmp #1", self.asm)
        self.assertIn("lda.l $004211", self.asm)
        self.assertIn("jml " + f"${self.sy['irq_handler']:06X}", self.asm)
        self.assertIn("rti", self.asm)

    def test_preserves_full_context_and_limits_hardware_writes(self):
        for label in ("LiveAudio_NmiService:", "LiveAudio_Irq:"):
            body = self.asm.split(label, 1)[1]
            self.assertIn("php\n    rep #$38\n.a16\n.i16\n    pha\n    phx\n    phy\n    phd\n    phb", body)
            self.assertIn("lda #0\n    tcd\n    sep #$20\n.a8\n    lda #0\n    pha\n    plb\n    rep #$38", body)
        self.assertGreaterEqual(self.asm.count("rep #$30\n.a16\n.i16\n    plb"), 3)
        for forbidden in ("$002100", "$002118", "$00420B", "$004200"):
            self.assertNotIn(forbidden, self.asm)
        self.assertIn("sta.l $00420C", self.asm)
        self.assertIn("sta.l $004209", self.asm)
        self.assertIn("sta.l $00420A", self.asm)
        self.assertIn("and #$FE\n    beq LiveAudio_NmiCurrentMaskOk", self.asm)
        self.assertIn("and #$FE\n    beq LiveAudio_NmiShadowMaskOk", self.asm)
        for check in ("$004300", "$004301", "$004302", "$004304"):
            self.assertIn(f"lda.l {check}", self.asm)
        self.assertIn("and #$01", self.asm)
        self.assertNotIn("sta.l " + f"${self.sy['Nmi_HdmaEnable']:06X}", self.asm)
        self.assertNotIn("AudioStream_Ack", self.asm)

    def test_irq_uses_two_late_pump_stages_only(self):
        self.assertEqual(self.asm.count(f"jsl ${self.sy['Tad_StreamLatePump']:06X}"), 2)
        self.assertIn("lda #128\n    sta.l $004209", self.asm)
        self.assertIn("lda #200\n    sta.l $004209", self.asm)
        self.assertIn("lda #1\n    sta.l LiveAudio_IrqStage", self.asm)
        self.assertIn("lda #2\n    sta.l LiveAudio_IrqStage", self.asm)
        # 65816 STZ has no long-addressing form.
        self.assertNotIn("stz.l", self.asm)
        self.assertIn("LiveAudio_NmiRtl:\n    rtl", self.asm)
        self.assertIn("LiveAudio_IrqRti:\n    rti", self.asm)

    def test_optional_wrapper_uses_source_ack_and_durable_completion(self):
        asm = self.pump_asm
        self.assertEqual(asm.count("jsl LiveAudio_Pump"), 2)
        self.assertEqual(asm.count(f"jsl ${self.sy['Tad_StreamLatePump']:06X}"), 1)
        self.assertIn("lda.l $7E7700\n    cmp #$B6D8", asm)
        self.assertIn("lda.l $7E7702\n    cmp #1", asm)
        self.assertNotIn("lda.l $7E8120\n    cmp #$B6D8", asm)
        for sym in ("AudioSemantic_FootDieStreamActive", "TadPrivate_stream_pending",
                    "TadPrivate_stream_chunks_accepted", "AudioStream_SourceChunks",
                    "AudioStream_TransportOnly", "AudioStream_SerialPermit",
                    "SourceAudio_Status"):
            self.assertIn(f"${self.sy[sym]:06X}", asm)
        # Prefill is ACK-count based: cap is min(7, source chunk count), with
        # a serial permit only when no source transfer is pending.
        prefill = asm.split("LiveAudio_PrefillUpdate:", 1)[1]
        self.assertIn("cmp #7\n    bcc LiveAudio_PrefillTargetReady", prefill)
        self.assertIn("cmp.l $7E770A", prefill)
        self.assertIn("sta.l $7E28C5", prefill)  # transport mode
        self.assertIn("sta.l $7E28C6", prefill)  # one-transfer permit
        # Acknowledge/status remain backend-owned; retire only after status 4,
        # inactive physical stream and empty pending transfer.
        self.assertIn("cmp #4\n    beq LiveAudio_PumpStatusOk", asm)
        self.assertIn("lda.l $7E281A\n    beq LiveAudio_PumpInactive", asm)
        self.assertIn("lda.l $7E28B0\n    beq LiveAudio_PumpNoPending", asm)
        self.assertIn("cmp #$B6D9\n    beq LiveAudio_PumpAudioTicketOk", asm)
        self.assertIn("${:06X},x".format(0x33A01C), asm)
        self.assertIn("sta.l $7E8318", asm)  # channel 11 terminal phase
        self.assertIn("sta.l $7E82F8", asm)  # retire channel 11 active dword
        self.assertIn("sta.l $7EFFE6", asm)  # retire compact active word
        self.assertNotIn("sta.l $7E8122", asm)  # preserve root ACK state
        self.assertNotIn("sta.l $7E28F0", asm)  # backend owns completion
        self.assertIn("sta.l $7E770A", asm)  # mutable prefill target lives in WRAM
        self.assertNotIn("LiveAudio_PrefillTarget:\n    .dw", asm)

    def test_prefill_reference_edges_and_retirement_gate(self):
        def prefill(accepted, chunks, pending):
            target = min(7, chunks)
            if accepted >= target:
                return 0, 0
            return 2, int(pending == 0)

        self.assertEqual(prefill(0, 20, 0), (2, 1))
        self.assertEqual(prefill(6, 20, 1), (2, 0))
        self.assertEqual(prefill(7, 20, 0), (0, 0))
        self.assertEqual(prefill(2, 2, 0), (0, 0))
        self.assertEqual(prefill(0, 0, 0), (0, 0))

        def may_retire(status, active, pending, channel_active, offset):
            return (status == 4 and active == 0 and pending == 0
                    and channel_active != 0 and offset % 32 == 0
                    and offset < SAMPLE_ROWS * 32)

        self.assertTrue(may_retire(4, 0, 0, 1, 0))
        for args in ((3, 0, 0, 1, 0), (4, 1, 0, 1, 0),
                     (4, 0, 1, 1, 0), (4, 0, 0, 0, 0),
                     (4, 0, 0, 1, 1), (4, 0, 0, 1, SAMPLE_ROWS * 32)):
            self.assertFalse(may_retire(*args), args)

    def test_emitted_context_trace_clears_backend_state_and_restores_exact_entry(self):
        def execute_trace(lines, cpu):
            for raw in lines:
                line = raw.split(";", 1)[0].strip().lower()
                if not line or line.endswith(":") or line.startswith("."):
                    continue
                op, _, operand = line.partition(" ")
                operand = operand.strip()
                if op == "php": cpu.stack.append((8, cpu.p))
                elif op in ("rep", "sep"):
                    mask = int(operand.removeprefix("#$"), 16)
                    cpu.p = cpu.p & ~mask if op == "rep" else cpu.p | mask
                elif op == "pha": cpu.stack.append((16 if cpu.p & 0x20 == 0 else 8, cpu.a))
                elif op == "phx": cpu.stack.append((16 if cpu.p & 0x10 == 0 else 8, cpu.x))
                elif op == "phy": cpu.stack.append((16 if cpu.p & 0x10 == 0 else 8, cpu.y))
                elif op == "phd": cpu.stack.append((16, cpu.dp))
                elif op == "phb": cpu.stack.append((8, cpu.dbr))
                elif op == "lda":
                    if operand.startswith("#$"):
                        value = int(operand[2:], 16)
                    elif operand.startswith("#"):
                        value = int(operand[1:], 10)
                    else:
                        value = 0x5A5A
                    cpu.a = value & (0xFF if cpu.p & 0x20 else 0xFFFF)
                elif op == "tcd": cpu.dp = cpu.a
                elif op == "plb": _, cpu.dbr = cpu.stack.pop()
                elif op == "pld": _, cpu.dp = cpu.stack.pop()
                elif op == "ply": _, cpu.y = cpu.stack.pop()
                elif op == "plx": _, cpu.x = cpu.stack.pop()
                elif op == "pla": _, cpu.a = cpu.stack.pop()
                elif op == "plp": _, cpu.p = cpu.stack.pop()
                # Non-context arithmetic, compares, branches and stores are
                # intentionally omitted; this trace follows the owned path.

        for a8 in (False, True):
            for x8 in (False, True):
                for decimal in (False, True):
                    p = (0x20 if a8 else 0) | (0x10 if x8 else 0) | (0x08 if decimal else 0) | 0x04
                    initial = dict(a=0x6B3C, x=0x127A if not x8 else 0x7A,
                                   y=0x43D1 if not x8 else 0xD1, dp=0x8E32,
                                   dbr=0x6F, p=p)
                    for name, call in (("LiveAudio_NmiService", "Tad_StreamOneShotHdmaFence"),
                                       ("LiveAudio_Irq", "Tad_StreamLatePump")):
                        section = self.asm.split(name + ":", 1)[1]
                        prologue = section.split("jsl " + f"${self.sy[call]:06X}", 1)[0]
                        cpu = type("CPU", (), dict(**initial, stack=[]))()
                        execute_trace(prologue.splitlines(), cpu)
                        self.assertEqual((cpu.p & 0x08, cpu.dp, cpu.dbr), (0, 0, 0), name)
                        restore_paths = (("LiveAudio_NmiDone:", "rtl"),) if name.endswith("NmiService") else (
                            ("LiveAudio_IrqReturn:", "rti"),
                            ("LiveAudio_IrqDelegate:", "jml "),
                        )
                        for restore_label, terminator in restore_paths:
                            saved_cpu = type("CPU", (), dict(**initial, stack=[]))()
                            execute_trace(prologue.splitlines(), saved_cpu)
                            restore = self.asm.split(restore_label, 1)[1].split(terminator, 1)[0]
                            execute_trace(restore.splitlines(), saved_cpu)
                            self.assertEqual((saved_cpu.p, saved_cpu.a, saved_cpu.x, saved_cpu.y,
                                              saved_cpu.dp, saved_cpu.dbr),
                                             tuple(initial[k] for k in ("p", "a", "x", "y", "dp", "dbr")),
                                             (name, restore_label))
                            self.assertEqual(saved_cpu.stack, [], (name, restore_label))

    def test_emitted_leaves_assemble_with_configured_poppy(self):
        dotnet = os.environ.get("DOTNET")
        poppy = os.environ.get("POPPY_DLL")
        if not dotnet or not poppy or not Path(dotnet).is_file() or not Path(poppy).is_file():
            self.skipTest("set DOTNET and POPPY_DLL to assemble with Poppy")
        with tempfile.TemporaryDirectory(prefix="live-audio-transport-") as td:
            folder = Path(td)
            for name, asm in (("transport", self.asm), ("pump", self.pump_asm)):
                source = folder / f"{name}.pasm"
                binary = folder / f"{name}.bin"
                symfile = folder / f"{name}.sym"
                source.write_text(".snes\n.bank 39\n.org $8000\n" + asm, encoding="utf-8")
                proc = subprocess.run(
                    [dotnet, poppy, str(source), "-o", str(binary), "-s", str(symfile)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertTrue(binary.is_file())
                self.assertGreater(binary.stat().st_size, 0)
                assembled = symfile.read_text(encoding="utf-8-sig")
                for label in ("LiveAudio_NmiService", "LiveAudio_Irq", "LiveAudio_NmiRtl",
                              "LiveAudio_IrqRti"):
                    self.assertIn(label, assembled)
                if name == "pump":
                    self.assertIn("LiveAudio_Pump", assembled)
                    self.assertIn("LiveAudio_PrefillUpdate", assembled)


if __name__ == "__main__":
    unittest.main()
