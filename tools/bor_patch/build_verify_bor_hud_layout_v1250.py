"""Top-aligned, disjoint two-player HUD spans derived from original BOR layout."""
from pathlib import Path
import ast,fcntl,hashlib,shutil,sys
from build_verify_bor_pin_slice_v1134 import symbols,off,cpu,regs,clean
from bor_linux_guard_v1132 import require_memory

ROOT=Path('/home/chad/bor-v1131-20261113');OLD=ROOT/'inputs/candidate-v1249';NEW=ROOT/'inputs/candidate-v1250';BODY=0x33e400
LAYOUT={0x81:(0xd000,32),0x82:(0xd040,22),0x88:(0xd020,32),0x89:(0xd068,24)}

def main():
 print('GUARDS',require_memory(True),flush=True);assert shutil.disk_usage(ROOT).free>18*2**30
 with (ROOT/'bor-mesen.lock').open('r+b') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);verify_only='--verify-only' in sys.argv
  assert NEW.exists() if verify_only else not NEW.exists()
  s=symbols(OLD);raw=(OLD/'bor.sfc').read_bytes();rom=bytearray(raw);changed=[];labels={};body=bytearray()
  def patch(at,before,after):
   assert len(before)==len(after) and raw[off(at):off(at)+len(before)]==before,(hex(at),before.hex())
   rom[off(at):off(at)+len(before)]=after;changed.append((off(at),len(before)))
  def findpatch(name,size,before,after):
   a=off(s[name]);i=raw.find(before,a,a+size);assert i>=0 and raw.find(before,i+1,a+size)<0,(name,before.hex())
   at=(s[name]&0xff0000)|0x8000|(i%32768);patch(at,before,after);return at
  # Bar staging remains independently owned; only transfer spans and destinations change.
  for name,oldtarget,newtarget,draw,offset in [('Hud_Play__bar_rebuild',0xd000,0xd080,'Hud_DrawBar',2),('Hud_Play__2p_bar',0xd1c0,0xd0a0,'Hud_Play__2p_drawbar',6)]:
   findpatch(name,100,b'\xa9'+oldtarget.to_bytes(2,'little')+b'\x8f'+s['DmaRequest_TargetAddr'].to_bytes(3,'little'),b'\xa9'+newtarget.to_bytes(2,'little')+b'\x8f'+s['DmaRequest_TargetAddr'].to_bytes(3,'little'))
   findpatch(name,100,b'\xa9\x40\x00\x8f'+s['DmaRequest_Length'].to_bytes(3,'little'),b'\xa9\x20\x00\x8f'+s['DmaRequest_Length'].to_bytes(3,'little'))
   # Both drawbar routines increment X by2 before their left cap.
   needle=b'\xa2\x00\x00\x20'+(s[draw]&65535).to_bytes(2,'little')
   findpatch(name,100,needle,b'\xa2'+offset.to_bytes(2,'little')+needle[3:])
  # Text row buffers keep their original lifetime and content. Each HUD writer
  # uploads only its own rectangle, so P2 cannot erase P1 or the central timer.
  # Tag only these four HUD call sites; ordinary title/pause/selection rows
  # with the same numbers MUST retain their full-width original destinations.
  for name,row,label,rep in [('Hud_Play__text_banked_score_changed',1,'Text_Str_HudScore',False),('Hud_Play__text_banked_check_lives',2,'Text_Str_HudLives',False),('Hud_Play__2p_text_score_changed',8,'Text_Str_HudP2Score',True),('Hud_Play__2p_text_lives',9,'Text_Str_HudP2Lives',True)]:
   suffix=(b'\xc2\x10' if rep else b'')+b'\xa2\x00\x00\xa0'+((s[label]-s['Text_StringPool'])&65535).to_bytes(2,'little')
   findpatch(name,85,b'\xa9'+bytes([row])+suffix,b'\xa9'+bytes([row|128])+suffix)
  textprefix=b'\xa9\x40\x00\x8f'+s['DmaRequest_Length'].to_bytes(3,'little')
  a=raw.find(textprefix,off(s['Text_FlushRow']),off(s['Text_FlushRow'])+60);assert a>=0
  hook=0x8000|(a%32768);labels['HudLayout1250_Text']=BODY
  body+=bytes.fromhex('08c230af')+s['Text_Row'].to_bytes(3,'little')+bytes.fromhex('29ff00')
  jumps=[]
  for row in LAYOUT:
   body+=b'\xc9'+row.to_bytes(2,'little')+b'\xd0\x04\x5c';jumps.append((len(body),row));body+=b'\0'*3
  body+=b'\x28'+textprefix+b'\x5c'+(hook+7).to_bytes(3,'little')
  for at,row in jumps:
   body[at:at+3]=(BODY+len(body)).to_bytes(3,'little');target,length=LAYOUT[row]
   body+=b'\xa9'+target.to_bytes(2,'little')+b'\x8f'+s['DmaRequest_TargetAddr'].to_bytes(3,'little')+b'\x28\xa9'+length.to_bytes(2,'little')+b'\x8f'+s['DmaRequest_Length'].to_bytes(3,'little')+b'\x5c'+(hook+7).to_bytes(3,'little')
  labels['HudLayout1250_TextResume']=hook+7;patch(hook,textprefix,b'\x5c'+BODY.to_bytes(3,'little')+b'\xea'*3)
  # Immutable score fast rows use the exact same physical rectangles.
  for name,old,new in [('SourceScoreRom_MapP1',0xd040,0xd000),('SourceScoreRom_MapP2',0xd200,0xd020)]:
   findpatch(name,14,b'\xa9'+old.to_bytes(2,'little'),b'\xa9'+new.to_bytes(2,'little'))
  findpatch('SourceScoreRom_Request',16,b'\xa9\x40\x00',b'\xa9\x20\x00')
  # Queue-full retry recognition follows the new physical ranges, preserving
  # all existing dirty flags/cache invalidation without touching successful ACKs.
  for name,old,new in [('HudTextRetry_P2Bar',0xd1c0,0xd0a0),('HudRetryFailure_P1',0xd000,0xd080)]:
   findpatch(name,10,b'\xc9'+old.to_bytes(2,'little'),b'\xc9'+new.to_bytes(2,'little'))
  for old,new in ((0xd040,0xd000),(0xd080,0xd040),(0xd200,0xd020),(0xd240,0xd068)):
   findpatch('HudTextRetry_SourceReady',35,b'\xc9'+old.to_bytes(2,'little'),b'\xc9'+new.to_bytes(2,'little'))
  retry=b'\xaf'+s['DmaRequest_Length'].to_bytes(3,'little')+b'\xc9\x40\x00'
  a=raw.find(retry,off(s['HudRetryFailure_QueueFull']),off(s['HudRetryFailure_QueueFull'])+40);assert a>=0
  rh=0x270000|0x8000|(a%32768);entry=BODY+len(body);labels['HudLayout1250_Retry']=entry
  body+=b'\xaf'+s['DmaRequest_Length'].to_bytes(3,'little')
  for length in (32,22,24):body+=b'\xc9'+length.to_bytes(2,'little')+b'\xd0\x04\x5c'+(rh+7).to_bytes(3,'little')
  body+=b'\xc9\x40\x00\x5c'+(rh+7).to_bytes(3,'little');labels['HudLayout1250_RetryResume']=rh+7
  patch(rh,retry,b'\x5c'+entry.to_bytes(3,'little')+b'\xea'*3)
  # The original timer is two digits at top center. Retain the existing
  # immutable18-byte ownership/retry slot, using padding instead of TIME text.
  for name,opcode in [('StageTimerHost_QueueRow',0xa9),('StageTimerHost_DrawTimer__pending',0xc9)]:findpatch(name,30,bytes([opcode,0xd6,0xd2]),bytes([opcode,0x56,0xd0]))
  for count in range(100):
   at=s['StageTimerHost_TimerRows']+count*18;old=raw[off(at):off(at)+18]
   assert old[:10]==bytes.fromhex('542549254d2545252025')
   new=b'\x20\x25'*4+old[10:14]+b'\x20\x25'*3;patch(at,old,new)
  assert not any(raw[off(BODY):off(BODY)+len(body)]) and not any(BODY<=v<BODY+len(body) for v in s.values())
  rom[off(BODY):off(BODY)+len(body)]=body;changed.append((off(BODY),len(body)))
  c=sum(rom)&65535;rom[0x7fdc:0x7fe0]=(c^65535).to_bytes(2,'little')+c.to_bytes(2,'little');changed.append((0x7fdc,4));assert sum(rom)&65535==c
  assert all(a==b or any(at<=i<at+length for at,length in changed) for i,(a,b) in enumerate(zip(raw,rom)))
  text=(OLD/'main.sym').read_text()
  for n,v in labels.items():text+=f'\n{v>>16:02X}:{v&65535:04X} {n}'
  if verify_only:assert (NEW/'bor.sfc').read_bytes()==rom and (NEW/'main.sym').read_text()==text+'\n'
  else:
   NEW.mkdir();(NEW/'bor.sfc').write_bytes(rom);shutil.copyfile(OLD/'world.sym',NEW/'world.sym');(NEW/'main.sym').write_text(text+'\n')
  n=0
  for row in range(256):
   for carry in (0,1):
    q=cpu(NEW);q.a=123;q.x=15;q.y=17;q.d=0xa85;q.p=0xc4|carry
    q.write(s['Text_Row'],row,1);q.write(s['DmaRequest_TargetAddr'],0xd000+row*64);before=clean(q);initial=regs(q)
    q.run('HudLayout1250_Text',stop=labels['HudLayout1250_TextResume'])
    target,length=LAYOUT.get(row,((0xd000+row*64)&65535,64));assert q.read(s['DmaRequest_TargetAddr'])==target and q.read(s['DmaRequest_Length'])==length,(row,hex(q.read(s['DmaRequest_TargetAddr'])),target,length)
    assert q.x==initial[1] and q.y==initial[2] and q.d==initial[4] and q.s==initial[-1]-3 and (q.p&1)==carry
    after=clean(q)
    for at in (s['DmaRequest_TargetAddr'],s['DmaRequest_Length']):
     for d in (0,1):after.pop(at+d,None);before.pop(at+d,None)
    assert after==before and not q.media;n+=1
  for length in (0,18,22,24,31,32,33,64,65,256):
   q=cpu(NEW);q.write(s['DmaRequest_Length'],length);q.run('HudLayout1250_Retry',stop=labels['HudLayout1250_RetryResume']);assert bool(q.p&2)==(length in (22,24,32,64));n+=1
  spans=[(0xd000,32),(0xd020,32),(0xd040,22),(0xd056,18),(0xd068,24),(0xd080,32),(0xd0a0,32)]
  assert all(a+size<=b or b+other<=a for i,(a,size) in enumerate(spans) for b,other in spans[i+1:])
  print('PASS',n,'linked row/retry cases; seven physical spans disjoint; source buffers and queue ownership unchanged; source timer digits retained',flush=True)
  for tag in ('early','full'):
   text=(ROOT/'runner'/f'palette1249_{tag}_worker.py').read_text();old=hashlib.sha256(raw).hexdigest();new=hashlib.sha256(rom).hexdigest();assert text.count(old)==1;text=text.replace(old,new,1);ast.parse(text)
   out=ROOT/'runner'/f'hud1250_{tag}_worker.py';assert not out.exists();out.write_text(text)
  print('BUILT',len(body),'helper bytes, isolated HUD candidate; requires actual screenshot/control/PPU qualification',flush=True)

if __name__=='__main__':main()
