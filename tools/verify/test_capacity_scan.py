"""Differential instruction traces against the unchanged conservative probe."""
import random
import unittest

import capacity_scan as candidate
from early_capacity import reference
from test_early_capacity import ProbeVM


class ScanVM(ProbeVM):
    def __init__(self, words, refs, *, y=0, bank=0):
        super().__init__(words, refs)
        self.op=[];self.labels={};self.Y=y;self.bank=bank;self.stack=[]
        for line in candidate.routine():
            line=line.strip()
            if not line or line.startswith('.'):continue
            if line.endswith(':'):self.labels[line[:-1]]=len(self.op)
            else:self.op.append(line)

    def mem(self, expr):
        if expr.endswith(',y'):
            address=(self.bank<<16)+self.num(expr[:-2])+self.Y
            if 0x42c000<=address<0x42c800:
                return self.map[(address-0x42c000)//2]
            raise AssertionError(hex(address))
        if expr.startswith('$D000'):
            assert self.bank==0x42
            expr=expr.replace('$D000','$42D000')
        return super().mem(expr)

    def run(self):
        pc=self.labels['CsPredict']
        for steps in range(150000):
            self.steps=steps+1
            op=self.op[pc];cmd,_,arg=op.partition(' ');cmd=cmd.removesuffix('.l')
            nextpc=pc+1
            if cmd=='phb':self.stack.append(self.bank)
            elif cmd=='phy':self.stack.extend([self.Y>>8,self.Y&255])
            elif cmd=='pea':
                n=self.num(arg);self.stack.extend([n>>8,n&255])
            elif cmd=='plb':self.bank=self.flag(self.stack.pop())
            elif cmd=='ply':self.Y=self.flag(self.stack.pop()+(self.stack.pop()<<8))
            elif cmd=='lda':self.A=self.flag(self.val(arg))
            elif cmd=='ldx':self.X=self.flag(self.val(arg))
            elif cmd=='ldy':self.Y=self.flag(self.val(arg))
            elif cmd=='sta':self.setmem(arg,self.A)
            elif cmd=='inc':self.setmem(arg,self.flag(self.mem(arg)+1))
            elif cmd=='inx':self.X=self.flag(self.X+1)
            elif cmd=='iny':self.Y=self.flag(self.Y+1)
            elif cmd=='dey':self.Y=self.flag(self.Y-1)
            elif cmd=='tax':self.X=self.flag(self.A)
            elif cmd=='tay':self.Y=self.flag(self.A)
            elif cmd=='asl':
                if arg=='a':
                    self.C=bool(self.A&0x8000);self.A=self.flag(self.A<<1)
                else:
                    value=self.mem(arg);self.C=bool(value&0x8000)
                    self.setmem(arg,self.flag(value<<1))
            elif cmd=='lsr':
                assert arg=='a';self.C=bool(self.A&1);self.A=self.flag(self.A>>1)
            elif cmd=='and':self.A=self.flag(self.A&self.val(arg))
            elif cmd=='ora':self.A=self.flag(self.A|self.val(arg))
            elif cmd=='clc':self.C=False
            elif cmd=='sec':self.C=True
            elif cmd=='adc':
                value=self.A+self.val(arg)+int(self.C);self.C=value>65535
                self.A=self.flag(value)
            elif cmd in ('cmp','cpx','cpy'):
                lhs=dict(cmp=self.A,cpx=self.X,cpy=self.Y)[cmd]
                rhs=self.val(arg);self.C=lhs>=rhs;self.flag(lhs-rhs)
            elif cmd in ('beq','bne','bcc','bcs'):
                cond=dict(beq=self.Z,bne=not self.Z,bcc=not self.C,bcs=self.C)[cmd]
                if cond:nextpc=self.labels[arg]
            elif cmd in ('jmp','bra'):nextpc=self.labels[arg]
            elif cmd=='rts':
                assert not self.stack
                return self.C
            else:raise AssertionError('UNSUPPORTED '+op)
            pc=nextpc
        raise AssertionError('CAPACITY_SCAN_LOOP')


class CapacityScanTests(unittest.TestCase):
    def compare(self, words, refs, *, y=0, bank=0):
        old=ProbeVM(words,refs);old.Y=y
        new=ScanVM(words,refs,y=y,bank=bank)
        expected=reference(words,refs)
        self.assertEqual(old.run(),not expected['conservative_fits'])
        self.assertEqual(new.run(),old.C)
        self.assertEqual((new.A,new.X,new.Y,new.C,new.Z),
                         (old.A,old.X,old.Y,old.C,old.Z))
        self.assertEqual(new.dp,old.dp)
        self.assertEqual(new.records,old.records)
        self.assertEqual(new.writes,old.writes)
        self.assertEqual(new.bank,bank)
        self.assertEqual(new.map,words);self.assertEqual(new.refs,refs)
        return old,new

    def test_capacity_boundaries_and_context(self):
        for actors in (0,1,171,172,173,1024):
            for free in (0,1,171,172):
                words=[0xffff]*actors+[0]*(1024-actors)
                refs=[1]*596+[0]*free+[1]*(172-free)
                for y,bank in ((0,0),(0xabcd,0x7e),(0xffff,0x42)):
                    with self.subTest(actors=actors,free=free,y=y,bank=bank):
                        self.compare(words,refs,y=y,bank=bank)

    def test_all_bitmap_bits_tags_duplicate_and_record_boundaries(self):
        for count in (1,15,16,17,48,49,596):
            words=list(range(count))+[0]*(1024-count)
            refs=[0x8000]*count+[1]*(596-count)+[0]*172
            self.compare(words,refs,y=0xface,bank=0xf4)
        words=[0xffff,596,767,768,0x3fff,0x4000,0x8000,0xfffe]*128
        self.compare(words,[0xffff]*768,y=0xface,bank=0x21)

    def test_random_maps_and_inconsistent_flags(self):
        rng=random.Random(0x4086)
        for trial in range(40):
            words=[rng.choice((0,0xffff,rng.randrange(768),rng.randrange(65536)))
                   for _ in range(1024)]
            refs=[rng.choice((0,1,0x4000,0x8000,0xc000,rng.randrange(65536)))
                  for _ in range(768)]
            self.compare(words,refs,y=rng.randrange(65536),bank=rng.randrange(256))

    def test_source_transform_preserves_disabled_and_old_bytes_count(self):
        source=['NbCapacityPredict:','.a16','.i16',' lda #0',' ldx #0',
                'NbCapacityClear:',' sta.l $003480,x',' rts']
        self.assertEqual(candidate.transform(source,False),source)
        changed=candidate.transform(source)
        self.assertEqual(changed[:7],source[:3]+[' jmp CsPredict',' nop',' nop',' nop'])
        self.assertEqual(changed[7:10],source[5:])
        with self.assertRaisesRegex(ValueError,'ALREADY'):
            candidate.transform(changed)
        with self.assertRaisesRegex(ValueError,'PINNED'):
            candidate.transform(source[1:])


if __name__=='__main__':unittest.main()
