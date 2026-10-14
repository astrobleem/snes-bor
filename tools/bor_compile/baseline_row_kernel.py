"""Emits a position-independent native 65816 five-word opaque row blitter.

This is executable machine code plus matching assembly, not pseudocode.
It has been tested in the INCLUDED LIMITED OPCODE INTERPRETER, not on Mesen
or hardware. The interpreter models only this kernel and nominal CPU cycles;
it does not model the SNES bus, SA-1 contention, interrupts, DMA or the PPU.

ABI (native CPU mode):
  DP+$0C: 24-bit pointer to 10 contiguous backdrop plane-pair row bytes
  DP+$3C: 24-bit pointer to 10 contiguous actor plane-pair row bytes
  DP+$32: (source coverage & ~foreground coverage), duplicated in both bytes
  X: output row offset (2*row, 0..14)
  output HIGH $42D680, LOW $42D6C0, matching the existing scratch lease.
A is clobbered. P, X, Y, D, DBR are preserved; stack is balanced. Caller must
own output scratch/DP and provide valid leases/pointers. It makes no PPU writes.
"""
from __future__ import annotations
from dataclasses import dataclass
import struct


@dataclass
class Kernel:
    code: bytes
    assembly: str
    labels: dict[str, int]


def emit(*, bg_dp=0x0C, source_dp=0x3C, mask_dp=0x32,
         high=0x42D680, low=0x42D6C0) -> Kernel:
    regions = [set(range(bg_dp, bg_dp + 3)), set(range(source_dp, source_dp + 3)),
               set(range(mask_dp, mask_dp + 2))]
    if any(min(r) < 0 or max(r) > 255 for r in regions) or any(regions[i] & regions[j] for i in range(3) for j in range(i)):
        raise ValueError('KERNEL_DP_LAYOUT')
    if not (0 <= high <= 0xFFFFFF-64 and 0 <= low <= 0xFFFFFF-16) or set(range(high,high+64)) & set(range(low,low+16)):
        raise ValueError('KERNEL_OUTPUT_LAYOUT')
    data=bytearray(); text=['; Native 65816. Assemble within one measured bank.',
        '; DP pointers/mask and X are caller-owned; see native_kernel.py ABI.',
        'AstraOpaqueRow:', '    php', '    rep #$30', '.a16', '.i16']
    data.extend([0x08,0xC2,0x30]); labels={}; fixups=[]
    def ins(b, line): data.extend(b);text.append('    '+line)
    def label(name): labels[name]=len(data);text.append(name+':')
    def branch(op, name, word=False):
        ins([op]+([0,0] if word else [0]), ('brl ' if word else 'bne ')+name)
        fixups.append((len(data)-(2 if word else 1),name,word))
    ins([0x5A], 'phy');ins([0xA0,0,0], 'ldy #0')
    ins([0xA5,mask_dp],f'lda ${mask_dp:02X}')
    branch(0xD0,'AstraCheckOpaque');branch(0x82,'AstraCopyBack',True)
    label('AstraCheckOpaque');ins([0xC9,255,255],'cmp #$FFFF')
    branch(0xD0,'AstraMixed');branch(0x82,'AstraCopySource',True)
    def body(kind):
        for pair in range(5):
            dest=high+pair*16 if pair<4 else low
            if kind=='mixed':
                ins([0xB7,source_dp],f'lda [${source_dp:02X}],y')
                ins([0x57,bg_dp],f'eor [${bg_dp:02X}],y')
                ins([0x25,mask_dp],f'and ${mask_dp:02X}')
                ins([0x57,bg_dp],f'eor [${bg_dp:02X}],y')
            else:
                dp=bg_dp if kind=='back' else source_dp
                ins([0xB7,dp],f'lda [${dp:02X}],y')
            ins([0x9F,*dest.to_bytes(3,'little')],f'sta.l ${dest:06X},x')
            if pair!=4:ins([0xC8],'iny');ins([0xC8],'iny')
    label('AstraMixed');body('mixed');branch(0x82,'AstraDone',True)
    label('AstraCopyBack');body('back');branch(0x82,'AstraDone',True)
    label('AstraCopySource');body('source')
    label('AstraDone');ins([0x7A],'ply');ins([0x28],'plp');ins([0x6B],'rtl')
    for pos,name,word in fixups:
        rel=labels[name]-pos-(2 if word else 1)
        if not word and not -128<=rel<=127:raise AssertionError('SHORT_BRANCH_RANGE')
        data[pos:pos+(2 if word else 1)]=rel.to_bytes(2 if word else 1,'little',signed=True)
    return Kernel(bytes(data),'\n'.join(text)+'\n',labels)


class Tiny65816:
    """A deliberately limited, fail-closed interpreter for the emitted opcodes.

    Native mode only; test entry may have M/X bits set. P/stack behavior is
    checked. A top-level RTL terminates the test, rather than fetching a caller.
    No claim of a general 65816 emulator or native hardware certification.
    """
    def __init__(self, code: bytes, memory: dict[int,int], *, dp=0x3400,
                 x=0, y=0x2345, p=0, a=0x7654, sp=0x1FFF, dbr=0):
        self.code=code;self.mem=memory;self.dp=dp;self.x=x;self.y=y
        self.p=p;self.a=a;self.sp=sp;self.dbr=dbr;self.pc=0
        self.cycles=0;self.instructions=0;self.writes=[]
        if p&0x10:self.x&=255;self.y&=255
    def read8(self,addr):return self.mem.get(addr&0xFFFFFF,0)
    def read16(self,addr):return self.read8(addr)|(self.read8(addr+1)<<8)
    def write8(self,addr,value):
        addr&=0xFFFFFF;self.mem[addr]=value&255;self.writes.append(addr)
    def push(self,value):self.write8(self.sp,value);self.sp=(self.sp-1)&65535
    def pull(self):self.sp=(self.sp+1)&65535;return self.read8(self.sp)
    def fetch(self):v=self.code[self.pc];self.pc+=1;return v
    def fetch16(self):return self.fetch()|(self.fetch()<<8)
    def nz(self,v,width):
        sign=1<<(width-1);self.p=(self.p&~0x82)|(0x02 if v==0 else 0)|(0x80 if v&sign else 0)
    def long_ind_y(self,off):
        at=(self.dp+off)&65535
        ptr=self.read8(at)|(self.read8((at+1)&65535)<<8)|(self.read8((at+2)&65535)<<16)
        return (ptr+self.y)&0xFFFFFF
    def run(self,limit=200):
        while self.instructions<limit:
            op=self.fetch();self.instructions+=1;wide=not(self.p&0x20)
            if op==0x08:self.push(self.p);self.cycles+=3
            elif op==0xC2:self.p&=~self.fetch();self.cycles+=3
            elif op==0x5A:
                if not self.p&0x10:self.push(self.y>>8)
                self.push(self.y);self.cycles+=3+(not bool(self.p&0x10))
            elif op==0x7A:
                self.y=self.pull()
                if not self.p&0x10:self.y|=self.pull()<<8
                self.nz(self.y,8 if self.p&0x10 else 16);self.cycles+=4+(not bool(self.p&0x10))
            elif op==0x28:
                self.p=self.pull()
                if self.p&0x10:self.x&=255;self.y&=255
                self.cycles+=4
            elif op==0xA0:
                self.y=self.fetch() if self.p&0x10 else self.fetch16()
                self.nz(self.y,8 if self.p&0x10 else 16);self.cycles+=2+(not bool(self.p&0x10))
            elif op in (0xA5,0x25):
                off=self.fetch();addr=(self.dp+off)&65535
                value=self.read16(addr) if wide else self.read8(addr)
                if op==0x25:value&=self.a
                if wide:self.a=value
                else:self.a=(self.a&0xFF00)|value
                self.nz(value,16 if wide else 8);self.cycles+=3+wide+bool(self.dp&255)
            elif op==0xC9:
                val=self.fetch16() if wide else self.fetch();mask=65535 if wide else 255
                a=self.a&mask;self.p=(self.p&~1)|(a>=val)
                self.nz((a-val)&mask,16 if wide else 8);self.cycles+=2+wide
            elif op==0xD0:
                delta=self.fetch();delta=delta-256 if delta>=128 else delta
                take=not(self.p&2)
                if take:self.pc+=delta
                self.cycles+=2+take
            elif op==0x82:
                delta=self.fetch16();delta=delta-65536 if delta>=32768 else delta
                self.pc+=delta;self.cycles+=4
            elif op in (0xB7,0x57):
                addr=self.long_ind_y(self.fetch())
                value=self.read16(addr) if wide else self.read8(addr)
                if op==0x57:value^=self.a& (65535 if wide else 255)
                if wide:self.a=value
                else:self.a=(self.a&0xFF00)|value
                self.nz(value,16 if wide else 8);self.cycles+=6+wide+bool(self.dp&255)
            elif op==0x9F:
                addr=self.fetch16()|(self.fetch()<<16);addr=(addr+self.x)&0xFFFFFF
                self.write8(addr,self.a)
                if wide:self.write8(addr+1,self.a>>8)
                self.cycles+=5+wide
            elif op==0xC8:
                self.y=(self.y+1)&(255 if self.p&0x10 else 65535)
                self.nz(self.y,8 if self.p&0x10 else 16);self.cycles+=2
            elif op==0x6B:self.cycles+=6;return self
            else:raise ValueError(f'UNSUPPORTED_TEST_OPCODE_{op:02X}')
        raise ValueError('TEST_KERNEL_INSTRUCTION_LIMIT')


def run_row(bg: bytes, src: bytes, mask: int, row: int, *, dp=0x3400,
            p=0, y=0x2345, bg_addr=0xE0FFFC, src_addr=0xE1FFFA):
    if len(bg)!=10 or len(src)!=10 or not 0<=row<8 or not 0<=mask<=65535:
        raise ValueError('ROW_TEST_DOMAIN')
    mem={}
    def put(at,data):mem.update({(at+i)&0xFFFFFF:v for i,v in enumerate(data)})
    put(bg_addr,bg);put(src_addr,src)
    put((dp+0x0C)&65535,bg_addr.to_bytes(3,'little'))
    put((dp+0x3C)&65535,src_addr.to_bytes(3,'little'))
    put((dp+0x32)&65535,mask.to_bytes(2,'little'))
    cpu=Tiny65816(emit().code,mem,dp=dp,x=row*2,y=y,p=p)
    original=(cpu.p,cpu.x,cpu.y,cpu.sp,cpu.dp,cpu.dbr)
    cpu.run()
    if (cpu.p,cpu.x,cpu.y,cpu.sp,cpu.dp,cpu.dbr)!=original:
        raise AssertionError('ROW_KERNEL_CALLER_CORRUPTION')
    result=b''.join(cpu.read16((0x42D680+pair*16 if pair<4 else 0x42D6C0)+2*row).to_bytes(2,'little') for pair in range(5))
    return result,cpu
