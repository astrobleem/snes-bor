"""Deletion, duplication, gap, inventory and provenance rejection regressions."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import fused_capture_evidence as capture


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def make_capture(base, count=3):
    root = base / 'capture'
    for case in capture.CASES:
        folder = root / case
        native = folder / 'native'
        native.mkdir(parents=True)
        (native / 'bor.sfc').write_bytes(b'executable')
        (native / 'bor.msu').write_bytes(b'immutable synthetic media')
        (native / 'events.log').write_bytes(b'raw observer log')
        write_json(folder / 'contract.json', {'case': case})
        write_json(folder / 'exact-coverage-profile.json', {})
        fields = []
        for index in range(count):
            row = dict(index=index, ppu=dict(frameCount=520 + index))
            for extension, key in (('png', 'screenshot_sha256'), ('vram', 'vram_sha256')):
                path = native / f'field-{index:04d}.{extension}'
                path.write_bytes(f'{case}/{index}/{extension}'.encode())
                row[key] = capture.sha(path)
            fields.append(row)
        write_json(folder / 'fields.json', fields)
    seal = capture.seal_native_capture(root, base=base,
        msu_sha256=hashlib.sha256(b'immutable synthetic media').hexdigest())
    return root, seal


class FusedCaptureEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root, self.seal = make_capture(self.base)
        self.folder = self.root / 'success'
        self.fields_path = self.folder / 'fields.json'
        self.fields = json.loads(self.fields_path.read_bytes())

    def verify(self):
        return capture.verify_capture(self.root, self.seal, base=self.base)

    def repin(self, name, value):
        path = self.root / name
        write_json(path, value)
        self.seal = capture.CaptureSeal(capture.sha(self.root / capture.PROVENANCE),
                                       capture.sha(self.root / capture.RAW_MANIFEST),
                                       self.seal.msu_sha256)

    def copied_origins(self):
        origins = self.base / 'original'
        provenance = json.loads((self.root / capture.PROVENANCE).read_bytes())
        for case in capture.CASES:
            shutil.copytree(self.root / case, origins / case)
            provenance['case_roots'][case] = f'original/{case}'
        for row in provenance['copies']:
            row['source'] = row['source'].replace('capture/', 'original/', 1)
        self.repin(capture.PROVENANCE, provenance)
        return origins

    def test_complete_fresh_capture_has_exact_coverage_and_raw_inventory(self):
        result = self.verify()
        self.assertEqual(result['observed_fields'], 24)
        self.assertEqual(result['raw_inputs'], 80)
        self.assertEqual(result['verified_origins'], 80)
        self.assertEqual(result['cases']['success'], dict(fields=3, first_frame=520,
            last_frame=522, consecutive=True, exact_png_vram_inventory=True))

    def test_missing_middle_record_duplicate_and_reordered_indices_reject(self):
        missing = copy.deepcopy(self.fields); del missing[1]
        duplicate = copy.deepcopy(self.fields); duplicate[1] = duplicate[0]
        reordered = list(reversed(self.fields))
        for changed in (missing, duplicate, reordered):
            with self.subTest(fields=changed):
                write_json(self.fields_path, changed)
                with self.assertRaisesRegex(ValueError, 'FIELD_INDEX'):
                    capture.verify_field_inventory(self.folder)

    def test_duplicate_gapped_and_reversed_physical_frames_reject(self):
        for frames in ((520, 520, 522), (520, 522, 523), (522, 521, 520)):
            with self.subTest(frames=frames):
                changed = copy.deepcopy(self.fields)
                for field, frame in zip(changed, frames):
                    field['ppu']['frameCount'] = frame
                write_json(self.fields_path, changed)
                with self.assertRaisesRegex(ValueError, 'FIELD_FRAME_SEQUENCE'):
                    capture.verify_field_inventory(self.folder)

    def test_non_list_empty_and_non_object_fields_reject(self):
        for value in ({}, [], [None]):
            with self.subTest(value=value):
                write_json(self.fields_path, value)
                with self.assertRaisesRegex(ValueError, 'FIELDS_NONEMPTY|FIELD_INDEX'):
                    capture.verify_field_inventory(self.folder)

    def test_indices_and_frames_require_integers_not_booleans(self):
        for key, value in (('index', False), ('index', '0'), ('frameCount', True),
                           ('frameCount', '520'), ('frameCount', -1)):
            with self.subTest(key=key, value=value):
                changed = copy.deepcopy(self.fields)
                target = changed[0] if key == 'index' else changed[0]['ppu']
                target[key] = value
                write_json(self.fields_path, changed)
                with self.assertRaisesRegex(ValueError, 'FIELD_INDEX|FIELD_FRAME_TYPE'):
                    capture.verify_field_inventory(self.folder)

    def test_removed_last_record_and_files_cannot_shorten_sealed_capture(self):
        write_json(self.fields_path, self.fields[:-1])
        for extension in ('png', 'vram'):
            (self.folder / 'native' / f'field-0002.{extension}').unlink()
        self.assertEqual(capture.verify_field_inventory(self.folder)['fields'], 2)
        with self.assertRaisesRegex(ValueError, 'COPY_SOURCE_HASH|RAW_INPUT_HASH|RAW_INVENTORY'):
            self.verify()

    def test_missing_png_and_vram_reject(self):
        for extension in ('png', 'vram'):
            path = self.folder / 'native' / f'field-0001.{extension}'
            original = path.read_bytes(); path.unlink()
            with self.subTest(extension=extension):
                with self.assertRaisesRegex(ValueError, 'FIELD_.*_INVENTORY'):
                    capture.verify_field_inventory(self.folder)
            path.write_bytes(original)

    def test_extra_png_and_vram_including_nested_captures_reject(self):
        for name in ('field-0099.png', 'field-0099.vram', 'nested/field-0000.png'):
            path = self.folder / 'native' / name
            path.parent.mkdir(exist_ok=True); path.write_bytes(b'extra')
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, 'FIELD_.*_INVENTORY'):
                    capture.verify_field_inventory(self.folder)
            path.unlink()

    def test_directory_cannot_replace_png_or_vram_file(self):
        for extension in ('png', 'vram'):
            path = self.folder / 'native' / f'field-0001.{extension}'
            original = path.read_bytes(); path.unlink(); path.mkdir()
            with self.subTest(extension=extension):
                with self.assertRaisesRegex(ValueError, 'FIELD_.*_FILE'):
                    capture.verify_field_inventory(self.folder)
            path.rmdir(); path.write_bytes(original)

    def test_field_metadata_hashes_are_enforced(self):
        changed = copy.deepcopy(self.fields)
        changed[0]['screenshot_sha256'] = 'f' * 64
        write_json(self.fields_path, changed)
        with self.assertRaisesRegex(ValueError, 'FIELD_PNG_HASH'):
            capture.verify_field_inventory(self.folder)

    def test_raw_executable_and_log_mutations_reject(self):
        for name in ('bor.sfc', 'events.log'):
            path = self.folder / 'native' / name
            original = path.read_bytes(); path.write_bytes(original + b'tampered')
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, 'COPY_SOURCE_HASH|RAW_INPUT_HASH'):
                    self.verify()
            path.write_bytes(original)

    def test_shared_msu_is_independently_pinned_despite_manifest_exclusion(self):
        self.copied_origins()
        for path in (self.folder / 'native' / 'bor.msu',
                     self.base / 'original' / 'success' / 'native' / 'bor.msu'):
            original=path.read_bytes();path.write_bytes(b'changed shared media')
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError,'MSU_INPUT_HASH'):
                    self.verify()
            path.write_bytes(original)

    def test_both_manifest_digests_are_checked_before_parsing(self):
        for name in (capture.PROVENANCE, capture.RAW_MANIFEST):
            path = self.root / name
            original = path.read_bytes(); path.write_bytes(b'{ malformed')
            with self.subTest(name=name), patch.object(capture.json, 'loads') as parse:
                # The provenance may be parsed first when testing the raw pin.
                if name == capture.RAW_MANIFEST:
                    parse.side_effect = lambda raw: json.JSONDecoder().decode(raw.decode())
                with self.assertRaisesRegex(ValueError, 'PROVENANCE_DIGEST|RAW_MANIFEST_DIGEST'):
                    self.verify()
                self.assertEqual(parse.call_count, 0 if name == capture.PROVENANCE else 1)
            path.write_bytes(original)

    def test_missing_or_directory_manifest_rejects(self):
        path = self.root / capture.PROVENANCE
        original = path.read_bytes(); path.unlink()
        with self.assertRaisesRegex(ValueError, 'PROVENANCE_FILE'):
            self.verify()
        path.mkdir()
        with self.assertRaisesRegex(ValueError, 'PROVENANCE_FILE'):
            self.verify()
        path.rmdir(); path.write_bytes(original)

    def test_manifest_omission_cannot_hide_an_existing_raw_input(self):
        rows = json.loads((self.root / capture.RAW_MANIFEST).read_bytes())
        self.repin(capture.RAW_MANIFEST, rows[1:])
        with self.assertRaisesRegex(ValueError, 'RAW_INVENTORY'):
            self.verify()

    def test_duplicate_raw_manifest_paths_reject(self):
        rows = json.loads((self.root / capture.RAW_MANIFEST).read_bytes())
        self.repin(capture.RAW_MANIFEST, rows + rows[:1])
        with self.assertRaisesRegex(ValueError, 'RAW_DUPLICATE'):
            self.verify()

    def test_extra_unsealed_native_input_rejects(self):
        (self.folder / 'native' / 'unexpected.bin').write_bytes(b'unsealed')
        with self.assertRaisesRegex(ValueError, 'RAW_INVENTORY'):
            self.verify()

    def test_raw_digest_must_agree_with_provenance_digest(self):
        rows = json.loads((self.root / capture.RAW_MANIFEST).read_bytes())
        rows[0]['sha256'] = 'f' * 64
        self.repin(capture.RAW_MANIFEST, rows)
        with self.assertRaisesRegex(ValueError, 'RAW_PROVENANCE_MAPPING'):
            self.verify()

    def test_duplicate_copy_and_wrong_case_mapping_reject(self):
        original = json.loads((self.root / capture.PROVENANCE).read_bytes())
        changed = copy.deepcopy(original); changed['copies'].append(changed['copies'][0])
        self.repin(capture.PROVENANCE, changed)
        with self.assertRaisesRegex(ValueError, 'COPY_DUPLICATE'):
            self.verify()
        changed = copy.deepcopy(original)
        changed['copies'][0]['source'] = changed['copies'][0]['source'].replace('/early/', '/ready/')
        self.repin(capture.PROVENANCE, changed)
        with self.assertRaisesRegex(ValueError, 'COPY_SOURCE_MAPPING'):
            self.verify()

    def test_copied_origins_and_destinations_are_both_hashed(self):
        origins = self.copied_origins()
        self.verify()
        path = origins / 'success' / 'native' / 'bor.sfc'
        path.write_bytes(b'changed origin')
        with self.assertRaisesRegex(ValueError, 'COPY_SOURCE_HASH'):
            self.verify()

    def test_copied_raw_destination_mutation_rejects(self):
        self.copied_origins()
        (self.folder / 'native' / 'bor.sfc').write_bytes(b'changed destination')
        with self.assertRaisesRegex(ValueError, 'RAW_INPUT_HASH'):
            self.verify()

    def test_path_traversal_rejects_even_with_fixture_manifest_pin(self):
        rows = json.loads((self.root / capture.RAW_MANIFEST).read_bytes())
        rows[0]['path'] = '../outside.bin'
        self.repin(capture.RAW_MANIFEST, rows)
        with self.assertRaisesRegex(ValueError, 'PATH_ESCAPE'):
            self.verify()

    def test_sealer_refuses_to_refresh_existing_evidence(self):
        with self.assertRaisesRegex(ValueError, 'SEAL_ALREADY_EXISTS'):
            capture.seal_native_capture(self.root, base=self.base)

    def test_derived_case_reports_can_be_rewritten_without_resealing_raw_inputs(self):
        before = self.verify()
        write_json(self.folder / 'certified.json', {'derived': 'new result'})
        self.assertEqual(self.verify(), before)


if __name__ == '__main__':
    unittest.main()
