"""Preserve the original row-preparation budget while aligning target origins."""
from pathlib import Path
import ast,fcntl,hashlib,os,shutil
from build_verify_bor_pin_slice_v1134 import symbols,off,cpu,regs
from bor_linux_guard_v1132 import require_memory
ROOT=Path('/home/chad/bor-v1131-20261113');OLD=ROOT/'inputs/candidate-v1292';NEW=ROOT/'inputs/candidate-v1297r2';BODY=0x33fa00

def main():
 print('GUARDS',require_memory(True),'DISK',round(shutil.disk_usage(ROOT).free/2**30,3),flush=True)
 assert shutil.disk_usage(ROOT).free>18*2**30 and os.getloadavg()[0]<os.cpu_count()
 with (ROOT/'bor-mesen.lock').open('r+b') as lease:
  fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB);assert not NEW.exists()
  s=symbols(OLD);raw=(OLD/'bor.sfc').read_bytes();rom=bytearray(raw);b=bytearray();labels={};fix=[]
  def e(op,v=None,n=2):
   b.append(op)
   if v is not None:b.extend(v.to_bytes(n,'little'))
  def lng(op,n):e(op,s[n] if isinstance(n,str) else n,3)
  def lab(n):labels[n]=BODY+len(b)
  def br(op,n):e(op);fix.append((len(b),n));b.append(0)
  lab('OpponentAlign1297r2');e(0xc2,0x30,1)
  lng(0xaf,'HudOpponent_Player');e(0x0a);e(0x18);e(0x69,36);e(0xaa)
  e(0xa9,0x200a);lng(0x9f,'HudOpponent_Work')
  # Eliminate the eight loop-control groups, retaining all health arithmetic
  # and all eight ordered tile writes. X remains the player's left origin.
  for i in range(8):
   lng(0xaf,'HudOpponent_Hp');e(0x29,255);e(0xc9,8);br(0x90,f'Partial{i}')
   e(0x38);e(0xe9,8);lng(0x8f,'HudOpponent_Hp');e(0xa9,8);br(0x80,f'Tile{i}')
   lab(f'Partial{i}');e(0x48);e(0xa9,0);lng(0x8f,'HudOpponent_Hp');e(0x68)
   lab(f'Tile{i}');e(0x18);e(0x69,1);e(0x09,0x2000);lng(0x9f,s['HudOpponent_Work']+2+i*2)
  e(0xa9,0x200b);lng(0x9f,s['HudOpponent_Work']+18)
  e(0x8a);e(0x38);e(0xe9,32);e(0xa8)
  e(0xa9,0x200b);e(0x38);e(0xa2,52)
  # Native-mode slow-ROM/WRAM bus accounting: old call/loop overhead888
  # clocks; this path472. Preserve its budget with416 clocks, not new work.
  for _ in range(25):e(0xea)
  for _ in range(3):e(0x80,0,1)
  lng(0x5c,'HudOpponent_Row__char')
  for at,n in fix:
   delta=labels[n]-(BODY+at+1);assert -128<=delta<128;b[at]=delta&255
  hook=s['HudOpponent_Row__draw'];expected=b'\x20'+(s['HudOpponent_DrawBar']&65535).to_bytes(2,'little')+b'\xa0\x00\x00'
  assert raw[off(hook):off(hook)+6]==expected
  assert not any(raw[off(BODY):off(BODY)+len(b)]) and not any(BODY<=v<BODY+len(b) for v in s.values())
  rom[off(hook):off(hook)+6]=b'\x5c'+BODY.to_bytes(3,'little')+b'\xea'*2
  rom[off(BODY):off(BODY)+len(b)]=b
  c=sum(rom)&65535;rom[0x7fdc:0x7fe0]=(c^65535).to_bytes(2,'little')+c.to_bytes(2,'little');assert sum(rom)&65535==c
  assert all(a==z or off(hook)<=i<off(hook)+6 or off(BODY)<=i<off(BODY)+len(b) or 0x7fdc<=i<0x7fe0 for i,(a,z) in enumerate(zip(raw,rom)))
  NEW.mkdir();(NEW/'bor.sfc').write_bytes(rom);shutil.copyfile(OLD/'world.sym',NEW/'world.sym')
  text=(OLD/'main.sym').read_text()+''.join(f'\n{v>>16:02X}:{v&65535:04X} {n}' for n,v in labels.items())+'\n';(NEW/'main.sym').write_text(text)
  verify_clock_budget(OLD,NEW)
  cases=0
  for player in (0,1):
   for hp in (0,1,7,8,31,49,63,64,255):
    for model in (0,2,3,22,23,24,25,255):
     pair=[]
     for product in (OLD,NEW):
      q=cpu(product);q.db=0;q.d=0xa00;q.p=0x24;q.s=0x1dff
      for n,v,w in [('Game_CampaignId',3,1),('G13_TwoPlayerEnabled',1,1),('HudOpponent_Player',player*2,2),('HudOpponent_BufferOffset',player*64,2),('HudOpponent_Dirty',0x101,2)]:q.write(s[n],v,w)
      q.write(s['HudOpponent_Targets']+player*2,267)
      q.write(0x7e0a00+266+s['CHAR_HP'],hp,1);q.write(0x7e0a00+266+s['CHAR_ROSTER_INDEX'],model,1)
      q.run('HudOpponent_Row',long=False);pair.append(q)
     a,z=pair;base=s['HudOpponent_Rows']+player*64
     old=bytes(a.byte(base+i) for i in range(64));got=bytes(z.byte(base+i) for i in range(64))
     shift=4+player*4;expected=bytearray(64)
     expected[shift:32]=old[:32-shift]
     expected[32+shift:32+shift+20]=old[34:54]
     assert got==expected,(player,hp,model,got.hex(),expected.hex())
     for at,size in [(s['DmaQueue'],64),(s['DmaQueue_BudgetTotal'],2),(s['HudOpponent_Targets'],6),(s['HudOpponent_Rows']+(1-player)*64,64)]:
      assert bytes(a.byte(at+i) for i in range(size))==bytes(z.byte(at+i) for i in range(size))
     assert a.media==z.media==[];cases+=1
  import build_verify_bor_hud_dma_v1281 as dma
  dma.NEW=NEW;dma.verify(False)
  oldsha=hashlib.sha256(raw).hexdigest();newsha=hashlib.sha256(rom).hexdigest()
  for mode in ('early','full'):
   text=(ROOT/f'runner/referencebar1292_{mode}_worker.py').read_text();assert text.count(oldsha)==1;text=text.replace(oldsha,newsha,1)
   # CHAR_HP_MAX is a constant, not an actor byte offset. Preserve historical
   # captures; future observations explicitly distinguish this from maxhealth.
   bad="hp_max=row[sym['CHAR_HP_MAX']]"
   assert text.count(bad)==1;text=text.replace(bad,"port_full_health_constant=sym['CHAR_HP_MAX']",1)
   ast.parse(text);p=ROOT/f'runner/opponentalign1297r2_{mode}_worker.py';assert not p.exists();p.write_text(text)
  print('PASS_REFERENCE_BUDGETED_ALIGNMENT',cases,'row pixel-origin cases plus457 physical ownership cases;',len(b),'bytes; no new RAM/queue changes. Vertical layout, portraits, font spacing and source maxhealth remain open.',flush=True)

def verify_clock_budget(old,new):
 from types import MethodType
 # Native-mode master clocks: slow ROM8, WRAM8, internal6. No DMA/NMI is
 # modeled here; real preemption and physical PPU still require gameplay.
 costs={0x20:46,0x60:42,0x5c:32,0xc2:22,0xa9:24,0xa2:24,0xa0:24,
        0xaf:48,0x8f:48,0x9f:48,0x29:24,0xc9:24,0xe9:24,0x69:24,
        0x09:24,0x38:14,0x18:14,0x48:30,0x68:36,0xe8:14,0xe0:24,
        0x0a:14,0xaa:14,0x8a:14,0xa8:14,0xea:14}
 totals=set();cases=0
 for player in (0,2):
  for hp in range(256):
   runs=[]
   for product in (old,new):
    q=cpu(product);q.sy=dict(q.sy);s=q.sy;q.p=4;q.db=0;q.d=0xa00;q.s=0x1dff
    q.write(s['HudOpponent_Player'],player);q.write(s['HudOpponent_Hp'],hp)
    trace=[];get=q.fetch;last=[-1]
    def fetch(self,n=1):
     if self.steps!=last[0]:
      last[0]=self.steps;trace.append((self.pc,self.byte(self.pc),self.p))
     return get(n)
    q.fetch=MethodType(fetch,q)
    q.run('HudOpponent_Row__draw',long=False,stop=s['HudOpponent_Row__char'])
    clocks=0
    for i,(pc,op,p) in enumerate(trace):
     assert not p&0x30,('WIDTH',hex(pc),p)
     if op in (0x90,0x80):
      nxt=trace[i+1][0] if i+1<len(trace) else q.pc
      clocks+=22 if op==0x80 or nxt!=pc+2 else 16
     else:clocks+=costs[op]
    runs.append((q,clocks))
   (a,ca),(b,cb)=runs
   assert ca==cb,(player,hp,ca,cb)
   assert a.a==b.a==0x200b and a.x==b.x==52 and a.s==b.s
   assert a.y==0 and b.y==4+player*2 and (a.p&1)==(b.p&1)==1
   assert a.p^b.p==2  # intended nonzero name offset; next LDA overwrites NZ
   assert a.read(a.sy['HudOpponent_Hp'])==b.read(b.sy['HudOpponent_Hp'])
   assert not a.media and not b.media
   totals.add(ca);cases+=1
 print('PASS_EXACT_ROW_BUDGET',cases,'all byte HP/player cases; clocks',sorted(totals),
       'source arithmetic and completed-row budget preserved; native NMI timing unproven',flush=True)


if __name__=='__main__':main()
