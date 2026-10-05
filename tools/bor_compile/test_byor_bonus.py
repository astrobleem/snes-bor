"""Bonus source route, capacity, identity, unlock and front-door gates."""
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from copy import deepcopy
from compiler import ROOT, Source, project, stage, key
from production_campaign import compile_queues, link_campaigns
sys.path[:0]=[str(ROOT),str(ROOT/'tools/audio')]
import shipped_content as shipped
import build_rom
import byor
from queue_abi import plan_build, TARGET_CAPACITY, QueueCapacityError, check_count
from normal_coverage import inventory
from source_noncombat import write_tables

class BonusTests(unittest.TestCase):
    def test_source_inventory_and_link(self):
        r=inventory(source_set='Bonus')
        self.assertEqual((r['source_set_id'],r['ifcomplete']),(3,1))
        self.assertEqual([key(e['source_path']) for e in r['entries']],['data/extra.txt','data/scenes/sewer.txt'])
        self.assertEqual([e['next_after'] for e in r['entries']],[False,False])
        a,b=r['entries']
        self.assertEqual((a['queue_records'],a['hole_prefix'],a['packed_records']),(184,0,184))
        self.assertEqual(len(a['queue_bindings']),166)
        self.assertEqual(b['animation_frames'],3)
        self.assertEqual([x['duration_ms'] for x in b['animations']],[20000,5000])
        self.assertEqual(r['structural_coverage']['status'],'COMPLETE')
        self.assertEqual(r['model_bindings']['crab']['source_type'],'none')
        self.assertEqual(r['model_bindings']['lobster']['source_type'],'enemy')

    def test_large_queue_and_limits(self):
        cfg=[c for c in shipped.STAGE_CONFIGS if c.get('source_set_id')==3]
        blobs=compile_queues(cfg,shipped.ROSTER_CONFIGS)
        self.assertEqual(len(next(iter(blobs.values()))),1840)
        plan=plan_build([dict(project=cfg[0]['pak'],set='Bonus',stage=50,source_path=cfg[0]['source_level'],packed_records=184)])
        self.assertEqual((plan['capacity'],plan['buffer_bytes'],plan['runtime_index_bits']),(184,1840,8))
        self.assertGreaterEqual(TARGET_CAPACITY,255)
        with self.assertRaises(QueueCapacityError):
            check_count(256,project='test',set_name='test',stage=0,source_path='stage')

    def test_long_world_projection_and_target_distance_domain(self):
        # Maximum signed deltas and unsigned Manhattan sums remain exact.
        self.assertLessEqual(2*32767,65535)
        for n in (-16383,-14400,-8191,0,8191,14400,16383):
            h,l=divmod(abs(n),256)
            projected=204*h+(4*(h+l)+2)//5
            self.assertEqual(projected,(4*abs(n)+2)//5)
        self.assertEqual((11520*5+2)//4,14400)
        self.assertLessEqual(13106*5+2,65535)

    def test_noncombat_activation_is_not_a_name_alias(self):
        text=(ROOT/'src/core/actor_behavior.pasm').read_text()
        self.assertIn('.include "../generated/source_noncombat.pasm"',text)
        self.assertNotIn('LOBSTER',text)
        self.assertNotIn('CRAB',text)
        self.assertIn('ActorBehavior_ModelFlags,x',text)
        self.assertIn('cmp.l Game_StageIndex',text)
        self.assertIn('cmp.l Spawn_Index',text)

    def test_scene_source_lowering(self):
        sys.path.insert(0,str(ROOT/'tools/scene_video'))
        from scene_sequences import source_sequences
        from convert_ending import CLIP_IDS
        from convert_rugal import SOURCE_PATH
        source=Source(shipped.STAGE_CONFIGS[0]['pak'])
        ids={key(SOURCE_PATH):1, **{key(f'DATA/SCENES/{n}.GIF'):v for n,v in CLIP_IDS.items()}}
        rows=source_sequences(source,shipped.SCENE_CONFIGS,lambda _:9,ids)
        self.assertEqual(rows[-1],dict(scene_id=3,audio_track=9,audio_repeat=1,clips=[7,6]))
        ids.pop(key('DATA/SCENES/SEWER.GIF'))
        with self.assertRaisesRegex(ValueError,'SCENE_CLIP_UNBOUND'):
            source_sequences(source,shipped.SCENE_CONFIGS,lambda _:9,ids)

    def test_missing_identity_and_scene_fail_closed(self):
        cfg=[c for c in shipped.STAGE_CONFIGS if c.get('source_set_id')==3]
        roster=deepcopy(shipped.ROSTER_CONFIGS)
        for r in roster:
            if r['source_character'].endswith('LOBSTER'): r['runtime_binding_sets']=()
        with self.assertRaisesRegex(ValueError,'MODEL_UNBOUND.*Lobster'):
            compile_queues(cfg,roster)
        with self.assertRaisesRegex(ValueError,'SCENE_MEDIA_UNBOUND'):
            link_campaigns(shipped.STAGE_CONFIGS,shipped.CAMPAIGN_CONFIGS,
                [s for s in shipped.SCENE_CONFIGS if s['scene_id']!='SEWER'])

    def test_compiler_noncombat_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            r=write_tables(shipped.STAGE_CONFIGS,shipped.ROSTER_CONFIGS,Path(d)/'tables.pasm')
            self.assertEqual(len(r['records']),50)
            source=Source(shipped.STAGE_CONFIGS[0]['pak'])
            ir=stage(source,'DATA/EXTRA.TXT')
            self.assertEqual([(i,x) for p,i,x in r['records']],[(i,q.coords[0]) for i,q in enumerate(ir.queue) if q.character and q.character.casefold()=='crab'])

    def test_worker_keeps_all_available_campaign_models(self):
        from build_normal_sa1_candidate import _campaign_inputs
        _,normal=_campaign_inputs('Normal')
        _,bonus=_campaign_inputs('Bonus')
        self.assertTrue({r['runtime_slot'] for r in normal}.issubset({r['runtime_slot'] for r in bonus}))
        self.assertEqual(len(bonus),len(normal)+1)
        self.assertIn('lobster',{r['name'] for r in bonus})
        self.assertNotIn('crab',{r['name'] for r in bonus})

    def test_front_door_delegates_shared_pipeline(self):
        with patch('build_normal_sa1_candidate.build',return_value=(Path('candidate'),{'candidate':{}})) as build:
            self.assertEqual(byor.main(['build','--set','Bonus','--output','candidate']),0)
            build.assert_called_once_with(Path('candidate'),None,source_set='Bonus')

    def test_front_door_resumes_same_shared_candidate(self):
        with patch('build_normal_sa1_candidate.build_from_source',return_value=(Path('candidate'),{'candidate':{}})) as build:
            self.assertEqual(byor.main(['build','--set','Bonus','--output','candidate',
                                       '--source-image','candidate']),0)
            build.assert_called_once_with(Path('candidate'),Path('candidate'),
                in_place=True,relink_source=True,source_set='Bonus')

    def test_front_door_repacks_regenerated_media_through_shared_builder(self):
        with patch('build_normal_sa1_candidate.build_from_source',return_value=(Path('candidate'),{'candidate':{}})) as build:
            self.assertEqual(byor.main(['build','--set','Bonus','--output','candidate',
                '--source-image','candidate','--repack-media']),0)
            build.assert_called_once_with(Path('candidate'),Path('candidate'),
                in_place=True,relink_source=True,source_set='Bonus',repack_media=True)

    def test_noncombat_consumes_canonical_epoch_with_sparse_callbacks(self):
        text=(ROOT/'src/core/actor_behavior.pasm').read_text()
        self.assertIn('ActorBehavior_SourceEpoch = $7E1774',text)
        self.assertIn('sbc.l ActorBehavior_LastFrame,x',text)
        self.assertIn('sta.l ActorBehavior_SourceDebt',text)
        body=text.split('ActorBehavior_Think__source_tick:',1)[1].split('ActorBehavior_Think__rational_clock:',1)[0]
        self.assertIn('inc $0C',body)
        self.assertIn('jsl S5_HostSourceTick',body)
        self.assertIn('bra ActorBehavior_Think__source_tick',body)
        # Committed time, including wrap, is independent of callback spacing.
        epochs=[65520,65530,14,14,121,500]
        last=epochs[0]; ticks=0
        for epoch in epochs[1:]:
            ticks+=(epoch-last)&65535
            last=epoch
        self.assertEqual(ticks,(500-65520)&65535)

    def test_generated_available_is_separate_from_unlock(self):
        buf=io.StringIO(); real_open=open
        def target(path,*a,**kw):
            return buf if str(path)=='tools/audio/campaign_config.pasm' else real_open(path,*a,**kw)
        with patch('builtins.open',side_effect=target),patch.object(buf,'close'):
            build_rom.write_campaign_include(normal_candidate=True,hard_candidate=True,bonus_candidate=True)
        self.assertIn('BorSet_ContentAvailable:\n    .db 1, 1, 1, 1',buf.getvalue())
        self.assertIn('BorSet_IfComplete:\n    .db 0, 0, 0, 1',buf.getvalue())
        self.assertIn('Campaign_Source_Counts:\n    .db 0, 16, 16, 2',buf.getvalue())

    def test_bonus_rejects_incomplete_candidate_family(self):
        with self.assertRaisesRegex(SystemExit,'BONUS_REQUIRES_COMPLETE_SOURCE_SIZED_CANDIDATE'):
            build_rom.main(bonus_candidate=True)

    def test_viewport_admission_preserves_every_visible_authored_pixel(self):
        # Rectangle admission must agree with authored per-pixel origins,
        # including the compiler's mirrored +1 convention at screen edges.
        for width,origin in ((1,0),(98,43),(141,71)):
            for base in range(-250,450):
                for left in (False,True):
                    start=base+origin-width+1 if left else base-origin
                    admitted=start<256 and start+width>0
                    pixels=[base+origin-x if left else base-origin+x for x in range(width)]
                    self.assertEqual(admitted,any(0<=x<256 for x in pixels))
        text=(ROOT/'src/core/source_visual_production.pasm').read_text()
        render=text.split('SourceVisual_RenderCurrent__same_field:',1)[1].split('SourceVisual_RenderCurrent__retired:',1)[0]
        self.assertLess(render.index('jsr SourceVisual_FrameInViewport'),render.index('jsr SourceVisual_SelectResidency'))
        self.assertIn('jsl SourceVisual_QueueRetireEntityOffset',render)
        self.assertIn('jsr SourceVisual_ProcessRetired',render)

    def test_visible_pieces_are_repinned_before_block_eviction(self):
        text=(ROOT/'src/core/source_visual_production.pasm').read_text()
        body=text.split('SourceVisual_PrepareBlocks__scan_start:',1)[1].split('SourceVisual_PrepareBlocks__allocated:',1)[0]
        self.assertLess(body.index('jsr SourceVisual_PinVisibleBlocks'),body.index('jsr SourceVisual_AllocateBlock'))
        self.assertIn('jsr SourceVisual_ViewportPiece',body)
        pin=text.split('SourceVisual_PinVisibleBlocks:',1)[1].split('; A cache record',1)[0]
        self.assertIn('ora.l SourceVisual_BlockActorMask',pin)
        self.assertNotIn('sta.l SourceVisual_BlockCache+2,x',pin)

    def test_reused_slot_cannot_resume_another_source_identity(self):
        text=(ROOT/'src/core/source_visual_production.pasm').read_text()
        body=text.split('SourceVisual_SelectResidency:',1)[1].split('SourceVisual_SelectResidency__replace:',1)[0]
        self.assertLess(body.index('lda.l SourceVisual_State+29,x'),body.index('jsr SourceVisual_LoadPendingEntry'))
        self.assertIn('bne SourceVisual_SelectResidency__identity_changed',body)

if __name__=='__main__': unittest.main()
