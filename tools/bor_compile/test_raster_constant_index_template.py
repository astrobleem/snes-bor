import importlib.util,unittest
import numpy as np
from raster_constant_index_template import construct
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets
from raster_obj_compact import unpack
from test_raster_slot_greedy import source_schedule


@unittest.skipUnless(importlib.util.find_spec('ortools'),'optional OR-Tools backend')
class ConstantIndexTemplateTests(unittest.TestCase):
    def test_word_indices_pixels_and_packets_are_preserved(self):
        source=source_schedule();result=construct(source,5)
        verify_packets(result)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        indices={}
        for p,m,words in zip(result['pieces'],result['piece_pixel_masks'],demand(result)[2]):
            image=unpack(m)
            for y,x in zip(*np.where(image)):
                key=p['bank'],int(words[y,x]);s=int(image[y,x])
                self.assertEqual(indices.setdefault(key,s),s)
                self.assertTrue(1<=s<=15)
        self.assertFalse(result['native_presentation_proven'])
        self.assertFalse(result['physical_slot_layout']['universal_raster_rejected'])
        self.assertEqual(result['average_writes'],np.mean([len(r['updates'])for r in result['trace'][1:]]))
        self.assertEqual(result['maximum_noninitial_prefetch_latency_lines'],0)

    def test_invalid_time_budget_is_explicit(self):
        with self.assertRaisesRegex(ValueError,'CONSTANT_INDEX_TIME_DOMAIN'):construct({},0)


if __name__=='__main__':unittest.main()
