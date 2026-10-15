"""Restricted 65816 byte assembler/executor for single-pass restoration tests.

Derived from the previously delivered home_borrow_bitmap_vm.py. BRA, LDX direct-page, and
caller-supplied external symbols were added. Not a complete hardware emulator.

This executes MACHINE BYTES, not source lines. It is deliberately NOT Mesen,
not a complete CPU emulator, and does not estimate SNES master clocks. Only
instructions used by the pinned helper and the bitmap overlay are admitted.
The stack, carry, NZ flags, little-endian word accesses, JSR/RTS, and indexed
long addressing are implemented for the tested native-mode, binary paths.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Sequence

# Encoder and byte decoder below are independent tables/branches.
SINGLE = {"tax":0xAA,"txa":0x8A,"inx":0xE8,"clc":0x18,"sec":0x38,
          "rts":0x60,"pha":0x48,"pla":0x68,"phx":0xDA,"plx":0xFA}
BRANCH = {"bcc":0x90,"bcs":0xB0,"beq":0xF0,"bne":0xD0,"bra":0x80}
IMMEDIATE = {"lda":0xA9,"ldx":0xA2,"cmp":0xC9,"cpx":0xE0,
             "and":0x29,"ora":0x09,"eor":0x49,"sbc":0xE9,"adc":0x69}
DIRECT = {"ldx":0xA6,"lda":0xA5,"sta":0x85,"cmp":0xC5,"and":0x25,"ora":0x05,
          "sbc":0xE5,"adc":0x65,"inc":0xE6}
LONG = {"lda.l":0xAF,"sta.l":0x8F,"cmp.l":0xCF,"eor.l":0x4F,"ora.l":0x0F}
LONG_X = {"lda.l":0xBF,"sta.l":0x9F}
ACCUMULATOR = {"asl":0x0A,"lsr":0x4A,"inc":0x1A}
EXTERNAL = {"WarmCopyBackdrop":0x39D050,"NbPreloadPair":0x39A480,
            "NbFlushQueue":0x39A4C0}


def value(expr: str, labels: dict[str,int]) -> int:
    expr = expr.strip()
    if expr in labels:
        return labels[expr]
    if expr.startswith("$"):
        return int(expr[1:],16)
    return int(expr,0)


@dataclass
class Program:
    base: int
    data: bytes
    symbols: dict[str,int]
    listing: list[tuple[int,bytes,str]]


def assemble(lines: Sequence[str], base: int=0x39B300, externals: dict[str,int] | None=None) -> Program:
    symbols = dict(EXTERNAL)
    symbols.update(externals or {})
    statements = []
    pc = base
    for raw in lines:
        line = raw.split(";",1)[0].strip()
        if not line or line in (".a16",".i16",".snes"):
            continue
        if line.startswith(".org") or line.startswith(".bank"):
            raise ValueError("Pass one contiguous helper block, without .org/.bank")
        if line.endswith(":"):
            label=line[:-1]
            if label in symbols:
                raise ValueError("Duplicate label: "+label)
            symbols[label]=pc
            continue
        op,_,arg=line.partition(" ")
        if op==".db":
            size=len(arg.split(","))
        elif op in SINGLE or arg=="a":
            size=1
        elif op in BRANCH:
            size=2
        elif op in ("jmp","jsr") or arg.startswith("#"):
            size=3
        elif op.endswith(".l"):
            size=4
        elif arg.startswith("$") and len(arg)==3:
            size=2
        else:
            raise ValueError("Unsupported statement: "+line)
        statements.append((pc,op,arg,line,size));pc+=size
    if pc>>16 != base>>16:
        raise ValueError("Helper crossed program bank")
    result=bytearray();listing=[]
    for pc,op,arg,line,size in statements:
        if op==".db":
            encoded=bytes(value(x,symbols) for x in arg.split(","))
        elif op in SINGLE:
            encoded=bytes([SINGLE[op]])
        elif arg=="a":
            encoded=bytes([ACCUMULATOR[op]])
        elif op in BRANCH:
            target=value(arg,symbols)
            delta=target-pc-2
            if not -128<=delta<=127:
                raise ValueError("Branch out of range: "+line)
            encoded=bytes([BRANCH[op],delta&255])
        elif op in ("jmp","jsr"):
            target=value(arg,symbols)
            if target>>16 != pc>>16:
                raise ValueError("Wrong same-bank jump target")
            encoded=bytes([0x4C if op=="jmp" else 0x20])+(target&65535).to_bytes(2,"little")
        elif arg.startswith("#"):
            encoded=bytes([IMMEDIATE[op]])+value(arg[1:],symbols).to_bytes(2,"little")
        elif op.endswith(".l"):
            indexed=arg.endswith(",x")
            address=value(arg[:-2] if indexed else arg,symbols)
            encoded=bytes([(LONG_X if indexed else LONG)[op]])+address.to_bytes(3,"little")
        else:
            encoded=bytes([DIRECT[op],value(arg,symbols)])
        if len(encoded)!=size:
            raise AssertionError("Encoder size disagreement")
        result+=encoded;listing.append((pc,encoded,line))
    return Program(base,bytes(result),symbols,listing)


class Machine:
    def __init__(self, program: Program):
        self.program=program
        self.ram={0:bytearray(65536),0x42:bytearray(65536)}
        self.a=0;self.x=0;self.y=0xBEEF;self.d=0x3400;self.dbr=0
        self.sp=0x01FF;self.c=False;self.z=False;self.n=False
        self.pc=program.base
        self.steps=0;self.reads=Counter();self.writes=[];self.hits=Counter()
        self.at={addr:name for name,addr in program.symbols.items()}
        self.hooks:dict[str,Callable[[Machine],None]]={}

    def poke16(self,address:int,v:int)->None:
        buf=self.ram[address>>16];off=address&65535
        buf[off]=v&255;buf[(off+1)&65535]=(v>>8)&255

    def peek16(self,address:int)->int:
        buf=self.ram[address>>16];off=address&65535
        return buf[off] | (buf[(off+1)&65535]<<8)

    def load_words(self,address:int,words:Sequence[int])->None:
        for i,w in enumerate(words):self.poke16(address+2*i,w)

    def blob(self,address:int,length:int)->bytes:
        return bytes(self.ram[address>>16][address&65535:(address&65535)+length])

    def read16(self,address:int)->int:
        address &= 0xFFFFFF
        if 0x42C000<=address<0x42C800:kind="pending_map"
        elif 0x42C800<=address<0x42D000:kind="committed_map"
        elif 0x42D000<=address<0x42D600:kind="references"
        elif 0x3500<=address<0x3598:kind="bitmaps"
        elif address>>16==0x39:kind="rom_data"
        else:kind="other"
        self.reads[kind]+=1
        if kind=="rom_data":
            off=address-self.program.base
            if not 0<=off<len(self.program.data)-1:raise AssertionError("ROM data range")
            return self.program.data[off] | self.program.data[off+1]<<8
        return self.peek16(address)

    def write16(self,address:int,v:int)->None:
        self.writes.append((address,v&65535,2,self.pc))
        self.poke16(address,v)

    def push16(self,v:int)->None:
        for b in (v>>8,v&255):
            self.ram[0][self.sp]=b&255
            self.writes.append((self.sp,b&255,1,self.pc))
            self.sp=(self.sp-1)&65535

    def pop16(self)->int:
        self.sp=(self.sp+1)&65535;lo=self.ram[0][self.sp]
        self.sp=(self.sp+1)&65535;hi=self.ram[0][self.sp]
        return lo|(hi<<8)

    def nz(self,v:int)->int:
        v &= 65535;self.z=(v==0);self.n=bool(v&0x8000);return v

    def run(self,label:str,max_steps:int=5_000_000)->None:
        before_sp=self.sp
        self.push16(0xFFEF)
        self.pc=self.program.symbols[label]
        stop=(self.program.base&0xFF0000)|0xFFF0
        start_steps=self.steps
        while self.pc!=stop:
            if self.steps-start_steps>=max_steps:raise RuntimeError("Instruction limit")
            self.steps+=1
            if self.pc in self.at:
                name=self.at[self.pc];self.hits[name]+=1
                if name in self.hooks:self.hooks[name](self)
            off=self.pc-self.program.base
            if not 0<=off<len(self.program.data):raise RuntimeError(f"Unimplemented external target {self.pc:06X}")
            b=self.program.data
            op=b[off]
            u8=lambda:b[off+1]
            u16=lambda:b[off+1]|(b[off+2]<<8)
            u24=lambda:b[off+1]|(b[off+2]<<8)|(b[off+3]<<16)
            step=1
            if op in (0xA9,0xA2,0xC9,0xE0,0x29,0x09,0x49,0xE9,0x69):
                v=u16();step=3
                if op==0xA9:self.a=self.nz(v)
                elif op==0xA2:self.x=self.nz(v)
                elif op in (0xC9,0xE0):
                    lhs=self.a if op==0xC9 else self.x
                    self.c=lhs>=v;self.nz(lhs-v)
                elif op==0x29:self.a=self.nz(self.a&v)
                elif op==0x09:self.a=self.nz(self.a|v)
                elif op==0x49:self.a=self.nz(self.a^v)
                elif op==0xE9:
                    r=self.a-v-(not self.c);self.c=r>=0;self.a=self.nz(r)
                else:
                    r=self.a+v+self.c;self.c=r>65535;self.a=self.nz(r)
            elif op in (0xA5,0xA6,0x85,0xC5,0x25,0x05,0xE5,0x65,0xE6):
                addr=(self.d+u8())&65535;step=2
                if op==0x85:self.write16(addr,self.a)
                else:
                    v=self.read16(addr)
                    if op==0xA5:self.a=self.nz(v)
                    elif op==0xA6:self.x=self.nz(v)
                    elif op==0xC5:self.c=self.a>=v;self.nz(self.a-v)
                    elif op==0x25:self.a=self.nz(self.a&v)
                    elif op==0x05:self.a=self.nz(self.a|v)
                    elif op==0xE5:
                        r=self.a-v-(not self.c);self.c=r>=0;self.a=self.nz(r)
                    elif op==0x65:
                        r=self.a+v+self.c;self.c=r>65535;self.a=self.nz(r)
                    else:self.write16(addr,self.nz(v+1))
            elif op in (0xAF,0xBF,0x8F,0x9F,0xCF,0x4F,0x0F):
                addr=(u24()+(self.x if op in (0xBF,0x9F) else 0))&0xFFFFFF;step=4
                if op in (0x8F,0x9F):self.write16(addr,self.a)
                else:
                    v=self.read16(addr)
                    if op in (0xAF,0xBF):self.a=self.nz(v)
                    elif op==0xCF:self.c=self.a>=v;self.nz(self.a-v)
                    elif op==0x4F:self.a=self.nz(self.a^v)
                    else:self.a=self.nz(self.a|v)
            elif op==0xAA:self.x=self.nz(self.a)
            elif op==0x8A:self.a=self.nz(self.x)
            elif op==0xE8:self.x=self.nz(self.x+1)
            elif op==0x0A:self.c=bool(self.a&0x8000);self.a=self.nz(self.a<<1)
            elif op==0x4A:self.c=bool(self.a&1);self.a=self.nz(self.a>>1)
            elif op==0x1A:self.a=self.nz(self.a+1)
            elif op==0x18:self.c=False
            elif op==0x38:self.c=True
            elif op in (0x90,0xB0,0xF0,0xD0,0x80):
                take={0x90:not self.c,0xB0:self.c,0xF0:self.z,0xD0:not self.z,0x80:True}[op]
                delta=u8();delta=delta-256 if delta>=128 else delta
                self.pc+=2+(delta if take else 0);continue
            elif op==0x4C:self.pc=(self.pc&0xFF0000)|u16();continue
            elif op==0x20:
                self.push16((self.pc+2)&65535)
                self.pc=(self.pc&0xFF0000)|u16();continue
            elif op==0x60:self.pc=(self.pc&0xFF0000)|((self.pop16()+1)&65535);continue
            elif op==0x48:self.push16(self.a)
            elif op==0x68:self.a=self.nz(self.pop16())
            elif op==0xDA:self.push16(self.x)
            elif op==0xFA:self.x=self.nz(self.pop16())
            else:raise RuntimeError(f"Unknown opcode {op:02X} at {self.pc:06X}")
            self.pc+=step
        if self.sp!=before_sp:raise AssertionError("Unbalanced stack")
