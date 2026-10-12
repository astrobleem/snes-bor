import unittest
import numpy as np
from source_visible_obj_composite import merge_visible_actors


class VisibleCompositeTests(unittest.TestCase):
    def test_source_dimensions_alpha_and_owner_survive_geometry_fusion(self):
        actors=[dict(pixels=np.array([[1,-1],[2,3]]),left=-1,top=0,metadata=dict(alpha=1))]
        with self.assertRaisesRegex(ValueError,'UNCLIPPED'):merge_visible_actors(actors,(4,4))
        actors[0]['pixels'][0,0]=actors[0]['pixels'][1,0]=-1
        actors.append(dict(pixels=np.array([[7,8]]),left=1,top=2,metadata=dict(alpha=0)))
        fused,proof=merge_visible_actors(actors,(4,4))
        self.assertEqual(fused[0]['pixels'][1,0],3)
        self.assertEqual(fused[0]['pixels'][2,1:3].tolist(),[7,8])
        self.assertEqual(fused[0]['source_owner_indices'][2,1:3].tolist(),[1,1])
        self.assertEqual(proof['source_actors'][0]['source_dimensions'],[2,2])
        self.assertEqual(proof['source_actors'][0]['source_metadata'],dict(alpha=1))
        self.assertFalse(proof['live_compositor_admitted'])
        actors.append(dict(pixels=np.array([[9]]),left=0,top=1))
        with self.assertRaisesRegex(ValueError,'OWNERSHIP_OVERLAP'):merge_visible_actors(actors,(4,4))


if __name__=='__main__':unittest.main()
