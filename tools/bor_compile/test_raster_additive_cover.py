import unittest
from raster_additive_cover import complete_cover
from source_scene_obj_math import add_rgb555


class AdditiveCoverTests(unittest.TestCase):
    def test_cross_pixel_unsaturated_channels_need_a_mixed_operand(self):
        # A fixes R=5 and B=7; B fixes G=12 and B=7. Their common exact
        # operand is not either pixel's minimal/min-max corner word.
        a_out=30|(31<<5)|(20<<10);a_bg=25|(21<<5)|(13<<10)
        b_out=31|(30<<5)|(20<<10);b_bg=29|(18<<5)|(13<<10)
        a_min=5|(10<<5)|(7<<10);b_min=2|(12<<5)|(7<<10)
        options,report=complete_cover([(a_out,a_min),(b_out,b_min)])
        common=set(options[a_out,a_min])&set(options[b_out,b_min])
        self.assertIn(5|(12<<5)|(7<<10),common)
        self.assertTrue(all(add_rgb555(c,a_bg)==a_out for c in options[a_out,a_min]))
        self.assertTrue(all(add_rgb555(c,b_bg)==b_out for c in options[b_out,b_min]))
        self.assertEqual(report['rgb555_operands_examined'],32768)
        self.assertTrue(report['all_valid_operand_coverages_retained'])

    def test_opaque_black_and_zero_additive_operand_stay_distinct(self):
        options,report=complete_cover([(0,None),(0,0)])
        self.assertEqual(options,{(0,0):[0]})
        self.assertEqual(report['valid_operands'],1)

    def test_empty_additive_domain_is_explicit(self):
        options,report=complete_cover([(0,None)])
        self.assertEqual(options,{})
        self.assertEqual(report['maximal_cover_operands'],0)
        self.assertEqual(report['rgb555_operands_examined'],0)
        self.assertTrue(report['complete_for_immutable_context'])


if __name__=='__main__':unittest.main()
