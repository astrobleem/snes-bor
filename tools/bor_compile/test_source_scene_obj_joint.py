import unittest
from unittest.mock import patch
import numpy as np
from source_bg_feasibility import rgb555
from source_scene_obj_joint import probe,saturated_corners


class JointSceneSolverTests(unittest.TestCase):
    def test_literal_ordinary_actors_share_one_fixed_bank(self):
        background=np.zeros((224,256,3),dtype=np.uint8);expected=background.copy();actors=[]
        for i in range(2):
            pixels=np.full((8,8),-1,dtype=np.int32);pixels[0,:4]=np.arange(1+i*4,5+i*4)
            actors.append(dict(pixels=pixels,left=i*8,top=0,metadata=dict(alpha=0)))
            expected[0,i*8:i*8+4,0]=pixels[0,:4]*8
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=8,write_budget=0,time_limit=3,solver_backend='cp-sat',literal_actor_bank=2)
        self.assertTrue(result['compiled_pixel_identity_verified'])
        self.assertEqual({p['bank']for p in result['pieces']},{2})
        self.assertEqual(result['literal_alpha_zero_actor_bank'],2)
        with self.assertRaisesRegex(ValueError,'LITERAL_ACTOR_BANK_POLICY'):
            with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)):
                probe(None,None,{},literal_actor_bank=4)

    def test_subscreen_operands_use_all_banks_with_explicit_layer_requirements(self):
        # Sixty-four simultaneous residual identities need five OBJ banks.
        background=np.full((224,256,3),8,dtype=np.uint8);expected=background.copy()
        pixels=np.full((8,64),-1,dtype=np.int32)
        values=[r|g<<5|b<<10 for r in range(1,5)for g in range(1,5)for b in range(1,5)]
        pixels[0]=values
        for x,c in enumerate(values):expected[0,x]=[(c>>shift&31)*8 for shift in(0,5,10)]
        actor=dict(pixels=pixels,left=0,top=0)
        with patch('source_scene_obj_joint.prepare',return_value=([actor],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=8,write_budget=0,time_limit=10,color_math='subscreen-additive')
        self.assertTrue(result['compiled_pixel_identity_verified'])
        self.assertGreaterEqual(len({p['bank']for p in result['pieces']}),5)
        self.assertTrue(result['main_screen_obj_disabled'])
        self.assertEqual(result['main_screen_color_math_layer'],'BG1')
        self.assertFalse(result['concurrent_main_obj_layer_routing_proven'])
        self.assertFalse(result['native_layer_routing_proven'])
        darker=np.full((8,8),0,dtype=np.int32);black=background.copy();black[:8,:8]=0
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=darker,left=0,top=0)],{},black)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            rejected=probe(None,None,{},size=8,write_budget=0,time_limit=10,color_math='subscreen-additive')
        self.assertEqual(rejected['solver']['status'],2)

    def test_geometry_hint_requires_new_hardware_checked_solution(self):
        from raster_geometry_hint import construct
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((16,16),-1,dtype=np.int32);pixels[9,9]=1
        expected=background.copy();expected[53,9,0]=8
        actors=[dict(pixels=pixels,left=0,top=44)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            initial=probe(None,None,{},size=16,write_budget=1,time_limit=5,solver_backend='cp-sat')
            hint=construct(initial)
            result=probe(None,None,{},size=8,write_budget=1,time_limit=5,solver_backend='cp-sat',schedule_hint=hint,fixed_rectangles=True)
            self.assertTrue(result['input_geometry_is_search_hint'])
            self.assertTrue(result['compiled_pixel_identity_verified'])
            self.assertEqual(result['geometry']['oam_entries'],1)
            with self.assertRaisesRegex(ValueError,'GEOMETRY_SEARCH_HINT_REQUIRES_FIXED_RECTANGLES'):
                probe(None,None,{},size=8,write_budget=1,time_limit=5,solver_backend='cp-sat',schedule_hint=hint)
            locked=construct(initial)
            for p in locked['pieces']:p['allowed_banks']=[p['bank']]
            result=probe(None,None,{},size=8,write_budget=1,time_limit=5,solver_backend='cp-sat',schedule_hint=locked,fixed_rectangles=True)
            self.assertEqual([p['bank']for p in result['pieces']],[p['bank']for p in locked['pieces']])

    def test_extra_fixed_bank_mask_solves_static_lifetime_capacity(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[:2]=np.arange(1,17).reshape(2,8)
        expected=background.copy();expected[112:114,:8,0]=np.arange(1,17).reshape(2,8)*8
        actors=[dict(pixels=pixels,left=0,top=112)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            hint=probe(None,None,{},size=8,write_budget=8,time_limit=5,solver_backend='cp-sat')
            self.assertEqual(hint['geometry']['oam_entries'],1)
            kwargs=dict(size=8,write_budget=0,time_limit=5,solver_backend='cp-sat',schedule_hint=hint,fixed_rectangles=True,
                preserve_hint_math_classes=True,preserve_hint_words=True,collapse_inactive_prefix=True,maximum_banks_per_piece_class=2)
            failed=probe(None,None,{},**kwargs)
            result=probe(None,None,{},rectangle_bank_slack=1,**kwargs)
        self.assertEqual(failed['solver']['status'],2)
        self.assertTrue(result['compiled_pixel_identity_verified'])
        self.assertEqual(result['geometry']['oam_entries'],2)
        self.assertEqual(result['peak_scheduled_writes'],0)
        self.assertEqual(result['additional_bank_masks_per_hint_rectangle'],1)
        self.assertFalse(result['native_presentation_proven'])
        for slack in(-1,8,True):
            with self.assertRaisesRegex(ValueError,'RECTANGLE_BANK_SLACK_DOMAIN'):probe(None,None,{},rectangle_bank_slack=slack)

    def test_general_empty_prefix_can_hold_first_visible_palette(self):
        from raster_slot_greedy import demand
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[0,0]=1;pixels[2,0]=2
        expected=background.copy();expected[112,0,0]=8;expected[114,0,0]=16
        actors=[dict(pixels=pixels,left=0,top=112)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            full=probe(None,None,{},size=8,write_budget=0,lookahead=55,time_limit=5,solver_backend='cp-sat')
            collapsed=probe(None,None,{},size=8,write_budget=0,lookahead=55,time_limit=5,solver_backend='cp-sat',collapse_inactive_prefix=True)
        self.assertTrue(collapsed['compiled_pixel_identity_verified'])
        self.assertEqual(sum(r['colors_written']for r in collapsed['trace'][1:113]),0)
        self.assertLess(collapsed['solver']['variables'],full['solver']['variables'])
        for a,b in zip(demand(full)[2],demand(collapsed)[2]):np.testing.assert_array_equal(a,b)

    def test_fixed_subdivided_hint_uses_actual_source_rectangles(self):
        import copy
        from raster_bank_rebalance import subdivide
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((16,16),-1,dtype=np.int32);pixels[9,9]=1
        expected=background.copy();expected[53,9,0]=8
        actors=[dict(pixels=pixels,left=0,top=44)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            initial=probe(None,None,{},size=16,write_budget=1,time_limit=5,solver_backend='cp-sat')
            hint=subdivide(initial,[0])
            result=probe(None,None,{},size='mixed',mixed_small_size=8,mixed_large_size=16,write_budget=1,time_limit=5,solver_backend='cp-sat',schedule_hint=hint,fixed_geometry=True,preserve_hint_math_classes=True,preserve_hint_words=True)
            self.assertTrue(result['compiled_pixel_identity_verified'])
            self.assertEqual(result['geometry']['oam_entries'],1)
            self.assertEqual((result['pieces'][0]['local_x'],result['pieces'][0]['local_y']),(8,8))
            bad=copy.deepcopy(hint);bad['pieces'][0]['x']+=1
            with self.assertRaisesRegex(ValueError,'JOINT_HINT_SOURCE_COORDINATES'):
                probe(None,None,{},size='mixed',mixed_small_size=8,mixed_large_size=16,write_budget=1,time_limit=5,solver_backend='cp-sat',schedule_hint=bad,fixed_geometry=True)
            bad=copy.deepcopy(hint);bad['piece_pixel_masks'][0]['pixels_hex']='00'*32
            with self.assertRaisesRegex(ValueError,'JOINT_HINT_SOURCE_PIXEL_COVERAGE'):
                probe(None,None,{},size='mixed',mixed_small_size=8,mixed_large_size=16,write_budget=1,time_limit=5,solver_backend='cp-sat',schedule_hint=bad,fixed_geometry=True)

    def test_unused_pool_gap_and_actor_free_prefix_allow_real_retention(self):
        import hashlib
        from raster_math_windows import compile_mask
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[3,0]=pixels[5,0]=1
        expected=background.copy();expected[3,0,0]=expected[5,0,0]=8
        candidate=dict(status='INTEGER_POOL_SOURCE_REPLAY_PROVEN',metadata={},
            source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
            full_interval_source_pixels_verified=True,zero_main_clipping_palette_demand_relaxed=False,
            selected_modes={str(y):'add'for y in range(3,6)},
            compiled_color_window_descriptors={str(y):compile_mask([True]*256)for y in range(3,6)},
            selected_palette_residency={str(y):{'0':[],'1':[1]if y!=4 else[]}for y in range(3,6)})
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=8,write_budget=0,time_limit=10,solver_backend='cp-sat',
                scanline_math_candidate=candidate,pin_scanline_pool_intervals=True,
                pool_interval_initial_preload=True,pool_interval_max_lines=1,pool_interval_gap_bridge_lines=1,collapse_inactive_prefix=True)
        self.assertTrue(result['compiled_pixel_identity_verified'])
        self.assertEqual(result['trace'][0]['colors_written'],1)
        self.assertEqual(result['peak_scheduled_writes'],0)
        self.assertTrue(result['collapse_inactive_prefix'])

    def test_future_interval_can_load_late_when_initial_bank_is_full(self):
        import hashlib
        from raster_math_windows import compile_mask
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,16),-1,dtype=np.int32);pixels[0,:15]=np.arange(1,16);pixels[1,0]=16
        expected=background.copy();expected[0,:15,0]=np.arange(1,16)*8;expected[1,0,0]=128
        candidate=dict(status='INTEGER_POOL_SOURCE_REPLAY_PROVEN',metadata={},
            source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
            full_interval_source_pixels_verified=True,zero_main_clipping_palette_demand_relaxed=False,
            selected_modes={'0':'add','1':'add'},
            compiled_color_window_descriptors={str(y):compile_mask([True]*256)for y in range(2)},
            selected_palette_residency={'0':{'0':[],'1':list(range(1,16))},'1':{'0':[],'1':[16]}})
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            hint=probe(None,None,{},size=16,write_budget=1,time_limit=10,solver_backend='cp-sat',additive_only=True)
            result=probe(None,None,{},size=16,write_budget=1,time_limit=10,solver_backend='cp-sat',
                schedule_hint=hint,fixed_geometry=True,preserve_hint_math_classes=True,preserve_hint_words=True,
                scanline_math_candidate=candidate,pin_scanline_pool_intervals=True,
                pool_interval_initial_preload=True,pool_interval_max_lines=1)
        self.assertTrue(result['compiled_pixel_identity_verified'])
        self.assertEqual(result['geometry']['oam_entries'],1)
        self.assertEqual(result['trace'][0]['colors_written'],15)
        self.assertEqual(result['trace'][1]['colors_written'],1)
        self.assertEqual(result['trace'][1]['updates'][0]['color'],16)

    def test_future_pool_interval_initial_preload_counts_occupied_prefix(self):
        import hashlib
        from raster_math_windows import compile_mask
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[1:3,0]=[1,2]
        expected=background.copy();expected[1:3,0,0]=[8,16]
        candidate=dict(status='INTEGER_POOL_SOURCE_REPLAY_PROVEN',metadata={},
            source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
            full_interval_source_pixels_verified=True,zero_main_clipping_palette_demand_relaxed=False,
            selected_modes={str(y):'add'for y in range(3)},
            compiled_color_window_descriptors={str(y):compile_mask([True]*256)for y in range(3)},
            selected_palette_residency={str(y):{'0':[],'1':[y]if y else[]}for y in range(3)})
        for preload in (False,True):
            with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                result=probe(None,None,{},size=8,write_budget=0,time_limit=10,solver_backend='cp-sat',
                    scanline_math_candidate=candidate,pin_scanline_pool_intervals=True,pool_interval_initial_preload=preload)
            if not preload:self.assertEqual(result['solver']['message'],'INFEASIBLE')
            else:
                self.assertTrue(result['compiled_pixel_identity_verified'])
                self.assertEqual(result['trace'][0]['colors_written'],2)
                self.assertEqual(result['peak_scheduled_writes'],0)
                self.assertTrue(result['initial_palette_may_preload_entire_frame'])

    def test_fixed_rectangle_search_can_preserve_words_and_math_classes(self):
        from raster_slot_greedy import demand
        background=np.zeros((224,256,3),dtype=np.uint8);background[:8,:16,0]=32
        pixels=np.full((8,16),6,dtype=np.int32);expected=background.copy();expected[:8,:16,0]=48
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            hint=probe(None,None,{},size=8,write_budget=0,time_limit=10,solver_backend='cp-sat',additive_only=True)
            result=probe(None,None,{},size=8,write_budget=0,time_limit=10,solver_backend='cp-sat',
                schedule_hint=hint,fixed_rectangles=True,preserve_hint_math_classes=True,preserve_hint_words=True,bank_symmetry=True,maximum_banks_per_piece_class=1)
        self.assertTrue(result['compiled_pixel_identity_verified'])
        self.assertTrue(result['preserve_hint_words'])
        self.assertTrue(result['fixed_single_bank_word_ownership_factored'])
        self.assertTrue(all(p['bank']>=4 for p in result['pieces']))
        _,_,a=demand(hint);_,_,b=demand(result)
        for old,new in zip(a,b):np.testing.assert_array_equal(old,new)
        with self.assertRaisesRegex(ValueError,'PRESERVED_HINT_POLICY'):probe(None,None,{},preserve_hint_words=True)

    def test_shared_parent_math_choices_coalesce_with_exact_source_replay(self):
        background=np.zeros((224,256,3),dtype=np.uint8);background[:8,:16,0]=32
        pixels=np.full((8,16),6,dtype=np.int32);expected=background.copy();expected[:8,:16,0]=48
        results=[]
        for coalesce in (False,True):
            with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                result=probe(None,None,{},size='mixed',write_budget=0,time_limit=10,solver_backend='cp-sat',additive_only=True,coalesce_math_choices=coalesce)
            self.assertTrue(result['compiled_pixel_identity_verified'])
            self.assertEqual(result['geometry']['oam_entries'],1)
            self.assertEqual(result['independent_actor_peak_tile_lower_bound'],2)
            results.append(result)
        self.assertLess(results[1]['distinct_math_choice_variables'],results[1]['math_choice_entries'])
        self.assertEqual(results[0]['math_choice_entries'],results[1]['math_choice_entries'])
        self.assertEqual(results[0]['source_rgb555_sha256'],results[1]['source_rgb555_sha256'])

    def test_saved_pool_intervals_use_one_fixed_bank_and_replay_exactly(self):
        import hashlib
        from raster_math_windows import compile_mask
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[:3,0]=[1,2,1]
        expected=background.copy();expected[:3,0,0]=[8,16,8]
        candidate=dict(status='INTEGER_POOL_SOURCE_REPLAY_PROVEN',metadata={},
            source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
            full_interval_source_pixels_verified=True,zero_main_clipping_palette_demand_relaxed=False,
            selected_modes={str(y):'add'for y in range(3)},
            compiled_color_window_descriptors={str(y):compile_mask([True]*256)for y in range(3)},
            selected_palette_residency={str(y):{'0':[],'1':[1,2]}for y in range(3)})
        for backend in ('cp-sat','highs'):
            with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                result=probe(None,None,{},size=8,write_budget=0,time_limit=10,solver_backend=backend,
                    additive_only=True,scanline_math_candidate=candidate,pin_scanline_pool_intervals=True)
            self.assertTrue(result['compiled_pixel_identity_verified'])
            self.assertTrue(result['scanline_pool_intervals_single_bank_restricted'])
            self.assertEqual(result['peak_scheduled_writes'],0)
            self.assertEqual(result['geometry']['oam_entries'],1)
            self.assertEqual(result['scanline_pool_interval_variables'],8)
        with self.assertRaisesRegex(ValueError,'JOINT_SCANLINE_INTERVAL_POLICY'):
            probe(None,None,{},pin_scanline_pool_intervals=True)

    def test_interval_bank_copies_are_charged_and_preserve_fixed_rectangles(self):
        import hashlib
        from raster_math_windows import compile_mask
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,24),-1,dtype=np.int32)
        for i in range(3):pixels[0,i*8:(i+1)*8]=[1]+list(range(2+7*i,9+7*i))
        expected=background.copy();expected[0,:24,0]=(pixels[0]*8).astype(np.uint8)
        candidate=dict(status='INTEGER_POOL_SOURCE_REPLAY_PROVEN',metadata={},
            source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
            full_interval_source_pixels_verified=True,zero_main_clipping_palette_demand_relaxed=False,
            selected_modes={'0':'add'},compiled_color_window_descriptors={'0':compile_mask([True]*256)},
            selected_palette_residency={'0':{'0':[],'1':list(range(1,23))}})
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            hint=probe(None,None,{},size=8,write_budget=0,time_limit=10,solver_backend='cp-sat')
            for copies in (1,2):
                result=probe(None,None,{},size=8,write_budget=0,time_limit=10,solver_backend='cp-sat',
                    scanline_math_candidate=candidate,pin_scanline_pool_intervals=True,
                    pool_interval_bank_copies=copies,schedule_hint=hint,fixed_rectangles=True)
                if copies==1:self.assertEqual(result['solver']['message'],'INFEASIBLE')
                else:
                    self.assertTrue(result['compiled_pixel_identity_verified'])
                    self.assertEqual(result['geometry']['oam_entries'],3)
                    self.assertEqual(sum(e['color']==1 for e in result['trace'][0]['updates']),2)

    def test_interval_chunk_retention_counts_only_new_bank_copies(self):
        import hashlib
        from raster_math_windows import compile_mask
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,24),-1,dtype=np.int32)
        for i in range(3):pixels[1:4,i*8:(i+1)*8]=[1]+list(range(2+7*i,9+7*i))
        expected=background.copy();expected[1:4,:24,0]=(pixels[1:4]*8).astype(np.uint8)
        candidate=dict(status='INTEGER_POOL_SOURCE_REPLAY_PROVEN',metadata={},
            source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
            full_interval_source_pixels_verified=True,zero_main_clipping_palette_demand_relaxed=False,
            selected_modes={str(y):'add'for y in range(4)},
            compiled_color_window_descriptors={str(y):compile_mask([True]*256)for y in range(4)},
            selected_palette_residency={str(y):{'0':[],'1':list(range(1,23))if y else[]}for y in range(4)})
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            hint=probe(None,None,{},size=8,write_budget=0,time_limit=10,solver_backend='cp-sat')
            for budget in (22,23):
                result=probe(None,None,{},size=8,write_budget=budget,lookahead=0,time_limit=10,solver_backend='cp-sat',
                    scanline_math_candidate=candidate,pin_scanline_pool_intervals=True,pool_interval_max_lines=1,
                    pool_interval_bank_copies=2,schedule_hint=hint,fixed_rectangles=True)
                if budget==22:self.assertEqual(result['solver']['message'],'INFEASIBLE')
                else:
                    self.assertTrue(result['compiled_pixel_identity_verified'])
                    self.assertEqual(result['peak_scheduled_writes'],23)
                    self.assertEqual([r['colors_written']for r in result['trace'][:4]],[0,23,0,0])

    def test_piece_class_mask_cap_is_an_explicit_construction_restriction(self):
        pixels=np.arange(16,dtype=np.int32).reshape(2,8)
        background=np.zeros((224,256,3),dtype=np.uint8);expected=background.copy();expected[:2,:8,0]=(pixels*8).astype(np.uint8)
        for cap in (1,2):
            with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                result=probe(None,None,{},size=8,write_budget=0,time_limit=10,solver_backend='cp-sat',
                    color_math='precomposited',maximum_banks_per_piece_class=cap)
            self.assertEqual(result['maximum_banks_per_piece_class'],cap)
            if cap==1:self.assertEqual(result['solver']['message'],'INFEASIBLE')
            else:self.assertTrue(result['compiled_pixel_identity_verified'])

    def test_row_capacity_search_replays_eviction_and_later_reuse(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[:3,0]=[1,2,1]
        expected=background.copy();expected[:3,0,0]=[8,16,8]
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=8,write_budget=120,lookahead=0,row_capacity_only=True,time_limit=10,color_math='precomposited',solver_backend='cp-sat')
        self.assertTrue(result['compiled_pixel_identity_verified'])
        self.assertTrue(result['palette_transfer_budget_relaxed'])
        self.assertEqual(result['geometry']['oam_entries'],1)
        for args in (dict(write_budget=22,lookahead=0),dict(write_budget=120,lookahead=1)):
            with self.assertRaisesRegex(ValueError,'JOINT_ROW_CAPACITY_ONLY_REQUIRES'):
                probe(None,None,{},row_capacity_only=True,**args)

    def test_scanline_controls_preserve_fixed_upper_bank_across_modes_and_window(self):
        import hashlib
        from raster_math_windows import compile_mask
        background=np.zeros((224,256,3),dtype=np.uint8)
        background[0,:3,0]=[32,64,32];background[1:3,0,0]=32
        pixels=np.full((8,8),-1,dtype=np.int32)
        pixels[0,:3]=2;pixels[1,0]=4;pixels[2,0]=5
        expected=background.copy();expected[0,:3,0]=16;expected[1,0,0]=32;expected[2,0,0]=40
        candidate=dict(status='INTEGER_POOL_SOURCE_REPLAY_PROVEN',metadata={},
            source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),
            full_interval_source_pixels_verified=True,zero_main_clipping_palette_demand_relaxed=False,
            selected_modes={'0':'subtract','1':'half-add'},
            compiled_color_window_descriptors={'0':compile_mask([x<2 for x in range(256)]),'1':compile_mask([True]*256)},
            selected_palette_residency={'0':{'0':[],'1':[2,6,10]},'1':{'0':[],'1':[4]}})
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=8,write_budget=4,time_limit=10,solver_backend='cp-sat',additive_only=True,scanline_math_candidate=candidate)
        self.assertTrue(result['compiled_pixel_identity_verified'])
        self.assertEqual(result['geometry']['oam_entries'],1)
        self.assertGreaterEqual(result['pieces'][0]['bank'],4)
        self.assertEqual(result['selected_modes'][0],'subtract')
        self.assertEqual(result['selected_modes'][1],'half-add')
        self.assertEqual(result['selected_modes'][2],'add')
        self.assertFalse(result['window_register_schedule_proven'])
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            hinted=probe(None,None,{},size=8,write_budget=4,time_limit=10,solver_backend='cp-sat',additive_only=True,scanline_math_candidate=candidate,schedule_hint=result,fixed_geometry=True)
        self.assertTrue(hinted['compiled_pixel_identity_verified'])
        self.assertTrue(hinted['fixed_geometry_and_pixel_bank_ownership'])
        self.assertGreater(hinted['solver']['boolean_stats']['hint_variables'],0)
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            literal_hint=probe(None,None,{},size=8,write_budget=4,time_limit=10,solver_backend='cp-sat')
            moved=probe(None,None,{},size=8,write_budget=4,time_limit=10,solver_backend='cp-sat',additive_only=True,scanline_math_candidate=candidate,schedule_hint=literal_hint,fixed_rectangles=True)
        self.assertLess(literal_hint['pieces'][0]['bank'],4)
        self.assertGreaterEqual(moved['pieces'][0]['bank'],4)
        self.assertEqual(moved['geometry']['oam_entries'],1)
        self.assertTrue(moved['compiled_pixel_identity_verified'])
        self.assertTrue(moved['fixed_rectangles_and_pixel_rectangle_ownership'])
        candidate['selected_palette_residency']['0']['1'].remove(10)
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            with self.assertRaisesRegex(ValueError,'JOINT_SCANLINE_CONTROL_SOURCE_PIXEL_COVERAGE'):
                probe(None,None,{},size=8,write_budget=4,time_limit=10,solver_backend='cp-sat',additive_only=True,scanline_math_candidate=candidate)

    def test_scanline_controls_reject_foreign_source_and_clipping_relaxation(self):
        from source_scene_obj_joint import scanline_controls
        for candidate in ({},dict(status='INTEGER_POOL_SOURCE_REPLAY_PROVEN',metadata={},source_rgb555_sha256='x',full_interval_source_pixels_verified=True,zero_main_clipping_palette_demand_relaxed=True)):
            with self.assertRaisesRegex(ValueError,'JOINT_SCANLINE_CONTROL_SOURCE_IDENTITY'):
                scanline_controls(candidate,{},'x',224)

    def test_distinct_frame_color_cap_balances_exact_words_including_black(self):
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[:2]=np.arange(16).reshape(2,8)
        background=np.zeros((224,256,3),dtype=np.uint8);expected=background.copy()
        expected[:2,:8,0]=np.arange(16).reshape(2,8)*8
        for cap,success in ((1,False),(2,True)):
            with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                result=probe(None,None,{},size=8,write_budget=0,lookahead=0,time_limit=10,
                    color_math='precomposited',solver_backend='cp-sat',maximum_frame_colors_per_bank=cap)
            self.assertEqual(result['status']=='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',success)
            if success:
                self.assertTrue(result['compiled_pixel_identity_verified'])
                colors=[{e['color']for row in result['trace']for e in row['updates']if e['bank']==b}for b in range(8)]
                self.assertEqual(set().union(*colors),set(range(16)))
                self.assertTrue(all(len(c)<=2 for c in colors))

    def test_initial_preload_occupies_capacity_until_first_prefetch_row(self):
        import hashlib,copy
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.full((16,16),-1,dtype=np.int32);pixels[0,0]=0;pixels[1,:15]=np.arange(15);pixels[12,0]=15
        expected=background.copy()
        for y,x in zip(*np.where(pixels>=0)):
            c=int(pixels[y,x]);expected[y,x]=[(c>>s&31)*8 for s in(0,5,10)]
        state={b:[None]*15 for b in range(8)};trace=[]
        for y in range(224):
            before=copy.deepcopy(state);events=[]
            for slot,c in (list(enumerate(range(15),1))if y==0 else[(1,15)]if y==12 else[]):
                events.append(dict(bank=0,slot=slot,old=state[0][slot-1],color=c));state[0][slot-1]=c
            trace.append(dict(scanline=y,resident_before=before,updates=events))
        image=np.zeros((16,16),dtype=np.uint8);image[0,0]=1;image[1,:15]=np.arange(1,16);image[12,0]=1;flat=image.flatten()
        hint=dict(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',compiled_pixel_identity_verified=True,color_math='precomposited',metadata={},
            source_rgb555_sha256=hashlib.sha256(rgb555(expected).astype('<u2').tobytes()).hexdigest(),trace=trace,
            pieces=[dict(actor=0,local_x=0,local_y=0,x=0,y=0,width=16,height=16,bank=0)],
            piece_pixel_masks=[dict(width=16,height=16,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex())])
        for lookahead,success in ((0,False),(1,True)):
            with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                result=probe(None,None,{},size=16,write_budget=0,early_write_budget=1,late_start=12,lookahead=lookahead,time_limit=10,
                    color_math='precomposited',solver_backend='cp-sat',schedule_hint=hint,fixed_geometry=True,feasibility_only=True)
            self.assertEqual(result['solver']['status']==0,success)
            self.assertTrue(result['initial_preload_prefix_capacity_modeled'])
            if success:self.assertTrue(result['compiled_pixel_identity_verified'])

    def test_fixed_geometry_keeps_split_atom_pixel_bank_ownership(self):
        import copy
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,8),31,dtype=np.int32);expected=background.copy();expected[:8,:8,0]=248
        actors=[dict(pixels=pixels,left=0,top=0)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            hint=probe(None,None,{},size=8,write_budget=0,time_limit=10,color_math='precomposited',solver_backend='cp-sat')
            p=hint['pieces'][0];p['bank']=0
            hint['pieces']=[p,dict(p,bank=1)];hint['piece_pixel_masks']=[]
            for begin,end in ((0,4),(4,8)):
                image=np.zeros((8,8),dtype=np.uint8);image[:,begin:end]=1;flat=image.flatten()
                hint['piece_pixel_masks'].append(dict(width=8,height=8,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
            hint['trace'][0]['updates']=[dict(bank=b,slot=1,color=31)for b in(0,1)]
            result=probe(None,None,{},size=8,write_budget=0,time_limit=10,color_math='precomposited',solver_backend='cp-sat',schedule_hint=hint,fixed_geometry=True)
        self.assertTrue(result['compiled_pixel_identity_verified'])
        self.assertTrue(result['fixed_geometry_and_pixel_bank_ownership'])
        self.assertEqual({p['bank']for p in result['pieces']},{0,1})
        from raster_obj_compact import unpack
        for piece,mask in zip(result['pieces'],result['piece_pixel_masks']):
            image=unpack(mask);self.assertEqual(np.count_nonzero(image),32)
            self.assertTrue(np.all(image[:,4:] == 0)if piece['bank']==0 else np.all(image[:,:4] == 0))

    def test_fixed_geometry_requires_identity_hint(self):
        with self.assertRaisesRegex(ValueError,'JOINT_FIXED_GEOMETRY_REQUIRES_HINT'):probe(None,None,{},fixed_geometry=True)

    def test_additive_only_reserves_normal_banks_and_preserves_pixels(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,8),31,dtype=np.int32);expected=background.copy();expected[:8,:8,0]=248
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=8,write_budget=0,time_limit=10,additive_only=True)
        self.assertTrue(r['compiled_pixel_identity_verified']);self.assertEqual(r['opaque_obj_banks_reserved'],4)
        self.assertTrue(all(p['bank']>=4 for p in r['pieces']))
        self.assertTrue(all(e['bank']>=4 for row in r['trace']for e in row['updates']))

    def test_pool_reports_required_final_output_color_identity_counts(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,8),31,dtype=np.int32);pixels[1,1]=0
        expected=background.copy();expected[:8,:8,0]=248;expected[1,1,0]=0
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=8,pool_only=True,time_limit=10,underlay_bypass=True)
        self.assertEqual(r['visible_final_obj_output_full_frame_colors'],1)
        self.assertEqual(r['peak_visible_final_obj_output_colors_per_scanline'],1)
        self.assertTrue(r['final_output_counts_apply_source_alpha_and_occlusion'])
        self.assertTrue(r['final_output_counts_exclude_exact_underlay_bypass_pixels'])
        self.assertEqual(r['underlay_bypassed_pixels'],1)

    def test_other_math_modes_are_explicit_pool_relaxation_only(self):
        with self.assertRaisesRegex(ValueError,'JOINT_MATH_MODES_REQUIRE_RELAXED_POOL_ONLY'):
            probe(None,None,{},pool_math_modes=('half-add',))
        background=np.zeros((224,256,3),dtype=np.uint8);background[:8,:8,0]=8
        pixels=np.full((8,8),16,dtype=np.int32);expected=background.copy();expected[:8,:8,0]=128
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=8,pool_only=True,pool_math_modes=('half-add',),time_limit=10)
        self.assertEqual(r['color_math'],'RELAXED_POOL_MATH_MODES')
        self.assertAlmostEqual(r['validated_dual_lower_bound'],0)
        self.assertFalse(r['global_math_mode_constraints_relaxed'])
        self.assertFalse(r['schedule_proven'])

    def test_additive_only_cannot_silently_approximate_darker_output(self):
        background=np.zeros((224,256,3),dtype=np.uint8);background[:,:,0]=248
        expected=background.copy();expected[:8,:8,0]=240;pixels=np.full((8,8),30,dtype=np.int32)
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=8,write_budget=0,time_limit=10,additive_only=True)
        self.assertEqual(r['solver']['status'],2);self.assertFalse(r['native_presentation_proven'])

    def test_pool_prefetch_obeys_actual_pixel_use_lookahead(self):
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.full((8,64),-1,dtype=np.int32);pixels[0,:60]=np.arange(1,61);pixels[2,0]=0
        expected=background.copy()
        for y,x in zip(*np.where(pixels>=0)):
            c=int(pixels[y,x]);expected[y+44,x]=[(c>>s&31)*8 for s in (0,5,10)]
        actors=[dict(pixels=pixels,left=0,top=44)]
        entries=[dict(kind=0,color=c,line=44,value=1)for c in range(1,61)]+[dict(kind=0,color=0,line=y,value=1)for y in (45,46)]
        pool=dict(status='POOLED_INTEGER_RESIDENCY_CANDIDATE',metadata={},fractional_residency=entries)
        for lead,expected_status in ((0,2),(1,0)):
            with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                r=probe(None,None,{},size=8,write_budget=0,early_write_budget=1,late_start=46,lookahead=lead,time_limit=10,pool_residency=pool,bank_symmetry=True,feasibility_only=True)
            self.assertEqual(r['solver']['status'],expected_status)
            if lead:
                self.assertTrue(r['compiled_pixel_identity_verified']);self.assertTrue(r['noninitial_prefetch_lookahead_enforced'])
                self.assertEqual(r['maximum_noninitial_prefetch_latency_lines'],1)
                self.assertTrue(r['noninitial_prefetch_latency_replayed'])

    def test_mixed_sixteen_small_geometry_is_a_legal_global_pair(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((16,16),31,dtype=np.int32);expected=background.copy();expected[:16,:16,0]=248
        actors=[dict(pixels=pixels,left=0,top=0)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size='mixed',mixed_small_size=16,write_budget=0,time_limit=10,color_math='precomposited',coalesce_opaque_choices=True)
        self.assertTrue(r['compiled_pixel_identity_verified'])
        self.assertEqual(r['mixed_small_size'],16)
        self.assertTrue(all(p['width']in(16,32)for p in r['pieces']))
        with self.assertRaisesRegex(ValueError,'MIXED_SMALL_SIZE_DOMAIN'):probe(None,None,{},mixed_small_size=12)
        with self.assertRaisesRegex(ValueError,'MIXED_SIZE_PAIR_DOMAIN'):probe(None,None,{},mixed_small_size=16,mixed_large_size=16)
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size='mixed',mixed_large_size=16,write_budget=0,time_limit=10,color_math='precomposited',coalesce_opaque_choices=True)
        self.assertTrue(r['compiled_pixel_identity_verified'])
        self.assertTrue(all(p['width']in(8,16)for p in r['pieces']))

    def test_precomposited_context_can_use_all_eight_opaque_banks(self):
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.full((8,120),-1,dtype=np.int32);pixels[0]=np.arange(120)
        expected=background.copy()
        expected[0,:120]=np.stack([(pixels[0]>>shift)&31 for shift in (0,5,10)],axis=-1)*8
        actors=[dict(pixels=pixels,left=0,top=0)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=8,write_budget=0,time_limit=10,color_math='precomposited',bank_symmetry=True,coalesce_opaque_choices=True)
        self.assertTrue(r['compiled_pixel_identity_verified'])
        self.assertEqual({p['bank']for p in r['pieces']},set(range(8)))
        self.assertEqual(r['peak_scheduled_writes'],0)
        self.assertEqual(sum(len(set(v)-{None})for v in r['trace'][0]['resident_before'].values()),0)
        self.assertEqual(r['trace'][0]['colors_written'],120)
        self.assertEqual(r['color_math'],'precomposited')

    def test_precomposited_refuses_additive_pool_identity(self):
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[0,0]=31
        background=np.zeros((224,256,3),dtype=np.uint8)
        actors=[dict(pixels=pixels,left=0,top=0)]
        pool=dict(status='POOLED_INTEGER_RESIDENCY_CANDIDATE',metadata={},fractional_residency=[])
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},background)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            with self.assertRaisesRegex(ValueError,'JOINT_POOL_COLOR_MATH'):
                probe(None,None,{},color_math='precomposited',pool_residency=pool)

    def test_equal_opaque_outputs_coalesce_across_distinct_underlays(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        background[0,0]=[32,0,0];background[0,1]=[32,8,0]
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[0,:2]=31
        expected=background.copy();expected[0,:2]=[248,0,0]
        actors=[dict(pixels=pixels,left=0,top=0)]
        results=[]
        for coalesce in (False,True):
            with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                r=probe(None,None,{},size=8,write_budget=0,time_limit=5,coalesce_opaque_choices=coalesce)
            self.assertTrue(r['compiled_pixel_identity_verified'])
            self.assertEqual(r['geometry']['oam_entries'],1)
            results.append(r)
        self.assertEqual(results[0]['distinct_opaque_choice_variables'],8)
        self.assertEqual(results[1]['distinct_opaque_choice_variables'],4)
        self.assertEqual(results[0]['source_rgb555_sha256'],results[1]['source_rgb555_sha256'])

    def test_grid_padding_changes_piece_origin_without_changing_source_pixels(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((32,32),-1,dtype=np.int32);pixels[9:11,9:11]=31
        expected=background.copy();expected[9:11,9:11,0]=248
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=8,write_budget=0,time_limit=5,
                    align_visible_bounds=True,grid_padding_x=7,grid_padding_y=7)
        self.assertTrue(r['compiled_pixel_identity_verified'])
        self.assertEqual(r['source_actor_canvases'],[[32,32]])
        self.assertEqual({(p['local_x'],p['local_y'])for p in r['pieces']},{(2,2),(10,2),(2,10),(10,10)})
        self.assertEqual(r['geometry']['oam_entries'],4)
        self.assertEqual(np.count_nonzero(pixels>=0),4)

    def test_grid_padding_requires_visible_bounds_and_legal_phase(self):
        for args in (dict(grid_padding_x=1),dict(align_visible_bounds=True,grid_padding_x=8)):
            with self.assertRaisesRegex(ValueError,'JOINT_GRID_PADDING_DOMAIN'):
                probe(None,None,{},size=8,**args)

    def test_complete_additive_family_uses_shared_noncorner_operand(self):
        word=lambda r,g,b:r|(g<<5)|(b<<10)
        common=word(5,12,7)
        background=np.zeros((224,256,3),dtype=np.uint8)
        background[0,0]=np.array([25,21,13])*8
        background[0,1]=np.array([29,18,13])*8
        pixels=np.full((8,8),-1,dtype=np.int32)
        pixels[0,0]=word(30,31,20);pixels[0,1]=word(31,30,20)
        expected=background.copy()
        expected[0,0]=np.array([30,31,20])*8
        expected[0,1]=np.array([31,30,20])*8
        pool=dict(status='POOLED_INTEGER_RESIDENCY_CANDIDATE',metadata={},
                  fractional_residency=[dict(kind=1,color=common,line=0,value=1)])
        with patch('source_scene_obj_joint.prepare',return_value=([dict(pixels=pixels,left=0,top=0)],{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=8,write_budget=0,time_limit=5,
                    complete_additive_cover=True,pool_residency=pool)
        self.assertTrue(r['compiled_pixel_identity_verified'])
        self.assertEqual(r['geometry']['oam_entries'],1)
        self.assertGreaterEqual(r['pieces'][0]['bank'],4)
        self.assertTrue(r['complete_additive_cover']['all_valid_operand_coverages_retained'])
        self.assertEqual(r['complete_additive_cover']['maximal_cover_operands'],1)

    def test_saturated_corners_include_white_missing_from_minimal_corpus(self):
        background=17|(9<<5)|(12<<10)
        values=saturated_corners(32767,background)
        self.assertEqual(len(values),8)
        self.assertIn(32767,values)
        from source_scene_obj_math import add_rgb555
        self.assertTrue(all(add_rgb555(c,background)==32767 for c in values))
        self.assertEqual(saturated_corners(0,background),[])

    def test_underlay_bypass_preserves_canvas_and_opaque_black(self):
        background=np.zeros((224,256,3),dtype=np.uint8);background[:,:,0]=255
        pixels=np.full((32,32),31,dtype=np.int32);pixels[0,0]=0;original=pixels.copy()
        expected=background.copy();expected[0,0]=0
        actors=[dict(pixels=pixels,left=0,top=0)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            r=probe(None,None,{},size=32,write_budget=0,time_limit=5,underlay_bypass=True,align_visible_bounds=True)
        self.assertTrue(r['compiled_pixel_identity_verified'])
        self.assertEqual(r['source_actor_canvases'],[[32,32]])
        self.assertEqual(r['underlay_bypassed_pixels'],1023)
        self.assertEqual(r['geometry']['oam_entries'],1)
        self.assertEqual(r['pieces'][0]['rows'][0],[0])
        self.assertLess(r['pieces'][0]['bank'],4)
        np.testing.assert_array_equal(pixels,original)

    def test_partition_bound_requires_a_transfer_window(self):
        with self.assertRaisesRegex(ValueError,'JOINT_DMA_PARTITION_REQUIRES_WINDOW'):
            probe(None,None,{},prepared_dma_partition=True)

    def test_dma_window_rejects_bank_label_symmetry(self):
        with self.assertRaisesRegex(ValueError,'JOINT_DMA_BANK_SYMMETRY_UNSAFE'):
            probe(None,None,{},prepared_dma_window=356,bank_symmetry=True)

    def test_dma_window_counts_both_color_bytes(self):
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[:2,:2]=np.arange(4).reshape(2,2)
        expected=background.copy()
        for y in range(2):
            for x in range(2):expected[y,x]=[int(pixels[y,x])*8,0,0]
        actors=[dict(pixels=pixels,left=0,top=0)]
        pool=dict(status='POOLED_INTEGER_RESIDENCY_CANDIDATE',metadata={},fractional_residency=[dict(kind=0,color=c,line=y,value=1)for y,c in ((0,0),(0,1),(1,2),(1,3))])
        for window,status in ((16,2),(17,0)):
            with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                r=probe(None,None,{},size=8,write_budget=2,prepared_dma_window=window,prepared_dma_partition=True,pool_residency=pool,time_limit=5)
            self.assertEqual(r['solver']['status'],status)
            if status==0:self.assertTrue(r['compiled_pixel_identity_verified'])

    def test_forced_opaque_row_requires_three_fixed_masks(self):
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.full((32,32),-1,dtype=np.int32);pixels[0,:31]=np.arange(31)
        expected=background.copy()
        for x in range(31):expected[0,x]=[x*8,0,0]
        actors=[dict(pixels=pixels,left=0,top=0)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=32,write_budget=0,time_limit=5,bank_symmetry=True)
        self.assertEqual(result['mandatory_geometry_lower_bound'],dict(oam_entries=3,peak_sprites=3,peak_tile_slivers=12))
        self.assertEqual(result['geometry']['oam_entries'],3)
        self.assertTrue(result['compiled_pixel_identity_verified'])

    def test_joint_encoding_preserves_opaque_black_and_negative_residual(self):
        background=np.full((224,256,3),112,dtype=np.uint8)
        pixels=np.full((8,8),-1,dtype=np.int32)
        pixels[0,0]=0;pixels[0,1]=32767;pixels[1,0]=31
        actors=[dict(pixels=pixels,left=0,top=0)]
        expected=background.copy()
        expected[0,0]=0;expected[0,1]=255;expected[1,0]=[255,0,0]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)), patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=8,write_budget=0,time_limit=5,feasibility_only=True,bank_symmetry=True)
        self.assertEqual(result['status'],'JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
        self.assertTrue(result['compiled_pixel_identity_verified'])
        self.assertEqual(result['peak_scheduled_writes'],0)
        black_pieces=[p for p in result['pieces'] if 0 in p['rows'].get(0,[])]
        self.assertEqual(len(black_pieces),1)
        self.assertLess(black_pieces[0]['bank'],4)
        self.assertTrue(result['no_color_reduction'])
        self.assertFalse(result['native_presentation_proven'])

    def test_four_opaque_banks_need_liveness_for_sixty_four_identities(self):
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.arange(64,dtype=np.int32).reshape(8,8)
        expected=background.copy()
        expected[:8,:8]=np.stack([(pixels>>shift)&31 for shift in (0,5,10)],axis=-1)*8
        actors=[dict(pixels=pixels,left=0,top=0)]
        for budget in (0,1):
            with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)), patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                result=probe(None,None,{},size=8,write_budget=budget,time_limit=5)
            if budget==0:
                self.assertEqual(result['status'],'BOUNDED_JOINT_SOLVER_NO_CANDIDATE')
                self.assertEqual(result['solver']['status'],2)
                self.assertFalse(result['universal_raster_rejected'])
            else:
                self.assertEqual(result['status'],'JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
                self.assertEqual(result['peak_scheduled_writes'],1)
                self.assertTrue(result['compiled_pixel_identity_verified'])

    def test_saturated_additive_alternatives_are_replayed_exactly(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        background[0,0]=[248,248,248]
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[0,:2]=32767
        expected=background.copy();expected[0,:2]=255
        actors=[dict(pixels=pixels,left=0,top=0)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=8,write_budget=0,time_limit=5,saturated_reuse=True,feasibility_only=True,bank_symmetry=True)
        self.assertEqual(result['status'],'JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
        self.assertEqual(result['additive_alternative_count'],3)
        self.assertTrue(result['compiled_pixel_identity_verified'])

    def test_visible_bounds_shift_pieces_without_changing_source_pixels(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((90,110),-1,dtype=np.int32);pixels[20:76,9:86]=31
        expected=background.copy();expected[40:96,39:116]=[255,0,0]
        actors=[dict(pixels=pixels,left=30,top=20)]
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=32,write_budget=0,time_limit=5,align_visible_bounds=True,bank_symmetry=True)
        self.assertTrue(result['compiled_pixel_identity_verified'])
        self.assertEqual(result['geometry']['oam_entries'],6)
        self.assertEqual(result['peak_scheduled_writes'],0)
        self.assertGreater(result['trace'][0]['colors_written'],0)
        self.assertEqual(min(p['local_x'] for p in result['pieces']),9)
        self.assertEqual(min(p['local_y'] for p in result['pieces']),20)

    def test_early_row_limit_is_enforced_before_late_window(self):
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.arange(64,dtype=np.int32).reshape(8,8)
        expected=background.copy()
        expected[:8,:8]=np.stack([(pixels>>shift)&31 for shift in (0,5,10)],axis=-1)*8
        actors=[dict(pixels=pixels,left=0,top=0)]
        for early,late_start,expected_status in ((0,75,2),(1,75,0),(0,1,0)):
            with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
                result=probe(None,None,{},size=8,write_budget=1,time_limit=5,early_write_budget=early,late_start=late_start,bank_symmetry=True,feasibility_only=True)
            self.assertEqual(result['solver']['status'],expected_status)
            if expected_status==0:
                self.assertTrue(result['compiled_pixel_identity_verified'])
                self.assertLessEqual(max((row['colors_written'] for row in result['trace'][1:late_start]),default=0),early)

    def test_pool_gap_cannot_reload_evicted_initial_color_for_free(self):
        background=np.full((224,256,3),255,dtype=np.uint8)
        pixels=np.full((8,64),-1,dtype=np.int32)
        pixels[0,0]=pixels[2,0]=0;pixels[1,:60]=np.arange(1,61)
        expected=background.copy()
        for y,x in zip(*np.where(pixels>=0)):
            c=int(pixels[y,x]);expected[y+44,x]=[(c>>shift&31)*8 for shift in (0,5,10)]
        actors=[dict(pixels=pixels,left=0,top=44)]
        entries=[dict(kind=0,color=c,line=y,value=1) for c in range(1,61) for y in (44,45)]
        entries += [dict(kind=0,color=0,line=y,value=1) for y in (44,46)]
        pool=dict(status='POOLED_INTEGER_RESIDENCY_CANDIDATE',metadata={},fractional_residency=entries)
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size=8,write_budget=0,early_write_budget=1,late_start=46,time_limit=5,pool_residency=pool,bank_symmetry=True,feasibility_only=True)
        self.assertEqual(result['solver']['status'],2)
        self.assertFalse(result['universal_raster_rejected'])

    def test_mixed_geometry_replays_actual_nonoverlapping_piece_masks(self):
        background=np.zeros((224,256,3),dtype=np.uint8)
        pixels=np.full((8,8),-1,dtype=np.int32);pixels[2,2]=31;pixels[2,3]=0
        expected=background.copy();expected[46,2]=[255,0,0]
        actors=[dict(pixels=pixels,left=0,top=44)]
        pool=dict(status='POOLED_INTEGER_RESIDENCY_CANDIDATE',metadata={},fractional_residency=[dict(kind=0,color=color,line=y,value=1)for color in (0,31)for y in range(44,47)])
        with patch('source_scene_obj_joint.prepare',return_value=(actors,{},expected)),patch('source_scene_obj_joint.compose_rgb8',return_value=(background,{})):
            result=probe(None,None,{},size='mixed',write_budget=0,time_limit=5,pool_residency=pool,clip_horizontal=True,pin_pool_intervals=True)
        self.assertEqual(result['status'],'JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
        self.assertEqual(result['geometry']['oam_entries'],1)
        self.assertTrue(result['full_pool_intervals_retained'])
        self.assertEqual(result['pool_residency_intervals'],2)
        self.assertEqual(len(result['piece_pixel_masks']),1)
        data=np.frombuffer(bytes.fromhex(result['piece_pixel_masks'][0]['pixels_hex']),dtype=np.uint8)
        self.assertEqual(int(np.count_nonzero(data&15)+np.count_nonzero(data>>4)),2)


if __name__=='__main__':unittest.main()
