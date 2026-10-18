"""Regression guards for the local EC observer and comparison adapter."""
from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch

import m4_exact_coverage_native as native


def example(rows=8):
    return {'transactions': {'3': {'calls': 2, 'covered': 1,
        'helper_clocks': 100, 'mark_clocks': [200],
        'verdicts': [dict(tile=4, covered=True, value=255, row_counter=rows),
                     dict(tile=5, covered=False, value=0, row_counter=8)]}}}


def checkpoint_fixture(folder,case):
    # Independent literal fixture for the three accepted checkpoint shapes.
    worlds={'cold','deferred','moved','newer'}
    states={'cold','deferred','moved','before-second','after-second'}
    if case=='valid':worlds.add('restoration');states.add('after-restoration')
    if case=='right':worlds=states={'cold','deferred','moved','left','noop'}
    names={s+'-world.bin' for s in worlds}
    names|={s+'-'+kind+'.bin' for s in states for kind in ('committed','pending','refs','cgram','vram')}
    names.add('initial-vram.bin')
    if case=='right':names.add('handoff-vram.bin')
    folder.mkdir(parents=True)
    for name in names:(folder/name).write_bytes(b'checkpoint')
    return names


def baseline_fixture(folder):
    (folder/'native').mkdir()
    rom=b'pinned Q8 control fixture'
    (folder/'native/bor.sfc').write_bytes(rom)
    rom_sha=hashlib.sha256(rom).hexdigest()
    profile=dict(rom_sha256=rom_sha,**example())
    encoded=json.dumps(profile,indent=2).encode()
    (folder/'exact-coverage-profile.json').write_bytes(encoded)
    return rom_sha,hashlib.sha256(encoded).hexdigest(),profile


class ExactCoverageAdapterTests(unittest.TestCase):
    def test_collection_keeps_profile_separate_from_timing_baselines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'success/native').mkdir(parents=True)
            (root/'success/native/bor.sfc').write_bytes(b'ROM')
            (root/'success/exact-coverage-profile.json').write_text(json.dumps(example()))
            baseline=dict(epoch2=dict(fields=23,master_clocks=1000),
                          epoch3=dict(fields=35,master_clocks=1500),
                          cases=dict(right=dict(transition_fields=23)))
            report=dict(epoch2=dict(fields=23,master_clocks=1000),
                        epoch3=dict(fields=33,master_clocks=1200),
                        cases=dict(right=dict(transition_fields=23)))
            original_read=Path.read_text
            def read(path,*args,**kwargs):
                if path==Path('docs/receipts/byor-motu-eight-pair-direct.json'):
                    return json.dumps(baseline)
                return original_read(path,*args,**kwargs)
            with patch.object(native,'load_baseline_profile',return_value=example()),\
                 patch.object(native.q8,'CASES',()),patch.object(native.q8,'collect_suite',return_value=report),\
                 patch.object(native.q8,'sha',return_value=native.BASE_SHA),patch.object(native,'audit_rom',return_value={}),\
                 patch.object(Path,'read_text',autospec=True,side_effect=read):
                result=native.collect_suite(root)
            self.assertEqual(result['exact_coverage']['3']['calls'],2)
            self.assertEqual(result['baseline_q8_epoch3'],baseline['epoch3'])

    def test_checkpoint_inventory_accepts_all_exact_case_sets(self):
        for case in native.q8.CASES:
            with self.subTest(case=case),tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp)/'native';names=checkpoint_fixture(folder,case)
                self.assertEqual(len(names),36 if case=='valid' else 32 if case=='right' else 30)
                self.assertEqual(native.require_checkpoint_inventory(folder,case),sorted(names))

    def test_checkpoint_inventory_rejects_missing_capture_of_each_kind(self):
        for suffix in ('world','committed','pending','refs','cgram','vram'):
            with self.subTest(suffix=suffix),tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp)/'native';checkpoint_fixture(folder,'success')
                (folder/('cold-'+suffix+'.bin')).unlink()
                with self.assertRaisesRegex(ValueError,'CHECKPOINT_INVENTORY:missing=cold-'):
                    native.require_checkpoint_inventory(folder,'success')

    def test_checkpoint_inventory_rejects_unexpected_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'native';checkpoint_fixture(folder,'success')
            (folder/'unexpected-world.bin').write_bytes(b'capture')
            with self.assertRaisesRegex(ValueError,'extra=unexpected-world.bin'):
                native.require_checkpoint_inventory(folder,'success')

    def test_checkpoint_inventory_rejects_directory_in_place_of_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'native';checkpoint_fixture(folder,'success')
            (folder/'cold-vram.bin').unlink();(folder/'cold-vram.bin').mkdir()
            with self.assertRaisesRegex(ValueError,'CHECKPOINT_NOT_FILE'):
                native.require_checkpoint_inventory(folder,'success')

    def test_collection_checks_candidate_and_control_inventories_before_certifying(self):
        for missing_side in ('candidate','control'):
            with self.subTest(side=missing_side),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);candidate=root/'candidate';control=root/'control'
                for parent in (candidate,control):checkpoint_fixture(parent/'success/native','success')
                parent=candidate if missing_side=='candidate' else control
                (parent/'success/native/cold-pending.bin').unlink()
                with patch.object(native,'load_baseline_profile',return_value={}),\
                     patch.object(native,'BASELINE',control),patch.object(native.q8,'CASES',('success',)),\
                     patch.object(native.q8,'collect_suite') as certify:
                    with self.assertRaisesRegex(ValueError,'CHECKPOINT_INVENTORY'):
                        native.collect_suite(candidate)
                    certify.assert_not_called()

    def test_baseline_profile_accepts_pinned_json_and_rom(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);rom_sha,profile_sha,profile=baseline_fixture(folder)
            with patch.object(native,'BASE_SHA',rom_sha),patch.object(native,'BASE_PROFILE_SHA256',profile_sha):
                self.assertEqual(native.load_baseline_profile(folder),profile)

    def test_baseline_digest_rejects_changed_json_before_certification(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);rom_sha,profile_sha,_=baseline_fixture(folder)
            path=folder/'exact-coverage-profile.json';path.write_bytes(path.read_bytes()+b'\n')
            with patch.object(native,'BASE_SHA',rom_sha),patch.object(native,'BASE_PROFILE_SHA256',profile_sha),\
                 patch.object(native.q8,'collect_suite') as certify,\
                 patch.object(native,'require_checkpoint_inventory') as inventory:
                with self.assertRaisesRegex(ValueError,'BASELINE_PROFILE_DIGEST'):
                    native.collect_suite(folder/'absent-candidate',profile_base=folder)
                certify.assert_not_called();inventory.assert_not_called()

    def test_baseline_profile_rejects_missing_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'BASELINE_PROFILE_MISSING'):
                native.load_baseline_profile(Path(tmp))

    def test_baseline_profile_still_rejects_changed_rom(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);rom_sha,profile_sha,_=baseline_fixture(folder)
            (folder/'native/bor.sfc').write_bytes(b'changed ROM')
            with patch.object(native,'BASE_SHA',rom_sha),patch.object(native,'BASE_PROFILE_SHA256',profile_sha):
                with self.assertRaisesRegex(ValueError,'PROFILE_CONTROL_HASH'):
                    native.load_baseline_profile(folder)

    def test_boolean_equivalence_does_not_require_same_nonzero_mask(self):
        old=example();new=example(1)
        new['transactions']['3']['verdicts'][0]['value']=1
        result=native.compare_profiles(new,old)['3']
        self.assertEqual((result['rows_visited'],result['baseline_rows_visited']),(9,16))

    def test_cell_order_and_verdict_must_match(self):
        for change in ('order','tile','verdict'):
            new=example();rows=new['transactions']['3']['verdicts']
            if change=='order':rows.reverse()
            elif change=='tile':rows[0]['tile']=6
            else:rows[0]['covered']=False
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'EXACT_CELL_VERDICT_DRIFT'):
                native.compare_profiles(new,example())

    def test_missing_transaction_and_bad_row_counts_reject(self):
        with self.assertRaisesRegex(ValueError,'COVERAGE_TRANSACTIONS'):
            native.compare_profiles({'transactions':{}},example())
        for count in (0,9):
            with self.subTest(count=count),self.assertRaisesRegex(ValueError,'ROW_VISIT_DOMAIN'):
                native.compare_profiles(example(count),example())

    def test_observer_has_separate_lua_end_tokens_and_real_phase_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            script=Path(tmp)/'observer.lua'
            sy=dict(OnlineCoverage=10,NbBeginRetry=20,NbRestorePlanStart=30,
                    NbAllPairsReady=40,NbAbort=50,NbVisible=60)
            with patch.object(native,'Q8_OBSERVER'),patch.object(native,'coverage_return',return_value=11):
                native.observer(script,dict(native_symbols=sy))
            text=script.read_text()
            self.assertNotIn('endend',text)
            self.assertEqual(text.count('emu.addMemoryCallback('),7)
            self.assertIn(' end,emu.callbackType.exec,40,40,',text)

    def test_candidate_observer_uses_new_helper_and_return(self):
        with tempfile.TemporaryDirectory() as tmp:
            script=Path(tmp)/'observer.lua'
            sy=dict(OnlineCoverage=10,NbBeginRetry=20,NbRestorePlanStart=30,
                    NbAllPairsReady=40,NbAbort=50,NbVisible=60,EcCoverage=70,EcHit=100)
            with patch.object(native,'Q8_OBSERVER'),patch.object(native,'coverage_return',return_value=11):
                native.observer(script,dict(native_symbols=sy))
            text=script.read_text()
            self.assertIn('exec,70,70,',text)
            self.assertIn('exec,100,100,',text)
            self.assertNotIn('exec,10,10,',text)

    def test_existing_root_rejects_before_capture_or_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('sys.argv',['ec','--output',tmp,'--build-only']),\
                 patch.object(native.q8,'build') as build,\
                 patch.object(native.q8,'configure_capture_runtime') as configure:
                with self.assertRaisesRegex(ValueError,'OUTPUT_MUST_BE_NEW'):native.main()
                build.assert_not_called();configure.assert_not_called()

    def test_disabled_control_delegates_unchanged_q8_builder(self):
        contract={}
        with patch.object(native.q8,'build',return_value=contract) as build,\
             patch.object(native.q8,'sha',return_value=native.BASE_SHA),\
             patch.object(native,'audit_rom') as audit:
            self.assertIs(native.build(Path('absent-child'),disabled=True),contract)
            build.assert_called_once_with(Path('absent-child'))
            audit.assert_not_called()

    def test_profile_rejects_unfiltered_callback_and_native_faults(self):
        for line in ('callback_owner.lua:1: syntax error','NB_FAULT|10|1|0|EC_COVER_NESTED'):
            with self.subTest(line=line),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'native').mkdir()
                (root/'native/mesen.log').write_text(line+'\n')
                with self.assertRaises(ValueError):native.profile(root,required=False)

    def test_profile_requires_exact_pass_and_one_mark(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'native').mkdir()
            log=root/'native/mesen.log';log.write_text('')
            with self.assertRaisesRegex(ValueError,'MISSING_EXACT_PASS'):native.profile(root)
            log.write_text('NB_EC_COVER|10|1|0|3|4|20|1|1\n')
            with self.assertRaisesRegex(ValueError,'MISSING_EXACT_PASS'):native.profile(root)


if __name__=='__main__':unittest.main()
