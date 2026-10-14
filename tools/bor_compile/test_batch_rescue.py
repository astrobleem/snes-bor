from __future__ import annotations
import random,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import batch_model as m
import nonblank_batch_rescue as asm


class BatchTests(unittest.TestCase):
    def test_iram_lease_exact_bytes_and_reserved_regions(self):
        self.assertEqual(asm.RESTORE_BASE,0x3480)
        self.assertEqual(asm.RESTORE_BASE+asm.RESTORE_CAPACITY*4,0x3500)
        self.assertEqual(asm.QUEUE_BASE,0x3500)
        self.assertEqual(asm.QUEUE_END,0x36E0)
        self.assertLessEqual(asm.QUEUE_END,0x3700)
        self.assertEqual(asm.QUEUE_CAPACITY,6)
        self.assertEqual(asm.QUEUE_SLOTS+2*asm.QUEUE_CAPACITY,0x42D66E)
        self.assertLess(asm.EXACT_RETRY,0x42D680)

    def test_capacity_deficit_with_foreground_exact_retry(self):
        # Retained 16->17 witness: old picture owns 644 slots, giving 124 tail.
        old=frozenset(range(644))
        p=m.admission(old,list(range(30)),list(range(96)),list(range(88)))
        self.assertTrue(p.admitted)
        self.assertTrue(p.exact_retry)
        self.assertEqual((p.selected_count,p.free_slots),(118,124))
        self.assertEqual(len(p.pending_slots),118)
        self.assertFalse(set(p.pending_slots)&old)
        self.assertEqual(m.windows_for_pairs(p.selected_count),20)
        # Without precise foreground filtering, 126 > 124 is unsafe.
        q=m.admission(old,list(range(30)),list(range(96)),list(range(96)))
        self.assertFalse(q.admitted)
        self.assertEqual(q.failure,'TWO_FRAME_SLOT_CAPACITY')

    def test_capacity_when_exact_does_not_suffice(self):
        old=frozenset(range(658))
        a=m.admission(old,list(range(30)),list(range(96)),list(range(90)))
        self.assertFalse(a.admitted);self.assertTrue(a.exact_retry)
        self.assertEqual(a.failure,'TWO_FRAME_SLOT_CAPACITY')
        self.assertFalse(a.pending_slots)
        b=m.admission(old,list(range(33)),list(range(1)),list(range(1)))
        self.assertFalse(b.admitted)
        self.assertEqual(b.failure,'RESTORE_RECORD_CAPACITY')

    def test_exact_coverage_requires_subset(self):
        with self.assertRaisesRegex(ValueError,'SUBSET'):
            m.admission([],[],[1,2],[2,3])
        with self.assertRaisesRegex(ValueError,'SUBSET'):
            m.admission([],[],[1,1],[1])

    def test_batches_are_dma_correct_and_prior_picture_immutable(self):
        r=random.Random(7144)
        for trial in range(150):
            old_slots=tuple(r.sample(range(768),r.randrange(40,150)))
            # Use old slots only, do not write to existing old residents.
            old_map=tuple(r.choice(old_slots) for _ in range(1024))
            free=[s for s in range(596,768) if s not in old_slots]
            chosen=r.sample(free,r.randrange(1,min(40,len(free))+1))
            old=bytearray(r.randbytes(65536))
            p=m.Publisher(old_map,old)
            p.begin(tuple(r.choice(chosen) if i<min(200,len(chosen)*3) else old_map[i] for i in range(1024)))
            pairs={s:r.randbytes(80) for s in chosen}
            scratch=bytearray(80)
            for s in chosen:
                scratch[:]=pairs[s];p.enqueue(s,scratch)
                scratch[:]=b'Z'*80
            p.finish_ready()
            self.assertEqual(p.windows,m.windows_for_pairs(len(chosen)))
            self.assertEqual(len(p.packets),2*len(chosen))
            self.assertEqual(sum(len(t.data) for t in p.packets),80*len(chosen))
            self.assertEqual(p.display,old_map)
            p.assert_old_untouched()
            for pkt in p.packets:
                off=(pkt.source-asm.QUEUE_BASE)%80
                self.assertIn(off,(0,64))
                self.assertLess(pkt.source,asm.QUEUE_END)
                self.assertEqual(pkt.destination,slice_dest(pkt.slot,pkt.plane))
                self.assertEqual(pkt.data,pairs[pkt.slot][:64] if pkt.plane=='HIGH' else pairs[pkt.slot][64:])
            p.commit()
            self.assertEqual(p.committed_epochs,1)
            self.assertEqual(bytes(p.vram[61440:63488]),bytes(p.vram[63488:65536]))
            for s in chosen:self.assertEqual(p.read_pair(s),pairs[s])

    def test_rollback_after_preload_preserves_old(self):
        r=random.Random(17)
        old_map=tuple(range(200))*5+tuple(range(24))
        old_map=old_map[:1024]
        p=m.Publisher(old_map,r.randbytes(65536));p.begin(old_map)
        p.enqueue(596,r.randbytes(80));p.flush();before=p.display
        p.rollback();self.assertEqual(p.display,before);self.assertEqual(p.committed_epochs,0)
        p.assert_old_untouched()
        # Abandoned bytes in unreferenced slot are safe to retain.
        self.assertEqual(p.queue,[])

    def test_reject_displayed_slot_and_partial_commit(self):
        p=m.Publisher((7,)*1024,bytes(65536))
        p.begin((8,)*1024)
        with self.assertRaisesRegex(ValueError,'UNSAFE_PENDING_SLOT'):p.enqueue(7,bytes(80))
        with self.assertRaisesRegex(ValueError,'COMMIT_BEFORE'):p.commit()
        p.enqueue(8,bytes(80));p.finish_ready();p.commit()
        self.assertEqual(p.display[1],8)
        self.assertEqual(p.read_pair(8),bytes(80))

    def test_successive_published_snapshots_preserve_new_display(self):
        r=random.Random(733)
        p=m.Publisher((0,)*1024,r.randbytes(65536))
        p.begin((1,)*128 + (0,)*896)
        p.enqueue(1,r.randbytes(80))
        p.finish_ready();p.commit()
        p.assert_old_untouched()
        saved1=p.read_pair(1)
        p.begin((2,)*128+(1,)*128+(0,)*768)
        with self.assertRaisesRegex(ValueError,'UNSAFE_PENDING_SLOT'):
            p.enqueue(1,r.randbytes(80))
        p.enqueue(2,r.randbytes(80));p.finish_ready()
        p.assert_old_untouched();self.assertEqual(p.read_pair(1),saved1)
        p.commit()
        self.assertEqual(p.committed_epochs,2)
        self.assertEqual(p.read_pair(1),saved1)
        self.assertEqual(p.display[0],2)

    def test_six_pair_vblank_budget_requires_native_timing(self):
        # The 1,961-clock estimate from the old BW-RAM direct path is only a
        # design input. I-RAM source + queue code MUST be measured natively.
        a=m.budget(6,1961,1500,50464,margin=10000)
        self.assertTrue(a['admissible'])
        b=m.budget(6,8000,1500,50464,margin=10000)
        self.assertFalse(b['admissible'])
        self.assertEqual(m.windows_for_pairs(108),18)
        self.assertEqual(m.windows_for_pairs(111),19)
        self.assertEqual(m.windows_for_pairs(126),21)

    def test_dma_emitter_has_separate_high_low_source_registers(self):
        a=asm._new_preloader();s='\n'.join(a)
        self.assertIn('NbQueueDirectPair:',s)
        self.assertIn('OnlineDmaDone10:',s)
        self.assertIn('OnlineDmaDone11:',s)
        self.assertEqual(s.count(' mvn $00,$42'),2)
        self.assertEqual(s.count(' sta.l $004372'),2)
        self.assertEqual(s.count(' sta.l $004375'),2)
        self.assertEqual(s.count(' sta.l $00420B'),2)
        self.assertIn(' sta.l $002116',s)
        self.assertIn(' adc #64',s)
        self.assertIn(' cmp #6',s)
        self.assertEqual(s.count(' jsr NbFreshVblank'),1)
        self.assertEqual(s.count(' jsr NbQueueDirectPair'),1)
        self.assertEqual(s.count('NbPairComplete:'),1)

    def test_transform_guards_missing_anchor(self):
        with self.assertRaisesRegex(asm.BatchContractError,'SOURCE_ANCHOR'):
            asm.transform(['.org $A000','NbBegin:'])


def slice_dest(slot,plane):
    return slot*64 if plane=='HIGH' else 49152+slot*16


if __name__=='__main__':unittest.main()
