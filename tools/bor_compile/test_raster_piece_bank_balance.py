import unittest
import numpy as np
from raster_piece_bank_balance import balance
from raster_slot_greedy import demand
import test_raster_word_bank_balance as fixtures


class PieceBalanceTests(unittest.TestCase):
    def test_fixed_geometry_and_alias_words_replayed(self):
        source = fixtures.WordBankBalanceTests().fixture()[0]
        result = balance(source,steps=200,seed=4,time_limit=5)
        self.assertEqual(len(result['pieces']),len(source['pieces']))
        for a,b in zip(demand(source)[2],demand(result)[2]): np.testing.assert_array_equal(a,b)
        self.assertLessEqual(result['piece_bank_balance']['final_objective'],
                             result['piece_bank_balance']['initial_objective'])
        self.assertFalse(result['piece_bank_balance']['physical_transfer_admitted'])

    def test_explicit_bank_domains_remain_fixed(self):
        source = fixtures.WordBankBalanceTests().fixture()[0]
        for p in source['pieces']: p['allowed_banks']=[p['bank']]
        result = balance(source,steps=200,time_limit=5)
        self.assertEqual(result['piece_bank_assignment'],[p['bank'] for p in source['pieces']])

    def test_paired_exchanges_keep_source_rows_and_declared_domains(self):
        import copy
        source=fixtures.WordBankBalanceTests().fixture()[0];before=copy.deepcopy(source)
        result=balance(source,steps=200,seed=9,time_limit=5,swap_probability=1,sample_equal_best=True)
        self.assertEqual(source,before)
        self.assertGreater(result['piece_bank_balance']['swap_proposals_sampled'],0)
        self.assertGreater(result['piece_bank_balance']['swap_moves_accepted'],0)
        self.assertGreater(result['piece_bank_balance']['equivalent_best_samples'],0)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        self.assertLessEqual(result['piece_bank_balance']['final_objective'],result['piece_bank_balance']['initial_objective'])
        for invalid in(-1,2,True,float('nan')):
            with self.assertRaisesRegex(ValueError,'SWAP_DOMAIN'):balance(source,swap_probability=invalid)
        peak=balance(source,steps=200,seed=10,time_limit=5,swap_probability=.5,sample_equal_best=True,peak_only=True)
        self.assertLessEqual(peak['piece_bank_balance']['final_objective'][:2],peak['piece_bank_balance']['initial_objective'][:2])
        for a,b in zip(demand(source)[2],demand(peak)[2]):np.testing.assert_array_equal(a,b)


if __name__ == '__main__': unittest.main()
