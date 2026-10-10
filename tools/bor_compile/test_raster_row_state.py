import unittest
from raster_row_state import optimize
from raster_obj_compact import unpack
from test_raster_slot_greedy import source_schedule


class RowStateTests(unittest.TestCase):
    def test_reload_black_and_independent_pixel_replay(self):
        source=source_schedule()
        result=optimize(source,lookahead=0,time_limit=15)
        self.assertEqual(result['pieces'],source['pieces'])
        self.assertTrue(result['physical_slot_layout']['all_packet_cgram_identities_verified'])
        self.assertEqual(result['physical_slot_layout']['maximum_noninitial_prefetch_latency_lines'],0)
        state={b:[None]*15 for b in range(8)};states=[]
        for row in result['trace']:
            for e in row['updates']:
                self.assertEqual(state[e['bank']][e['slot']-1],e['old'])
                state[e['bank']][e['slot']-1]=e['color']
            states.append({b:list(v) for b,v in state.items()})
        for p,mask in zip(result['pieces'],result['piece_pixel_masks']):
            image=unpack(mask)
            for y in range(16):
                for x in range(16):
                    if x==15:self.assertEqual(image[y,x],0);continue
                    self.assertNotEqual(image[y,x],0)
                    expected=x if y<7 or y>=12 else 15
                    self.assertEqual(states[y][p['bank']][int(image[y,x])-1],expected)
        self.assertFalse(result['physical_slot_layout']['native_timing_admitted'])

    def test_small_window_is_family_failure_not_raster_rejection(self):
        source=source_schedule();source['trace']=source['trace'][:2]
        source['trace'][1]['updates']=[dict(bank=b,slot=s+1,old=s,color=15+s) for b in (0,1) for s in range(15)]
        for p,mask in zip(source['pieces'],source['piece_pixel_masks']):
            p['height']=2;image=unpack(mask)[:2];flat=image.flatten()
            mask.update(height=2,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex())
        result=optimize(source,window=17,lookahead=0,time_limit=15)
        self.assertEqual(result['solver_status'],'INFEASIBLE')
        self.assertFalse(result['universal_raster_rejected'])

    def test_invalid_domain_and_mask_rejected(self):
        with self.assertRaisesRegex(ValueError,'ROW_STATE_DOMAIN'):
            optimize(source_schedule(),lookahead=-1)
        source=source_schedule();source['piece_pixel_masks'].pop()
        with self.assertRaisesRegex(ValueError,'PIECE_MASK_COUNT'):optimize(source)

    def test_fixed_initial_layout_retains_exact_source_preload(self):
        source=source_schedule();result=optimize(source,lookahead=0,time_limit=10,fixed_initial_slots=True)
        self.assertTrue(result['physical_slot_layout']['fixed_initial_slots'])
        self.assertEqual(result['trace'][0]['updates'],[dict(e,kind='required') for e in source['trace'][0]['updates']])
        self.assertTrue(result['physical_slot_layout']['pixel_color_identity_verified'])

    def test_fixed_initial_bank_can_prefetch_before_first_visible_row(self):
        source=source_schedule();source['trace']=source['trace'][:3]
        source['trace'][2]['updates']=[dict(bank=0,slot=s+1,old=s,color=15+s) for s in range(15)]
        source['pieces']=source['pieces'][:1];source['piece_pixel_masks']=source['piece_pixel_masks'][:1]
        p=source['pieces'][0];mask=source['piece_pixel_masks'][0];p['height']=3
        image=unpack(mask)[:3];image[:2]=0;flat=image.flatten()
        mask.update(height=3,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex())
        result=optimize(source,window=200,lookahead=1,time_limit=15,fixed_initial_slots=True)
        self.assertTrue(result['physical_slot_layout']['pixel_color_identity_verified'])
        self.assertGreater(result['trace'][1]['colors_written'],0)
        self.assertEqual(sum(r['colors_written'] for r in result['trace'][1:]),15)
        self.assertLess(result['physical_slot_layout']['peak_prepared_commit_span'],200)


if __name__=='__main__':unittest.main()
