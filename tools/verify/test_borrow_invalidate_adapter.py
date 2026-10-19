"""Independent machine-byte, full-leaf and fail-closed evidence checks."""
import copy
import hashlib
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest.mock import patch

import borrow_invalidate_evidence as evidence
import m4_borrow_invalidate_native as native

FIXTURE = Path('out/byor-motu-borrow-invalidate-build-v1/success/native')


def record(kind,clock,*data):
    return 'NB_'+kind+'|'+str(clock)+'|10|40|'+'|'.join(map(str,data))


def hexwords(words):
    return b''.join(word.to_bytes(2,'little') for word in words).hex()


def native_records():
    refs = [0]*768; refs[10] = 0x4000
    table = [0x8001,0x4002,0x800a]+[0]*593
    after_refs = refs.copy(); after_refs[10] = 0xc000
    after_table = table.copy(); after_table[2] = 0xc00a
    before = dict(a=0xabba,x=0x3333,y=0x1111,d=0x3400,dbr=0x7e,sp=0x1ff0,ps=0x44,counter=7)
    after = dict(before,a=0xc000,x=20,ps=0xc4)
    trace = 'd7140ad715c0d01400d015c0'
    return '\n'.join((record('BH_COST',110,'BhInvalidate',3),
        record('BI_ENTRY',110,1,3,*[before[k] for k in evidence.REGISTERS],10,3,1,hexwords(refs),hexwords(table),evidence.CALLER_RETURN),
        record('BI_RTS',470,1,3,evidence.RETURN_OK,*[after[k] for k in evidence.REGISTERS],
               10,3,1,hexwords(after_refs),hexwords(after_table),trace),
        record('BI_EXIT',510,1,3,400,evidence.CALLER_RETURN,*[dict(after,sp=before['sp']+2)[k] for k in evidence.REGISTERS],
               10,3,1,hexwords(after_refs),hexwords(after_table),trace)))


class BorrowInvalidateAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=evidence.ROOT/'out'); self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve()
        self.assertTrue(self.directory.is_relative_to(evidence.ROOT/'out'))
        self.log = self.directory/'mesen.log'

    def test_independent_literal_original_symbols_and_disabled_identity(self):
        result = native.audit_rom((FIXTURE/'bor.sfc').read_bytes(),FIXTURE)['borrow_invalidate']
        self.assertEqual((result['code_bytes'],result['branch_sites']),(63,320))
        control = Path('out/byor-motu-borrow-invalidate-disabled-v1/success/native/bor.sfc')
        self.assertEqual(native.capture.sha(control),evidence.BASE_ROM_SHA256)

    def test_dispatch_helper_and_unrelated_rom_mutations_reject(self):
        from m4_input_controller_native import offset
        original = (FIXTURE/'bor.sfc').read_bytes()
        for pc in (native.PATCH_PC,native.PATCH_PC+2,0x39ab00,0x39ab30,0x39a900,0x398000):
            changed = bytearray(original); changed[offset(pc)] ^= 1
            with self.subTest(pc=hex(pc)),self.assertRaisesRegex(ValueError,'UNAUTHORIZED_ROM_BYTE'):
                native.audit_rom(changed,FIXTURE)

    def test_original_leaf_matches_independent_instruction_model(self):
        from test_borrow_invalidate import _initial,_original
        rng = random.Random(0xB1E)
        for count in (0,1,2,41,95,596):
            for case in range(30):
                table = [rng.randrange(65536) for _ in range(596)]
                refs = [rng.randrange(65536) for _ in range(768)]
                home = rng.randrange(800); prepared = rng.choice((0,1,1,1,2))
                if count and case % 2 == 0:
                    home = rng.randrange(596); table[rng.randrange(count)] = home | rng.choice((0,0x4000,0x8000,0xc000))
                    refs[home] = rng.choice((0,0x4000,0x8000,0xc000,1,0x8005))
                before = dict(a=rng.randrange(65536),x=rng.randrange(65536),y=rng.randrange(65536),
                    d=0x3400,dbr=rng.randrange(256),sp=0x1ff0,ps=rng.randrange(256)&0xcf,counter=0x4321)
                original = _original(_initial(table[:count],refs,owner_id=home,active=prepared,
                    a=before['a'],x=before['x'],y=before['y'],p=before['ps'],dbr=before['dbr'],sp=before['sp']))
                result,outrefs,outtable,trace,pc = evidence.original_leaf(before,home,count,prepared,refs,table)
                expected = {k:original[{'ps':'p'}.get(k,k)] for k in evidence.REGISTERS if k != 'counter'}
                expected['counter'] = before['counter']
                self.assertEqual(result,expected); self.assertEqual(outrefs,original['refs'])
                self.assertEqual(outtable[:count],original['owners']); self.assertEqual(outtable[count:],table[count:])
                writes = ''.join(f'{(a&65535):04x}{v&255:02x}{((a+1)&65535):04x}{v>>8:02x}' for a,v in original['writes'])
                self.assertEqual(trace,writes)

    def test_native_full_state_and_byte_trace(self):
        self.log.write_text(native_records())
        calls = evidence.native_calls(self.log)
        self.assertEqual(len(calls),1); self.assertEqual(calls[0]['master_clocks'],400)
        self.assertTrue(all(calls[0][key] for key in
            ('exact_cpu_context','exact_reference_and_table_state','ordered_write_trace')))

    def test_wrong_cpu_state_return_input_or_ordered_write_rejects(self):
        rows = native_records().splitlines(); original = rows[3].split('|')
        for index,value in ((7,'999'),(8,'0'),(9,'0'),(10,'0'),(11,'0'),(12,'0'),
                            (13,'8191'),(14,'0'),(15,'1'),(16,'11'),(17,'4'),(18,'2')):
            parts = original.copy(); parts[index] = value
            changed = rows.copy(); changed[3] = '|'.join(parts); self.log.write_text('\n'.join(changed))
            with self.subTest(index=index),self.assertRaises(ValueError): evidence.native_calls(self.log)
        for index in (19,20,21):
            parts = original.copy(); parts[index] = ('f' if parts[index][0]!='f' else '0')+parts[index][1:]
            changed = rows.copy(); changed[3] = '|'.join(parts); self.log.write_text('\n'.join(changed))
            with self.subTest(index=index),self.assertRaisesRegex(ValueError,'CALL_REFERENCE_OR_TABLE_STATE|CALL_ORDERED_BYTE_WRITES'):
                evidence.native_calls(self.log)

    def test_missing_duplicate_and_entire_pair_deletion_reject(self):
        rows = native_records().splitlines()
        values = ('\n'.join(rows[:2]),'\n'.join(rows[1:]),'\n'.join(rows+[rows[-1]]),
                  '\n'.join(rows+[record('BH_COST',610,'BhInvalidate',3)]))
        for value in values:
            self.log.write_text(value)
            with self.assertRaisesRegex(ValueError,'CALL_INCOMPLETE|ORIGINAL_ENTRY|EXIT_SEQUENCE'):
                evidence.native_calls(self.log)

    def test_pre_return_snapshot_and_actual_return_are_both_required(self):
        rows = native_records().splitlines()
        for index,value in ((2,None),(2,rows[2].replace('NB_BI_RTS|470','NB_BI_RTS|510')),
                            (3,rows[3].replace('|8178|','|8176|'))):
            changed = rows.copy()
            if value is None: del changed[index]
            else: changed[index] = value
            self.log.write_text('\n'.join(changed))
            with self.assertRaises(ValueError): evidence.native_calls(self.log)
        changed = rows.copy(); parts = changed[2].split('|'); parts[7] = '1'; changed[2] = '|'.join(parts)
        self.log.write_text('\n'.join(changed))
        with self.assertRaisesRegex(ValueError,'RTS_CPU'): evidence.native_calls(self.log)

    def test_current_receipt_pinned_before_parse_and_same_marker_gain_gate(self):
        value = evidence.load_baseline(); value['candidate_epoch3']['master_clocks'] += 1
        path = self.directory/'receipt.json'; path.write_text(json.dumps(value))
        with patch.object(evidence.json,'loads') as loads:
            with self.assertRaisesRegex(ValueError,'BASE_RECEIPT_DIGEST'): evidence.load_baseline(path)
            loads.assert_not_called()
        self.log.write_text(native_records()); current = evidence.native_calls(self.log)
        control = copy.deepcopy(current); control[0]['master_clocks'] = 600
        result = evidence.compare_calls(current,control)
        self.assertEqual(result['3']['saved_clocks'],200)
        for changed in ([],[dict(current[0],home=11)],[dict(current[0],master_clocks=481)]):
            with self.assertRaisesRegex(ValueError,'CONTROL_CALL|LEAF_CPU_GAIN'):
                evidence.compare_calls(changed,control)

    def test_epoch_fields_and_clocks_cannot_regress(self):
        baseline = evidence.load_baseline()
        good = {epoch:dict(baseline['candidate_'+epoch]) for epoch in ('epoch2','epoch3')}
        evidence.verify_timing(good,baseline)
        for epoch in good:
            for key in ('fields','master_clocks'):
                bad = copy.deepcopy(good); bad[epoch][key] += 1
                with self.subTest(epoch=epoch,key=key),self.assertRaisesRegex(ValueError,'REGRESSION'):
                    evidence.verify_timing(bad,baseline)

    def timing_fixture(self):
        full = evidence.load_native_baseline(evidence.load_baseline())
        return {'cases':{name:{key:copy.deepcopy(row[key]) for key in
            ('observed_fields','transactions','transition_fields') if key in row}
            for name,row in full['cases'].items()}}

    def test_complete_native_baseline_is_pinned_before_parse(self):
        baseline = evidence.load_baseline()
        baseline['retained_full_native_receipt']['sha256'] = '0'*64
        with patch.object(evidence.capture.json,'loads') as loads:
            with self.assertRaisesRegex(ValueError,'BASE_NATIVE_RECEIPT_DIGEST'):
                evidence.load_native_baseline(baseline)
            loads.assert_not_called()

    def test_successful_restoration_transaction_clock_regression_rejects(self):
        baseline = self.timing_fixture();evidence.compare_case_timings(baseline,baseline)
        for key in ('master_clocks','fields'):
            current = copy.deepcopy(baseline)
            current['cases']['valid']['transactions'][-1][key] += 1
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'CASE_TRANSACTION_.*REGRESSION:valid:4'):
                evidence.compare_case_timings(current,baseline)

    def test_abort_clock_and_observed_field_regressions_reject(self):
        baseline = self.timing_fixture()
        current = copy.deepcopy(baseline);current['cases']['early']['transactions'][-1]['master_clocks'] += 76
        with self.assertRaisesRegex(ValueError,'CASE_TRANSACTION_CLOCK_REGRESSION:early:3'):
            evidence.compare_case_timings(current,baseline)
        current = copy.deepcopy(baseline);current['cases']['right']['observed_fields'] += 1
        with self.assertRaisesRegex(ValueError,'CASE_FIELD_REGRESSION:right'):
            evidence.compare_case_timings(current,baseline)

    def test_missing_case_or_transaction_inventory_rejects(self):
        baseline = self.timing_fixture()
        current = copy.deepcopy(baseline);del current['cases']['valid']
        with self.assertRaisesRegex(ValueError,'CASE_TIMING_INVENTORY'):
            evidence.compare_case_timings(current,baseline)
        current = copy.deepcopy(baseline);current['cases']['valid']['transactions'].pop()
        with self.assertRaisesRegex(ValueError,'CASE_TRANSACTION_INVENTORY:valid'):
            evidence.compare_case_timings(current,baseline)

    def control_fixture(self):
        root = self.directory/'control'; folder = root/'success'; native_dir = folder/'native'
        native_dir.mkdir(parents=True); (root/'capture-runtime').mkdir()
        (native_dir/'bor.sfc').write_bytes(b'control'); (native_dir/'bor.msu').write_bytes(b'msu')
        (folder/'contract.json').write_text('{"borrow_invalidate":false}')
        (root/'capture-runtime/capture-runtime.json').write_text('{"initial_sram":{}}')
        (native_dir/'field-0000.png').write_bytes(b'png'); (native_dir/'field-0000.vram').write_bytes(bytes(65536))
        fields = [dict(index=0,ppu=dict(frameCount=10),
            screenshot_sha256=native.capture.sha(native_dir/'field-0000.png'),
            vram_sha256=native.capture.sha(native_dir/'field-0000.vram'))]
        (folder/'fields.json').write_text(json.dumps(fields))
        self.addCleanup(patch.stopall)
        patch.object(evidence,'BASE_ROM_SHA256',hashlib.sha256(b'control').hexdigest()).start()
        patch.object(evidence.capture,'MSU_SHA256',hashlib.sha256(b'msu').hexdigest()).start()
        patch.object(evidence.ready,'runtime_initial_sram',return_value={'verified':True}).start()
        return root

    def test_control_seal_is_single_use_and_checks_complete_inventory(self):
        root = self.control_fixture(); digest = evidence.seal_control(root)
        self.assertEqual(evidence.verify_control(root,digest)['coverage']['fields'],1)
        with self.assertRaisesRegex(ValueError,'ALREADY_EXISTS'): evidence.seal_control(root)
        (root/'success/native/unlisted.bin').write_bytes(b'new')
        with self.assertRaisesRegex(ValueError,'CONTROL_RAW_INVENTORY'): evidence.verify_control(root,digest)
        (root/'success/native/unlisted.bin').unlink()
        nested = root/'success/native/nested'; nested.mkdir(); (nested/'bor.msu').write_bytes(b'not the pinned shared media')
        with self.assertRaisesRegex(ValueError,'CONTROL_RAW_INVENTORY'): evidence.verify_control(root,digest)

    def test_control_raw_mutation_and_manifest_tamper_reject(self):
        root = self.control_fixture(); digest = evidence.seal_control(root)
        path = root/'success/fields.json'; original = path.read_bytes(); path.write_text('[]')
        with self.assertRaisesRegex(ValueError,'CONTROL_HASH_OR_DUPLICATE'): evidence.verify_control(root,digest)
        path.write_bytes(original)
        manifest = root/evidence.CONTROL_MANIFEST; manifest.write_text('{}')
        with self.assertRaisesRegex(ValueError,'CONTROL_MANIFEST_DIGEST'): evidence.verify_control(root,digest)

    def test_control_root_escape_rejects_before_manifest_read(self):
        with patch.object(evidence.capture,'_pinned_json') as reads:
            with self.assertRaisesRegex(ValueError,'CONTROL_ROOT_ESCAPE'):
                evidence.verify_control(evidence.ROOT.parent,'a'*64)
            reads.assert_not_called()

    def test_candidate_corruption_rejects_before_control_or_original_certifier(self):
        from test_fused_capture_evidence import make_capture,write_json
        root,seal = make_capture(self.directory,count=12)
        fields = json.loads((root/'success/fields.json').read_bytes()); del fields[10]
        write_json(root/'success/fields.json',fields)
        real = native.capture.verify_capture
        def verify(folder,chosen=native.capture.RETAINED_SEAL):
            return {} if Path(folder).resolve()==native.BASELINE.resolve() else real(folder,chosen,base=self.directory)
        with patch.object(native.capture,'verify_capture',side_effect=verify), \
             patch.object(evidence,'verify_control') as control,patch.object(native.accepted,'collect_suite') as certify:
            with self.assertRaisesRegex(ValueError,'COPY_SOURCE_HASH|RAW_INPUT_HASH'):
                native.collect_suite(root,seal,self.directory/'unused','a'*64)
            control.assert_not_called(); certify.assert_not_called()

    def test_existing_pass_is_refused_before_recollection_or_mutation(self):
        receipt = self.directory/'borrow-invalidate-receipt.json'
        original = '{"classification":"BYOR_MOTU_BORROW_INVALIDATE_PASS","old":true}'
        receipt.write_text(original)
        with patch.object(evidence,'load_baseline') as baseline, \
             patch.object(native.capture,'verify_capture') as captures,patch.object(native.accepted,'collect_suite') as certify:
            with self.assertRaisesRegex(ValueError,'EXISTING_PASS_RECEIPT'):
                native.collect_suite(self.directory,evidence.BASE_SEAL,self.directory/'unused','a'*64)
            baseline.assert_not_called();captures.assert_not_called();certify.assert_not_called()
        self.assertEqual(receipt.read_text(),original)

    def test_cli_requires_both_control_and_candidate_pins_without_resealing(self):
        for extra in ([],['--provenance-sha256','a'*64],
                      ['--provenance-sha256','a'*64,'--raw-manifest-sha256','b'*64],
                      ['--control-root','unused']):
            with patch.object(sys,'argv',['inv','--output','unused','--collect-suite',*extra]), \
                 patch.object(native,'collect_suite') as collect,patch.object(native.capture,'seal_native_capture') as seal:
                with self.assertRaisesRegex(ValueError,'PINS_REQUIRED'): native.main()
                collect.assert_not_called(); seal.assert_not_called()

    def collection_context(self,captures,controls=None,after_clocks=400):
        from contextlib import ExitStack
        stack = ExitStack(); self.addCleanup(stack.close)
        control_root = self.directory/'control'; (control_root/'success').mkdir(parents=True)
        (control_root/'success/contract.json').write_text('{"borrow_invalidate":false}')
        for case in native.capture.CASES:
            (self.directory/case).mkdir()
            (self.directory/case/'contract.json').write_text('{"borrow_invalidate":true}')
        self.log.write_text(native_records()); current = evidence.native_calls(self.log)
        control = copy.deepcopy(current); control[0]['master_clocks'] = 600
        current[0]['master_clocks'] = after_clocks
        baseline = evidence.load_baseline()
        report = {epoch:dict(baseline['candidate_'+epoch]) for epoch in ('epoch2','epoch3')}
        report.update(self.timing_fixture())
        stack.enter_context(patch.object(native.capture,'verify_capture',side_effect=captures))
        stack.enter_context(patch.object(evidence,'verify_control',side_effect=[{},{}] if controls is None else controls))
        stack.enter_context(patch.object(evidence,'native_calls',return_value=control))
        stack.enter_context(patch.object(native.accepted,'collect_suite',return_value=report))
        stack.enter_context(patch.object(native,'profile',return_value={'calls':current}))
        return control_root

    def test_post_certification_candidate_mutation_cannot_write_pass(self):
        control = self.collection_context([{}, {'raw':1}, {'raw':2}])
        with self.assertRaisesRegex(ValueError,'RAW_CAPTURE_CHANGED'):
            native.collect_suite(self.directory,evidence.BASE_SEAL,control,'a'*64)
        self.assertFalse((self.directory/'borrow-invalidate-receipt.json').exists())

    def test_post_certification_baseline_mutation_cannot_write_pass(self):
        control = self.collection_context([{'base':1}, {}, {}, {'base':2}])
        with self.assertRaisesRegex(ValueError,'BASELINE_CAPTURE_CHANGED'):
            native.collect_suite(self.directory,evidence.BASE_SEAL,control,'a'*64)
        self.assertFalse((self.directory/'borrow-invalidate-receipt.json').exists())

    def test_post_certification_control_mutation_cannot_write_pass(self):
        control = self.collection_context([{}, {}, {}, {}],controls=[{'control':1},{'control':2}])
        with self.assertRaisesRegex(ValueError,'CONTROL_CAPTURE_CHANGED'):
            native.collect_suite(self.directory,evidence.BASE_SEAL,control,'a'*64)
        self.assertFalse((self.directory/'borrow-invalidate-receipt.json').exists())

    def test_small_cpu_gain_cannot_write_pass(self):
        control = self.collection_context([{}, {}],after_clocks=481)
        with self.assertRaisesRegex(ValueError,'LEAF_CPU_GAIN_BELOW_20_PERCENT'):
            native.collect_suite(self.directory,evidence.BASE_SEAL,control,'a'*64)
        self.assertFalse((self.directory/'borrow-invalidate-receipt.json').exists())

    def test_disabled_candidate_contract_rejects_before_original_certifier(self):
        control = self.collection_context([{}, {}])
        (self.directory/'success/contract.json').write_text('{"borrow_invalidate":false}')
        with self.assertRaisesRegex(ValueError,'CANDIDATE_ENABLED_CONTRACT'):
            native.collect_suite(self.directory,evidence.BASE_SEAL,control,'a'*64)
        native.accepted.collect_suite.assert_not_called()


if __name__ == '__main__':
    unittest.main()
