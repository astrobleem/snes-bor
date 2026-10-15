"""Offline differential tests. Synthetic maps are NOT native captured evidence."""
from __future__ import annotations
import hashlib
import json
import random
import runpy
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/bor_compile'))
from home_borrow_bitmap import (transform,membership_reference,BitmapContractError,
    BITMAP_BYTES,COMMITTED_BITS,PENDING_BITS,BITMAP_END)
from home_borrow_bitmap_vm import assemble,Machine
REF=runpy.run_path(str(ROOT/'reference/home_borrow_836e8a9.py'))
OLD_LINES=REF['_code']()
SOURCE=['.org $B300',*OLD_LINES,'.org $C000']
NEW_LINES=transform(SOURCE)[1:-1]
OLD=assemble(OLD_LINES);NEW=assemble(NEW_LINES)
INVALID=[297,298,299,327,328,329,356,357,358,359,360,361,387,388,389,
    390,391,392,393,417,418,419,420,421,422,423,512,513,514,524,525,526,
    529,530,544,545,550,552,574,575,576,584]
VALID=[204,232,233,234,264,265,266,268,269,295,296,300,325,326,330,331,355,362,528,549]


def synthetic_inventory_fixture():
    """Reproduce reported candidate inventory using SYNTHETIC coherent maps.
    This is not the user's captured 1024-cell map or native timing workload.
    """
    absent=set(INVALID+VALID)
    occupied=[h for h in range(596) if h not in absent]+list(range(660,768))
    cm=(occupied*2)[:1024]
    refs=[Counter(cm)[h] | (0x8000 if h in INVALID else 0) for h in range(768)]
    backgrounds=[h for h in range(596) if h not in absent]
    pm=(backgrounds*2)[:1024]
    for i in range(10):pm[i]=0x4000+(596+i) # already planned restoration tails
    pm[-95:]=[0xFFFF]*95
    return cm,pm,refs,606


def setup(program,cm,pm,refs,tail_cursor=606,**controls):
    m=Machine(program)
    m.ram[0][0x3480:0x36e0]=bytes([0xA5])*608
    m.load_words(0x42C800,cm);m.load_words(0x42C000,pm);m.load_words(0x42D000,refs)
    m.run('BhInitialize');m.run('BhBegin')
    m.poke16(0x42D600,1);m.poke16(0x42D674,1);m.poke16(0x342E,tail_cursor)
    for addr,key,default in ((0x42D702,'policy',0),(0x42D70A,'budget',64),
                             (0x42D70E,'quota',64),(0x42D674,'exact',1)):
        m.poke16(addr,controls.get(key,default))
    m.steps=0;m.reads.clear();m.writes.clear();m.hits.clear()
    return m


def outcome(m):
    n=m.peek16(0x42D700)
    return (m.c,m.peek16(0x42D706),m.peek16(0x42D70C),
            tuple(m.peek16(0x42D710+2*i) for i in range(n)))


def eligible_reference(home,refs,committed,pending):
    if refs[home]&0x3FFF:return False,0
    if refs[home]&0x4000 or home in committed:return True,None
    return False,int(all((w&0x3FFF)!=home for w in pending))


class BitmapPatchTests(unittest.TestCase):
    def test_pinned_reference_git_blob(self):
        b=(ROOT/'reference/home_borrow_836e8a9.py').read_bytes()
        self.assertEqual(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),
                         '0c79a1a6706d1e7a88d819461cbbd798fdd74bff')

    def test_original_binary_size_matches_pinned_native_report(self):
        self.assertEqual(len(OLD.data),825)
        self.assertEqual(OLD.symbols['BhCodeEnd'],0x39B639)
        self.assertEqual(len(NEW.data),1014)
        self.assertLess(NEW.symbols['BhCodeEnd'],0x39C000)

    def test_source_drift_and_double_application_rejected(self):
        with self.assertRaises(BitmapContractError):transform(transform(SOURCE))
        for before,after in [(' cmp #65',' cmp #64'),(' and #$3FFF',' and #$7FFF'),
                             (' jsr BhEligible',' jsr BhTake')]:
            changed=SOURCE.copy();changed[changed.index(before)]=after
            with self.assertRaises(BitmapContractError):transform(changed)

    def test_unrelated_helper_source_unchanged(self):
        def block(lines,lo,hi):return lines[lines.index(lo):lines.index(hi)]
        self.assertEqual(block(OLD_LINES,'BhInitialize:','BhPrepare:'),
                         block(NEW_LINES,'BhInitialize:','BhPrepare:'))
        self.assertEqual(block(OLD_LINES,'BhClass:','BhEligible:'),
                         block(NEW_LINES,'BhClass:','BhEligible:'))
        # The complete allocator, invalidation, fault, READY, rollback and
        # commit routines remain byte-for-byte SOURCE-identical.
        self.assertEqual(block(OLD_LINES,'BhTake:','BhCodeEnd:'),
                         block(NEW_LINES,'BhTake:','BhBitmapBuild:'))

    def test_all_home_bits_and_tag_semantics(self):
        for tag in (0,0x4000,0x8000,0xC000):
            cm=[tag+h for h in range(596)]+[0xFFFF]*428
            pm=cm.copy();refs=[0]*768
            m=setup(NEW,cm,pm,refs);m.run('BhBitmapBuild')
            self.assertFalse(m.c)
            first,second=membership_reference(cm,pm)
            self.assertEqual(m.blob(COMMITTED_BITS,BITMAP_BYTES),first)
            self.assertEqual(m.blob(PENDING_BITS,BITMAP_BYTES),second)
            self.assertEqual(m.reads['pending_map'],1024)
            self.assertEqual(m.reads['committed_map'],1024)
            self.assertEqual(first,bytes(76) if tag else second)
            self.assertEqual(second[-2:],b'\x0f\x00') # 596 live bits, 12 padding bits

    def test_guard_precedence_and_boundary_homes_machine_bytes(self):
        homes=(0,1,7,8,15,16,31,32,255,256,583,584,594,595)
        for home in homes:
            for count,flags,committed_use,pending_use in (
                (0,0,False,False),(0,0x8000,False,False),(1,0,False,False),
                (1,0x4000,True,True),(0,0x4000,False,False),
                (0,0,True,False),(0,0,False,True)):
                cm=[767]*1024;pm=[0xFFFF]*1024;refs=[0]*768
                if committed_use:cm[1023]=home
                if pending_use:pm[1023]=0xC000|home
                refs[home]=count|flags
                a=setup(OLD,cm,pm,refs);b=setup(NEW,cm,pm,refs)
                b.run('BhBitmapBuild')
                for m in (a,b):m.poke16(0x3476,home);m.run('BhEligible')
                self.assertEqual(a.c,b.c)
                if not a.c:self.assertEqual(a.a,b.a)
                self.assertEqual(b.y,0xBEEF)

    def test_out_of_domain_map_words_never_set_home_bits(self):
        cm=[596,767,768,0x3FFF,0xFFFF,0x4000,0x8000,0xC000]*128
        pm=cm.copy();m=setup(NEW,cm,pm,[0]*768);m.run('BhBitmapBuild')
        cb,pb=membership_reference(cm,pm)
        self.assertEqual(m.blob(COMMITTED_BITS,76),cb)
        self.assertEqual(m.blob(PENDING_BITS,76),pb)
        self.assertEqual(cb,bytes(76))
        self.assertEqual(pb,b'\x01'+bytes(75))

    def test_randomized_bitmap_membership_and_eligibility(self):
        rng=random.Random(0x836E8A9)
        for case in range(24):
            pool=rng.sample(range(768),rng.randrange(30,160))
            cm=[rng.choice(pool) for _ in range(1024)]
            pm=[rng.choice(pool)|(rng.randrange(4)<<14) for _ in range(1024)]
            for i in rng.sample(range(1024),100):pm[i]=0xFFFF
            refs=[rng.choice((0,0,0x8000,1,0x8001,0x4000,0xC001)) for _ in range(768)]
            m=setup(NEW,cm,pm,refs);m.run('BhBitmapBuild')
            self.assertEqual(m.blob(COMMITTED_BITS,76)+m.blob(PENDING_BITS,76),
                             b''.join(membership_reference(cm,pm)))
            reads_before=m.reads.copy()
            for home in range(596):
                m.poke16(0x3476,home);m.run('BhEligible')
                carry,answer=eligible_reference(home,refs,cm,pm)
                self.assertEqual(m.c,carry,(case,home))
                if not carry:self.assertEqual(m.a,answer,(case,home))
            self.assertEqual(m.reads['pending_map'],reads_before['pending_map'])
            self.assertEqual(m.reads['committed_map'],reads_before['committed_map'])

    def test_reported_inventory_synthetic_fixture_same_41_choices(self):
        data=synthetic_inventory_fixture();a=setup(OLD,*data);b=setup(NEW,*data)
        a.run('BhPrepare');b.run('BhPrepare')
        self.assertEqual(outcome(a),outcome(b))
        self.assertEqual([x&0x3FFF for x in outcome(b)[3]],INVALID[:41])
        self.assertEqual(b.reads['pending_map'],2048) # marker count + ONE bitmap scan
        self.assertEqual(b.reads['committed_map'],1024)
        self.assertEqual(b.hits['BhBitmapBuild'],1)
        self.assertLess(b.steps,a.steps//4)

    def test_valid_first_quota_policy_unchanged(self):
        data=synthetic_inventory_fixture()
        for quota in (1,2,20,64):
            a=setup(OLD,*data,policy=1,quota=quota)
            b=setup(NEW,*data,policy=1,quota=quota)
            a.run('BhPrepare');b.run('BhPrepare')
            self.assertEqual(outcome(a),outcome(b))
            self.assertEqual(outcome(b)[3][0],204)

    def test_insufficient_budget_and_max_overflow_unchanged(self):
        data=synthetic_inventory_fixture()
        for budget in (0,1,40,41,64):
            a=setup(OLD,*data,budget=budget);b=setup(NEW,*data,budget=budget)
            a.run('BhPrepare');b.run('BhPrepare')
            self.assertEqual(outcome(a),outcome(b))
            self.assertEqual(b.c,budget<41)
        for need in (64,65,100):
            cm,pm,refs,cursor=synthetic_inventory_fixture()
            pm[-(54+need):]=[65535]*(54+need)
            a=setup(OLD,cm,pm,refs,cursor);b=setup(NEW,cm,pm,refs,cursor)
            a.run('BhPrepare');b.run('BhPrepare')
            self.assertEqual(outcome(a),outcome(b));self.assertTrue(b.c)
            if need>64:self.assertEqual(b.hits['BhBitmapBuild'],0)

    def test_tails_sufficient_and_conservative_paths_execute_no_new_work(self):
        cm,pm,refs,cursor=synthetic_inventory_fixture()
        for exact,markers in ((0,95),(1,0),(1,54)):
            pending=[0]*1024
            if markers:pending[-markers:]=[65535]*markers
            a=setup(OLD,cm,pending,refs,cursor,exact=exact)
            b=setup(NEW,cm,pending,refs,cursor,exact=exact)
            a.run('BhPrepare');b.run('BhPrepare')
            self.assertEqual(outcome(a),outcome(b))
            self.assertEqual(a.steps,b.steps)
            self.assertEqual(a.reads,b.reads)
            self.assertEqual(b.hits['BhBitmapBuild'],0)
            self.assertEqual(b.blob(0x3500,480),bytes([0xA5])*480)

    def test_bitmap_builder_rejects_every_live_queue_or_wrong_state(self):
        data=synthetic_inventory_fixture()
        for addr,bad in ((0x42D600,0),(0x42D600,2),(0x42D600,3),
                         (0x42D660,1),(0x42D608,1),(0x42D60A,3),(0x42D70C,1)):
            m=setup(NEW,*data);m.poke16(addr,bad)
            before=m.blob(0x3480,608);m.run('BhBitmapBuild')
            self.assertTrue(m.c);self.assertEqual(m.blob(0x3480,608),before)
            self.assertEqual(m.reads['pending_map'],0)
            self.assertEqual(m.reads['committed_map'],0)

    def test_temporary_write_bounds_and_guarded_memory_unchanged(self):
        m=setup(NEW,*synthetic_inventory_fixture())
        bwram=m.blob(0x42C000,0x1600)
        m.run('BhPrepare')
        self.assertEqual(m.blob(0x42C000,0x1600),bwram)
        self.assertEqual(m.blob(0x3480,128),bytes([0xA5])*128)
        self.assertEqual(m.blob(BITMAP_END,0x36E0-BITMAP_END),bytes([0xA5])*(0x36E0-BITMAP_END))
        allowed_dp={0x3470,0x3472,0x3474,0x3476,0x3478,0x347A,0x347C,0x347E}
        for addr,val,size,pc in m.writes:
            allowed=(addr in allowed_dp or COMMITTED_BITS<=addr<BITMAP_END or
                     0x42D700<=addr<0x42D790 or 0x100<=addr<0x200)
            self.assertTrue(allowed,hex(addr))
        self.assertEqual((m.y,m.d,m.dbr,m.sp),(0xBEEF,0x3400,0,0x1FF))

    def test_rebuild_after_queue_overwrite_and_changed_maps(self):
        cm,pm,refs,cursor=synthetic_inventory_fixture()
        m=setup(NEW,cm,pm,refs,cursor);m.run('BhPrepare')
        m.ram[0][0x3500:0x36E0]=bytes([0x7E])*480 # subsequent queue lifetime
        m.run('BhBegin')
        cm=[767]*1024;pm=[65535]*1024
        m.load_words(0x42C800,cm);m.load_words(0x42C000,pm)
        m.run('BhBitmapBuild')
        self.assertEqual(m.blob(COMMITTED_BITS,152),bytes(152))
        self.assertEqual(m.blob(BITMAP_END,0x36E0-BITMAP_END),bytes([0x7E])*(0x36E0-BITMAP_END))

    def test_partial_pool_then_reentry_drops_old_journal(self):
        data=synthetic_inventory_fixture();a=setup(OLD,*data,budget=40);b=setup(NEW,*data,budget=40)
        for m in (a,b):
            m.run('BhPrepare');self.assertTrue(m.c)
            m.run('BhBegin');m.poke16(0x42D70A,64);m.run('BhPrepare')
        self.assertEqual(outcome(a),outcome(b));self.assertFalse(b.c)

    def test_only_modeled_semantics_no_cycle_claim(self):
        # The executable runner deliberately offers no cycles/masterClock field.
        m=Machine(NEW)
        self.assertFalse(hasattr(m,'cycles'))
        self.assertFalse(hasattr(m,'masterClock'))


def performance_example():
    data=synthetic_inventory_fixture();result={}
    for name,p in (('old',OLD),('bitmap',NEW)):
        m=setup(p,*data);m.run('BhPrepare')
        result[name]={'executed_instructions':m.steps,'data_word_reads':dict(m.reads),
                      'selected_homes':[x&0x3FFF for x in outcome(m)[3]],
                      'carry_rejection':m.c,'helper_bytes':len(p.data),
                      'helper_end':f'{p.symbols["BhCodeEnd"]:06X}'}
    return {'scope':'SYNTHETIC coherent maps matching the reported inventory; NOT native timing',
            'cases':result,'extra_rom_bytes':len(NEW.data)-len(OLD.data),
            'temporary_queue_bytes':152,'persistent_ram_bytes_added':0}

if __name__=='__main__':
    unittest.main()
