"""S7 presentation compatibility, independent of authored LEVELS next flags."""
from copy import deepcopy
import subprocess
import sys
import unittest
from compiler import ROOT, Source, project
from production_campaign import completion_flags
sys.path.insert(0, str(ROOT / 'tools/audio'))
from shipped_content import CAMPAIGN_CONFIGS, STAGE_CONFIGS

PIN = 'c8cbd71b200cab869d3f953bdd07352c172577ed'

class EasyCompletionTests(unittest.TestCase):
    def test_authored_flags_unmodified_and_runtime_policy_explicit(self):
        source = Source(STAGE_CONFIGS[0]['pak'])
        sets = {s.name: s for s in project(source).sets}
        for name, cid in [('Easy', 'BOR_ORIGINAL'), ('Normal', 'BOR_NORMAL_1A_INTERNAL')]:
            cfg = CAMPAIGN_CONFIGS[cid]
            before = deepcopy(cfg['entries'])
            flags = completion_flags(cfg['entries'], name)
            self.assertEqual(cfg['entries'], before)
            self.assertEqual([e['next_after'] for e in before], [e.next_after for e in sets[name].entries])
            self.assertEqual(cfg['completion_flags'], flags)
            self.assertEqual(flags, [1] * 15 + [0] if name == 'Easy' else [int(e.next_after) for e in sets[name].entries])
        self.assertEqual(CAMPAIGN_CONFIGS['BOR_ORIGINAL']['completion_flags'][:3], [1, 1, 1])

    def test_s7_pending_scene_evidence(self):
        def pinned(path):
            return subprocess.check_output(['git', 'show', PIN + ':' + path], cwd=ROOT, text=True)
        ending = pinned('src/core/ending.pasm')
        dispatch = ending.split('StageComplete_Dispatch:', 1)[1]
        self.assertIn('cmp #CAMPAIGN_BOR_ORIGINAL\n    beq StageComplete_Dispatch__source_next', dispatch)
        campaign = pinned('src/core/campaign.pasm')
        continuation = campaign.split('Game_Campaign_AdvanceAfterScene:', 1)[1]
        self.assertIn('bcs Game_Campaign_AdvanceAfterScene__end', continuation)
        self.assertIn('dec a\n    sta.l Game_CampaignOrdinal', continuation)
        self.assertIn('lda #1\n    sta.l Stage_LoadPending', continuation)
        self.assertIn('Game_Campaign_AdvanceAfterScene__end:\n    jsl Game_Campaign_HandleEnd', continuation)

    def test_unknown_policy_rejected(self):
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_COMPLETION_POLICY'):
            completion_flags([], 'unknown')

if __name__ == '__main__':
    unittest.main()
