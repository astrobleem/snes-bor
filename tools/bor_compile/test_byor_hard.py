"""Focused BYOR front door and independent Hard source linkage gates."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from compiler import ROOT, Source, key, project, stage
from production_campaign import compile_queues, link_campaigns
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/audio')]
import byor
import build_rom
import shipped_content as shipped
from stage_water import normal_stage_inputs


class ByorHardTests(unittest.TestCase):
    def test_source_route_queue_and_environment_linkage(self):
        source = Source(shipped.STAGE_CONFIGS[0]['pak'])
        sets = project(source).sets
        self.assertEqual([(s.name, s.ifcomplete) for s in sets],
                         [('Easy', 0), ('Normal', 0), ('Hard', 0), ('Bonus', 1)])
        hard = sets[2]
        entries = shipped.CAMPAIGN_CONFIGS['BOR_HARD']['entries']
        scenes = {s['scene_id']: key(s['source_scene']) for s in shipped.SCENE_CONFIGS}
        self.assertEqual([key(e['source_level']) if e['kind'] == 'stage'
                          else scenes[e['scene_id']] for e in entries],
                         [key(e.source_path) for e in hard.entries])
        self.assertEqual([e['next_after'] for e in entries],
                         [e.next_after for e in hard.entries])
        configs = [c for c in shipped.STAGE_CONFIGS if c.get('source_set_id') == 2]
        blobs = compile_queues(configs, shipped.ROSTER_CONFIGS)
        self.assertEqual(len(configs), 14)
        self.assertEqual(len(blobs), 14)
        for cfg in configs:
            ir = stage(source, cfg['source_level'])
            self.assertEqual(len(blobs[cfg['spawn']]),
                             10 * (len(ir.queue) + len(ir.environment.get('hole', []))))
        _, parsed = normal_stage_inputs(shipped.STAGE_CONFIGS)
        self.assertEqual(Counter(shipped.STAGE_CONFIGS[i]['source_set_id'] for i in parsed),
                         {0: 14, 1: 14, 2: 14, 3: 1})

    def test_missing_hard_model_fails_closed(self):
        configs = [c for c in shipped.STAGE_CONFIGS if c.get('source_set_id') == 2]
        roster = deepcopy(shipped.ROSTER_CONFIGS)
        for row in roster:
            if row['source_character'].endswith('RAMON'):
                row['runtime_binding_sets'] = (1,)
        with self.assertRaisesRegex(ValueError, 'MODEL_UNBOUND.*Ramon'):
            compile_queues(configs, roster)

    def test_front_door_capability_rejection_and_pipeline_delegation(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(SystemExit) as error:
                byor.main(['build', '--source', str(Path(temp) / 'unknown.pak'),
                           '--set', 'Hard', '--output', temp])
            self.assertEqual(error.exception.code, 2)
        with patch('build_normal_sa1_candidate.build', return_value=(Path('candidate'),
                   {'candidate': {'rom_sha256': 'rom', 'msu_sha256': 'msu'}})) as builder:
            self.assertEqual(byor.main(['build', '--set', 'Hard', '--output', 'candidate']), 0)
            builder.assert_called_once_with(Path('candidate'), None, source_set='Hard')

    def test_default_build_does_not_expose_hard(self):
        import io
        text = io.StringIO()
        real_open = open
        def output_only(path, *args, **kwargs):
            return text if str(path) == 'tools/audio/campaign_config.pasm' else real_open(path, *args, **kwargs)
        with patch('builtins.open', side_effect=output_only), patch.object(text, 'close'):
            build_rom.write_campaign_include(normal_candidate=True)
        self.assertIn('BorSet_ContentAvailable:\n    .db 1, 1, 0, 0', text.getvalue())
        self.assertIn('Campaign_Source_Counts:\n    .db 16, 16, 16, 2', text.getvalue())


if __name__ == '__main__':
    unittest.main()
