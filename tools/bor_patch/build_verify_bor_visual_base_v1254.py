"""Apply only the source-palette and HUD fixes to an isolated v903 ROM."""
from pathlib import Path
import ast,fcntl,hashlib,shutil,sys
from build_verify_bor_pin_slice_v1134 import symbols,cpu,regs,clean
from bor_linux_guard_v1132 import require_memory
ROOT=Path('/home/chad/bor-v1131-20261113');BASE=ROOT/'inputs/baseline';NEW=ROOT/'inputs/candidate-v1254'

def main():
 print('GUARDS',require_memory(True),flush=True);assert shutil.disk_usage(ROOT).free>18*2**30
 with (ROOT/'bor-mesen.lock').open('r+b') as lease:
  fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB);assert not NEW.exists()
  raw=(BASE/'bor.sfc').read_bytes()
  assert hashlib.sha256(raw).hexdigest()=='d657e710ea67af130a670c69a41c9fc52fb430cd877758ee361357d227a2a9b8'
  rom=bytearray(raw);allowed=set();names={}
  for before,after in [('candidate-v1246','candidate-v1249'),('candidate-v1249','candidate-v1250')]:
   a=ROOT/'inputs'/before;b=ROOT/'inputs'/after;old=(a/'bor.sfc').read_bytes();new=(b/'bor.sfc').read_bytes();assert len(old)==len(new)==len(rom)
   changed=[i for i,(x,y) in enumerate(zip(old,new)) if x!=y and not 0x7fdc<=i<0x7fe0]
   for i in changed:assert rom[i]==old[i],(before,hex(i),'base mismatch');rom[i]=new[i];allowed.add(i)
   sa=symbols(a);sb=symbols(b)
   for n,v in sb.items():
    if n not in sa:names[n]=v
   print('APPLIED_ISOLATED_DIFF',before,after,len(changed),'bytes',flush=True)
  c=sum(rom)&65535;rom[0x7fdc:0x7fe0]=(c^65535).to_bytes(2,'little')+c.to_bytes(2,'little');assert sum(rom)&65535==c
  assert all(a==b or i in allowed or 0x7fdc<=i<0x7fe0 for i,(a,b) in enumerate(zip(raw,rom)))
  base_sy=symbols(BASE);assert not any(n in base_sy for n in names)
  text=(BASE/'main.sym').read_text()
  for n,v in names.items():text+=f'\n{v>>16:02X}:{v&65535:04X} {n}'
  NEW.mkdir();(NEW/'bor.sfc').write_bytes(rom);(NEW/'main.sym').write_text(text+'\n');shutil.copyfile(BASE/'world.sym',NEW/'world.sym')
  # Both selected components must execute exactly like the already verified
  # v1250 versions. The baseline's other code, data and addresses are untouched.
  n=0
  for row in range(256):
   for status in (4,0xc5):
    pair=[]
    for folder in (ROOT/'inputs/candidate-v1250',NEW):
     q=cpu(folder);q.write(q.sy['Text_Row'],row,1);q.a=123;q.x=18;q.y=64;q.d=0xa85;q.p=status;q.run('Text_FlushRow',long=False);pair.append(q)
    assert regs(pair[0])==regs(pair[1]) and clean(pair[0])==clean(pair[1]),row;n+=1
  for mode in (0,1,2):
   for magic in (0,0xc04d):
    for slot in range(8):
     pair=[]
     for folder in (ROOT/'inputs/candidate-v1250',NEW):
      q=cpu(folder);s=q.sy;q.x=slot*8;q.write(s['Game_CampaignId'],3,1);q.write(s['SourceInput_Magic'],0x1a60);q.write(s['SourceVisual_CompletedMagic'],magic);q.write(0x7e1760,mode)
      at=s['DmaQueue']+slot*8;q.write(at+7,0x7e,1);q.write(at+5,0x2300);q.write(at+2,0x100+slot*32);q.run('SourceVisual_AllowCgramRequest');pair.append(q)
     assert regs(pair[0])==regs(pair[1]) and clean(pair[0])==clean(pair[1]);n+=1
  print('PASS',n,'linked exact palette/HUD component comparisons; remainder is exact v903 bytes',flush=True)
  h=hashlib.sha256((ROOT/'inputs/candidate-v1250/bor.sfc').read_bytes()).hexdigest()
  for tag in ('early','full'):
   text=(ROOT/'runner'/f'hud1250_{tag}_worker.py').read_text();assert text.count(h)==1;text=text.replace(h,hashlib.sha256(rom).hexdigest(),1);ast.parse(text)
   p=ROOT/'runner'/f'visual1254_{tag}_worker.py';assert not p.exists();p.write_text(text)

if __name__=='__main__':main()
