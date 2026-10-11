import hashlib,importlib.util,json,unittest
import numpy as np
from raster_row_slot_permutations import optimize
from raster_slot_greedy import demand
import test_raster_slot_layout as fixtures


@unittest.skipUnless(importlib.util.find_spec('ortools'),'optional OR-Tools backend')
class RowSlotPermutationTests(unittest.TestCase):
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
