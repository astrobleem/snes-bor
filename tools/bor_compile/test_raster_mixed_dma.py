import copy,unittest
import test_raster_physical_event_schedule as fixtures
from raster_mixed_dma import partition,compile


class MixedDmaTests(unittest.TestCase):
    def test_sparse_words_use_mode3_with_exact_address_and_color_bytes(self):
        source=fixtures.PhysicalEventScheduleTests().schedule();before=copy.deepcopy(source)
        result=compile(source,target_window=33)
        self.assertEqual(source,before)
        self.assertEqual(result['mixed_dma_transport']['peak_prepared_commit_span'],32)
        packet=result['prepared_mixed_dma_packets'][2]['packets'][0]
        self.assertEqual(packet['mode'],3)
        self.assertEqual(packet['data_hex'],'81811f0093930000')
        self.assertEqual(result['prepared_mixed_dma_packets'][2]['channels_required'],1)
        self.assertFalse(result['mixed_dma_transport']['native_timing_admitted'])

    def test_four_dense_ranges_remain_ordinary_dma(self):
        points=[1,2,17,18,49,50,113,114]
        span,ranges,sparse=partition(points)
        self.assertEqual(span,184);self.assertEqual(len(ranges),4);self.assertFalse(sparse)

    def test_subset_guard_prevents_unbounded_enumeration(self):
        with self.assertRaisesRegex(ValueError,'BOUNDED_SUBSET_LIMIT'):partition(list(range(22)))
        with self.assertRaisesRegex(ValueError,'SUBSET_DOMAIN'):partition([],22)


if __name__=='__main__':unittest.main()
