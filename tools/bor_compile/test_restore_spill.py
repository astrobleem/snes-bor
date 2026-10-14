"""Offline tests of emitted source splice and record indexing, not native Poppy/Mesen."""
import unittest
import re
from restore_spill import (transform, record_address, RestoreSpillContractError,
    NEW_CAPACITY, IRAM_BASE, SPILL_BASE, SPILL_END, QUEUE_BASE, QUEUE_END, META_BASE)


def source_fixture():
    # Exact contiguous record access excerpts from b40172b batch-emitted source,
    # with labels and remaining calls needed to ensure fail-closed contracts.
    return ['.org $A000','NbBeginRetry:',
        'NbRestorePlan:','.a16','.i16',' lda.l $42D606',' cmp #32',
        ' jsr NbFree',' lda.l $42D606',' asl a',' asl a',' tax',
        ' lda $30',' sta.l $003480,x',' lda $2C',' sta.l $003482,x',
        ' lda.l $42D606',' inc a',' sta.l $42D606',
        'NbActorPlanStart:','.a16','.i16',
        'NbRestoreProduce:','.a16','.i16',
        ' lda $60',' cmp.l $42D606',' bcs NbActorProduceStart',
        ' asl a',' asl a',' tax',
        ' lda.l $003482,x',' sta $64',' lda.l $003480,x',' sta $2C',
        ' jsr WarmCopyBackdrop',
        'NbActorProduceStart:','.a16','.i16',' jsr NbPreloadPair',
        'NbFree:','.a16','.i16',' rts',
        'NbFlushQueue:','.a16','.i16',
        ' jsr NbFlushQueue', ' jsr NbFlushQueue', ' jsr NbFlushQueue',
        'NbCodeEnd:','.org $C000']


def program_region(code, start, end):
    a=code.index(start)+1; b=code.index(end,a)
    return code[a:b]


def run_65816_subset(code, memory, *, a=0, x=0, dp=None):
    """Execute exactly the restore path instructions, in A16/I16 semantics.

    This is an instruction-semantic sanity check, NOT a timing/accuracy model of
    the complete CPU. It fails closed on any unhandled instruction.
    """
    dp=dp if dp is not None else {}
    labels={v[:-1]:i for i,v in enumerate(code) if v.endswith(':')}
    pc=0; carry=False; steps=0
    def operand_address(op):
        m=re.fullmatch(r'\$([0-9A-Fa-f]{2,6})(,x)?',op)
        if not m:raise AssertionError(f'operand {op}')
        addr=int(m.group(1),16)
        if m.group(2):addr+=x
        return addr
    while pc<len(code):
        steps+=1
        if steps>120:raise AssertionError('interpreter loop')
        raw=code[pc].strip();pc+=1
        if not raw or raw.startswith('.') or raw.endswith(':'):continue
        op,_,arg=raw.partition(' ')
        if op=='jsr':
            if arg not in ('NbFree','WarmCopyBackdrop'):raise AssertionError(raw)
            if arg=='WarmCopyBackdrop':break
        elif op=='lda':
            if arg.startswith('#'):a=int(arg[1:])
            elif arg.startswith('$'):
                ad=operand_address(arg)
                a=dp.get(ad,0) if ad<0x100 else memory.get(ad,0)
            else:raise AssertionError(raw)
            a&=65535
        elif op=='sta' or op=='sta.l':
            ad=operand_address(arg)
            if ad<0x100:dp[ad]=a&65535
            else:memory[ad]=a&65535
        elif op=='lda.l':a=memory.get(operand_address(arg),0)&65535
        elif op=='asl':
            if arg!='a':raise AssertionError(raw)
            carry=bool(a&0x8000);a=(a*2)&65535
        elif op=='tax':x=a
        elif op=='txa':a=x
        elif op=='cpx':carry=x>=int(arg[1:])
        elif op=='sec':carry=True
        elif op=='sbc':
            val=int(arg[1:]);a=(a-val-(0 if carry else 1))&65535
        elif op=='bcs':
            if carry:pc=labels[arg]
        elif op=='bra':pc=labels[arg]
        else:raise AssertionError(f'Unhandled instruction {raw}')
    return dict(a=a,x=x,dp=dp,memory=memory,steps=steps)


class SourceContract(unittest.TestCase):
    def test_known_generated_form_splices_without_touching_control(self):
        original=source_fixture();after=transform(original)
        self.assertEqual(original,source_fixture())
        self.assertEqual(after.count(' cmp #48'),1)
        self.assertIn('NbRestoreStoreOverflow:',after)
        self.assertIn('NbRestoreLoadOverflow:',after)
        self.assertEqual(after.count(' jsr NbFlushQueue'),3)
        self.assertEqual(after.count('NbCodeEnd:'),1)
        self.assertEqual(after.count('NbActorProduceStart:'),1)
        self.assertEqual(after.count(' sta.l $42D620,x'),1)
        self.assertEqual(after.count(' lda.l $42D620,x'),1)
    def test_undefined_or_duplicate_label_fails(self):
        a=source_fixture();a.remove('NbBeginRetry:')
        with self.assertRaisesRegex(RestoreSpillContractError,'LABEL_DRIFT'):transform(a)
        a=source_fixture();a.insert(2,'NbRestoreStoreOverflow:')
        with self.assertRaisesRegex(RestoreSpillContractError,'DUPLICATE_SPILL'):transform(a)
    def test_existing_claim_in_spill_fails(self):
        a=source_fixture();a.insert(a.index('NbCodeEnd:'),' sta.l $42D620,x')
        with self.assertRaisesRegex(RestoreSpillContractError,'SCRATCH_SPILL_ALREADY_CLAIMED'):transform(a)
    def test_unknown_emitter_revision_fails(self):
        a=source_fixture();a[a.index(' sta.l $003480,x')]=' sta.l $003484,x'
        with self.assertRaisesRegex(RestoreSpillContractError,'RECORD_STORE'):transform(a)
        a=source_fixture();a[a.index(' cmp #32')]=' cmp #34'
        with self.assertRaisesRegex(RestoreSpillContractError,'RECORD_COUNT_GUARD'):transform(a)
    def test_memory_bounds_and_independent_queue(self):
        self.assertEqual(NEW_CAPACITY,48)
        self.assertEqual(record_address(0),0x3480)
        self.assertEqual(record_address(31),0x34fc)
        self.assertEqual(record_address(32),0x42d620)
        self.assertEqual(record_address(33),0x42d624)
        self.assertEqual(record_address(47),0x42d65c)
        self.assertEqual(SPILL_END,META_BASE)
        self.assertEqual(QUEUE_BASE,0x3500)
        self.assertEqual(QUEUE_END,0x36e0)
        for i in (-1,48,65536):
            with self.assertRaises(ValueError):record_address(i)
    def test_all_48_record_write_and_load_native_semantics(self):
        a=transform(source_fixture())
        store=program_region(a,'NbRestorePlan:','NbActorPlanStart:')
        load=program_region(a,'NbRestoreProduce:','NbActorProduceStart:')
        # Store starts with the first 'jsr NbFree' after the count guard.
        store=store[store.index(' jsr NbFree'):store.index('NbRestoreStoreDone:')+1]
        load=load[load.index(' asl a'):load.index(' jsr WarmCopyBackdrop')+1]
        mem={addr:0xCACA for addr in range(0x3500,0x36e0,2)}
        mem.update({addr:0xBABA for addr in range(0x42d660,0x42d67e,2)})
        for i in range(48):
            mem[0x42d606]=i
            home=i*9+7;slot=767-i
            run_65816_subset(store,mem,dp={0x30:home,0x2c:slot})
        for i in range(48):
            loaded=run_65816_subset(load,mem,a=i,dp={})
            self.assertEqual(loaded['dp'][0x2c],i*9+7,(i,'home'))
            self.assertEqual(loaded['dp'][0x64],767-i,(i,'slot'))
        self.assertTrue(all(mem[addr]==0xCACA for addr in range(0x3500,0x36e0,2)))
        self.assertTrue(all(mem[addr]==0xBABA for addr in range(0x42d660,0x42d67e,2)))
    def test_relative_branch_ranges_remain_short(self):
        a=transform(source_fixture())
        sizes={'cpx':3,'cmp':2,'cmp.l':4,'bcs':2,'bra':2,'lda':2,'lda.l':4,
               'sta':2,'sta.l':4,'tax':1,'txa':1,'sec':1,'sbc':3,'asl':1,
               'jsr':3,'inc':1}
        for start,end in [('NbRestorePlan:','NbActorPlanStart:'),
                          ('NbRestoreProduce:','NbActorProduceStart:')]:
            code=program_region(a,start,end)
            offsets=[];labels={};pc=0
            for line in code:
                op,_,arg=line.strip().partition(' ')
                offsets.append(pc)
                if op.endswith(':'):labels[op[:-1]]=pc;continue
                if not op or op.startswith('.'):continue
                pc+=(3 if op in ('lda','cmp') and arg.startswith('#') else sizes[op])
            for index,line in enumerate(code):
                op,_,arg=line.strip().partition(' ')
                if op in ('bcs','bra') and arg.startswith('NbRestore'):
                    delta=labels[arg]-(offsets[index]+2)
                    self.assertTrue(-128<=delta<=127,(start,line,delta))
    def test_failed_transaction_does_not_touch_queue_or_map(self):
        # Repeated planning overwrites records but never affects the queue;
        # an abort before preloading cannot change physical VRAM/committed map.
        a=transform(source_fixture());store=program_region(a,'NbRestorePlan:','NbActorPlanStart:')
        store=store[store.index(' jsr NbFree'):store.index('NbRestoreStoreDone:')+1]
        mem={0x42d660:0,0x42d662:99,0x42c800:0xABCD}
        for attempt in range(3):
            for i in range(34):
                mem[0x42d606]=i
                run_65816_subset(store,mem,dp={0x30:100+attempt,0x2c:700-i})
            self.assertEqual(mem[0x42d660],0)
            self.assertEqual(mem[0x42d662],99)
            self.assertEqual(mem[0x42c800],0xABCD)

if __name__=='__main__':unittest.main()
