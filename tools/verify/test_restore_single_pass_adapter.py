"""Offline trace/contract tests. Does not pretend to execute Poppy or Mesen."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import restore_single_pass as rp
import m4_restore_single_pass_native as adapter
from test_restore_single_pass import PlanMachine,synthetic_ten_home_case,OLD,NEW
from restore_single_pass_vm import assemble


def dump(words):
    return b''.join(int(w).to_bytes(2,'little') for w in words).hex()


def trace(pending,refs,exact=True,cursor=596):
    m=PlanMachine(True,pending,refs,cursor,exact)
    m.run('TestStart')
    outcome='complete' if m.outcome=='success' else m.outcome
    begin=dict(clock=100,data=['3',str(int(exact)),str(cursor),dump(pending),dump(refs)])
    finish=dict(clock=100+m.steps,data=['3',outcome,str(m.reads['pending_map']),
            str(m.hits['RpReadIramHome']+m.hits['RpReadSpillHome']),str(m.peek16(0x3418)),
            str(m.peek16(0x342e)),str(m.peek16(0x42d606)),dump(m.pending()),
            m.blob(0x3480,128).hex(),m.blob(0x42d620,64).hex()])
    return begin,finish


class AdapterTests(unittest.TestCase):
    def test_actual_retained_bootstrap_marker(self):
        prefix='-- bootstrap only\n'
        self.assertEqual(adapter.bootstrap_prefix(prefix+'-- NONBLANK_OBSERVER_BEGIN\nold observers'),prefix)
        for value in ('-- ONLINE_OBSERVER_BEGIN', '-- NONBLANK_OBSERVER_BEGIN\n-- NONBLANK_OBSERVER_BEGIN'):
            with self.assertRaises(ValueError):adapter.bootstrap_prefix(value)

    def test_independent_trace_checks_completed_map_and_order(self):
        begin,end=trace(*synthetic_ten_home_case())
        r=adapter.verify_plan(begin,end)
        self.assertEqual(r['map_words'],1024)
        self.assertEqual(len(r['records']),10)
        self.assertTrue(r['successful_map_matches_eager_oracle'])

    def test_corrupted_map_or_record_trace_is_rejected(self):
        begin,end=trace(*synthetic_ten_home_case())
        for index in (7,8):
            bad=deepcopy(end);raw=bytearray.fromhex(bad['data'][index]);raw[0]^=1;bad['data'][index]=raw.hex()
            with self.assertRaises(ValueError):adapter.verify_plan(begin,bad)

    def test_trace_evidence_is_stable_after_json_roundtrip(self):
        begin,end=trace(*synthetic_ten_home_case())
        actual=adapter.verify_plan(begin,end)
        stored=json.loads(json.dumps(actual))
        self.assertEqual(stored,actual)
        stored['records'][0][1]^=1
        self.assertNotEqual(stored,actual)

    def test_retry_and_abort_use_private_prefix_not_eager_partial_map(self):
        refs=[1]*768;refs[0]=refs[1]=0x8001;refs[596]=0
        pending=[0,1,0]+[100]*1021
        for exact in (False,True):
            begin,end=trace(pending,refs,exact)
            r=adapter.verify_plan(begin,end)
            self.assertEqual(r['outcome'],'abort' if exact else 'retry')
            self.assertEqual(r['map_words'],2)
            self.assertFalse(r['successful_map_matches_eager_oracle'])

    def test_trace_repeated_or_missing_map_cell_rejects(self):
        begin,end=trace(*synthetic_ten_home_case())
        end['data'][2]='1025'
        with self.assertRaisesRegex(ValueError,'ORDERED'):adapter.verify_plan(begin,end)

    def test_evidence_never_discards_native_or_lua_faults(self):
        begin,end=trace(*synthetic_ten_home_case())
        good='\n'.join('NB_'+kind+'|'+str(event['clock'])+'|1|0|'+'|'.join(event['data'])
                       for kind,event in (('RP_BEGIN',begin),('RP_END',end)))+'\n'
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);(folder/'native').mkdir();log=folder/'native/mesen.log'
            log.write_text(good)
            self.assertEqual(len(adapter.evidence(folder)['plans']),1)
            for fault in ('NB_FAULT|42|1|0|INJECTED\n', 'callback_owner.lua:123: exception\n'):
                log.write_text(good+fault)
                with self.assertRaises(ValueError):adapter.evidence(folder)
            log.write_text(good.splitlines()[0]+'\n')
            with self.assertRaisesRegex(ValueError,'INCOMPLETE'):adapter.evidence(folder)

    def test_observer_keeps_both_cpu_frozen_memory_and_no_queue_guards(self):
        names=('NbRestorePlan','RpCellLoaded','RpReadIramHome','RpReadSpillHome',
               'NbActorPlanStart','NbBeginRetry','NbAbort','NbPreloadPair','BhPrepare','SpReadyBoundary')
        sy={n:0x39a000+32*i for i,n in enumerate(names)}
        text=adapter.observer_extension(sy)
        self.assertNotIn('endend',text)
        self.assertNotRegex(text,r'\dend\b')
        for message in ('RP_NONCURRENT_MAP_WRITE','RP_FROZEN_MAP_OR_DIRECTORY_WRITE',
                        'RP_QUEUE_TOUCHED','RP_LATCH_TOUCHED','RP_JOURNAL_TOUCHED'):
            self.assertEqual(text.count(message),2)
        self.assertIn('emu.cpuType.sa1',text)
        self.assertIn("rpFinish('retry')",text)
        self.assertIn("rpFinish('abort')",text)

    def test_exact_rom_growth_is_53_bytes(self):
        old=assemble(rp.original_plan(),0x39a100,{'NbActorPlanStart':0x39a18d,'NbAbort':0x39a400,'NbFree':0x39a500})
        main=assemble(rp.main_loop(),0x39a100,{'NbActorPlanStart':0x39a136,'RpResolveRestore':0x39a700})
        resolve=assemble(rp.resolver(),0x39a700,{'NbReroute':0x39a125,'NbFree':0x39a500,'NbAbort':0x39a400})
        self.assertEqual((len(old.data),len(main.data),len(resolve.data)),(141,54,140))
        self.assertEqual(len(main.data)+len(resolve.data)-len(old.data),53)

if __name__=='__main__':unittest.main()
