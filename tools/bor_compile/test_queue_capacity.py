"""Only queue capacity/layout, packing and source-shape regressions."""
import json
import re
import tempfile
import unittest
from pathlib import Path
from compiler import ROOT, Source, lower, stage, StageIR, QueueIR, compile_project
from queue_abi import SPEC, RECORD_SIZE, TARGET_CAPACITY, check_count, QueueCapacityError, plan_build, write_contract, assert_layout
from queue_capacity import report
from regenerate_queues import generate
from certify import BASE, MSU_SHA


class QueueTests(unittest.TestCase):
    def test_abi_width_and_arena(self):
        self.assertEqual(RECORD_SIZE,10)
        self.assertEqual((SPEC['arena_base'],SPEC['arena_end_exclusive']),(0x7F9200,0x7FA000))
        self.assertEqual(TARGET_CAPACITY,255)
        self.assertLessEqual(TARGET_CAPACITY*RECORD_SIZE+SPEC['guard_bytes']+1,0xE00)
        self.assertLess(TARGET_CAPACITY*RECORD_SIZE,1<<SPEC['copy_count_bits'])

    def test_no_clamp_and_context_diagnostic(self):
        for name in ('BOR','TMNT','MOTU','Future'):
            c=dict(project=name,set_name='Set',stage=1,source_path='DATA/STAGE.TXT')
            self.assertEqual(check_count(255,**c),2550)
            for count,capacity in ((256,255),(94,92)):
                with self.assertRaises(QueueCapacityError) as raised: check_count(count,capacity=capacity,**c)
                d=raised.exception.diagnostic
                self.assertEqual(d['code'],'QUEUE_CAPACITY_EXCEEDED');self.assertEqual(d['packed_records'],count)
                self.assertEqual(d['required_bytes'],count*10);self.assertEqual(d['project'],name)
        ir=StageIR('data/huge.txt',[],queue=[QueueIR('wait',at=0) for _ in range(256)])
        with self.assertRaises(QueueCapacityError): lower(ir,{}, {})

    def test_source_shapes_and_build_scopes(self):
        r=report()
        self.assertEqual(r['production']['capacity'],92)
        self.assertEqual(r['complete_normal']['capacity'],107)
        bor=r['projects'][0]
        normal5b=next(x for x in bor['rows'] if x['source_path'].lower().endswith('normal\\5b.txt'))
        extra=next(x for x in bor['rows'] if x['source_path'].lower().endswith('extra.txt'))
        self.assertEqual(normal5b['packed_records'],94)
        self.assertEqual((extra['authored_records'],extra['packed_records'],extra['required_bytes']),(184,184,1840))
        self.assertEqual(plan_build([normal5b])['capacity'],94)
        self.assertEqual(plan_build(bor['rows'])['capacity'],184)
        for second in r['projects'][1:]:
            self.assertFalse(second['complete_packed_inventory'])
            self.assertTrue(any(x['packed_records'] is None for x in second['rows']))

    def test_generated_layout_roundtrip(self):
        r=report();plan=r['production']
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'queue_abi'
            write_contract(plan,path)
            self.assertEqual(json.loads(path.with_suffix('.json').read_text()),plan)
            text=path.with_suffix('.pasm').read_text()
            self.assertIn('QUEUE_CAPACITY = 92',text)
            self.assertIn('QUEUE_BUFFER_BYTES = 920',text)

    def test_actual_generated_allocation(self):
        path=ROOT/'src/generated/queue_abi.json'
        plan=json.loads(path.read_text())
        r=assert_layout(ROOT,plan)
        self.assertEqual(r['status'],'PASS')
        self.assertEqual(plan['capacity'],max(x['packed_records'] for x in plan['stages']))
        self.assertEqual(plan['buffer_end_exclusive'],0x7F9200+plan['capacity']*10)
        symbols={name:int(value,16) for value,name in re.findall(r'(?m)^00:([0-9A-F]+) (\w+)$',
            (ROOT/'src/main.sym').read_text())}
        self.assertEqual(symbols['SpawnTable_Wram'],plan['buffer_base'])
        self.assertEqual(symbols['QUEUE_CAPACITY'],plan['capacity'])
        self.assertEqual(symbols['QUEUE_BUFFER_BYTES'],plan['buffer_bytes'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'queue_abi';write_contract(plan,path)
            for ext in ('.json','.pasm'):
                self.assertEqual(path.with_suffix(ext).read_bytes(),(ROOT/('src/generated/queue_abi'+ext)).read_bytes())
        for name,value in symbols.items():
            if SPEC['arena_base']<=value<SPEC['arena_end_exclusive']:
                self.assertTrue(name.startswith('QUEUE_') or name=='SpawnTable_Wram',name)

    def test_accepted_queues_unchanged(self):
        queues=generate(Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak'),ROOT/'distribution/bor.msu')
        self.assertEqual(len(queues),24)
        for path,data in queues.items(): self.assertEqual((ROOT/path).read_bytes(),data)

    def test_unseen_normal5b_full_queue_shadow(self):
        source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
        _,queues=compile_project(source,BASE,ROOT/'distribution/bor.msu',MSU_SHA)
        blob=queues['data/normal/5b.txt']
        self.assertEqual(len(blob),940)
        row=dict(project=source.path.name,set='Normal',stage=10,source_path='DATA\\NORMAL\\5B.TXT',packed_records=len(blob)//RECORD_SIZE)
        plan=plan_build([row])
        self.assertEqual((plan['capacity'],plan['buffer_bytes']),(94,940))
        self.assertEqual(assert_layout(ROOT,plan)['status'],'PASS')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'queue_abi';write_contract(plan,path)
            self.assertIn('QUEUE_CAPACITY = 94',path.with_suffix('.pasm').read_text())


if __name__=='__main__': unittest.main()
