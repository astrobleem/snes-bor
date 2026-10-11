import copy,hashlib,importlib.util,unittest
import numpy as np
from raster_window_slot_schedule import derive,optimize
from raster_math_windows import compile_mask,compile_sparse_mask,evaluate
from raster_obj_math_cover import apply_math
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets
from test_raster_slot_layout import SlotLayoutTests


@unittest.skipUnless(importlib.util.find_spec('ortools'),'optional OR-Tools backend')
class WindowSlotTests(unittest.TestCase):
    def test_joint_bank_assignment_stays_fixed_and_respects_math_eligibility(self):
        source,bg,expected=self.source();source['pieces'][0]['allowed_banks']=[4,5]
        result=optimize(source,bg,expected,time_limit=5,maximum_writes=0,movable_pieces=[0])
        verify_packets(result)
        self.assertIn(result['pieces'][0]['bank'],[4,5])
        self.assertTrue(result['physical_slot_layout']['piece_banks_fixed_across_all_scanlines'])
        self.assertTrue(result['physical_slot_layout']['complete_source_frame_pixel_identity_proven'])
        self.assertEqual(len(result['pieces']),len(source['pieces']))
        with self.assertRaisesRegex(ValueError,'MOVABLE_PIECES'):optimize(source,bg,expected,movable_pieces=[1])
        with self.assertRaisesRegex(ValueError,'ENCODING_COMBINATION'):optimize(source,bg,expected,movable_pieces=[0],complete_exact_operands=True)

    def test_saturated_exact_operands_can_reuse_resident_words(self):
        source,bg,_=self.source();mask=np.zeros((8,8),dtype=np.uint8);mask[0,:2]=[1,2]
        flat=mask.flatten();source['piece_pixel_masks'][0]['pixels_hex']=(flat[::2]|flat[1::2]<<4).tobytes().hex()
        empty={b:[None]*15 for b in range(8)};state=copy.deepcopy(empty);state[4][:2]=[30,31]
        source['trace']=[dict(scanline=y,resident_before=copy.deepcopy(empty if y==0 else state),updates=[dict(bank=4,slot=s+1,old=None,color=c)for s,c in enumerate([30,31])]if y==0 else[])for y in range(16)]
        bg[:]=0;bg[0,:2]=[1,2];expected=bg.copy();expected[0,:2]=31
        source['source_rgb555_sha256']=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()
        result=optimize(source,bg,expected,time_limit=5,maximum_writes=0,reuse_exact_operands=True)
        verify_packets(result)
        self.assertGreater(result['physical_slot_layout']['pixels_with_multiple_exact_operand_choices'],0)
        self.assertTrue(result['physical_slot_layout']['complete_source_frame_pixel_identity_proven'])
        self.assertEqual(result['physical_slot_layout']['peak_actual_palette_writes'],0)
        repaired=optimize(result,bg,expected,time_limit=5,maximum_writes=0,reuse_exact_operands=True,repair_interval=(0,0))
        verify_packets(repaired)
        self.assertEqual([r['resident_before']for r in repaired['trace'][2:]],[r['resident_before']for r in result['trace'][2:]])
        self.assertTrue(repaired['physical_slot_layout']['complete_source_frame_pixel_identity_proven'])
        with self.assertRaisesRegex(ValueError,'REPAIR_INTERVAL'):optimize(result,bg,expected,repair_interval=(4,3))
        complete=optimize(source,bg,expected,time_limit=5,maximum_writes=0,complete_exact_operands=True)
        verify_packets(complete)
        self.assertEqual(complete['physical_slot_layout']['complete_rgb555_operand_covers'][4]['rgb555_operands_examined'],32768)
        self.assertTrue(complete['physical_slot_layout']['complete_source_frame_pixel_identity_proven'])

    def test_mandatory_bank_lifetimes_require_writes_beyond_fifteen_colors(self):
        source=SlotLayoutTests().schedule();source['color_math']='additive';source['pieces']=[dict(source['pieces'][0],width=32,height=32)]
        mask=np.zeros((32,32),dtype=np.uint8);mask[:20,0]=1;flat=mask.flatten()
        source['piece_pixel_masks']=[dict(width=32,height=32,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex())]
        state={b:[None]*15 for b in range(8)};trace=[]
        for y in range(32):
            before=copy.deepcopy(state);events=[]
            if y<20:events=[dict(bank=0,slot=1,old=state[0][0],color=y)];state[0][0]=y
            trace.append(dict(scanline=y,resident_before=before,updates=events))
        source['trace']=trace;source['scanline_math_controls_source_bound']=True
        source['selected_modes']={str(y):'add'for y in range(32)}
        source['compiled_color_window_descriptors']={str(y):compile_mask([False]*256)for y in range(32)}
        bg=np.full((32,256),33,dtype=np.uint16);expected=bg.copy();expected[:20,0]=np.arange(20,dtype=np.uint16)
        source['source_rgb555_sha256']=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()
        failed=optimize(source,bg,expected,time_limit=3,maximum_writes=0)
        self.assertEqual(failed['solver_status'],'INFEASIBLE');self.assertGreater(failed['mandatory_identity_bank_interval_cuts'],0)
        result=optimize(source,bg,expected,time_limit=5,maximum_writes=1)
        verify_packets(result)
        self.assertTrue(result['physical_slot_layout']['complete_source_frame_pixel_identity_proven'])
        self.assertGreaterEqual(sum(len(r['updates'])for r in result['trace'][1:]),5)

    def source(self):
        source=SlotLayoutTests().schedule();source['color_math']='additive'
        source['pieces']=source['pieces'][:1];source['pieces'][0]['bank']=4
        source['piece_pixel_masks']=source['piece_pixel_masks'][:1]
        for row in source['trace']:
            row['resident_before'][4]=row['resident_before'][0];row['resident_before'][0]=[None]*15
            row['resident_before'][1]=[None]*15
            row['updates']=[dict(e,bank=4)for e in row['updates']if e['bank']==0]
        background=np.full((16,256),33,dtype=np.uint16);expected=background.copy()
        source['selected_modes']={str(y):'add'for y in range(16)}
        source['compiled_color_window_descriptors']={str(y):compile_mask([True]*256,fixed_positive_union=True)for y in range(16)}
        source['scanline_math_controls_source_bound']=True
        _,_,images=demand(source)
        for p,image in zip(source['pieces'],images):
            for ly,lx in zip(*np.where(image>=0)):expected[p['y']+ly,p['x']+lx]=apply_math(int(image[ly,lx]),int(background[p['y']+ly,p['x']+lx]),'add')
        source['source_rgb555_sha256']=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()
        return source,background,expected

    def test_fixed_banks_window_choices_replay_exact_context_and_packets(self):
        source,bg,expected=self.source()
        result=optimize(source,bg,expected,window=337,time_limit=5,maximum_writes=0)
        verify_packets(result)
        self.assertEqual([{k:v for k,v in p.items()if k!='rows'}for p in result['pieces']],source['pieces'])
        self.assertTrue(result['physical_slot_layout']['complete_source_frame_pixel_identity_proven'])
        self.assertEqual(result['physical_slot_layout']['peak_actual_palette_writes'],0)
        self.assertFalse(result['physical_slot_layout']['native_timing_admitted'])
        actual=bg.copy();_,_,images=demand(result)
        for p,image in zip(result['pieces'],images):
            for ly,lx in zip(*np.where(image>=0)):
                y,x=p['y']+ly,p['x']+lx;word=int(image[ly,lx])
                actual[y,x]=apply_math(word,int(bg[y,x]),result['selected_modes'][str(y)])if evaluate(result['compiled_color_window_descriptors'][str(y)],x)else word
        np.testing.assert_array_equal(actual,expected)
        self.assertTrue(np.array_equal(images[0]>=0,demand(source)[2][0]>=0))

    def test_context_hash_and_math_authority_are_required(self):
        source,bg,expected=self.source();wrong=expected.copy();wrong[0,0]^=1
        with self.assertRaisesRegex(ValueError,'CONTEXT_IDENTITY'):derive(source,bg,wrong)
        wrong_bg=bg.copy();wrong_bg[1,0]^=1024
        with self.assertRaisesRegex(ValueError,'INPUT_PIXEL_MATH_IDENTITY'):derive(source,wrong_bg,expected)
        broken=copy.deepcopy(source);broken['scanline_math_controls_source_bound']=False
        with self.assertRaisesRegex(ValueError,'SOURCE_CONTROLS_REQUIRED'):derive(broken,bg,expected)
        broken=copy.deepcopy(source);broken['pieces'][0]['allowed_banks']=[5]
        with self.assertRaisesRegex(ValueError,'FIXED_BANK_ELIGIBILITY'):derive(broken,bg,expected)

    def test_three_positive_runs_use_two_inverted_windows_with_fixed_hint(self):
        from ortools.sat.python import cp_model
        from unittest.mock import patch
        source,bg,_=self.source();mask=np.zeros((8,8),dtype=np.uint8);mask[0,:5]=np.arange(1,6,dtype=np.uint8)
        flat=mask.flatten();source['piece_pixel_masks'][0]['pixels_hex']=(flat[::2]|flat[1::2]<<4).tobytes().hex()
        empty={b:[None]*15 for b in range(8)};state=copy.deepcopy(empty);state[4][:5]=[31,32,33,34,35]
        source['trace']=[dict(scanline=y,resident_before=copy.deepcopy(empty if y==0 else state),updates=[dict(bank=4,slot=s+1,old=None,color=c)for s,c in enumerate(state[4][:5])]if y==0 else[])for y in range(16)]
        descriptor=compile_sparse_mask({0:True,1:False,2:True,3:False,4:True})
        source['compiled_color_window_descriptors']={str(y):descriptor for y in range(16)}
        expected=bg.copy()
        for x,word in enumerate(state[4][:5]):expected[0,x]=apply_math(word,int(bg[0,x]),'add')if evaluate(descriptor,x)else word
        source['source_rgb555_sha256']=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()
        constructor=cp_model.CpSolver
        def fixed_hint_solver():
            solver=constructor();solver.parameters.fix_variables_to_their_hinted_value=True;return solver
        with patch.object(cp_model,'CpSolver',fixed_hint_solver):result=optimize(source,bg,expected,time_limit=5,maximum_writes=0)
        verify_packets(result)
        self.assertTrue(result['compiled_color_window_descriptors']['0']['wobjsel_color_bits']&0x50)
        self.assertEqual(result['physical_slot_layout']['peak_actual_palette_writes'],0)


if __name__=='__main__':unittest.main()
