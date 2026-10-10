import unittest,itertools
import numpy as np
from source_scene_obj_lower_bound import cover_eight,bound


class SliverBoundTests(unittest.TestCase):
    def test_interval_count_matches_exhaustive_cover(self):
        domain=(0,1,7,8,15,16)
        for used in itertools.product((False,True),repeat=len(domain)):
            points=[x for x,q in zip(domain,used)if q]
            options={sum(1<<i for i,x in enumerate(points)if left<=x<left+8)for left in range(-7,17)}
            costs={0:0}
            for mask in range(1<<len(points)):
                if mask in costs:
                    for option in options:
                        combined=mask|option;costs[combined]=min(costs.get(combined,999),costs[mask]+1)
            self.assertEqual(cover_eight(points),costs[(1<<len(points))-1])

    def test_actor_ownership_and_clipping_are_explicit(self):
        actor=dict(left=-4,top=0,pixels=np.zeros((1,12),dtype=np.int32))
        r=bound([actor,dict(actor)],1,8)
        self.assertEqual(r['trace'][0]['actor_tile_lower_bounds'],[1,1])
        self.assertEqual(r['trace'][0]['merged_pixels_tile_lower_bound'],1)
        self.assertFalse(r['actor_owned_geometry_rejected'])
        actor['pixels'][:]=-1
        self.assertEqual(bound([actor],1,8)['peak_actor_owned_tile_lower_bound'],0)


if __name__=='__main__':unittest.main()
