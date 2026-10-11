import unittest
from raster_piece_bank_cache import optimize
from raster_slot_greedy import demand


class PieceBankCacheTests(unittest.TestCase):
    def fixture(self):
        from test_raster_word_bank_balance import WordBankBalanceTests
        return WordBankBalanceTests().fixture()[0]

    def test_shared_word_aliases_allow_one_write_with_fixed_object_banks(self):
        source=self.fixture();result=optimize(source,time_limit=5,write_budget=1,window=1,lookahead=0)
        self.assertEqual(result['piece_bank_cache']['status'],'FIXED_PIECE_BANK_CACHE_AND_OPERAND_IDENTITIES_PROVEN')
        self.assertEqual(result['geometry']['oam_entries'],2)
        self.assertEqual(result['pieces'][0]['bank'],result['pieces'][1]['bank'])
        self.assertEqual(result['peak_scheduled_writes'],1)
        self.assertEqual(result['maximum_noninitial_prefetch_latency_lines'],0)
        self.assertTrue(result['piece_bank_cache']['per_bank_word_aliases_counted_once'])
        self.assertFalse(result['piece_bank_cache']['physical_transfer_admitted'])
        self.assertFalse(result['piece_bank_cache']['native_timing_admitted'])
        import numpy as np
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)

    def test_distinct_eligible_banks_require_two_reload_writes(self):
        source=self.fixture()
        for p in source['pieces']:p['allowed_banks']=[p['bank']]
        rejected=optimize(source,time_limit=5,write_budget=1,window=1000,lookahead=0)
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        admitted=optimize(source,time_limit=5,write_budget=2,window=1000,lookahead=0)
        self.assertEqual(admitted['peak_scheduled_writes'],2)
        self.assertEqual(admitted['geometry']['oam_entries'],2)
        self.assertFalse(rejected['universal_raster_rejected'])

    def test_same_words_in_disjoint_math_classes_cannot_share_a_bank(self):
        source=self.fixture();source['pieces'][1]['bank']=5
        for row in source['trace']:
            row['resident_before'][5]=row['resident_before'][1];row['resident_before'][1]=[None]*15
            for event in row['updates']:
                if event['bank']==1:event['bank']=5
        rejected=optimize(source,time_limit=5,write_budget=1,window=1000,lookahead=0,search_strategy='sat')
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        admitted=optimize(source,time_limit=5,write_budget=2,window=1000,lookahead=0)
        self.assertLess(admitted['pieces'][0]['bank'],4)
        self.assertGreaterEqual(admitted['pieces'][1]['bank'],4)


if __name__=='__main__':unittest.main()
