"""Offline machine-byte verification; NEVER presented as native Mesen timing."""
from __future__ import annotations
import random
import unittest
from home_borrow_bitmap import _routines,membership_reference,COMMITTED_BITS,PENDING_BITS,BITMAP_BYTES
from home_bitmap_shared_cells import transform,original_loop,shared_loop,SharedCellContractError
from bitmap_shared_vm import assemble,Machine


def full(new=False):
    old=_routines()
    if new:
        p=old.index('BhBitmapMapLoop:');q=old.index('BhBitmapBuilt:')
        old=old[:p]+shared_loop()+old[q:]
    return assemble(old,base=0x39B700)

OLD=full(False)
NEW=full(True)


def load(program,committed,pending,state=1):
    m=Machine(program)
    m.ram[0][0x34A0:0x36e0]=bytes([0xA5])*(0x36e0-0x34a0)
    m.load_words(0x42C800,committed)
    m.load_words(0x42C000,pending)
    m.poke16(0x42D600,state)
    m.poke16(0x42D660,0)
    m.poke16(0x42D608,0)
    m.poke16(0x42D60A,0)
    m.poke16(0x42D70C,0)
    return m


def result(m):
    return m.blob(COMMITTED_BITS,BITMAP_BYTES)+m.blob(PENDING_BITS,BITMAP_BYTES)


def run_pair(cm,pm):
    a,b=load(OLD,cm,pm),load(NEW,cm,pm)
    a.run('BhBitmapBuild');b.run('BhBitmapBuild')
    answer=b''.join(membership_reference(cm,pm))
    if a.c or b.c or result(a)!=answer or result(b)!=answer:
        raise AssertionError('Membership changed')
    return a,b

class SharedBitmapTests(unittest.TestCase):
    def test_binary_encodings_and_size(self):
        self.assertEqual(len(OLD.data),205)
        self.assertEqual(len(NEW.data),240)
        self.assertEqual(len(NEW.data)-len(OLD.data),35)
        self.assertIn(b'\xdf\x00\xc0\x42',NEW.data)  # CMP $42C000,X
        self.assertEqual(NEW.symbols['BhBitmapCodeEnd']-NEW.symbols['BhBitmapBuild'],240)
        self.assertEqual(OLD.symbols['BhBitmapCodeEnd']-OLD.symbols['BhBitmapBuild'],205)

    def test_strict_overlay_scope(self):
        source=['NbRestorePlan:','RpResolveRestore:','BhEligible:',*_routines(),
                'BhCodeEnd:','.org $C000']
        candidate=transform(source)
        lo=source.index('BhBitmapMapLoop:');hi=source.index('BhBitmapBuilt:')
        self.assertEqual(candidate[:lo],source[:lo])
        self.assertEqual(candidate[lo:lo+len(shared_loop())],shared_loop())
        self.assertEqual(candidate[lo+len(shared_loop()):],source[hi:])
        with self.assertRaises(SharedCellContractError):transform(candidate)
        for before,after in [(' cmp #2048',' cmp #2047'),(' lda.l $42C000,x',' lda.l $42C800,x')]:
            drift=source.copy();k=drift.index(before,lo);drift[k]=after
            with self.assertRaises(SharedCellContractError):transform(drift)

    def test_identical_backdrop_words_are_shared_exactly(self):
        cm=[i%596 for i in range(1024)];pm=cm.copy()
        a,b=run_pair(cm,pm)
        self.assertEqual(b.hits['BhBitmapDifferent'],0)
        self.assertEqual(b.hits['BhBitmapMapLoop'],1024)
        self.assertEqual(a.reads['pending_map'],b.reads['pending_map'])
        self.assertLess(b.steps,a.steps)
        self.assertLess(b.hits['BhBitmapAddress'],a.hits['BhBitmapAddress'])
        self.assertEqual(a.hits['BhBitmapAddress'],2048)
        self.assertEqual(b.hits['BhBitmapAddress'],1024)
        self.assertEqual(b.y,0xBEEF)

    def test_tagged_committed_words_never_use_unsafe_fast_path(self):
        for tag in (0,0x4000,0x8000,0xC000):
            cm=[tag + i%596 for i in range(1024)];pm=cm.copy()
            a,b=run_pair(cm,pm)
            self.assertEqual(a.blob(0x3598,0x148),b.blob(0x3598,0x148))
            if tag:self.assertEqual(b.hits['BhBitmapDifferent'],0)
        # Tagged PENDING may point at the same physical home but must still
        # execute the original slow membership check (and set pending bits).
        cm=[i%596 for i in range(1024)]
        pm=[h|0x4000 for h in cm]
        a,b=run_pair(cm,pm)
        self.assertEqual(b.hits['BhBitmapDifferent'],1024)
        self.assertEqual(b.hits['BhBitmapAddress'],2048)

    def test_out_of_domain_and_actor_markers(self):
        cm=([596,767,768,0x3fff,0x4000,0x8000,0xc000,0xffff]*128)
        pm=([0xffff,768,0x4001,0x8000,0xc000,595,0xdead,0]*128)
        run_pair(cm,pm)

    def test_mixed_controlled_map_no_stray_writes(self):
        cm=([i%596 for i in range(895)]+[650+i%90 for i in range(129)])
        pm=cm.copy()
        for k in range(30):pm[k*3]=0xffff
        for k in range(20):pm[k*5+500]=(cm[k*5+500]|0x4000)
        a,b=run_pair(cm,pm)
        self.assertLess(b.steps,a.steps)
        self.assertEqual(b.hits['BhBitmapMapLoop'],1024)
        self.assertEqual(b.reads['committed_map'],1024)
        self.assertEqual(b.reads['pending_map'],1024+b.hits['BhBitmapDifferent'])
        writes=[v for v in b.writes if 0x3500<=v[0]<0x36e0]
        self.assertTrue(all(0x3500<=at<0x3598 for at,_,_,_ in writes))
        self.assertEqual(b.blob(0x3598,0x148),bytes([0xA5])*0x148)

    def test_randomized_full_map_differentials(self):
        rng=random.Random(0xC028EFF)
        for case in range(48):
            cm=[rng.randrange(768) for _ in range(1024)]
            pm=cm.copy()
            for at in rng.sample(range(1024),rng.randrange(30,250)):
                h=rng.randrange(1024)
                pm[at]=rng.choice((h,h|0x4000,h|0x8000,0xffff))
            if case%8==0:
                for at in rng.sample(range(1024),20):
                    cm[at]=(rng.randrange(596)|0x4000)
                    pm[at]=cm[at]
            a,b=run_pair(cm,pm)
            self.assertEqual(b.hits['BhBitmapMapLoop'],1024)
            self.assertEqual(b.blob(0x3598,0x148),bytes([0xA5])*0x148)

    def test_live_queue_and_wrong_state_are_rejected_before_bitmap_writes(self):
        cm=[300]*1024;pm=cm.copy()
        for addr,bad in ((0x42D600,0),(0x42D600,3),(0x42D660,1),
                         (0x42D608,2),(0x42D60A,3),(0x42D70C,1)):
            m=load(NEW,cm,pm);m.poke16(addr,bad);before=m.blob(0x3500,480)
            m.run('BhBitmapBuild');self.assertTrue(m.c)
            self.assertEqual(m.blob(0x3500,480),before)
            self.assertEqual(m.reads['committed_map'],0)
            self.assertEqual(m.reads['pending_map'],0)

    def test_result_is_independent_of_initial_dead_queue_bytes(self):
        cm=[i%596 for i in range(1024)];pm=cm.copy()
        m=load(NEW,cm,pm);m.ram[0][0x3500:0x3598]=b'\xff'*152
        m.run('BhBitmapBuild')
        self.assertEqual(result(m),b''.join(membership_reference(cm,pm)))

if __name__=='__main__':unittest.main()
