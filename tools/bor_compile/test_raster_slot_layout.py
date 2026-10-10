import copy,importlib.util,unittest
import numpy as np
from raster_obj_compact import unpack
from raster_slot_layout import optimize


@unittest.skipUnless(importlib.util.find_spec('ortools'),'optional OR-Tools backend')
class SlotLayoutTests(unittest.TestCase):
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

    def test_demand_groups_retain_a_color_across_an_unused_line(self):
        r=optimize(self.schedule(),window=356,time_limit=10,demand_gap=1,flexible_prefetch=True)
        self.assertEqual(r['physical_slot_layout']['used_lifetime_segments'],3)
        self.assertTrue(r['physical_slot_layout']['pixel_color_identity_verified'])
        image=unpack(r['piece_pixel_masks'][0])
        self.assertEqual(image[0,0],image[2,0])
        hinted=optimize(self.schedule(),window=356,time_limit=10,demand_gap=1,flexible_prefetch=True,layout_hint=r)
        self.assertTrue(hinted['physical_slot_layout']['layout_hint_used'])
        self.assertTrue(hinted['physical_slot_layout']['all_packet_cgram_identities_verified'])
        invalid=copy.deepcopy(r);invalid['source_rgb555_sha256']='different'
        with self.assertRaisesRegex(ValueError,'HINT_IDENTITY'):optimize(self.schedule(),layout_hint=invalid)
        with self.assertRaisesRegex(ValueError,'DEMAND_GAP_DOMAIN'):optimize(self.schedule(),demand_gap=-1)


if __name__=='__main__':unittest.main()
