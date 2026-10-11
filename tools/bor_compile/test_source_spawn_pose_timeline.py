import unittest
from pathlib import Path
from compiler import Source
from source_spawn_pose_timeline import intersect,query


class SpawnPoseTests(unittest.TestCase):
    def test_intersections_clip_expiry_and_exclude_touching_boundaries(self):
        parent=[dict(index=i,start_tick=i*5,delay_ticks=5,declaration={})for i in range(3)]
        child=dict(index=3,start_tick=2,delay_ticks=8,declaration={})
        result=intersect(parent,child,3,9)
        self.assertEqual([(r['parent_frame'],r['interval_ticks'])for r in result],[(1,[5,9])])
        self.assertEqual(intersect(parent,child,20,40),[])

    def test_authored_breath_peak_has_parent_hold_pose_without_reachability_claim(self):
        source=Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak')
        r=query(source,'He_ManB','freespecial4','HBreath',11,parent_position=(80,220,0))
        e=r['events'][0];self.assertEqual(e['birth']['birth_tick'],48)
        self.assertEqual(e['child_nominal_frame_interval'],[114,120])
        pose=e['parent_child_intersections'];self.assertEqual([(p['parent_frame'],p['interval_ticks'])for p in pose],[(6,[114,120])])
        self.assertTrue(pose[0]['parent_frame_source']['values'][0].endswith('breath7.png'))
        self.assertEqual(e['birth']['script_position_changes'][0],[2,'position',98.0,220.0,93.0])
        self.assertFalse(r['source_reachability_proven']);self.assertFalse(r['universal_concurrency_bound'])
        with self.assertRaisesRegex(ValueError,'CHILD_FRAME_DOMAIN'):query(source,'He_ManB','freespecial4','HBreath',True)
        with self.assertRaisesRegex(ValueError,'AUTHORED_CHILD_REQUIRED'):query(source,'He_ManB','freespecial4','Knightbot',0)


if __name__=='__main__':unittest.main()
