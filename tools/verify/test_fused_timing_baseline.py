"""Tests for digest-first loading of the retained fused timing receipt."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fused_timing_baseline as baseline
from fused_timing_baseline import (
    BASE_ROM_SHA256, DEFAULT_RECEIPT, RECEIPT_SHA256,
    TimingBaselineContractError, load_timing_baseline,
)


class FusedTimingBaselineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.receipt = json.loads(DEFAULT_RECEIPT.read_bytes())

    def write_receipt(self, value, name='receipt.json'):
        path = self.directory / name
        path.write_text(json.dumps(value, sort_keys=True), encoding='utf-8')
        return path

    def test_loads_retained_digest_pinned_receipt_and_rom(self):
        result = load_timing_baseline()
        raw = DEFAULT_RECEIPT.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), RECEIPT_SHA256)
        self.assertEqual(result['candidate_rom_sha256'], BASE_ROM_SHA256)
        self.assertEqual(result['baseline_epoch2']['master_clocks'], 8416382)
        self.assertEqual(result['candidate_epoch3']['master_clocks'], 12034092)

    def test_same_rom_epoch2_and_epoch3_timing_tampering_fails_digest(self):
        mutations = (
            ('candidate_epoch2', 'fields'),
            ('candidate_epoch2', 'master_clocks'),
            ('candidate_epoch3', 'fields'),
            ('candidate_epoch3', 'master_clocks'),
        )
        for epoch, field in mutations:
            with self.subTest(epoch=epoch):
                changed = json.loads(json.dumps(self.receipt))
                changed[epoch][field] += 1
                self.assertEqual(changed['candidate_rom_sha256'], BASE_ROM_SHA256)
                path = self.write_receipt(changed, epoch + '.json')
                with self.assertRaisesRegex(TimingBaselineContractError,
                                            'FTB_RECEIPT_SHA256'):
                    load_timing_baseline(path)

    def test_rom_marker_change_rejected_even_with_fixture_digest(self):
        changed = json.loads(json.dumps(self.receipt))
        changed['candidate_rom_sha256'] = 'f' * 64
        path = self.write_receipt(changed, 'wrong-rom.json')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        with patch.object(baseline, 'RECEIPT_SHA256', digest):
            with self.assertRaisesRegex(TimingBaselineContractError,
                                        'FTB_BASE_ROM_IDENTITY'):
                load_timing_baseline(path)

    def test_missing_and_non_file_paths_are_rejected(self):
        with self.assertRaisesRegex(TimingBaselineContractError,
                                    'FTB_RECEIPT_UNREADABLE'):
            load_timing_baseline(self.directory / 'missing.json')
        with self.assertRaisesRegex(TimingBaselineContractError,
                                    'FTB_RECEIPT_UNREADABLE'):
            load_timing_baseline(self.directory)

    def test_malformed_wrong_digest_fails_before_json_parse(self):
        path = self.directory / 'malformed.json'
        path.write_bytes(b'{ malformed json')
        with self.assertRaisesRegex(TimingBaselineContractError,
                                    'FTB_RECEIPT_SHA256'):
            load_timing_baseline(path)

    def test_malformed_content_with_fixture_digest_is_rejected_as_json(self):
        path = self.directory / 'malformed-matching-digest.json'
        path.write_bytes(b'{ malformed json')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        with patch.object(baseline, 'RECEIPT_SHA256', digest):
            with self.assertRaisesRegex(TimingBaselineContractError,
                                        'FTB_RECEIPT_JSON'):
                load_timing_baseline(path)


if __name__ == '__main__':
    unittest.main()
