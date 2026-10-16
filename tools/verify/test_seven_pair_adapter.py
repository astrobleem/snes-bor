"""Native-adapter and receipt probes without Poppy/Mesen; native not certified."""
import sys
import types
import tempfile
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch
import m4_seven_pair_native as native


class AdapterTests(TestCase):
    def test_observer_uses_original_when_shared_entrypoint_is_patched(self):
        import m4_bitmap_shared_native as shared
        names=('Q7PolicyDone','Q7SpillSource','NbVisible','BhRollbackFinished',
               'BhRollbackEmpty','NbQueueSpace','NbFlushQueue','Q7PolicyBegin')
        contract={'native_symbols':{name:0x39a000+32*i for i,name in enumerate(names)}}
        with tempfile.TemporaryDirectory() as tmp:
            script=Path(tmp)/'callback_owner.lua';script.write_text('')
            with patch.object(native,'ORIGINAL_SHARED_OBSERVER') as saved, \
                 patch.object(shared,'observer',native.observer):
                native.observer(script,contract)
                saved.assert_called_once_with(script,contract)
            self.assertIn('Q7_EXTRA_IRAM_WRITE_OWNER',script.read_text())

    def _events(self,*events):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        p=Path(tmp.name);(p/'native').mkdir()
        (p/'native/mesen.log').write_text('\n'.join(events)+'\n')
        return p

    def test_native_metadata_seventh_source_pair(self):
        p=self._events(
           'NB_Q7_POLICY|100|30|225|3|10|0|7',
           'NB_Q7_SOURCE7|101|30|225|3|1',
           'NB_Q7_SOURCE7|102|30|225|3|2',
           'NB_PACKET|103|30|225|3|24|1000|13488|64|payload',
           'NB_PACKET|104|30|225|3|24|24826|13552|16|payload')
        # source 0x34b0=13488 and 0x34f0=13552; low word 0x6000+1000//4=24826
        r=native.packet_evidence(p)
        self.assertEqual(r['seventh_dma_transactions'],[3])
        self.assertEqual(r['seventh_dma_high_pairs'],1)

    def test_reject_wrong_seventh_low_packet(self):
        p=self._events(
           'NB_Q7_POLICY|100|30|225|3|10|0|7',
           'NB_PACKET|103|30|225|3|24|1000|13488|64|payload',
           'NB_PACKET|104|30|225|3|24|24826|13554|16|payload')
        with self.assertRaisesRegex(ValueError,'Q7_SEVENTH_HIGH_LOW_DESCRIPTOR'):
            native.packet_evidence(p)

    def test_reject_seventh_in_six_mode(self):
        p=self._events(
           'NB_Q7_POLICY|100|30|225|3|10|2|6',
           'NB_PACKET|103|30|225|3|24|1000|13488|64|payload',
           'NB_PACKET|104|30|225|3|24|24826|13552|16|payload')
        with self.assertRaisesRegex(ValueError,'Q7_DMA_WITHOUT_SEVEN_CAPACITY'):
            native.packet_evidence(p)

    def test_native_faults_never_filtered(self):
        p=self._events('NB_FAULT|101|30|225|Q7_EXTRA_IRAM_WRITE_OWNER|1910')
        with self.assertRaisesRegex(ValueError,'Q7_NATIVE_SAFETY'):
            native.packet_evidence(p)

    def test_inherited_certifier_exact_two_edits(self):
        # The adapter rewrites precisely the two old hard limits. Any change
        # to the original certifier source must cause a hard stop.
        def certify(folder):
            high={'source':0x34B0};count=7
            if high['source'] not in range(0x3500,0x36e0,80):
                raise ValueError('SOURCE_BAD')
            if not 1<=count<=6:
                raise ValueError('COUNT_BAD')
            return 'accepted'
        module=types.SimpleNamespace(certify=certify)
        with patch.dict(sys.modules,{'m4_home_borrow_evidence':module}):
            self.assertEqual(native.candidate_home_certifier('ignored'),'accepted')

    def test_inherited_certifier_drift_rejected(self):
        def certify(folder):
            return 'changed'
        module=types.SimpleNamespace(certify=certify)
        with patch.dict(sys.modules,{'m4_home_borrow_evidence':module}):
            with self.assertRaisesRegex(ValueError,'Q7_INHERITED_HOME_CERTIFIER_DRIFT'):
                native.candidate_home_certifier('ignored')

    def test_right_certifier_seventh_sources_and_ready_fences(self):
        def certify(folder,contract,fields):
            sources=[0x3500+80*i for i in range(6)]+[0x34b0]
            for i,source in enumerate(sources):
                h={'source':source};l={'source':source+64}
                if h['source'] not in range(0x3500,0x36e0,80):
                    raise ValueError('SOURCE_BAD')
                if (h['source'],l['source'])!=(0x3500+80*i,0x3540+80*i):
                    raise ValueError('SEQUENCE_BAD')
            ready=100
            if any(0x3500<=e['source']<0x36e0 and e['end']>=ready for e in folder):
                raise ValueError('READY_FENCE_BAD')
            return 'accepted'
        with patch.object(native,'ORIGINAL_RIGHT_CERTIFIER',certify):
            self.assertEqual(native.candidate_right_certifier([],{},[]),'accepted')
            for source in (0x34b0,0x34f0,0x3500):
                with self.assertRaisesRegex(ValueError,'READY_FENCE_BAD'):
                    native.candidate_right_certifier([{'source':source,'end':100}],{},[])

    def test_right_certifier_drift_is_rejected(self):
        def certify(folder,contract,fields):return 'changed'
        with patch.object(native,'ORIGINAL_RIGHT_CERTIFIER',certify):
            with self.assertRaisesRegex(ValueError,'INHERITED_RIGHT_CERTIFIER_DRIFT'):
                native.candidate_right_certifier([],{},[])

    def test_partial_queue_policy_is_scoped_to_the_failed_request(self):
        evidence=dict(policy=[[1,8,1,7],[2,6,0,7],[3,10,2,6]],
            seventh_dma_transactions=[1,2],seventh_source_calls=[[1,1],[2,1]])
        native.require_partial_six(evidence)
        for bad in (
            dict(evidence,seventh_dma_transactions=[1,2,3]),
            dict(evidence,seventh_source_calls=[[3,1]]),
            dict(evidence,policy=[[3,10,2,7]])):
            with self.assertRaises(ValueError):native.require_partial_six(bad)

    def test_right_recertification_keeps_original_oracle_and_faults(self):
        import json
        import m4_source_safepoint_native as safe
        import m4_nonblank_batch_native as right
        import m4_home_borrow_bitmap_native as bm
        import m4_restore_single_pass_native as single
        import m4_bitmap_shared_native as shared
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/'contract.json').write_text('{}')
            (folder/'fields.json').write_text('[]')
            def original_oracle(path,contract,fields):
                self.assertEqual((path,contract,fields),(folder,{},[]))
                self.assertIs(right.certify,native.candidate_right_certifier)
                self.assertIs(safe.audit_rom,native.audit_rom)
                return {'classification':'BYOR_MOTU_SOURCE_SAFEPOINT_PASS'}
            with patch.object(safe,'certify',side_effect=original_oracle) as oracle, \
                 patch.object(bm,'bitmap_evidence',return_value={'plans':[]}), \
                 patch.object(single,'evidence',return_value={}), \
                 patch.object(shared,'shared_evidence',return_value=[]), \
                 patch.object(native,'packet_evidence',return_value={}), \
                 patch.object(native,'presentation_windows',return_value={}):
                self.assertEqual(native.certify_right(folder)['classification'],'SEVEN_PAIR_RIGHT_CONTROL')
                oracle.assert_called_once()
                oracle.side_effect=ValueError('original pixel or DMA fault')
                with self.assertRaisesRegex(ValueError,'original pixel or DMA fault'):
                    native.certify_right(folder)

    def test_complete_windows_and_original_six_source_order_are_enforced(self):
        def event(kind,clock,*data):
            return 'NB_'+kind+'|'+str(clock)+'|0|225|'+'|'.join(map(str,data))
        lines=[event('Q7_POLICY',10,3,10,0,7),event('VBLANK_START',100),
               event('BATCH',200,'NbQueueHasPending',3,7)]
        for i in range(7):
            source=0x34b0 if i==6 else 0x3500+80*i
            clock=300+100*i
            for delta,src,size,word in ((0,source,64,32*i),(10,source+64,16,0x6000+8*i)):
                lines.extend((event('PACKET',clock+delta,3,24,word,src,size,'payload'),
                              event('DONE',clock+delta+4,3,src,size)))
        lines.extend((event('BATCH',1000,'NbQueueDrainDone',3,7),event('VBLANK_END',20000),
            event('VBLANK_START',20500),event('PHASE',21000,'NbMapCommit',3),
            event('PHASE',30000,'NbMapsComplete',3),event('VBLANK_END',50000)))
        folder=self._events(*lines)
        result=native.presentation_windows(folder)
        self.assertEqual(result['batches'][0]['margin_clocks'],19000)
        self.assertEqual(result['maps'][0]['margin_clocks'],20000)
        self.assertEqual(result['seventh_dma'][0]['high_source'],0x34b0)
        text='\n'.join(lines)+'\n'
        for bad in (text.replace('NB_BATCH|1000|','NB_BATCH|15000|'),
                    text.replace('NB_PHASE|30000|','NB_PHASE|45000|'),
                    text.replace('|0|13568|64|payload','|0|13648|64|payload')):
            (folder/'native/mesen.log').write_text(bad)
            with self.assertRaises(ValueError):native.presentation_windows(folder)


    def test_helper_operand_only_relocation(self):
        from unittest.mock import patch
        fake_audit=types.SimpleNamespace(statements=lambda lines,sy: {
            0:(0x39B000,3,'jsr Foo'),1:(0x39B300,3,'jsr Foo')})
        fake_offset=types.SimpleNamespace(offset=lambda x:x-0x390000)
        oldsy={'SpCodeEnd':0x39B003,'BhCodeEnd':0x39B303,'NbCodeEnd':0x39A500,'Foo':0x39A100}
        sy=dict(oldsy,Foo=0x39A180)
        original=bytearray(0xC000);compiled=bytearray(0xC000)
        for at in (0xB000,0xB300):
            original[at:at+3]=bytes.fromhex('2000a1')
            compiled[at:at+3]=bytes.fromhex('2080a1')
        with patch.dict(sys.modules,{'m4_rect_map_audit':fake_audit,
                                     'm4_input_controller_native':fake_offset}):
            target,fixups=native.helper_relocations(original,compiled,[],[],oldsy,sy)
        self.assertEqual(len(fixups),2)
        self.assertEqual(target[0xB000:0xB003],bytes.fromhex('2080a1'))
        self.assertEqual(target[0xB300:0xB303],bytes.fromhex('2080a1'))
        self.assertEqual(target[0xA000:0xA003],bytes(3))

    def test_helper_refuses_nonoperand_change(self):
        fake_audit=types.SimpleNamespace(statements=lambda lines,sy: {0:(0x39B000,3,'jsr Foo')})
        fake_offset=types.SimpleNamespace(offset=lambda x:x-0x390000)
        oldsy={'SpCodeEnd':0x39B003,'BhCodeEnd':0x39B300,'NbCodeEnd':0x39A500,'Foo':0x39A100}
        sy=dict(oldsy,Foo=0x39A180)
        original=bytearray(0xC000);compiled=bytearray(0xC000)
        original[0xB000:0xB003]=bytes.fromhex('2000a1')
        compiled[0xB000:0xB003]=bytes.fromhex('2180a1')
        with patch.dict(sys.modules,{'m4_rect_map_audit':fake_audit,
                                     'm4_input_controller_native':fake_offset}):
            with self.assertRaisesRegex(ValueError,'Q7_HELPER_UNEXPECTED_OPCODE'):
                native.helper_relocations(original,compiled,[],[],oldsy,sy)


if __name__=='__main__':main()
