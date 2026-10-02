"""Focused S1 checks. A green test suite does not turn BLOCKED entries green."""
import tempfile
import unittest
from pathlib import Path

from compiler import ROOT, Source, model_catalog
from certify import (BASE, MSU_SHA, STAGE_REQUIREMENTS, certify, clips_from_msu,
                     queue_record, validate_model, verdict)


class ContractTests(unittest.TestCase):
    def test_every_dependency_required(self):
        bindings=dict.fromkeys(STAGE_REQUIREMENTS,True)
        self.assertEqual(verdict(STAGE_REQUIREMENTS,bindings,[])['status'],'CERTIFIED')
        for name in STAGE_REQUIREMENTS:
            b=bindings.copy();del b[name]
            self.assertEqual(verdict(STAGE_REQUIREMENTS,b,[])['status'],'BLOCKED')
        self.assertEqual(verdict(STAGE_REQUIREMENTS,bindings,[{'reason':'unbound alias'}])['status'],'BLOCKED')

    def test_decode_record_keeps_distinct_fields(self):
        r=queue_record(bytes([1,0,2,0,3,1,77,50,16,31]))
        self.assertEqual((r['trigger'],r['x'],r['y'],r['kind'],r['map'],r['subtype_or_pickup']),(1,2,3,5,1,2))
        self.assertEqual((r['hp_or_2p'],r['item_runtime_id'],r['actor_runtime_id']),(50,16,31))

    def test_unknown_model_directive_cannot_hide_behind_pinned_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'DATA').mkdir()
            (p/'DATA/MODELS.TXT').write_text('load X data/x.txt')
            (p/'DATA/x.txt').write_text('name X\ntype enemy\nteleport 20\nanim idle\n')
            source=Source(p)
            r=validate_model(source,model_catalog(source)['x'],accepted_id=3)
            self.assertEqual(r['status'],'BLOCKED')
            self.assertEqual(r['unknown_directives'][0]['directive'],'teleport')


class GoldenBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
        cls.r=certify(cls.source)

    def test_complete_accepted_layout(self):
        r=self.r['layout']
        self.assertEqual(r['comparison'],'BYTE_IDENTICAL')
        self.assertEqual(r['shadow_sha256'],MSU_SHA)
        self.assertEqual((r['vm_offset'],r['total_size']),(0x585C50,28722026))
        self.assertTrue(r['counts_agree']);self.assertTrue(r['vm_agrees'])
        self.assertEqual(set(r['counts'].values()),{32})

    def test_seven_stale_inputs(self):
        rows=self.r['stale_queues']
        self.assertEqual(len(rows),7)
        self.assertEqual([len(r['differences']) for r in rows],[5,7,4,7,2,25,3])
        for r in rows:
            self.assertTrue(r['compiler_matches_accepted'])
            self.assertTrue(r['worktree_matches_accepted'])
            self.assertNotEqual(r['committed_sha256'],r['accepted_msu_sha256'])
            self.assertEqual(r['compiler_sha256'],r['accepted_msu_sha256'])
            for d in r['differences']:
                for stable in ('trigger','x','y','facing','map','hp_or_2p'):
                    self.assertEqual(d['committed'][stable],d['accepted'][stable])

    def test_source_discovered_reuse_and_tables(self):
        self.assertTrue(self.r['golden_presentation_reuse_matches'])
        self.assertTrue(self.r['golden_queue_reproduction'])
        for row in self.r['golden_runtime_tables']:
            for name in ('audio_matches','scroll_matches','mirror_matches'):
                self.assertTrue(row[name],(row['source_path'],name))

    def test_campaign_source_boundaries_not_availability(self):
        self.assertTrue(self.r['golden_campaign_matches'])
        normal=self.r['golden_campaign_boundaries'][1]
        self.assertEqual(normal['next_flags'],[0,0,1,1,0,0,1,0,1,0])
        self.assertEqual((normal['compiled_prefix'],normal['source_entries']),(10,16))
        self.assertFalse(normal['content_available']);self.assertFalse(normal['selectable'])

    def test_scenes_order_timing_audio_and_media(self):
        for name,nframes in (('rugal',126),('ending',1997)):
            r=self.r['scenes'][f'data/scenes/{name}.txt']
            self.assertEqual(r['status'],'CERTIFIED')
            self.assertTrue(all(r['bindings'].values()))
            self.assertEqual(sum(c['frames'] for c in r['clips']),nframes)
        sewer=self.r['scenes']['data/scenes/sewer.txt']
        self.assertTrue(sewer['source_timing_known'])
        self.assertEqual(sewer['status'],'BLOCKED')
        self.assertEqual([a['delays_ms'] for a in sewer['source']['animations']],[[10000,10000],[5000]])

    def test_full_normal_layout_not_source_certification(self):
        r=self.r['candidate_layouts']['Normal']
        self.assertEqual(r['status'],'LAYOUT_RESOLVED_NOT_SOURCE_CERTIFIED')
        self.assertEqual(r['stage_count'],36)
        self.assertEqual(r['total_size'],29007854)
        self.assertFalse(self.r['full_normal_certified'])
        # S2 checks every model, including accepted actors: an accepted ID
        # alone is no longer a waiver for unbound fall-role attacks/maps.
        self.assertEqual(self.r['golden_stage_status'],{'BLOCKED':24})

    def test_real_runtime_limits_are_not_relabeled_supported(self):
        blockers=[b for e in self.r['entries'] for b in e['blockers']]
        for directive in ('alias','map','coords','water','endhole','blocked','rock','model-contract'):
            self.assertTrue(any(b.get('directive')==directive for b in blockers),directive)
        for e in self.r['entries']:
            if e['status']=='CERTIFIED':
                self.assertFalse(e['blockers']);self.assertFalse(e['missing_bindings'])

    def test_bonus_models_not_fake_enemies(self):
        extra=self.r['extra']
        self.assertEqual(extra['authored_records'],184)
        self.assertEqual(extra['kinds'],{'spawn':166,'wait':7,'group':11})
        self.assertIsNone(extra['packed_records'])
        for name,count in (('crab',50),('lobster',27)):
            self.assertEqual(sum(v for k,v in extra['model_counts'].items() if k.lower()==name),count)
            m=self.r['models'][name]
            self.assertIsNone(m['runtime_id']);self.assertEqual(m['status'],'BLOCKED')
            self.assertFalse(m['missing_media'])
        self.assertEqual((self.r['models']['crab']['type'],self.r['models']['crab']['speed']),('none',9))
        self.assertEqual(len(self.r['models']['lobster']['remaps']),5)
        for name in ('time','ramon'):
            self.assertIsNone(self.r['models'][name]['runtime_id'])

    def test_deterministic_and_no_production_publication(self):
        second=certify(self.source)
        self.assertEqual(self.r,second)
        self.assertFalse(self.r['production_changed'])


if __name__=='__main__': unittest.main()
