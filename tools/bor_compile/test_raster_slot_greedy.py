import copy,itertools,unittest
import numpy as np
from raster_obj_compact import unpack
from raster_slot_greedy import partition,schedule_slots


def source_schedule():
    state={b:[None]*15 for b in range(8)};trace=[]
    for y in range(16):
        before=copy.deepcopy(state);events=[]
        for bank in (0,1):
            colors=list(range(15))if y==0 else[15]if y==7 else[0]if y==12 else[]
            for s,c in enumerate(colors):
                events.append(dict(bank=bank,slot=s+1,old=state[bank][s],color=c));state[bank][s]=c
        trace.append(dict(scanline=y,resident_before=before,updates=events))
    image=np.zeros((16,16),dtype=np.uint8)
    for y in range(16):
        image[y,:15]=np.arange(1,16)if y<7 or y>=12 else 1
    flat=image.flatten();mask=dict(width=16,height=16,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex())
    pieces=[dict(x=16*b,y=0,width=16,height=16,bank=b)for b in (0,1)]
    return dict(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',compiled_pixel_identity_verified=True,pieces=pieces,piece_pixel_masks=[mask,copy.deepcopy(mask)],trace=trace)


class GreedyTests(unittest.TestCase):
    def test_packet_partition_matches_all_small_groupings(self):
        bounds=[(1,1),(15,15),(17,19),(49,49)]
        for maximum in range(1,5):
            costs=[]
            for cuts in itertools.product((False,True),repeat=3):
                if sum(cuts)+1>maximum:continue
                groups=[];start=0
                for i,cut in enumerate((*cuts,True)):
                    if cut:groups.append((bounds[start][0],bounds[i][1]));start=i+1
                costs.append(max(0,sum(16*(hi-lo+1)+24 for lo,hi in groups)-40))
            self.assertEqual(partition(bounds,maximum)[0],min(costs))

    def test_eviction_reload_and_opaque_black_preserve_every_piece_pixel(self):
        source=source_schedule();result=schedule_slots(source,window=356,lookahead=0,seed=4)
        report=result['physical_slot_layout'];self.assertTrue(report['pixel_color_identity_verified'])
        self.assertGreaterEqual(report['color_reload_events'],2)
        self.assertEqual(report['maximum_noninitial_prefetch_latency_lines'],0)
        self.assertFalse(report['native_timing_admitted'])
        state={b:[None]*15 for b in range(8)};states=[]
        for row in result['trace']:
            for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
            states.append(copy.deepcopy(state))
        for p,mask in zip(result['pieces'],result['piece_pixel_masks']):
            image=unpack(mask)
            for y in range(16):
                for x in range(16):
                    if x==15:self.assertEqual(image[y,x],0);continue
                    self.assertNotEqual(image[y,x],0)
                    expected=x if y<7 or y>=12 else 15
                    self.assertEqual(states[y][p['bank']][int(image[y,x])-1],expected)

    def test_small_window_failure_is_bounded_without_raster_rejection(self):
        result=schedule_slots(source_schedule(),window=17,lookahead=0)
        self.assertEqual(result['status'],'BOUNDED_GREEDY_NO_CANDIDATE')
        self.assertEqual(result['failed_scanline'],7)
        self.assertFalse(result['universal_raster_rejected'])

    def test_missing_piece_mask_rejected(self):
        source=source_schedule();source['piece_pixel_masks'].pop()
        with self.assertRaisesRegex(ValueError,'PIECE_MASK_COUNT'):schedule_slots(source)

    def test_interval_repacking_retains_exact_black_and_fixed_banks(self):
        source=source_schedule()
        for seed in range(4):
            with self.subTest(seed=seed):
                result=schedule_slots(source,window=2000,lookahead=8,seed=seed,repack=True)
                self.assertEqual(result['pieces'],source['pieces'])
                self.assertTrue(result['physical_slot_layout']['interval_repacking_enabled'])
                self.assertTrue(result['physical_slot_layout']['all_packet_cgram_identities_verified'])
                self.assertTrue(result['physical_slot_layout']['pixel_color_identity_verified'])

    def test_bank_permutation_preserves_math_eligibility_and_pixel_identity(self):
        source=source_schedule()
        source['pieces'][1]['bank']=5
        for row in source['trace']:
            row['resident_before'][5]=row['resident_before'][1]
            row['resident_before'][1]=[None]*15
            for event in row['updates']:
                if event['bank']==1:event['bank']=5
        result=schedule_slots(source,window=2000,lookahead=8,seed=7,repack=True,permute_banks=True)
        mapping=result['physical_slot_layout']['fixed_piece_bank_permutation']
        self.assertEqual(set(mapping.values()),set(range(8)))
        self.assertTrue(all((b>=4)==(target>=4)for b,target in mapping.items()))
        self.assertEqual([p['bank']for p in result['pieces']],[mapping[p['bank']]for p in source['pieces']])
        self.assertTrue(result['physical_slot_layout']['pixel_color_identity_verified'])

    def test_global_beam_replays_complete_state_path(self):
        result=schedule_slots(source_schedule(),window=2000,lookahead=8,global_beam=3,beam=4,repack=True)
        self.assertEqual(result['physical_slot_layout']['global_beam'],3)
        self.assertTrue(result['physical_slot_layout']['pixel_color_identity_verified'])
        self.assertTrue(result['physical_slot_layout']['all_packet_cgram_identities_verified'])
        failed=schedule_slots(source_schedule(),window=17,lookahead=0,global_beam=3,beam=4)
        self.assertEqual(failed['status'],'BOUNDED_GREEDY_NO_CANDIDATE')
        self.assertFalse(failed['universal_raster_rejected'])


if __name__=='__main__':unittest.main()
