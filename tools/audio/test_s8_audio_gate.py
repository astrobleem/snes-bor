"""Focused S8 source, TIMEOVER, and fail-closed build ownership checks."""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_audio
import plan_action_residency as planner
import verify_runtime_audio as verifier
import generate_normal_audio
import s8_audio_scope


class S8AudioTests(unittest.TestCase):
    def test_normal_source_closure_and_new_bindings(self):
        data = generate_normal_audio.bindings()
        self.assertEqual(len(data["normal_scope"]["stages"]), 14)
        self.assertEqual(len(data["normal_scope"]["roster_indices"]), 37)
        old = s8_audio_scope.roster()
        self.assertEqual(len(old), 45)
        spec = json.loads(s8_audio_scope.baseline("tools/audio/batch_b_audio.json"))
        from generate_batch_b_assembly import SEMANTICS
        for i in range(len(old)):
            expected = spec["diesounds"].get(str(i), {}) if i < 21 else {}
            self.assertEqual(data["rows"][i]["source_id"], expected.get("source", 255))
            self.assertEqual(data["rows"][i]["semantic"], int(SEMANTICS[expected.get("semantic", "NONE")][1:], 16))
        self.assertEqual(data["rows"][45]["asset"], "bor-original:DATA\\SOUNDS\\DIE1.WAV")
        self.assertEqual((data["rows"][45]["source_id"], data["rows"][45]["semantic"]), (1, 1))
        self.assertEqual(data["rows"][46]["classification"], "NEW_SOURCE_NO_DIESOUND")

    def test_unknown_new_source_diesound_rejected(self):
        import entity_parse
        original = entity_parse.parse_entity
        def changed(text):
            result = original(text)
            if result.get("name", "").lower() == "ramon":
                result["diesound"] = "DATA\\SOUNDS\\UNKNOWN_NEW.WAV"
            return result
        with patch.object(entity_parse, "parse_entity", changed), self.assertRaisesRegex(SystemExit, "no source backend"):
            generate_normal_audio.bindings()

    def test_baseline_adapter_change_rejected(self):
        original = Path.read_bytes
        def changed(path):
            result = original(path)
            return result + b"changed" if path == verifier.ROOT / "src/core/vm/audio_batch_b_generated.pasm" else result
        with patch.object(Path, "read_bytes", changed), self.assertRaisesRegex(SystemExit, "accepted audio adapter changed"):
            s8_audio_scope.accepted_inventory()

    def test_death_selector_isolated_assembly(self):
        dotnet = os.environ.get("DOTNET", r"C:\Users\chad\.dotnet\dotnet.exe")
        poppy = os.environ.get("POPPY_DLL", r"E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll")
        self.assertTrue(Path(dotnet).exists() and Path(poppy).exists(), "isolated assembler unavailable")
        source = (verifier.ROOT / "src/core/vm/vm_native_engine.pasm").read_text()
        code = "AudioSemantic_EmitDiesound:" + source.split("AudioSemantic_EmitDiesound:", 1)[1].split("; Shared stream backend policy", 1)[0]
        code += (verifier.ROOT / "src/core/vm/audio_batch_b_generated.pasm").read_text()
        code += generate_normal_audio.OUTPUT.read_text()
        defined = set(re.findall(r"(?m)^(\w+)\s*(?::|=)", code))
        referenced = set(re.findall(r"\b[A-Za-z_]\w*\b", code))
        symbols = {}
        for bank, address, name in re.findall(r"(?m)^([0-9A-Fa-f]+):([0-9A-Fa-f]+)\s+(\w+)", (verifier.ROOT / "src/main.sym").read_text()):
            if name in referenced and name not in defined:
                symbols[name] = (int(bank, 16) << 16) | int(address, 16)
        header = ".snes\n.bank 1\n.org $8000\n" + "".join(f"{k} = ${v:X}\n" for k, v in symbols.items())
        with tempfile.TemporaryDirectory(prefix="s8-audio-asm-") as temp:
            path = Path(temp) / "selector.pasm"
            path.write_text(header + code)
            result = subprocess.run([dotnet, poppy, str(path), "-o", str(Path(temp) / "selector.bin")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runtime_inventory_never_explores_and_includes_normal(self):
        explorer = Mock()
        explorer.explore_stage.side_effect = AssertionError("obsolete explorer called")
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, runtime_sfx_states=explorer):
            output = Path(tmp) / "actions.json"
            with contextlib.redirect_stdout(io.StringIO()):
                planner.main(True, output)
            data = json.loads(output.read_text())
        explorer.explore_stage.assert_not_called()
        players = {m["identity"] for m in data["models"] if m["family"] == "bor-original" and m["playable"]}
        self.assertEqual(players, {"KULA", "MAXIMA", "MARY", "MIGHTY"})
        self.assertTrue({"RAMON", "MISC\\TIME"} <= {m["identity"] for m in data["models"]})
        self.assertIn("bor-original:DATA\\SOUNDS\\TIMEOVER.WAV", data["source_hashes"])
        self.assertFalse(any(a["role"].endswith("_is_grab") for m in data["models"] for a in m["actions"]))

    def test_linked_timeover_data(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertIn("bor-original:DATA\\SOUNDS\\TIMEOVER.WAV", verifier.verify_linked_data())

    def test_corrupt_blob_rejected(self):
        original = Path.read_bytes
        def corrupt(path):
            data = original(path)
            return data + b"corruption" if path == verifier.rebuild.OUT_BIN else data
        with patch.object(Path, "read_bytes", corrupt), self.assertRaisesRegex(SystemExit, "inputs changed"):
            verifier.verify_linked_data()

    def test_stale_source_sample_rejected(self):
        original = Path.read_bytes
        def corrupt(path):
            data = original(path)
            return data + b"corruption" if path.name == "timeover.wav" else data
        with patch.object(Path, "read_bytes", corrupt), self.assertRaisesRegex(SystemExit, "inputs changed"):
            verifier.verify_linked_data()

    def test_wrong_timer_semantic_rejected(self):
        original = Path.read_text
        def corrupt(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path == verifier.ROOT / "src/main.pasm":
                text = text.replace("AUDIO_SEMANTIC_TIMEOVER   = $1D", "AUDIO_SEMANTIC_TIMEOVER   = $0A")
            return text
        with patch.object(Path, "read_text", corrupt), contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(SystemExit, "TIMEOVER semantic"):
            verifier.verify_linked_data()

    def test_sfx_only_has_no_music_and_propagates_gate_failure(self):
        calls = []
        def run(*args):
            calls.append(args)
            if args[0] == "verify_sfx_production_banks.py":
                raise RuntimeError("coverage failure")
        with patch.object(build_audio, "run", run), self.assertRaisesRegex(RuntimeError, "coverage failure"):
            build_audio.main(sfx_only=True)
        self.assertIn(("plan_action_residency.py", "--runtime-actions"), calls)
        self.assertIn(("verify_sfx_production_banks.py", "--runtime-actions"), calls)
        self.assertFalse(any("music" in c[0] or "runtime_sfx_states" in c[0] for c in calls))

    def test_default_build_fails_before_music_encoding(self):
        calls = []
        def run(*args):
            calls.append(args)
            if args[0] == "verify_sfx_production_banks.py":
                raise RuntimeError("coverage failure")
        with patch.object(build_audio, "run", run), self.assertRaises(RuntimeError):
            build_audio.main()
        self.assertFalse(any("music" in c[0] for c in calls))


if __name__ == "__main__":
    unittest.main()
