"""Native adapter negative checks. These are NOT native Mesen runs."""
from __future__ import annotations
import json,tempfile,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
import m4_eight_pair_native as q
from eight_pair_direct import SCRATCH_HIGH,SCRATCH_LOW


class AdapterTests(unittest.TestCase):
    def test_partial_mode_two_policy_reads_record_mode_capacity_shape(self):
        for row in ([10,2,6],(10,2,6)):
            q.verify_partial_fallback({'policy':{'1':[(8,1,8)],'3':[row]},
                                       'eighth_transactions':[1,2]})
        for policies,eighth in (([],[]),([(10,0,6)],[]),([(10,2,8)],[]),([(10,2,6)],[3])):
            with self.assertRaisesRegex(ValueError,'PARTIAL_MODE_2_USED_DIRECT_PAIR'):
                q.verify_partial_fallback({'policy':{'3':policies},'eighth_transactions':eighth})

    def test_pool_identity_preserves_order_checks_across_json_transaction_keys(self):
        pool=dict(homes=[3,5],original_invalid=[3],original_valid=[5],policy=1,limit=64,need=2)
        q.verify_pool_identity({3:pool},{'3':pool},'success')
        changed={**pool,'homes':[5,3]}
        with self.assertRaisesRegex(ValueError,'BORROWING_ORDER_CHANGED:3'):
            q.verify_pool_identity({3:changed},{'3':pool},'success')
        with self.assertRaisesRegex(ValueError,'MISSING_POOL_TRANSACTION:3'):
            q.verify_pool_identity({},{'3':pool},'success')
        with self.assertRaisesRegex(ValueError,'AMBIGUOUS_POOL_TRANSACTION'):
            q.verify_pool_identity({3:pool,'3':pool},{'3':pool},'success')

    def test_policy_store_callback_includes_final_instruction_completion(self):
        # Native 65816 writes report the PC after the four-byte STA.l.
        # The second permitted write completes exactly at Q7PolicyDone.
        code=bytes.fromhex('a906008f76d642af06d642c90d00b010af02d642c90200f007a908008f76d642')
        begin=0x39a0ee
        allowed=q.policy_write_completions(code,begin)
        self.assertEqual(allowed,[0x39a0f5,0x39a10e])
        self.assertEqual(allowed[-1],begin+len(code))
        self.assertNotIn(begin+len(code)-1,allowed)
        self.assertNotIn(begin+len(code)+1,allowed)
        for broken in (code[:-1],code.replace(bytes.fromhex('8f76d642'),bytes.fromhex('8f70d642'),1)):
            with self.assertRaisesRegex(ValueError,'Q8_POLICY_STORE_DRIFT'):
                q.policy_write_completions(broken,begin)

    def test_capture_runtime_keeps_binary_and_render_settings_identity(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        root=Path(t.name);source=root/'source';source.mkdir()
        for name in ('Mesen.exe','Mesen.dll','MesenCore.dll','Mesen.deps.json','Mesen.runtimeconfig.json'):
            (source/name).write_bytes(('original:'+name).encode())
        settings={'Preferences':{'OverrideScreenshotFolder':False,'ScreenshotFolder':'old','Other':17},
                  'Video':{'Brightness':0,'Scale':2},'Snes':{'BlendHighResolutionModes':False}}
        original=json.dumps(settings).encode();(source/'settings.json').write_bytes(original)
        runtime=root/'private';exe=q.prepare_capture_runtime(runtime,source/'Mesen.exe')
        self.assertEqual(exe,runtime/'Mesen.exe')
        self.assertEqual((source/'settings.json').read_bytes(),original)
        actual=json.loads((runtime/'settings.json').read_text())
        expected=json.loads(original);expected['Preferences'].update(
            OverrideScreenshotFolder=True,ScreenshotFolder=str(runtime/'Screenshots'),
            OverrideSaveDataFolder=True,SaveDataFolder=str(runtime/'Saves'),
            OverrideSaveStateFolder=True,SaveStateFolder=str(runtime/'SaveStates'))
        self.assertEqual(actual,expected)
        manifest=json.loads((runtime/'capture-runtime.json').read_text())
        self.assertFalse(manifest['global_settings_modified'])
        for name,value in manifest['binary_sha256'].items():
            self.assertEqual(q.sha(source/name),value)
            self.assertEqual(q.sha(runtime/name),value)
        self.assertTrue((runtime/'Screenshots').is_dir())

    def test_capture_runtime_preserves_existing_sram_input_and_isolates_writes(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        root=Path(t.name);source=root/'source';source.mkdir();saves=root/'old-saves';saves.mkdir()
        for name in ('Mesen.exe','Mesen.dll','MesenCore.dll','Mesen.deps.json','Mesen.runtimeconfig.json'):
            (source/name).write_bytes(name.encode())
        seed=bytes(range(256));(saves/'bor.srm').write_bytes(seed)
        config={'Preferences':{'OverrideSaveDataFolder':True,'SaveDataFolder':str(saves)}}
        original=json.dumps(config).encode();(source/'settings.json').write_bytes(original)
        runtime=root/'private';q.prepare_capture_runtime(runtime,source/'Mesen.exe')
        manifest=json.loads((runtime/'capture-runtime.json').read_text())
        self.assertEqual((runtime/'Saves/bor.srm').read_bytes(),seed)
        self.assertEqual(manifest['initial_sram']['sha256'],q.sha(saves/'bor.srm'))
        (runtime/'Saves/bor.srm').write_bytes(b'private later state')
        self.assertEqual((saves/'bor.srm').read_bytes(),seed)
        self.assertEqual((source/'settings.json').read_bytes(),original)
        self.assertEqual(json.loads((runtime/'settings.json').read_text())['Preferences']['SaveDataFolder'],
                         str(runtime/'Saves'))

    def test_capture_runtime_rejects_incomplete_matched_build(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        root=Path(t.name);(root/'Mesen.exe').write_bytes(b'exe only')
        with self.assertRaisesRegex(ValueError,'CAPTURE_MATCHED_BUILD_MISSING'):
            q.prepare_capture_runtime(root/'private',root/'Mesen.exe')
        self.assertFalse((root/'private').exists())

    def folder(self,*events):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        p=Path(t.name);(p/'native').mkdir()
        (p/'native/mesen.log').write_text('\n'.join(events)+'\n')
        return p

    @staticmethod
    def log(kind,clock,*args):
        return 'NB_'+kind+'|'+str(clock)+'|30|230|'+'|'.join(map(str,args))

    def stream(self):
        payload=bytes(range(80));slot=708
        c=self.log
        return [c('Q7_POLICY',5,3,10,0,8),
          c('Q8_HELD',10,3,slot,payload.hex()),
          c('Q8_DIRECT',20,3,slot,payload.hex()),
          c('PACKET',24,3,0x18,slot*32,SCRATCH_HIGH,64,payload[:64].hex()),
          c('DONE',26,3,SCRATCH_HIGH,64,0x18),
          c('PACKET',28,3,0x18,0x6000+slot*8,SCRATCH_LOW,16,payload[64:].hex()),
          c('DONE',29,3,SCRATCH_LOW,16,0x18),
          c('Q8_FENCED',30,3,slot)]

    def test_exact_dma_payload(self):
        r=q.packet_evidence(self.folder(*self.stream()))
        self.assertEqual(r['eighth_high_pairs'],1)
        self.assertTrue(r['all_eighth_fences_complete'])
        self.assertEqual(r['eighth_transactions'],[3])

    def test_reject_native_fault(self):
        events=self.stream()+[self.log('FAULT',31,'Q8_SCRATCH_WRITTEN')]
        with self.assertRaisesRegex(ValueError,'Q8_NATIVE_SAFETY'):
            q.packet_evidence(self.folder(*events))

    def test_reject_invalid_policy(self):
        lines=self.stream();lines[0]=lines[0].replace('|10|0|8','|10|2|8')
        with self.assertRaisesRegex(ValueError,'Q8_POLICY_MISMATCH'):
            q.packet_evidence(self.folder(*lines))

    def test_reject_changed_scratch_between_stage_and_dma(self):
        lines=self.stream();lines[1]=lines[1][:-2]+'ee'
        with self.assertRaisesRegex(ValueError,'Q8_SCRATCH_CONTENT_OR_DMA_PAIR_DRIFT'):
            q.packet_evidence(self.folder(*lines))

    def test_reject_corrupt_high_dma_payload(self):
        lines=self.stream();lines[3]=lines[3][:-2]+'ab'
        with self.assertRaisesRegex(ValueError,'Q8_SCRATCH_CONTENT_OR_DMA_PAIR_DRIFT'):
            q.packet_evidence(self.folder(*lines))

    def test_reject_corrupt_low_source(self):
        lines=self.stream();lines[5]=lines[5].replace('|'+str(SCRATCH_LOW)+'|','|13552|')
        with self.assertRaisesRegex(ValueError,'Q8_INCOMPLETE_ZERO_COPY_PAIR'):
            q.packet_evidence(self.folder(*lines))

    def test_reject_missing_low_fence(self):
        lines=self.stream();lines.pop(6)
        with self.assertRaisesRegex(ValueError,'Q8_MISSING_DMA_COMPLETION_FENCE'):
            q.packet_evidence(self.folder(*lines))

    def test_reject_incomplete_pair(self):
        lines=self.stream();lines.pop(7)
        with self.assertRaisesRegex(ValueError,'Q8_INCOMPLETE_ZERO_COPY_PAIR'):
            q.packet_evidence(self.folder(*lines))

    def test_q7_observer_pinned_policy_rewrite(self):
        old=('nbWord(0x42d670)'*0)
        old=('nbWord(0x42d670) records<=12 and mode~=2 and 7 or 6 '
             'nbWord(0x42d670)~=7 nbWord(0x42d670)~=7 '
             'nbWord(0x42d670)~=7')
        got=q._patch_q7_observer(old)
        self.assertEqual(got.count('nbWord(0x42d676)'),4)
        self.assertEqual(got.count('nbWord(0x42d676)~=8'),3)
        self.assertNotIn('nbWord(0x42d670)',got)
        self.assertIn('records<=12 and mode~=2 and 8 or 6',got)
        with self.assertRaisesRegex(ValueError,'Q8_Q7_OBSERVER_ADDRESS_DRIFT'):
            q._patch_q7_observer(old.replace('nbWord(0x42d670)','broken',1))

    def test_original_home_certifier_scope_is_not_relaxed(self):
        def certify(folder):
            high={'source':0x42d680,'size':64};count=8
            if high['source'] not in range(0x3500,0x36e0,80):raise ValueError('UNSUPPORTED_SOURCE')
            if not 1<=count<=6:raise ValueError('BATCH_LIMIT')
            return 'PASS'
        module=types.SimpleNamespace(certify=certify)
        with patch.dict(sys.modules,{'m4_home_borrow_evidence':module}):
            self.assertEqual(q.candidate_home_certifier(None),'PASS')
        def no_oracle(folder):return 'INCORRECT'
        with patch.dict(sys.modules,{'m4_home_borrow_evidence':types.SimpleNamespace(certify=no_oracle)}):
            with self.assertRaisesRegex(ValueError,'Q8_ORIGINAL_HOME_ORACLE_DRIFT'):
                q.candidate_home_certifier(None)

    def test_window_oracle_reuses_original_with_scratch_source(self):
        class OriginalPolicy:
            @staticmethod
            def queue_limit(n,m=0):return 7
            @staticmethod
            def queue_address(i,n,m=0):return 0x34b0 if i==6 else 0x3500+80*i
        policy=OriginalPolicy()
        def original_windows(folder):
            self.assertEqual(folder,'original')
            self.assertEqual(policy.queue_limit(10,0),8)
            self.assertEqual(policy.queue_address(7,10),0x42d680)
            self.assertEqual(policy.queue_address(6,10),0x34b0)
            self.assertEqual(policy.queue_limit(25,0),6)
            return {'batches':[],'maps':[]}
        fake=types.SimpleNamespace(q7=policy,presentation_windows=original_windows,observer=lambda a,b:None)
        with patch.object(q,'prior',return_value=fake):
            saved=q._Q7_WINDOWS,q._Q7_OBSERVER
            q._Q7_WINDOWS=q._Q7_OBSERVER=None
            try:self.assertEqual(q.presentation_windows('original'),{'batches':[],'maps':[]})
            finally:q._Q7_WINDOWS,q._Q7_OBSERVER=saved
        self.assertEqual(policy.queue_limit(10),7)
        self.assertEqual(policy.queue_address(6,10),0x34b0)

    def test_right_certifier_only_edits_three_exact_guards(self):
        def certify(folder,contract,fields):
            for i,src in enumerate([0x3500+80*j for j in range(6)]+[0x34b0,0x42d680]):
                h={'source':src};l={'source':src+64}
                if h['source'] not in range(0x3500,0x36e0,80):
                    raise ValueError('ORIGINAL_SOURCE_RESTRICTION')
                if (h['source'],l['source'])!=(0x3500+80*i,0x3540+80*i):
                    raise ValueError('ORIGINAL_SEQUENCE_RESTRICTION')
            if any(0x3500<=e['source']<0x36e0 and e['end']>=100 for e in folder):
                raise ValueError('READY_FENCE_UNSAFE')
            return 'PASS'
        fake=types.SimpleNamespace(ORIGINAL_RIGHT_CERTIFIER=certify)
        right=types.SimpleNamespace(__dict__={})
        with patch.object(q,'prior',return_value=fake),patch.dict(sys.modules,{'m4_nonblank_batch_native':right}):
            self.assertEqual(q.candidate_right_certifier([],{},[]),'PASS')
            for source in (0x34b0,0x42d680,0x3500):
                with self.assertRaisesRegex(ValueError,'READY_FENCE_UNSAFE'):
                    q.candidate_right_certifier([{'source':source,'end':100}],{},[])

    def test_strict_acceptance_hard_fails(self):
        with self.assertRaisesRegex(ValueError,'Q8_ACCEPTANCE'):
            q.require(False,'deliberate')

if __name__=='__main__':unittest.main()
