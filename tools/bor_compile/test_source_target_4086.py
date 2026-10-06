import unittest
from dataclasses import replace
from source_target_4086 import Target, find, metadata, descriptor, order_table, BASE, FIRST_UNUSED


class SourceTarget(unittest.TestCase):
    def test_facing_preference_and_pool_order(self):
        actor = Target(1, type=2, hostile=1)
        left = Target(2, x=-10*65536, type=1)
        right = Target(3, x=20*65536, type=1)
        near_right = replace(right, token=4, x=5*65536)
        self.assertEqual(find([actor,left,right],1),2)
        self.assertEqual(find([actor,right,left],1),3)
        self.assertEqual(find([actor,left,near_right],1),4)
        self.assertEqual(find([replace(actor,direction=0),right,left],1),2)

    def test_vulnerability_and_invincibility_precedence(self):
        actor = Target(1, type=2, hostile=1)
        near = Target(2, x=1*65536, type=1)
        far = Target(3, x=-100*65536, type=1)
        self.assertEqual(find([actor,replace(near,vulnerable=False),far],1),3)
        self.assertEqual(find([actor,replace(near,invincible=1),far],1),3)
        self.assertEqual(find([actor,replace(near,invincible=2),far],1),2)

    def test_filters_distance_and_signed_coordinates(self):
        actor = Target(1, type=2, hostile=1, x=-32768*65536, detect=-1)
        far = Target(2, type=1, x=32767*65536, hide=-1)
        self.assertIsNone(find([actor,far],1))
        near = replace(far,x=actor.x+9999*65536)
        self.assertEqual(find([actor,near],1),2)
        for row in (replace(near,x=near.x+1),replace(near,hide=0),replace(near,dead=True),
                    replace(near,alive=False),replace(near,type=0)):
            self.assertIsNone(find([actor,row],1))
        self.assertIsNone(find([actor,near],0))

    def test_metadata_lease_and_pool_limits(self):
        self.assertEqual(len(metadata(Target(1))),20)
        self.assertEqual(len(descriptor(128,0xffffffff)),8)
        self.assertEqual((BASE,FIRST_UNUSED),(0x41e800,0x41f300))
        with self.assertRaises(ValueError): descriptor(129,0)
        with self.assertRaises(ValueError): find([Target(1)],2)
        with self.assertRaises(ValueError): find([Target(1),Target(1)],1)

    def test_pointer_order_and_active_prefix_are_independent_of_slots(self):
        rows=[Target(1,type=2,hostile=1),Target(2,type=1,x=-65536),Target(3,type=1,x=2*65536)]
        self.assertEqual(find(rows,1,order=[0,2,1]),3)
        self.assertEqual(find(rows,1,order=[0,1,2]),2)
        self.assertIsNone(find(rows,1,order=[0,1,2],scan_count=1))
        with self.assertRaises(ValueError): order_table([0,0,2])


if __name__ == '__main__': unittest.main()
