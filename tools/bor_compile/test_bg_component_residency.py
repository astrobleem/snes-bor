import unittest
import numpy as np
from bg_component_residency import plan_plane


class ComponentResidency(unittest.TestCase):
    def test_preload_and_commit_replay_keep_exact_tile_identity(self):
        a=np.zeros((224,256),dtype=np.uint8);b=a.copy();b[0:8,0:8]=1
        c=b.copy();c[0:8,0:8]=2
        report,maps,tiles=plan_plane([a,b,c],8,2)
        self.assertEqual(report['frames'][1]['preload_bytes'],64)
        self.assertEqual(report['frames'][2]['commit_bytes'],64)
        self.assertTrue(all(f['pixel_index_identity_verified'] for f in report['frames']))
        self.assertEqual(len(tiles),192)
        self.assertNotEqual(int(maps[0][0,0]),int(maps[1][0,0]))
    def test_single_frame_capacity_rejected(self):
        a=np.zeros((224,256),dtype=np.uint8);a[0:8,0:8]=1
        with self.assertRaisesRegex(ValueError,'SINGLE_FRAME'):plan_plane([a],8,1)


if __name__=='__main__':unittest.main()
