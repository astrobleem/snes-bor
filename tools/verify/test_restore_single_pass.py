"""Execute encoded old/new planner instructions, not a line-based simulation.

The instruction tests stop at the allocator's genuine retry/rejection targets;
the full rollback/composition/DMA bodies are exercised only by the native suite.
No SNES master-clock timings are inferred from this restricted executor.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
import random
import unittest

import restore_single_pass as rp
from restore_single_pass_vm import assemble, Machine

# Exact allocator control flow from the pinned batch + home-borrow transforms.
# Borrowing is not prepared until AFTER restoration, so BhTake is unreachable.
ALLOCATOR = rp.asm('''
NbFree:
 lda $2E
 cmp #768
 bcc NbFreeCheck
 lda.l $42D70C
 cmp #1
 bne BhOriginalExhaustion
 jsr BhTake
 bcs BhOriginalExhaustion
 rts
BhOriginalExhaustion:
 pla
 lda.l $42D674
 bne NbExactExhausted
 lda #1
 sta.l $42D674
 jmp NbBeginRetry
NbExactExhausted:
 jmp NbAbort
NbFreeCheck:
 asl a
 tax
 lda.l $42D000,x
 and #$3FFF
 beq NbFreeFound
 inc $2E
 jmp NbFree
NbFreeFound:
 lda $2E
 sta $2C
 inc $2E
 rts
NbActorPlanStart:
 rts
NbAbort:
 rts
NbBeginRetry:
 rts
BhTake:
 rts
''')


def program(candidate: bool):
    main = rp.main_loop() if candidate else rp.original_plan()
    return assemble(rp.asm('''
TestStart:
 lda #0
 sta $18
 jmp NbRestorePlan
''') + main + ALLOCATOR + (rp.resolver() if candidate else []), base=0x39A000)

OLD = program(False)
NEW = program(True)

class PlanMachine(Machine):
    def __init__(self, candidate: bool, pending, refs, cursor=596, exact=True):
        super().__init__(NEW if candidate else OLD)
        self.ram[0][:] = bytes([0xA5])*65536
        self.ram[0x42][:] = bytes([0x5A])*65536
        self.load_words(0x42C000, pending)
        self.load_words(0x42D000, refs)
        self.poke16(0x342E, cursor)
        self.poke16(0x42D606, 0)
        self.poke16(0x42D674, int(exact))
        self.poke16(0x42D70C, 0)
        self.outcome = None
        self.reservations = []
        self.record_reads = 0
        self.first_reads = []
        self.hooks['NbFreeFound'] = lambda m: self.reservations.append(m.peek16(0x342E))
        self.hooks['NbActorPlanStart'] = lambda m: setattr(self, 'outcome', 'success')
        self.hooks['NbAbort'] = lambda m: setattr(self, 'outcome', 'abort')
        self.hooks['NbBeginRetry'] = lambda m: setattr(self, 'outcome', 'retry')
        self.hooks['BhTake'] = lambda m: (_ for _ in ()).throw(AssertionError('Borrowing before BhPrepare'))
        if candidate:
            self.hooks['RpCellLoaded'] = lambda m: self.first_reads.append(m.peek16(0x3418))

    def read16(self, address):
        if 0x3480 <= address < 0x3500 or 0x42D620 <= address < 0x42D660:
            self.record_reads += 1
        return super().read16(address)

    def records(self):
        return [(self.peek16(rp.record_address(i)), self.peek16(rp.record_address(i)+2))
                for i in range(self.peek16(0x42D606))]

    def pending(self):
        return [self.peek16(0x42C000+2*i) for i in range(1024)]


def check_pair(pending, refs, *, cursor=596, exact=True, run_old=True):
    old = PlanMachine(False, pending, refs, cursor, exact) if run_old else None
    new = PlanMachine(True, pending, refs, cursor, exact)
    oracle = rp.reference(pending, refs, cursor)
    for m in [m for m in (old, new) if m is not None]:
        before = {k: bytes(v) for k, v in m.ram.items()}
        state = (m.y, m.d, m.dbr, m.sp)
        m.run('TestStart')
        assert (m.y, m.d, m.dbr, m.sp) == state
        expected = 'success' if oracle['success'] else ('retry' if not exact and oracle['failure']=='tail_exhausted' else 'abort')
        assert m.outcome == expected, (m.outcome, expected)
        assert m.records() == oracle['records']
        assert m.reservations == [d for h,d in oracle['records']]
        assert m.peek16(0x342E) == oracle['cursor']
        assert m.peek16(0x3418) == oracle['stopped_cell']
        if oracle['success']:
            assert m.pending() == oracle['pending']
        assert m.blob(0x42D000, 1536) == bytes(before[0x42][0xD000:0xD600])
        assert m.blob(0x3500, 480) == bytes(before[0][0x3500:0x36E0])
        assert m.blob(0x42D60C, 20) == bytes(before[0x42][0xD60C:0xD620])
        assert m.blob(0x42D700, 144) == bytes(before[0x42][0xD700:0xD790])
        # No source, queue, directory, journal, latch or PPU writes.
        for address, value, size, pc in m.writes:
            legal = ((0x100 <= address < 0x200) or
                     (0x3400 <= address and address+size <= 0x3480) or
                     (0x3480 <= address and address+size <= 0x3500) or
                     (0x42C000 <= address and address+size <= 0x42C800) or
                     (0x42D620 <= address and address+size <= 0x42D660) or
                     address in (0x42D606, 0x42D674))
            assert legal, hex(address)
        # Only the live record prefix can be read or modified.
        count = len(oracle['records'])
        for i in range(count,48):
            address = rp.record_address(i)
            assert m.blob(address,4) == before[address>>16][address&65535:(address&65535)+4]
    assert new.reads['pending_map'] == oracle['stopped_cell'] + (not oracle['success'])
    assert new.first_reads == list(range(new.reads['pending_map']))
    if old is not None:
        assert new.records() == old.records()
        assert new.reservations == old.reservations
    return old, new, oracle


def fixture_source():
    return rp.asm('''
NbBeginRetry:
 lda #0
 sta.l $42D606
NbRestorePlanStart:
 lda #0
 sta $18
''') + rp.original_plan() + rp.asm('''
NbActorPlanStart:
 rts
NbCodeEnd:
SpLatched:
 rts
BhBitmapBuilt:
 rts
BhCodeEnd:
''') + ['.org $C000']


def synthetic_ten_home_case():
    """Shape-only test, NOT Sol's captured map: 10 homes, 95 actors, 64 tails."""
    rng = random.Random(0x8D317E5)
    invalid = [10,53,100,151,204,300,401,500,544,575]
    available = [h for h in range(596) if h not in invalid]
    pending = [rng.choice(available) for _ in range(1024)]
    for i,h in enumerate(invalid):
        for at in (100+i, 430+3*i, 900+2*i):
            pending[at]=h
    pending[:95]=[65535]*95
    refs = [0]*768
    for h in invalid: refs[h]=0x8000 | rng.randrange(4)
    for s in range(596,704): refs[s]=1
    return pending,refs


class RestorationTests(unittest.TestCase):
    def test_ten_home_consecutive_shape(self):
        old,new,_=check_pair(*synthetic_ten_home_case())
        self.assertEqual(old.reads['pending_map'],11264)
        self.assertEqual(new.reads['pending_map'],1024)
        self.assertLess(new.steps,old.steps)

    def test_no_restorations_has_no_extra_executed_instructions(self):
        pending=[i%596 for i in range(1024)]; refs=[0]*768
        old,new,_=check_pair(pending,refs)
        self.assertEqual(old.steps,new.steps)
        self.assertEqual(new.record_reads,0)

    def test_every_cell_same_invalid_home_allocates_only_once(self):
        refs=[0]*768;refs[204]=0x8007
        old,new,o=check_pair([204]*1024,refs)
        self.assertEqual(o['records'],[(204,596)])
        self.assertEqual(new.records(),[(204,596)])

    def test_all_48_records_and_repeats_after_capacity(self):
        refs=[0]*768
        for h in range(48): refs[h]=0x8000
        pending=list(range(48))+[47,32,31,0]*244
        self.assertEqual(len(pending),1024)
        old,new,o=check_pair(pending,refs)
        self.assertEqual(len(o['records']),48)
        self.assertGreater(new.hits['RpReadSpillHome'],0)

    def test_49th_distinct_home_rejects_before_allocation(self):
        refs=[0]*768
        for h in range(49):refs[h]=0x8000
        pending=list(range(49))+[100]*975
        old,new,o=check_pair(pending,refs)
        self.assertEqual(o['failure'],'record_limit')
        self.assertEqual(new.outcome,'abort')
        self.assertEqual(len(new.reservations),48)

    def test_last_slot_and_exact_failure_stack(self):
        refs=[0]*768;refs[0]=refs[1]=0x8000
        pending=[0,0,1]+[100]*1021
        _,m,o=check_pair(pending,refs,cursor=767)
        self.assertEqual(m.reservations,[767])
        self.assertEqual(o['failure'],'tail_exhausted')
        self.assertEqual(m.sp,0x1FF)

    def test_conservative_exhaustion_retains_original_retry_unwind(self):
        refs=[1]*768;refs[0]=0x8001
        _,m,o=check_pair([0]+[65535]*1023,refs,exact=False)
        self.assertEqual(m.outcome,'retry')
        self.assertEqual(m.peek16(0x42D674),1)
        self.assertEqual(m.sp,0x1FF)

    def test_32nd_and_33rd_split_records_do_not_read_latch(self):
        refs=[0]*768
        for h in range(33):refs[h]=0x8000
        _,m,o=check_pair(list(range(33))+[32,31,0]*330+[32],refs)
        self.assertEqual(len(o['records']),33)
        self.assertEqual(m.peek16(0x34FC),31)
        self.assertEqual(m.peek16(0x42D620),32)

    def test_tags_tail_words_and_actor_markers_are_preserved(self):
        words=[0xFFFF,0x4000|204,0x8000|204,0xC000|204,596,767]
        pending=(words*171)[:1024];refs=[0]*768;refs[204]=0x8000
        _,m,o=check_pair(pending,refs)
        self.assertEqual(m.pending(),pending)
        self.assertEqual(o['records'],[])

    def test_scattered_free_tails_and_high_flags_match_original(self):
        refs=[0]*768
        for h in (0,31,32,595):refs[h]=0x8000
        refs[596:]=[0x8001]*172
        for i,s in enumerate((597,612,711,767)):refs[s]=[0,0x4000,0x8000,0xC000][i]
        _,m,_=check_pair(([0,31,32,595]*256),refs)
        self.assertEqual(m.reservations,[597,612,711,767])

    def test_random_full_maps_against_eager_reference(self):
        rng=random.Random(0xC0FFEE)
        for case in range(64):
            n=rng.randrange(0,51)
            invalid=set(rng.sample(range(596),n))
            refs=[rng.randrange(3) for _ in range(768)]
            for h in invalid:refs[h]|=0x8000
            for s in rng.sample(range(596,768),rng.randrange(0,80)):refs[s]=rng.choice((0,0x4000,0x8000,0xC000))
            values=list(range(596))+[65535,767,0x4000|23,0x8000|99]
            pending=[rng.choice(values) for _ in range(1024)]
            # Explicit duplicates stress record searches without synthetic state writes.
            if invalid:
                for i in range(0,1024,11):pending[i]=rng.choice(tuple(invalid))
            with self.subTest(case=case):check_pair(pending,refs,exact=bool(case%2),run_old=False)


class OverlayTests(unittest.TestCase):
    def test_exact_two_source_edits(self):
        src=fixture_source(); out=rp.transform(src)
        a=src.index('NbRestorePlan:');b=src.index('NbActorPlanStart:')
        expected=src[:a]+rp.main_loop()+src[b:]
        i=expected.index('NbCodeEnd:');expected[i:i]=rp.resolver()
        self.assertEqual(out,expected)
        self.assertEqual(out.count(' jsr NbFree'),1)
        self.assertNotIn(' jsr RpResolveRestore',out)

    def test_source_drift_is_not_silently_adapted(self):
        src=fixture_source();src[src.index(' cmp #48')]=' cmp #49'
        with self.assertRaisesRegex(rp.RestoreContractError,'PINNED_PLAN'):rp.transform(src)

    def test_retry_reset_must_be_zero_and_present(self):
        for action in ('remove','nonzero'):
            src=fixture_source();i=src.index(' sta.l $42D606')
            if action=='remove':del src[i]
            else:src[i-1]=' lda #1'
            with self.assertRaisesRegex(rp.RestoreContractError,'RESET'):rp.transform(src)

    def test_double_application_rejects(self):
        with self.assertRaisesRegex(rp.RestoreContractError,'ALREADY'):rp.transform(rp.transform(fixture_source()))

    def test_required_bitmap_and_source_latch_contract(self):
        for label in ('BhBitmapBuilt:','SpLatched:'):
            src=fixture_source();src.remove(label)
            with self.assertRaises(rp.RestoreContractError):rp.transform(src)

    def test_record_address_boundaries(self):
        self.assertEqual([rp.record_address(i) for i in (0,31,32,47)],
                         [0x3480,0x34FC,0x42D620,0x42D65C])
        for i in (-1,48,True):
            with self.assertRaises(ValueError):rp.record_address(i)

    def test_independent_encoder_known_opcodes(self):
        p=assemble([' ldx $70',' bra Done',' lda #1','Done:',' rts'],0x39A000)
        self.assertEqual(p.data,bytes.fromhex('a6708003a9010060'))
        m=Machine(p);m.poke16(0x3470,123);m.run('Done')
        self.assertEqual(m.sp,0x1FF)


def report():
    cases={}
    for name,pending,refs in [('synthetic_ten_home_95_actor_64_tail',*synthetic_ten_home_case()),
                              ('no_restore',[i%596 for i in range(1024)],[0]*768)]:
        old,new,oracle=check_pair(pending,refs)
        def row(m):return dict(executed_instructions=m.steps,pending_map_word_reads=m.reads['pending_map'],
                              restoration_record_word_reads=m.record_reads,reference_word_reads=m.reads['references'])
        cases[name]=dict(original=row(old),candidate=row(new),records=oracle['records'],
                         allocation_order_identical=True,completed_map_identical=True)
    return dict(scope='Restricted byte execution; synthetic maps, not native SNES timing',
                base_commit=rp.BASE_COMMIT,plan_source_sha256=rp.plan_digest(),cases=cases,
                code_bytes=dict(original_plan=len(assemble(rp.original_plan(),0x39A100,
                                {'NbActorPlanStart':0x39A18D,'NbAbort':0x39A400,'NbFree':0x39A500}).data)),
                native_poppy_mesen_run_here=False)

if __name__=='__main__':unittest.main()
