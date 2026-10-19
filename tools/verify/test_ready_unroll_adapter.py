"""Native admission, exact write trace, ROM and threshold fault tests."""
import copy,json,re
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import m4_ready_unroll_native as native
import ready_unroll_evidence as evidence


class AdapterTests(unittest.TestCase):
    def rows(self):
        words=[(i%768)|(0x4000 if i%3 else 0) for i in range(1024)]
        def dump(items):return b''.join(x.to_bytes(2,'little') for x in items).hex()
        before=dict(a=3,x=4,y=5,d=0x3400,dbr=0,sp=0x1fe0,ps=0x4d,counter=0)
        after=dict(before,a=2048,x=2046,ps=0x4f,counter=2048)
        order=evidence.ready.REGISTERS;trace=''
        for i,word in enumerate(words):
            address=0xc000+2*i;word&=0x3fff
            trace+=f'{address:04x}{word&255:02x}{address+1:04x}{word>>8:02x}'
        return [dict(kind='BH_COST',clock=90,data=['BhReadyOK','3']),
            dict(kind='RV_ENTRY',clock=100,data=['3',*[str(before[k]) for k in order],dump(words)]),
            dict(kind='RV_SCAN',clock=200,data=['3','100',*[str(after[k]) for k in order],dump([w&0x3fff for w in words])]),
            dict(kind='RU_TRACE',clock=200,data=['3',trace])]

    def parse(self,rows):
        with patch.object(evidence.ready,'events',return_value=rows):return evidence.native_scans(Path('unused'))

    def test_cpu_map_ordered_bytes_and_stack_admission(self):
        rows=self.rows();self.assertEqual(self.parse(rows)['3']['ordered_pending_map_byte_writes'],2048)
        for bad in (rows[:-1],rows+[rows[-1]]):
            with self.assertRaises(ValueError):self.parse(bad)
        for clock in (99,100,101,199,201):
            bad=copy.deepcopy(rows);bad[-1]['clock']=clock
            with self.assertRaisesRegex(ValueError,'WRITE_TRACE_BOUNDARY'):self.parse(bad)
        for index in (0,6,12,12282):
            bad=copy.deepcopy(rows);s=bad[-1]['data'][1];bad[-1]['data'][1]=s[:index]+'f'+s[index+1:]
            with self.assertRaisesRegex(ValueError,'ORDERED_PENDING'):self.parse(bad)
        bad=copy.deepcopy(rows);bad[1]['data'][6]=str(0x346f);bad[2]['data'][7]=str(0x346f)
        with self.assertRaisesRegex(ValueError,'STACK_AND_DP_DISJOINT'):self.parse(bad)

    def test_ready_threshold_is_inclusive_and_inventory_fail_closed(self):
        before={'3':dict(master_clocks=400)}
        self.assertEqual(evidence.compare_ready({'3':dict(master_clocks=300)},before)['3']['saved_clocks'],100)
        for bad in ({'3':dict(master_clocks=301)}, {}, {'2':dict(master_clocks=300)}):
            with self.assertRaises(ValueError):evidence.compare_ready(bad,before)

    def test_whole_rom_and_original_symbols_are_pinned(self):
        folder=Path('out/byor-motu-ready-unroll-static-v1/candidate/native')
        rom=(folder/'bor.sfc').read_bytes();result=native.audit_rom(rom,folder)
        self.assertEqual(result['ready_unroll']['code_bytes'],911)
        self.assertEqual(result['ready_unroll']['branch_sites'],351)
        self.assertEqual(native.capture.sha(Path('out/byor-motu-ready-unroll-static-v1/control/native/bor.sfc')),native.BASE_SHA)
        from m4_input_controller_native import offset
        for pc in (0x39a1f7,0x39a800,0x39ab00,0x39ae8e,0x39a200):
            changed=bytearray(rom);changed[offset(pc)]^=1
            with self.assertRaises(ValueError):native.audit_rom(changed,folder)

    def test_observer_only_relocates_entry_and_exact_store_offsets(self):
        from actor_s5_entity_fixture import symbols
        base=Path('out/byor-motu-ref-rebuild-v2/success/native/callback_owner.lua').read_text()
        sy=symbols(Path('out/byor-motu-ready-unroll-static-v1/candidate/native/publisher.sym'))
        result=native.observer_text(base,sy)
        table=result.split('local ruOffsets={',1)[1].split('}',1)[0]
        offsets={int(pc):int(at) for pc,at in re.findall(r'\[(\d+)\]=(\d+)',table)}
        self.assertEqual(offsets,{0x39ab1c+17*i:2*i for i in range(32)})
        self.assertEqual(result.count('RV_MAP_WRITE_OWNER:snes'),base.count('RV_MAP_WRITE_OWNER:snes'))
        self.assertEqual(result.count('RV_MAP_WRITE_OWNER:sa1'),base.count('RV_MAP_WRITE_OWNER:sa1'))
        for kind in ('QUEUE_OWNER:', 'Q7_EXTRA_IRAM_WRITE_OWNER:', 'Q8_SLOT_WRITE_OWNER:', 'CC_STACK_CANARY'):
            self.assertEqual([x for x in result.splitlines() if kind in x],[x for x in base.splitlines() if kind in x])
        for bad in ('',base+base,result):
            with self.assertRaises(ValueError):native.observer_text(bad,sy)

    def test_legacy_size_lexer_compatibility_is_scoped_and_size_only(self):
        import m4_rect_map_audit as lexer
        original=lexer.statements
        lines=['.bank 57','.org $AB00','.a16','.i16','Example:','cld']
        symbols={'Example':0x39ab00}
        with self.assertRaisesRegex(ValueError,'UNKNOWN_INSTRUCTION_SIZE'):original(lines,symbols)
        with native.size_lexer_compatibility():
            row=lexer.statements(lines,symbols)[5]
            self.assertEqual(row[:2],(0x39ab00,1))
        self.assertIs(lexer.statements,original)
        self.assertEqual(lines[-1],'cld')
        code,_=native.independent_code();self.assertEqual(code[7],0xd8)

    def test_existing_pass_receipt_is_rejected_before_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'ready-unroll-receipt.json';path.write_bytes(b'KEEP')
            with patch.object(native.capture,'verify_capture',side_effect=AssertionError('TOO_LATE')):
                with self.assertRaisesRegex(ValueError,'EXISTING_PASS_RECEIPT_MUST_BE_RETAINED'):
                    native.collect_suite(root,None)
            self.assertEqual(path.read_bytes(),b'KEEP')


if __name__=='__main__':unittest.main()
