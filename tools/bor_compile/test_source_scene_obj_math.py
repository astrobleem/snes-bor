import itertools
import unittest
import numpy as np
from source_scene_obj_math import residual, add_rgb555, minimum_cover, split_interval_bound, subdivide_for_limits
from source_scene_obj_raster import geometry


class ExactObjMathTests(unittest.TestCase):
    def test_channel_residuals_exhaustive(self):
        for shift, output, background in itertools.product((0, 5, 10), range(32), range(32)):
            result = residual(output << shift, background << shift)
            if output < background:
                self.assertIsNone(result)
            else:
                self.assertEqual(add_rgb555(result, background << shift), output << shift)

    def test_saturation_and_black_are_opaque_identities(self):
        self.assertEqual(residual(0, 0), 0)
        self.assertEqual(add_rgb555(32767, 32767), 32767)
        self.assertEqual(residual(32767, 32767), 0)
        self.assertIsNone(residual(31, 1024))

    def test_minimum_cover_against_brute_force(self):
        pairs = list(itertools.product(range(3), repeat=2))
        for bits in range(1 << len(pairs)):
            edges = [pair for i, pair in enumerate(pairs) if bits & (1 << i)]
            for forced_bits in (0, 1, 3, 7):
                forced = {i for i in range(3) if forced_bits & (1 << i)}
                left, right = minimum_cover(edges, forced)
                best = 6
                for mask in range(64):
                    l = {i for i in range(3) if mask & (1 << i)}
                    r = {i for i in range(3) if mask & (1 << (i + 3))}
                    if forced <= l and all(a in l or b in r for a, b in edges):
                        best = min(best, len(l) + len(r))
                self.assertEqual(len(left) + len(right), best)
                self.assertTrue(forced <= left)

    def test_eligibility_pools_share_transfer_window(self):
        group = [set(range(40)), set(range(40, 80))]
        result = split_interval_bound([group, group])
        self.assertEqual(result['status'], 'CGRAM_DATA_WINDOW_INFEASIBLE')
        self.assertEqual(result['worst_interval']['minimum_data_bytes'], 79)

    def test_subdivision_preserves_sparse_source_pixels(self):
        surfaces = []
        for i in range(9):
            pixels = np.full((32, 32), -1, dtype=np.int32)
            pixels[3, 5] = i
            surfaces.append(dict(pixels=pixels, left=0, top=0))
        original = geometry(surfaces, 'mixed')
        pieces, result = subdivide_for_limits(original, surfaces, 32)
        self.assertEqual(result['status'], 'SUBDIVISION_GEOMETRY_PROVEN')
        self.assertLessEqual(max(sum(p['width']//8 for p in pieces if p['y'] <= y < p['y']+p['height']) for y in range(32)), 34)
        for i in range(9):
            covering = [p for p in pieces if p['actor'] == i and p['local_x'] <= 5 < p['local_x']+p['width'] and p['local_y'] <= 3 < p['local_y']+p['height']]
            self.assertEqual(len(covering), 1)
            self.assertEqual(covering[0]['rows'][3], [i])


if __name__ == '__main__':
    unittest.main()
