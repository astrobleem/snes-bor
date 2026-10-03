"""Normal inventory tests: structural assertions only, no emulator/build writes."""
import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import normal_coverage as coverage
from compiler import CAPABILITIES, Directive, Source, key


class NormalCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = coverage.inventory()

    def test_exact_source_all_entries_occurrences_and_scenes(self):
        report = self.report
        self.assertEqual(report['structural_coverage']['status'], 'COMPLETE')
        self.assertEqual(report['structural_coverage']['entries'], 16)
        self.assertEqual(report['structural_coverage']['stages'], 14)
        self.assertEqual(report['structural_coverage']['directive_kinds'], 31)
        self.assertEqual(report['structural_coverage']['occurrences'], 3179)
        self.assertEqual(sum(r['occurrences'] for r in report['directives']),
                         len(report['occurrences']))
        entries = report['entries']
        self.assertEqual([e['ordinal'] for e in entries], list(range(16)))
        self.assertEqual([e['ordinal'] for e in entries if e['next_after']], [2, 3, 6, 8, 10, 14])
        self.assertEqual([(e['ordinal'], e['scene_id'], e['animation_frames'])
                          for e in entries if e['kind'] == 'scene'],
                         [(13, 'RUGAL', 126), (15, 'ENDING', 1997)])
        self.assertEqual([key(e['source_path']) for e in entries[-4:]],
                         ['data/normal/6b.txt', 'data/scenes/rugal.txt',
                          'data/normal/6c.txt', 'data/scenes/ending.txt'])

    def test_actual_lowering_and_physical_bindings(self):
        stages = [r for r in self.report['entries'] if r['kind'] == 'stage']
        self.assertEqual([r['physical_id'] for r in stages], list(range(22, 36)))
        self.assertEqual([r['packed_records'] for r in stages],
                         [43, 37, 22, 84, 45, 40, 31, 63, 52, 64, 94, 107, 19, 34])
        for row in stages:
            self.assertEqual(row['packed_records'], row['queue_records'] + row['hole_prefix'])
            self.assertEqual(len(row['packed_sha256']), 64)
            self.assertTrue(row['media_binding_sources'])
            self.assertTrue(row['encoded_object_slots'])

    def test_every_directive_has_explicit_lowering_consumer_adapter(self):
        for row in self.report['directives']:
            with self.subTest(domain=row['domain'], directive=row['directive']):
                self.assertTrue(row['lowering'])
                self.assertTrue(row['consumer'])
                self.assertTrue(row['compatibility_adapter'])
                self.assertTrue(all(ref['found'] and ref['line'] > 0 for ref in row['static_evidence']))
                self.assertEqual(row['runtime_evidence'], 'NOT_RUN')
        for occurrence in self.report['occurrences']:
            self.assertGreater(occurrence['line'], 0)
            if occurrence['domain'] == 'queue':
                self.assertGreaterEqual(occurrence['queue_index'], 0)

    def test_gaps_are_not_native_or_runtime_passes(self):
        report = self.report
        self.assertEqual(report['native_coverage']['status'], 'NOT_ESTABLISHED')
        self.assertEqual(report['runtime_evidence'], dict(status='NOT_RUN', emulator_used=False, claims=[]))
        self.assertEqual(report['release_verdict'], 'BLOCKED_UNVERIFIED')
        features = {f['feature'] for f in report['features']}
        self.assertTrue({'multiple_frontpanels', 'health_saturation', 'signed_altitude'} <= features)
        self.assertTrue(any(f['status'] == 'PENDING_NATIVE' for f in report['features']))
        self.assertTrue(report['native_coverage']['pending'])
        self.assertNotIn('PASS', json.dumps(report))

    def test_parser_recognition_does_not_grant_coverage(self):
        for domain, parser_domain in [('project', 'levels'), ('stage', 'stage'), ('scene', 'scene')]:
            with self.subTest(domain=domain), patch.dict(CAPABILITIES[parser_domain], teleport='SUPPORTED'):
                with self.assertRaisesRegex(coverage.CoverageError, 'UNMAPPED_DIRECTIVE'):
                    coverage.audit_directives(domain, 'newsource.txt', [Directive(77, 'teleport', ['1'])])
        # Also reject a known parser keyword not encountered/reviewed in the
        # selected Normal block; an allowlist expansion requires review.
        with self.assertRaisesRegex(coverage.CoverageError, 'project.ifcomplete'):
            coverage.audit_directives('project', 'DATA/LEVELS.TXT', [Directive(39, 'ifcomplete', ['1'])])

    def test_held_item_blockers_follow_required_source_types(self):
        report = self.report
        held = report['held_item_coverage']
        authored = [o for o in report['occurrences'] if o['directive'] in ('item', '2pitem')]
        self.assertEqual(held['required_uses'], len(authored))
        self.assertEqual(held['model_types'], {'obstacle': len(authored)})
        for row in report['directives']:
            if row['directive'] in ('item', '2pitem'):
                status = row['required_source']
                self.assertEqual(status['status'], 'COMPAT_ADAPTER')
                self.assertFalse(status['blocks_normal_implementation'])
                self.assertEqual(status['required_uses'], row['occurrences'])
                self.assertEqual(status['unsupported_uses'], [])
                self.assertEqual(row['runtime_evidence'], 'NOT_RUN')
        self.assertFalse(any('queue.item:' in p or 'queue.2pitem:' in p
                             for p in report['native_coverage']['pending']))
        future = coverage.required_use_status(('queue', 'item'),
                                              [dict(directive='item', model_type='enemy')], [])
        self.assertTrue(future['blocks_normal_implementation'])
        self.assertEqual(future['status'], 'PENDING_NATIVE')

    def test_all_frontpanel_sequences_static_not_native(self):
        row = next(r for r in self.report['directives']
                   if (r['domain'], r['directive']) == ('stage', 'frontpanel'))
        self.assertFalse(row['required_source']['blocks_normal_implementation'])
        self.assertEqual(row['required_source']['status'], 'STATIC_IMPLEMENTED')
        self.assertEqual(row['required_source']['native_status'], 'PENDING_NATIVE')
        fp = self.report['frontpanel_coverage']
        self.assertEqual(fp['implementation_status'], 'STATIC_IMPLEMENTED')
        self.assertEqual(fp['native_status'], 'PENDING_NATIVE')
        self.assertEqual(fp['runtime_evidence'], 'NOT_RUN')
        self.assertTrue(all(fp['integration_checks'].values()))
        self.assertEqual((fp['stage_bindings'], fp['declarations'], fp['unique_source_assets']), (7, 10, 9))
        self.assertEqual([key(s['source_path']) for s in fp['sequences']],
                         ['data/normal/'+p+'.txt' for p in ('1a','3b','3c','4b','6a','6b','6c')])
        authored = [o for o in self.report['occurrences'] if o['directive'] == 'frontpanel']
        actual = [(key(s['source_path']), layer['line'], key(layer['source_path']))
                  for s in fp['sequences'] for layer in s['layers']]
        self.assertEqual(actual, [(key(o['source_path']), o['line'], key(o['values'][0])) for o in authored])
        source = Source(coverage.PAK)
        import hashlib
        for s in fp['sequences']:
            for layer in s['layers']:
                self.assertEqual(layer['sha256'], hashlib.sha256(source.read(layer['source_path'])).hexdigest())
        gaps = [f for f in self.report['features'] if f['feature'] == 'multiple_frontpanels']
        self.assertEqual(len(gaps), 1)
        self.assertEqual(key(gaps[0]['source_path']), 'data/normal/1a.txt')
        self.assertEqual(gaps[0]['declarations'], 4)
        self.assertEqual(gaps[0]['status'], 'PENDING_NATIVE')
        self.assertEqual(gaps[0]['implementation_status'], 'STATIC_IMPLEMENTED')
        self.assertEqual(self.report['release_verdict'], 'BLOCKED_UNVERIFIED')

    def test_frontpanel_definitions_without_hooks_remain_pending(self):
        import shipped_content
        configs = [c for c in shipped_content.STAGE_CONFIGS if c.get('source_set_id') == 1]
        original = Path.read_text
        mutations = [
            ('src/main.pasm', 'jsl '+name, '; absent call')
            for name in ('StageFp_BG2ColdInit','StageFp_BG2SceneReset','StageFp_BG2BootDispatch',
                         'StageFp_BG2PlayDispatch','StageFp_BG2OamAttr')]
        mutations += [('src/core/nmi.pasm', 'jsl StageFp_BG2CommitDispatch', '; absent call'),
                      ('src/main.pasm', '.include "core/stage_frontpanel_bg2.pasm"', '; absent include'),
                      ('build_rom.py', 'from stage_frontpanel_bg2 import materialize_normal', 'from stage_frontpanel import materialize_normal')]
        for filename, needle, replacement in mutations:
            def missing(path, *args, **kwargs):
                text = original(path, *args, **kwargs)
                return text.replace(needle, replacement) if path.as_posix().endswith(filename) else text
            with self.subTest(filename=filename, needle=needle), patch.object(Path, 'read_text', missing):
                fp = coverage.frontpanel_evidence(Source(coverage.PAK), configs)
            self.assertEqual(fp['implementation_status'], 'PENDING_IMPLEMENTATION')
            self.assertEqual(fp['native_status'], 'PENDING_NATIVE')
            status = coverage.required_use_status(('stage','frontpanel'), [], [], frontpanel=fp)
            self.assertTrue(status['blocks_normal_implementation'])

    def test_selector_static_implementation_is_not_runtime_proof(self):
        selection = self.report['selection_coverage']
        self.assertEqual(selection['implementation_status'], 'STATIC_IMPLEMENTED')
        self.assertEqual(selection['runtime_evidence'], 'NOT_RUN')
        self.assertEqual(selection['owner'], 'Curie')
        self.assertTrue(all(selection['integration_checks'].values()))
        self.assertEqual(len(selection['requirements']), 2)
        row = next(r for r in self.report['directives']
                   if (r['domain'], r['directive']) == ('project', 'set'))
        self.assertEqual(row['required_source']['status'], 'STATIC_IMPLEMENTED')
        self.assertFalse(row['required_source']['blocks_normal_implementation'])
        self.assertTrue(all(e['found'] for e in row['static_evidence']))
        self.assertFalse(any(gap.startswith('project.set:') for gap in self.report['native_coverage']['pending']))
        self.assertEqual(self.report['release_verdict'], 'BLOCKED_UNVERIFIED')

    def test_selector_definition_without_integration_stays_pending(self):
        original = Path.read_text
        def missing_hook(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if str(path).replace('\\', '/').endswith('src/core/charselect.pasm'):
                return text.replace('jsl BorSetSelect_Play', '; missing selector call')
            return text
        with patch.object(Path, 'read_text', missing_hook):
            result = coverage.selection_evidence()
        self.assertEqual(result['implementation_status'], 'PENDING_IMPLEMENTATION')
        self.assertFalse(result['integration_checks']['difficulty_prompt_hooks'])

    def test_new_source_directive_rejected_in_real_inventory(self):
        for path in ('DATA/NORMAL/1A.TXT', 'DATA/SCENES/ENDING.TXT', 'DATA/LEVELS.TXT'):
            source = Source(coverage.PAK)
            raw = source.read(path)
            if path == 'DATA/LEVELS.TXT':
                # Insert into the actual selected block, not another set.
                raw = re.sub(rb'(set[ \t]+Normal)', rb'\1\nteleport 1', raw)
                self.assertIn(b'teleport', raw)
            else:
                raw += b'\nteleport 1\n'
            source.cache[key(path)] = raw
            with self.subTest(path=path), self.assertRaisesRegex(coverage.CoverageError, 'UNMAPPED_DIRECTIVE'):
                coverage.inventory(source)

    def test_definition_in_comments_is_not_a_consumer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # Fixtures only; no shared/generated production paths.
            (root / 'fake.pasm').write_text('; Consumer:\nOther:\n    rtl\n')
            (root / 'fake.py').write_text('# def lower():\nvalue = "lower"\n')
            self.assertFalse(coverage.locate('fake.pasm#Consumer', root)['found'])
            self.assertFalse(coverage.locate('fake.py#lower', root)['found'])
            self.assertTrue(coverage.locate('fake.pasm#Other', root)['found'])

    def test_missing_consumer_fails_structural_coverage(self):
        original = coverage.locate
        def missing(reference, root=coverage.ROOT):
            if reference.endswith('#StageEnv_ApplySpawnMap'):
                return dict(reference=reference, found=False)
            return original(reference, root)
        with patch.object(coverage, 'locate', side_effect=missing):
            report = coverage.inventory()
        self.assertEqual(report['structural_coverage']['status'], 'INCOMPLETE')
        self.assertTrue(report['structural_coverage']['missing_definitions'])
        self.assertEqual(report['release_verdict'], 'BLOCKED_UNVERIFIED')

    def test_native_requirement_cannot_be_satisfied_by_inventory(self):
        with patch.object(coverage, 'inventory', return_value=self.report), contextlib.redirect_stdout(io.StringIO()) as output:
            code = coverage.main(['--require-native'])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())['runtime_evidence']['status'], 'NOT_RUN')

    def test_normal_time_ramon_use_actual_set_scoped_bindings(self):
        for name in ('time', 'ramon'):
            binding = self.report['model_bindings'][name]
            self.assertTrue(binding['source_defaults'])
            self.assertIn(name, binding['source_definition'].lower())
            encoded = [q for e in self.report['entries'] if e['kind'] == 'stage'
                       for q in e['queue_bindings'] if q['model'].casefold() == name]
            self.assertTrue(encoded)
            self.assertTrue(all(q['encoded_object_slot'] == binding['runtime_slot'] for q in encoded))

    def test_new_recognized_scene_clip_needs_real_lowering(self):
        source = Source(coverage.PAK)
        path = 'DATA/SCENES/ENDING.TXT'
        # Valid animation grammar and valid existing GIF, but not the ending
        # encoder's declared ordered clip list. Parser acceptance must fail.
        source.cache[key(path)] = source.read(path) + b'\nanimation DATA/SCENES/RUGAL.GIF 0 0\n'
        with self.assertRaisesRegex(coverage.CoverageError, 'SCENE_CLIP_LOWERING_UNBOUND'):
            coverage.inventory(source)


if __name__ == '__main__':
    unittest.main()
