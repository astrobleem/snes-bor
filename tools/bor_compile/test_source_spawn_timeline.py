import unittest
from pathlib import Path
from compiler import Source
from source_spawn_timeline import derive,overlap


class SpawnTimelineTests(unittest.TestCase):
    def test_expiry_boundary_and_duplicate_births(self):
        peak,rows=overlap([dict(birth_tick=0,expiry_tick=10),dict(birth_tick=10,expiry_tick=20),dict(birth_tick=10,expiry_tick=11)])
        self.assertEqual(peak,2)
        self.assertEqual(next(r for r in rows if r['tick']==10)['active_events'],[1,2])
        self.assertEqual(rows[-1]['count'],0)

    def test_actual_script_body_positions_and_conditional_source_lifetimes(self):
        source=Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak')
        report=derive(source,parent_position=(1880,220,0),direction=0)
        breath=next(a for a in report['animations']if a['parent_model']=='He_ManB')
        event=breath['births'][0]
        self.assertEqual((event['birth_tick'],event['expiry_tick'],event['lifespan_ticks']),(48,348,300))
        self.assertEqual(event['script_position_changes'][0],[2,'position',1862.0,220.0,93.0])
        rise=next(a for a in report['animations']if a['parent_model']=='Skeletor'and a['animation']=='rise')
        self.assertEqual((len(rise['births']),rise['peak_declared_lifetime_overlap_upper_bound']),(16,13))
        self.assertFalse(rise['child_initialization_and_callbacks_bound'])
        self.assertFalse(report['source_reachability_proven'])
        self.assertFalse(report['native_presentation_proven'])


if __name__=='__main__':unittest.main()
