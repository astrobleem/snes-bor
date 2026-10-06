import unittest
import numpy as np
from bg_component_residency import plan_plane
from bg_component_deadlines import derive_jobs, schedule, replay


class Deadlines(unittest.TestCase):
    def test_prefetch_free_slot_and_defer_last_live_slot(self):
        a=np.zeros((224,256),dtype=np.uint8)
        b=a.copy();b[:8,:8]=1
        c=a.copy();c[:8,:8]=2
        plan={};maps={}
        for name,bpp in [('high',8),('low',2)]:
            plan[name],maps[name],_=plan_plane([a,b,c],bpp,2)
        starts=[0,2,4];jobs=derive_jobs(plan,maps,starts)
        self.assertEqual([j['release'] for j in jobs],[0,4,0,4])
        self.assertEqual([j['deadline'] for j in jobs],[2,4,2,4])
        fields,passed=schedule(jobs,{},4,20000)
        self.assertTrue(passed)
        self.assertTrue(replay(fields,plan,maps,starts))
        self.assertEqual(len(fields[0]['jobs']),2)
        self.assertEqual(len(fields[4]['jobs']),2)

    def test_mandatory_map_transfer_cannot_bypass_budget(self):
        fields,passed=schedule([],{1:[dict(address=0xf000,bytes=2048)]},1,10000)
        self.assertFalse(passed)
        self.assertTrue(fields[-1]['mandatory_budget_exceeded'])


if __name__=='__main__':unittest.main()
