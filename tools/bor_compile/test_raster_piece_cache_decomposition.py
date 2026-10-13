import copy,unittest
import numpy as np
import test_raster_word_bank_balance as fixtures
from raster_slot_greedy import demand
from raster_piece_cache_decomposition import search,nonpositive_solver_dual
from raster_bank_residency import relaxed_bound
from test_raster_mask_rectangle_cover import fixture as mask_fixture


class DecompositionTests(unittest.TestCase):
    def test_wrapped_padding_and_clipped_slivers_use_actual_hardware_rows(self):
        source=mask_fixture();piece=source['pieces'][0]
        piece.update(x=248,y=220,local_x=0,local_y=0,width=64,height=64)
        image=np.zeros((64,64),dtype=np.uint8);image[0,7]=1;flat=image.flatten()
        source['pieces']=[piece];source['piece_pixel_masks']=[dict(width=64,height=64,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex())]
        state=source['trace'][-1]['resident_before']
        source['trace'] += [dict(scanline=y,resident_before=copy.deepcopy(state),updates=[])for y in range(16,224)]
        reservation=dict(oam_entries=0,sprites_per_line=[0]*224,tile_slivers_per_line=[0]*224)
        reservation['sprites_per_line'][0]=32
        blocked=search(source,iterations=1,time_limit=5,row_word_masks=True,geometry_reservation=reservation)
        self.assertIsNone(blocked['best_fractional_cache_bound'])
        self.assertFalse(blocked['iterations'][0]['reserved_geometry_admitted'])
        reservation['sprites_per_line'][0]=0;reservation['tile_slivers_per_line'][220]=33
        admitted=search(source,iterations=1,time_limit=5,row_word_masks=True,geometry_reservation=reservation)
        self.assertEqual(admitted['geometry']['peak_tile_slivers'],1)
        self.assertEqual(admitted['combined_reserved_geometry']['peak_tile_slivers'],34)
        self.assertEqual(admitted['geometry_reservation'],reservation)
        self.assertFalse(admitted['reservation_palette_and_layer_demand_included'])

    def test_repaired_master_keeps_source_identity_and_admission_scope(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        result=search(source,iterations=2,time_limit=10,master_seconds=2,
            master_search_strategy='sat-repair')
        report=result.get('piece_cache_decomposition',result)
        self.assertEqual(report['master_search_strategy'],'sat-repair')
        self.assertTrue(report['master_hints_are_soft'])
        self.assertFalse(report['native_timing_admitted'])
        self.assertFalse(report['universal_raster_rejected'])
        self.assertIn('master_branches',report['iterations'][0])
        if 'trace'in result:
            self.assertEqual([sorted(set(image[image>=0]))for image in demand(source)[2]],
                             [sorted(set(image[image>=0]))for image in demand(result)[2]])
        with self.assertRaisesRegex(ValueError,'MASTER_SEARCH_STRATEGY'):
            search(source,master_search_strategy='unsupported')

    def test_fresh_dual_sign_noise_is_clipped_without_accepting_invalid_certificates(self):
        np.testing.assert_array_equal(nonpositive_solver_dual([-1.,0.,1e-14]),[-1.,0.,0.])
        for bad in ([1e-6],[float('nan')],[[0.]]):
            with self.assertRaisesRegex(ValueError,'FRESH_DUAL_SIGN'):
                nonpositive_solver_dual(bad)

    def test_seed_outside_allowed_banks_is_rejected(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        source['pieces'][0]['allowed_banks']=[b for b in range(8)if b!=source['pieces'][0]['bank']]
        with self.assertRaisesRegex(ValueError,'SEED_BANK_ELIGIBILITY'):
            search(source)

    def test_other_actor_geometry_reservation_is_enforced(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        height=len(source['trace'])
        reserved=dict(oam_entries=128,sprites_per_line=[0]*height,tile_slivers_per_line=[0]*height)
        result=search(source,iterations=2,time_limit=10,master_seconds=1,row_word_masks=True,
                      geometry_reservation=reserved)
        self.assertIsNone(result['best_fractional_cache_bound'])
        self.assertFalse(result['iterations'][0]['reserved_geometry_admitted'])
        self.assertEqual(result['iterations'][0]['master_status'],'INFEASIBLE')
        for field,limit in [('sprites_per_line',32),('tile_slivers_per_line',34)]:
            full=dict(oam_entries=0,sprites_per_line=[0]*height,tile_slivers_per_line=[0]*height)
            full[field]=[limit]*height
            blocked=search(source,iterations=2,time_limit=10,master_seconds=1,
                           row_word_masks=True,geometry_reservation=full)
            self.assertIsNone(blocked['best_fractional_cache_bound'])
            self.assertEqual(blocked['iterations'][0]['master_status'],'INFEASIBLE')
        reserved['oam_entries']=1
        result=search(source,iterations=2,time_limit=10,master_seconds=1,row_word_masks=True,
                      geometry_reservation=reserved)
        self.assertLessEqual(result['geometry']['oam_entries']+1,128)
        self.assertFalse(result['piece_cache_decomposition']['reservation_proves_concurrent_palette_or_layer_admission'])
        for bad in ({},dict(reserved,oam_entries=True),dict(reserved,sprites_per_line=[0]),
                    dict(reserved,tile_slivers_per_line=[35]*height)):
            with self.assertRaisesRegex(ValueError,'GEOMETRY_RESERVATION_DOMAIN'):
                search(source,row_word_masks=True,geometry_reservation=bad)
        with self.assertRaisesRegex(ValueError,'GEOMETRY_RESERVATION_DOMAIN'):
            search(source,geometry_reservation=reserved)

    def test_interval_master_bounds_replay_against_cache_lp_and_resume(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        for objective in ('writes','dma-window'):
            before=search(source,iterations=1,time_limit=5,objective_kind=objective)
            result=search(source,iterations=2,time_limit=10,master_seconds=1,
                          objective_kind=objective,interval_cut_span=8,
                          resume_report=before['piece_cache_decomposition'])
            report=result['piece_cache_decomposition']
            self.assertGreater(report['interval_cut_count'],0)
            for iteration in report['iterations']:
                self.assertLessEqual(iteration['independently_replayed_interval_lower_bound'],
                                     iteration['validated_dual_lower_bound']+1e-6)
            for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        for bad in (-1,257,True):
            with self.assertRaisesRegex(ValueError,'INTERVAL_CUT_DOMAIN'):
                search(source,interval_cut_span=bad)

    def test_resume_checks_duals_and_keeps_prior_assignments(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        first=search(source,iterations=2,time_limit=10,master_seconds=1)
        saved=first['piece_cache_decomposition']
        resumed=search(source,iterations=2,time_limit=10,master_seconds=1,resume_report=saved)
        report=resumed['piece_cache_decomposition']
        self.assertEqual(report['restored_certified_cuts'],len(saved['certified_master_cuts']))
        self.assertTrue(set(map(tuple,saved['evaluated_assignments']))<=set(map(tuple,report['evaluated_assignments'])))
        for a,b in zip(demand(source)[2],demand(resumed)[2]):np.testing.assert_array_equal(a,b)
        bad=copy.deepcopy(saved);bad['cache_basis_sha256']='stale'
        with self.assertRaisesRegex(ValueError,'SOURCE_BASIS'):
            search(source,resume_report=bad)
        bad=copy.deepcopy(saved);bad['certified_master_cuts'][0]['inequality_dual']=[[0,1.]]
        with self.assertRaisesRegex(ValueError,'DUAL_DOMAIN'):
            search(source,resume_report=bad)
        bad=copy.deepcopy(saved);bad['certified_master_cuts'][0]['inequality_dual']=[[0,-100.]]
        with self.assertRaisesRegex(ValueError,'DUAL_STATIONARITY'):
            search(source,resume_report=bad)
        bad=copy.deepcopy(saved);bad['certified_master_cuts'][0]['upper_dual']=[[saved['cache_lp_variables']-1,-1.]]
        with self.assertRaisesRegex(ValueError,'UNBOUNDED_PEAK_DUAL'):
            search(source,resume_report=bad)
        bad=copy.deepcopy(saved);bad['certified_master_cuts'][0]['upper_dual']=[[0,-100.]]
        # A nonpositive bound multiplier alone is valid but weak, so accepts.
        search(source,iterations=1,time_limit=5,resume_report=bad)
        bad=copy.deepcopy(saved);bad['evaluated_assignments'][0][0]=8
        with self.assertRaisesRegex(ValueError,'ASSIGNMENT_DOMAIN'):
            search(source,resume_report=bad)

    def test_dual_cuts_and_rebuilt_operands(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        result=search(source,iterations=4,time_limit=10,master_seconds=1)
        report=result['piece_cache_decomposition']
        self.assertTrue(report['iterations'])
        self.assertLessEqual(report['best_fractional_cache_bound'],1)
        self.assertAlmostEqual(relaxed_bound(result,lookahead=16,time_limit=5)['peak_write_lower_bound'],
                               report['best_fractional_cache_bound'])
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        self.assertFalse(report['physical_transfer_admitted'])

    def test_fixed_domains_do_not_change(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        for p in source['pieces']:p['allowed_banks']=[p['bank']]
        result=search(source,iterations=3,time_limit=10,master_seconds=1)
        self.assertEqual([p['bank']for p in result['pieces']],[p['bank']for p in source['pieces']])

    def test_dma_objective_replays_operands_without_timing_admission(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        result=search(source,iterations=2,time_limit=10,master_seconds=1,
                      objective_kind='dma-window',write_budget=21)
        report=result['piece_cache_decomposition']
        self.assertEqual(report['objective_kind'],'dma-window')
        self.assertEqual(report['write_budget'],21)
        self.assertIsNotNone(report['best_fractional_dma_span_bound'])
        for iteration in report['iterations']:
            self.assertAlmostEqual(iteration['validated_dual_lower_bound'],
                                   iteration['peak_dma_span_lower_bound'])
            self.assertLessEqual(iteration['maximum_primal_violation'],1e-6)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        self.assertFalse(report['physical_transfer_admitted'])
        self.assertFalse(report['native_timing_admitted'])

    def test_invalid_dma_objective_rejected(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        for kwargs in ({'objective_kind':'unknown'},{'write_budget':121},
                       {'write_budget':True}):
            with self.assertRaisesRegex(ValueError,'OBJECTIVE_DOMAIN'):
                search(source,**kwargs)

    def test_row_word_masks_keep_source_pixels_and_full_geometry_limits(self):
        source=fixtures.WordBankBalanceTests().fixture()[0]
        result=search(source,iterations=3,time_limit=10,master_seconds=1,
                      row_word_masks=True)
        def pixels(frame):
            return {(p['actor'],p['x']+x,p['y']+y):int(c)
                    for p,image in zip(frame['pieces'],demand(frame)[2])
                    for y,row in enumerate(image)for x,c in enumerate(row)if c>=0}
        self.assertEqual(pixels(source),pixels(result))
        self.assertTrue(result['piece_cache_decomposition']['row_word_masks'])
        self.assertLessEqual(result['geometry']['oam_entries'],128)
        self.assertLessEqual(result['geometry']['peak_sprites'],32)
        self.assertLessEqual(result['geometry']['peak_tile_slivers'],34)
        self.assertFalse(result['piece_cache_decomposition']['native_timing_admitted'])


if __name__=='__main__':unittest.main()
