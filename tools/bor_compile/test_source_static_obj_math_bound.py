import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
from source_static_obj_math_bound import measure
from raster_obj_math_cover import MODES


class StaticObjBoundTests(unittest.TestCase):
    def run_fixture(self,effect=False):
        layer=dict(kind='actor:Ordinary',alpha=0,path='ordinary.png',requested_map=0,source_flip=True)
        actors=[dict(metadata=layer,pixels=np.array([[-1,1]]),left=0,top=0)]
        if effect:actors.append(dict(metadata=dict(alpha=1),pixels=np.array([[15]]),left=0,top=128))
        canvas=np.zeros((224,256,3),dtype=np.uint8)
        with patch('source_static_obj_math_bound.prepare',return_value=(actors,{},canvas)), \
             patch('source_static_obj_math_bound.compose_rgb8',return_value=(canvas,{})), \
             patch('source_static_obj_math_bound.discover',return_value={'models':[{'name':'Ordinary'}]}), \
             patch('source_static_obj_math_bound.model_palettes',return_value={}), \
             patch('source_static_obj_math_bound.select_model_palette',return_value=({'rgb8':[]},0)), \
             patch('source_static_obj_math_bound.decode',return_value=(np.array([[1,2]]),np.array([[[8,0,0],[16,0,0]]]),'hash')), \
             patch('source_static_obj_math_bound.complete_math_cover',return_value=({(mode,15,0):[15]for mode in MODES},{})), \
             patch('source_static_obj_math_bound.lower_bound',return_value={'status':'TEST_BOUND'}) as bound:
            result=measure(SimpleNamespace(index={}), 'stage', {},scanline_interval=[125,139])
        return result,bound

    def test_static_words_use_flipped_visible_source_pixels(self):
        result,bound=self.run_fixture()
        self.assertEqual(result['reserved_visible_source_words'],[1])
        self.assertEqual(result['ordinary_actors'][0]['whole_frame_raw_words'],2)
        self.assertEqual(result['status'],'NO_NONBYPASSED_EFFECT_PIXELS')
        bound.assert_not_called()

    def test_hardware_window_bound_pins_raw_ordinary_words(self):
        result,bound=self.run_fixture(effect=True)
        self.assertEqual(bound.call_args.kwargs['reserved_normal_colors'],{1})
        self.assertEqual(bound.call_args.kwargs['window_pixels'][128][0]['output'],15)
        self.assertTrue(result['outside_interval_demand_relaxed'])
        self.assertFalse(result['universal_raster_rejected'])


if __name__=='__main__':unittest.main()
