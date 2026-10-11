import unittest
from raster_window_residency import optimize
from raster_slot_greedy import demand
from raster_slot_refine import verify_packets
import test_raster_window_slot_schedule as fixtures


class WindowResidencyTests(unittest.TestCase):
    def test_shared_mode_search_preserves_exact_pixels_with_fixed_banks(self):
        import copy,hashlib,itertools
        import numpy as np
        from raster_obj_math_cover import apply_math
        source,_,_=fixtures.WindowSlotTests().source()
        image=np.tile(np.arange(1,9,dtype=np.uint8),(8,1));flat=image.flatten()
        source['piece_pixel_masks'][0]['pixels_hex']=(flat[::2]|flat[1::2]<<4).tobytes().hex()
        bg=np.zeros((16,256),dtype=np.uint16);expected=bg.copy();words=[]
        for i,channels in enumerate(itertools.product((8,10,12,14),repeat=3)):
            y,x=divmod(i,8);under=sum(c<<shift for c,shift in zip(channels,(0,5,10)))
            bg[y,x]=under;expected[y,x]=apply_math(32767,under,'half-add')
            words.append(sum(((int(expected[y,x])>>shift&31)-(under>>shift&31))<<shift for shift in(0,5,10)))
        state={b:[None]*15 for b in range(8)};trace=[]
        for y in range(16):
            before=copy.deepcopy(state);events=[]
            if y<8:
                for s,c in enumerate(words[y*8:y*8+8]):
                    events.append(dict(bank=4,slot=s+1,old=state[4][s],color=c));state[4][s]=c
            trace.append(dict(scanline=y,resident_before=before,updates=events))
        source['trace']=trace;source['selected_modes']={str(y):'add'for y in range(16)}
        source['source_rgb555_sha256']=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()
        failed=optimize(source,bg,expected,time_limit=10,maximum_writes=0)
        self.assertEqual(failed['solver_status'],'INFEASIBLE')
        for backend in('cp-sat','highs'):
            result=optimize(source,bg,expected,time_limit=10,maximum_writes=0,movable_math_modes=True,solver_backend=backend)
            self.assertGreater(result['bank_residency']['changed_scanline_math_modes'],0)
            self.assertEqual([{k:p[k]for k in source['pieces'][i]}for i,p in enumerate(result['pieces'])],source['pieces'])
            self.assertEqual(result['bank_residency']['peak_actual_palette_writes'],0)
            self.assertTrue(result['bank_residency']['complete_source_frame_pixel_identity_proven'])
            verify_packets(result);demand(result)

    def test_liveness_capacity_requires_seven_writes_and_preserves_opaque_zero(self):
        import copy,hashlib
        import numpy as np
        source,_,_=fixtures.WindowSlotTests().source();source['pieces'][0]['bank']=0
        indices=np.tile(np.arange(1,9,dtype=np.uint8),(8,1));flat=indices.flatten();source['piece_pixel_masks'][0]['pixels_hex']=(flat[::2]|flat[1::2]<<4).tobytes().hex()
        state={b:[None]*15 for b in range(8)};trace=[]
        for y in range(16):
            before=copy.deepcopy(state);events=[]
            if y<8:
                for s in range(8):
                    c=8*y+s;events.append(dict(bank=0,slot=s+1,old=state[0][s],color=c));state[0][s]=c
            trace.append(dict(scanline=y,resident_before=before,updates=events))
        source['trace']=trace;bg=np.zeros((16,256),dtype=np.uint16);expected=bg.copy();expected[:8,:8]=np.arange(64,dtype=np.uint16).reshape(8,8)
        source['source_rgb555_sha256']=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()
        for backend in('cp-sat','highs'):
            failed=optimize(source,bg,expected,time_limit=10,maximum_writes=6,solver_backend=backend)
            self.assertEqual(failed['solver_status'],'INFEASIBLE')
            result=optimize(source,bg,expected,time_limit=10,maximum_writes=7,solver_backend=backend)
            self.assertEqual(result['bank_residency']['peak_actual_palette_writes'],7)
            self.assertEqual(set(demand(result)[2][0].flatten()),set(range(64)))
            self.assertFalse(result['bank_residency']['native_timing_admitted'])

    def test_disjoint_interval_flow_matches_independent_bank_dp(self):
        from ortools.sat.python import cp_model
        from raster_bank_residency import constrain_flow,favorable_span
        import random
        model=cp_model.CpModel();cases=[];costs=[];rng=random.Random(4086)
        for mask in range(256):
            counts=[rng.randint(1,15)if mask>>b&1 else 0 for b in range(8)]
            n=[model.new_constant(c)for c in counts];active=[model.new_constant(int(c>0))for c in counts]
            cost=constrain_flow(model,n,active,4097,f'mask{mask}');costs.append(cost)
            cases.append(counts)
            costs.append(constrain_flow(model,n,active,4097,f'linearMask{mask}',linear=True));cases.append(counts)
        model.minimize(sum(costs));solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=15
        self.assertEqual(solver.solve(model),cp_model.OPTIMAL)
        for counts,cost in zip(cases,costs):
            updates=[dict(bank=b)for b,n in enumerate(counts)for _ in range(n)]
            self.assertEqual(max(0,solver.value(cost)-40),favorable_span(updates))
        model=cp_model.CpModel();counts=[1,15,4,0,0,0,0,0]
        cost=constrain_flow(model,[model.new_constant(c)for c in counts],[model.new_constant(int(c>0))for c in counts],337,'threeBanks')
        model.minimize(cost);self.assertEqual(solver.solve(model),cp_model.OPTIMAL)
        self.assertEqual(solver.value(cost)-40,336)

    def test_complete_source_replay_does_not_admit_physical_or_native_timing(self):
        source,bg,expected=fixtures.WindowSlotTests().source()
        result=optimize(source,bg,expected,time_limit=5,maximum_writes=0)
        demand(result);verify_packets(result)
        self.assertTrue(result['bank_residency']['complete_source_frame_pixel_identity_proven'])
        self.assertEqual(result['bank_residency']['peak_actual_palette_writes'],0)
        self.assertFalse(result['bank_residency']['physical_slot_window_admitted'])
        self.assertFalse(result['native_presentation_proven'])

    def test_context_and_budget_domain_reject(self):
        source,bg,expected=fixtures.WindowSlotTests().source()
        with self.assertRaisesRegex(ValueError,'DOMAIN'):optimize(source,bg,expected,maximum_writes=-1)
        wrong=expected.copy();wrong[0,0]^=1
        with self.assertRaisesRegex(ValueError,'CONTEXT_IDENTITY'):optimize(source,bg,wrong)


if __name__=='__main__':unittest.main()
