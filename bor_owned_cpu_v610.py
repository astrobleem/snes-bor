"""Small strict 65816 instruction runner for linked DMA/guard byte-stack proofs.

LEGACY GENERIC LoROM byte mapper, NOT an SA-1 cartridge authority proof.
In particular it falsely supplies ROM at SCPU40..4F, which SA-1 maps to
BW-RAM. Retained tests using44..4B are conditional instruction models only.
For explicit qualified mapping state use bor_sa1_mapper_v1343.Sa1MappedCpu;
that opt-in model itself does not attest current runtime/MMC/peripherals.

No loader, dispatch, validator, or return is stubbed. PPU DMA transport is
modeled; real timing and vblank require the separate native emulator run.
"""
from pathlib import Path
import re

class Cpu:
 assets={}
 def __init__(self,folder,mem=None):
  p=Path(folder)/'product';key=str(p.resolve())
  if key not in self.assets:
   rom=(p/'bor.sfc').read_bytes();sy={}
   for line in (p/'main.sym').read_text().splitlines():
    r=re.match(r'([\da-fA-F]{2}):([\da-fA-F]{4,6})\s+(\S+)',line)
    if r:
     bank,off,name=r.groups();sy[name]=int(off,16) if len(off)>4 else int(bank+off,16)
   self.assets[key]=(rom,sy)
  self.rom,self.sy=self.assets[key]
  self.m=dict(mem or {});self.a=0xabcd;self.x=0;self.y=0x5678;self.db=0;self.d=0xa85
  self.p=4;self.s=0x1dff;self.media=[];self.writes=[];self.steps=0;self.observer=None
 def phys(self,at):
  bank=at>>16
  return 0x7e0000+(at&65535) if (bank<64 or 128<=bank<192) and at&65535<8192 else at
 def byte(self,at):
  at=self.phys(at)
  if at>>16 not in (0x7e,0x7f,0x43) and at&65535>=32768:
   return self.rom[(at>>16)*32768+(at&65535)-32768]
  return self.m.get(at,0)
 def read(self,at,n=2):return sum(self.byte(at+i)<<(8*i) for i in range(n))
 def write(self,at,v,n=2):
  at=self.phys(at)
  v&=(1<<(8*n))-1
  if self.observer:self.observer(self,at,v,n)
  for i in range(n):self.m[at+i]=(v>>(8*i))&255;self.writes.append(at+i)
  if at==0x420b:
   assert v==128 and self.byte(0x4370)==1 and self.byte(0x4371)==0x18 and self.byte(0x2115)==0x80
   src=self.read(0x4372)|(self.byte(0x4374)<<16);size=self.read(0x4375);target=self.read(0x2116)*2
   assert size in (64,768),('modeled row or HUD-band VRAM transfer only',size)
   self.media.append(dict(source=src,target=target,length=size))
   for i in range(size):self.m[0x800000+target+i]=self.byte(src+i)
   self.write(0x4372,(src+size)&65535);self.write(0x2116,((target+size)//2)&65535)
 def push(self,v,n=2):
  for i in reversed(range(n)):
   self.m[0x7e0000+self.s]=(v>>(8*i))&255;self.s=(self.s-1)&65535
 def pop(self,n=2):
  v=0
  for i in range(n):self.s=(self.s+1)&65535;v|=self.byte(self.s)<<(8*i)
  return v
 def flag(self,bit,value):self.p=(self.p|bit) if value else (self.p&~bit)
 def nz(self,v,n=2):
  v&=(1<<(n*8))-1;self.flag(2,v==0);self.flag(128,v&(1<<(n*8-1)));return v
 def load(self,v,n):
  v=self.nz(v,n);self.a=((self.a&0xff00)|v) if n==1 else v
 def fetch(self,n=1):v=self.read(self.pc,n);self.pc=(self.pc&0xff0000)|((self.pc+n)&65535);return v
 def validate_rmw_write(self,at,n):
  # The legacy generic mapper has no hardware ownership authority. Strict
  # subclasses must validate the whole RMW destination before its first write.
  pass
 def inc_absolute(self,n):
  # Native-mode W65C816S: WDC datasheet sections3.5/3.5.1 and table5-5.
  # DBR selects the base; data words carry across banks (24-bit wrap),
  # unlike the bank-preserving instruction stream. Only N/Z change.
  # Local Nexen SnesCpu.Shared.h::WriteWordRmw writes MSB before LSB.
  # Idle bus cycles are NOT modeled here; this is not a timing certificate.
  at=(self.db<<16)|self.fetch(2)
  value=sum(self.byte((at+i)&0xffffff)<<(i*8) for i in range(n))
  value=(value+1)&((1<<(n*8))-1)
  self.validate_rmw_write(at,n)
  self.nz(value,n)
  for i in reversed(range(n)):self.write((at+i)&0xffffff,(value>>(i*8))&255,1)
 def run(self,label,long=True,stop=None):
  self.pc=self.sy[label];initial_s=self.s
  sentinel=0x00ff00 if long else (self.pc&0xff0000)|0xff00
  self.push((sentinel-1)&65535,2) if not long else (self.push(0,1),self.push((sentinel-1)&65535,2))
  stops=set(stop) if isinstance(stop,(list,tuple,set)) else {stop}
  while self.pc!=sentinel and self.pc not in stops:
   self.steps+=1;assert self.steps<100000,(label,hex(self.pc))
   if self.pc==self.sy.get('Core_Error_Handler'):return 'error'
   pc=self.pc;self.previous_pc=pc;op=self.fetch();n=1 if self.p&32 else 2;ix=1 if self.p&16 else 2;mask=(1<<(n*8))-1
   if op in (0xc2,0xe2):
    f=self.fetch();self.p=(self.p&~f) if op==0xc2 else (self.p|f)
   elif op==0xa9:self.load(self.fetch(n),n)
   elif op==0xa2:self.x=self.nz(self.fetch(ix),ix)
   elif op==0xa0:self.y=self.nz(self.fetch(ix),ix)
   elif op==0xac:self.y=self.nz(self.read((self.db<<16)+self.fetch(2),ix),ix)
   elif op==0xae:self.x=self.nz(self.read((self.db<<16)+self.fetch(2),ix),ix)
   elif op==0xa6:self.x=self.nz(self.read((self.d+self.fetch())&65535,ix),ix)
   elif op==0xa3:self.load(self.read((self.s+self.fetch())&65535,n),n)
   elif op==0x83:self.write((self.s+self.fetch())&65535,self.a,n)
   elif op in (0xaf,0xbf,0xad,0xbd,0xb9,0xa5):
    at=self.fetch(3) if op in (0xaf,0xbf) else self.d+self.fetch() if op==0xa5 else (self.db<<16)+self.fetch(2)
    if op in (0xbf,0xbd):at+=self.x
    if op==0xb9:at+=self.y
    self.load(self.read(at,n),n)
   elif op in (0x8f,0x9f,0x8d,0x9d,0x99,0x85):
    at=self.fetch(3) if op in (0x8f,0x9f) else self.d+self.fetch() if op==0x85 else (self.db<<16)+self.fetch(2)
    self.write(at+(self.x if op in (0x9f,0x9d) else self.y if op==0x99 else 0),self.a,n)
   elif op==0x8c:self.write((self.db<<16)+self.fetch(2),self.y,ix)
   elif op==0x8e:self.write((self.db<<16)+self.fetch(2),self.x,ix)
   elif op==0x9c:self.write((self.db<<16)+self.fetch(2),0,n)
   elif op==0x9e:self.write(((self.db<<16)+self.fetch(2)+self.x)&0xffffff,0,n)
   elif op==0xce:
    at=(self.db<<16)+self.fetch(2);v=self.nz(self.read(at,n)-1,n);self.write(at,v,n)
   elif op==0xee:self.inc_absolute(n)
   elif op==0x64:self.write((self.d+self.fetch())&65535,0,n)
   elif op in (0xe6,0xc6):
    at=(self.d+self.fetch())&65535;v=self.nz(self.read(at,n)+(1 if op==0xe6 else -1),n);self.write(at,v,n)
   elif op==0xc3:
    v=self.read((self.s+self.fetch())&65535,n);a=self.a&mask;self.flag(1,a>=v);self.nz(a-v,n)
   elif op==0xc5:
    v=self.read((self.d+self.fetch())&65535,n);a=self.a&mask;self.flag(1,a>=v);self.nz(a-v,n)
   elif op==0xcd:
    v=self.read((self.db<<16)+self.fetch(2),n);a=self.a&mask;self.flag(1,a>=v);self.nz(a-v,n)
   elif op==0xec:
    v=self.read((self.db<<16)+self.fetch(2),ix);a=self.x&((1<<(8*ix))-1);self.flag(1,a>=v);self.nz(a-v,ix)
   elif op in (0xc9,0xcf,0xdf,0xd9,0xe0,0xc0):
    if op in (0xe0,0xc0):v=self.fetch(ix);a=self.x if op==0xe0 else self.y;size=ix
    else:
     at=self.fetch(3)+(self.x if op==0xdf else 0) if op in (0xcf,0xdf) else (self.db<<16)+self.fetch(2)+self.y if op==0xd9 else None
     v=self.fetch(n) if op==0xc9 else self.read(at,n);a=self.a&mask;size=n
    self.flag(1,a>=v);self.nz(a-v,size)
   elif op in (0x29,0x09,0x89):
    v=self.fetch(n)
    if op==0x89:self.flag(2,not(self.a&v))
    else:self.load(self.a&v if op==0x29 else self.a|v,n)
   elif op in (0x2d,0x39):self.load(self.a&self.read((self.db<<16)+self.fetch(2)+(self.y if op==0x39 else 0),n),n)
   elif op==0x0d:self.load(self.a|self.read((self.db<<16)+self.fetch(2),n),n)
   elif op==0x05:self.load(self.a|self.read((self.d+self.fetch())&65535,n),n)
   elif op in (0x24,0x2c):
    at=(self.d+self.fetch())&65535 if op==0x24 else (self.db<<16)+self.fetch(2)
    v=self.read(at,n);self.flag(2,not(self.a&v));self.flag(128,bool(v&(1<<(n*8-1))));self.flag(64,bool(v&(1<<(n*8-2))))
   elif op in (0x0f,0x1f):self.load(self.a|self.read(self.fetch(3)+(self.x if op==0x1f else 0),n),n)
   elif op in (0x2f,0x3f):self.load(self.a&self.read(self.fetch(3)+(self.x if op==0x3f else 0),n),n)
   elif op==0x23:self.load(self.a&self.read((self.s+self.fetch())&65535,n),n)
   elif op==0x43:self.load(self.a^self.read((self.s+self.fetch())&65535,n),n)
   elif op==0x03:self.load(self.a|self.read((self.s+self.fetch())&65535,n),n)
   elif op==0xe3:
    assert not self.p&8,'decimal SBC stack-relative not modeled'
    a=self.a&mask;v=self.read((self.s+self.fetch())&65535,n);result=a-v-(not(self.p&1))
    self.flag(64,(a^v)&(a^result)&((mask+1)>>1));self.flag(1,result>=0);self.load(result,n)
   elif op in (0xed,0x6d):
    assert not self.p&8,'decimal ADC/SBC absolute not modeled'
    a=self.a&mask;v=self.read((self.db<<16)+self.fetch(2),n)
    result=a-v-(not(self.p&1)) if op==0xed else a+v+bool(self.p&1)
    self.flag(64,((a^v) if op==0xed else ~(a^v))&(a^result)&((mask+1)>>1))
    self.flag(1,result>=0 if op==0xed else result>mask);self.load(result,n)
   elif op==0x65:
    assert not self.p&8,'decimal ADC direct not modeled'
    a=self.a&mask;v=self.read((self.d+self.fetch())&65535,n);result=a+v+bool(self.p&1)
    self.flag(64,~(a^v)&(a^result)&((mask+1)>>1));self.flag(1,result>mask);self.load(result,n)
   elif op==0xff:
    assert not self.p&8,'decimal SBC long,X not modeled'
    a=self.a&mask;v=self.read(self.fetch(3)+self.x,n);result=a-v-(not(self.p&1))
    self.flag(64,(a^v)&(a^result)&((mask+1)>>1));self.flag(1,result>=0);self.load(result,n)
   elif op in (0x69,0x63,0x6f,0x7f,0xe9,0xef,0xe5,0xf9,0xe3):
    assert not self.p&8,'decimal ADC/SBC not modeled'
    v=self.read((self.db<<16)+self.fetch(2)+self.y,n) if op==0xf9 else self.read(self.fetch(3)+(self.x if op==0x7f else 0),n) if op in (0x6f,0x7f,0xef) else self.read((self.s+self.fetch())&65535,n) if op in (0x63,0xe3) else self.read((self.d+self.fetch())&65535,n) if op==0xe5 else self.fetch(n)
    result=(self.a&mask)-v-(not(self.p&1)) if op in (0xe9,0xef,0xe5,0xf9,0xe3) else (self.a&mask)+v+bool(self.p&1)
    subtract=op in (0xe9,0xef,0xe5,0xf9,0xe3)
    self.flag(64,((self.a^v) if subtract else ~(self.a^v))&(self.a^result)&((mask+1)>>1))
    self.flag(1,result>=0 if op in (0xe9,0xef,0xe5,0xf9,0xe3) else result>mask);self.load(result,n)
   elif op in (0x4a,0x0a):
    a=self.a&mask;self.flag(1,a&1 if op==0x4a else a&(mask+1>>1));self.load(a>>1 if op==0x4a else a<<1,n)
   elif op==0x6a:
    a=self.a&mask;carry=bool(self.p&1);self.flag(1,a&1);self.load((a>>1)|(int(carry)<<(8*n-1)),n)
   elif op==0x2a:
    a=self.a&mask;carry=bool(self.p&1);self.flag(1,a&(1<<(8*n-1)));self.load((a<<1)|int(carry),n)
   elif op==0x2e:
    at=(self.db<<16)+self.fetch(2);v=self.read(at,n);carry=bool(self.p&1)
    self.flag(1,v&(1<<(8*n-1)));self.write(at,self.nz((v<<1)|int(carry),n),n)
   elif op==0x4e:
    at=(self.db<<16)+self.fetch(2);v=self.read(at,n);self.flag(1,v&1);self.write(at,self.nz(v>>1,n),n)
   elif op==0x6e:
    at=(self.db<<16)+self.fetch(2);v=self.read(at,n);carry=bool(self.p&1)
    self.flag(1,v&1);self.write(at,self.nz((v>>1)|(int(carry)<<(8*n-1)),n),n)
   elif op in (0x1a,0x3a):self.load(self.a+(1 if op==0x1a else -1),n)
   elif op in (0xaa,0xa8,0x9b,0xbb):
    v=self.a if op in (0xaa,0xa8) else self.x if op==0x9b else self.y
    if op in (0xaa,0xbb):self.x=self.nz(v,ix)
    else:self.y=self.nz(v,ix)
   elif op in (0x8a,0x98):self.load(self.x if op==0x8a else self.y,n)
   elif op==0x3b:
    assert n==2;self.load(self.s,2)
   elif op==0x1b:
    assert n==2;self.s=self.a&65535
   elif op==0x5b:self.d=self.nz(self.a)
   elif op==0x7b:
    assert n==2,'TDC proof currently requires A16'
    self.load(self.d,2)
   elif op in (0xc8,0x88,0xe8,0xca):
    if op in (0xc8,0x88):self.y=self.nz(self.y+(1 if op==0xc8 else -1),ix)
    else:self.x=self.nz(self.x+(1 if op==0xe8 else -1),ix)
   elif op==0x78:self.flag(4,True)
   elif op==0x58:self.flag(4,False)
   elif op==0xd8:self.flag(8,False)
   elif op==0xb8:self.flag(64,False)
   elif op in (0x18,0x38):self.flag(1,op==0x38)
   elif op in (0x08,0x48,0xda,0x5a,0x8b,0x0b):
    value,size={0x08:(self.p,1),0x48:(self.a,n),0xda:(self.x,ix),0x5a:(self.y,ix),0x8b:(self.db,1),0x0b:(self.d,2)}[op];self.push(value,size)
   elif op in (0x28,0x68,0xfa,0x7a,0xab,0x2b):
    size={0x28:1,0x68:n,0xfa:ix,0x7a:ix,0xab:1,0x2b:2}[op];v=self.pop(size)
    if op==0x28:self.p=v
    elif op==0x68:self.load(v,n)
    elif op==0xfa:self.x=self.nz(v,ix)
    elif op==0x7a:self.y=self.nz(v,ix)
    elif op==0xab:self.db=self.nz(v,1)
    else:self.d=self.nz(v)
   elif op in (0x90,0xb0,0xf0,0xd0,0x80,0x30,0x10):
    rel=self.fetch();rel-=256 if rel>127 else 0
    take={0x90:not(self.p&1),0xb0:bool(self.p&1),0xf0:bool(self.p&2),0xd0:not(self.p&2),0x80:True,0x30:bool(self.p&128),0x10:not(self.p&128)}[op]
    if take:self.pc+=rel
   elif op==0x82:
    rel=self.fetch(2);self.pc+=rel-65536 if rel>32767 else rel
   elif op in (0x4c,0x5c):self.pc=self.fetch(3) if op==0x5c else (self.pc&0xff0000)|self.fetch(2)
   elif op in (0x20,0x22):
    target=self.fetch(3) if op==0x22 else (self.pc&0xff0000)|self.fetch(2)
    if op==0x22:self.push(self.pc>>16,1)
    self.push((self.pc-1)&65535);self.pc=target
   elif op in (0x60,0x6b):
    ret=self.pop();bank=self.pop(1) if op==0x6b else self.pc>>16;self.pc=(bank<<16)|((ret+1)&65535)
   elif op==0xf4:self.push(self.fetch(2))
   elif op in (0x2f,0x3f):self.load(self.a&self.read(self.fetch(3)+(self.x if op==0x3f else 0),n),n)
   elif op==0x49:self.load(self.a^self.fetch(n),n)
   elif op in (0x4f,0x5f):self.load(self.a^self.read((self.fetch(3)+(self.x if op==0x5f else 0))&0xffffff,n),n)
   elif op==0xeb:
    self.a=((self.a&255)<<8)|(self.a>>8);self.nz(self.a&255,1)
   elif op in (0x54,0x44):
    dest=self.fetch();src=self.fetch();count=(self.a&65535)+1
    assert ix==2,'block-move proof requires index16'
    delta=1 if op==0x54 else -1
    for _ in range(count):
     self.write((dest<<16)|self.y,self.byte((src<<16)|self.x),1)
     self.x=(self.x+delta)&65535;self.y=(self.y+delta)&65535
    self.a=65535;self.db=dest
   elif op==0xea:pass
   else:raise AssertionError((label,hex(pc),hex(op)))
  if self.pc==sentinel:assert self.s==initial_s,('stack',label,hex(self.s),hex(initial_s))
  return 'return' if self.pc==sentinel else 'stop'
