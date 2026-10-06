import unittest
from pathlib import Path
import numpy as np
from compiler import Source
from source_screen_lookup import matrix,derive


class ScreenLookup(unittest.TestCase):
    def test_all_channel_inputs_use_rgb8_screen_before_hardware_projection(self):
        values=list(range(256))
        for channel in range(3):
            sources=[[0,0,0] for _ in values];destinations=[[0,0,0] for _ in values]
            for n in values:sources[n][channel]=n;destinations[n][channel]=n
            result=matrix(sources,destinations)
            expected=np.array([[((255-((255-s)*(255-d)//255))>>3)<<(5*channel)
                                for d in values] for s in values],dtype='<u2')
            self.assertTrue(np.array_equal(result,expected))
        # RGB555 first would erase source low bits before SCREEN arithmetic.
        self.assertEqual(int(matrix([[7,0,0]],[[7,0,0]])[0,0]),1)

    def test_reject_invalid_colors_instead_of_truncating(self):
        for color in ([-1,0,0],[256,0,0],[1.5,0,0],[1,2]):
            with self.assertRaises(ValueError):matrix([color],[[0,0,0]])

    def test_source_alpha_selection_and_exact_vocabulary(self):
        r=derive(Source(Path(__file__).resolve().parents[2]/'Masters of the Universe [v.3.0 Build 4086].pak'))
        self.assertEqual(r['destination_rgb8_colors'],1375)
        self.assertEqual(len(r['destinations']),len(set(map(tuple,r['destinations']))))
        self.assertEqual([e['model'] for e in r['effects']],['HBreath','HWWind','SkFBall'])
        self.assertEqual([e['rows'] for e in r['effects']],[254,246,129])
        self.assertFalse(r['stacked_screen_layers_bound'])
        self.assertTrue(r['no_color_reduction'])


if __name__=='__main__':unittest.main()
