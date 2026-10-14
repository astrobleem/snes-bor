"""Pressure instruction boundaries and preservation of the exact predictor."""
import unittest
from pathlib import Path
from early_capacity import _pressure_gate,_predictor,transform,legacy_transform
from test_early_capacity import ProbeVM,fixture
from m4_conditional_capacity_native import audit_rom,audit_capacity

class GateVM(ProbeVM):
    def __init__(self,refs):
        super().__init__([0]*1024,refs)
        self.op=[];self.labels={};self.reads=[]
        for line in _pressure_gate():
            t=line.strip()
            if not t or t.startswith('.'):continue
            if t.endswith(':'):self.labels[t[:-1]]=len(self.op)
            else:self.op.append(t)
        self.labels['NbCapacityPredict']=0
    def mem(self,expr):
        if expr.startswith('$42D000'):
            self.reads.append(0x42d000+self.X)
        elif expr!='$70':raise AssertionError('Gate touched another memory authority:'+expr)
        return super().mem(expr)

class PressureTests(unittest.TestCase):
    def test_native_emitted_boundary_semantics_and_early_stop(self):
        for free in (0,124,128,129,134,172):
            refs=[0x8001]*768
            refs[596:596+free]=[0xc000]*free
            vm=GateVM(refs);seed=bytes(vm.records);carry=vm.run()
            self.assertEqual(carry,free<=128)
            self.assertEqual(vm.dp[0x70],min(free,129))
            self.assertEqual(len(vm.reads),172 if free<=128 else 129)
            self.assertEqual(bytes(vm.records),seed);self.assertEqual(vm.writes,[])
            self.assertTrue(all(0x42d4a8<=x<=0x42d5fe for x in vm.reads))
    def test_false_negative_leaves_existing_safe_fallback(self):
        src=Path('out/byor-motu-restore-spill-regression-v1/native/publisher.pasm').read_text().splitlines()
        out=transform(src)
        self.assertEqual(out[out.index('NbFree:'):out.index('NbFreshVblank:')],src[src.index('NbFree:'):src.index('NbFreshVblank:')])
        vm=GateVM([1]*596+[0]*134+[1]*38);self.assertFalse(vm.run())
        # A demand of 135 exceeds 134; skipping only the heuristic does not
        # remove NbFree's proven guarded exhaustion/retry path.
        self.assertIn(' jmp NbBeginRetry',out[out.index('NbFree:'):out.index('NbFreshVblank:')])
    def test_exact_retry_branches_around_both_calls(self):
        out=transform(fixture());a=out.index('NbRestorePlanStart:');b=out.index('NbRestorePlan:')
        self.assertEqual(out[a+3:a+5],[' lda.l $42D674',' bne NbCapacityPredictSkip'])
        self.assertLess(out.index('NbCapacityPredictSkip:'),b)
    def test_exact_predictor_and_legacy_control_are_unchanged(self):
        old=legacy_transform(fixture());new=transform(fixture())
        a=new.index('NbCapacityPredict:');b=new.index('NbCapacityPressureGate:')
        self.assertEqual(new[a:b],_predictor())
        self.assertNotIn('NbCapacityPressureGate:',old)
    def test_flag_disabled_rom_is_certified_identity(self):
        from m4_nonblank_component_native import sha
        self.assertEqual(sha(Path('out/byor-motu-conditional-capacity-disabled-v1/native/bor.sfc').read_bytes()),'05c3cef5f282113867b8dbc235e3bc72a7a718064023cbf58ff9bfc7410aa45d')
    def test_gate_authority_and_minimal_scratch(self):
        code=_pressure_gate()
        self.assertFalse(any('$003480' in x or '$42C000' in x or '$0021' in x for x in code))
        self.assertEqual([x for x in code if x.strip().startswith(('sta','inc'))],[' sta $70',' inc $70'])
    def test_native_unit_binary_and_scope(self):
        from m4_pressure_gate_unit_native import audit
        n=Path('out/byor-motu-pressure-unit-v4/native')
        self.assertTrue(audit((n/'bor.sfc').read_bytes(),n)['restored_before_cold_production'])
    def test_native_boundary_invocations_and_existing_fallback(self):
        from m4_pressure_gate_unit_native import certify
        r=certify(Path('out/byor-motu-pressure-unit-v4'))
        self.assertTrue(r['false_negative_134_free_safe_retry_and_second_exhaustion'])
        self.assertEqual(r['native_gate_boundaries_verified'],[124,128,129,134])
    def test_actual_candidate_branch_and_code_audits(self):
        for path,audit in [('out/byor-motu-conditional-capacity-regression-v1/native',audit_rom),('out/byor-motu-conditional-capacity-success-v1/native',audit_capacity)]:
            n=Path(path);self.assertTrue(audit((n/'bor.sfc').read_bytes(),n)['all_other_rom_bytes_identical'])
