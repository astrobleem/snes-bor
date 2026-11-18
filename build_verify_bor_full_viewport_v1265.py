"""Full-width viewport: include the fractional right-edge tile in camera clamp."""
from pathlib import Path
import ast,fcntl,hashlib,os,shutil,sys
from build_verify_bor_pin_slice_v1134 import cpu,symbols,off,regs,clean
from bor_linux_guard_v1132 import require_memory
ROOT=Path('/home/chad/bor-v1131-20261113');OLD=ROOT/'inputs/candidate-v1264';NEW=ROOT/'inputs/candidate-v1265';BODY=0x33ea00

def location(s,raw):
 start=s['Core_StreamScroll_ClampCamera'];end=s['Core_StreamScroll_ClampCamera__right_ok'];data=raw[off(start):off(end)]
 pat=bytes.fromhex('8a18691f00');assert data.count(pat)==1
 return start+data.index(pat)

def build():
 assert not NEW.exists();s=symbols(OLD);raw=(OLD/'bor.sfc').read_bytes();rom=bytearray(raw);at=location(s,raw)
 # Original absolute read preserves the caller's DB convention. CMP sets
 # carry iff any fractional pixel is present; TXA preserves that carry.
 b=b'\xad'+(s['Screen_PosX']&65535).to_bytes(2,'little')+bytes.fromhex('290700c901008a691f006b')
 assert not any(raw[off(BODY):off(BODY)+len(b)]) and not any(BODY<=v<BODY+len(b) for v in s.values())
 rom[off(at):off(at)+5]=b'\x22'+BODY.to_bytes(3,'little')+b'\xea';rom[off(BODY):off(BODY)+len(b)]=b
 c=sum(rom)&65535;rom[0x7fdc:0x7fe0]=(c^65535).to_bytes(2,'little')+c.to_bytes(2,'little');assert sum(rom)&65535==c
 assert all(a==v or off(at)<=i<off(at)+5 or off(BODY)<=i<off(BODY)+len(b) or 0x7fdc<=i<0x7fe0 for i,(a,v) in enumerate(zip(raw,rom)))
 NEW.mkdir();(NEW/'bor.sfc').write_bytes(rom);shutil.copyfile(OLD/'world.sym',NEW/'world.sym')
 text=(OLD/'main.sym').read_text()+f'\n33:EA00 FullViewport1265Right\n33:{(BODY+len(b))&65535:04X} FullViewport1265End\n'
 (NEW/'main.sym').write_text(text);print('BUILT',len(b),'bytes; original clamp and left/right watermark semantics retained',flush=True)

def verify():
 s=symbols(NEW);count=changed=0;extra=set()
 def case(lo,hi,x,status=4,enabled=1,db=0):
  nonlocal count,changed
  pair=[]
  for folder in (OLD,NEW):
   q=cpu(folder);q.db=db;q.p=status;q.x=0x1357
   q.write(s['StreamScroll_Enabled'],enabled,1);q.write(s['StreamScroll_StagedLo'],lo);q.write(s['StreamScroll_StagedHi'],hi)
   addr=(db<<16)+(s['Screen_PosX']&65535);q.write(addr,x);q.writes=[];q.run('Core_StreamScroll_ClampCamera',long=False);pair.append(q)
  a,b=pair;av=a.read(addr);bv=b.read(addr)
  if enabled:
   expected=max(lo*8,min(x,max(0,hi-31)*8)) if (x+255)//8>hi or x//8<lo else x
   assert bv==expected,(lo,hi,x,av,bv,expected)
   if hi-lo>=31:assert bv//8>=lo and (bv+255)//8<=hi,(lo,hi,x,bv)
  else:assert bv==x
  assert b.y==a.y and b.db==a.db and b.d==a.d and b.s==a.s and not b.media
  am,bm=clean(a),clean(b);allowed={b.phys(addr),b.phys(addr+1)}
  assert all(k in allowed for k in am.keys()|bm.keys() if am.get(k)!=bm.get(k))
  assert all(k in allowed or 0x7e1c00<=k<0x7e2000 for k in b.writes)
  if av==bv:assert regs(a)==regs(b),(lo,hi,x,regs(a),regs(b))
  else:changed+=1;assert x&7 and (x+255)//8>hi and bv<=av
  extra.add(b.steps-a.steps);count+=1
 for lo in (0,1,17,100,376):
  for width in (31,32,35,63):
   hi=lo+width
   for col in {max(0,lo-1),lo,lo+1,hi-32,hi-31,hi-30,hi}:
    if col>=0:
     for fraction in range(8):case(lo,hi,col*8+fraction)
 for p in range(256):
  if not p&8:
   for db in (0,0x80):
    case(0,31,7,p,1,db);case(0,33,7,p,1,db);case(0,31,7,p,0,db)
 print('PASS_CLAMP',count,'linked cases;',changed,'necessary fractional clamps; instruction delta',sorted(extra),'; no new state, media or PPU writes; native timing still required',flush=True)

def workers():
 previous=hashlib.sha256((OLD/'bor.sfc').read_bytes()).hexdigest();digest=hashlib.sha256((NEW/'bor.sfc').read_bytes()).hexdigest();s=symbols(NEW)
 lua="\nlocal camera1265last=-1;local camera1265count=0\nemu.addEventCallback(function()\n local x=emu.readWord("+str(s['Screen_PosX'])+",emu.memType.snesMemory)\n if x~=camera1265last then camera1265last=x;camera1265count=camera1265count+1;if camera1265count>512 then error('BORCAMERA1265_CAP') end;print('BORCAMERA1265|'..borOrdinal..'|'..x..'|'..emu.readWord("+str(s['StreamScroll_StagedLo'])+",emu.memType.snesMemory)..'|'..emu.readWord("+str(s['StreamScroll_StagedHi'])+",emu.memType.snesMemory)) end\nend,emu.eventType.endFrame)\n"
 assert 'emu.write' not in lua
 for mode in ('early','full'):
  text=(ROOT/f'runner/fullview1264_{mode}_worker.py').read_text();assert text.count(previous)==1;text=text.replace(previous,digest,1)
  f=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='observer_source');old=ast.literal_eval(f.body[0].value)
  text=text.replace(repr(old),repr(old+lua),1).replace('line.startswith((' ,"line.startswith((b'BORCAMERA1265',",1);ast.parse(text)
  p=ROOT/f'runner/fullview1265_{mode}_worker.py'
  if p.exists():assert p.read_text()==text
  else:p.write_text(text)

def main():
 print('GUARDS',require_memory(True),'DISK',round(shutil.disk_usage(ROOT).free/2**30,3),flush=True)
 assert shutil.disk_usage(ROOT).free>18*2**30 and os.getloadavg()[0]<os.cpu_count()
 with (ROOT/'bor-mesen.lock').open('r+b') as f:
  fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  if '--verify-only' not in sys.argv:build()
  verify();workers()
if __name__=='__main__':main()
