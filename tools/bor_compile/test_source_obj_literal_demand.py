import unittest
import numpy as np
from source_obj_literal_demand import build
from raster_slot_greedy import demand


class LiteralDemandTests(unittest.TestCase):
    def test_opaque_zero_fixed_banks_and_actor_ownership_replay(self):
        pixels=np.full((8,16),-1,dtype=np.int32);pixels[0]=np.arange(16);pixels[1]=np.arange(16)[::-1]
        actors=[dict(left=0,top=0,pixels=pixels)];bg=np.zeros((224,256),dtype=np.uint16);gold=bg.copy();gold[:2,:16]=pixels[:2]
        r=build(actors,{},bg,gold);_,_,images=demand(r)
        self.assertEqual(sum(np.sum(a>=0)for a in images),32)
        self.assertEqual({p['bank']for p in r['pieces']},{0,1})
        self.assertTrue(any(0 in a for a in images))
        self.assertFalse(r['native_presentation_proven'])
        actors.append(actors[0])
        with self.assertRaisesRegex(ValueError,'PIXEL_OWNER'):build(actors,{},bg,gold)

    def test_construction_capacity_and_bad_output_are_explicit(self):
        pixels=np.arange(121,dtype=np.int32)[None,:];bg=np.zeros((224,256),dtype=np.uint16);gold=bg.copy();gold[0,:121]=pixels
        with self.assertRaisesRegex(ValueError,'NOT_UNIVERSAL_REJECTION'):build([dict(left=0,top=0,pixels=pixels)],{},bg,gold)
        pixels=np.array([[1]],dtype=np.int32)
        with self.assertRaisesRegex(ValueError,'SOURCE_OUTPUT_REPLAY'):build([dict(left=0,top=0,pixels=pixels)],{},bg,bg)


if __name__=='__main__':unittest.main()
