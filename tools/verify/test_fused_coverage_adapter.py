"""Independent ROM mutation and performance guards for the fused scanner."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import m4_fused_coverage_native as native

FIXTURE=Path('out/byor-motu-fused-coverage-build-v1/success/native')


class FusedCoverageAdapterTests(unittest.TestCase):
    def test_valid_rom_and_preserved_ec_helper(self):
        from m4_input_controller_native import offset
        rom=(FIXTURE/'bor.sfc').read_bytes()
        result=native.audit_rom(rom,FIXTURE)['fused_coverage']
        self.assertEqual(result['status'],'PASS')
        original=(native.BASE/'bor.sfc').read_bytes()
        self.assertEqual(rom[offset(0x39A700):offset(0x39A71F)],
                         original[offset(0x39A700):offset(0x39A71F)])

    def test_rom_mutations_reject_call_opcode_operand_helper_and_unrelated_byte(self):
        from m4_input_controller_native import offset
        from actor_s5_entity_fixture import symbols
        original=(FIXTURE/'bor.sfc').read_bytes()
        sy=symbols(native.BASE/'publisher.sym')
        lines=(native.BASE/'publisher.pasm').read_text().splitlines()
        call=native.accepted.callsite(lines,sy)
        for pc in (call,call+1,native.fused.CODE_START,0x398000):
            with self.subTest(pc=hex(pc)):
                changed=bytearray(original);changed[offset(pc)]^=1
                with self.assertRaisesRegex(ValueError,'UNAUTHORIZED_ROM_BYTE'):
                    native.audit_rom(changed,FIXTURE)

    def test_accepted_profile_digest_rejects_changed_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'success').mkdir()
            (root/'success/exact-coverage-profile.json').write_text('{"rom_sha256":"'+native.BASE_SHA+'"}')
            with patch.object(native,'BASELINE',root):
                with self.assertRaisesRegex(ValueError,'ACCEPTED_PROFILE_DIGEST'):
                    native.load_accepted_profile()

    def test_timing_requires_clock_and_field_gain_without_epoch2_regression(self):
        baseline={'candidate_epoch2':dict(fields=23,master_clocks=100),
                  'candidate_epoch3':dict(fields=33,master_clocks=200)}
        good={'epoch2':dict(fields=23,master_clocks=100),'epoch3':dict(fields=32,master_clocks=190)}
        native.verify_timing(good,baseline)
        for epoch,key,value in (('epoch2','fields',24),('epoch2','master_clocks',101),
                                ('epoch3','fields',33),('epoch3','master_clocks',200)):
            with self.subTest(epoch=epoch,key=key):
                changed=copy.deepcopy(good);changed[epoch][key]=value
                with self.assertRaisesRegex(ValueError,'ACCEPTED_EPOCH'):
                    native.verify_timing(changed,baseline)

    def test_accepted_checkpoint_inventory_precedes_native_certification(self):
        with patch.object(native.capture,'verify_capture',return_value={}),\
             patch.object(native,'load_accepted_profile',return_value={}),\
             patch.object(native.accepted,'require_checkpoint_inventory',side_effect=ValueError('missing checkpoint')),\
             patch.object(native.accepted,'collect_suite') as certify:
            with self.assertRaisesRegex(ValueError,'missing checkpoint'):
                native.collect_suite(Path('unused'))
            certify.assert_not_called()

    def test_tampered_same_rom_timing_receipt_rejects_before_native_certification(self):
        import fused_timing_baseline as timing
        changed=json.loads(timing.DEFAULT_RECEIPT.read_bytes())
        changed['candidate_epoch3']['fields']+=1
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'receipt.json';path.write_text(json.dumps(changed))
            with patch.object(native,'load_timing_baseline',side_effect=lambda:timing.load_timing_baseline(path)),\
                 patch.object(native.capture,'verify_capture') as evidence,\
                 patch.object(native.accepted,'collect_suite') as certify:
                with self.assertRaisesRegex(ValueError,'FTB_RECEIPT_SHA256'):
                    native.collect_suite(Path('unused'))
                evidence.assert_not_called();certify.assert_not_called()

    def test_deleted_record_index_ten_rejects_before_native_certification(self):
        from test_fused_capture_evidence import make_capture,write_json
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root,seal=make_capture(base,count=12)
            path=root/'success/fields.json';fields=json.loads(path.read_bytes());del fields[10]
            write_json(path,fields)
            real_verify=native.capture.verify_capture
            with patch.object(native.capture,'verify_capture',side_effect=lambda r,s:real_verify(r,s,base=base)),\
                 patch.object(native.accepted,'collect_suite') as certify:
                with self.assertRaisesRegex(ValueError,'COPY_SOURCE_HASH|RAW_INPUT_HASH'):
                    native.collect_suite(root,seal)
                certify.assert_not_called()

    def test_raw_mutation_during_certification_rejects_before_pass_receipt(self):
        from test_fused_capture_evidence import make_capture
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root,seal=make_capture(base)
            real_verify=native.capture.verify_capture
            def certify(_root):
                (root/'success/native/events.log').write_bytes(b'mutated by certifier')
                return dict(observed_fields=24,epoch2=dict(fields=23,master_clocks=8416382),
                            epoch3=dict(fields=32,master_clocks=11676720))
            with patch.object(native.capture,'verify_capture',side_effect=lambda r,s:real_verify(r,s,base=base)),\
                 patch.object(native,'load_accepted_profile',return_value={}),\
                 patch.object(native.accepted,'require_checkpoint_inventory',return_value=[]),\
                 patch.object(native.accepted,'expected_checkpoints',return_value=[]),\
                 patch.object(native.accepted,'collect_suite',side_effect=certify),\
                 patch.object(native,'compare_row_profiles',return_value={}):
                with self.assertRaisesRegex(ValueError,'COPY_SOURCE_HASH|RAW_INPUT_HASH'):
                    native.collect_suite(root,seal)
                self.assertFalse((root/'fused-coverage-receipt.json').exists())

    def test_cli_requires_both_capture_pins_and_collection_mode(self):
        import sys
        for arguments,code in ((['--collect-suite','--provenance-sha256','a'*64],'BOTH_CAPTURE_PINS_REQUIRED'),
                               (['--collect-suite','--raw-manifest-sha256','b'*64],'BOTH_CAPTURE_PINS_REQUIRED'),
                               (['--build-only','--provenance-sha256','a'*64,
                                 '--raw-manifest-sha256','b'*64],'CAPTURE_PINS_REQUIRE_COLLECTION')):
            with self.subTest(arguments=arguments),\
                 patch.object(sys,'argv',['fused','--output','unused',*arguments]),\
                 patch.object(native,'collect_suite') as collect:
                with self.assertRaisesRegex(ValueError,code):native.main()
                collect.assert_not_called()

    def test_cli_default_collection_uses_retained_pins_without_resealing(self):
        import sys
        report=dict(classification='PASS',observed_fields=1,verified_rgb555_pixels=1)
        with patch.object(sys,'argv',['fused','--output','unused','--collect-suite']),\
             patch.object(native,'collect_suite',return_value=report) as collect,\
             patch.object(native.capture,'seal_native_capture') as seal,\
             patch('builtins.print'):
            native.main()
            collect.assert_called_once_with(Path('unused').resolve(),native.capture.RETAINED_SEAL)
            seal.assert_not_called()

    def test_cli_explicit_collection_passes_trusted_pins_without_resealing(self):
        import sys
        report=dict(classification='PASS',observed_fields=1,verified_rgb555_pixels=1)
        with patch.object(sys,'argv',['fused','--output','unused','--collect-suite',
                         '--provenance-sha256','a'*64,'--raw-manifest-sha256','b'*64]),\
             patch.object(native,'collect_suite',return_value=report) as collect,\
             patch.object(native.capture,'seal_native_capture') as seal,\
             patch('builtins.print'):
            native.main()
            collect.assert_called_once_with(Path('unused').resolve(),native.capture.CaptureSeal('a'*64,'b'*64))
            seal.assert_not_called()

    def test_row_profile_rejects_changed_cell_verdict_or_first_hit(self):
        baseline={'transactions':{'3':dict(calls=1,covered=1,helper_clocks=100,mark_clocks=[200],
            verdicts=[dict(tile=12,covered=True,row_counter=8)])}}
        native.compare_row_profiles(baseline,baseline)
        for field,value in (('tile',13),('covered',False),('row_counter',7)):
            with self.subTest(field=field):
                changed=copy.deepcopy(baseline);changed['transactions']['3']['verdicts'][0][field]=value
                with self.assertRaisesRegex(ValueError,'VERDICT_DRIFT|ROW_VISIT_DRIFT'):
                    native.compare_row_profiles(changed,baseline)


if __name__=='__main__':unittest.main()
