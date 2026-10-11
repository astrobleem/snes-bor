import hashlib,importlib.util,json,unittest
import numpy as np
from raster_row_slot_permutations import optimize
from raster_slot_greedy import demand
import test_raster_slot_layout as fixtures


@unittest.skipUnless(importlib.util.find_spec('ortools'),'optional OR-Tools backend')
class RowSlotPermutationTests(unittest.TestCase):
    def test_restricted_interval_retains_explicit_partial_identity_contract(self):
        from raster_bank_residency import restrict_interval
        source=restrict_interval(fixtures.SlotLayoutTests().schedule(),2,2)
        result=optimize(source,348,10,free_residency=True)
        report=result['physical_slot_layout']
        self.assertTrue(report['outside_interval_pixels_relaxed'])
        self.assertFalse(report['complete_source_frame_pixel_identity_proven'])
        self.assertFalse(report['full_frame_transfer_window_enforced'])
        self.assertFalse(report['native_timing_admitted'])
        self.assertEqual(result['status'],'RESTRICTED_SCANLINE_DEMAND_ONLY')
        with self.assertRaises(ValueError):demand(result)
        _,_,before=demand(source,allow_restricted=True)
        _,_,after=demand(result,allow_restricted=True)
        self.assertTrue(all(np.array_equal(a,b)for a,b in zip(before,after)))

    def test_packet_and_pixel_replay_with_fixed_banks_and_opaque_zero(self):
        source=fixtures.SlotLayoutTests().schedule()
        source.update(scanline_math_controls_source_bound=True,selected_modes={'0':'subtract'},compiled_color_window_descriptors={'0':{'bounds':[[0,15],[255,0]]}})
        result=optimize(source,356,10,free_residency=True)
        self.assertTrue(result['physical_slot_layout']['live_slot_moves_allowed'])
        self.assertFalse(result['physical_slot_layout']['fixed_resident_sets'])
        self.assertTrue(result['physical_slot_layout']['all_packet_cgram_identities_verified'])
        self.assertEqual(result['pieces'],source['pieces'])
        _,_,a=demand(source);_,_,b=demand(result)
        self.assertTrue(all(np.array_equal(x,y)for x,y in zip(a,b)))
        payload=dict(pieces=result['pieces'],pixel_masks=result['piece_pixel_masks'],trace=result['trace'],selected_modes=source['selected_modes'],compiled_color_window_descriptors=source['compiled_color_window_descriptors'])
        self.assertEqual(result['compiled_schedule_sha256'],hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest())
        self.assertFalse(result['physical_slot_layout']['native_timing_admitted'])

    def test_source_word_verified_physical_hint(self):
        import copy
        source=fixtures.SlotLayoutTests().schedule()
        hint=optimize(source,356,10,free_residency=True)
        result=optimize(source,356,10,free_residency=True,layout_hint=hint)
        self.assertTrue(result['physical_slot_layout']['physical_layout_hint_used'])
        self.assertTrue(result['physical_slot_layout']['pixel_color_identity_verified'])
        invalid=copy.deepcopy(hint);invalid['source_rgb555_sha256']='different'
        with self.assertRaisesRegex(ValueError,'ROW_SLOT_HINT_IDENTITY'):
            optimize(source,356,10,free_residency=True,layout_hint=invalid)

    def test_local_repair_keeps_surrounding_physical_states_and_full_pixels(self):
        source=fixtures.SlotLayoutTests().schedule()
        hint=optimize(source,356,10,free_residency=True)
        result=optimize(source,1,10,free_residency=True,layout_hint=hint,repair_interval=(1,1))
        self.assertFalse(result['physical_slot_layout']['full_frame_transfer_window_enforced'])
        self.assertEqual(result['physical_slot_layout']['physical_repair_interval'],[1,1])
        self.assertEqual(result['physical_slot_layout']['physical_repair_transfer_interval'],[1,2])
        self.assertEqual(result['physical_slot_layout']['requested_repair_window_master_clocks'],1)
        def states(schedule):
            state={b:[None]*15 for b in range(8)};rows=[]
            for row in schedule['trace']:
                for event in row['updates']:state[event['bank']][event['slot']-1]=event['color']
                rows.append({b:values.copy()for b,values in state.items()})
            return rows
        a,b=states(hint),states(result)
        self.assertTrue(all(a[y]==b[y]for y in range(len(a))if y!=1))
        _,_,before=demand(source);_,_,after=demand(result)
        self.assertTrue(all(np.array_equal(a,b)for a,b in zip(before,after)))
        with self.assertRaisesRegex(ValueError,'ROW_SLOT_REPAIR_DOMAIN'):
            optimize(source,356,10,repair_interval=(1,1))

    def test_invalid_transfer_domain_is_explicit(self):
        with self.assertRaisesRegex(ValueError,'ROW_SLOT_PERMUTATION_DOMAIN'):
            optimize(fixtures.SlotLayoutTests().schedule(),0,10)

    def test_fixed_resident_multisets_preserve_every_source_pixel(self):
        source=fixtures.SlotLayoutTests().schedule()
        result=optimize(source,356,10)
        self.assertTrue(result['physical_slot_layout']['fixed_resident_sets'])
        _,_,before=demand(source);_,_,after=demand(result)
        self.assertTrue(all(np.array_equal(a,b)for a,b in zip(before,after)))


if __name__=='__main__':unittest.main()
