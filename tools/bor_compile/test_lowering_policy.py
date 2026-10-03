import copy
import ast
import re
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from dataclasses import asdict

from compiler import ROOT, Source
from model_ir import parse_model
from actor_lowering import lower_model, CATEGORIES, source_random32_step, source_random_fraction
from lowering_policy import Profile, apply_policy, certify_policy, require_certified
from actor_frame_abi import pack_source_frame, pack_animation, check_actor_media_extent
from recertify_actor_entries import recertify


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
        cls.ir=parse_model(source,'DATA/CHARS/KULA/KULA.TXT','Kula','fixture','historical-bor')

    def binding(self,source):
        return dict(baseline='fixture',source_identity=source['source_identity'],source_sha256=source['source_sha256'],
            runtime_id=22,animations={'attack1':dict(delay=4,geometry='fixture geometry')},
            contract=dict(damage=4,collision=[32,64],behavior='accepted',stats='accepted',effects='accepted',palettes=1))

    def test_same_ir_two_policies(self):
        before=asdict(self.ir);source=lower_model(self.ir)
        original=copy.deepcopy(source)
        exact=apply_policy(source)
        compat=apply_policy(source,Profile.ACCEPTED_COMPAT,accepted=self.binding(source))
        frames=next(a['frames'] for a in source['animations'] if a['role']=='attack1')
        self.assertEqual([i for i,f in enumerate(frames) if f['attack'] and f['attack']['force']],[2,3])
        self.assertEqual([frames[i]['attack']['force'] for i in (2,3)],[5,5])
        self.assertEqual([f['delay'] for f in frames],[4,4,4,4,2,2])
        self.assertEqual(exact['source_fingerprint'],compat['source_fingerprint'])
        self.assertEqual(source,original);self.assertEqual(asdict(self.ir),before)
        self.assertEqual(next(a for a in compat['adaptations'] if a.get('role')=='attack1' and a['category']=='TIMING')['accepted'],4)

    def test_no_hidden_fallback(self):
        source=lower_model(self.ir)
        exact=apply_policy(source,accepted=self.binding(source))
        self.assertEqual(exact['profile'],'SOURCE_EXACT')
        self.assertEqual(exact['adaptations'],[])
        with self.assertRaises(ValueError): require_certified(exact)
        with self.assertRaises(ValueError): apply_policy(source,'automatic')
        for accepted in (None,dict(self.binding(source),source_identity=['other','model'])):
            self.assertEqual(apply_policy(source,Profile.ACCEPTED_COMPAT,accepted=accepted)['blockers'],['NO_ACCEPTED_COMPAT_BINDING'])

    def test_labels_do_not_cross(self):
        source=lower_model(self.ir)
        compat=apply_policy(source,Profile.ACCEPTED_COMPAT,accepted=self.binding(source))
        proof=dict(passed=True,baseline='fixture',source_fingerprint=compat['source_fingerprint'])
        self.assertEqual(certify_policy(compat,equivalence_proof=proof)['status'],'ADAPTER_EQUIVALENT')
        exact=apply_policy(source)
        self.assertEqual(certify_policy(exact,equivalence_proof=proof)['status'],'BLOCKED')
        self.assertEqual(certify_policy(exact,source_categories={'ATTACKS':'SOURCE_CERTIFIED'})['status'],'BLOCKED')
        categories={c:'SOURCE_CERTIFIED' for c in CATEGORIES}
        self.assertEqual(certify_policy(exact,source_categories=categories)['status'],'SOURCE_CERTIFIED')

    def test_exact_frame_abi(self):
        source=lower_model(self.ir)
        blob=pack_animation(source,'attack1')
        self.assertEqual(len(blob),6*32)
        frames=[struct.unpack_from('<16H',blob,i*32) for i in range(6)]
        self.assertEqual([f[0] for f in frames],[8,8,8,8,4,4])
        self.assertEqual([f[6] for f in frames],[0,0,5,5,0,0])
        self.assertEqual(frames[2][9:13],(16,65535-81,55,65535-65))
        with self.assertRaises(ValueError): pack_animation(source,'attack1',bank_offset=65500)
        with self.assertRaises(ValueError): pack_animation(source,'attack1',profile=Profile.ACCEPTED_COMPAT)
        compat=apply_policy(source,Profile.ACCEPTED_COMPAT,accepted=self.binding(source))
        with self.assertRaisesRegex(ValueError,'REJECTS_COMPAT_TARGET'):
            pack_animation(compat['target'],'attack1')
        frame=copy.deepcopy(source['animations'][0]['frames'][0])
        frame['source_binding']['delay_ticks']=65536
        with self.assertRaises(ValueError): pack_source_frame(frame)

    def test_source_rng_is_not_byte_sampling(self):
        seed=1234567890
        observed=[]
        for _ in range(5):
            seed,value=source_random32_step(seed)
            observed.append((value,value%1000))
        self.assertEqual(observed,[(0x17488a27,927),(0x040f2cf9,417),
                                   (0x350938b0,784),(0xb1bb71ad,565),(0x1b015346,686)])
        self.assertEqual(source_random_fraction(999).denominator,1000)
        self.assertEqual(source_random_fraction(1000),0)
        with self.assertRaises(ValueError): source_random32_step(-1)

    def test_accepted_hit_tail_restores_real_width(self):
        main=(ROOT/'src/main.pasm').read_text()
        tail=main.split('Character_HitApply__ScoreAndFinish__scored:',1)[1]
        instructions=[line.split(';',1)[0].strip() for line in tail.splitlines()]
        instructions=[line for line in instructions if line and not line.startswith('.')]
        self.assertEqual(instructions[0],'sep #$20')
        self.assertEqual(instructions[1],'lda #1')
        wrapper=(ROOT/'src/core/player2_context.pasm').read_text().split('G13_Game_Score_Award:',1)[1]
        self.assertIn('php',wrapper)
        self.assertRegex(wrapper,r'plp\s+rtl')

    def test_actor_media_address_domain(self):
        self.assertEqual(check_actor_media_extent(0xffffff,1)['end_exclusive'],0x1000000)
        for offset,size in ((0x1000000,1),(0xffffff,2),(-1,32),(0,0)):
            with self.assertRaisesRegex(ValueError,'ACTOR_MEDIA_ADDRESS_RANGE'):
                check_actor_media_extent(offset,size,project='fixture',model='subject')
        import pack_msu_roster
        class TooLarge:
            def __len__(self): return 1<<24
        with patch.object(pack_msu_roster,'pack_character_blob',return_value=(TooLarge(),{})):
            with self.assertRaisesRegex(ValueError,'ACTOR_MEDIA_ADDRESS_RANGE'):
                pack_msu_roster.pack_roster(['fixture-model'])

    def test_new_compiler_policy_has_no_identity_behavior_literals(self):
        for name in ('lowering_policy.py','accepted_actor_policy.py','actor_lowering.py',
                     'actor_frame_abi.py','live_actor_evidence.py','actor_catalog.py'):
            tree=ast.parse((ROOT/'tools/bor_compile'/name).read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Constant) and isinstance(node.value,str):
                    self.assertNotIn(node.value.casefold(),{'time','ramon','crab','lobster'},name)
        for name in ('actor_behavior.pasm','actor_s5_isolated.pasm','actor_s5_clock_isolated.pasm',
                     'actor_catalog_isolated.pasm'):
            path=ROOT/'src/core'/name
            if not path.exists(): continue
            code='\n'.join(line.split(';',1)[0] for line in path.read_text().splitlines())
            self.assertIsNone(re.search(r'(?i)\b(?:cmp|cpx|cpy)\s+#[^\r\n]*(?:crab|lobster|ramon|\btime\b)',code),name)

    def test_entry_recertification_keeps_scene_and_environment_evidence(self):
        previous={'entries':[
            dict(kind='STAGE',source_path='stage.txt',set_name='set',status='BLOCKED',
                 bindings={'models':False,'environment':False},
                 blockers=[dict(directive='water',reason='waves unsupported'),
                           dict(directive='model-contract',reason='old model result')]),
            dict(kind='SCENE',source_path='scene.txt',set_name='set',status='CERTIFIED',
                 bindings={'media':True},blockers=[])]}
        actors=dict(project_id='project',models={'subject':dict(ir={'source_path':'model.txt'},
            lowering_profiles={'SOURCE_EXACT':dict(status='BLOCKED',blockers=['AI_REQUIRED']),
                               'ACCEPTED_COMPAT':dict(status='ADAPTER_EQUIVALENT',blockers=[])})})
        with patch('recertify_actor_entries.scoped_id',return_value='project'), \
             patch('recertify_actor_entries.stage',return_value=SimpleNamespace(queue=[SimpleNamespace(character='Subject',item=None)])):
            result=recertify(previous,actors,object())
        self.assertEqual(result['per_set']['set'],{'BLOCKED':1,'CERTIFIED':1})
        self.assertEqual(result['entries'][0]['blockers'][0]['directive'],'water')
        self.assertEqual(result['entries'][0]['blockers'][1]['reason'],['AI_REQUIRED'])
        self.assertFalse(result['entries'][0]['bindings']['models'])
        self.assertEqual(previous['entries'][0]['blockers'][1]['reason'],'old model result')

    def test_raster_comparison_exposes_accepted_synthetic_roles(self):
        from certify_actors import compare_raster_roles
        palette=bytes(32); frame=bytes([7])*768
        result=compare_raster_roles(palette+frame*2,palette+frame,
            {'idle':{'frame_count':1},'walk':{'frame_count':1}},
            {'idle_frame_count':1},0)
        self.assertEqual(result['roles']['idle']['status'],'BYTE_IDENTICAL')
        self.assertEqual(result['roles']['walk']['status'],'ACCEPTED_REPEATED_ROLE')
        self.assertEqual(result['roles']['walk']['source_raster_roles'],['idle'])
        self.assertFalse(result['source_behavior_certified'])

    def test_live_evidence_never_promotes_model_or_wrong_source(self):
        from live_actor_evidence import attach_entity_evidence
        report={'project_id':'project','models':{'subject':{'ir':{'source_sha256':'source'},
            'lowering_profiles':{'SOURCE_EXACT':{'status':'BLOCKED'}}}}}
        proof=dict(status='PASS',project_id='project',production_rom_sha256='rom',production_artifacts_unchanged=True,
            source_hashes={'Subject':'source'},proof=dict(status='PASS',
                cases=[{'actor':'Subject','force':5}],organic_attack_selection=False,
                organic_spawn=False,source_raster_alignment=False,full_damage_callback=False,
                full_actor_certification=False))
        result=attach_entity_evidence(report,proof,proof_sha256='proof',runtime_sha256='rom')
        self.assertEqual(result['whole_actor_certificates_added'],0)
        self.assertEqual(report['models']['subject']['lowering_profiles']['SOURCE_EXACT']['status'],'BLOCKED')
        proof['source_hashes']['Subject']='wrong'
        with self.assertRaisesRegex(ValueError,'SOURCE_MISMATCH'):
            attach_entity_evidence(report,proof,proof_sha256='proof',runtime_sha256='rom')
        proof['project_id']='foreign'
        with self.assertRaisesRegex(ValueError,'PROJECT_MISMATCH'):
            attach_entity_evidence(report,proof,proof_sha256='proof',runtime_sha256='rom')


if __name__=='__main__': unittest.main()
