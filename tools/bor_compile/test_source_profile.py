"""Foreign inspection and fail-closed CLI gates, without generating shared assets."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/bor_compile')]
from compiler import Source
from source_profile import document, discover, inspect, resolve_profile
import byor

MOTU = ROOT / 'Masters of the Universe [v.3.0 Build 4086].pak'


class SourceProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = inspect(MOTU)

    def test_foreign_structure_and_player_authority(self):
        r = self.report
        self.assertEqual([(s['id'], s['name'], s['ifcomplete']) for s in r['sets']], [(0, 'Demo', 0)])
        self.assertEqual([e['source_path'].replace('\\', '/').lower() for e in r['sets'][0]['entries']],
                         ['data/levels/guile2.txt', 'data/levels/holes.txt'])
        self.assertEqual([p['declaration'] for p in r['players']], ['He_Man'])
        self.assertEqual(len(r['models']), 16)
        self.assertEqual(sum(q['source_spawns'] for q in r['queues']), 22)
        self.assertEqual(sum(q['authored_records'] for q in r['queues']), 34)
        self.assertEqual(r['queues'][0]['diagnostics'][0]['code'], 'QUEUE_AT_WITHOUT_RECORD')
        self.assertIsNone(r['source']['authenticated_engine_build'])
        self.assertIsNone(r['profile'])

    def test_inspection_keeps_unknowns_and_script_boundaries(self):
        matrix = self.report['capability_matrix']
        self.assertTrue(any(r['directive']=='rush' for r in matrix))
        self.assertTrue(any(r['directive']=='@cmd' for r in matrix))
        self.assertFalse(any(r['directive']=='void' for r in matrix))
        self.assertEqual(len(self.report['scripts']), 5)
        self.assertTrue(any(d['inline_scripts'] for d in self.report['documents']))
        self.assertEqual(len(self.report['documents']), 99)

    def test_hardware_color_limit_after_rgb555_alias_collapse(self):
        peak = max(self.report['resource_limits'], key=lambda r:r['required_colors'])
        self.assertEqual(peak['model'], 'HBreath')
        self.assertEqual(peak['required_colors'], 204)
        self.assertEqual(peak['minimum_palettes'], 14)
        self.assertEqual(peak['available_colors'], 120)
        self.assertEqual(peak['dimensions'], [110, 90])
        self.assertLessEqual(peak['maximum_scanline_colors'], 120)
        self.assertIn('not proof all SNES', peak['scope'])

    def test_build_reports_real_gaps_and_never_invokes_original_builder(self):
        with patch('source_profile.inspect', return_value=self.report), \
             patch('build_normal_sa1_candidate.build') as builder, \
             contextlib.redirect_stderr(io.StringIO()) as stderr:
            result = byor.main(['build', '--source', str(MOTU), '--set', 'Demo',
                                '--output', 'build/byor-motu'])
        self.assertEqual(result, 2)
        builder.assert_not_called()
        report = json.loads(stderr.getvalue())
        self.assertFalse(report['candidate_produced'])
        self.assertEqual(report['diagnostics'][0]['required_colors'], 204)
        self.assertTrue(any(r['code']=='GENERIC_CAPABILITY_MISSING:@cmd' for r in report['diagnostics']))

    def test_source_set_names_come_from_supplied_archive(self):
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaises(SystemExit):
                byor.main(['build', '--source', str(MOTU), '--set', 'Easy', '--output', 'unused'])
        self.assertIn('Demo', stderr.getvalue())
        self.assertIn('SOURCE_SET_UNKNOWN', stderr.getvalue())

    def test_unknown_does_not_abort_later_sets_or_registry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'data').mkdir()
            (root/'data/levels.txt').write_text('mystery 17\nset New Name\nfile data/stage.txt\nnext\n')
            (root/'data/stage.txt').write_text('strange 1\n')
            (root/'data/models.txt').write_text('load Hero data/hero.txt\n')
            (root/'data/hero.txt').write_text('name Hero\ntype player\n')
            s = Source(root)
            docs = {k:document(s,n) for k,(n,_) in s.index.items()}
            r = discover(s,docs)
            self.assertEqual(r['sets'][0]['name'], 'New Name')
            self.assertTrue(r['sets'][0]['entries'][0]['next_after'])
            self.assertEqual(r['global_settings'][0]['directive'], 'mystery')
            self.assertEqual(r['models'][0]['type'], 'player')


if __name__ == '__main__':
    unittest.main()
