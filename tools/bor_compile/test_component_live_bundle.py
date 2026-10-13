import copy
import unittest

import numpy as np
from bg_component_residency import OnlinePlaneCache
from component_live_bundle import OnlineComponentBundle,context_identity,full_component_layout,FENCES


def tiles(value=0):
    return [(x,y,np.full((8,8),value,dtype=np.uint8))for y in range(28)for x in range(32)]


def snapshot():
    return dict(source_tick=1,actors=[dict(token=0x414000,model=3,model_generation=1,animation='idle',frame=0,palette='source',remap=0,position=[80,220,0],flip=False,alpha=0)],
                camera=[0,0],underlay='opaque-source',layer_order=[0],hud=dict(health=150,mp=100))


class LiveBundleTests(unittest.TestCase):
    def test_full_layout_cannot_retain_extra_obj_arena(self):
        plan=full_component_layout()
        self.assertEqual(sum(b-a for a,b in plan['allocations'].values()),65536)
        self.assertEqual(plan['obj_chr_bytes'],0)
        self.assertEqual(plan['hud_owner'],'component_canvas')
        self.assertFalse(plan['native_live_admitted'])

    def test_all_context_dependencies_invalidate_identity(self):
        base=snapshot();identity=context_identity(base)
        for key in ('source_tick','camera','underlay','layer_order','hud'):
            changed=copy.deepcopy(base);changed[key]=str(changed[key])+'changed'
            if key=='source_tick':changed[key]=2
            self.assertNotEqual(context_identity(changed),identity)
        for key in base['actors'][0]:
            changed=copy.deepcopy(base);changed['actors'][0][key]=str(changed['actors'][0][key])+'changed'
            self.assertNotEqual(context_identity(changed),identity)

    def test_tile_storage_stays_pinned_until_publication(self):
        cache=OnlinePlaneCache(2,2)
        first=cache.prepare(1,tiles());slot=first['writes'][0]['slot']
        with self.assertRaisesRegex(ValueError,'NOT_READY'):cache.publish(1)
        cache.acknowledge(1,slot);cache.publish(1)
        second=cache.prepare(2,tiles(1))
        self.assertNotEqual(second['writes'][0]['slot'],slot)
        self.assertEqual(cache.visible,{slot})
        with self.assertRaisesRegex(ValueError,'TRANSFER_FENCE'):cache.acknowledge(1,second['writes'][0]['slot'])
        cache.acknowledge(2,second['writes'][0]['slot']);cache.publish(2)
        third=cache.prepare(3,tiles(2))
        self.assertEqual(third['writes'][0]['slot'],slot)

    def test_no_spare_slot_defers_instead_of_overwriting_display(self):
        cache=OnlinePlaneCache(2,1)
        cache.prepare(1,tiles());cache.acknowledge(1,0);cache.publish(1)
        before=dict(cache.resident)
        with self.assertRaisesRegex(ValueError,'SAFE_PRELOAD_CAPACITY'):cache.prepare(2,tiles(1))
        self.assertEqual(cache.resident,before)
        self.assertIsNone(cache.pending)

    def test_whole_bundle_requires_both_planes_and_all_fences(self):
        bundle=OnlineComponentBundle();snap=snapshot();identity=context_identity(snap)
        member=dict(epoch=1,context=identity)
        prepared=bundle.prepare(1,snap,tiles(4),tiles(),member,member,dict(member,drawn=True))
        for plane in ('high','low'):
            for write in prepared[plane]['writes']:bundle.acknowledge(1,plane+'_chr',write['slot'])
        for fence in FENCES[:-1]:bundle.acknowledge(1,fence)
        with self.assertRaisesRegex(ValueError,'NOT_READY'):bundle.publish(1,safe_boundary=True)
        self.assertIsNone(bundle.high.visible_epoch)
        self.assertIsNone(bundle.low.visible_epoch)
        bundle.acknowledge(1,FENCES[-1])
        with self.assertRaisesRegex(ValueError,'NOT_READY'):bundle.publish(1,safe_boundary=False)
        self.assertEqual(bundle.publish(1,safe_boundary=True)['context'],identity)
        self.assertEqual(bundle.high.visible_epoch,bundle.low.visible_epoch)

    def test_mixed_epochs_and_undrawn_hud_rejected(self):
        bundle=OnlineComponentBundle();snap=snapshot();m=dict(epoch=1,context=context_identity(snap))
        with self.assertRaisesRegex(ValueError,'MIXED_SNAPSHOT'):
            bundle.prepare(1,snap,tiles(4),tiles(),m,dict(m,epoch=2),dict(m,drawn=True))
        with self.assertRaisesRegex(ValueError,'HUD_DRAW_REQUIRED'):
            bundle.prepare(1,snap,tiles(4),tiles(),m,m,m)

    def test_low_plane_capacity_failure_rolls_back_high_prepare(self):
        bundle=OnlineComponentBundle();bundle.low=OnlinePlaneCache(2,1)
        snap=snapshot();m=dict(epoch=1,context=context_identity(snap))
        low=tiles();low[1]=(1,0,np.ones((8,8),dtype=np.uint8))
        with self.assertRaisesRegex(ValueError,'SAFE_PRELOAD_CAPACITY'):
            bundle.prepare(1,snap,tiles(4),low,m,m,dict(m,drawn=True))
        self.assertIsNone(bundle.high.pending)
        self.assertIsNone(bundle.low.pending)


if __name__=='__main__':unittest.main()
