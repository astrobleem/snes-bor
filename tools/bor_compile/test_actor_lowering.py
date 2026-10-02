"""S5 descriptor/reference tests. These are NOT live runtime certificates."""
import ast
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path
import unittest

from compiler import Directive
from model_ir import ModelIR, AnimationIR, FrameIR
from actor_lowering import (allocate_ids, attack_at, certify_current, drift_spawn,
                            drift_tick, effect_descriptor, lower_model, role_binding)


def fixture(role='fall'):
    attack=dict(kind='attack',raw=['1','2','3','4','7','1'],box=[1,2,3,4],force=7,drop=1)
    frame=FrameIR(4,'frame.gif','abc',[16,24],
        dict(delay=7,offset=[2,3],bbox=[1,2,3,4],attack=attack,move=-2))
    return ModelIR('p','Different','model.txt','sha','historical-bor',('p','model.txt'),[],
                   stats={'type':'enemy'},animations=[AnimationIR(role,frames=[frame])])


class ActorLoweringTests(unittest.TestCase):
    def test_no_source_mutation(self):
        ir=fixture();before=asdict(ir)
        lowered=lower_model(ir,8)
        lowered['animations'][0]['frames'][0]['attack']['force']=99
        self.assertEqual(asdict(ir),before)

    def test_source_corner_transform_and_clock(self):
        frame=lower_model(fixture())['animations'][0]['frames'][0]
        self.assertEqual(frame['source_binding']['body_corners'],[-1,-1,2,3])
        self.assertEqual(frame['source_binding']['attack_corners'],[-1,-1,2,3])
        self.assertEqual(frame['source_binding']['delay_ticks'],14)
        self.assertTrue(frame['source_binding']['vulnerable'])
        ir=fixture();ir.animations[0].frames[0].state['bbox']=[0,0,0,0]
        lowered=lower_model(ir)
        self.assertFalse(lowered['animations'][0]['frames'][0]['source_binding']['vulnerable'])
        self.assertEqual(certify_current(ir,lowered)['matrix']['COLLISION']['status'],'BLOCKED')

    def test_arbitrary_role_attack_and_behavior_flag(self):
        for role in ('fall','idle','walk','attack1','unbound-role'):
            actor=lower_model(fixture(role))
            self.assertIsNone(attack_at(actor,role,0))
            self.assertEqual(attack_at(actor,role,0,attacking=True)['force'],7)
            self.assertEqual(attack_at(actor,role,0,projectile=True)['drop'],1)
        # Descriptor preservation is not evidence an unknown role runs.
        self.assertEqual(role_binding('unbound-role').status,'UNSUPPORTED')

    def test_zero_force_and_invalid_frame(self):
        ir=fixture();ir.animations[0].frames[0].state['attack']['force']=0
        actor=lower_model(ir)
        self.assertIsNone(attack_at(actor,'fall',0,attacking=True))
        with self.assertRaises(IndexError): attack_at(actor,'fall',-1,attacking=True)

    def test_pinned_ids_and_project_isolation(self):
        ids=[('p','b'),('p','a'),('p','c')]
        expected={('p','b'):4,('p','a'):1,('p','c'):2}
        self.assertEqual(allocate_ids(ids,{('p','b'):4},reserved=[0]),expected)
        self.assertEqual(allocate_ids(reversed(ids),{('p','b'):4},reserved=[0]),expected)
        with self.assertRaises(ValueError): allocate_ids([('p','a'),('q','a')])
        with self.assertRaises(ValueError): allocate_ids(ids,maximum=1)
        with self.assertRaises(ValueError): allocate_ids(ids,{('p','a'):0},reserved=[0])

    def test_drift_samples_once_and_checks_before_motion(self):
        ir=fixture('walk');ir.stats={'type':'none','speed':'9'}
        behavior=lower_model(ir)['behavior']
        left=drift_spawn(behavior,0,0,Fraction(1,2))
        right=drift_spawn(behavior,160,160,Fraction(1,2))
        self.assertEqual(left['xdir'],Fraction(12,5))
        self.assertEqual(right['xdir'],-left['xdir'])
        self.assertFalse(left['attacking']);self.assertFalse(left['damage_callback'])
        left['x']=Fraction(400)
        after=drift_tick(left,0)
        self.assertTrue(after['alive'])
        self.assertEqual(after['x'],Fraction(2012,5))
        self.assertFalse(drift_tick(after,0)['alive'])
        self.assertFalse(drift_tick(dict(after,alive=False),500)['alive'])
        with self.assertRaises(ValueError): drift_spawn(behavior,0,0,1)

    def test_effect_consumes_semantics_not_name(self):
        descriptor=effect_descriptor({'default_effect':'reset_timer'})
        self.assertEqual(descriptor['source_counter_value'],40000)
        self.assertEqual(descriptor['source_tick_hz'],200)
        self.assertFalse(descriptor['target_bound'])

    def test_no_false_certification(self):
        ir=fixture();result=certify_current(ir,lower_model(ir,4))
        self.assertEqual(result['status'],'BLOCKED')
        for category in ('COLLISION','ATTACKS','ASSETS','STATS','AI_BEHAVIOR'):
            self.assertEqual(result['matrix'][category]['status'],'BLOCKED')
        self.assertEqual(result['matrix']['IDENTITY']['status'],'CERTIFIED')

    def test_unknown_directive_survives_into_matrix(self):
        ir=fixture();ir.diagnostics=[dict(category='UNKNOWN_SOURCE_SEMANTIC',
            reason='unbound behavior',animation_role=None,line=1,directive='magic')]
        ir.directives=[Directive(1,'magic',['42'])]
        lower=lower_model(ir,0)
        self.assertEqual(lower['directives'][0]['values'],['42'])
        result=certify_current(ir,lower)
        self.assertTrue(any(x['directive']=='magic' for x in result['matrix']['AI_BEHAVIOR']['blockers']))

    def test_new_lowering_has_no_named_behavior_selectors(self):
        text=Path(__file__).with_name('actor_lowering.py').read_text()
        for node in ast.walk(ast.parse(text)):
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                self.assertNotIn(node.value.casefold(),{'time','ramon','crab','lobster'})


if __name__=='__main__': unittest.main()
