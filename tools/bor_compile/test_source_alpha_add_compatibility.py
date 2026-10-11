import unittest
from source_alpha_add_compatibility import channel_errors


class AlphaCompatibilityTests(unittest.TestCase):
    def test_exhaustive_projection_error_is_retained_without_policy_selection(self):
        report=channel_errors()
        self.assertEqual(report['exhaustive_source_destination_pairs'],65536)
        self.assertEqual(sum(report['signed_error_histogram'].values()),65536)
        self.assertEqual(report['maximum_absolute_rgb5_channel_error'],8)
        self.assertEqual(report['minimum_signed_rgb5_channel_error'],-1)
        self.assertEqual(report['signed_error_histogram']['0'],16842)
        # Both black operands and a fully saturated source agree exactly;
        # SRC=80, DST=80 exposes the non-SCREEN nature of projected addition.
        for src,dst,error in ((0,231,0),(80,0,0),(255,127,0),(80,80,4),(15,15,-1)):
            exact=(255-((255-src)*(255-dst)//255))>>3
            alternative=min(31,(src>>3)+(dst>>3))
            self.assertEqual(alternative-exact,error)


if __name__=='__main__':unittest.main()
