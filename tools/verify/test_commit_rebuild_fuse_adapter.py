"""Fail-closed fused clone/recount evidence and native admission checks."""
import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import m4_commit_rebuild_fuse_native as native
import commit_rebuild_fuse_evidence as evidence


class AdapterTests(unittest.TestCase):
    def rows(self):
        words=[i%768 for i in range(1024)];refs=[(i*97)&65535 for i in range(768)]
        result,ref_trace=evidence.reference.expected_rebuild(refs,words)
        def dump(items):return b''.join(w.to_bytes(2,'little') for w in items).hex()
        before=dict(a=2047,x=7,y=9,d=0x3400,dbr=0,sp=0x1fe0,ps=0x4c,counter=2048)
        after=dict(before,a=result[words[-1]],x=words[-1]*2,y=2048,ps=0x4f)
        order=evidence.reference.REGISTERS
        trace=''.join(f'{0xc800+2*i:04x}{w&255:02x}{0xc801+2*i:04x}{w>>8:02x}' for i,w in enumerate(words))
        return [dict(kind='PHASE',clock=90,frame=1,data=['NbMapsComplete','3']),
            dict(kind='RF_ENTRY',clock=100,frame=1,data=['3',*[str(before[k]) for k in order],dump(refs),dump(words)]),
            dict(kind='CF_ENTRY',clock=100,frame=1,data=['3',dump([0xffff]*1024)]),
            dict(kind='RF_SCAN',clock=200,frame=1,data=['3','100',*[str(after[k]) for k in order],dump(result),dump(words),ref_trace]),
            dict(kind='CF_SCAN',clock=200,frame=1,data=['3',dump(words),trace,'2048','3586']),
            dict(kind='PHASE',clock=210,frame=1,data=['NbVisible','3'])]

    def parse(self,rows):
        with patch.object(evidence.reference.ready,'events',return_value=rows):return evidence.native_scans(Path('unused'))

    def test_exact_clone_reference_traces_and_read_inventory(self):
        rows=self.rows();self.assertTrue(self.parse(rows)['3']['committed_map_exact'])
        for ix,value in ((1,'ffff'*1024),(2,''),(3,'2047'),(4,'3584')):
            bad=copy.deepcopy(rows);bad[4]['data'][ix]=value
            with self.assertRaises(ValueError):self.parse(bad)
        for bad in (rows[:4]+rows[5:],rows+[rows[4]]):
            with self.assertRaises(ValueError):self.parse(bad)

    def test_context_and_boundary_inventory(self):
        for row,ix,value in ((1,6,'20000'),(1,8,'0'),(3,2,'7')):
            bad=self.rows();bad[row]['data'][ix]=value
            with self.assertRaises(ValueError):self.parse(bad)
        bad=self.rows();bad[4]['clock']=201
        with self.assertRaisesRegex(ValueError,'CLONE_BOUNDARIES'):self.parse(bad)

    def test_twenty_percent_threshold_is_inclusive(self):
        before={'3':dict(master_clocks=500)}
        self.assertEqual(evidence.compare_postmap({'3':dict(master_clocks=400)},before)['3']['saved_clocks'],100)
        for bad in ({'3':dict(master_clocks=401)}, {}, {'2':dict(master_clocks=400)}):
            with self.assertRaises(ValueError):evidence.compare_postmap(bad,before)

    def test_existing_pass_is_preserved_before_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'commit-rebuild-fuse-receipt.json';path.write_bytes(b'KEEP')
            with patch.object(native.capture,'verify_capture',side_effect=AssertionError('TOO_LATE')):
                with self.assertRaisesRegex(ValueError,'EXISTING_PASS_RECEIPT_MUST_BE_RETAINED'):
                    native.collect_suite(root,None)
            self.assertEqual(path.read_bytes(),b'KEEP')

    def test_independent_access_pcs_and_literal_gap(self):
        code,labels,access=native.independent_code()
        self.assertEqual(code[:11],bytes.fromhex('088bf44242ababd8a20000'))
        self.assertEqual(code[-12:],bytes.fromhex('bba00008ab28c000084ca9a2'))
        self.assertLess(labels['CfCodeEnd'],0x39b000)
        counts={kind:sum(v[0]==kind for v in access.values()) for kind in ('clear_read','clear_write','map_read','map_write','ref_read','ref_write','final_read')}
        self.assertEqual(counts,dict(clear_read=32,clear_write=32,map_read=32,map_write=32,ref_read=32,ref_write=32,final_read=1))
        # Mesen raw cpu.pc points after opcode+two operand fetches at the
        # physical data bus callback; retain that convention for every rule.
        opcodes=dict(clear_read=0xbd,clear_write=0x9d,map_read=0xbd,map_write=0x9d,
            ref_read=0xb9,ref_write=0x99,final_read=0xb9)
        for pc,(kind,_) in access.items():self.assertEqual(code[pc-0x39ab00-3],opcodes[kind])

    def test_whole_rom_and_original_symbols_are_pinned(self):
        folder=Path('out/byor-motu-commit-rebuild-fuse-static-v2/candidate/native')
        rom=(folder/'bor.sfc').read_bytes();result=native.audit_rom(rom,folder)
        self.assertEqual(result['commit_rebuild_fuse']['code_bytes'],825)
        self.assertEqual(result['commit_rebuild_fuse']['branch_sites'],318)
        self.assertEqual(native.capture.sha(Path('out/byor-motu-commit-rebuild-fuse-static-v2/control/native/bor.sfc')),native.BASE_SHA)
        from m4_input_controller_native import offset
        for pc in (0x39a26b,0x39a26e,0x39a26f,0x39a900,0x39ab00,0x39ae38,0x39a200):
            changed=bytearray(rom);changed[offset(pc)]^=1
            with self.assertRaises(ValueError):native.audit_rom(changed,folder)

    def test_scoped_size_lexer_preserves_literal_semantics(self):
        import m4_rect_map_audit as lexer
        original=lexer.statements
        lines=['.bank 57','.org $AB00','.a16','.i16','Example:','cld','tyx']
        symbols={'Example':0x39ab00}
        with self.assertRaisesRegex(ValueError,'UNKNOWN_INSTRUCTION_SIZE'):original(lines,symbols)
        with native.size_lexer_compatibility():
            rows=lexer.statements(lines,symbols)
            self.assertEqual(rows[5][:2],(0x39ab00,1))
            self.assertEqual(rows[6][:2],(0x39ab01,1))
        self.assertIs(lexer.statements,original)
        code,_,_=native.independent_code()
        self.assertEqual(code[7],0xd8)
        self.assertEqual(code[-12],0xbb)

    def test_host_budget_resumes_only_unfinished_exact_frames(self):
        class Session:
            def __init__(self):self.calls=[];self.index=0
            def run_frames(self,count):
                self.calls.append(count);self.index+=1
                start=10 if self.index<=11 else 11
                advanced=0 if self.index<=10 else 1
                return dict(startFrame=start,endFrame=start+advanced,framesAdvanced=advanced,
                    timedOut=advanced<count,isPaused=True)
            def get_cpu_state(self):return dict(pc=0xab0b,cycleCount=self.index*100)
        m=Session();rows=[]
        native.run_frames_observed(m,2,rows.append,clock=lambda:0)
        self.assertEqual(m.calls,[2]*11+[1])
        self.assertEqual(len([r for r in rows if r['kind']=='frame_response']),12)
        self.assertEqual(len([r for r in rows if r['kind']=='cpu_diagnostic']),11)

    def test_frame_drift_overshoot_unpaused_and_host_deadline_reject(self):
        from types import SimpleNamespace
        valid=dict(startFrame=10,endFrame=11,framesAdvanced=1,timedOut=False,isPaused=True)
        for mutation in (dict(endFrame=12),dict(framesAdvanced=2,endFrame=12),dict(isPaused=False),dict(framesAdvanced=True)):
            row=dict(valid,**mutation);m=SimpleNamespace(run_frames=lambda _:row)
            with self.assertRaises(ValueError):native.run_frames_observed(m,1,lambda _:None,clock=lambda:0)
        row=dict(valid,endFrame=10,framesAdvanced=0,timedOut=True)
        m=SimpleNamespace(run_frames=lambda _:row,get_cpu_state=lambda:dict(cycleCount=1))
        ticks=iter((0,31))
        with self.assertRaisesRegex(ValueError,'OBSERVER_HOST_FRAME_DEADLINE'):
            native.run_frames_observed(m,1,lambda _:None,clock=lambda:next(ticks))
        m.run_frames=lambda _:valid
        ticks=iter((0,0,31,31))
        with self.assertRaisesRegex(ValueError,'OBSERVER_HOST_FRAME_DEADLINE'):
            native.run_frames_observed(m,1,lambda _:None,clock=lambda:next(ticks))

    def test_frame_response_is_flushed_before_diagnostic_error_and_socket_restored(self):
        from types import SimpleNamespace
        class Socket:
            timeout=60
            def gettimeout(self):return self.timeout
            def settimeout(self,value):self.timeout=value
        sock=Socket();rows=[]
        def bad():
            self.assertEqual(rows[0]['kind'],'frame_response')
            self.assertEqual(sock.timeout,30)
            raise RuntimeError('DIAGNOSTIC_FAILED')
        m=SimpleNamespace(_sock=sock,run_frames=lambda _:dict(startFrame=10,endFrame=10,
            framesAdvanced=0,timedOut=True,isPaused=True),get_cpu_state=bad)
        with self.assertRaisesRegex(RuntimeError,'DIAGNOSTIC_FAILED'):
            native.run_frames_observed(m,1,rows.append,clock=lambda:0)
        self.assertEqual(sock.timeout,60)
        self.assertEqual(len(rows),1)
        responses=iter((dict(startFrame=10,endFrame=10,framesAdvanced=0,timedOut=True,isPaused=False),
            dict(startFrame=10,endFrame=11,framesAdvanced=1,timedOut=False,isPaused=True)))
        m.run_frames=lambda _:next(responses)
        m.get_cpu_state=lambda:self.fail('UNPAUSED_DIAGNOSTIC')
        rows=[];native.run_frames_observed(m,1,rows.append,clock=lambda:0)
        self.assertEqual([r['kind'] for r in rows],['frame_response','frame_response'])
        self.assertEqual(sock.timeout,60)


if __name__=='__main__':unittest.main()
