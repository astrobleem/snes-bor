"""Independent faults at the native copy boundary and exact ROM patch."""
import copy
from pathlib import Path
import unittest

import m4_preload_pair_native as native
import preload_pair_evidence as evidence


class BoundaryTests(unittest.TestCase):
    def fixture(self,index=3):
        regs=dict(a=index,x=77,y=31,d=0x3400,dbr=0x39,sp=0x1fee,ps=0x47,counter=index)
        source=bytes(range(80));stage=bytes([0x5a]*560)
        dest=0x34b0 if index==6 else 0x3500+80*index
        before=(regs,index,0x1234,0x5678,source,stage)
        after_stage=bytearray(stage);after_stage[dest-0x34b0:dest-0x34b0+80]=source
        out=dict(regs,a=0xffff,x=0xd6d0,y=dest+80,ps=4)
        after=(out,index,dest,0x5678 if index==6 else 16*index,source,bytes(after_stage))
        writes=[] if index==6 else [(0x474,16*index),(0x475,0)]
        writes.extend(((0x472,dest&255),(0x473,dest>>8)))
        writes.extend((dest-0x3000+i,value) for i,value in enumerate(source))
        trace=''.join(f'{at+0x3000:04x}{value:02x}' for at,value in writes)
        return before,after,trace

    def test_native_binary_contexts(self):
        for index in range(7): evidence.validate(*self.fixture(index))

    def test_cpu_write_order_sentinels_and_source_faults(self):
        before,after,trace=self.fixture()
        for field in ('a','x','y','d','dbr','sp','ps','counter'):
            changed=copy.deepcopy(after);changed[0][field]^=1
            with self.assertRaisesRegex(ValueError,'CONTINUATION_CPU'):
                evidence.validate(before,changed,trace)
        for slot in (1,2,3,4,5):
            changed=list(after)
            if isinstance(changed[slot],int):changed[slot]^=1
            else:changed[slot]=bytes([changed[slot][0]^1])+changed[slot][1:]
            with self.assertRaises(ValueError):evidence.validate(before,changed,trace)
        for bad in ('',trace[6:]+trace[:6],trace[:-2]+'ff'):
            with self.assertRaisesRegex(ValueError,'WRITE_ORDER'):
                evidence.validate(before,after,bad)
        for bad in ('0474'+trace[4:],trace+'0', '0000'+trace[4:]):
            with self.assertRaises(ValueError):evidence.validate(before,after,bad)

    def test_native_entry_width_decimal_alias_fail_closed(self):
        for field,value in (('d',0),('ps',0x27),('ps',0x4f),('sp',0x3475)):
            before,after,trace=self.fixture();before[0][field]=value
            with self.assertRaises(ValueError):evidence.validate(before,after,trace)

    def test_pairing_pins_inputs_and_function_regression(self):
        before,after,trace=self.fixture();proof=evidence.validate(before,after,trace)
        row=dict(sequence=1,transaction='3',master_clocks=100,**proof)
        self.assertEqual(evidence.compare_calls([dict(row,master_clocks=80)],[row])['3']['improvement_percent'],20)
        for bad in (dict(row,input_sha256='wrong'),dict(row,master_clocks=101)):
            with self.assertRaises(ValueError):evidence.compare_calls([bad],[row])
        # Unread bytes in a target that is completely overwritten need not
        # match between cold launches. Per-call whole-stage proofs still hold.
        changed=list(before);changed[5]=bytes([0x19]*560)
        changed_out=list(after);stage=bytearray(changed[5]);stage[320:400]=before[4]
        changed_out[5]=bytes(stage)
        proof2=evidence.validate(tuple(changed),tuple(changed_out),trace)
        self.assertEqual(proof['input_sha256'],proof2['input_sha256'])
        self.assertNotEqual(proof['preserved_stage_before_sha256'],proof2['preserved_stage_before_sha256'])

    def test_ownership_extension_is_exact_and_retains_original_checks(self):
        import re
        from actor_s5_entity_fixture import symbols
        folder=Path('out/byor-motu-preload-pair-static-v1/native')
        sy=symbols(folder/'publisher.sym')
        text=Path('out/byor-motu-preload-pair-pilot-v1/control/success/native/callback_owner.lua').read_text()
        after=native.ownership_observer(text,sy)
        for flag in ('CC_STACK_WRITE:sa1','CC_STACK_CANARY','SPILL_OWNER:snes','Q7_EXTRA_IRAM_WRITE_OWNER:',
                     'nbWord(0x42d606)>12','nbWord(0x42d676)~=8','nbWord(0x42d660)~=6',"'sa1'~='snes'"):
            self.assertEqual(after.count(flag),text.count(flag),flag)
        original_slot=[line for line in text.splitlines() if 'Q8_SLOT_WRITE_OWNER:' in line]
        self.assertEqual([line for line in after.splitlines() if 'Q8_SLOT_WRITE_OWNER:' in line],original_slot)
        table=after.split('local ppStoreOffsets={',1)[1].split('}',1)[0]
        parsed={int(pc):int(offset) for pc,offset in re.findall(r'\[(\d+)\]=(\d+)',table)}
        self.assertEqual(parsed,{sy['PpCopyStart']+7*(i+1):2*i for i in range(40)})
        for bad in ('',text+text,after):
            with self.assertRaises(ValueError):native.ownership_observer(bad,sy)

    def test_real_native_record_shape_and_required_store_bracket(self):
        from unittest.mock import patch
        before,after,trace=self.fixture()
        def data(parts):
            regs,index,base,scratch,source,stage=parts
            return [*[str(regs[k]) for k in evidence.REGISTERS],str(index),str(base),str(scratch),source.hex(),stage.hex()]
        rows=[dict(kind='PP_ENTRY',clock=100,data=['1','3',*data(before)]),
            dict(kind='PP_STORE_BEGIN',clock=200,data=['1','3',str(0x35f0),'3']),
            dict(kind='PP_EXIT',clock=300,data=['1','3','200',*data(after),trace])]
        with patch.object(evidence.ready,'events',return_value=rows):
            self.assertEqual(len(evidence.native_calls(Path('unused'),enabled=True)),1)
            with self.assertRaises(ValueError):evidence.native_calls(Path('unused'),enabled=False)
        for bad in (rows[::2],rows[:2]+[rows[1]]+rows[2:],rows[1:]):
            with patch.object(evidence.ready,'events',return_value=bad),self.assertRaises(ValueError):
                evidence.native_calls(Path('unused'),enabled=True)
        for clock in (99,100,300,301):
            bad=copy.deepcopy(rows);bad[1]['clock']=clock
            with patch.object(evidence.ready,'events',return_value=bad),self.assertRaises(ValueError):
                evidence.native_calls(Path('unused'),enabled=True)

    def test_independent_literal_and_static_candidate(self):
        code,labels=native.independent_code()
        self.assertEqual(len(code),373)
        self.assertEqual(labels['PpCodeEnd'],0x39ac75)
        self.assertEqual(code.count(bytes.fromhex('9f')),40)
        folder=Path('out/byor-motu-preload-pair-static-v1/native')
        report=native.audit_rom((folder/'bor.sfc').read_bytes(),folder)
        self.assertEqual(report['preload_pair']['branch_sites'],323)
        for at in (native.PATCH_PC,native.CONTINUE_PC,0x39ab00,0x39ac74,0x39a200):
            from m4_input_controller_native import offset
            rom=bytearray((folder/'bor.sfc').read_bytes());rom[offset(at)]^=1
            with self.assertRaises(ValueError):native.audit_rom(rom,folder)


if __name__=='__main__':unittest.main()
