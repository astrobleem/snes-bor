import unittest
import numpy as np
from raster_scanline_bank_geometry import bound,exact_row_word_options
from test_raster_mask_rectangle_cover import fixture


class RowBankGeometryTests(unittest.TestCase):
    def test_exact_black_and_bank_domains_remain_separate(self):
        source=fixture();result=bound(source,5,time_limit=3)
        self.assertEqual(result['status'],'ROW_BANK_GEOMETRY_RELAXED_WITNESS')
        self.assertEqual(result['tile_slivers'],2)
        self.assertEqual([(p['color'],p['bank'])for p in result['pixels']],[(0,0),(33,4)])
        self.assertFalse(result['complete_frame_admitted'])
        self.assertFalse(result['native_timing_admitted'])

    def test_impossible_row_limit_is_only_fixed_encoding_rejection(self):
        result=bound(fixture(),5,time_limit=3,tile_limit=1)
        self.assertEqual(result['solver_status'],'INFEASIBLE')
        self.assertFalse(result['universal_raster_rejected'])

    def test_ambiguous_visible_pixel_owner_fails(self):
        source=fixture();source['pieces'][1].update(x=10,local_x=10)
        with self.assertRaisesRegex(ValueError,'VISIBLE_OVERLAP'):bound(source,5)

    def test_explicit_word_options_are_replayed_without_claiming_input_identity(self):
        result=bound(fixture(),5,time_limit=3,pixel_word_options={12:{2:[1,9]},32:{2:[1,9]}})
        self.assertTrue(result['explicit_pixel_word_option_domain'])
        self.assertFalse(result['source_word_and_bank_capacity_replayed'])
        self.assertTrue(all(p['bank']==2 and p['color']in(1,9)for p in result['pixels']))
        with self.assertRaisesRegex(ValueError,'OPTION_PIXELS'):bound(fixture(),5,pixel_word_options={})

    def test_diagnostic_limit_never_admits_hardware(self):
        result=bound(fixture(),5,time_limit=3,tile_limit=128)
        self.assertTrue(result['diagnostic_limit_exceeds_hardware'])
        self.assertFalse(result['complete_frame_admitted'])

    def test_reopened_operands_match_exact_background_output(self):
        from raster_math_windows import compile_sparse_mask
        from raster_obj_math_cover import apply_math
        source=fixture();source.update(scanline_math_controls_source_bound=True,selected_modes={'5':'add'},
            compiled_color_window_descriptors={'5':compile_sparse_mask({x:1 for x in range(256)})})
        bg=np.zeros(256,dtype=np.uint16);bg[32]=1;expected=bg.copy();expected[32]=34
        options,proof=exact_row_word_options(source,5,bg,expected)
        self.assertEqual(options[32][0],[34]);self.assertEqual(options[32][4],[33])
        self.assertEqual(proof['complete_row_source_pixels_replayed'],256)
        result=bound(source,5,time_limit=3,pixel_word_options=options)
        for p in result['pixels']:
            actual=apply_math(p['color'],int(bg[p['x']]),'add')if p['bank']>=4 else p['color']
            self.assertEqual(actual,expected[p['x']])
        expected[200]=1
        with self.assertRaisesRegex(ValueError,'SOURCE_OUTPUT_REPLAY'):exact_row_word_options(source,5,bg,expected)


if __name__=='__main__':unittest.main()
