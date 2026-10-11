import unittest
from raster_bank_span_bound import lower_bound
from test_raster_slot_greedy import source_schedule


class BankSpanBoundTests(unittest.TestCase):
    def test_compulsory_adjacent_bank_misses_have_exact_small_bound(self):
        result=lower_bound(source_schedule(),5)
        self.assertEqual(result['solver_status'],'OPTIMAL')
        self.assertEqual(result['validated_integer_peak_span_lower_bound'],32)
        self.assertEqual(result['relaxed_aggregate_peak_span'],32)
        self.assertGreaterEqual(result['aggregate_bank_write_counts'][7][0],1)
        self.assertGreaterEqual(result['aggregate_bank_write_counts'][7][1],1)
        self.assertFalse(result['schedule_proven'])
        self.assertFalse(result['native_timing_admitted'])
        self.assertFalse(result['universal_raster_rejected'])

    def test_separated_banks_charge_two_ranges(self):
        source=source_schedule();source['pieces'][1]['bank']=2
        for row in source['trace']:
            row['resident_before'][2]=row['resident_before'][1];row['resident_before'][1]=[None]*15
            for e in row['updates']:
                if e['bank']==1:e['bank']=2
        result=lower_bound(source,5)
        self.assertEqual(result['solver_status'],'OPTIMAL')
        self.assertEqual(result['validated_integer_peak_span_lower_bound'],40)

    def test_invalid_limit_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'BANK_SPAN_BOUND_TIME_LIMIT'):lower_bound({},0)

    def test_linear_ranges_and_dp_match_small_exact_bound(self):
        for backend in('cp-sat','highs'):
            result=lower_bound(source_schedule(),5,'ranges',backend)
            self.assertEqual(result['validated_integer_peak_span_lower_bound'],32)
            self.assertEqual(result['relaxed_aggregate_peak_span'],32)
            self.assertTrue(result['independent_partition_replayed'])
        with self.assertRaisesRegex(ValueError,'BANK_SPAN_BOUND_BACKEND'):lower_bound({},5,'dp','highs')


if __name__=='__main__':unittest.main()
