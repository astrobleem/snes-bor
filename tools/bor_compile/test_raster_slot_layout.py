import copy,hashlib,importlib.util,json,unittest
import numpy as np
from raster_obj_compact import unpack
from raster_slot_layout import optimize


@unittest.skipUnless(importlib.util.find_spec('ortools'),'optional OR-Tools backend')
class SlotLayoutTests(unittest.TestCase):
    def test_hint_empty_rows_preserve_identity_but_real_row_changes_reject(self):
        from raster_slot_greedy import demand
        from raster_slot_refine import verify_packets
        source=self.schedule()
        hint=optimize(source,window=356,time_limit=3,flexible_prefetch=True)
        hint['pieces'][0].setdefault('rows',{})['999']=[]
        result=optimize(source,window=356,time_limit=3,flexible_prefetch=True,layout_hint=hint)
        verify_packets(result)
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)
        hint['pieces'][0]['rows']['999']=[1]
        with self.assertRaisesRegex(ValueError,'HINT_IDENTITY'):
            optimize(source,window=356,time_limit=3,flexible_prefetch=True,layout_hint=hint)

    def test_reordered_banks_preserve_piece_domains_before_transfer_admission(self):
        from raster_slot_greedy import demand
        source=self.schedule();source['pieces'][1]['bank']=3
        for row in source['trace']:
            row['resident_before'][3],row['resident_before'][1]=row['resident_before'][1],row['resident_before'][3]
            for e in row['updates']:
                if e['bank']==1:e['bank']=3
        for p in source['pieces']:p['allowed_banks']=[p['bank']]
        blocked=optimize(source,33,5,reorder_banks=True,split_bank_ranges=True,flexible_prefetch=True,retain_write_times=True)
        self.assertEqual(blocked['solver_status'],'INFEASIBLE')
        result=optimize(source,41,5,reorder_banks=True,split_bank_ranges=True,flexible_prefetch=True,retain_write_times=True)
        self.assertTrue(result['physical_slot_layout']['piece_bank_domains_verified'])
        self.assertTrue(all(p['bank']in p['allowed_banks']for p in result['pieces']))
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)

    def test_fixed_address_coverage_pruning_matches_all_contiguous_partitions(self):
        from itertools import combinations
        from ortools.sat.python import cp_model
        from raster_physical_ranges import constrain_fixed_addresses
        for points in ([17,19],[65,127],[15,17,31,33,63]):
            for limit in(1,2,4):
                costs=[]
                for count in range(1,min(limit,len(points))+1):
                    for cuts in combinations(range(1,len(points)),count-1):
                        edges=(0,*cuts,len(points))
                        costs.append(sum(24+16*(points[edges[j+1]-1]-points[edges[j]]+1)for j in range(count)))
                model=cp_model.CpModel();flags={}
                for address in points:
                    bank,slot=divmod(address,16);flags.setdefault((1,bank),[]).append((15*bank+slot-1,1))
                flags.setdefault((1,0),[]).append((0,0))
                ranges,peak=constrain_fixed_addresses(model,flags,2,limit,4096,packet_hints={1:[(0,127)]})
                model.minimize(peak);solver=cp_model.CpSolver()
                self.assertEqual(solver.solve(model),cp_model.OPTIMAL)
                self.assertEqual(solver.value(peak),min(costs))
                self.assertTrue(all(ranges[1,address]==(0,0,0,0)for address in range(128)if address<min(points)or address>max(points)))

    def test_feasibility_only_keeps_transfer_and_pixel_checks(self):
        from raster_slot_greedy import demand
        from raster_slot_refine import verify_packets
        source=self.schedule()
        result=optimize(source,window=33,time_limit=3,feasibility_only=True)
        verify_packets(result)
        self.assertEqual(result['physical_slot_layout']['solver_objective'],'FEASIBILITY_ONLY')
        self.assertIsNone(result['physical_slot_layout']['restricted_family_peak_span_lower_bound'])
        self.assertLess(result['physical_slot_layout']['peak_prepared_commit_span'],33)
        _,_,a=demand(source);_,_,b=demand(result)
        self.assertTrue(all(np.array_equal(x,y)for x,y in zip(a,b)))
        rejected=optimize(source,window=32,time_limit=3,feasibility_only=True)
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        with self.assertRaisesRegex(ValueError,'FEASIBILITY_DOMAIN'):
            optimize(source,feasibility_only=1)

    def test_lifetime_timing_respects_necessary_bank_window(self):
        from raster_bank_residency import favorable_span
        from raster_slot_refine import verify_packets
        source=self.schedule()
        rejected=optimize(source,window=356,time_limit=3,flexible_prefetch=True,
            retain_write_times=True,split_bank_ranges=True,necessary_bank_window=32)
        self.assertEqual(rejected['solver_status'],'INFEASIBLE')
        accepted=optimize(source,window=356,time_limit=3,flexible_prefetch=True,
            retain_write_times=True,split_bank_ranges=True,necessary_bank_window=33)
        verify_packets(accepted)
        self.assertTrue(all(favorable_span(r['updates'])<33 for r in accepted['trace'][1:]))
        costs=[r['prepared_commit_span']for r in accepted['prepared_dma_packets']]
        self.assertEqual((max(costs),sum(costs)),(32,32))
        self.assertEqual(accepted['physical_slot_layout']['solver_objective'],'PEAK_THEN_TOTAL_TRANSFER_COST')
        self.assertEqual(accepted['physical_slot_layout']['restricted_family_peak_span_lower_bound'],32)
        self.assertEqual(accepted['physical_slot_layout']['necessary_bank_window_master_clocks'],33)
        with self.assertRaisesRegex(ValueError,'NECESSARY_BANK_WINDOW_DOMAIN'):
            optimize(source,necessary_bank_window=33)

    def test_prefetch_time_neighborhood_preserves_exact_words(self):
        from raster_slot_greedy import demand
        from raster_slot_refine import verify_packets
        source=self.schedule()
        hint=optimize(source,window=356,time_limit=3,flexible_prefetch=True,retain_write_times=True,split_bank_ranges=True)
        result=optimize(source,window=356,time_limit=3,flexible_prefetch=True,
            rectangle_lifetimes=True,split_bank_ranges=True,layout_hint=hint,hint_time_radius=1)
        verify_packets(result)
        self.assertEqual(result['physical_slot_layout']['hint_time_radius_lines'],1)
        _,_,a=demand(source);_,_,b=demand(result)
        self.assertTrue(all(np.array_equal(x,y)for x,y in zip(a,b)))
        times={}
        for row in hint['trace']:
            for e in row['updates']:times.setdefault((e['bank'],e['color']),[]).append(row['scanline'])
        for row in result['trace']:
            for e in row['updates']:
                self.assertTrue(any(abs(row['scanline']-y)<=1 for y in times[e['bank'],e['color']]))
        for radius in(-1,True):
            with self.assertRaisesRegex(ValueError,'HINT_TIME_RADIUS_DOMAIN'):
                optimize(source,flexible_prefetch=True,layout_hint=hint,hint_time_radius=radius)
        with self.assertRaisesRegex(ValueError,'HINT_TIME_RADIUS_DOMAIN'):
            optimize(source,hint_time_radius=1)

    def test_bounded_lifetime_repair_preserves_pixels_and_external_slots(self):
        from raster_slot_greedy import demand
        from raster_slot_refine import verify_packets
        source=self.schedule()
        hint=optimize(source,window=356,time_limit=3,flexible_prefetch=True,retain_write_times=True,split_bank_ranges=True)
        result=optimize(source,window=356,time_limit=3,flexible_prefetch=True,retain_write_times=True,
            split_bank_ranges=True,layout_hint=hint,lifetime_repair_interval=(1,2),search_strategy='lns')
        self.assertEqual(result['physical_slot_layout']['solver_search_strategy'],'lns')
        self.assertEqual(result['physical_slot_layout']['lifetime_repair_interval'],[1,2])
        self.assertGreater(result['physical_slot_layout']['movable_complete_lifetimes'],0)
        verify_packets(result)
        _,_,a=demand(source);_,_,b=demand(result)
        self.assertTrue(all(np.array_equal(x,y)for x,y in zip(a,b)))
        # The row-zero lifetime crosses the repair boundary and remains fixed.
        a=next(e for e in hint['trace'][0]['updates']if e['bank']==0)
        b=next(e for e in result['trace'][0]['updates']if e['bank']==0)
        self.assertEqual(a['slot'],b['slot'])
        for interval in((-1,2),(2,1),(0,16)):
            with self.assertRaisesRegex(ValueError,'LIFETIME_REPAIR_DOMAIN'):
                optimize(source,flexible_prefetch=True,retain_write_times=True,split_bank_ranges=True,
                    layout_hint=hint,lifetime_repair_interval=interval)
        with self.assertRaisesRegex(ValueError,'LIFETIME_REPAIR_DOMAIN'):
            optimize(source,lifetime_repair_interval=(1,2))
        with self.assertRaisesRegex(ValueError,'SEARCH_STRATEGY'):
            optimize(source,search_strategy='invalid')

    def test_idle_prefix_fold_preserves_source_words_and_opaque_zero(self):
        from raster_slot_greedy import demand
        source=self.schedule();prefix=4
        empty={b:[None]*15 for b in range(8)}
        source['trace']=[dict(scanline=y,resident_before=copy.deepcopy(empty),updates=[])for y in range(prefix)]+source['trace']
        for y,row in enumerate(source['trace']):row['scanline']=y
        for piece in source['pieces']:piece['y']+=prefix
        _,_,before=demand(source)
        result=optimize(source,window=356,time_limit=10,flexible_prefetch=True,
            split_bank_ranges=True,collapse_idle_prefix=True)
        self.assertEqual(result['physical_slot_layout']['first_visible_source_line'],prefix)
        self.assertTrue(result['physical_slot_layout']['idle_prefix_collapsed'])
        self.assertTrue(all(not row['updates']for row in result['trace'][1:prefix+1]))
        _,_,after=demand(result)
        self.assertTrue(all(np.array_equal(a,b)for a,b in zip(before,after)))
        with self.assertRaisesRegex(ValueError,'IDLE_PREFIX_DOMAIN'):optimize(source,collapse_idle_prefix=True)
        with self.assertRaisesRegex(ValueError,'IDLE_PREFIX_DOMAIN'):optimize(source,flexible_prefetch=True,retain_write_times=True,collapse_idle_prefix=True)

    def test_source_bound_alpha_controls_are_part_of_schedule_identity(self):
        source=self.schedule()
        source.update(scanline_math_controls_source_bound=True,selected_modes={'0':'half-add'},compiled_color_window_descriptors={'0':{'bounds':[[3,8],[255,0]]}})
        result=optimize(source,window=356,time_limit=10)
        base=dict(pieces=result['pieces'],pixel_masks=result['piece_pixel_masks'],trace=result['trace'])
        self.assertNotEqual(result['compiled_schedule_sha256'],hashlib.sha256(json.dumps(base,sort_keys=True).encode()).hexdigest())
        base.update(selected_modes=source['selected_modes'],compiled_color_window_descriptors=source['compiled_color_window_descriptors'])
        self.assertEqual(result['compiled_schedule_sha256'],hashlib.sha256(json.dumps(base,sort_keys=True).encode()).hexdigest())

    def test_paired_ranges_preserve_pixels_and_allow_inactive_pair_gaps(self):
        from raster_slot_greedy import demand
        source=self.schedule()
        source['pieces'][1]['bank']=7
        for row in source['trace']:
            row['resident_before'][7],row['resident_before'][1]=row['resident_before'][1],row['resident_before'][7]
            for event in row['updates']:
                if event['bank']==1:event['bank']=7
        _,_,a=demand(source)
        for flexible in(False,True):
            result=optimize(source,window=356,time_limit=10,paired_bank_ranges=True,flexible_prefetch=flexible)
            self.assertTrue(result['physical_slot_layout']['paired_bank_ranges'])
            self.assertTrue(result['physical_slot_layout']['all_packet_cgram_identities_verified'])
            _,_,b=demand(result)
            self.assertTrue(all(np.array_equal(x,y)for x,y in zip(a,b)))
            for row in result['prepared_dma_packets']:
                for p in row['packets']:
                    first=p['cgram_word_address']-128;last=first+p['word_count']-1
                    self.assertEqual(first//32,last//32)
        with self.assertRaisesRegex(ValueError,'PAIRED_RANGE_DOMAIN'):optimize(source,paired_bank_ranges=True,reorder_banks=True)

    def test_persistent_color_slot_family_replays_every_packet_and_pixel(self):
        result=optimize(self.schedule(),window=356,time_limit=10,
            flexible_prefetch=True,retain_write_times=True,persistent_color_slots=True)
        self.assertEqual(result['physical_slot_layout']['status'],'PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN')
        self.assertTrue(result['physical_slot_layout']['persistent_color_slots'])
        identities={}
        for row in result['trace']:
            for event in row['updates']:identities.setdefault((event['bank'],event['color']),set()).add(event['slot'])
        self.assertTrue(all(len(slots)==1 for slots in identities.values()))

    def schedule(self):
        state={b:[None]*15 for b in range(8)};trace=[]
        changes={0:[(0,1,31)],1:[(0,1,992)],2:[(0,1,31),(1,3,0)]}
        for y in range(16):
            before=copy.deepcopy(state);events=[]
            for b,s,c in changes.get(y,[]):events.append(dict(bank=b,slot=s,old=state[b][s-1],color=c));state[b][s-1]=c
            trace.append(dict(scanline=y,resident_before=before,updates=events))
        a=np.zeros((8,8),dtype=np.uint8);a[:3,0]=1
        b=np.zeros((8,8),dtype=np.uint8);b[2,0]=3
        masks=[]
        for image in (a,b):
            flat=image.flatten();masks.append(dict(width=8,height=8,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
        pieces=[dict(actor=0,bank=bank,x=x,y=0,local_x=x,local_y=0,width=8,height=8)for bank,x in ((0,0),(1,8))]
        return dict(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',compiled_pixel_identity_verified=True,no_color_reduction=True,pieces=pieces,piece_pixel_masks=masks,trace=trace)

    def test_physical_packets_and_reindexed_opaque_black_are_exact(self):
        for flexible in (False,True):
            r=optimize(self.schedule(),window=356,time_limit=10,flexible_prefetch=flexible)
            self.assertEqual(r['physical_slot_layout']['status'],'PHYSICAL_SLOT_PACKETS_AND_PIXEL_IDENTITIES_PROVEN')
            self.assertTrue(r['physical_slot_layout']['all_packet_cgram_identities_verified'])
            state={b:[None]*15 for b in range(8)};states=[]
            for row in r['trace']:
                for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
                states.append(copy.deepcopy(state))
            images=[unpack(m)for m in r['piece_pixel_masks']]
            self.assertEqual([states[y][0][int(images[0][y,0])-1]for y in range(3)],[31,992,31])
            self.assertNotEqual(images[1][2,0],0)
            self.assertEqual(states[2][1][int(images[1][2,0])-1],0)

    def test_tiny_window_rejects_fixed_timing_but_preloading_works(self):
        self.assertEqual(optimize(self.schedule(),window=1,time_limit=10)['solver_status'],'INFEASIBLE')
        r=optimize(self.schedule(),window=1,time_limit=10,flexible_prefetch=True)
        self.assertEqual(r['physical_slot_layout']['peak_prepared_commit_span'],0)
        self.assertEqual(r['peak_scheduled_writes'],0)

    def test_rectangle_lifetimes_preserve_reload_and_opaque_black(self):
        for window in (1,356):
            r=optimize(self.schedule(),window=window,time_limit=10,flexible_prefetch=True,rectangle_lifetimes=True,split_bank_ranges=True,reorder_banks=True)
            self.assertTrue(r['physical_slot_layout']['rectangle_lifetimes'])
            self.assertTrue(r['physical_slot_layout']['pixel_color_identity_verified'])
            self.assertTrue(r['physical_slot_layout']['all_packet_cgram_identities_verified'])
            if window==1:self.assertEqual(r['physical_slot_layout']['peak_prepared_commit_span'],0)
        with self.assertRaisesRegex(ValueError,'RECTANGLE_LIFETIME_DOMAIN'):optimize(self.schedule(),rectangle_lifetimes=True)

    def test_fixed_time_rectangle_lifetimes_preserve_all_source_slots_and_words(self):
        from raster_slot_refine import verify_packets
        from raster_slot_greedy import demand
        source=self.schedule()
        result=optimize(source,window=356,time_limit=5,flexible_prefetch=True,retain_write_times=True,rectangle_lifetimes=True,split_bank_ranges=True)
        verify_packets(result)
        self.assertTrue(result['physical_slot_layout']['rectangle_lifetimes'])
        self.assertTrue(result['physical_slot_layout']['retain_write_times'])
        for a,b in zip(demand(source)[2],demand(result)[2]):np.testing.assert_array_equal(a,b)

    def test_demand_groups_retain_a_color_across_an_unused_line(self):
        r=optimize(self.schedule(),window=356,time_limit=10,demand_gap=1,flexible_prefetch=True)
        self.assertEqual(r['physical_slot_layout']['used_lifetime_segments'],3)
        self.assertTrue(r['physical_slot_layout']['pixel_color_identity_verified'])
        image=unpack(r['piece_pixel_masks'][0])
        self.assertEqual(image[0,0],image[2,0])
        hinted=optimize(self.schedule(),window=356,time_limit=10,demand_gap=1,flexible_prefetch=True,layout_hint=r)
        self.assertTrue(hinted['physical_slot_layout']['layout_hint_used'])
        self.assertTrue(hinted['physical_slot_layout']['all_packet_cgram_identities_verified'])
        fixed=optimize(self.schedule(),window=356,time_limit=10,demand_gap=1,flexible_prefetch=True,layout_hint=r,fix_hint_slots=True)
        self.assertTrue(fixed['physical_slot_layout']['fixed_hint_slots'])
        self.assertEqual(fixed['piece_pixel_masks'],r['piece_pixel_masks'])
        with self.assertRaisesRegex(ValueError,'FIXED_HINT_REQUIRES_PREFETCH_HINT'):optimize(self.schedule(),fix_hint_slots=True)
        invalid=copy.deepcopy(r);invalid['source_rgb555_sha256']='different'
        with self.assertRaisesRegex(ValueError,'HINT_IDENTITY'):optimize(self.schedule(),layout_hint=invalid)
        with self.assertRaisesRegex(ValueError,'DEMAND_GAP_DOMAIN'):optimize(self.schedule(),demand_gap=-1)

    def test_bank_permutation_preserves_fixed_piece_bank_and_math_class(self):
        source=self.schedule()
        source['pieces'][1]['bank']=4
        for row in source['trace']:
            row['resident_before'][4],row['resident_before'][1]=row['resident_before'][1],row['resident_before'][4]
            for event in row['updates']:
                if event['bank']==1:event['bank']=4
        r=optimize(source,window=356,time_limit=10,flexible_prefetch=True,reorder_banks=True)
        layout=r['physical_slot_layout'];mapping=layout['fixed_piece_bank_permutation']
        self.assertEqual(sorted(mapping.values()),list(range(8)))
        for old,new in mapping.items():self.assertEqual(old//4,new//4)
        for old,new in zip(source['pieces'],r['pieces']):self.assertEqual(new['bank'],mapping[old['bank']])
        self.assertTrue(layout['all_packet_cgram_identities_verified'])
        permuted=copy.deepcopy(r);permutation={b:(b//4)*4+(b%4+1)%4 for b in range(8)}
        permuted['physical_slot_layout']['fixed_piece_bank_permutation']={old:permutation[new]for old,new in mapping.items()}
        for p in permuted['pieces']:p['bank']=permutation[p['bank']]
        for row in permuted['trace']:
            row['resident_before']={permutation[b]:values for b,values in row['resident_before'].items()}
            for e in row['updates']:e['bank']=permutation[e['bank']]
        warm=optimize(source,window=356,time_limit=10,flexible_prefetch=True,reorder_banks=True,layout_hint=permuted)
        self.assertTrue(warm['physical_slot_layout']['pixel_color_identity_verified'])
        states=[];state={b:[None]*15 for b in range(8)}
        for row in r['trace']:
            for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
            states.append(copy.deepcopy(state))
        for piece,mask,values in zip(r['pieces'],r['piece_pixel_masks'],([31,992,31],[None,None,0])):
            image=unpack(mask)
            for y,color in enumerate(values):
                if color is not None:self.assertEqual(states[y][piece['bank']][int(image[y,0])-1],color)
        with self.assertRaisesRegex(ValueError,'BANK_REORDER_REQUIRES_PREFETCH'):optimize(source,reorder_banks=True)

    def test_split_ranges_replay_prefetch_and_bank_permutation(self):
        fixed=optimize(self.schedule(),window=356,time_limit=10,split_bank_ranges=True)
        self.assertTrue(fixed['physical_slot_layout']['all_packet_cgram_identities_verified'])
        r=optimize(self.schedule(),window=356,time_limit=10,flexible_prefetch=True,reorder_banks=True,split_bank_ranges=True)
        self.assertTrue(r['physical_slot_layout']['split_bank_ranges'])
        self.assertTrue(r['physical_slot_layout']['pixel_color_identity_verified'])
        self.assertTrue(r['physical_slot_layout']['all_packet_cgram_identities_verified'])

    def test_physical_interval_cost_matches_exhaustive_partitions(self):
        from itertools import combinations
        from ortools.sat.python import cp_model
        from raster_physical_ranges import constrain
        for addresses in ([1,15],[1,15,17,31],[2,4,9,65,127],[15,17,31,33,63]):
            for limit in (1,2,4):
                costs=[]
                for count in range(1,min(limit,len(addresses))+1):
                    for cuts in combinations(range(1,len(addresses)),count-1):
                        bounds=(0,*cuts,len(addresses))
                        costs.append(sum(24+16*(addresses[bounds[j+1]-1]-addresses[bounds[j]]+1)for j in range(count)))
                model=cp_model.CpModel();flags={};slots=[]
                for i,address in enumerate(addresses):
                    bank,slot=divmod(address,16)
                    slots.append(model.new_constant(slot-1))
                    flags.setdefault((1,bank),[]).append((i,model.new_constant(1)))
                ranges,peak=constrain(model,flags,slots,2,limit,4096)
                model.minimize(peak);solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=10
                self.assertEqual(solver.solve(model),cp_model.OPTIMAL)
                self.assertEqual(solver.value(peak),min(costs))
        # Widely separated words in one bank can fit as two ranges, while
        # the one-range bank hull consumes 224 clocks after the span credit.
        self.assertEqual(2*(24+16)-40,40)

    def test_direct_physical_address_optimizes_math_class_bank_destinations(self):
        from ortools.sat.python import cp_model
        from raster_physical_ranges import constrain
        model=cp_model.CpModel()
        normal=model.new_int_var(0,3,'normalBank')
        additive=model.new_int_var(4,7,'additiveBank')
        flags={(1,0):[(0,model.new_constant(1))],(1,4):[(1,model.new_constant(1))]}
        ranges,peak=constrain(model,flags,[model.new_constant(14),model.new_constant(0)],2,1,356,{0:normal,4:additive})
        model.minimize(peak);solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=10
        self.assertEqual(solver.solve(model),cp_model.OPTIMAL)
        self.assertEqual((solver.value(normal),solver.value(additive)),(3,4))
        self.assertEqual(solver.value(peak),24+16*3)
        # The range bridges transparent bank word 64. Palette identity is
        # unaffected because packet construction writes transparent zero there.
        active,begin,end,length=ranges[1,0]
        self.assertEqual((solver.value(begin),solver.value(end)),(63,65))

    def test_global_slot_permutation_retains_full_bank_lifetimes(self):
        source=self.schedule();state={b:[None]*15 for b in range(8)};trace=[]
        for y in range(16):
            before=copy.deepcopy(state);events=[]
            changes=[(s,s)for s in range(1,16)]if y==0 else[(1,16)]if y==1 else[]
            for slot,color in changes:
                events.append(dict(bank=0,slot=slot,old=state[0][slot-1],color=color));state[0][slot-1]=color
            trace.append(dict(scanline=y,resident_before=before,updates=events))
        image=np.zeros((16,16),dtype=np.uint8);image[0,:15]=np.arange(1,16);image[1,0]=1
        flat=image.flatten();source.update(trace=trace,pieces=[dict(actor=0,bank=0,x=0,y=0,local_x=0,local_y=0,width=16,height=16)],piece_pixel_masks=[dict(width=16,height=16,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex())])
        hint=optimize(source,window=356,time_limit=10,flexible_prefetch=True,split_bank_ranges=True)
        result=optimize(source,window=356,time_limit=10,flexible_prefetch=True,split_bank_ranges=True,reorder_banks=True,layout_hint=hint,permute_hint_slots=True)
        layout=result['physical_slot_layout']
        self.assertTrue(layout['pixel_color_identity_verified'])
        self.assertTrue(layout['all_packet_cgram_identities_verified'])
        self.assertEqual(result['peak_scheduled_writes'],1)
        for values in layout['fixed_hint_slot_permutations'].values():self.assertEqual(sorted(values),list(range(15)))
        with self.assertRaisesRegex(ValueError,'PERMUTE_HINT_DOMAIN'):optimize(source,permute_hint_slots=True)

    def test_retain_write_times_preserves_events_with_free_physical_positions(self):
        source=self.schedule()
        r=optimize(source,window=356,time_limit=10,flexible_prefetch=True,retain_write_times=True,reorder_banks=True,split_bank_ranges=True)
        self.assertTrue(r['physical_slot_layout']['retain_write_times'])
        self.assertEqual([row['colors_written']for row in r['trace']],[len(row['updates'])for row in source['trace']])
        self.assertTrue(r['physical_slot_layout']['all_packet_cgram_identities_verified'])
        with self.assertRaisesRegex(ValueError,'RETAIN_WRITE_TIMES_DOMAIN'):optimize(source,retain_write_times=True)
        with self.assertRaisesRegex(ValueError,'RETAIN_WRITE_TIMES_DOMAIN'):optimize(source,flexible_prefetch=True,retain_write_times=True,demand_gap=0)
        source['trace'][1]['updates'].append(dict(bank=1,slot=3,old=None,color=0))
        source['trace'][2]['updates']=[e for e in source['trace'][2]['updates']if e['bank']!=1]
        source['trace'][2]['resident_before'][1][2]=0
        with self.assertRaisesRegex(ValueError,'RETAIN_WRITE_TIMES_LATENCY'):optimize(source,flexible_prefetch=True,retain_write_times=True,lookahead=0)
        r=optimize(source,window=356,time_limit=10,flexible_prefetch=True,retain_write_times=True,lookahead=1,split_bank_ranges=True)
        self.assertEqual(r['physical_slot_layout']['maximum_noninitial_prefetch_latency_lines'],1)
        self.assertEqual(r['physical_slot_layout']['input_schedule_noninitial_prefetch_latency_lines'],1)


if __name__=='__main__':unittest.main()
