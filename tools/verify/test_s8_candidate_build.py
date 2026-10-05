"""Focused candidate gating/output tests; no compiler, packer, or emulator."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tools/verify"),
                str(ROOT / "tools/bor_compile"), str(ROOT / "tools/audio")]
import build_rom as build
import _harness as harness
import production_campaign
import compiler
import build_normal_sa1_candidate as normal_sa1


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="s8-candidate-test-")
        self.addCleanup(self.temp.cleanup)
        self.old_cwd = Path.cwd()
        self.addCleanup(os.chdir, self.old_cwd)
        os.chdir(self.temp.name)
        self.root = Path.cwd()
        for directory in ("src", "tools/audio", "build", "distribution"):
            Path(directory).mkdir(parents=True, exist_ok=True)
        self.protected = {p: p.encode() for p in
                          ("build/bor.sfc", "build/bor.msu", "distribution/bor.sfc", "distribution/bor.msu")}
        for p, data in self.protected.items():
            Path(p).write_bytes(data)
        Path("distribution/bor-1.pcm").write_bytes(b"fixture music")
        Path("tools/audio/music_catalog.json").write_text(json.dumps({"tracks": [{
            "track_id": 1, "msu_pcm_path": "distribution/bor-1.pcm",
            "msu_pcm_hash": hashlib.sha256(b"fixture music").hexdigest()}]}))

    def assert_protected(self):
        for p, data in self.protected.items():
            self.assertEqual(Path(p).read_bytes(), data, p)

    def test_normal_sa1_models_follow_normal_character_selector(self):
        original = Path.cwd()
        os.chdir(ROOT)
        try:
            _, models = normal_sa1._campaign_inputs()
        finally:
            os.chdir(original)
        selected = {row['name']: row['runtime_slot'] for row in models if row['playable']}
        self.assertEqual(selected, {'kula': 22, 'maxima': 23, 'mary': 24, 'mighty': 25})
        self.assertEqual(sum(not row['playable'] for row in models), 17)
        self.assertNotIn('ralf', selected)

    def test_availability_is_explicit_and_resets_to_default(self):
        sets = [SimpleNamespace(name=n, set_id=i, ifcomplete=0)
                for i, n in enumerate(("Easy", "Normal", "Hard", "Bonus"))]
        def table(name):
            text = Path("tools/audio/campaign_config.pasm").read_text()
            return re.search(rf"{name}:\s*\.db ([^\n]+)", text)[1]
        authority = SimpleNamespace(sets=[SimpleNamespace(name=name, source_id=index, entries=[None] * len(build.CAMPAIGN_ENTRY_MAPS[{"Easy":"BOR_ORIGINAL","Normal":"BOR_NORMAL_1A_INTERNAL","Hard":"BOR_HARD","Bonus":"BOR_BONUS"}[name]]))
                                         for index, name in enumerate(('Easy', 'Normal', 'Hard', 'Bonus'))])
        with patch.object(build, "parse_levels_from_pak", return_value=sets), \
             patch.object(compiler, 'Source'), patch.object(compiler, 'project', return_value=authority):
            build.write_campaign_include()
            self.assertEqual(table("BorSet_ContentAvailable"), "0, 0, 0, 0")
            build.write_campaign_include(normal_candidate=True)
            self.assertEqual(table("BorSet_ContentAvailable"), "1, 1, 0, 0")
            self.assertIn("CAMPAIGN_BOR_NORMAL_DEV", table("BorSet_CampaignMap"))
            build.write_campaign_include(normal_candidate=True, hard_candidate=True)
            self.assertEqual(table("BorSet_ContentAvailable"), "1, 1, 1, 0")
            self.assertIn("CAMPAIGN_BOR_NORMAL_DEV", table("BorSet_CampaignMap"))
            build.write_campaign_include()
            self.assertEqual(table("BorSet_ContentAvailable"), "0, 0, 0, 0")
            self.assertNotIn("CAMPAIGN_BOR_NORMAL_DEV", table("BorSet_CampaignMap"))

    def test_candidate_outputs_and_music_are_isolated(self):
        with contextlib.redirect_stdout(io.StringIO()):
            build.write_build_outputs(b"candidate rom", b"candidate msu", normal_candidate=True)
        self.assert_protected()
        self.assertEqual(Path("build/s8_candidate/bor.sfc").read_bytes(), b"candidate rom")
        self.assertEqual(Path("build/s8_candidate/bor.msu").read_bytes(), b"candidate msu")
        self.assertEqual(Path("build/s8_candidate/bor-1.pcm").read_bytes(), b"fixture music")
        self.assertEqual(Path("distribution/bor-1.pcm").read_bytes(), b"fixture music")

    def test_candidate_directory_is_selectable_and_pcm_remains_hardlinked(self):
        target = Path("build/custom-normal")
        with contextlib.redirect_stdout(io.StringIO()):
            build.write_build_outputs(b"candidate rom", b"candidate msu",
                                      normal_candidate=True, candidate_dir=target)
        self.assertEqual((target / "bor.sfc").read_bytes(), b"candidate rom")
        self.assertEqual((target / "bor.msu").read_bytes(), b"candidate msu")
        self.assertTrue(os.path.samefile("distribution/bor-1.pcm", target / "bor-1.pcm"))
        self.assertFalse(Path("build/s8_candidate").exists())
        self.assert_protected()

    def test_bad_music_hash_prevents_candidate_publication(self):
        Path("distribution/bor-1.pcm").write_bytes(b"corrupt")
        with self.assertRaisesRegex(SystemExit, "candidate PCM hash mismatch"):
            build.write_build_outputs(b"rom", b"msu", normal_candidate=True)
        self.assertFalse(Path("build/s8_candidate").exists())
        self.assert_protected()

    def test_default_output_targets_unchanged(self):
        with contextlib.redirect_stdout(io.StringIO()):
            build.write_build_outputs(b"production rom", b"production msu")
        self.assertEqual(Path("build/bor.sfc").read_bytes(), b"production rom")
        self.assertEqual(Path("distribution/bor.sfc").read_bytes(), b"production rom")
        self.assertEqual(Path("distribution/bor.msu").read_bytes(), b"production msu")
        self.assertFalse(Path("build/s8_candidate").exists())

    def test_link_rom_matches_pre_extraction_algorithm_without_publishing(self):
        def original_bytes(blob):
            # Independent compact expression of the previous main() block.
            rom = bytearray(build.ROM_SIZE)
            rom[:len(blob)] = blob
            rom[0x7FC0:0x7FC0 + 21] = b"BEATS OF RAGE SNES   "
            rom[0x7FD5:0x7FDC] = bytes((0x23, 0x35, 0x0C, 0x08, 0x01, 0x33, 0))
            for offset, value in ((0x7FE4, 0xFFB0), (0x7FE6, 0xFFB0),
                                  (0x7FE8, 0xFFB0), (0x7FEA, 0xFFA0),
                                  (0x7FEC, 0xFFB0), (0x7FF4, 0xFFB0),
                                  (0x7FF8, 0xFFB0), (0x7FFA, 0xFFA0),
                                  (0x7FFC, 0xFC03), (0x7FFE, 0xFFB0)):
                rom[offset:offset + 2] = value.to_bytes(2, "little")
            checksum = sum(rom) & 0xFFFF
            rom[0x7FDC:0x7FE0] = ((~checksum) & 0xFFFF).to_bytes(2, "little") + checksum.to_bytes(2, "little")
            return bytes(rom)

        for size in (0, 0x10000, build.ROM_SIZE):
            with self.subTest(size=size), contextlib.ExitStack() as stack:
                blob = (bytes(range(256)) * ((size + 255) // 256))[:size]
                Path("src/main.bin").write_bytes(blob)
                assemble = stack.enter_context(patch.object(build, "assemble"))
                bank = stack.enter_context(patch.object(build, "validate_bank0_layout"))
                text = stack.enter_context(patch.object(build, "validate_text_bank_layout"))
                score = stack.enter_context(patch.object(build, "validate_score_layout"))
                publish = stack.enter_context(patch.object(build, "write_build_outputs"))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                result = build.link_rom()
                self.assertIsInstance(result, bytes)
                self.assertEqual(result, original_bytes(blob))
                assemble.assert_called_once_with()
                bank.assert_called_once_with(bytearray(blob), "src/main.sym")
                text.assert_called_once_with("src/main.sym")
                score.assert_called_once_with("src/main.sym")
                publish.assert_not_called()
                self.assert_protected()

    def test_link_rom_rejects_validation_failure_and_overflow(self):
        Path("src/main.bin").write_bytes(bytes(build.ROM_SIZE + 1))
        with patch.object(build, "assemble"), patch.object(build, "validate_bank0_layout"), \
             patch.object(build, "validate_text_bank_layout"), patch.object(build, "validate_score_layout"), \
             contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(SystemExit, "ROM resource overflow"):
            build.link_rom()
        Path("src/main.bin").write_bytes(b"fixture")
        with patch.object(build, "assemble"), patch.object(build, "validate_bank0_layout", side_effect=ValueError("layout failure")), \
             contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "layout failure"):
            build.link_rom()
        self.assert_protected()

    def test_main_candidate_suppresses_shared_msu_and_assembly_failure_publishes_nothing(self):
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(production_campaign, "materialize_actor_bindings"))
            stack.enter_context(patch.object(production_campaign, "materialize_stage_bindings"))
            stack.enter_context(patch("source_noncombat.write_tables"))
            for name in ("prepare_campaign_queues", "bank0_layout_guard_self_test",
                         "write_stage_scroll_include", "write_bor_player_select_include",
                         "write_source_visual_layout_include"):
                stack.enter_context(patch.object(build, name))
            gate = stack.enter_context(patch.object(build, "write_campaign_include"))
            stack.enter_context(patch.object(build.build_audio, "main"))
            pack = stack.enter_context(patch.object(build, "build_msu_assets", return_value=(b"msu", {})))
            stack.enter_context(patch.object(build, "assemble", side_effect=RuntimeError("assembly failed")))
            publish = stack.enter_context(patch.object(build, "write_build_outputs"))
            with self.assertRaisesRegex(RuntimeError, "assembly failed"):
                build.main(normal_candidate=True)
            gate.assert_called_once_with(normal_candidate=True, hard_candidate=False, bonus_candidate=False)
            pack.assert_called_once_with(write_output=False, source_sized_visual=False)
            publish.assert_not_called()
        self.assert_protected()

    def test_rom_override_default_relative_absolute_and_invalid(self):
        with patch.object(harness, "repo_root_from", return_value=str(self.root)):
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(Path(harness.rom_path(__file__)), self.root / "distribution/bor.sfc")
            relative = "build/bor.sfc"
            with patch.dict(os.environ, BOR_TEST_ROM=relative):
                self.assertEqual(Path(harness.rom_path(__file__)), (self.root / relative).resolve())
            with tempfile.TemporaryDirectory() as external:
                fixture = Path(external) / "named.sfc"
                fixture.write_bytes(b"explicit external fixture")
                with patch.dict(os.environ, BOR_TEST_ROM=str(fixture)):
                    self.assertEqual(Path(harness.rom_path(__file__)), fixture.resolve())
            with patch.dict(os.environ, BOR_TEST_ROM="missing.sfc"), self.assertRaises(FileNotFoundError):
                harness.rom_path(__file__)
            with patch.dict(os.environ, BOR_TEST_ROM=""), self.assertRaises(ValueError):
                harness.rom_path(__file__)
            with patch.dict(os.environ, BOR_TEST_ROM="build"), self.assertRaises(ValueError):
                harness.rom_path(__file__)


if __name__ == "__main__":
    unittest.main()
