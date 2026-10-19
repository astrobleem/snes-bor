"""Independent byte, native evidence, timing and fail-closed collection tests."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import m4_ready_validate_native as native
import ready_validate_evidence as evidence

FIXTURE = Path('out/byor-motu-ready-validate-build-v2/success/native')


def log_record(kind, clock, *data):
    return 'NB_' + kind + '|' + str(clock) + '|10|40|' + '|'.join(map(str, data))


def map_hex(words):
    return b''.join(word.to_bytes(2, 'little') for word in words).hex()


def scan_records(before=None, after=None, words=None, result=None):
    entry = dict(a=17, x=99, y=123, d=0x3400, dbr=0, sp=0x1fff, ps=0x44, counter=0)
    exit_state = dict(entry, a=2048, x=2046, ps=0x47, counter=2048)
    entry.update(before or {}); exit_state.update(after or {})
    words = words or [(i % 768) | 0x4000 for i in range(1024)]
    result = result or [word & 0x3fff for word in words]
    return '\n'.join((log_record('BH_COST', 90, 'BhReadyOK', 3),
                      log_record('RV_ENTRY', 100, 3, *[entry[k] for k in evidence.REGISTERS], map_hex(words)),
                      log_record('RV_SCAN', 200, 3, 100, *[exit_state[k] for k in evidence.REGISTERS], map_hex(result))))


class ReadyValidateAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.log = self.directory / 'mesen.log'

    def test_independent_machine_bytes_and_original_fused_scanner(self):
        from m4_input_controller_native import offset
        rom = (FIXTURE / 'bor.sfc').read_bytes()
        result = native.audit_rom(rom, FIXTURE)['ready_validate']
        self.assertEqual(result['code_bytes'], 55)
        self.assertEqual(result['branch_sites'], 312)
        self.assertEqual(rom[offset(0x39A740):offset(0x39A79B)],
                         (native.BASE / 'bor.sfc').read_bytes()[offset(0x39A740):offset(0x39A79B)])

    def test_rom_dispatch_helper_and_unrelated_mutations_reject(self):
        from m4_input_controller_native import offset
        original = (FIXTURE / 'bor.sfc').read_bytes()
        for pc in (native.PATCH_PC, native.PATCH_PC + 1, 0x39A800, 0x398000):
            with self.subTest(pc=hex(pc)):
                changed = bytearray(original); changed[offset(pc)] ^= 1
                with self.assertRaisesRegex(ValueError, 'UNAUTHORIZED_ROM_BYTE'):
                    native.audit_rom(changed, FIXTURE)

    def test_timing_receipt_pins_consumed_keys_before_json_parse(self):
        original = evidence.load_baseline()
        for epoch in ('candidate_epoch2', 'candidate_epoch3'):
            for key in ('fields', 'master_clocks'):
                with self.subTest(epoch=epoch, key=key):
                    changed = copy.deepcopy(original); changed[epoch][key] += 1
                    path = self.directory / 'receipt.json'; path.write_text(json.dumps(changed))
                    with patch.object(evidence.json, 'loads') as parse:
                        with self.assertRaisesRegex(ValueError, 'BASE_RECEIPT_DIGEST'):
                            evidence.load_baseline(path)
                        parse.assert_not_called()

    def test_retained_ready_interval_has_existing_native_boundary(self):
        result = evidence.ready_intervals(native.BASELINE / 'success/native/mesen.log')
        self.assertEqual(result['3']['master_clocks'], 490896)
        self.assertEqual(evidence.load_baseline()['function_attribution']['residual'][0]['clocks'], 479820)

    def seed_manifest(self):
        path = Path('out/byor-motu-ready-validate-v1/capture-runtime/capture-runtime.json')
        return json.loads(path.read_bytes())

    def test_initial_sram_is_bound_to_digest_pinned_baseline(self):
        manifest = self.seed_manifest()
        result = evidence.verify_initial_sram(manifest)
        self.assertEqual(result['sha256'], 'a7574d35205ca9a5b724f78a6cc5d1a7f499b894892aae31dbfaa69902fa8fa1')
        self.assertEqual(result['bytes'], 262144)
        self.assertEqual(result['authority_receipt_sha256'], evidence.BASE_RECEIPT_SHA256)
        self.assertEqual(Path(result['source']).resolve(), Path(manifest['initial_sram']['source']).resolve())

    def test_changed_seed_path_with_matching_manifest_digest_rejects_before_read(self):
        manifest = self.seed_manifest(); other = self.directory / 'other.srm'
        data = b'another existing seed'; other.write_bytes(data)
        manifest['initial_sram'] = dict(source=str(other), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        baseline = evidence.load_baseline()
        with patch.object(evidence, 'load_baseline', return_value=baseline), patch.object(Path, 'read_bytes') as read:
            with self.assertRaisesRegex(ValueError, 'INITIAL_SRAM_SOURCE_PATH'):
                evidence.verify_initial_sram(manifest)
            read.assert_not_called()

    def test_changed_declared_seed_hash_rejects_before_seed_read(self):
        manifest = self.seed_manifest(); manifest['initial_sram']['sha256'] = '0' * 64
        baseline = evidence.load_baseline()
        with patch.object(evidence, 'load_baseline', return_value=baseline), patch.object(Path, 'read_bytes') as read:
            with self.assertRaisesRegex(ValueError, 'INITIAL_SRAM_DECLARED_DIGEST'):
                evidence.verify_initial_sram(manifest)
            read.assert_not_called()

    def test_changed_actual_seed_bytes_reject_despite_original_manifest(self):
        manifest = self.seed_manifest(); baseline = evidence.load_baseline()
        with patch.object(evidence, 'load_baseline', return_value=baseline), \
             patch.object(Path, 'read_bytes', return_value=b'changed actual seed'):
            with self.assertRaisesRegex(ValueError, 'INITIAL_SRAM_INPUT_DIGEST'):
                evidence.verify_initial_sram(manifest)

    def test_missing_seed_and_changed_size_reject(self):
        original = self.seed_manifest()
        for seed in (None, {}, dict(original['initial_sram'], bytes=True),
                     dict(original['initial_sram'], bytes=262143)):
            with self.subTest(seed=seed):
                manifest = copy.deepcopy(original); manifest['initial_sram'] = seed
                with self.assertRaisesRegex(ValueError, 'INITIAL_SRAM_MANIFEST|INITIAL_SRAM_SIZE'):
                    evidence.verify_initial_sram(manifest)

    def test_seed_manifest_tampering_precedes_original_native_certifier(self):
        manifest = self.seed_manifest(); manifest['initial_sram']['sha256'] = '0' * 64
        runtime = self.directory / 'capture-runtime'; runtime.mkdir()
        (runtime / 'capture-runtime.json').write_text(json.dumps(manifest))
        with patch.object(native.capture, 'verify_capture', return_value={}), \
             patch.object(native.accepted, 'collect_suite') as certify:
            with self.assertRaisesRegex(ValueError, 'INITIAL_SRAM_DECLARED_DIGEST'):
                native.collect_suite(self.directory, native.capture.RETAINED_SEAL)
            certify.assert_not_called()
        self.assertFalse((self.directory / 'ready-validate-receipt.json').exists())

    def test_ready_interval_requires_unique_marker_and_preceding_drain(self):
        ready = log_record('PHASE', 200, 'NbReady', 3)
        drain = log_record('BATCH', 100, 'NbQueueDrainDone', 3)
        for value in (ready, '\n'.join((drain, ready, ready)),
                      '\n'.join((log_record('BATCH', 300, 'NbQueueDrainDone', 3), ready))):
            with self.subTest(value=value):
                self.log.write_text(value)
                with self.assertRaisesRegex(ValueError, 'READY_'):
                    evidence.ready_intervals(self.log)

    def test_native_scan_reconstructs_map_and_full_exit_context(self):
        self.log.write_text(scan_records())
        result = evidence.native_scans(self.log)
        self.assertEqual(result['3'], dict(master_clocks=100, words=1024,
            context_preserved=True, exact_map_transform=True))

    def test_native_scan_rejects_changed_registers_and_partial_map(self):
        for key, value in (('a', 2047), ('x', 2048), ('y', 122), ('d', 0),
                           ('dbr', 1), ('sp', 0x1ffe), ('ps', 0x46), ('counter', 2047)):
            with self.subTest(key=key):
                self.log.write_text(scan_records(after={key: value}))
                with self.assertRaisesRegex(ValueError, 'SCAN_'):
                    evidence.native_scans(self.log)
        result = [i % 768 for i in range(1024)]; result[10] ^= 1
        self.log.write_text(scan_records(result=result))
        with self.assertRaisesRegex(ValueError, 'SCAN_MAP_SEMANTICS'):
            evidence.native_scans(self.log)

    def test_native_scan_rejects_missing_duplicate_or_rejectable_records(self):
        valid = scan_records()
        for text in (valid.splitlines()[0], '\n'.join(valid.splitlines()[:2]),
                     '\n'.join(valid.splitlines()[1:]),
                     valid + '\n' + valid, log_record('FAULT', 200, 'RV_CONTEXT')):
            with self.subTest(text=text[:80]):
                self.log.write_text(text)
                with self.assertRaisesRegex(ValueError, 'SCAN_|NATIVE_FAULT'):
                    evidence.native_scans(self.log)
        words = [i % 768 for i in range(1024)]
        for invalid in (0x8000, 768):
            words[10] = invalid; self.log.write_text(scan_records(words=words))
            with self.assertRaisesRegex(ValueError, 'SCAN_INPUT_REJECTABLE'):
                evidence.native_scans(self.log)

    def test_interval_comparison_and_epoch_timing_fail_closed(self):
        evidence.compare_intervals({'3': dict(master_clocks=50)}, {'3': dict(master_clocks=100)})
        for current in ({}, {'3': dict(master_clocks=100)}):
            with self.assertRaisesRegex(ValueError, 'READY_'):
                evidence.compare_intervals(current, {'3': dict(master_clocks=100)})
        baseline = evidence.load_baseline()
        good = dict(epoch2=dict(fields=22, master_clocks=8000000),
                    epoch3=dict(fields=31, master_clocks=11000000))
        evidence.verify_timing(good, baseline)
        for epoch, key in (('epoch2', 'fields'), ('epoch2', 'master_clocks'),
                           ('epoch3', 'fields'), ('epoch3', 'master_clocks')):
            bad = copy.deepcopy(good)
            bad[epoch][key] = baseline['candidate_' + epoch][key] + (1 if epoch == 'epoch2' else 0)
            with self.assertRaisesRegex(ValueError, 'EPOCH'):
                evidence.verify_timing(bad, baseline)

    def test_capture_rejection_precedes_original_native_certifier(self):
        with patch.object(native.capture, 'verify_capture', side_effect=[{}, ValueError('incomplete capture')]), \
             patch.object(native.accepted, 'collect_suite') as certify:
            with self.assertRaisesRegex(ValueError, 'incomplete capture'):
                native.collect_suite(self.directory, native.capture.RETAINED_SEAL)
            certify.assert_not_called()

    def test_deleted_field_ten_is_rejected_by_real_capture_guard_before_certification(self):
        from test_fused_capture_evidence import make_capture, write_json
        base = self.directory; root, seal = make_capture(base, count=12)
        path = root / 'success/fields.json'
        fields = json.loads(path.read_bytes()); del fields[10]; write_json(path, fields)
        real_verify = native.capture.verify_capture
        def verify(folder, chosen=native.capture.RETAINED_SEAL):
            if Path(folder).resolve() == native.BASELINE.resolve():
                return {}
            return real_verify(folder, chosen, base=base)
        with patch.object(native.capture, 'verify_capture', side_effect=verify), \
             patch.object(native.accepted, 'collect_suite') as certify:
            with self.assertRaisesRegex(ValueError, 'COPY_SOURCE_HASH|RAW_INPUT_HASH'):
                native.collect_suite(root, seal)
            certify.assert_not_called()

    def test_timing_tampering_rejects_before_capture_reads_or_certification(self):
        baseline = evidence.load_baseline(); baseline['candidate_epoch3']['fields'] += 1
        path = self.directory / 'tampered.json'; path.write_text(json.dumps(baseline))
        real_load = evidence.load_baseline
        with patch.object(evidence, 'load_baseline', side_effect=lambda: real_load(path)), \
             patch.object(native.capture, 'verify_capture') as captures, \
             patch.object(native.accepted, 'collect_suite') as certify:
            with self.assertRaisesRegex(ValueError, 'BASE_RECEIPT_DIGEST'):
                native.collect_suite(self.directory, native.capture.RETAINED_SEAL)
            captures.assert_not_called(); certify.assert_not_called()

    def test_post_certification_raw_change_cannot_write_pass_receipt(self):
        report = dict(epoch2=dict(fields=22, master_clocks=8000000),
                      epoch3=dict(fields=31, master_clocks=11000000))
        with patch.object(native.capture, 'verify_capture', side_effect=[{}, {'before': 1}, {'after': 1}]), \
             patch.object(native.evidence, 'runtime_initial_sram', return_value={}), \
             patch.object(native.accepted, 'collect_suite', return_value=report), \
             patch.object(native.evidence, 'ready_intervals', return_value={'3': dict(master_clocks=100)}), \
             patch.object(native.evidence, 'ready_successes', return_value={'3': 90}), \
             patch.object(native, 'profile', return_value=dict(scans={'3': {}}, ready_intervals={'3': dict(master_clocks=50)})), \
             patch.object(native.accepted.accepted, 'expected_checkpoints', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'RAW_CAPTURE_CHANGED'):
                native.collect_suite(self.directory, native.capture.RETAINED_SEAL)
        self.assertFalse((self.directory / 'ready-validate-receipt.json').exists())

    def test_cli_collection_requires_explicit_paired_trusted_pins(self):
        for extra in ([], ['--provenance-sha256', 'a' * 64], ['--raw-manifest-sha256', 'b' * 64]):
            with self.subTest(extra=extra), \
                 patch.object(sys, 'argv', ['ready', '--output', 'unused', '--collect-suite', *extra]), \
                 patch.object(native, 'collect_suite') as collect, \
                 patch.object(native.capture, 'seal_native_capture') as seal:
                with self.assertRaisesRegex(ValueError, 'TRUSTED_CAPTURE_PINS_REQUIRED|BOTH_CAPTURE_PINS_REQUIRED'):
                    native.main()
                collect.assert_not_called(); seal.assert_not_called()

    def test_cli_explicit_collection_passes_pins_without_resealing(self):
        report = dict(classification='PASS', observed_fields=1, verified_rgb555_pixels=1)
        with patch.object(sys, 'argv', ['ready', '--output', 'unused', '--collect-suite',
                          '--provenance-sha256', 'a' * 64, '--raw-manifest-sha256', 'b' * 64]), \
             patch.object(native, 'collect_suite', return_value=report) as collect, \
             patch.object(native.capture, 'seal_native_capture') as seal, patch('builtins.print'):
            native.main()
            collect.assert_called_once_with(Path('unused').resolve(), native.capture.CaptureSeal('a' * 64, 'b' * 64))
            seal.assert_not_called()


if __name__ == '__main__':
    unittest.main()
