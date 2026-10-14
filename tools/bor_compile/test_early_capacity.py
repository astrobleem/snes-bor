"""Self-contained tests of the emitted 16-bit 65816 conservative-footprint probe.

The little interpreter implements only the opcodes used by NbCapacityPredict.
No SNES bus/interrupt/DMA modeling; native Mesen is still required.
"""
import random
import unittest
from early_capacity import (_predictor,transform,reference,EarlyCapacityContractError,
                            FIRST_TAIL_SLOT,RESTORE_RECORD_CAPACITY)

class ProbeVM:
    def __init__(self,words,refs,record_seed=b''):
        self.map=words;self.refs=refs
        self.records=bytearray((record_seed or bytes([0xA5])*128))
        assert len(self.records)==128
        self.dp={};self.A=0;self.X=0;self.Y=0;self.C=False;self.Z=False
        self.writes=[];self.steps=0
        asm=_predictor()
        self.op=[];self.labels={}
        for line in asm:
            t=line.strip()
            if not t or t.startswith('.') or t.startswith(';'):continue
            if t.endswith(':'):
                self.labels[t[:-1]]=len(self.op)
            else:self.op.append(t)

    def num(self,s):
        s=s.strip().lstrip('#')
        return int(s[1:],16) if s.startswith('$') else int(s)
    def mem(self,expr):
        name=expr.strip();indexed=name.endswith(',x')
        if indexed:name=name[:-2]
        address=self.num(name)
        if address<256:
            if indexed:raise NotImplementedError(expr)
            return self.dp.get(address,0)
        address+=self.X if indexed else 0
        if 0x3480<=address<0x3500:
            i=address-0x3480
            return self.records[i] | (self.records[i+1]<<8)
        if 0x42c000<=address<0x42c800:
            return self.map[(address-0x42c000)//2]
        if 0x42d000<=address<0x42d600:
            return self.refs[(address-0x42d000)//2]
        raise AssertionError(hex(address))
    def setmem(self,expr,value):
        value &= 0xffff;indexed=expr.endswith(',x')
        name=expr[:-2] if indexed else expr
        address=self.num(name)
        if address<256:
            self.dp[address]=value;return
        address+=self.X if indexed else 0
        if 0x3480<=address<0x3500:
            i=address-0x3480;self.records[i]=value&255;self.records[i+1]=value>>8
            self.writes.append((address,value));return
        raise AssertionError('WRITE OUTSIDE RESTORE SCRATCH '+hex(address))
    def flag(self,val):
        self.Z=(val&0xffff)==0
        return val&0xffff
    def val(self,operand):return self.num(operand) if operand.startswith('#') else self.mem(operand)
    def run(self):
        pc=self.labels['NbCapacityPredict']
        for steps in range(150000):
            self.steps=steps+1
            op=self.op[pc];cmd,_,arg=op.partition(' ');cmd=cmd.removesuffix('.l')
            nextpc=pc+1
            if cmd=='lda':self.A=self.flag(self.val(arg))
            elif cmd=='ldx':self.X=self.flag(self.val(arg))
            elif cmd=='sta':self.setmem(arg,self.A)
            elif cmd=='inc':self.setmem(arg,self.flag(self.mem(arg)+1))
            elif cmd=='inx':self.X=self.flag(self.X+1)
            elif cmd=='dey':self.Y=self.flag(self.Y-1)
            elif cmd=='tax':self.X=self.flag(self.A)
            elif cmd=='tay':self.Y=self.flag(self.A)
            elif cmd=='asl':
                if arg=='a':
                    self.C=bool(self.A & 0x8000);self.A=self.flag(self.A<<1)
                else:
                    v=self.mem(arg);self.C=bool(v&0x8000)
                    self.setmem(arg,self.flag(v<<1))
            elif cmd=='lsr':
                assert arg=='a';self.C=bool(self.A&1);self.A=self.flag(self.A>>1)
            elif cmd=='and':self.A=self.flag(self.A&self.val(arg))
            elif cmd=='ora':self.A=self.flag(self.A|self.val(arg))
            elif cmd=='clc':self.C=False
            elif cmd=='sec':self.C=True
            elif cmd=='adc':
                v=self.A+self.val(arg)+int(self.C);self.C=v>65535;self.A=self.flag(v)
            elif cmd in ('cmp','cpx'):
                lhs=self.A if cmd=='cmp' else self.X
                rhs=self.val(arg);self.C=lhs>=rhs;self.flag(lhs-rhs)
            elif cmd in ('beq','bne','bcc','bcs'):
                cond={'beq':self.Z,'bne':not self.Z,'bcc':not self.C,'bcs':self.C}[cmd]
                if cond:nextpc=self.labels[arg]
            elif cmd=='jmp':nextpc=self.labels[arg]
            elif cmd=='rts':return self.C
            else:raise AssertionError('UNSUPPORTED OPCODE '+op)
            pc=nextpc
        raise AssertionError('INFINITE 65816 PREDICTOR LOOP')


def fixture():
    return ['.org $A000','NbBeginRetry:', '.a16','.i16',
        ' lda #0',' sta.l $42D660', ' lda #0',' sta.l $42D606',
        'NbRestorePlanStart:','.a16','.i16',' lda #0',' sta $18','NbRestorePlan:',
        ' lda $18','NbActorPlanStart:',' lda #0','NbRestoreProduce:',
        ' nop','NbQueueDirectPair:',' rts','NbCodeEnd:','.org $C000']


def measured_bytes():
    """Reject 8-bit conditional branch deltas requiring assembler trampolines."""
    instr=[];p=0;labels={}
    sizes={
        'lda':lambda a:3 if a.startswith('#') else 5 if a.startswith('$00') or a.startswith('$42') else 2,
        'ldx':lambda a:3 if a.startswith('#') else 2,
        'sta':lambda a:5 if a.startswith('$00') or a.startswith('$42') else 2,
        'inc':lambda a:2,'inx':lambda a:1,'dey':lambda a:1,
        'tax':lambda a:1,'tay':lambda a:1,'asl':lambda a:1 if a=='a' else 2,'lsr':lambda a:1,
        'and':lambda a:3 if a.startswith('#') else 2,
        'ora':lambda a:3 if a.startswith('#') else 2,
        'clc':lambda a:1,'sec':lambda a:1,'adc':lambda a:3 if a.startswith('#') else 2,
        'cmp':lambda a:3 if a.startswith('#') else 2,
        'cpx':lambda a:3 if a.startswith('#') else 2,
        'beq':lambda a:2,'bne':lambda a:2,'bcc':lambda a:2,'bcs':lambda a:2,
        'jmp':lambda a:3,'rts':lambda a:1,
    }
    for x in _predictor():
        x=x.strip()
        if x.startswith('.') or not x:continue
        if x.endswith(':'):labels[x[:-1]]=p;continue
        op,_,arg=x.partition(' ');op=op.removesuffix('.l')
        size=sizes[op](arg)
        instr.append((p,size,op,arg));p+=size
    for at,size,op,arg in instr:
        if op in ('beq','bne','bcc','bcs'):
            delta=labels[arg]-at-size
            assert -128<=delta<=127,(op,arg,delta)
        if op=='jmp':assert arg in labels
    return p

class EarlyCapacityTests(unittest.TestCase):
    def test_label_contract_and_opt_in_scope(self):
        src=fixture();before=src[:];dst=transform(src)
        self.assertEqual(src,before)
        self.assertEqual(dst.count(' jsr NbCapacityPredict'),1)
        self.assertEqual(dst.count(' jmp NbBeginRetry'),1)
        self.assertTrue(dst.index('NbCapacityPredict:')<dst.index('NbCodeEnd:'))
        self.assertEqual(dst.count('NbRestorePlan:'),1)
        self.assertEqual(dst.count('NbQueueDirectPair:'),1)
        with self.assertRaises(EarlyCapacityContractError):transform(dst)
        with self.assertRaises(EarlyCapacityContractError):transform(src[:src.index('NbCodeEnd:')])
        src2=src[:];src2.remove(' sta.l $42D606')
        with self.assertRaises(EarlyCapacityContractError):transform(src2)

    def test_size_and_branch_ranges(self):
        n=measured_bytes()
        self.assertLess(n,600)

    def test_real_conservative_and_exact_slot_arithmetic(self):
        # Base identity map with 34 distinct invalid homes. The four extra
        # homes are exposed only when eight foreground-occluded actor cells
        # are admitted as backdrop instead of actor, as in retained 16->17.
        base=[42]*1024
        extra=[529,544,575,576]
        actor_cells=list(range(0,96));occluded=actor_cells[-8:]
        for j,i in enumerate(occluded):base[i]=extra[j//2]
        for i in range(100,130):base[i]=i-100
        flagged=set(range(30))|set(extra)
        refs=[0]*768
        for home in flagged:refs[home]=0x8000
        for slot in range(596,768):refs[slot]=0 if slot<720 else 1  # 124 free
        conservative=base[:];exact=base[:]
        for idx in actor_cells:conservative[idx]=0xFFFF
        for idx in actor_cells[:-8]:exact[idx]=0xFFFF
        cons=reference(conservative,refs);ex=reference(exact,refs)
        self.assertEqual((cons['actor'],cons['restoration_homes'],cons['free_tail']),(96,30,124))
        self.assertEqual((ex['actor'],ex['restoration_homes'],ex['free_tail']),(88,34,124))
        self.assertTrue(ex['conservative_fits']);self.assertFalse(cons['conservative_fits'])
        for mp,expected in [(conservative,True),(exact,False)]:
            vm=ProbeVM(mp,refs)
            self.assertEqual(vm.run(),expected)
            self.assertTrue(all(0x3480<=a<0x3480+76 for a,_ in vm.writes))
            self.assertEqual(vm.records[76:],bytes([0xA5])*52)

    def test_48_record_limit_and_equality(self):
        mp=[0]*1024
        refs=[0]*768
        for h in range(49):refs[h]=0x8000;mp[h]=h
        for s in range(596,768):refs[s]=0 if s<750 else 1
        vm=ProbeVM(mp,refs)
        self.assertTrue(vm.run())  # must retry because 49 > 48 even if 154 free
        refs[48]=0
        self.assertFalse(ProbeVM(mp,refs).run())
        for s in range(596,768):refs[s]=1
        for s in range(596,596+48):refs[s]=0
        self.assertFalse(ProbeVM(mp,refs).run())  # exact equality allowed
        refs[643]=1
        self.assertTrue(ProbeVM(mp,refs).run())

    def test_no_actor_no_restorations(self):
        mp=[0]*1024;refs=[0]*768
        self.assertFalse(ProbeVM(mp,refs).run())
        for s in range(596,768):refs[s]=1
        self.assertFalse(ProbeVM(mp,refs).run())  # zero slots needed

    def test_randomized_emitted_instruction_semantics(self):
        rng=random.Random(0x51A16)
        for j in range(110):
            mp=[rng.randrange(596) for _ in range(1024)]
            for i in rng.sample(range(896),rng.randrange(0,180)):
                mp[i]=0xFFFF
            refs=[rng.choice([0,1,2,0x8000,0x8001,0x8002]) for _ in range(768)]
            expected=reference(mp,refs)
            initial=rng.randbytes(128)
            vm=ProbeVM(mp,refs,initial)
            self.assertEqual(vm.run(),not expected['conservative_fits'],j)
            self.assertEqual(vm.dp[0x72],expected['actor'])
            self.assertEqual(vm.dp[0x74],expected['restoration_homes'])
            self.assertEqual(vm.dp[0x70],expected['free_tail'])
            self.assertEqual(vm.map,mp)
            self.assertEqual(vm.refs,refs)
            self.assertEqual(vm.records[76:],initial[76:])
            self.assertLess(vm.steps,150000)

if __name__=='__main__':unittest.main()
