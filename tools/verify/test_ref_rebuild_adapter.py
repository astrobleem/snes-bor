"""Independent bytes and fail-closed native evidence/collection tests."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import m4_ref_rebuild_native as native
import ref_rebuild_evidence as evidence

FIXTURE = Path('out/byor-motu-ref-rebuild-build-v2/success/native')


def record(kind, clock, *data):
    return 'NB_' + kind + '|' + str(clock) + '|10|40|' + '|'.join(map(str, data))


def words_hex(words):
    return b''.join(x.to_bytes(2, 'little') for x in words).hex()


def scan_records(before=None, after=None, refs=None, maps=None, output=None, trace=None):
    refs = refs or [(i & 0x3fff) | (0x8000 if i % 2 else 0) for i in range(768)]
    maps = maps or [i % 768 for i in range(1024)]
    expected = [word & 0x8000 for word in refs]; writes = []
    for i, value in enumerate(expected):
        writes.extend(((0xd000 + 2 * i, value & 255), (0xd001 + 2 * i, value >> 8)))
    for slot in maps:
        expected[slot] += 1; value = expected[slot]
        writes.extend(((0xd000 + 2 * slot, value & 255), (0xd001 + 2 * slot, value >> 8)))
    entry = dict(a=65535, x=51200, y=53248, d=0x3400, dbr=0x7e, sp=0x1fff, ps=0x44, counter=2048)
    final = dict(entry, a=expected[maps[-1]], x=2 * maps[-1], y=2048, ps=0x47)
    entry.update(before or {}); final.update(after or {})
    trace = ''.join(f'{a:04x}{v:02x}' for a, v in writes) if trace is None else trace
    return '\n'.join((record('PHASE', 100, 'NbMapsComplete', 3),
        record('RF_ENTRY', 110, 3, *[entry[k] for k in evidence.REGISTERS], words_hex(refs), words_hex(maps)),
        record('RF_SCAN', 510, 3, 400, *[final[k] for k in evidence.REGISTERS],
               words_hex(expected if output is None else output), words_hex(maps), trace),
        record('PHASE', 600, 'NbVisible', 3)))


class RefRebuildAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name); self.log = self.directory / 'mesen.log'

    def test_independent_machine_bytes_and_existing_helpers(self):
        from m4_input_controller_native import offset
        rom = (FIXTURE / 'bor.sfc').read_bytes()
        result = native.audit_rom(rom, FIXTURE)['ref_rebuild']
        self.assertEqual(result['code_bytes'], 435); self.assertEqual(result['branch_sites'], 316)
        original = (native.BASE / 'bor.sfc').read_bytes()
        self.assertEqual(rom[offset(0x39A700):offset(0x39A837)], original[offset(0x39A700):offset(0x39A837)])

    def test_dispatch_operand_helper_and_unrelated_mutations_reject(self):
        from m4_input_controller_native import offset
        original = (FIXTURE / 'bor.sfc').read_bytes()
        for pc in (native.PATCH_PC, native.PATCH_PC + 2, 0x39A900, 0x398000):
            with self.subTest(pc=hex(pc)):
                changed = bytearray(original); changed[offset(pc)] ^= 1
                with self.assertRaisesRegex(ValueError, 'UNAUTHORIZED_ROM_BYTE'):
                    native.audit_rom(changed, FIXTURE)

    def test_disabled_control_is_accepted_ready_rom(self):
        path = Path('out/byor-motu-ref-rebuild-disabled-v1/success/native/bor.sfc')
        self.assertEqual(native.capture.sha(path), evidence.BASE_ROM_SHA256)

    def test_timing_receipt_is_pinned_before_parse(self):
        original = evidence.load_baseline()
        for epoch in ('candidate_epoch2', 'candidate_epoch3'):
            for key in ('fields', 'master_clocks'):
                changed = copy.deepcopy(original); changed[epoch][key] += 1
                path = self.directory / 'receipt.json'; path.write_text(json.dumps(changed))
                with self.subTest(epoch=epoch, key=key), patch.object(evidence.json, 'loads') as parse:
                    with self.assertRaisesRegex(ValueError, 'BASE_RECEIPT_DIGEST'):
                        evidence.load_baseline(path)
                    parse.assert_not_called()

    def test_postmap_interval_reuses_original_native_markers(self):
        rows = evidence.postmap_intervals(native.BASELINE / 'success/native/mesen.log')
        self.assertEqual(set(rows), {'2', '3'})
        self.assertEqual(rows['3']['master_clocks'], 569326)

    def test_postmap_interval_missing_duplicate_and_clock_order_reject(self):
        start = record('PHASE', 100, 'NbMapsComplete', 3)
        end = record('PHASE', 200, 'NbVisible', 3)
        for value in (start, end, start + '\n' + start + '\n' + end,
                      start + '\n' + end + '\n' + end,
                      start + '\n' + record('PHASE', 99, 'NbVisible', 3)):
            self.log.write_text(value)
            with self.assertRaisesRegex(ValueError, 'POSTMAP_'):
                evidence.postmap_intervals(self.log)

    def test_rebuild_checks_all_reference_words_byte_writes_and_context(self):
        self.log.write_text(scan_records())
        self.assertEqual(evidence.native_rebuilds(self.log)['3'], dict(master_clocks=400,
            cleared_words=768, map_words=1024, byte_writes=3584, exact_reference_transform=True,
            ordered_write_trace=True, context_preserved=True))

    def test_changed_reference_table_or_write_trace_rejects(self):
        good = scan_records(); rows = good.splitlines()
        for index, label in ((10, 'REFERENCE_TRANSFORM'), (12, 'ORDERED_BYTE_WRITE_TRACE')):
            parts = rows[2].split('|'); at = 4 + index
            parts[at] = ('f' if parts[at][0] != 'f' else '0') + parts[at][1:]
            changed = rows.copy(); changed[2] = '|'.join(parts); self.log.write_text('\n'.join(changed))
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, label):
                evidence.native_rebuilds(self.log)
        parts = rows[2].split('|'); parts[-1] = parts[-1][6:] + parts[-1][:6]
        changed = rows.copy(); changed[2] = '|'.join(parts); self.log.write_text('\n'.join(changed))
        with self.assertRaisesRegex(ValueError, 'ORDERED_BYTE_WRITE_TRACE'):
            evidence.native_rebuilds(self.log)

    def test_changed_registers_reject(self):
        for key, value in (('a', 999), ('x', 0), ('y', 2046), ('d', 0), ('dbr', 1),
                           ('sp', 0x1ffe), ('ps', 0x46), ('counter', 2047)):
            with self.subTest(key=key):
                self.log.write_text(scan_records(after={key: value}))
                with self.assertRaisesRegex(ValueError, 'ENTRY_ABI|EXIT_REGISTERS|EXIT_CONTEXT'):
                    evidence.native_rebuilds(self.log)

    def test_invalid_slot_or_changed_pending_map_rejects(self):
        rows = scan_records().splitlines()
        changed = rows.copy(); entry = changed[1].split('|')
        entry[-1] = '0003' + entry[-1][4:]
        changed[1] = '|'.join(entry); self.log.write_text('\n'.join(changed))
        with self.assertRaisesRegex(ValueError, 'INPUT_WORDS_OR_SLOTS'):
            evidence.native_rebuilds(self.log)
        changed = rows.copy(); exit_parts = changed[2].split('|')
        exit_parts[-2] = '0100' + exit_parts[-2][4:]
        changed[2] = '|'.join(exit_parts); self.log.write_text('\n'.join(changed))
        with self.assertRaisesRegex(ValueError, 'REFERENCE_TRANSFORM'):
            evidence.native_rebuilds(self.log)

    def test_wrong_cpu_width_or_elapsed_metadata_rejects(self):
        self.log.write_text(scan_records(before={'ps': 0x64}))
        with self.assertRaisesRegex(ValueError, 'ENTRY_ABI'):
            evidence.native_rebuilds(self.log)
        self.log.write_text(scan_records().replace('RF_SCAN|510|10|40|3|400|', 'RF_SCAN|510|10|40|3|401|'))
        with self.assertRaisesRegex(ValueError, 'SCAN_CLOCKS'):
            evidence.native_rebuilds(self.log)

    def test_missing_duplicate_or_wrong_phase_scan_rejects(self):
        rows = scan_records().splitlines()
        for value in ('\n'.join((rows[0], rows[3])), '\n'.join(rows[:2] + rows[3:]),
                      '\n'.join(rows[:2] + [rows[1]] + rows[2:]),
                      '\n'.join(rows[:3] + [rows[2]] + rows[3:]),
                      '\n'.join(rows).replace('RF_ENTRY|110|', 'RF_ENTRY|99|')):
            self.log.write_text(value)
            with self.assertRaisesRegex(ValueError, 'ENTRY_RECORD|EXIT_RECORD|SCAN_'):
                evidence.native_rebuilds(self.log)

    def test_interval_comparison_and_epoch_timing_require_actual_gain(self):
        evidence.compare_intervals({'3': dict(master_clocks=50)}, {'3': dict(master_clocks=100)})
        for current in ({}, {'3': dict(master_clocks=100)}):
            with self.assertRaisesRegex(ValueError, 'POSTMAP_'):
                evidence.compare_intervals(current, {'3': dict(master_clocks=100)})
        baseline = evidence.load_baseline()
        good = dict(epoch2=dict(fields=22, master_clocks=7900000), epoch3=dict(fields=31, master_clocks=11000000))
        evidence.verify_timing(good, baseline)
        for epoch, key in (('epoch2', 'fields'), ('epoch2', 'master_clocks'),
                           ('epoch3', 'fields'), ('epoch3', 'master_clocks')):
            bad = copy.deepcopy(good)
            bad[epoch][key] = baseline['candidate_' + epoch][key] + (1 if key == 'fields' else 0)
            with self.assertRaisesRegex(ValueError, 'REGRESSION_OR_NO_GAIN'):
                evidence.verify_timing(bad, baseline)

    def test_deleted_interior_field_rejects_before_original_certifier(self):
        from test_fused_capture_evidence import make_capture, write_json
        base = self.directory; root, seal = make_capture(base, count=12)
        fields = json.loads((root / 'success/fields.json').read_bytes()); del fields[10]
        write_json(root / 'success/fields.json', fields)
        real = native.capture.verify_capture
        def verify(folder, chosen=native.capture.RETAINED_SEAL):
            return {} if Path(folder).resolve() == native.BASELINE.resolve() else real(folder, chosen, base=base)
        with patch.object(native.capture, 'verify_capture', side_effect=verify), \
             patch.object(native.accepted, 'collect_suite') as certify:
            with self.assertRaisesRegex(ValueError, 'COPY_SOURCE_HASH|RAW_INPUT_HASH'):
                native.collect_suite(root, seal)
            certify.assert_not_called()

    def test_timing_tamper_precedes_capture_and_certification(self):
        baseline = evidence.load_baseline(); baseline['candidate_epoch3']['master_clocks'] += 1
        path = self.directory / 'tampered.json'; path.write_text(json.dumps(baseline))
        real = evidence.load_baseline
        with patch.object(evidence, 'load_baseline', side_effect=lambda: real(path)), \
             patch.object(native.capture, 'verify_capture') as captures, \
             patch.object(native.accepted, 'collect_suite') as certify:
            with self.assertRaisesRegex(ValueError, 'BASE_RECEIPT_DIGEST'):
                native.collect_suite(self.directory, evidence.BASE_SEAL)
            captures.assert_not_called(); certify.assert_not_called()

    def collection_context(self, captures, scans=None):
        from contextlib import ExitStack
        stack = ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(patch.object(native.capture, 'verify_capture', side_effect=captures))
        stack.enter_context(patch.object(native.accepted, 'collect_suite', return_value=dict(
            epoch2=dict(fields=22, master_clocks=7900000), epoch3=dict(fields=31, master_clocks=11000000))))
        stack.enter_context(patch.object(native.evidence, 'postmap_intervals', return_value={'3': dict(master_clocks=100)}))
        stack.enter_context(patch.object(native, 'profile', return_value=dict(
            scans={'3': {}} if scans is None else scans, postmap_intervals={'3': dict(master_clocks=50)})))
        stack.enter_context(patch.object(native.accepted.accepted.accepted, 'expected_checkpoints', return_value=[]))

    def test_post_certification_raw_mutation_cannot_write_pass(self):
        self.collection_context([{}, {'raw': 1}, {'raw': 2}])
        with self.assertRaisesRegex(ValueError, 'RAW_CAPTURE_CHANGED'):
            native.collect_suite(self.directory, evidence.BASE_SEAL)
        self.assertFalse((self.directory / 'ref-rebuild-receipt.json').exists())

    def test_baseline_mutation_cannot_write_pass(self):
        self.collection_context([{'base': 1}, {}, {}, {'base': 2}])
        with self.assertRaisesRegex(ValueError, 'BASELINE_CAPTURE_CHANGED'):
            native.collect_suite(self.directory, evidence.BASE_SEAL)
        self.assertFalse((self.directory / 'ref-rebuild-receipt.json').exists())

    def test_whole_scan_pair_deletion_cannot_write_pass(self):
        self.collection_context([{}, {}], scans={})
        with self.assertRaisesRegex(ValueError, 'BASELINE_SCAN_TRANSACTION_DRIFT'):
            native.collect_suite(self.directory, evidence.BASE_SEAL)
        self.assertFalse((self.directory / 'ref-rebuild-receipt.json').exists())

    def test_twenty_percent_gain_gate_cannot_write_pass_on_small_gain(self):
        self.collection_context([{}, {}])
        with patch.object(native, 'profile', return_value=dict(scans={'3': {}},
                          postmap_intervals={'3': dict(master_clocks=85)})):
            with self.assertRaisesRegex(ValueError, 'POSTMAP_GAIN_BELOW_20_PERCENT'):
                native.collect_suite(self.directory, evidence.BASE_SEAL)
        self.assertFalse((self.directory / 'ref-rebuild-receipt.json').exists())

    def test_cli_requires_explicit_paired_trusted_pins(self):
        for extra in ([], ['--provenance-sha256', 'a' * 64], ['--raw-manifest-sha256', 'b' * 64]):
            with patch.object(sys, 'argv', ['refs', '--output', 'unused', '--collect-suite', *extra]), \
                 patch.object(native, 'collect_suite') as collect, \
                 patch.object(native.capture, 'seal_native_capture') as seal:
                with self.assertRaisesRegex(ValueError, 'TRUSTED_CAPTURE_PINS_REQUIRED|BOTH_CAPTURE_PINS_REQUIRED'):
                    native.main()
                collect.assert_not_called(); seal.assert_not_called()

    def test_cli_passes_pins_without_resealing(self):
        with patch.object(sys, 'argv', ['refs', '--output', 'unused', '--collect-suite',
                          '--provenance-sha256', 'a' * 64, '--raw-manifest-sha256', 'b' * 64]), \
             patch.object(native, 'collect_suite', return_value=dict(classification='PASS', observed_fields=1,
                          verified_rgb555_pixels=1)) as collect, \
             patch.object(native.capture, 'seal_native_capture') as seal, patch('builtins.print'):
            native.main()
            collect.assert_called_once_with(Path('unused').resolve(), native.capture.CaptureSeal('a' * 64, 'b' * 64))
            seal.assert_not_called()


if __name__ == '__main__':
    unittest.main()
