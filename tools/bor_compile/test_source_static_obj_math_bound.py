import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
from source_static_obj_math_bound import measure
from raster_obj_math_cover import MODES


class StaticObjBoundTests(unittest.TestCase):
    def test_integer_controls_only_does_not_enable_integer_palette_admission(self):
        result,bound=self.run_fixture(effect=True,integer_controls_only=True,control_write_budget=22)
        self.assertTrue(bound.call_args.kwargs['integer_modes'])
        self.assertTrue(bound.call_args.kwargs['integer_windows'])
        self.assertEqual(bound.call_args.kwargs['write_budget'],22)
        self.assertFalse(bound.call_args.kwargs.get('integer_palette',False))
        self.assertNotIn('source_control_candidate',result)
        for options in (dict(integer_controls_only=1),dict(integer_controls_only=True,integer_pool_budget=22),dict(control_write_budget=22)):
            with self.assertRaisesRegex(ValueError,'INTEGER_CONTROL_POLICY'):
                measure(None,None,{},**options)

    def test_relaxed_controls_keep_static_ordinary_words_on_every_effect_row(self):
        from source_static_obj_math_bound import MODES
        layer=dict(kind='actor:Ordinary',alpha=0,path='ordinary.png',requested_map=0,source_flip=False)
        actors=[dict(metadata=layer,pixels=np.array([[1]]),left=0,top=0),
                dict(metadata=dict(alpha=1),pixels=np.array([[2],[-1],[3]]),left=0,top=10)]
        canvas=np.zeros((224,256,3),dtype=np.uint8)
        with patch('source_static_obj_math_bound.prepare',return_value=(actors,{},canvas)),patch('source_static_obj_math_bound.compose_rgb8',return_value=(canvas,{})),patch('source_static_obj_math_bound.discover',return_value={'models':[{'name':'Ordinary'}]}),patch('source_static_obj_math_bound.model_palettes',return_value={}),patch('source_static_obj_math_bound.select_model_palette',return_value=({'rgb8':[]},0)),patch('source_static_obj_math_bound.decode',return_value=(np.array([[1]]),np.array([[[8,0,0]]]),'hash')),patch('source_static_obj_math_bound.cover_lower_bound',return_value=dict(status='TEST_RELAXATION'))as bound:
            result=measure(SimpleNamespace(index={}),None,{},relax_per_pixel_controls=True)
        rows=bound.call_args.args[0]
        self.assertTrue(all((1,())in rows[y]for y in range(10,13)))
        self.assertEqual(rows[0],set())
        self.assertEqual(result['reserved_visible_source_words'],[1])
        self.assertTrue(result['ordinary_palette_reservation_enforced_through_effect_interval'])

    def test_fractional_weights_guide_controls_without_importing_a_palette(self):
        canvas=np.zeros((224,256,3),dtype=np.uint8);expected=canvas.copy();expected[1,0,0]=16
        actors=[dict(metadata=dict(alpha=1),pixels=np.array([[2]]),left=0,top=1)]
        fractional=dict(status='TEST_RELAXATION',fractional_residency=[dict(kind=1,color=4,line=1,value=1.)])
        with patch('source_static_obj_math_bound.prepare',return_value=(actors,{},expected)),patch('source_static_obj_math_bound.compose_rgb8',return_value=(canvas,{})),patch('source_static_obj_math_bound.discover',return_value={'models':[]}),patch('source_static_obj_math_bound.cover_lower_bound',return_value=fractional):
            result=measure(SimpleNamespace(index={}),None,{},relax_per_pixel_controls=True)
        guide=result['fractional_control_guide']
        self.assertEqual(guide['selected_modes'],{1:'half-add'})
        self.assertEqual(guide['selected_window_eligibility'],{1:{0:1}})
        self.assertFalse(guide['fractional_palette_imported'])
        self.assertFalse(guide['pixel_coverage_admitted'])

    def test_per_pixel_control_relaxation_is_only_a_necessary_capacity_bound(self):
        canvas=np.zeros((224,256,3),dtype=np.uint8);expected=canvas.copy();expected[1,0,0]=16
        actors=[dict(metadata=dict(alpha=1),pixels=np.array([[2]]),left=0,top=1)]
        with patch('source_static_obj_math_bound.prepare',return_value=(actors,{},expected)),patch('source_static_obj_math_bound.compose_rgb8',return_value=(canvas,{})),patch('source_static_obj_math_bound.discover',return_value={'models':[]}),patch('source_static_obj_math_bound.cover_lower_bound',return_value=dict(status='TEST_RELAXATION'))as bound:
            result=measure(SimpleNamespace(index={}),None,{},relax_per_pixel_controls=True)
        self.assertTrue(result['global_scanline_math_mode_relaxed'])
        self.assertTrue(result['window_gate_relaxed_per_pixel'])
        self.assertFalse(result['palette_bank_assignment_proven'])
        self.assertEqual(bound.call_args.kwargs['capacities'],(60,60))
        self.assertIn(2,next(iter(bound.call_args.args[0][1]))[1])
        self.assertEqual(result['effect_cache_interval'],[1,1])
        self.assertEqual(bound.call_args.args[0][0],set())
        self.assertEqual(bound.call_args.args[0][2],set())
        with self.assertRaisesRegex(ValueError,'RELAXED_CONTROL_POLICY'):
            measure(None,None,{},relax_per_pixel_controls=True,integer_pool_budget=22)

    def run_fixture(self,effect=False,ordinary_residency='static',scanline_interval=(125,139),integer_bound=None,ordinary_top=0,hardware_windows=True,background_red=0,allowed_modes=MODES,all_visible_actor_pixels_reencodable=False,integer_pool_hint=None,integer_controls_hint=None,integer_controls_only=False,control_write_budget=None):
        layer=dict(kind='actor:Ordinary',alpha=0,path='ordinary.png',requested_map=0,source_flip=True)
        actors=[dict(metadata=layer,pixels=np.array([[-1,1]]),left=0,top=ordinary_top)]
        if effect:actors.append(dict(metadata=dict(alpha=1),pixels=np.array([[15]]),left=0,top=128))
        canvas=np.zeros((224,256,3),dtype=np.uint8)
        background=canvas.copy();background[:,:,0]=background_red
        with patch('source_static_obj_math_bound.prepare',return_value=(actors,{},canvas)), \
             patch('source_static_obj_math_bound.compose_rgb8',return_value=(background,{})), \
             patch('source_static_obj_math_bound.discover',return_value={'models':[{'name':'Ordinary'}]}), \
             patch('source_static_obj_math_bound.model_palettes',return_value={}), \
             patch('source_static_obj_math_bound.select_model_palette',return_value=({'rgb8':[]},0)), \
             patch('source_static_obj_math_bound.decode',return_value=(np.array([[1,2]]),np.array([[[8,0,0],[16,0,0]]]),'hash')), \
             patch('source_static_obj_math_bound.complete_math_cover',return_value=({(mode,out,background_red//8):[out-background_red//8]for mode in MODES for out in (1,15)},{})), \
             patch('source_static_obj_math_bound.lower_bound',return_value=integer_bound or {'status':'TEST_BOUND'}) as bound:
            result=measure(SimpleNamespace(index={}), 'stage', {},scanline_interval=scanline_interval,ordinary_residency=ordinary_residency,integer_pool_budget=21 if integer_bound else None,hardware_windows=hardware_windows,allowed_modes=allowed_modes,all_visible_actor_pixels_reencodable=all_visible_actor_pixels_reencodable,integer_pool_hint=integer_pool_hint,integer_controls_hint=integer_controls_hint,integer_controls_only=integer_controls_only,control_write_budget=control_write_budget)
        return result,bound

    def test_control_guide_does_not_import_palette_residency(self):
        guide=dict(selected_modes={'128':'add'},selected_window_eligibility={'128':{'0':1}})
        _,bound=self.run_fixture(effect=True,integer_bound={'status':'TEST_BOUND'},integer_controls_hint=guide)
        self.assertEqual(bound.call_args.kwargs['controls_hint'],guide)
        self.assertIsNone(bound.call_args.kwargs['residency_hint'])

    def test_integer_pool_hint_requires_matching_source_context(self):
        previous,_=self.run_fixture(effect=True)
        hint=dict(previous,cache_bound={'status':'SOFT_HINT'})
        result,bound=self.run_fixture(effect=True,integer_bound={'status':'TEST_BOUND'},integer_pool_hint=hint)
        self.assertEqual(bound.call_args.kwargs['residency_hint'],hint['cache_bound'])
        hint['source_rgb555_sha256']='stale'
        with self.assertRaisesRegex(ValueError,'POOL_HINT_SOURCE_IDENTITY'):
            self.run_fixture(effect=True,integer_bound={'status':'TEST_BOUND'},integer_pool_hint=hint)

    def test_all_actor_reencoding_covers_ordinary_pixels_without_literal_reservation(self):
        result,bound=self.run_fixture(effect=True,ordinary_top=128,all_visible_actor_pixels_reencodable=True)
        self.assertEqual(result['reserved_visible_source_words'],[])
        self.assertEqual({p['output']for p in bound.call_args.kwargs['window_pixels'][128]},{1,15})
        self.assertTrue(result['cross_actor_compiled_mask_ownership_required'])
        self.assertFalse(result['alpha_compatibility_policy_selected'])
        self.assertFalse(result['palette_bank_assignment_proven'])
        with self.assertRaisesRegex(ValueError,'REENCODING_POLICY'):
            measure(None,None,{},all_visible_actor_pixels_reencodable=1)

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

    def test_scanline_policy_pins_only_visible_ordinary_row_words(self):
        result,bound=self.run_fixture(effect=True,ordinary_residency='scanline',scanline_interval=(0,139))
        self.assertEqual(bound.call_args.kwargs['reserved_normal_colors'],())
        self.assertEqual(bound.call_args.kwargs['required_normal_rows'],{0:{1}})
        self.assertFalse(result['static_words_fixed_in_lower_class'])
        self.assertEqual(result['ordinary_union_word_count'],1)

    def test_serialized_integer_controls_replay_source_and_reject_stale_words(self):
        witness=dict(status='RELAXED_MODE_LIVENESS_CANDIDATE',integer_pool_pixel_coverage_verified=True,
            selected_palette_residency={'128':{'0':[1],'1':[15]}},selected_modes={'128':'add'},
            selected_window_eligibility={'128':{'0':1}},reserved_normal_colors=[1],peak_write_objective=0)
        result,_=self.run_fixture(effect=True,integer_bound=witness)
        candidate=result['source_control_candidate']
        self.assertEqual(candidate['status'],'INTEGER_POOL_SOURCE_REPLAY_PROVEN')
        self.assertEqual(candidate['checked_visible_source_pixels'],1)
        self.assertFalse(candidate['physical_transfer_admitted'])
        witness['selected_palette_residency']['128']['1']=[14]
        with self.assertRaisesRegex(AssertionError,'MODE_INTEGER_POOL_PIXEL_REPLAY'):
            self.run_fixture(effect=True,integer_bound=witness)

    def test_integer_replay_includes_ordinary_only_interval_endpoint(self):
        witness=dict(status='RELAXED_MODE_LIVENESS_CANDIDATE',integer_pool_pixel_coverage_verified=True,
            selected_palette_residency={str(y):{'0':[1],'1':[15]}for y in range(128,131)},
            selected_modes={str(y):'add'for y in range(128,131)},
            selected_window_eligibility={'128':{'0':1},'129':{},'130':{}},peak_write_objective=0)
        result,_=self.run_fixture(effect=True,ordinary_residency='scanline',scanline_interval=(128,130),integer_bound=witness,ordinary_top=130)
        self.assertEqual(result['source_control_candidate']['checked_visible_source_pixels'],2)
        self.assertEqual(set(result['source_control_candidate']['selected_modes']),{128,129,130})

    def test_no_window_policy_compiles_math_enabled_everywhere(self):
        from raster_math_windows import evaluate
        witness=dict(status='RELAXED_MODE_LIVENESS_CANDIDATE',integer_pool_pixel_coverage_verified=True,
            selected_palette_residency={'128':{'0':[1],'1':[14]}},selected_modes={'128':'add'},
            reserved_normal_colors=[1],peak_write_objective=0)
        result,_=self.run_fixture(effect=True,integer_bound=witness,hardware_windows=False,background_red=8)
        descriptor=result['source_control_candidate']['compiled_color_window_descriptors'][128]
        self.assertTrue(all(evaluate(descriptor,x)for x in range(256)))

    def test_constant_math_mode_restricts_solver_choices(self):
        result,bound=self.run_fixture(effect=True,allowed_modes=('add',))
        self.assertEqual(result['allowed_math_modes'],['add'])
        self.assertEqual(set(bound.call_args.args[0][128]),{'add'})
        with self.assertRaisesRegex(ValueError,'MATH_MODE_DOMAIN'):
            self.run_fixture(effect=True,allowed_modes=('invalid',))


if __name__=='__main__':unittest.main()
