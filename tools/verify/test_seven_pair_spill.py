"""Offline policy, source-anchor and scratch-lifetime tests. Not Mesen."""
from __future__ import annotations
import sys
import types
import unittest
from unittest.mock import patch
from seven_pair_spill import (queue_limit, queue_address, batch_sizes, transform,
    SevenPairContractError, SEVENTH_PAIR_BASE, SEVENTH_PAIR_END,
    _source_helper, _policy)


def source_calc():
    return [' lda $70',' asl a',' asl a',' asl a',' asl a',' sta $74',
            ' asl a',' asl a',' clc',' adc $74',' clc',' adc #$3500',' sta $72']


def fixture():
    calc=source_calc()
    return [
      'BhActorPlanAdmitted:', '.a16', '.i16', 'NbActorPlan:', '.a16','.i16',
      'NbRestoreProduce:', '.a16','.i16','NbActorProduce:','.a16','.i16',
      'NbPreloadPair:','.a16','.i16',
      ' lda.l $42D660',' cmp #6',' bcc NbQueueSpace',' jsr NbFlushQueue',
      'NbQueueSpace:','.a16','.i16',
      ' lda.l $42D660',' sta $70',*calc,
      ' phb',' lda #63',' ldx #$D680',
      ' sta.l $42D660',' cmp #6',' bne NbQueueNotFull',
      'NbQueueNotFull:','.a16','.i16',
      'NbFlushQueue:','.a16','.i16',
      'NbQueueDrain:','.a16','.i16',
      ' sta $2C',*calc,'NbPairBegin:','.a16','.i16',
      'RpResolveRestore:','.a16','.i16','NbCodeEnd:','.a16','.i16',
      'BhBitmapBuilt:','.a16','.i16','.org $C000'
    ]


class SevenPairTests(unittest.TestCase):
    def setUp(self):
        self.patcher=patch.dict(sys.modules,{'nonblank_batch_rescue':types.SimpleNamespace(_source_addr_from_index=source_calc)})
        self.patcher.start();self.addCleanup(self.patcher.stop)

    def test_twelve_record_boundary(self):
        for n in range(49):
            self.assertEqual(queue_limit(n),7 if n<=12 else 6)
            self.assertEqual(queue_limit(n,2),6)
        for bad in (-1,49,65535,'10'):
            with self.assertRaises(ValueError):queue_limit(bad)

    def test_alias_ledger(self):
        for n in range(13):
            low=0x3480+4*n
            self.assertLessEqual(low,SEVENTH_PAIR_BASE)
            self.assertEqual(queue_address(6,n),0x34b0)
            self.assertEqual(SEVENTH_PAIR_END,0x3500)
        for n in range(13,49):
            with self.assertRaises(ValueError):queue_address(6,n)
        self.assertEqual(queue_address(5,12),0x3690)
        self.assertEqual([queue_address(i,12) for i in range(7)],
                         [0x3500,0x3550,0x35a0,0x35f0,0x3640,0x3690,0x34b0])
        self.assertTrue(all(not (0x3480<=queue_address(i,12)<0x34B0)
                            for i in range(7)))

    def test_batch_boundaries(self):
        self.assertEqual(batch_sizes(105,10),[7]*15)
        self.assertEqual(batch_sizes(105,10,2),[6]*17+[3])
        self.assertEqual(batch_sizes(105,34),[6]*17+[3])
        self.assertEqual(batch_sizes(108,6),[7]*15+[3])
        self.assertEqual(batch_sizes(0,10),[])

    def test_transform_exact_source(self):
        old=fixture();new=transform(old)
        self.assertEqual(new.count('Q7SourceFromIndex:'),1)
        self.assertEqual(new.count(' jsr Q7SourceFromIndex'),2)
        self.assertEqual(new.count(' sta.l $42D670'),2)
        self.assertEqual(new.count(' cmp.l $42D670'),2)
        self.assertEqual(new.count('Q7PolicyDone:'),1)
        self.assertLess(new.index('NbQueueDrain:'),new.index('Q7SourceFromIndex:'))
        self.assertLess(new.index('Q7CodeEnd:'),new.index('NbCodeEnd:'))
        # Both queue transfer descriptors and the earlier code remain untouched.
        self.assertEqual(new[new.index('RpResolveRestore:'):new.index('Q7SourceFromIndex:')],
                         old[old.index('RpResolveRestore:'):old.index('NbCodeEnd:')])
        with self.assertRaises(SevenPairContractError):transform(new)

    def test_fail_closed_on_queue_drift(self):
        src=fixture();src.remove(' cmp #6')
        with self.assertRaises(SevenPairContractError):transform(src)
        src=fixture();src.remove('RpResolveRestore:')
        with self.assertRaises(SevenPairContractError):transform(src)
        src=fixture();src[src.index(' sta $2C')]=' sta $2D'
        with self.assertRaises(SevenPairContractError):transform(src)

    def test_policy_uses_only_count_and_fault_mode(self):
        txt='\n'.join(_policy())
        self.assertIn('lda.l $42D606',txt)
        self.assertIn('lda.l $42D602',txt)
        self.assertNotIn('7FBA90',txt)  # no epoch-dependent behavior
        self.assertNotIn('414000',txt)  # no actor-dependent behavior

    def test_mapped_source_helper_no_extra_writes(self):
        txt='\n'.join(_source_helper())
        self.assertIn('lda #$34B0',txt)
        self.assertIn('adc #$3500',txt)
        self.assertEqual(txt.count('sta $72'),2)
        self.assertNotIn('sta.l $42D000',txt)

    def test_packet_equivalence(self):
        # Content of HIGH/LOW descriptors must stay identical; only source
        # of seventh queued pair changes, never destination/ordering.
        import random
        for seed in range(24):
            rng=random.Random(seed)
            count=rng.randrange(1,240)
            pairs=[(rng.randbytes(64),rng.randbytes(16),rng.randrange(596,768)) for _ in range(count)]
            for records in (0,10,12,13,34,48):
                out=[];pos=0
                for batch in batch_sizes(count,records):
                    staged={queue_address(i,records):pairs[pos+i] for i in range(batch)}
                    for i in range(batch):
                        out.append(staged[queue_address(i,records)])
                    pos+=batch
                self.assertEqual(pairs,out)


if __name__=='__main__':unittest.main()
