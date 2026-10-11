import copy,hashlib,unittest
from unittest.mock import patch
import numpy as np
from source_obj_pool_segments import merge
from raster_math_windows import compile_mask
from source_bg_feasibility import rgb555


class PoolSegmentTests(unittest.TestCase):
    def fixture(self):
        pixels=np.full((3,8),-1,dtype=np.int32);pixels[:,0]=[1,2,3]
        actor=dict(pixels=pixels,left=0,top=0,metadata=dict(alpha=0))
        background=np.zeros((224,256,3),dtype=np.uint8);expected=background.copy();expected[:3,0,0]=[8,16,24]
        digest=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest()
        def segment(first,last):
            return dict(status='INTEGER_POOL_SOURCE_REPLAY_PROVEN',metadata={},source_rgb555_sha256=digest,
                full_interval_source_pixels_verified=True,zero_main_clipping_palette_demand_relaxed=False,
                selected_modes={str(y):'add'for y in range(first,last+1)},
                selected_palette_residency={str(y):{'0':[y+1],'1':[]}for y in range(first,last+1)},
                compiled_color_window_descriptors={str(y):compile_mask([True]*256)for y in range(first,last+1)})
        return [actor],background,expected,[segment(0,1),segment(1,2)]

    def run_merge(self,segments,actors,background,expected,budget=1):
        with patch('source_obj_pool_segments.prepare',return_value=(actors,{},expected)),patch('source_obj_pool_segments.compose_rgb8',return_value=(background,{})):
            return merge(None,None,{},segments,budget)

    def test_boundary_identity_and_full_pixel_replay(self):
        actors,bg,expected,segments=self.fixture()
        r=self.run_merge(segments,actors,bg,expected)
        self.assertEqual(r['checked_visible_source_pixels'],3)
        self.assertEqual(r['peak_replayed_pool_writes'],1)
        self.assertEqual(r['segment_boundaries'],[1])
        self.assertFalse(r['physical_transfer_admitted'])
        with self.assertRaisesRegex(ValueError,'WRITE_BUDGET'):
            self.run_merge(segments,actors,bg,expected,budget=0)

    def test_boundary_reset_and_missing_literal_word_are_rejected(self):
        actors,bg,expected,segments=self.fixture();bad=copy.deepcopy(segments)
        bad[1]['selected_palette_residency']['1']['0']=[3]
        with self.assertRaisesRegex(ValueError,'BOUNDARY_PALETTE_RESET'):self.run_merge(bad,actors,bg,expected)
        bad=copy.deepcopy(segments);bad[1]['selected_palette_residency']['2']['0']=[4]
        with self.assertRaisesRegex(ValueError,'ORDINARY_LITERAL_MISSING'):self.run_merge(bad,actors,bg,expected)


if __name__=='__main__':unittest.main()
