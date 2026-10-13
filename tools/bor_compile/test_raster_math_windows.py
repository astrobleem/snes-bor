import itertools
import unittest
from raster_math_windows import compile_mask,compile_sparse_mask,evaluate,best_weighted_mask


class WindowTests(unittest.TestCase):
    def test_weighted_guide_matches_exhaustive_bounded_masks(self):
        scores={x:(float(x%3),float((x+1)%3))for x in (2,4,8,16,32,64)}
        value,mask=best_weighted_mask(scores,maximum_transitions=2)
        expected=max(sum(scores[x][b]for x,b in zip(scores,bits))
                     for bits in itertools.product((0,1),repeat=len(scores))
                     if sum(a!=b for a,b in zip(bits,bits[1:]))<=2)
        self.assertEqual(value,expected)
        descriptor=compile_sparse_mask(mask)
        self.assertTrue(all(evaluate(descriptor,x)==bool(b)for x,b in mask.items()))
        with self.assertRaisesRegex(ValueError,'SCORE_DOMAIN'):
            best_weighted_mask({256:(0.,1.)})

    def test_all_masks_with_up_to_four_transitions_replay(self):
        for count in range(5):
            for positions in itertools.combinations((1,32,64,96,128,192,255),count):
                for first in (0,1):
                    mask=[first^(sum(p<=x for p in positions)%2)for x in range(256)]
                    descriptor=compile_mask(mask)
                    self.assertEqual([int(evaluate(descriptor,x))for x in range(256)],mask)
                    self.assertFalse(descriptor['register_timing_admitted'])

    def test_many_alternating_intervals_fail_explicitly(self):
        with self.assertRaisesRegex(ValueError,'NOT_REPRESENTABLE'):compile_mask([x%2 for x in range(256)])

    def test_sparse_source_positions_can_use_inverted_two_windows(self):
        pixels={10:1,20:0,30:1,40:0,50:1}
        descriptor=compile_sparse_mask(pixels)
        self.assertEqual(descriptor['wobjsel_color_bits'],0xf0)
        self.assertEqual(descriptor['wobjlog_color_bits'],4)
        self.assertTrue(all(evaluate(descriptor,x)==bool(v)for x,v in pixels.items()))

    def test_fixed_controls_disable_unused_window_without_changing_eligibility(self):
        for mask in ([0]*256,[1]*256,[int(32<=x<=64 or 128<=x<=200)for x in range(256)]):
            descriptor=compile_mask(mask,True)
            self.assertEqual(descriptor['wobjsel_color_bits'],0xa0)
            self.assertEqual(descriptor['wobjlog_color_bits'],0)
            self.assertEqual([int(evaluate(descriptor,x))for x in range(256)],mask)
        with self.assertRaisesRegex(ValueError,'POSITIVE_UNION_NOT_REPRESENTABLE'):
            compile_mask([int(not(32<=x<=64 or 128<=x<=200))for x in range(256)],True)


if __name__=='__main__':unittest.main()
