"""One authenticated HUD descriptor, two half-row physical VRAM transfers."""
from pathlib import Path
from types import MethodType
import ast,fcntl,hashlib,os,shutil,sys
from build_verify_bor_pin_slice_v1134 import cpu,symbols,off,regs
from bor_linux_guard_v1132 import require_memory
ROOT=Path('/home/chad/bor-v1131-20261113');OLD=ROOT/'inputs/candidate-v1271';NEW=ROOT/'inputs/candidate-v1281'
BODY=0x33ed00

def build():
 assert not NEW.exists();s=symbols(OLD);raw=(OLD/'bor.sfc').read_bytes();rom=bytearray(raw);patches=[]
 def patch(at,before,after):
  i=off(at);assert len(before)==len(after) and raw[i:i+len(before)]==before,(hex(at),before.hex())
  assert not any(i<j+n and j<i+len(after) for j,n in patches)
  rom[i:i+len(after)]=after;patches.append((i,len(after)))
 def find(name,length,before,after):
  lo=off(s[name]);hits=[i for i in range(lo,lo+length) if raw.startswith(before,i)];assert len(hits)==1,(name,before.hex())
  i=hits[0];at=(i//32768)<<16|0x8000+i%32768;patch(at,before,after);return at
 # Same builder/copy/dirty/pending code and64-byte immutable source per
 # player. Only constants change: first16 cells name, next16 cells bar.
 for name,length,before,after in [
  ('HudOpponent_Row__draw',12,b'\xa0\x18\x00',b'\xa0\x00\x00'),
  ('HudOpponent_Row__print',50,b'\xc0\x40\x00',b'\xc0\x20\x00'),
  ('HudOpponent_DrawBar',20,b'\x8f'+(s['HudOpponent_Work']+2).to_bytes(3,'little'),b'\x8f'+(s['HudOpponent_Work']+34).to_bytes(3,'little')),
  ('HudOpponent_DrawBar',20,b'\xa2\x04\x00',b'\xa2\x24\x00'),
  ('HudOpponent_DrawBar__tile',45,b'\xe0\x14\x00',b'\xe0\x34\x00'),
  ('HudOpponent_DrawBar__tile',45,b'\x8f'+(s['HudOpponent_Work']+20).to_bytes(3,'little'),b'\x8f'+(s['HudOpponent_Work']+52).to_bytes(3,'little')),
  ('HudOpponent_Row__copyloop',100,b'\xa9\x80\xd2',b'\xa9\x20\xd1'),
  ('HudOpponent_Row__p1addr',6,b'\xa9\x80\xd1',b'\xa9\x00\xd1'),
  ('HudOpponent_Row__address',45,b'\xa9\x00\x8f'+s['DmaRequest_TypeFlags'].to_bytes(3,'little'),b'\xa9\x04\x8f'+s['DmaRequest_TypeFlags'].to_bytes(3,'little'))]:find(name,length,before,after)
 error=b'\xf4'+s['Error_InvalidDmaTransferType'].to_bytes(2,'little')+b'\x20'+(s['Core_Error_Handler']&65535).to_bytes(2,'little')
 lo=off(s['Core_Dma_Enqueue']);hits=[i for i in range(lo,lo+32) if raw.startswith(error,i)];assert len(hits)==1
 enqueue_error=(hits[0]//32768)<<16|0x8000+hits[0]%32768
 queue_error=s['Core_Dma_ProcessQueue__bad_type'];assert raw[off(queue_error):off(queue_error)+8]==b'\xc2\x31'+error
 b=bytearray();labels={};fix=[]
 def e(op,v=None,n=2):
  b.append(op)
  if v is not None:b.extend(v.to_bytes(n,'little'))
 def lab(n):labels[n]=BODY+len(b)
 def lng(op,n):e(op,s[n] if isinstance(n,str) else n,3)
 def go(n):e(0x82);fix.append((len(b),n,2));b.extend(b'\0\0')
 def require_equal(n):e(0xf0,3,1);go(n)
 def br(op,n):e(op);fix.append((len(b),n,1));b.append(0)
 def error_exit(return_pc,normalize=True):
  if normalize:e(0xc2,0x31,1)
  e(0xf4,s['Error_InvalidDmaTransferType']);e(0xf4,return_pc&65535);lng(0x5c,'Core_Error_Handler')
 lab('HudDma1281Enqueue');e(0xc9,4);require_equal('HudDma1281EnqueueError')
 for name,val,mask in [('DmaRequest_Length',64,False),('DmaRequest_SourceBank',0x7e,True)]:
  lng(0xaf,name)
  if mask:e(0x29,255)
  e(0xc9,val);require_equal('HudDma1281EnqueueError')
 lng(0xaf,'DmaRequest_SourceAddrLow');e(0xc9,s['HudOpponent_Rows']&65535);br(0xf0,'HudDma1281EnqueueP1')
 e(0xc9,(s['HudOpponent_Rows']+64)&65535);require_equal('HudDma1281EnqueueError')
 lng(0xaf,'DmaRequest_TargetAddr');e(0xc9,0xd120);go('HudDma1281EnqueueTarget')
 lab('HudDma1281EnqueueP1');lng(0xaf,'DmaRequest_TargetAddr');e(0xc9,0xd100)
 lab('HudDma1281EnqueueTarget');require_equal('HudDma1281EnqueueError');e(0xa9,64);lng(0x5c,'Core_Dma_Enqueue__valid_length')
 lab('HudDma1281EnqueueError');error_exit(enqueue_error+5,False)
 lab('HudDma1281Queue');e(0xc2,0x31,1)
 for addr,val,mask in [(s['DmaQueue']+4,0x44,True),(s['DmaQueue'],64,False),(s['DmaQueue']+7,0x7e,True)]:
  lng(0xbf,addr)
  if mask:e(0x29,255)
  e(0xc9,val);require_equal('HudDma1281QueueError')
 e(0xda);e(0x8a);e(0x4a);e(0x4a);e(0x4a);e(0xaa);lng(0xbf,'DmaQueue_Owner');e(0x29,255);e(0xfa);e(0xc9,0);require_equal('HudDma1281QueueError')
 lng(0xbf,s['DmaQueue']+5);e(0xc9,s['HudOpponent_Rows']&65535);br(0xf0,'HudDma1281QueueP1')
 e(0xc9,(s['HudOpponent_Rows']+64)&65535);require_equal('HudDma1281QueueError')
 lng(0xbf,s['DmaQueue']+2);e(0xc9,0xd120);go('HudDma1281QueueTarget')
 lab('HudDma1281QueueP1');lng(0xbf,s['DmaQueue']+2);e(0xc9,0xd100)
 lab('HudDma1281QueueTarget');require_equal('HudDma1281QueueError')
 # The descriptor stays active across BOTH transfers. No staged source or
 # global request is mutated. Source auto-increment advances exactly32B.
 lng(0xbf,s['DmaQueue']+5);e(0x8d,0x4372)
 lng(0xbf,s['DmaQueue']+2);e(0x4a);e(0x8d,0x2116);e(0xa9,32);e(0x8d,0x4375)
 e(0xe2,0x20,1)
 for addr,val in ((0x2115,0x80),(0x4374,0x7e),(0x4370,1),(0x4371,0x18),(0x420b,0x80)):e(0xa9,val,1);e(0x8d,addr)
 e(0xc2,0x31,1);lng(0xbf,s['DmaQueue']+2);e(0x18);e(0x69,64);e(0x4a);e(0x8d,0x2116);e(0xa9,32);e(0x8d,0x4375)
 e(0xe2,0x20,1);e(0xa9,0x80,1);e(0x8d,0x420b);e(0xc2,0x31,1);lng(0x5c,'Core_Dma_ProcessQueue__next')
 lab('HudDma1281QueueError');error_exit(queue_error+7)
 lab('HudDma1281End')
 for at,name,width in fix:
  delta=labels[name]-(BODY+at+width);assert -(1<<(8*width-1))<=delta<(1<<(8*width-1)),(name,delta)
  b[at:at+width]=delta.to_bytes(width,'little',signed=True)
 assert not any(raw[off(BODY):off(BODY)+len(b)]) and not any(BODY<=v<BODY+len(b) for v in s.values())
 patch(enqueue_error,error,b'\x5c'+labels['HudDma1281Enqueue'].to_bytes(3,'little')+b'\xea'*2)
 patch(queue_error,b'\xc2\x31'+error,b'\x5c'+labels['HudDma1281Queue'].to_bytes(3,'little')+b'\xea'*4)
 patch(BODY,bytes(len(b)),b)
 c=sum(rom)&65535;rom[0x7fdc:0x7fe0]=(c^65535).to_bytes(2,'little')+c.to_bytes(2,'little');assert sum(rom)&65535==c
 assert all(x==y or any(i<=j<i+n for i,n in patches) or 0x7fdc<=j<0x7fe0 for j,(x,y) in enumerate(zip(raw,rom)))
 NEW.mkdir();(NEW/'bor.sfc').write_bytes(rom);shutil.copyfile(OLD/'world.sym',NEW/'world.sym');text=(OLD/'main.sym').read_text()
 for n,v in labels.items():text+=f'\n{v>>16:02X}:{v&65535:04X} {n}'
 (NEW/'main.sym').write_text(text+'\n');print('BUILT',len(b),'bytes; new type4 only via original error paths; existing0..3 dispatch/validator paths untouched; no new RAM',flush=True)

def verify(strict_admission=True):
 s=symbols(NEW);count=0
 def blob(q,at,n):return bytes(q.byte(at+i) for i in range(n))
 def fixture(player=0,hp=49):
  q=cpu(NEW);q.db=0;q.d=0xa00;q.p=0x24;q.s=0x1dff
  for n,v,w in [('Game_CampaignId',3,1),('G13_TwoPlayerEnabled',1,1),('HudOpponent_Player',player*2,2),('HudOpponent_BufferOffset',player*64,2),('HudOpponent_Dirty',0x0101,2)]:q.write(s[n],v,w)
  q.write(s['HudOpponent_Targets']+player*2,267);q.write(0x7e0a00+266+s['CHAR_HP'],hp,1);q.write(0x7e0a00+266+s['CHAR_ROSTER_INDEX'],2,1)
  original=q.write
  def write(self,at,v,n=2):
   if self.phys(at)!=0x420b:return original(at,v,n)
   assert v==128 and self.byte(0x4370)==1 and self.byte(0x4371)==24 and self.byte(0x2115)==128
   src=self.read(0x4372)|(self.byte(0x4374)<<16);size=self.read(0x4375);target=self.read(0x2116)*2
   assert size==32 and target in (0xd100,0xd120,0xd140,0xd160),(size,hex(target))
   slot=self.read(s['DmaQueue_CurrentSlot']);assert self.byte(s['DmaQueue']+slot+4)==0x44,'retired before both physical transfers'
   self.media.append((src,target,size))
   for i in range(size):self.m[0x800000+target+i]=self.byte(src+i)
   original(0x4372,(src+size)&65535);original(0x4375,0);original(0x2116,(target+size)//2)
  q.write=MethodType(write,q);return q
 def active(q):return [i for i in range(0,64,8) if q.byte(s['DmaQueue']+i+4)&64]
 for player in (0,1):
  for hp in (0,1,7,8,31,49,63,64,255):
   for cursor in range(0,64,8):
    q=fixture(player,hp);q.write(s['DmaQueue_CurrentSlot'],cursor);q.run('HudOpponent_Row',long=False)
    assert active(q)==[cursor] and q.read(s['DmaQueue_BudgetTotal'])==64
    base=s['HudOpponent_Rows']+player*64;target=0xd100+player*32;expected=blob(q,base,64)
    before=blob(q,s['HudOpponent_Rows'],128);q.write(0x7e0a00+266+s['CHAR_HP'],13,1);q.run('HudOpponent_Row',long=False);assert blob(q,s['HudOpponent_Rows'],128)==before
    q.run('Core_Dma_ProcessQueue',long=False);assert q.media==[(base,target,32),(base+32,target+64,32)]
    assert bytes(q.m.get(0x800000+target+i,0) for i in range(32))+bytes(q.m.get(0x800000+target+64+i,0) for i in range(32))==expected
    assert not active(q) and q.read(s['DmaQueue_BudgetTotal'])==0;count+=1
  for cursor in range(0,64,8):
   q=fixture(player);q.write(s['DmaQueue_CurrentSlot'],cursor)
   for i in range(0,64,8):q.write(s['DmaQueue']+i+4,0x40,1)
   q.run('HudOpponent_Row',long=False);assert q.byte(s['HudOpponent_Dirty']+player)==1
   q.write(s['DmaQueue']+cursor+4,0,1);q.run('HudOpponent_Row',long=False);assert q.byte(s['HudOpponent_Dirty']+player)==0 and q.read(s['DmaQueue']+cursor)==64;count+=1
 # New type rejects malformed identities at producer AND physical dispatch.
 for player in (0,1):
  for field,value in ((0,0),(0,32),(0,128),(2,0xd180),(2,0xd100+32*(1-player)),(5,0x5a12),(5,0x5a10+64*(1-player)),(7,0x7f),(4,0xc4),(4,0x64),(4,0x54)):
   q=fixture(player);q.run('HudOpponent_Row',long=False);q.write(s['DmaQueue']+field,value,1 if field in (4,7) else 2)
   assert q.run('Core_Dma_ProcessQueue',long=False)=='error' and not q.media;count+=1
  for owner in (1,6,255):
   q=fixture(player);q.run('HudOpponent_Row',long=False);q.write(s['DmaQueue_Owner'],owner,1)
   assert q.run('Core_Dma_ProcessQueue',long=False)=='error' and not q.media and q.byte(s['DmaQueue_Owner'])==owner;count+=1
 for player in (0,1):
  for field,value,width in [('DmaRequest_Length',0,2),('DmaRequest_Length',32,2),('DmaRequest_Length',128,2),('DmaRequest_SourceBank',0x7f,1),('DmaRequest_SourceAddrLow',0x5a12,2),('DmaRequest_TargetAddr',0xd180,2),('DmaRequest_TargetAddr',0xd100+32*(1-player),2)]:
   q=fixture(player)
   for n,v,w in [('DmaRequest_TypeFlags',4,1),('DmaRequest_Length',64,2),('DmaRequest_SourceBank',0x7e,1),('DmaRequest_SourceAddrLow',(s['HudOpponent_Rows']+64*player)&65535,2),('DmaRequest_TargetAddr',0xd100+32*player,2)]:q.write(s[n],v,w)
   q.write(s[field],value,width)
   outcome=q.run('Core_Dma_Enqueue',long=False)
   if strict_admission or (field=='DmaRequest_Length' and value==0):
    assert outcome=='error' and not active(q) and not q.media
   else:
    assert outcome!='error' and q.p&1 and len(active(q))==1
    assert q.run('Core_Dma_ProcessQueue',long=False)=='error' and not q.media
   count+=1
 # All preexisting request types and invalid values retain original behavior.
 for flags in range(256):
  if flags==4:continue
  a,b=cpu(OLD),cpu(NEW)
  for q in (a,b):
   q.write(s['DmaRequest_TypeFlags'],flags,1);q.write(s['DmaRequest_Length'],256)
  ra=a.run('Core_Dma_Enqueue',long=False);rb=b.run('Core_Dma_Enqueue',long=False)
  assert ra==rb and regs(a)==regs(b),(flags,ra,rb,regs(a),regs(b))
  assert a.m==b.m,(flags,'memory');count+=1
 print('PASS_HUD_DMA',count,'linked physical two-row, ring, pending immutable, full/retry, malformed descriptor/owner rejection, original type/flags equivalence; native timing not proved',flush=True)

def workers():
 oldsha=hashlib.sha256((OLD/'bor.sfc').read_bytes()).hexdigest();newsha=hashlib.sha256((NEW/'bor.sfc').read_bytes()).hexdigest()
 for mode in ('early','full'):
  text=(ROOT/f'runner/fullview1271_{mode}_worker.py').read_text();assert text.count(oldsha)==1;text=text.replace(oldsha,newsha,1);ast.parse(text)
  p=ROOT/f'runner/huddma1281_{mode}_worker.py';assert not p.exists();p.write_text(text)

def main():
 print('GUARDS',require_memory(True),'DISK',round(shutil.disk_usage(ROOT).free/2**30,3),'LOAD',os.getloadavg(),flush=True)
 assert shutil.disk_usage(ROOT).free>18*2**30 and os.getloadavg()[0]<os.cpu_count()
 with (ROOT/'bor-mesen.lock').open('r+b') as f:
  fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  if '--verify-only' not in sys.argv:build()
  verify();workers()
if __name__=='__main__':main()
