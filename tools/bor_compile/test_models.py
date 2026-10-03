"""S2: source-only model/environment/resource tests; never run a game."""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from compiler import ROOT, Source, baseline, key, stage
from model_ir import parse_model, validate_model_ir, pickup_effect, UNKNOWN
from analyze import analyze, environment, scoped_id, validate_environment
from regenerate_queues import generate, install
from certify import BASE


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        image=io.BytesIO();Image.new('P',(16,24)).save(image,format='GIF')
        (self.root/'f.gif').write_bytes(image.getvalue())

    def tearDown(self): self.temp.cleanup()

    def parse(self,text):
        (self.root/'actor.txt').write_text(text)
        return parse_model(Source(self.root),'actor.txt','Arbitrary','test-project','historical-bor')

    def test_sticky_state_and_animation_delay_carry(self):
        ir=self.parse('name Arbitrary\ntype enemy\nanim idle\ndelay 7\noffset 2 3\nbbox 1 2 3 4\nattack 1 2 3 4 5 1\nframe f.gif\nframe f.gif\nanim walk\nframe f.gif')
        a,b=ir.animations
        self.assertEqual(a.frames[0].state,a.frames[1].state)
        self.assertEqual(b.frames[0].state,dict(delay=7,offset=[0,0],bbox=[0,0,0,0],attack=None,move=0))
        self.assertEqual(a.frames[0].dimensions,[16,24])

    def test_unknown_and_bad_scalar_are_diagnostics(self):
        ir=self.parse('type enemy\nspeed wrong\nteleport 9\nanim idle\nframe f.gif')
        result=validate_model_ir(ir)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertTrue(any(d['directive']=='teleport' for d in result['diagnostics']))
        self.assertEqual(ir.stats['speed'],'wrong')

    def test_missing_asset_is_not_dummy_frame(self):
        ir=self.parse('anim idle\nframe missing.gif')
        self.assertEqual(len(ir.animations[0].frames),0)
        self.assertEqual(validate_model_ir(ir)['status'],'BLOCKED')
        ir=self.parse('anim idle\nsound missing.wav\nframe f.gif')
        self.assertTrue(any(d['category']=='MISSING_ASSET' for d in validate_model_ir(ir)['diagnostics']))

    def test_unknown_type_and_missing_stage_fail_closed(self):
        ir=self.parse('type magical\nanim idle\nframe f.gif')
        self.assertTrue(any(d['directive']=='type' for d in validate_model_ir(ir)['diagnostics']))
        (self.root/'DATA').mkdir()
        (self.root/'DATA/LEVELS.TXT').write_text('set Test\nfile data/missing.txt')
        (self.root/'DATA/MODELS.TXT').write_text('load Arbitrary actor.txt')
        r=analyze(Source(self.root),'historical-bor')
        self.assertEqual(r['summary']['stage_entries'],1)
        self.assertEqual(r['entries'][0]['status'],'BLOCKED')

    def test_noncombat_driver_is_not_model_name_specific(self):
        a=self.parse('name NotCrab\ntype none\nspeed 9\nanim walk\nframe f.gif')
        r=validate_model_ir(a)
        self.assertEqual(r['behavior']['source_speed'],'9/10')
        self.assertEqual(r['behavior']['driver'],'noncombat_horizontal_drift')
        self.assertEqual(r['status'],'BLOCKED')

    def test_five_maps_and_fall_attack_survive(self):
        ir=self.parse('type enemy\n'+('remap f.gif f.gif\n'*5)+'anim fall\nattack 0 0 8 8 12 1\nframe f.gif')
        r=validate_model_ir(ir)
        self.assertEqual(len(ir.remaps),5)
        self.assertFalse(any(d['directive']=='remap' for d in r['diagnostics']))
        self.assertTrue(any(d['animation_role']=='fall' for d in r['diagnostics']))
        self.assertEqual(ir.animations[0].frames[0].state['attack']['force'],12)

    def test_engine_pickup_rule_is_not_actor_alias(self):
        self.assertEqual(pickup_effect('historical-bor','TIME'),'reset_timer')
        self.assertEqual(pickup_effect('historical-bor','TIME',health=10),'health')
        self.assertEqual(pickup_effect('historical-bor','TIME',score=10),'score')
        self.assertEqual(pickup_effect('historical-bor','1UP'),'extra_life')
        self.assertEqual(pickup_effect('unspecified','Time'),UNKNOWN)
        ir=self.parse('name 1UP\ntype item\nanim idle\nframe f.gif')
        self.assertEqual(validate_model_ir(ir)['status'],'LOWERABLE_WITH_ADAPTER')

    def test_alias_depth_and_altitude_are_distinct(self):
        (self.root/'stage.txt').write_text('spawn Actor\ncoords 380 155 -5\nalias Display\nmap 5\nat 0')
        ir=stage(Source(self.root),'stage.txt');e=environment(ir)
        self.assertEqual(e.spawn_altitudes,[dict(queue=0,altitude=-5,depth=155)])
        self.assertEqual(e.display_aliases[0]['model'],'Actor')
        self.assertEqual(e.display_aliases[0]['display_alias'],'Display')
        self.assertEqual({d['directive'] for d in validate_environment(ir)['diagnostics']},{'alias','coords'})

    def test_project_scope_is_content_not_directory(self):
        ir=self.parse('name Same\nanim idle\nframe f.gif')
        first=scoped_id(Source(self.root))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for p in self.root.iterdir(): (root/p.name).write_bytes(p.read_bytes())
            self.assertEqual(first,scoped_id(Source(root)))
            (root/'actor.txt').write_text('name Same\nspeed 9')
            second=scoped_id(Source(root))
            self.assertNotEqual(first,second)
            other=parse_model(Source(root),'actor.txt','Same',second)
            self.assertNotEqual(ir.identity,other.identity)


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
        cls.r=analyze(cls.source,'historical-bor')

    def test_four_models_use_one_ir_and_explicit_blockers(self):
        for name in ('time','ramon','crab','lobster'):
            m=self.r['models'][name]
            expected='LOWERABLE_WITH_ADAPTER' if name=='ramon' else 'BLOCKED'
            self.assertEqual(m['capability']['status'],expected,name)
            self.assertTrue(m['ir']['animations'])
            self.assertFalse(m['capability']['certified'])
        self.assertEqual(len(self.r['models']['lobster']['ir']['remaps']),5)
        self.assertEqual(self.r['models']['crab']['capability']['behavior']['source_speed'],'9/10')

    def test_bonus_and_resource_requirements(self):
        extra=next(e for e in self.r['entries'] if key(e['source_path'])=='data/extra.txt')
        self.assertEqual(extra['authored_queue_count'],184)
        self.assertEqual(extra['packed_queue_candidate_count'],184)
        self.assertIn('crab',extra['required_models']);self.assertIn('lobster',extra['required_models'])
        normal=next(e for e in self.r['entries'] if key(e['source_path'])=='data/normal/5b.txt')
        self.assertEqual(normal['packed_queue_candidate_count'],94)
        self.assertFalse(any(d['directive']=='queue_capacity' for d in normal['diagnostics']))
        self.assertLessEqual(normal['packed_queue_candidate_count'],self.r['resources']['limits']['queue_records'])
        self.assertFalse(self.r['publication']['enabled'])

    def test_analysis_determinism(self):
        self.assertEqual(self.r,analyze(self.source,'historical-bor'))

    def test_real_other_paks_without_custom_parser(self):
        for filename,counts in (
            ('Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak',(1,4,2,67)),
            ('Masters of the Universe [v.3.0 Build 4086].pak',(1,2,0,16))):
            path=ROOT/filename
            if not path.exists(): continue  # Optional local content; never download.
            r=analyze(Source(path))
            self.assertEqual(tuple(r['summary'][k] for k in ('sets','stage_entries','scene_entries','source_models')),counts)
            self.assertEqual(r['summary']['certified'],0)
            self.assertTrue(r['project']['diagnostics'])
            self.assertNotEqual(r['project_id'],self.r['project_id'])
            self.assertFalse(r['publication']['enabled'])

    def test_clean_committed_queue_tree_regeneration(self):
        cfg,git=baseline(BASE)
        # Reject any dependency on historical dirty queue bytes during generation.
        read=Path.read_bytes
        def guarded(path):
            if path.name=='spawn_table.bin' and path.is_relative_to(ROOT/'out'):
                raise AssertionError('generator read worktree derived queue')
            return read(path)
        with patch.object(Path,'read_bytes',guarded):
            candidates=generate(self.source,ROOT/'distribution/bor.msu')
        self.assertEqual(len(candidates),24)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for path in candidates:
                target=root/path;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(git(path))
            changed=install(candidates,root)
            self.assertEqual(set(changed),{f'out/spawn_{s}/spawn_table.bin' for s in
                ('3easy','3beasy','3ceasy','4aeasy','4beasy','5aeasy','5beasy')})
            self.assertEqual(install(candidates,root),[])
            for path,data in candidates.items(): self.assertEqual((root/path).read_bytes(),data)


if __name__=='__main__': unittest.main()
