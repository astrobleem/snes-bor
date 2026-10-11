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


if __name__ == '__main__': unittest.main()
