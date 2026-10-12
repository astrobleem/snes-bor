import unittest
from raster_piece_bank_cache import optimize
from raster_slot_greedy import demand


class PieceBankCacheTests(unittest.TestCase):
    def test_class_interval_pressure_counts_unique_source_words(self):
        import copy
        state={b:[None]*15 for b in range(8)};trace=[]
        for y in range(8):
            before=copy.deepcopy(state);updates=[]
            for slot in range(8):
                word=8*y+slot
                updates.append(dict(bank=0,slot=slot+1,old=state[0][slot],color=word))
                state[0][slot]=word
            trace.append(dict(scanline=y,resident_before=before,updates=updates))
        source=dict(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',compiled_pixel_identity_verified=True,
            pieces=[dict(actor=0,x=0,y=0,local_x=0,local_y=0,width=8,height=8,bank=0)],
            piece_pixel_masks=[dict(width=8,height=8,pixels_hex='21436587'*8)],trace=trace)
        blocked=optimize(source,time_limit=5,write_budget=0,window=1000,lookahead=8,
            allow_word_masks=True,row_word_masks=True,maximum_masks_per_piece=4)
        self.assertEqual(blocked['solver_status'],'INFEASIBLE')
        self.assertGreater(blocked['compulsory_eligibility_class_interval_cuts'],0)
        self.assertTrue(blocked['eligibility_class_cuts_are_necessary_only'])
        admitted=optimize(source,time_limit=5,write_budget=8,window=1000,lookahead=8,
            allow_word_masks=True,row_word_masks=True,maximum_masks_per_piece=4)
        def pixels(frame):return {(p['y']+y,p['x']+x):int(c)for p,image in zip(frame['pieces'],demand(frame)[2])for y,row in enumerate(image)for x,c in enumerate(row)if c>=0}
        self.assertEqual(pixels(source),pixels(admitted))
        self.assertFalse(admitted['piece_bank_cache']['native_timing_admitted'])

    def test_concurrent_reservation_counts_padding_without_palette_admission(self):
        source=self.fixture();height=len(source['trace'])
        reservation=dict(oam_entries=126,sprites_per_line=[30]*height,tile_slivers_per_line=[30]*height)
        source['geometry_reservation']=reservation
        r=optimize(source,time_limit=5,write_budget=2,window=1000,lookahead=0)
        self.assertEqual(r['combined_reserved_geometry'],dict(oam_entries=128,peak_sprites=32,peak_tile_slivers=34))
        self.assertFalse(r['reservation_palette_and_layer_demand_included'])
        reservation['tile_slivers_per_line'][0]=31
        self.assertEqual(optimize(source,time_limit=5,write_budget=2,window=1000,lookahead=0)['solver_status'],'INFEASIBLE')
        reservation['oam_entries']=True
        with self.assertRaisesRegex(ValueError,'GEOMETRY_RESERVATION'):optimize(source,time_limit=5)

    def test_row_masks_keep_fixed_oam_banks_and_exact_source_pixels(self):
        source=self.fixture()
        result=optimize(source,time_limit=5,write_budget=0,window=9999,lookahead=0,allow_word_masks=True,row_word_masks=True,maximum_oam=4)
        def pixels(frame):return{(p['actor'],p['y']+y,p['x']+x):int(c)for p,image in zip(frame['pieces'],demand(frame)[2])for y,row in enumerate(image)for x,c in enumerate(row)if c>=0}
        self.assertEqual(pixels(source),pixels(result))
        self.assertEqual(result['peak_scheduled_writes'],0)
        self.assertEqual(result['piece_bank_cache']['word_bank_selection_scope'],'piece row')
        self.assertTrue(result['piece_bank_cache']['fixed_bank_per_compiled_oam_entry'])
        self.assertTrue(result['piece_bank_cache']['interchangeable_bank_first_piece_order'])
        self.assertLessEqual(result['geometry']['oam_entries'],4)
        rejected=optimize(source,time_limit=5,write_budget=0,window=1000,lookahead=0,allow_word_masks=True,row_word_masks=True,maximum_oam=2)
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        with self.assertRaisesRegex(ValueError,'ROW_MASKS_REQUIRE'):
            optimize(source,row_word_masks=True)

    def test_lossless_word_masks_preload_sixteenth_word_with_hardware_geometry(self):
        source=self.fixture()
        blocked=optimize(source,time_limit=5,write_budget=0,window=1000,lookahead=0,allow_word_masks=True,maximum_oam=2)
        self.assertEqual(blocked['solver_status'],'INFEASIBLE')
        result=optimize(source,time_limit=5,write_budget=0,window=1000,lookahead=0,allow_word_masks=True,maximum_oam=4)
        self.assertEqual(result['peak_scheduled_writes'],0)
        self.assertEqual(result['geometry']['oam_entries'],4)
        self.assertTrue(result['piece_bank_cache']['source_pixel_exact_word_masks_allowed'])
        def pixels(frame):return{(p['actor'],p['y']+y,p['x']+x):int(c)for p,image in zip(frame['pieces'],demand(frame)[2])for y,row in enumerate(image)for x,c in enumerate(row)if c>=0}
        self.assertEqual(pixels(source),pixels(result))
        self.assertFalse(result['piece_bank_cache']['physical_transfer_admitted'])

    def test_split_assignment_hint_preserves_pixels_without_fixing_choices(self):
        from raster_piece_bank_cache import validated_assignment_hints
        source=self.fixture()
        hint=optimize(source,time_limit=5,write_budget=0,window=1000,lookahead=0,allow_word_masks=True,row_word_masks=True,maximum_oam=4)
        choices=validated_assignment_hints(source,hint,demand(source)[2],{i:tuple(range(4))for i in range(2)},True,True)
        self.assertGreater(len(choices),0)
        result=optimize(source,time_limit=5,write_budget=0,window=1000,lookahead=0,allow_word_masks=True,row_word_masks=True,maximum_oam=4,assignment_hint=hint,search_strategy='sat-repair')
        self.assertTrue(result['piece_bank_cache']['validated_assignment_hint_used'])
        self.assertTrue(result['piece_bank_cache']['bank_choice_hints_are_soft'])
        self.assertEqual(result['peak_scheduled_writes'],0)
        # A hint admitting four objects cannot make the two-object model pass.
        blocked=optimize(source,time_limit=5,write_budget=0,window=1000,lookahead=0,allow_word_masks=True,row_word_masks=True,maximum_oam=2,assignment_hint=hint,search_strategy='sat-repair')
        self.assertEqual(blocked['solver_status'],'INFEASIBLE')

    def test_assignment_hints_reject_source_or_bank_identity_changes(self):
        import copy
        from raster_piece_bank_cache import validated_assignment_hints
        source=self.fixture();images=demand(source)[2];domains={i:tuple(range(4))for i in range(2)}
        bad=copy.deepcopy(source);bad['source_rgb555_sha256']='different'
        with self.assertRaisesRegex(ValueError,'HINT_SOURCE_IDENTITY'):
            validated_assignment_hints(source,bad,images,domains,True,True)
        bad=copy.deepcopy(source);bad['pieces'][0]['x']+=1
        with self.assertRaisesRegex(ValueError,'HINT_PIXEL_IDENTITY'):
            validated_assignment_hints(source,bad,images,domains,True,True)
        with self.assertRaisesRegex(ValueError,'HINT_BANK_ELIGIBILITY'):
            validated_assignment_hints(source,source,images,{i:(7,)for i in range(2)},True,True)

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
