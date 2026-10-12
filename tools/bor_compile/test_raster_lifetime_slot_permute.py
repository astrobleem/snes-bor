import copy,unittest
import numpy as np
import test_raster_physical_event_schedule as fixtures
from raster_lifetime_slot_permute import optimize
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets
from raster_obj_compact import unpack


class LifetimeSlotPermutationTests(unittest.TestCase):
    def test_connected_component_exchange_preserves_overlapping_lifetimes(self):
        source=fixtures.PhysicalEventScheduleTests().schedule()
        source['trace'][0]['updates'].append(dict(bank=0,slot=2,old=None,color=1024))
        for row in source['trace'][1:]:row['resident_before'][0][1]=1024
        image=unpack(source['piece_pixel_masks'][0]);image[0,1]=2;image[1,1]=2;flat=image.flatten()
        source['piece_pixel_masks'][0]['pixels_hex']=(flat[::2]|flat[1::2]<<4).tobytes().hex()
        result=optimize(source,steps=2000,time_limit=5,seed=637,target_window=1,kempe_probability=1)
        verify_packets(result)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        self.assertGreaterEqual(result['physical_slot_layout']['maximum_accepted_kempe_component_size'],3)
        self.assertTrue(result['physical_slot_layout']['overlap_constraints_verified'])

    def test_reloads_and_opaque_zero_survive_legal_lifetime_exchanges(self):
        source=fixtures.PhysicalEventScheduleTests().schedule();before=copy.deepcopy(source)
        result=optimize(source,steps=1000,time_limit=5,seed=635,target_window=1)
        self.assertEqual(source,before);self.assertEqual(source['pieces'],result['pieces'])
        verify_packets(result)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        report=result['physical_slot_layout']
        self.assertTrue(report['overlap_constraints_verified'])
        self.assertTrue(report['write_times_fixed'])
        self.assertFalse(report['native_timing_admitted'])
        self.assertLessEqual(report['peak_prepared_commit_span'],40)
        self.assertEqual(result['maximum_noninitial_prefetch_latency_lines'],0)

    def test_invalid_search_domain_fails_explicitly(self):
        with self.assertRaisesRegex(ValueError,'LIFETIME_RECOLOR_DOMAIN'):optimize({},steps=-1)


if __name__=='__main__':unittest.main()
