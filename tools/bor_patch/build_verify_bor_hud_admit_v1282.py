"""Keep HUD producer admission on the ordinary path; authenticate before DMA."""
from pathlib import Path
import ast,fcntl,hashlib,os,shutil
from build_verify_bor_pin_slice_v1134 import symbols,off
from bor_linux_guard_v1132 import require_memory
ROOT=Path('/home/chad/bor-v1131-20261113');OLD=ROOT/'inputs/candidate-v1281';NEW=ROOT/'inputs/candidate-v1282'

def main():
 print('GUARDS',require_memory(True),'DISK',round(shutil.disk_usage(ROOT).free/2**30,3),'LOAD',os.getloadavg(),flush=True)
 assert shutil.disk_usage(ROOT).free>18*2**30 and os.getloadavg()[0]<os.cpu_count()
 with (ROOT/'bor-mesen.lock').open('r+b') as f:
  fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);assert not NEW.exists()
  s=symbols(OLD);raw=(OLD/'bor.sfc').read_bytes();rom=bytearray(raw);lo=off(s['Core_Dma_Enqueue'])
  matches=[i for i in range(lo,lo+24) if raw.startswith(b'\xc9\x04\x00',i)];assert len(matches)==1
  at=matches[0]+1;rom[at]=5
  c=sum(rom)&65535;rom[0x7fdc:0x7fe0]=(c^65535).to_bytes(2,'little')+c.to_bytes(2,'little');assert sum(rom)&65535==c
  assert all(x==y or i==at or 0x7fdc<=i<0x7fe0 for i,(x,y) in enumerate(zip(raw,rom)))
  NEW.mkdir();(NEW/'bor.sfc').write_bytes(rom)
  for name in ('main.sym','world.sym'):shutil.copyfile(OLD/name,NEW/name)
  import build_verify_bor_hud_dma_v1281 as dma
  dma.NEW=NEW;dma.verify(False)
  oldsha=hashlib.sha256(raw).hexdigest();newsha=hashlib.sha256(rom).hexdigest()
  for mode in ('early','full'):
   text=(ROOT/f'runner/huddma1281_{mode}_worker.py').read_text();assert text.count(oldsha)==1;text=text.replace(oldsha,newsha,1);ast.parse(text)
   p=ROOT/f'runner/hudadmit1282_{mode}_worker.py';assert not p.exists();p.write_text(text)
  print('BUILT one max-type immediate; original ordinary producer path/cost, existing types unchanged; exact type4 identity/owner/flags/length authentication still runs before first physical write',flush=True)
if __name__=='__main__':main()
