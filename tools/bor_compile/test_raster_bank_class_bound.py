import unittest
import copy
from test_raster_slot_greedy import source_schedule
from raster_bank_class_bound import lower_bound


class BankClassBoundTests(unittest.TestCase):
    def test_shared_words_count_once_inside_class(self):
        result=lower_bound(source_schedule(),lookahead=0,time_limit=5)
        self.assertEqual(result['opaque_class_capacities'],[60,60])
        self.assertEqual(result['peak_write_lower_bound'],0)
        self.assertEqual(result['validated_dual_lower_bound'],0)
        self.assertFalse(result['universal_raster_rejected'])

    def test_all_eight_bank_route_uses_one_class(self):
        source=copy.deepcopy(source_schedule());source['color_math']='subscreen-additive'
        result=lower_bound(source,lookahead=0,time_limit=5)
        self.assertEqual(result['opaque_class_capacities'],[120])
        self.assertEqual(result['bank_classes'],[list(range(8))])


if __name__=='__main__':unittest.main()
