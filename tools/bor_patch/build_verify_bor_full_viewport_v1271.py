"""Fractional clamp with an equal-duration zero-camera arithmetic path."""
from pathlib import Path
import ast,fcntl,hashlib,os,shutil,sys
from build_verify_bor_pin_slice_v1134 import cpu,symbols,off,regs,clean
from bor_linux_guard_v1132 import require_memory
from build_verify_bor_full_viewport_v1265 import location
ROOT=Path('/home/chad/bor-v1131-20261113');OLD=ROOT/'inputs/candidate-v1264';REFERENCE=ROOT/'inputs/candidate-v1265';NEW=ROOT/'inputs/candidate-v1271'
FALL=0x33eb00;POSITIVE=0x33eb80

def build():
 assert not NEW.exists();s=symbols(OLD);raw=(OLD/'bor.sfc').read_bytes();rom=bytearray(raw)
 start=s['Core_StreamScroll_ClampCamera'];active=s['Core_StreamScroll_ClampCamera__active'];right=s['Core_StreamScroll_ClampCamera__right_ok'];last=s['Core_StreamScroll_ClampCamera__left_ok'];at=location(s,raw)
 assert raw[off(active):off(active)+6]==b'\xc2\x31\xaf'+s['Screen_PosX'].to_bytes(3,'little')
 assert raw[off(active)+6:off(at)]==bytes.fromhex('4a4a4aaa')
 assert raw[off(at):off(at)+5]==bytes.fromhex('8a18691f00') and raw[off(last)]==0x60
 oldfall=raw[off(at)+13:off(right)]
 assert oldfall[:4]==b'\xaf'+s['StreamScroll_StagedHi'].to_bytes(3,'little')
 # The ordinary zero path ends ADC at the same slow-ROM clock as the old
 # LSR/LSR/LSR/TAX/TXA/CLC/ADC sequence: both108 master clocks, excluding
 # interrupt overlap. Native timing is measured, not inferred from this sum.
 z=bytearray(raw[off(start):off(active)+6])
 z+=b'\xf0\x04\x5c'+POSITIVE.to_bytes(3,'little')
 z+=bytes.fromhex('a20000ea890000691f00')
 z+=b'\xcf'+s['StreamScroll_StagedHi'].to_bytes(3,'little')
 bcc=len(z);z+=b'\x90\x00';beq=len(z);z+=b'\xf0\x00';z+=b'\x5c'+FALL.to_bytes(3,'little')
 newright=start+len(z);z+=raw[off(right):off(last)+1];newlast=start+len(z)-1
 z[bcc+1]=newright-(start+bcc+2);z[beq+1]=newright-(start+beq+2)
 assert len(z)<=last+1-start
 fallback=oldfall+b'\x5c'+newright.to_bytes(3,'little')
 positive=bytearray(raw[off(active):off(last)])
 idx=at-active;positive[idx:idx+5]=b'\xaf'+s['Screen_PosX'].to_bytes(3,'little')+bytes.fromhex('290700c901008a691f00')
 positive+=b'\x5c'+newlast.to_bytes(3,'little')
 patches=[(start,bytes(z)+b'\xea'*(last+1-start-len(z))),(FALL,fallback),(POSITIVE,bytes(positive))]
 for address,data in patches[1:]:assert not any(raw[off(address):off(address)+len(data)]) and not any(address<=v<address+len(data) for v in s.values())
 for address,data in patches:rom[off(address):off(address)+len(data)]=data
 c=sum(rom)&65535;rom[0x7fdc:0x7fe0]=(c^65535).to_bytes(2,'little')+c.to_bytes(2,'little');assert sum(rom)&65535==c
 assert all(a==v or any(off(t)<=i<off(t)+len(b) for t,b in patches) or 0x7fdc<=i<0x7fe0 for i,(a,v) in enumerate(zip(raw,rom)))
 labels={'Core_StreamScroll_ClampCamera__right_ok':newright,'Core_StreamScroll_ClampCamera__left_ok':newlast,'Core_StreamScroll_ClampCamera__have_right_col':FALL+s['Core_StreamScroll_ClampCamera__have_right_col']-(at+13),'FullViewport1271Positive':POSITIVE,'FullViewport1271Fallback':FALL}
 lines=(OLD/'main.sym').read_text().splitlines();lines=[l for l in lines if not any(l.split()[-1:]==[n] for n in labels)]
 for n,v in labels.items():lines.append(f'{v>>16:02X}:{v&65535:04X} {n}')
 NEW.mkdir();(NEW/'bor.sfc').write_bytes(rom);(NEW/'main.sym').write_text('\n'.join(lines)+'\n');shutil.copyfile(OLD/'world.sym',NEW/'world.sym')
 print('BUILT in-place',len(z),'of',last+1-start,'bytes; moved fallback',len(fallback),'positive',len(positive),'; no new RAM or DMA/PPU work',flush=True)

def verify():
 s=symbols(NEW);count=0
 def case(lo,hi,x,status=4,enabled=1,db=0):
  nonlocal count
  pair=[]
  for folder in (REFERENCE,NEW):
   q=cpu(folder);q.p=status;q.db=db;q.write(s['StreamScroll_Enabled'],enabled,1);q.write(s['StreamScroll_StagedLo'],lo);q.write(s['StreamScroll_StagedHi'],hi);q.write((db<<16)+(s['Screen_PosX']&65535),x);q.writes=[]
   q.run('Core_StreamScroll_ClampCamera',long=False);pair.append(q)
  a,b=pair;assert regs(a)==regs(b) and clean(a)==clean(b),(lo,hi,x,status,regs(a),regs(b));assert not b.media
  if enabled and hi-lo>=31:
   out=b.read((db<<16)+(s['Screen_PosX']&65535));assert out//8>=lo and (out+255)//8<=hi
  count+=1
 for lo in (0,1,17,100,376):
  for width in (31,32,35,63):
   hi=lo+width
   for col in {max(0,lo-1),lo,lo+1,hi-32,hi-31,hi-30,hi}:
    if col>=0:
     for f in range(8):case(lo,hi,col*8+f)
 for p in range(256):
  if not p&8:
   for db in (0,0x80):
    for hi in (0,30,31,32,33,55):case(0,hi,0,p,1,db)
    case(0,31,7,p,1,db);case(0,31,7,p,0,db)
 print('PASS_GEOMETRY_ABI',count,'exact reference linked cases; static zero arithmetic108 master clocks each; native interrupt/timing qualification required',flush=True)

def observer(s):
 lua='''\nlocal camera1271start=nil;local camera1271n=0
local function camera1271enter()
 local q=emu.getState();camera1271start={q.masterClock,emu.readWord(SCREEN,emu.memType.snesMemory),emu.readWord(HIGH,emu.memType.snesMemory)}
end
local function camera1271leave()
 if camera1271start then local q=emu.getState();camera1271n=camera1271n+1;if camera1271n>1200 then error('CAMERA1271_CAP') end;print('BORCAMCOST1271|'..borOrdinal..'|'..camera1271start[2]..'|'..camera1271start[3]..'|'..(q.masterClock-camera1271start[1]));camera1271start=nil end
end
'''.replace('SCREEN',str(s['Screen_PosX'])).replace('HIGH',str(s['StreamScroll_StagedHi']))
 for name,fn in [('Core_StreamScroll_ClampCamera','camera1271enter'),('Core_StreamScroll_ClampCamera__left_ok','camera1271leave')]:
  at=off(s[name]);lua+=f'emu.addMemoryCallback({fn},emu.callbackType.exec,{at},{at},emu.cpuType.snes,emu.memType.snesPrgRom)\n'
 return lua

def workers():
 prev=hashlib.sha256((REFERENCE/'bor.sfc').read_bytes()).hexdigest()
 for folder,tag in ((NEW,'1271'),(OLD,'1264cost')):
  digest=hashlib.sha256((folder/'bor.sfc').read_bytes()).hexdigest();lua=observer(symbols(folder));assert 'emu.write' not in lua
  for mode in ('early','full'):
   text=(ROOT/f'runner/fullview1265_{mode}_worker.py').read_text();assert text.count(prev)==1;text=text.replace(prev,digest,1)
   f=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='observer_source');old=ast.literal_eval(f.body[0].value)
   text=text.replace(repr(old),repr(old+lua),1).replace('line.startswith((' ,"line.startswith((b'BORCAMCOST1271',",1);ast.parse(text)
   p=ROOT/f'runner/fullview{tag}_{mode}_worker.py'
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
