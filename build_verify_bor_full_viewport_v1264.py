"""Isolated full-width BG1 window; no instruction, control or DMA cost changes."""
from pathlib import Path
import ast,fcntl,hashlib,os,shutil,sys
from build_verify_bor_pin_slice_v1134 import cpu,symbols,off,regs,clean
from bor_linux_guard_v1132 import require_memory
ROOT=Path('/home/chad/bor-v1131-20261113');OLD=ROOT/'inputs/candidate-v1254';NEW=ROOT/'inputs/candidate-v1264'
PATTERN=bytes.fromhex('a9038d2321a9108d2621a9ef8d2721a9018d2e21')

def build():
 assert not NEW.exists();raw=(OLD/'bor.sfc').read_bytes();assert raw.count(PATTERN)==1;at=raw.index(PATTERN);rom=bytearray(raw)
 rom[at+6]=0;rom[at+11]=255
 c=sum(rom)&65535;rom[0x7fdc:0x7fe0]=(c^65535).to_bytes(2,'little')+c.to_bytes(2,'little');assert sum(rom)&65535==c
 assert all(a==b or i in (at+6,at+11) or 0x7fdc<=i<0x7fe0 for i,(a,b) in enumerate(zip(raw,rom)))
 address=((at//32768)<<16)|(32768+at%32768)
 NEW.mkdir();(NEW/'bor.sfc').write_bytes(rom);shutil.copyfile(OLD/'world.sym',NEW/'world.sym')
 (NEW/'main.sym').write_text((OLD/'main.sym').read_text()+f'\n{address>>16:02X}:{address&65535:04X} FullViewport1264\n')
 print('BUILT two existing WH0/WH1 immediates 16..239 -> 0..255; unchanged instruction layout and final flags; no runtime scheduling changes',flush=True)

def verify():
 raw=(OLD/'bor.sfc').read_bytes();at=raw.index(PATTERN);address=((at//32768)<<16)|(32768+at%32768);count=0
 for status in range(256):
  for db in (0,0x80):
   pair=[]
   for p in (OLD,NEW):
    q=cpu(p);q.sy['FullViewport1264']=address;q.p=status|32;q.db=db;q.run('FullViewport1264',stop=address+len(PATTERN));pair.append(q)
   a,b=pair;assert regs(a)==regs(b) and a.steps==b.steps==8
   oldmem,newmem=clean(a),clean(b);allowed={(db<<16)+0x2126,(db<<16)+0x2127}
   assert all(k in allowed for k in oldmem.keys()|newmem.keys() if oldmem.get(k)!=newmem.get(k))
   assert a.writes==b.writes and [b.byte(k) for k in sorted(allowed)]==[0,255]
   count+=1
 print('PASS_WINDOW',count,'linked width/status/bank cases; only two hardware window values differ; native BG/scroll checks required',flush=True)

def workers():
 oldsha=hashlib.sha256((OLD/'bor.sfc').read_bytes()).hexdigest();newsha=hashlib.sha256((NEW/'bor.sfc').read_bytes()).hexdigest()
 lua='''\nlocal view1264seen={}
emu.addEventCallback(function()
 if (borOrdinal==355 or borOrdinal==968) and not view1264seen[borOrdinal] then
  view1264seen[borOrdinal]=true;local q=emu.getState();local fields={}
  for k,v in pairs(q) do if string.find(string.lower(k),'window',1,true) and (type(v)=='number' or type(v)=='boolean') then fields[#fields+1]=k..'='..tostring(v) end end
  table.sort(fields);print('BORVIEW1264|'..borOrdinal..'|'..table.concat(fields,','))
 end
end,emu.eventType.endFrame)
'''
 assert 'emu.write' not in lua
 for mode in ('early','full'):
  text=(ROOT/f'runner/visual1254_{mode}_worker.py').read_text();assert text.count(oldsha)==1;text=text.replace(oldsha,newsha,1)
  f=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='observer_source');old=ast.literal_eval(f.body[0].value)
  text=text.replace(repr(old),repr(old+lua),1).replace('line.startswith((' ,"line.startswith((b'BORVIEW1264',",1);ast.parse(text)
  p=ROOT/f'runner/fullview1264_{mode}_worker.py'
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
