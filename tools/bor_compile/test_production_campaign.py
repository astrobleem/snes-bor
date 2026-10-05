"""Focused campaign linkage checks; no production build or generated outputs."""
import sys
import io
import unittest
from copy import deepcopy
from unittest.mock import patch
from PIL import Image

from compiler import ROOT, Source, baseline, key, presentation, project, stage
import production_campaign as linker

sys.path.insert(0, str(ROOT / 'tools' / 'audio'))
import shipped_content as shipped


class MemorySource(Source):
    def __init__(self, files):
        self.cache = {key(p): v.encode() for p, v in files.items()}
        self.index = {key(p): (p, None) for p in files}


class ProductionCampaignTests(unittest.TestCase):
    def test_source_entries_and_boundaries(self):
        source = Source(shipped.STAGE_CONFIGS[0]['pak'])
        for source_set in project(source).sets[:2]:
            cid = {'Easy': 'BOR_ORIGINAL', 'Normal': 'BOR_NORMAL_1A_INTERNAL'}[source_set.name]
            entries = shipped.CAMPAIGN_CONFIGS[cid]['entries']
            self.assertEqual(len(entries), 16)
            self.assertEqual([e['kind'].upper() for e in entries],
                             [e.kind for e in source_set.entries])
            self.assertEqual([e['next_after'] for e in entries],
                             [e.next_after for e in source_set.entries])
            scenes = {s['scene_id']: key(s['source_scene']) for s in shipped.SCENE_CONFIGS}
            self.assertEqual([key(e['source_level']) if e['kind'] == 'stage'
                              else scenes[e['scene_id']] for e in entries],
                             [key(e.source_path) for e in source_set.entries])
            configs = {key(c['source_level']): c for c in shipped.STAGE_CONFIGS}
            for entry in source_set.entries:
                if entry.kind == 'STAGE':
                    self.assertEqual(configs[key(entry.source_path)]['source_set_id'],
                                     source_set.source_id)

    def test_legacy_physical_ids_and_import_baseline(self):
        accepted, _ = baseline('c8cbd71b200cab869d3f953bdd07352c172577ed')
        self.assertEqual([key(c['source_level']) for c in shipped.STAGE_CONFIGS[:32]],
                         [key(c['source_level']) for c in accepted['STAGE_CONFIGS'][:32]])
        self.assertEqual(len(shipped.STAGE_MEDIA_BINDINGS), 23)
        for name, ids in shipped.LEGACY_BOR_STAGE_IDS.items():
            source_set = next(s for s in project(Source(shipped.STAGE_CONFIGS[0]['pak'])).sets
                              if s.name == name)
            levels = [key(e.source_path) for e in source_set.entries if e.kind == 'STAGE']
            self.assertEqual([key(shipped.STAGE_CONFIGS[i]['source_level']) for i in ids],
                             levels[:len(ids)])
        for i in shipped.LEGACY_FOREIGN_STAGE_IDS:
            self.assertEqual(shipped.STAGE_CONFIGS[i], accepted['STAGE_CONFIGS'][i])
        for c in shipped.STAGE_CONFIGS[:32]:
            if c['family'] == 'bor-original':
                self.assertTrue(c['spawn'].startswith('out/compiler_campaign/'))
                self.assertEqual(c['queue_identity_policy'], 'source-identity')
        for actual, legacy in zip(shipped.STAGE_MEDIA_BINDINGS[:22], accepted['STAGE_CONFIGS']):
            self.assertEqual(actual, legacy)
        self.assertTrue(any(c['converted_prefix'] == 'out/ramon' for c in shipped.ROSTER_CONFIGS))
        self.assertTrue(any(c['converted_prefix'] == 'out/time' for c in shipped.ROSTER_CONFIGS))

    def fixture(self, extra=''):
        source = MemorySource({
            'DATA/LEVELS.TXT': 'set Easy\nfile easy.txt\nnext\nset Normal\nfile normal.txt\n' + extra,
            'easy.txt': 'background easy.gif',
            'normal.txt': 'background normal.gif',
            'easy.gif': '', 'normal.gif': '',
            'scene.txt': '',
        })
        bitmap = io.BytesIO()
        Image.new('RGB', (2, 2), 'red').save(bitmap, format='GIF')
        source.cache['easy.gif'] = source.cache['normal.gif'] = bitmap.getvalue()
        bindings = [dict(family='bor-original', pak='fixture', source_level='easy.txt',
                         bg='accepted/bg', frontpanel=None, spawn='accepted/spawn.bin')]
        return source, bindings

    def test_exact_content_reuse_and_no_input_mutation(self):
        source, bindings = self.fixture()
        before = deepcopy(bindings)
        with patch.object(linker, 'Source', return_value=source):
            configs, campaigns, _ = linker.link_campaigns(bindings, {}, [])
        self.assertEqual(bindings, before)
        self.assertEqual(configs[1]['bg'], 'accepted/bg')
        self.assertNotEqual(configs[0]['spawn'], configs[1]['spawn'])
        self.assertEqual(presentation(source, stage(source, 'easy.txt')),
                         presentation(source, stage(source, 'normal.txt')))
        bitmap = io.BytesIO()
        Image.new('RGB', (2, 2), 'blue').save(bitmap, format='GIF')
        source.cache['normal.gif'] = bitmap.getvalue()
        with patch.object(linker, 'Source', return_value=source):
            with self.assertRaisesRegex(ValueError, 'STAGE_MEDIA_UNBOUND'):
                linker.link_campaigns(bindings, {}, [])

    def test_unknown_progression_and_stage_fail_closed(self):
        for target in ('DATA/LEVELS.TXT', 'normal.txt'):
            source, bindings = self.fixture()
            source.cache[key(target)] += b'\nteleport 1\n'
            with self.subTest(target=target), patch.object(linker, 'Source', return_value=source):
                with self.assertRaises(ValueError):
                    linker.link_campaigns(bindings, {}, [])

    def test_unbound_scene_fails_closed(self):
        source, bindings = self.fixture('scene scene.txt\n')
        with patch.object(linker, 'Source', return_value=source):
            with self.assertRaisesRegex(ValueError, 'SCENE_MEDIA_UNBOUND'):
                linker.link_campaigns(bindings, {}, [])

    def test_legacy_pin_drift_fails_closed(self):
        source, bindings = self.fixture()
        for pins in ({'Normal': (2,)}, {'Normal': (1, 2)}):
            with self.subTest(pins=pins), patch.object(linker, 'Source', return_value=source):
                with self.assertRaisesRegex(ValueError, 'LEGACY_STAGE_ID_DRIFT'):
                    linker.link_campaigns(bindings, {}, [], legacy_stage_ids=pins)


if __name__ == '__main__':
    unittest.main()
