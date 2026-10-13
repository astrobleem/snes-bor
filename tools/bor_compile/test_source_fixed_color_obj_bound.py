import unittest
import importlib.util
import numpy as np

from source_fixed_color_obj_bound import derive_colors, inputs, replay
from raster_obj_math_cover import apply_math


class FixedColorTests(unittest.TestCase):
    def fixture(self):
        background = np.zeros((3, 6), dtype=np.uint16)
        actors = [dict(metadata=dict(alpha=0), pixels=np.array([[1]]), top=0, left=0),
                  dict(metadata=dict(alpha=1), pixels=np.array([[6, 0]]), top=1, left=0)]
        expected = background.copy()
        expected[0, 0] = 1
        expected[1, 0] = 6
        data = inputs(actors, background, {1: 2}, ('add',))
        pixels, reserve, ordinary, bypass, rows, window_pixels, cover = data
        bound = dict(selected_palette_residency={'1': {'0': [1], '1': [4]}},
                     selected_modes={'1': 'add'}, selected_window_eligibility={'1': {'0': 1}},
                     peak_write_objective=0, reserved_normal_colors=[1])
        return background, actors, expected, data, bound

    def test_fixed_color_is_shared_and_channel_values_are_legal(self):
        pixels = [(1, 0, 6 | (8 << 5) | (10 << 10)), (1, 1, 7 | (4 << 5) | (9 << 10))]
        self.assertEqual(derive_colors(pixels, 'add-minimum'), {1: 6 | (4 << 5) | (9 << 10)})
        for policy in ('zero', 'add-minimum', 'subtract-headroom', 'half-add-bright'):
            self.assertTrue(all(0 <= c < 32768 for c in derive_colors(pixels, policy).values()))

    def test_replay_includes_ordinary_background_and_effect_equal_to_background(self):
        bg, actors, expected, data, bound = self.fixture()
        pixels, reserve, ordinary, bypass, rows, window_pixels, cover = data
        self.assertEqual(reserve, {1})
        self.assertEqual(bypass, 1)
        self.assertEqual(pixels, [(1, 0, 6)])
        result = replay(bound, rows, window_pixels, {1: 2}, pixels, ordinary, bg, expected)
        self.assertEqual(result['viewport_pixels_replayed'], 18)
        self.assertEqual(result['fixed_color_register_bytes'], {1: [0x22, 0x40, 0x80]})
        self.assertFalse(result['cgwsel_add_subscreen'])
        self.assertFalse(result['native_timing_admitted'])
        self.assertFalse(result['physical_transfer_admitted'])

    def test_independent_replay_rejects_wrong_fixed_operand_and_missing_ordinary_residency(self):
        bg, actors, expected, data, bound = self.fixture()
        pixels, reserve, ordinary, bypass, rows, window_pixels, cover = data
        with self.assertRaisesRegex(AssertionError, 'FIXED_COLOR_SOURCE_PIXEL_REPLAY'):
            replay(bound, rows, window_pixels, {1: 3}, pixels, ordinary, bg, expected)
        bound['selected_palette_residency']['1']['0'] = []
        with self.assertRaisesRegex(AssertionError, 'STATIC_RESERVATION_REPLAY'):
            replay(bound, rows, window_pixels, {1: 2}, pixels, ordinary, bg, expected)

    def test_replay_rejects_an_uncovered_background_pixel(self):
        bg, actors, expected, data, bound = self.fixture()
        pixels, reserve, ordinary, bypass, rows, window_pixels, cover = data
        expected[2, 5] = 1
        with self.assertRaisesRegex(AssertionError, 'COMPLETE_VIEWPORT_REPLAY'):
            replay(bound, rows, window_pixels, {1: 2}, pixels, ordinary, bg, expected)

    def test_row_domain_rejects_missing_extra_or_non_rgb555_colors(self):
        bg, actors, expected, data, bound = self.fixture()
        for fixed in ({}, {1: 2, 2: 0}, {1: -1}, {1: 32768}, {1: True}, {'1': 2}):
            with self.assertRaisesRegex(ValueError, 'FIXED_COLOR_ROW_DOMAIN'):
                inputs(actors, bg, fixed, ('add',))

    def test_halving_fixed_color_does_not_use_subscreen_backdrop_exception(self):
        bg, actors, expected, data, bound = self.fixture()
        pixels, reserve, ordinary, bypass, rows, window_pixels, cover = inputs(actors, bg, {1: 2}, ('half-add',))
        choices = next(iter(rows[1]['half-add']))[1]
        self.assertTrue(choices)
        self.assertTrue(all(apply_math(c, 2, 'half-add') == 6 for c in choices))
        bound['selected_modes']['1'] = 'half-add'
        bound['selected_palette_residency']['1']['1'] = [10]
        replay(bound, rows, window_pixels, {1: 2}, pixels, ordinary, bg, expected)

    def test_no_window_replay_enables_math_at_all_coordinates(self):
        bg, actors, expected, data, bound = self.fixture()
        pixels, reserve, ordinary, bypass, rows, window_pixels, cover = data
        del bound['selected_window_eligibility']
        result = replay(bound, rows, None, {1: 2}, pixels, ordinary, bg, expected)
        from raster_math_windows import evaluate
        descriptor = result['compiled_color_window_descriptors'][1]
        self.assertTrue(all(evaluate(descriptor, x) for x in range(256)))

    @unittest.skipUnless(importlib.util.find_spec('ortools'), 'optional OR-Tools backend')
    def test_joint_fixed_color_choice_has_one_shared_integer_control_and_exact_replay(self):
        from raster_math_mode_liveness import lower_bound
        bg, actors, expected, data, _ = self.fixture()
        pixels, reserve, ordinary, bypass, original_rows, _, cover = data
        rows = [{}, {'first:add': {(6, (4,))}, 'second:add': {(6, (3,))}}, {}]
        choices = {1: {'first:add': ('add', 2), 'second:add': ('add', 3)}}
        bound = lower_bound(rows, reserved_normal_colors=reserve, integer_modes=True,
                            integer_palette=True, integer_backend='cp-sat', write_budget=0,
                            capacities=(1, 1), time_limit=5)
        self.assertTrue(bound['integer_pool_pixel_coverage_verified'])
        # Independent replay permits only the physical 60/60 classes; the
        # solver's smaller test caches are a stronger fixture restriction.
        result = replay(bound, rows, None, None, pixels, ordinary, bg, expected, choices)
        label = bound['selected_modes'][1]
        self.assertEqual(result['fixed_color_rgb555_rows'], {1: choices[1][label][1]})
        self.assertEqual(result['selected_math_modes'], {1: 'add'})
        self.assertEqual(result['viewport_pixels_replayed'], 18)

    def test_positive_windows_replay_uses_the_native_two_window_family(self):
        from source_fixed_color_obj_bound import measure
        bg, actors, expected, data, bound = self.fixture()
        actors[1]['left'] = 2
        expected[1, 0] = 0
        expected[1, 2] = 6
        pixels, reserve, ordinary, bypass, rows, window_pixels, cover = inputs(actors, bg, {1: 2}, ('add',))
        bound['selected_window_eligibility'] = {'1': {'0': 0, '2': 1, '255': 0}}
        bound['positive_union_with_disabled_edges_only'] = True
        result = replay(bound, rows, window_pixels, {1: 2}, pixels, ordinary, bg, expected)
        self.assertEqual(result['compiled_color_window_descriptors'][1]['wobjsel_color_bits'], 0xa0)
        self.assertEqual(result['compiled_color_window_descriptors'][1]['wobjlog_color_bits'], 0)
        with self.assertRaisesRegex(ValueError, 'POSITIVE_WINDOWS_REQUIRE_WINDOWS'):
            measure(None, None, {}, hardware_windows=False, positive_windows_only=True)


if __name__ == '__main__':
    unittest.main()
