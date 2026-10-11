import unittest
from raster_global_bank_classes import assign_masks,permutation_bound
from test_raster_slot_greedy import source_schedule


class GlobalBankClassTests(unittest.TestCase):
    def test_shared_geometry_ceiling_combines_disjoint_math_domains(self):
        pieces=[dict(x=i*8,y=0,width=8,height=8,rows={0:[1]},allowed_banks=[0]if i<18 else[4])for i in range(35)]
        rejected=assign_masks(pieces,time_limit=5)
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        self.assertFalse(rejected['universal_raster_rejected'])
        accepted=assign_masks(pieces[:34],time_limit=5)
        self.assertEqual(accepted['status'],'JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN')
        self.assertEqual(accepted['peak_tile_slivers'],34)
        self.assertEqual(accepted['peak_sprites'],34)
        self.assertTrue(accepted['oam_and_sprite_admission_deferred'])
        self.assertFalse(accepted['physical_transfer_admitted'])
        self.assertEqual(set(accepted['assignment']),{0,4})

    def test_global_word_bank_and_rolling_union_are_replayed(self):
        pieces=[dict(x=0,y=0,width=8,height=8,rows={0:list(range(15)),1:[15]},allowed_banks=[0,1])]
        result=assign_masks(pieces,time_limit=5,residency_window_lines=2)
        self.assertEqual(result['status'],'JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN')
        self.assertEqual(len(result['pieces']),2)
        for bank in result['assignment']:
            colors={c for p,b in zip(result['pieces'],result['assignment'])if b==bank for row in p['rows'].values()for c in row}
            self.assertLessEqual(len(colors),15)
        restricted=assign_masks([dict(pieces[0],allowed_banks=[0])],time_limit=5,residency_window_lines=2)
        self.assertEqual(restricted['solver_status'],'INFEASIBLE')

    def test_permutation_bound_preserves_math_eligibility_and_fixed_residency(self):
        report=permutation_bound(source_schedule())
        self.assertEqual(report['legal_permutations_checked'],576)
        self.assertEqual(report['minimum_peak_favorable_span'],32)
        self.assertTrue(all((b<4)==(target<4)for b,target in enumerate(report['best_bank_mapping'])))
        self.assertFalse(report['native_timing_admitted'])


if __name__=='__main__':unittest.main()
