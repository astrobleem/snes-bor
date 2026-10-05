"""Normal's new bindings do not mutate source IR or migrate Easy adapters."""
import sys
import subprocess
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
from compiler import ROOT, Source, stage, model_catalog, key
from production_campaign import compile_queues, bind_queue_identities
from build_spawn_table import (RECORD_KIND_BOSS_IDENTIFIED, RECORD_KIND_PROP,
                               SUBTYPE_IDENTIFIED_ENEMY, SUBTYPE_BIKER, SUBTYPE_SHIFT)
sys.path.insert(0, str(ROOT / 'tools/audio'))
from shipped_content import STAGE_CONFIGS, ROSTER_CONFIGS


class NormalBindingTests(unittest.TestCase):
    def test_all_normal_spawn_source_identity_and_nonidentity_bytes(self):
        configs = [c for c in STAGE_CONFIGS if c.get('source_set_id') == 1]
        self.assertEqual(len(configs), 14)
        self.assertTrue(all(c['queue_identity_policy'] == 'source-identity' for c in configs))
        packed = compile_queues(configs, ROSTER_CONFIGS)
        with patch('production_campaign.bind_queue_identities', side_effect=lambda ir, data, roster, entities: data):
            before = compile_queues(configs, ROSTER_CONFIGS)
        source = Source(configs[0]['pak'])
        models = model_catalog(source)
        spawns = 0
        for cfg in configs:
            ir = stage(source, cfg['source_level'])
            prefix = len(ir.environment.get('hole', []))
            actual, legacy = packed[cfg['spawn']], before[cfg['spawn']]
            self.assertEqual(len(actual), len(legacy))
            self.assertEqual(actual[:prefix * 10], legacy[:prefix * 10])
            for index, event in enumerate(ir.queue, prefix):
                row, old = actual[index * 10:(index + 1) * 10], legacy[index * 10:(index + 1) * 10]
                if event.kind != 'spawn':
                    self.assertEqual(row, old)
                    continue
                spawns += 1
                model = models[event.character.casefold()]
                path = key(model['source_path'])
                bindings = [i for i, r in enumerate(ROSTER_CONFIGS)
                            if r['family'] == cfg['family'] and 1 in r.get('runtime_binding_sets', (0, 1))
                            and key(r['source_character']) in (path.rsplit('/', 1)[0], path.removesuffix('.txt'))]
                self.assertEqual(len(bindings), 1, event.character)
                self.assertEqual(row[9], bindings[0], (cfg['source_level'], event.character))
                self.assertEqual(row[:6], old[:6])  # includes extended map bits
                self.assertEqual(row[7:9], old[7:9])  # HP/2P and contained identity
                self.assertEqual(row[6] & 0x18, old[6] & 0x18)  # low map bits
                if old[6] & 7 == RECORD_KIND_PROP:
                    self.assertEqual(row[6], old[6])
                else:
                    self.assertEqual(row[6] & 7, RECORD_KIND_BOSS_IDENTIFIED)
                    subtype = str(model['entity'].get('subtype') or '').casefold()
                    expected = SUBTYPE_BIKER if subtype == 'biker' else 0 if event.boss else SUBTYPE_IDENTIFIED_ENEMY
                    self.assertEqual(row[6] >> SUBTYPE_SHIFT, expected)
        self.assertGreater(spawns, 0)

    def test_zero_binding_and_all_map_bits_preserved(self):
        event = SimpleNamespace(kind='spawn', character='Ralf', boss=False)
        ir = SimpleNamespace(queue=[event], environment={}, source_path='synthetic')
        for high in range(256):
            for low in (0, 8, 16, 24):
                raw = bytes([1, 2, 3, 4, 5, high, low, 7, 8, 99])
                result = bind_queue_identities(ir, raw, {'ralf': 0}, {'ralf': {}})
                self.assertEqual(result[:6], raw[:6])
                self.assertEqual(result[6], low | RECORD_KIND_BOSS_IDENTIFIED
                                 | (SUBTYPE_IDENTIFIED_ENEMY << SUBTYPE_SHIFT))
                self.assertEqual(result[7:9], raw[7:9])
                self.assertEqual(result[9], 0)
        with self.assertRaisesRegex(ValueError, 'MODEL_UNBOUND'):
            bind_queue_identities(ir, raw, {}, {'ralf': {}})
        with self.assertRaisesRegex(ValueError, 'MODEL_BINDING_RANGE'):
            bind_queue_identities(ir, raw, {'ralf': 256}, {'ralf': {}})

    def test_policy_fail_closed(self):
        cfg = deepcopy(next(c for c in STAGE_CONFIGS if c.get('source_set_id') == 1))
        for policy in (None, 'unknown', 'accepted-legacy'):
            cfg['queue_identity_policy'] = policy
            with self.assertRaisesRegex(ValueError, 'QUEUE_IDENTITY_POLICY'):
                compile_queues([cfg], ROSTER_CONFIGS)

    def test_new_sparse_enemy_and_effect(self):
        cfg = next(c for c in STAGE_CONFIGS if c['source_level'] == 'DATA\\NORMAL\\5A.TXT')
        source = Source(cfg['pak'])
        ir = stage(source, cfg['source_level'])
        packed = compile_queues([cfg], ROSTER_CONFIGS)[cfg['spawn']]
        for index, event in enumerate(ir.queue):
            if event.character not in ('Ramon', 'Time'):
                continue
            self.assertIsNone(event.health)
            record = packed[index * 10:(index + 1) * 10]
            if event.character == 'Ramon':
                self.assertEqual(record[7], 6)  # source10 -> accepted 64/100 HP scale
                self.assertEqual(record[9], 45)
            else:
                self.assertEqual(record[6] >> 5, 6)
                self.assertEqual(record[9], 46)
                self.assertEqual(record[7], 1)  # live pickup slot, source health is zero

    def test_easy_uses_source_identity_bindings(self):
        configs = [c for c in STAGE_CONFIGS if c.get('source_set_id') == 0]
        self.assertTrue(all(c['queue_identity_policy'] == 'source-identity' for c in configs))
        blobs = compile_queues(configs, ROSTER_CONFIGS)
        for cfg in configs:
            ir = stage(Source(cfg['pak']), cfg['source_level'])
            prefix = len(ir.environment.get('hole', []))
            for index, event in enumerate(ir.queue, prefix):
                if event.kind != 'spawn':
                    continue
                record = blobs[cfg['spawn']][index * 10:(index + 1) * 10]
                if event.character.casefold() == 'steamer':
                    self.assertEqual(record[6] >> 5, 7)
                if event.character.casefold() == 'ramon':
                    self.assertEqual(record[9], 45)
                if event.character.casefold() == 'time':
                    self.assertEqual(record[9], 46)
                    self.assertEqual(record[6] >> 5, 6)

    def test_no_new_set_identity_fallback(self):
        configs = [c for c in STAGE_CONFIGS if c.get('source_set_id') == 1]
        with self.assertRaisesRegex(ValueError, 'MODEL_UNBOUND'):
            compile_queues(configs, ROSTER_CONFIGS[:45])


if __name__ == '__main__':
    unittest.main()
