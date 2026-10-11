import hashlib,importlib.util,json,unittest
import numpy as np
from raster_row_slot_permutations import optimize
from raster_slot_greedy import demand
import test_raster_slot_layout as fixtures


@unittest.skipUnless(importlib.util.find_spec('ortools'),'optional OR-Tools backend')
class RowSlotPermutationTests(unittest.TestCase):
    def test_full_middle_bank_can_bridge_three_banks_at_native_boundary(self):
        import copy
        from raster_slot_refine import verify_packets
        source=fixtures.SlotLayoutTests().schedule();source['pieces']=[];source['piece_pixel_masks']=[]
        for x,bank,slots in((0,0,[15]),(8,1,list(range(1,9))),(16,1,list(range(9,16))),(24,2,list(range(1,5)))):
            image=np.zeros((8,8),dtype=np.uint8);image[:2,:len(slots)]=slots;flat=image.flatten()
            source['pieces'].append(dict(x=x,y=0,width=8,height=8,bank=bank))
            source['piece_pixel_masks'].append(dict(width=8,height=8,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
        state={b:[None]*15 for b in range(8)};trace=[]
        for y in range(16):
            before=copy.deepcopy(state);target=copy.deepcopy(state);events=[]
            if y==0:target={b:[0]*15 for b in range(8)}
            if y<2:
                target[0][14]=101+300*y;target[1]=list(range(201+300*y,216+300*y));target[2][:4]=list(range(301+300*y,305+300*y))
            for b in range(8):
                for s,c in enumerate(target[b]):
                    if c!=state[b][s]:events.append(dict(bank=b,slot=s+1,old=state[b][s],color=c))
            state=target;trace.append(dict(scanline=y,resident_before=before,updates=events))
        source['trace']=trace
        expected=np.zeros((16,256),dtype=np.uint16)
        for p,words in zip(source['pieces'],demand(source)[2]):
            for y,x in zip(*np.where(words>=0)):expected[p['y']+y,p['x']+x]=words[y,x]
        source['source_rgb555_sha256']=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()
        # One range covers twenty dirty opaque words and two transparent words.
        # raw cost=22*16+24=376, prepared span=336. The old 20/active-bank
        # shortcut would demand 380 and incorrectly exclude this valid case.
        result=optimize(source,337,5,necessary_bank_window=337,range_encoding='coverage',maximum_writes=20)
        verify_packets(result)
        self.assertEqual(result['peak_scheduled_writes'],20)
        self.assertLessEqual(result['physical_slot_layout']['peak_prepared_commit_span'],336)
        self.assertTrue(all(np.array_equal(a,b)for a,b in zip(demand(source)[2],demand(result)[2])))
        failed=optimize(source,336,5,necessary_bank_window=336,range_encoding='coverage',maximum_writes=20)
        self.assertEqual(failed['solver_status'],'INFEASIBLE')

    def test_dense_bank_rows_match_fifteen_words_and_preserve_opaque_zero(self):
        import copy
        from raster_slot_refine import verify_packets
        source=fixtures.SlotLayoutTests().schedule()
        piece=dict(source['pieces'][0],width=16,height=16)
        image=np.zeros((16,16),dtype=np.uint8);image[:2,:15]=np.arange(1,16,dtype=np.uint8)
        flat=image.flatten();source['pieces']=[piece]
        source['piece_pixel_masks']=[dict(width=16,height=16,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex())]
        state={b:[None]*15 for b in range(8)};trace=[]
        for y in range(16):
            before=copy.deepcopy(state);events=[]
            if y<2:
                for slot in range(15):
                    color=15*y+slot;events.append(dict(bank=0,slot=slot+1,old=state[0][slot],color=color));state[0][slot]=color
            trace.append(dict(scanline=y,resident_before=before,updates=events))
        source['trace']=trace
        result=optimize(source,225,5,free_residency=True,maximum_writes=15,range_encoding='coverage')
        verify_packets(result)
        self.assertEqual(result['physical_slot_layout']['peak_prepared_commit_span'],224)
        self.assertTrue(result['physical_slot_layout']['distinct_required_word_slot_matching_enforced'])
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        self.assertEqual(demand(result)[2][0][0,0],0)
        rejected=optimize(source,224,5,free_residency=True,maximum_writes=15,range_encoding='coverage')
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')

    def test_necessary_bank_window_charges_all_physical_changes(self):
        from test_raster_slot_greedy import source_schedule
        from raster_bank_residency import favorable_span
        source=source_schedule()
        failed=optimize(source,1001,5,free_residency=True,necessary_bank_window=32,range_encoding='coverage')
        self.assertEqual(failed['solver_status'],'INFEASIBLE')
        result=optimize(source,1001,5,free_residency=True,necessary_bank_window=33,range_encoding='coverage')
        self.assertTrue(result['physical_slot_layout']['pixel_color_identity_verified'])
        self.assertEqual(result['physical_slot_layout']['necessary_bank_window_master_clocks'],33)
        self.assertTrue(all(favorable_span(r['updates'])<33 for r in result['trace'][1:]))
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        with self.assertRaisesRegex(ValueError,'ROW_SLOT_NECESSARY_BANK_WINDOW'):optimize({},necessary_bank_window=0)

    def test_write_cap_counts_physical_changes_but_allows_initial_prefill(self):
        source=fixtures.SlotLayoutTests().schedule()
        result=optimize(source,356,10,free_residency=True,maximum_writes=0)
        self.assertEqual(result['peak_scheduled_writes'],0)
        self.assertTrue(result['physical_slot_layout']['full_frame_write_budget_enforced'])
        self.assertTrue(result['physical_slot_layout']['pixel_color_identity_verified'])
        with self.assertRaisesRegex(ValueError,'WRITE_BUDGET_DOMAIN'):
            optimize(source,maximum_writes=-1)

    def test_verified_physical_hint_can_be_fixed_without_hint_contradictions(self):
        from ortools.sat.python import cp_model
        from unittest.mock import patch
        constructor=cp_model.CpSolver
        def fixed_hint_solver():
            solver=constructor()
            solver.parameters.fix_variables_to_their_hinted_value=True
            return solver
        for free in(False,True):
            source=fixtures.SlotLayoutTests().schedule()
            hint=optimize(source,356,10,free_residency=free)
            with patch.object(cp_model,'CpSolver',fixed_hint_solver):
                result=optimize(source,356,10,free_residency=free,layout_hint=hint)
            self.assertTrue(result['physical_slot_layout']['all_packet_cgram_identities_verified'])

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
        self.assertLessEqual(result['physical_slot_layout']['peak_commit_span_lower_bound_for_this_restricted_model'],result['physical_slot_layout']['peak_prepared_commit_span'])
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
        with self.assertRaisesRegex(ValueError,'ROW_SLOT_SEARCH_STRATEGY'):
            optimize(fixtures.SlotLayoutTests().schedule(),search_strategy='unknown')

    def test_lns_hint_retains_exact_source_and_no_native_claim(self):
        source=fixtures.SlotLayoutTests().schedule()
        hint=optimize(source,356,10,True)
        result=optimize(source,356,2,True,hint,search_strategy='lns')
        self.assertEqual(result['physical_slot_layout']['solver_search_strategy'],'lns')
        self.assertFalse(result['physical_slot_layout']['native_timing_admitted'])
        self.assertTrue(all(np.array_equal(a,b)for a,b in zip(demand(source)[2],demand(result)[2])))

    def test_fixed_address_coverage_preserves_source_and_local_exit_transfer(self):
        source=fixtures.SlotLayoutTests().schedule()
        hint=optimize(source,356,10,True)
        result=optimize(source,356,10,True,hint,(1,1),range_encoding='coverage')
        self.assertEqual(result['physical_slot_layout']['physical_range_encoding'],'coverage')
        self.assertEqual(result['physical_slot_layout']['physical_repair_transfer_interval'],[1,2])
        self.assertTrue(all(np.array_equal(a,b)for a,b in zip(demand(source)[2],demand(result)[2])))

    def test_persistent_word_indices_keep_compiled_indices_constant(self):
        from raster_constant_index_template import construct
        from raster_obj_compact import unpack
        source=fixtures.SlotLayoutTests().schedule();hint=construct(source,5)
        result=optimize(hint,356,5,True,hint,range_encoding='coverage',persistent_word_indices=True)
        indices={}
        for p,m,words in zip(result['pieces'],result['piece_pixel_masks'],demand(result)[2]):
            image=unpack(m)
            for y,x in zip(*np.where(image)):
                key=p['bank'],int(words[y,x]);s=int(image[y,x]);self.assertEqual(indices.setdefault(key,s),s)
        self.assertTrue(result['physical_slot_layout']['persistent_word_index_family_only'])
        self.assertFalse(result['physical_slot_layout']['native_timing_admitted'])

    def test_fixed_resident_multisets_preserve_every_source_pixel(self):
        source=fixtures.SlotLayoutTests().schedule()
        result=optimize(source,356,10)
        self.assertTrue(result['physical_slot_layout']['fixed_resident_sets'])
        _,_,before=demand(source);_,_,after=demand(result)
        self.assertTrue(all(np.array_equal(a,b)for a,b in zip(before,after)))


if __name__=='__main__':unittest.main()
