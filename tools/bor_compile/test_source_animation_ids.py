import unittest
from source_animation_ids import configure,role_id,animation_constant


class AnimationIdentities(unittest.TestCase):
    def test_source_loader_and_constant_names_are_distinct(self):
        c=configure([])
        self.assertEqual(role_id(c,'waiting'),59)
        self.assertEqual(role_id(c,'select'),25)
        self.assertEqual(role_id(c,'freespecial4'),44)
        self.assertEqual(animation_constant(c,'ANI_SELECT'),59)
        self.assertEqual(role_id(c,'attack1'),8)
        self.assertEqual(animation_constant(c,'ANI_ATTACK'),7)
        self.assertEqual(role_id(c,'pain5'),4)
        self.assertEqual(animation_constant(c,'ANI_PAIN5'),85)

    def test_expansion_order_is_global(self):
        c=configure([dict(directive='maxfollows',values=['10'])])
        self.assertEqual(role_id(c,'follow5'),162)
        self.assertEqual(role_id(c,'follow6'),163)
        self.assertEqual(animation_constant(c,'ani_follow10'),167)
        self.assertEqual(c['max_animations'],168)
        c=configure([dict(directive='maxidles',values=['3']),dict(directive='maxfollows',values=['10'])])
        self.assertEqual(role_id(c,'idle2'),162)
        self.assertEqual(role_id(c,'follow5'),164)

    def test_clamping_and_explicit_rejection(self):
        c=configure([dict(directive='maxfollows',values=['0'])])
        self.assertEqual(c['limits']['max_follows'],4)
        for role in ['follow5','follow0','unknown']:
            with self.assertRaises(ValueError):role_id(c,role)
        with self.assertRaises(ValueError):configure([dict(directive='maxfollows',values=['1025'])])


if __name__=='__main__':unittest.main()
