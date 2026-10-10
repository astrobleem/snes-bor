import unittest
from raster_obj_math_cover import MODES,apply_math,complete_math_cover


class MathCoverTests(unittest.TestCase):
    def test_halving_precedes_addition_clamping_and_follows_subtraction_clamping(self):
        self.assertEqual(apply_math(31,31,'half-add'),31)
        self.assertEqual(apply_math(31,1,'half-add'),16)
        self.assertEqual(apply_math(1,31,'half-subtract'),0)
        self.assertEqual(apply_math(31,2,'half-subtract'),14)

    def test_complete_modes_cover_every_brute_force_valid_operand(self):
        keys=[(0,0),(16,1),(31,0),(5,2)]
        for modes in (MODES,('half-add',),('subtract',)):
            options,report=complete_math_cover(keys,modes)
            coverage=lambda c:{key for key in keys if any(apply_math(c,key[1],m)==key[0]for m in modes)}
            retained={c:coverage(c)for values in options.values()for c in values}
            for c in range(32768):
                covered=coverage(c)
                if covered:self.assertTrue(any(covered<=candidate for candidate in retained.values()))
            for key,values in options.items():
                self.assertTrue(all(key in coverage(c)for c in values))
            self.assertFalse(report['global_mode_schedule_proven'])

    def test_unreachable_math_output_preserves_empty_choice(self):
        options,_=complete_math_cover([(31,0)],('half-add',))
        self.assertEqual(options[31,0],[])

    def test_tagged_coverage_retains_operands_across_mode_changes(self):
        keys=[(16,1),(5,2)]
        options,report=complete_math_cover(keys,tag_modes=True)
        tagged=[(m,*key)for m in MODES for key in keys]
        def coverage(c):return {key for key in tagged if apply_math(c,key[2],key[0])==key[1]}
        retained={c:coverage(c)for values in options.values()for c in values}
        for c in range(32768):
            covered=coverage(c)
            if covered:self.assertTrue(any(covered<=candidate for candidate in retained.values()))
        self.assertTrue(report['mode_tagged_coverage'])
        self.assertFalse(report['modes_relaxed_per_pixel'])


if __name__=='__main__':unittest.main()
