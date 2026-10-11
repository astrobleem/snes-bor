import unittest
from raster_global_bank_classes import assign_masks,permutation_bound,fixed_slot_schedule,persistent_index_bound
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
