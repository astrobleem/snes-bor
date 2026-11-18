"""Use existing normal-stage palette initialization time for original HUD colors."""
from pathlib import Path
from types import MethodType
import ast,fcntl,hashlib,os,shutil,sys
from build_verify_bor_pin_slice_v1134 import symbols,off,cpu,regs,clean
from bor_linux_guard_v1132 import require_memory
ROOT=Path('/home/chad/bor-v1131-20261113');OLD=ROOT/'inputs/candidate-v1282';NEW=ROOT/'inputs/candidate-v1292';BODY=0x33f800

def main():
 print('GUARDS',require_memory(True),'DISK',round(shutil.disk_usage(ROOT).free/2**30,3),flush=True)
 assert shutil.disk_usage(ROOT).free>18*2**30 and os.getloadavg()[0]<os.cpu_count()
 with (ROOT/'bor-mesen.lock').open('r+b') as lease:
  fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB);verify='--verify-only' in sys.argv
  assert NEW.exists() if verify else not NEW.exists()
  s=symbols(OLD);raw=(OLD/'bor.sfc').read_bytes();rom=bytearray(raw)
  entry=s['StageFp_BG2BootLoad__palette_skip']-3;resume=s['StageFp_BG2BootLoad__palette']+11
  expected=bytes.fromhex('a20800af012000cad0f9a9048f212100a21800af0120008f222100cad0f5')
  assert raw[off(entry):off(resume)]==expected,(raw[off(entry):off(resume)].hex(),expected.hex())
  assert entry>>16<0x40 and BODY>>16<0x40
  for loop,end in [(entry+3,entry+10),(s['StageFp_BG2BootLoad__palette'],resume)]:
   assert loop>>8==(end-1)>>8,'Account for branch page crossing before changing timing'
  body=bytearray();read=bytes.fromhex('af012000');write=bytes.fromhex('8f222100')
  body+=read*8
  for at,value in [(0x2121,1),(0x2122,0xff),(0x2122,0x22),(0x2121,3),(0x2122,0xff),(0x2122,0x7b)]:
   body+=bytes([0xa9,value,0x8f])+at.to_bytes(3,'little')
  body+=bytes.fromhex('a9048f212100')+(read+write)*24
  # All ROM accesses here are slow LoROM(8 clocks), MMIO is6, internal6.
  # Original: LDX8 +8*(LDA.l/DEX/BNE) +LDA4/STA.l/LDX24
  #           +24*(LDA.l/STA.l/DEX/BNE) =3370 master clocks.
  original_clocks=24+(8*(38+14)+7*22+16)+(16+38+24)+(24*(38+38+14)+23*22+16)
  new_without_padding=32+8*38+6*(16+38)+(16+38)+24*(38+38)+24+32
  assert original_clocks==3370 and new_without_padding==2594
  body+=b'\xea'*46+bytes.fromhex('8000')*6
  assert new_without_padding+46*14+6*22==original_clocks
  # Final LDX0 restores the same flags/X as the original last DEX; carry
  # and A's high byte are untouched. All32 MSU reads still occur in order.
  body+=bytes.fromhex('a20000')+b'\x5c'+resume.to_bytes(3,'little')
  assert not any(raw[off(BODY):off(BODY)+len(body)]) and not any(BODY<=v<BODY+len(body) for v in s.values())
  rom[off(entry):off(entry)+7]=b'\x5c'+BODY.to_bytes(3,'little')+b'\xea'*3
  rom[off(BODY):off(BODY)+len(body)]=body
  checksum=sum(rom)&65535;rom[0x7fdc:0x7fe0]=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
  assert sum(rom)&65535==checksum
  spans=[(off(entry),7),(off(BODY),len(body)),(0x7fdc,4)]
  assert all(a==b or any(p<=i<p+n for p,n in spans) for i,(a,b) in enumerate(zip(raw,rom)))
  text=(OLD/'main.sym').read_text()+f'\n33:F800 OriginalBar1292\n{entry>>16:02X}:{entry&65535:04X} OriginalBar1292Entry\n{resume>>16:02X}:{resume&65535:04X} OriginalBar1292Resume\n'
  if verify:assert (NEW/'bor.sfc').read_bytes()==rom and (NEW/'main.sym').read_text()==text
  else:
   NEW.mkdir();(NEW/'bor.sfc').write_bytes(rom);(NEW/'main.sym').write_text(text);shutil.copyfile(OLD/'world.sym',NEW/'world.sym')
  count=0
  for seed in range(16):
   for db in (0,0x7e):
    for carry in (0,1):
     pair=[];stream=bytes((i*17+seed*23)&255 for i in range(32));initial=bytes((i*11+seed)&255 for i in range(32))
     for folder,name in [(OLD,'OriginalBar1292BaselineEntry'),(NEW,'OriginalBar1292')]:
      q=cpu(folder);q.sy['OriginalBar1292BaselineEntry']=entry;q.p=0x24|carry;q.db=db;q.x=34;q.y=39;q.d=0xa85;q.a=0xab77
      state={'read':0,'cgaddr':0,'palette':bytearray(initial)};get=q.read;put=q.write
      def reader(self,at,n=2,get=get,state=state):
       if self.phys(at)==0x2001:
        assert n==1 and state['read']<32
        v=stream[state['read']];state['read']+=1;return v
       return get(at,n)
      def writer(self,at,v,n=2,put=put,state=state):
       if self.phys(at)==0x2121:assert n==1;state['cgaddr']=(v&255)*2
       if self.phys(at)==0x2122:
        assert n==1;state['palette'][state['cgaddr']]=v&255;state['cgaddr']+=1
       return put(at,v,n)
      q.read=MethodType(reader,q);q.write=MethodType(writer,q);q.run(name,stop=resume);pair.append((q,state))
     (a,sa),(b,sb)=pair
     assert regs(a)==regs(b) and clean(a)==clean(b) and not a.media and not b.media
     assert sa['read']==sb['read']==32 and sa['cgaddr']==sb['cgaddr']==32
     expected=bytearray(initial);expected[8:]=stream[8:];assert sa['palette']==expected
     expected[2:4]=bytes.fromhex('ff22');expected[6:8]=bytes.fromhex('ff7b');assert sb['palette']==expected
     count+=1
  import build_verify_bor_hud_dma_v1281 as dma
  dma.NEW=NEW;dma.verify(False)
  oldsha=hashlib.sha256(raw).hexdigest();newsha=hashlib.sha256(rom).hexdigest()
  for mode in ('early','full'):
   src=(ROOT/f'runner/hudadmit1282_{mode}_worker.py').read_text();assert src.count(oldsha)==1
   src=src.replace(oldsha,newsha,1);ast.parse(src);p=ROOT/f'runner/referencebar1292_{mode}_worker.py';assert not p.exists();p.write_text(src)
  print('PASS_REFERENCE_BUDGET',count,'MSU stream/CGRAM/ABI/queue cases;',len(body),'bytes; static3370 master clocks, native timing and original pixels still require verification',flush=True)

if __name__=='__main__':main()
