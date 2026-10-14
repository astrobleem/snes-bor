"""Offline verification for bounded source-transaction map scan and commit.

Includes a tiny A16/I16 interpreter for the *generated assembler statements*;
it is not an electrical 65816/PPU emulator and does not replace Mesen.
"""
import random
import unittest
from rect_map_opt import (MapContractError, ORIGINAL_SCAN, ORIGINAL_COMMIT,
    SCAN_REPLACEMENT, COMMIT_ROUTINE, transform, rect_runs, full_runs,
    rect_commit, apply_word_runs)


def fixture():
    return ['OnlineBlank:','OnlineMapsTransfer:','.a16','.i16',' jsr WarmFlush',
            *ORIGINAL_COMMIT[4:],'OnlineComplete:',
            '.org $D000',*ORIGINAL_SCAN,
            'WarmMapDmaHigh:','WarmMapDmaLow:',
            ' lda $72',' rts',
            '.org $D400','WarmDirectPair:',
            ' rts','.org $E000']


class InlineModel:
    """Execute supported emitted assembly operations in 16-bit accumulator/index mode.

    No frame timing, bus contention or actual DMA. The map DMA subroutines
    are replaced by read-only region-transfer observers against the same data.
    """
    def __init__(self,asm,committed,pending,rect):
        self.p=[s.strip() for s in asm if s.strip() and not s.strip().startswith('.org')]
        self.labels={s[:-1]:i for i,s in enumerate(self.p) if s.endswith(':')}
        self.base=list(committed);self.pending=list(pending)
        self.dp=dict(zip((0x78,0x7a,0x7c,0x7e),rect))
        self.a=0;self.x=0;self.y=0;self.c=0;self.z=0;self.s=[]
        self.packets=[];self.vram=[list(committed),list(committed)]
        self.vram_addr=0
    def get(self,s):
        if s.startswith('#'):return int(s[1:].replace('$','0x'),0)
        if s.endswith(',x'):
            addr=int(s[:-2].replace('$','0x'),0)
            if addr==0x42c000:return self.pending[self.x//2]
            if addr==0x42c800:return self.base[self.x//2]
            raise ValueError(('long index',s))
        if s.startswith('$'):
            return self.dp.get(int(s[1:],16),0)
        raise ValueError(('operand',s))
    def put(self,d,v):
        v&=65535
        if d=='$002116':self.vram_addr=v;return
        self.dp[int(d[1:],16)]=v
    def run(self,start):
        pc=self.labels[start]+1
        for n in range(150000):
            s=self.p[pc];pc+=1
            if s.endswith(':') or s.startswith('.') or s in ('phb','plb'):continue
            op,_,arg=s.partition(' ');arg=arg.strip()
            if op in ('lda','lda.l','ldx','ldy'):
                setattr(self,op[:3][-1],self.get(arg))
            elif op in ('sta','sta.l'):self.put(arg,self.a)
            elif op=='stx':self.put(arg,self.x)
            elif op=='tay':self.y=self.a
            elif op=='tax':self.x=self.a
            elif op=='inx':self.x=(self.x+1)&65535
            elif op=='inc':
                if arg=='a':self.a=(self.a+1)&65535
                else:self.put(arg,self.get(arg)+1)
            elif op=='dec':
                if arg=='a':self.a=(self.a-1)&65535
                else:self.put(arg,self.get(arg)-1)
            elif op=='asl':
                assert arg=='a';self.c=(self.a>>15)&1;self.a=(self.a<<1)&65535
            elif op=='lsr':
                assert arg=='a';self.c=self.a&1;self.a>>=1
            elif op in ('clc','sec'):self.c=int(op=='sec')
            elif op=='adc':
                v=self.a+self.get(arg)+self.c;self.a=v&65535;self.c=int(v>65535)
            elif op=='sbc':
                v=self.a-self.get(arg)-(1-self.c);self.a=v&65535;self.c=int(v>=0)
            elif op in ('cmp','cmp.l','cpx'):
                lhs=self.a if op.startswith('cmp') else self.x;rhs=self.get(arg)
                self.c=int(lhs>=rhs);self.z=int(lhs==rhs)
            elif op=='jmp':pc=self.labels[arg]+1
            elif op in ('bcc','bcs','bne','beq'):
                yes={'bcc':self.c==0,'bcs':self.c==1,'bne':self.z==0,'beq':self.z==1}[op]
                if yes:pc=self.labels[arg]+1
            elif op=='jsr':
                if arg not in ('WarmMapDmaHigh','WarmMapDmaLow'):
                    raise ValueError(('unknown call',arg))
                off=self.get('$72');count=self.get('$74')
                assert count>0 and count%2==0 and off%2==0
                idx=0 if arg.endswith('High') else 1
                assert self.vram_addr==((0x7800 if idx==0 else 0x7c00)+off//2)
                self.packets.append((idx,off,count))
                self.vram[idx][off//2:(off+count)//2]=self.pending[off//2:(off+count)//2]
            elif op=='mvn':
                assert arg=='$42,$42' and self.c in (0,1)
                n=(self.a+1)&65535
                assert n>0 and self.x>=0xc000 and self.y==self.x+0x800
                source=(self.x-0xc000)//2
                size=n//2
                assert n%2==0 and source>=0 and source+size<=1024
                self.base[source:source+size]=self.pending[source:source+size]
                self.a=0xffff;self.x=(self.x+n)&0xffff;self.y=(self.y+n)&0xffff
            elif op=='rts':return n
            else:raise ValueError(('unsupported opcode',s,n))
        raise ValueError('interpreter run limit')


class RectMapTests(unittest.TestCase):
    def test_source_transform_preserves_hot_order_and_originals(self):
        original=fixture();result=transform(original)
        self.assertIn('WarmCommitMapRect:',result)
        self.assertEqual(result.count(' jsr WarmCommitMapRect'),1)
        self.assertLess(result.index('OnlineMapsTransfer:'),result.index('OnlineComplete:'))
        self.assertEqual(result[:result.index('OnlineMapsTransfer:')],original[:original.index('OnlineMapsTransfer:')])
        self.assertEqual(result[result.index('WarmMapDmaHigh:'):],original[original.index('WarmMapDmaHigh:'):])
        self.assertNotIn(' lda #2047',result)
    def test_fail_closed_missing_and_changed_both_contracts(self):
        a=fixture()
        with self.assertRaises(MapContractError):transform(transform(a))
        for old,new in [(' cmp.l $42C800,x',' cmp.l $42C802,x'),
                        (' lda #2047',' lda #2046'),
                        (' jsr WarmFlush',' jsr StageSomething'),
                        ('WarmDirectPair:','OtherDMA:')]:
            mutated=list(a);mutated[mutated.index(old)]=new
            with self.subTest(old=old),self.assertRaises(MapContractError):transform(mutated)
    def test_special_rows_and_boundary_runs(self):
        zeros=[0]*1024
        for rect,edits in [
            ((0,31,0,27),[(0,1),(31,2),(32,3),(895,4)]),
            ((31,31,27,27),[(895,10)]),
            ((0,0,0,0),[(0,11)]),
            ((4,11,7,18),[(7*32+4,13),(18*32+11,14)]),
        ]:
            target=zeros.copy()
            for i,v in edits:target[i]=v
            reference=full_runs(zeros,target)
            result=rect_runs(zeros,target,rect)
            self.assertEqual(apply_word_runs(zeros,target,result),target)
            self.assertEqual(apply_word_runs(zeros,target,reference),target)
            self.assertEqual(rect_commit(zeros,target,rect),target)
    def test_preserves_explicit_negative_capability(self):
        with self.assertRaises(ValueError):rect_runs([0]*1024,[0]*1024,(0,32,0,27))
        with self.assertRaises(ValueError):rect_runs([0]*1024,[0]*1024,(0,31,-1,27))
        with self.assertRaises(ValueError):rect_runs([0]*1024,[0]*1024,(2,1,0,1))
    def test_assembled_statement_interpreter_against_full_scan_and_commit(self):
        rng=random.Random(0xF548981D)
        cases=325
        for case in range(cases):
            if case%7==0:rect=(0,31,0,27)
            elif case%7==1:rect=(31,31,27,27)
            elif case%7==2:rect=(0,0,0,0)
            else:
                x0=rng.randrange(0,32);x1=rng.randrange(x0,32)
                y0=rng.randrange(0,28);y1=rng.randrange(y0,28)
                rect=(x0,x1,y0,y1)
            base=[rng.randrange(768) for _ in range(1024)]
            pending=base.copy()
            x0,x1,y0,y1=rect
            for y in range(y0,y1+1):
                for x in range(x0,x1+1):
                    if rng.random()<0.29:
                        pending[y*32+x]=rng.randrange(768)
            model=InlineModel(SCAN_REPLACEMENT+COMMIT_ROUTINE,base,pending,rect)
            model.run('WarmSparseMaps')
            self.assertEqual(model.vram[0],pending)
            self.assertEqual(model.vram[1],pending)
            expected=rect_runs(base,pending,rect)
            self.assertEqual([(i,o,n) for i in (0,1) for o,n in expected],
                             sorted(model.packets,key=lambda x:(x[0],x[1])))
            # Native commit invokes only after all map & CHR DMAs have finished.
            self.assertEqual(model.base,base)
            model.run('WarmCommitMapRect')
            self.assertEqual(model.base,pending)
            self.assertEqual(len(model.base),1024)
    def test_sparse_scan_excludes_dirty_data_outside_union_by_contract(self):
        base=[0]*1024;pending=base.copy();rect=(7,19,10,20)
        pending[0]=1
        self.assertEqual(rect_runs(base,pending,rect),[])
        self.assertNotEqual(full_runs(base,pending),[])
        self.assertNotEqual(rect_commit(base,pending,rect),pending)
        # This is why the existing full COMMITTED->MAP initialization and
        # union-only mutation path MUST remain unchanged.
    def test_epoch_17_worklist_size(self):
        # A 345-cell union was observed in the 18-epoch native profiling run.
        # Actual bounds are read from Sol's retained native observation;
        # this verifies the maximal potential scan win without inventing bounds.
        old_scan=1024;union=345
        self.assertEqual(old_scan-union,679)
        self.assertLess(union/old_scan,0.34)


if __name__=='__main__':unittest.main()

class PatchSizingTests(unittest.TestCase):
    def test_65816_candidate_size_and_short_branch_displacements(self):
        from size_audit import report,sizes
        r=report()
        self.assertEqual(r['old_scan_bytes'],91)
        self.assertLess(r['estimated_map_dma_entry_from_d1cc'],r['hard_next_org']-64)
        # Label-to-instruction byte-offsets in the proposed routines.
        lines=SCAN_REPLACEMENT+COMMIT_ROUTINE
        addr=0;labels={};branches=[]
        for line in lines:
            if line.endswith(':'):labels[line[:-1]]=addr
            else:
                n=sizes([line]);op,_,arg=line.strip().partition(' ')
                if op in ('bcc','bcs','bne','beq','bpl','bmi'):branches.append((op,arg,addr))
                addr+=n
        for op,dst,at in branches:
            self.assertIn(dst,labels)
            off=labels[dst]-(at+2)
            self.assertTrue(-128<=off<=127,(op,dst,off))


class RetainedEmitterTests(unittest.TestCase):
    def test_decimal_operand_spelling(self):
        decimal=[s.replace('$42C000,x','4374528,x').replace('$42C800,x','4376576,x') for s in fixture()]
        self.assertEqual(transform(decimal),transform(fixture()))
    def test_decimal_operand_drift_rejected(self):
        drift=[s.replace('$42C000,x','4374529,x') for s in fixture()]
        with self.assertRaises(MapContractError):transform(drift)
