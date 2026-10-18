"""Q8 zero-copy policy, exact anchors, scratch lifetime and DMA semantics.

Offline tests: NOT a hardware certification or an instruction-clock estimate.
"""
from __future__ import annotations
import random,sys,types,unittest
from unittest.mock import patch
from eight_pair_direct import *


def source_calc():
    return [' lda $70',' asl a',' asl a',' asl a',' asl a',' sta $74',
            ' asl a',' asl a',' clc',' adc $74',' clc',' adc #$3500',' sta $72']


def fixture():
    # Reproduce Q7's exact control and queue-copy anchors (other assembly is
    # intentionally schematic; Mesen verifies the real complete publisher).
    from test_seven_pair_spill import fixture as q7_fixture
    with patch.dict(sys.modules,{'nonblank_batch_rescue':types.SimpleNamespace(
        _source_addr_from_index=source_calc)}):
        from seven_pair_spill import transform as q7
        a=q7(q7_fixture())
    idx=a.index(' jsr Q7SourceFromIndex',a.index('NbQueueSpace:'))
    start=idx+1
    end=a.index(' sta.l $42D660',start)
    a[start:end]=[' phb',' lda #63',' ldx #$D680',' ldy $72',' mvn $00,$42',' plb',
                  ' phb',' ldx #$D6C0',' lda #15',' mvn $00,$42',' plb',
                  ' lda.l $42D660',' inc a']
    flush=a.index('NbQueueNotFull:')
    a[flush:flush]=[' jsr NbFlushQueue']
    # The synthetic original fixture has the first sta.l immediately after.
    idx=a.index('NbPairBegin:')
    a[idx+3:idx+3]=[' jsr NbQueueDirectPair','NbPairComplete:','.a16','.i16',
                     'NbQueueDirectPair:','.a16','.i16']
    a+=['WarmDirectPair:','.a16','.i16','OnlineDmaDone8:','.a16','.i16',
        'OnlineDmaDone9:','.a16','.i16','OnlineDmaDone10:','.a16','.i16',
        'OnlineDmaDone11:','.a16','.i16']
    return a


class EightPairTests(unittest.TestCase):
    def test_record_policy_and_mode_two(self):
        for n in range(49):
            self.assertEqual(queue_capacity(n),8 if n<=12 else 6)
            self.assertEqual(queue_capacity(n,2),6)
        for bad in (None,True,12.0,'12',-1,49):
            with self.assertRaises(ValueError):queue_capacity(bad)
        for bad in (True,-1,65536):
            with self.assertRaises(ValueError):queue_capacity(5,bad)

    def test_exact_byte_leases(self):
        self.assertEqual((SCRATCH_HIGH,SCRATCH_LOW,SCRATCH_END),(0x42d680,0x42d6c0,0x42d6d0))
        self.assertEqual(SCRATCH_END-SCRATCH_HIGH,80)
        self.assertEqual(SLOT8_WORD,0x42d670)
        self.assertEqual(NEW_LIMIT_WORD,0x42d676)
        self.assertLess(SLOT8_WORD+1,EXACT_RETRY)
        self.assertGreater(NEW_LIMIT_WORD,EXACT_RETRY+1)
        self.assertEqual([output_sources(i,10) for i in range(8)],
         [(0x3500+i*80,0x3540+i*80) for i in range(6)]+[(0x34b0,0x34f0),(0x42d680,0x42d6c0)])
        self.assertIsNone(staging_source(7,10))
        self.assertIsNotNone(staging_source(6,10))

    def test_batch_boundaries(self):
        self.assertEqual(batch_sizes(105,10),[8]*13+[1])
        self.assertEqual(batch_sizes(108,6),[8]*13+[4])
        self.assertEqual(batch_sizes(105,10,2),[6]*17+[3])
        self.assertEqual(batch_sizes(105,13),[6]*17+[3])
        self.assertEqual(batch_sizes(0,10),[])

    def test_exact_source_and_calls(self):
        before=fixture();after=transform(before)
        self.assertEqual(after.count('Q8ScratchNoStage:'),1)
        self.assertEqual(after.count('Q8DirectScratch:'),1)
        self.assertEqual(after.count(' jsr WarmDirectPair'),1)
        self.assertEqual(after.count(' jsr NbQueueDirectPair'),1)
        self.assertEqual(after.count(' jsr Q7SourceFromIndex'),2)
        self.assertEqual(after.count(' cmp.l $42D670'),0)
        self.assertEqual(after.count(' cmp.l $42D676'),2)
        self.assertEqual(after.count(' sta.l $42D676'),2)
        self.assertEqual(after.count(' sta.l $42D670'),0)
        self.assertIn(' lda #8',after)
        self.assertLess(after.index('Q8ScratchNoStage:'),after.index('NbQueueNotFull:'))
        self.assertLess(after.index('Q8DirectScratch:'),after.index('NbPairComplete:'))
        self.assertEqual(after[after.index('Q7SourceFromIndex:'):after.index('Q7CodeEnd:')],
                         before[before.index('Q7SourceFromIndex:'):before.index('Q7CodeEnd:')])
        with self.assertRaises(EightPairContractError):transform(after)

    def test_nothing_changes_outside_queue_and_policy(self):
        before=fixture();after=transform(before)
        self.assertEqual(before[:before.index('Q7PolicyBegin:')],after[:after.index('Q7PolicyBegin:')])
        self.assertEqual(before[before.index('Q7SourceFromIndex:'):],
                         after[after.index('Q7SourceFromIndex:'):])
        self.assertNotIn(' sta.l $42D000','\n'.join(after))
        self.assertNotIn(' lda.l $7FBA90','\n'.join(after))

    def test_misidentified_q7_source_fails_closed(self):
        for mutation in ('policy','scratch','drain','metadata','label'):
            a=fixture()
            if mutation=='policy':a[a.index(' lda #7')]=' lda #9'
            if mutation=='scratch':a[a.index(' mvn $00,$42')]=' mvn $00,$00'
            if mutation=='drain':a[a.index(' jsr NbQueueDirectPair')]=' jsr WarmDirectPair'
            if mutation=='metadata':a+=[' lda.l $42D676']
            if mutation=='label':a.remove('WarmDirectPair:')
            with self.subTest(mutation=mutation),self.assertRaises(EightPairContractError):transform(a)

    def test_fail_closed_if_full_queue_does_not_flush(self):
        a=fixture();p=a.index('NbQueueNotFull:');self.assertEqual(a[p-1],' jsr NbFlushQueue');a.pop(p-1)
        # A previous entry-boundary flush still exists; this test removes the
        # stage-full flush without allowing the eighth scratch to go stale.
        with self.assertRaisesRegex(EightPairContractError,'IMMEDIATE_FULL_QUEUE_FLUSH'):
            transform(a)

    def test_8th_index_not_available_in_six_mode(self):
        for records,mode in ((48,0),(13,0),(0,2),(10,2)):
            with self.assertRaises(ValueError):staging_source(7,records,mode)
        for bad in (-1,8,True,'7'):
            with self.assertRaises(ValueError):staging_source(bad,10)

    def test_direct_pair_is_last_composition(self):
        src=transform(fixture())
        # The 8th slot is explicitly not staged. Once accepted, queue count
        # grows from 7 to 8, forcing immediate synchronous NbFlushQueue.
        low=src.index('Q8ScratchNoStage:');hi=src.index('NbQueueNotFull:')
        self.assertEqual(src[low+3:low+7],[' lda.l $42D660',' inc a',' sta.l $42D660',' cmp.l $42D676'])
        self.assertEqual(src[hi-1], ' jsr NbFlushQueue')
        self.assertNotIn(' mvn $00,$42',src[low:hi])
        direct=src[src.index('Q8DirectScratch:'):src.index('Q8DirectComplete:')]
        self.assertEqual(direct[-1],' jsr WarmDirectPair')

    def test_packet_payload_semantics_randomized(self):
        rng=random.Random(8558)
        for size in (0,1,7,8,13,14,15,16,17,104,105,108,235):
            source=[(rng.randbytes(64),rng.randbytes(16),i%768) for i in range(size)]
            rebuilt=[];cursor=0
            for count in batch_sizes(size,10):
                staged={}
                scratch=None
                for i in range(count):
                    addr=staging_source(i,10)
                    if addr is None:scratch=source[cursor+i]
                    else:staged[addr]=source[cursor+i]
                for i in range(count):
                    addr=staging_source(i,10)
                    rebuilt.append(scratch if addr is None else staged[addr])
                cursor+=count
            self.assertEqual(source,rebuilt)

    def test_restoration_and_rollback_mode_timeline(self):
        # Native checks the physical writes; offline enforces bounded record
        # lifetime and no request when >12 records are still live.
        for records in range(49):
            cap=queue_capacity(records)
            staged=[staging_source(i,records) for i in range(cap)]
            if cap==8:
                self.assertEqual(staged[-1],None)
                self.assertTrue(0x3480+records*4<=0x34b0)
            else:
                self.assertNotIn(None,staged)


if __name__=='__main__':unittest.main()
