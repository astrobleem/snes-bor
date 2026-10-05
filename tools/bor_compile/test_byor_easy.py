"""Focused original Easy source coverage and differential migration gates."""
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from compiler import ROOT, Source, project, stage
from normal_coverage import inventory
from production_campaign import compile_queues
from easy_differential import compare
import sys
sys.path[:0]=[str(ROOT),str(ROOT/'tools/audio')]
import byor
import build_rom
import shipped_content as shipped


class EasyConvergenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory=inventory(source_set='Easy')
        cls.baseline=json.loads((ROOT/'docs/receipts/byor-easy-m3-baseline.json').read_text())

    def test_source_route_capacity_and_native_bindings(self):
        r=self.inventory
        self.assertEqual((r['source_set_id'],r['ifcomplete']),(0,0))
        self.assertEqual(len(r['entries']),16)
        stages=[e for e in r['entries'] if e['kind']=='stage']
        self.assertEqual([e['physical_id'] for e in stages],[0,1,2,*range(11,22)])
        self.assertEqual(sum(e['packed_records'] for e in stages),667)
        self.assertEqual(sum(e['queue_records'] for e in stages),664)
        self.assertEqual(sum(len(e['queue_bindings']) for e in stages),545)
        self.assertEqual(sum(e['hole_prefix'] for e in stages),3)
        self.assertEqual([e['ordinal'] for e in r['entries'] if e['next_after']],[2,3,6,8,10,14])
        self.assertEqual(r['structural_coverage']['status'],'COMPLETE')
        self.assertTrue(all(c['queue_identity_policy']=='source-identity' for c in shipped.STAGE_CONFIGS if c['family']=='bor-original'))
        self.assertEqual(r['model_bindings']['ramon']['runtime_slot'],45)
        self.assertEqual(r['model_bindings']['time']['runtime_slot'],46)

    def test_semantic_differential_against_accepted_master(self):
        d=compare(self.baseline,shipped)
        self.assertEqual(d['baseline_master'],'5d9ef2df66b3c132f046db57dcc13e302c5c247d')
        self.assertEqual(d['counts'],dict(LEGACY_EQUIVALENT=512,SOURCE_CORRECTS_LEGACY=249,ACCEPTED_COMPAT=4,REGRESSION=0,UNPROVEN=0))
        self.assertEqual(sum(d['queue_identity_corrections'].values()),238)

    def test_source_mirror_preserves_pose_and_resource_identity(self):
        text=(ROOT/'src/core/source_visual_production.pasm').read_text()
        self.assertIn('SourceVisual_WriteMirror:',text)
        self.assertIn('jsr SourceVisual_ViewportMirrorPiece',text)
        self.assertIn('jsr SourceVisual_WriteCurrentPiece',text)
        self.assertIn('adc #248',text)
        join=text.split('SourceVisual_Emit__x_high_ready:',1)[1].split('jsr SourceVisual_ViewportNormalPiece',1)[0]
        self.assertIn('rep #$31',join)
        self.assertIn('.a16',join)
        for z in range(160,233):
            source_foot=310-z
            native_ground=(4*z+2)//5
            self.assertLessEqual(abs((4*source_foot+2)//5-(248-native_ground)),1)

    def test_oam_request_coordinate_writes_preserve_tile_byte(self):
        text=(ROOT/'src/core/source_visual_production.pasm').read_text()
        writer=text.split('SourceVisual_WriteCurrentPiece:',1)[1].split('rep #$31',1)[0]
        self.assertLess(writer.index('sep #$20'),writer.index('sta.l OamSetSprite_Y'))
        oam=(ROOT/'src/core/oam.pasm').read_text()
        self.assertIn('OamSetSprite_Y    = $7E53AC ; .db',oam)
        self.assertIn('OamSetSprite_Tile = $7E53AD ; .db',oam)
        self.assertNotIn('rep #$20',writer.split('sta.l OamSetSprite_Y')[0])

    def test_pending_visual_lease_reload_and_palette_scratch_ownership(self):
        text=(ROOT/'src/core/source_visual_production.pasm').read_text()
        found=text.split('SourceVisual_SelectResidency__found:',1)[1].split('SourceVisual_SelectResidency__mark:',1)[0]
        self.assertLess(found.index('lda.l SourceVisual_Record'),found.index('lda.l SourceVisual_State+8,x'))
        self.assertIn('tax',found.split('lda.l SourceVisual_State+8,x')[0])
        self.assertNotIn('SourceVisual_Temp+2',text)
        self.assertIn('SourceVisual_PaletteTransferBit = $7E44B0',text)
        # Palette queue masking must not overlap the persistent atlas base.
        self.assertNotEqual(0x7E44B0,0x7E4B50+2)

    def test_palette_reuse_validates_content_identity_and_actor_ownership(self):
        text=(ROOT/'src/core/source_visual_production.pasm').read_text()
        mapped=text.split('SourceVisual_AllocatePalettes__already_mapped:',1)[1].split('SourceVisual_AllocatePalettes__map:',1)[0]
        self.assertIn('jsr SourceVisual_ValidatePaletteMap',mapped)
        self.assertIn('sta.l SourceVisual_State+4,x',mapped)
        self.assertIn('sta.l SourceVisual_State+14,x',mapped)
        validate=text.split('SourceVisual_ValidatePaletteMap:',1)[1].split('SourceVisual_AllocatePaletteIdentity:',1)[0]
        self.assertIn('cmp.l SourceVisual_PaletteGlobalIndex',validate)
        self.assertIn('and.l SourceVisual_PaletteTransferBit',validate)
        self.assertIn('cmp #8',validate)

    def test_missing_real_easy_identity_fails_closed(self):
        from copy import deepcopy
        configs=[c for c in shipped.STAGE_CONFIGS if c.get('source_set_id')==0]
        roster=deepcopy(shipped.ROSTER_CONFIGS)
        roster[45]['runtime_binding_sets']=(1,2,3)
        with self.assertRaisesRegex(ValueError,'MODEL_UNBOUND.*Ramon'):
            compile_queues(configs,roster)

    def test_retired_easy_legacy_identity_policy_is_rejected(self):
        from copy import deepcopy
        cfg=deepcopy(next(c for c in shipped.STAGE_CONFIGS if c.get('source_set_id')==0))
        cfg['queue_identity_policy']='accepted-legacy'
        with self.assertRaisesRegex(ValueError,'QUEUE_IDENTITY_POLICY'):
            compile_queues([cfg],shipped.ROSTER_CONFIGS)

    def test_cli_shared_pipeline(self):
        with patch('build_normal_sa1_candidate.build',return_value=(Path('candidate'),{'candidate':{}})) as build:
            self.assertEqual(byor.main(['build','--set','Easy','--output','candidate']),0)
            build.assert_called_once_with(Path('candidate'),None,source_set='Easy')

    def test_easy_media_resume_keeps_all_original_sets_linked(self):
        import tempfile
        import build_normal_sa1_candidate as candidate
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            (path/'bor.msu').write_bytes(b'fixture')
            with patch.object(build_rom,'write_campaign_include') as gate, \
                 patch.object(build_rom,'build_msu_assets',return_value=(b'repacked',{})), \
                 patch.object(build_rom,'write_source_visual_layout_include'), \
                 patch.object(build_rom,'link_rom',return_value=b'linked'), \
                 patch.object(candidate,'_build_overlay',return_value=(path,{})):
                candidate.build_from_source(path,path,in_place=True,source_set='Easy',repack_media=True)
                gate.assert_called_once_with(normal_candidate=True,hard_candidate=True,bonus_candidate=True)

    def test_all_original_sets_use_shared_dispatch_and_source_flags(self):
        buf=io.StringIO();real_open=open
        def target(path,*a,**kw):return buf if str(path)=='tools/audio/campaign_config.pasm' else real_open(path,*a,**kw)
        with patch('builtins.open',side_effect=target),patch.object(buf,'close'):
            build_rom.write_campaign_include(normal_candidate=True,hard_candidate=True,bonus_candidate=True)
        self.assertIn('BorSet_CampaignMap:\n    .db '+', '.join(['CAMPAIGN_BOR_NORMAL_DEV']*4),buf.getvalue())
        self.assertIn('Campaign_Source_Counts:\n    .db 16, 16, 16, 2',buf.getvalue())
        for name,c in shipped.CAMPAIGN_CONFIGS.items():
            if c.get('family')=='bor-original':
                self.assertEqual(c['completion_policy'],'source-next')
                self.assertEqual(c['completion_flags'],[int(e['next_after']) for e in c['entries']])


if __name__=='__main__':unittest.main()
