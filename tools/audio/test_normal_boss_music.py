"""Focused source/predicate tests only; no assembly, encoding or emulator."""
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import normal_boss_music as music


class BossMusicTests(unittest.TestCase):
    def test_exact_s7_profile_boundary(self):
        old = subprocess.check_output(['git','show',
            'c8cbd71b200cab869d3f953bdd07352c172577ed:src/core/spawn.pasm'], cwd=music.ROOT).decode()
        current = music.gate((music.ROOT/'src/core/spawn.pasm').read_text())
        # S7 predates the environment-done label; isolate the same predicate.
        end = old.index('Spawn_Play__advance_boss_music:')
        start = old.rindex('    lda.l Spawn_ScratchKind', 0, end)
        legacy = old[start:old.index('Spawn_Play__advance_index:',end)]
        changed = []
        for campaign in range(4):
            for kind in range(7):
                for subtype in range(4):
                    a = music.selects_boss(legacy,kind,subtype,campaign)
                    b = music.selects_boss(current,kind,subtype,campaign)
                    if a != b: changed.append((campaign,kind,subtype,a,b))
        self.assertEqual(changed,[(3,5,1,True,False)])

    def test_source_tracks_and_actual_cases(self):
        result = music.receipt()
        rows = {r['slot']:r for r in result['stages']}
        self.assertEqual(len(rows),14)
        self.assertEqual((rows[25]['stage_track'],rows[25]['boss_track']),(11,1))
        self.assertEqual([e['queue_index'] for e in rows[25]['biker_events']], [22,23,51,52,53,54,55,56])
        self.assertTrue(all(not e['boss'] for e in rows[25]['biker_events']))
        self.assertEqual(rows[25]['authored_boss_events'],[dict(queue_index=64,at=3200,model='Heavy')])
        self.assertEqual(rows[29]['boss_track'],0)
        self.assertEqual([e['queue_index'] for e in rows[29]['biker_events']],[39,40])

    def test_unknown_instruction_fails_closed(self):
        with self.assertRaises(ValueError):
            music.selects_boss('jsl Unknown',5,1,3)


if __name__=='__main__':unittest.main()
