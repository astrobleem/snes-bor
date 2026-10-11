import unittest
from raster_global_bank_classes import assign_masks,permutation_bound,fixed_slot_schedule,persistent_index_bound
from test_raster_slot_greedy import source_schedule


class GlobalBankClassTests(unittest.TestCase):
    def test_sat_strategy_preserves_transfer_witness(self):
        pieces=[dict(x=0,y=0,width=8,height=8,
                     rows={y:list(range(y*8,y*8+8))for y in range(8)},allowed_banks=[0])]
        result=assign_masks(pieces,time_limit=5,prepared_dma_window=97,
                            write_budget=7,search_strategy='sat')
        self.assertEqual(result['status'],'JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN')
        self.assertTrue(result['aggregate_transfer_intervals_and_partitions_replayed'])
        self.assertEqual(result['aggregate_transfer_span'],96)
        self.assertFalse(result['physical_transfer_admitted'])
        with self.assertRaisesRegex(ValueError,'SEARCH_STRATEGY'):
            assign_masks(pieces,search_strategy='unknown')

    def test_epoch_transfer_unions_count_repeated_identity_once(self):
        # Sixteen identities repeat across two epochs, not thirty-two colors.
        pieces=[dict(x=0,y=0,width=8,height=8,rows={y:list(range(8*(y%2),8*(y%2)+8))for y in range(4)},allowed_banks=[0])]
        result=assign_masks(pieces,time_limit=5,prepared_dma_window=1,write_budget=1,word_epoch_lines=2,word_bank_hint={c:0 for c in range(16)})
        self.assertEqual(result['status'],'JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN')
        self.assertEqual(result['aggregate_transfer_span'],0)
        self.assertTrue(result['aggregate_transfer_intervals_and_partitions_replayed'])
        self.assertFalse(result['global_word_bank_identity_restricted'])
        self.assertEqual(result['word_epoch_lines'],2)
        self.assertFalse(result['physical_transfer_admitted'])
        with self.assertRaisesRegex(ValueError,'EPOCH_POLICY'):assign_masks(pieces,word_epoch_lines=2,persistent_word_indices=True)

    def test_rebuilt_masks_preserve_pixels_and_reject_wrong_ownership(self):
        import copy
        from raster_global_bank_classes import rebuild_schedule
        from raster_slot_greedy import demand
        source=source_schedule()
        for p in source['pieces']:p.update(actor=0,local_x=p['x'],local_y=p['y'])
        pieces=[dict(p,allowed_banks=list(range(4)),rows={p['y']+y:sorted({int(c)for c in row if c>=0})for y,row in enumerate(image)if any(c>=0 for c in row)})for p,image in zip(source['pieces'],demand(source)[2])]
        search=assign_masks(pieces,time_limit=5,maximum_oam_entries=128)
        rebuilt=rebuild_schedule(source,search)
        def pixels(frame):
            return {(p['actor'],p['y']+y,p['x']+x):int(c)for p,image in zip(frame['pieces'],demand(frame)[2])for y,row in enumerate(image)for x,c in enumerate(row)if c>=0}
        self.assertEqual(pixels(source),pixels(rebuilt))
        bad=copy.deepcopy(search);bad['assignment'][0]=4
        with self.assertRaisesRegex(ValueError,'BANK_ELIGIBILITY'):rebuild_schedule(source,bad)
        bad=copy.deepcopy(search);bad['pieces'][0]['x']+=1
        with self.assertRaisesRegex(ValueError,'GEOMETRY'):rebuild_schedule(source,bad)

    def test_aggregate_transfer_bound_replays_and_is_not_residency_admission(self):
        pieces=[dict(x=0,y=0,width=8,height=8,rows={y:list(range(y*8,y*8+8))for y in range(8)},allowed_banks=[0])]
        rejected=assign_masks(pieces,time_limit=5,prepared_dma_window=97,write_budget=6)
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        admitted=assign_masks(pieces,time_limit=5,prepared_dma_window=97,write_budget=7)
        self.assertEqual(admitted['status'],'JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN')
        self.assertEqual(admitted['aggregate_transfer_span'],96)
        self.assertTrue(admitted['aggregate_transfer_intervals_and_partitions_replayed'])
        self.assertTrue(admitted['palette_residency_and_physical_slots_relaxed'])
        self.assertFalse(admitted['physical_transfer_admitted'])
        disjoint=assign_masks(pieces+[dict(pieces[0],allowed_banks=[1])],
                              time_limit=5,prepared_dma_window=337)
        self.assertEqual(disjoint['status'],'JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN')
        self.assertTrue(disjoint['aggregate_transfer_intervals_and_partitions_replayed'])
        self.assertFalse(disjoint['physical_transfer_admitted'])
        with self.assertRaisesRegex(ValueError,'OVERLAPPING_DOMAINS'):
            assign_masks(pieces+[dict(pieces[0],allowed_banks=[0,1])],prepared_dma_window=337)

    def test_explicit_oam_ceiling_counts_split_masks(self):
        pieces=[dict(x=(i%8)*16,y=(i//8)*16,width=16,height=16,rows={(i//8)*16:list(range(16))},allowed_banks=[0,1])for i in range(17)]
        rejected=assign_masks(pieces,time_limit=5,maximum_oam_entries=33)
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        admitted=assign_masks(pieces,time_limit=5,maximum_oam_entries=34)
        self.assertEqual(admitted['oam_entries'],34)
        self.assertEqual(admitted['peak_tile_slivers'],32)
        self.assertEqual(admitted['peak_sprites'],16)
        with self.assertRaisesRegex(ValueError,'OAM_DOMAIN'):assign_masks(pieces,maximum_oam_entries=129)

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

    def test_subscreen_permutation_bound_uses_all_eight_banks(self):
        source=source_schedule();source['color_math']='subscreen-additive'
        report=permutation_bound(source)
        self.assertEqual(report['legal_permutations_checked'],40320)
        self.assertEqual(report['minimum_peak_favorable_span'],32)
        self.assertFalse(report['native_timing_admitted'])

    def test_fixed_word_index_template_reuses_slots_only_on_exact_rows(self):
        pieces=[dict(x=0,y=0,width=8,height=8,rows={0:[0],3:[2]},allowed_banks=[0])]
        indices=[dict(allowed_banks=[0],color=c,obj_palette_word_offset=1)for c in(0,2)]
        trace,states=fixed_slot_schedule(pieces,[0],indices,8)
        self.assertEqual(states[0][0][0],0)
        self.assertEqual(states[2][0][0],0)
        self.assertEqual(states[3][0][0],2)
        self.assertEqual([r['colors_written']for r in trace],[1,0,0,1,0,0,0,0])
        self.assertEqual(trace[3]['updates'][0]['old'],0)
        self.assertEqual(trace[3]['updates'][0]['slot'],1)
        conflict=[dict(pieces[0],rows={0:[0,2]})]
        with self.assertRaisesRegex(AssertionError,'ROW_CONFLICT'):fixed_slot_schedule(conflict,[0],indices,8)

    def test_joint_word_indices_preserve_opaque_zero_and_bank_selection(self):
        pieces=[dict(x=0,y=0,width=8,height=8,rows={0:list(range(15)),2:[15]},allowed_banks=[0])]
        result=assign_masks(pieces,time_limit=5,residency_window_lines=2,persistent_word_indices=True)
        self.assertEqual(result['status'],'JOINT_GLOBAL_BANK_MASK_WORD_IDENTITIES_PROVEN')
        self.assertTrue(result['persistent_word_indices'])
        indices=result['word_slot_indices']
        self.assertEqual(len(indices),16)
        self.assertTrue(all(1<=v['obj_palette_word_offset']<=15 for v in indices))
        trace,states=fixed_slot_schedule(result['pieces'],result['assignment'],indices,8)
        self.assertEqual(set(c for c in states[0][0]if c is not None),set(range(15)))
        self.assertIn(15,states[2][0])
        self.assertEqual(trace[2]['colors_written'],1)

    def test_constant_word_indices_can_fail_without_row_bank_overflow(self):
        import copy,numpy as np
        source=source_schedule();source['pieces']=source['pieces'][:1]
        image=np.zeros((16,16),dtype=np.uint8);image[0,:15]=np.arange(1,16)
        for y in range(1,15):image[y,0]=y;image[y,1]=15
        image[15,:2]=[2,15]
        flat=image.flatten();source['piece_pixel_masks']=[dict(width=16,height=16,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex())]
        state={b:[None]*15 for b in range(8)};trace=[]
        for y in range(16):
            before=copy.deepcopy(state);events=[]
            edits=list(enumerate(range(15),1))if y==0 else[(15,15)]if y==1 else[(2,14)]if y==15 else[]
            for slot,c in edits:
                events.append(dict(bank=0,slot=slot,old=state[0][slot-1],color=c));state[0][slot-1]=c
            trace.append(dict(scanline=y,resident_before=before,updates=events))
        source['trace']=trace
        rejected=persistent_index_bound(source,15,5)
        self.assertTrue(rejected['fixed_word_indices_rejected'])
        self.assertFalse(rejected['universal_raster_rejected'])
        admitted=persistent_index_bound(source,16,5)
        self.assertFalse(admitted['fixed_word_indices_rejected'])
        self.assertEqual(admitted['banks'][0]['status'],'OPTIMAL')


if __name__=='__main__':unittest.main()
