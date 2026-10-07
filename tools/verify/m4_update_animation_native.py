"""Timed animation over actual actor state; pending frame services stay pending."""
import argparse, hashlib, json, struct
from pathlib import Path
from compiler import Source
from source_animation_step import derive as timing, pack as pack_timing, Animation, decide, validate_update_frame_pairing
from source_frame_effects_4086 import derive as effects, pack as pack_effects
from source_update_animation_inputs import derive as inputs, pack as pack_inputs
from m4_target_metadata_native import LUA as BASE
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_attack_finish_native import FRAMEZERO_SETUP

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('rom','source','output'):p.add_argument('--'+key,type=Path,required=True)
 p.add_argument('--guards',action='store_true');p.add_argument('--complete-frame',action='store_true');p.add_argument('--kill',action='store_true');p.add_argument('--resume-guards',action='store_true');a=p.parse_args();a.complete_frame=a.complete_frame or a.resume_guards;a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 source=Source(a.source);tr=timing(source);tt=pack_timing(tr);er=effects(source);fe=pack_effects(er);validate_update_frame_pairing(tt,fe);up=pack_inputs(inputs(source));rows=[]
 for an in tr['animations']:
  rule=Animation(an['count'],an['loop_mode'],an['loop_min'],an['loop_max'])
  for frame in sorted({0,an['count']-1}):
   for direction in (-1,0,1):
    for equal in (0,1):
     action,result=decide(rule,frame,direction,0xffffffff if equal else 0xfffeffff,0xffffffff)
     slot=(0,1,95,96,127)[len(rows)%5];model=er['models'].index(an['model'])
     rows.append(dict(slot=slot,model=model,count=128,time=0xffffffff,frame=frame,direction=direction,equal=equal,handle=an['handle'],delay=an['delays'][result],action=action,result=result,bad='',fault=0,entities=[dict(slot=slot,model=model,handle=an['handle'],frame=frame,exists=1,type=0,hostile=1,dead=0,invincible=0,detect=-1,hide=-1)]))
 if a.guards:
  seed=next(c for c in rows if c['action']==2);rows=[]
  for slot in (0,1,95,96,127):
   for bad in ('ready','busy','sticky','phase','time','base','bank','bytes','frame','direction','autokill_lease','autokill_cost','autokill_move','kill_low','kill_high','textbox'):
    rows.append(dict(seed,slot=slot,entities=[dict(seed['entities'][0],slot=slot)],bad=bad,fault=1))
 if a.kill:
  assert not a.guards and not a.complete_frame
  rows=[dict(c,autokill=value,action=3)for c in rows if c['action']==2 for value in (1,65536,0x80000000,0xffffffff)]
 tables=[(58,0,fe),(59,0,up),(60,0,tt)];append='';bindings={};probes={};apply='SourceUpdateAnimation4086_Begin'
 if a.complete_frame:
  assert not a.guards
  from script_callback_owner import derive as callbacks_profile, pack as pack_callbacks
  from source_script_clone import derive as clone_profile, pack as pack_clone
  from source_frame_effect_plan import derive as plan_profile, pack as pack_plan
  cb,*_=callbacks_profile(source);callbacks=pack_callbacks(cb);clone=pack_clone(clone_profile(source));pr=plan_profile(er);plan=pack_plan(pr)
  rows=[c for c in rows if c['action']==1 and cb['models'][c['model']]['program']==65535 and pr['animations'][c['handle']-1]['frames'][c['result']]['ops']==[17,23]]
  assert rows and len(fe+callbacks+clone)<32768 and len(up+plan)<32768
  for c in rows:
   an=er['animations'][c['handle']-1];c['motion']=an['frames'][c['result']]['move'];c['first_base']=an['frames'][0]['move']['base'];c['flip']=an['events']['flipframe']==c['result']
  tables=[(58,0,fe+callbacks+clone),(59,0,up+plan),(60,0,tt)]
  apply='TimedFrameCompleteProbe'
  append='''TimedFrameCompleteProbe:
.a16
.i16
 php
 rep #$38
 jsl TIMEDBEGIN
 bcs TimedFrameCompleteProbe_Bad
 cmp #1
 bne TimedFrameCompleteProbe_Bad
 jsl WORLDGUARD
 bcc TimedFrameCompleteProbe_Bad
 jsl CALLBACKBEGIN
 bcs TimedFrameCompleteProbe_Bad
 jsl CALLBACKRUN
 bcs TimedFrameCompleteProbe_Bad
 cmp #4
 bne TimedFrameCompleteProbe_Bad
 lda #1
 jsl FRAMEACK
 bcs TimedFrameCompleteProbe_Bad
 jsl EFFECTRUN
 bcs TimedFrameCompleteProbe_Bad
 cmp #0
 bne TimedFrameCompleteProbe_Bad
 jsl TIMEDCONTINUE
 bcs TimedFrameCompleteProbe_Bad
 jsl WORLDGUARD
 bcs TimedFrameCompleteProbe_Bad
 plp
 clc
 rtl
TimedFrameCompleteProbe_Bad:
.a16
.i16
 plp
 sec
 rtl
'''
  bindings=dict(TIMEDBEGIN='SourceUpdateAnimation4086_Begin',TIMEDCONTINUE='SourceUpdateAnimation4086_Continue',WORLDGUARD='SourceUpdateAnimation4086_CheckWorldAck',CALLBACKBEGIN='SourceAnimationCallback4086_Begin',CALLBACKRUN='SourceAnimationCallback4086_Run',FRAMEACK='SourceUpdateFrame4086_Ack',EFFECTRUN='SourceFrameEffects4086_Run')
  if a.resume_guards:
   seed=rows[0];rows=[]
   for slot in (0,1,95,96,127):
    for bad in ('world','tick','state','pending','phase','slot','time_low','time_high','frame_ready','frame_state','frame_pending','frame_slot','self_active','self_fault','plan_state','plan_service'):
     rows.append(dict(seed,slot=slot,entities=[dict(seed['entities'][0],slot=slot)],fault=1,resume_bad=bad))
   append=append.replace(' jsl TIMEDCONTINUE','TimedFrameResumeProbe:\n.a16\n.i16\n nop\n jsl TIMEDCONTINUE')
   probes['TIMEDRESUMEPROBE']='TimedFrameResumeProbe'
 lua=BASE[:BASE.index('emu.addMemoryCallback(function()local s=emu.getState();cpu=')].replace('TABLESIZE','0')
 setup=r'''
 local s=c.slot;local v=0x414000+s*80;local side=0x416800+s*64;local life=0x439000+s*80;local aux=0x41f500+s*20;local flags=0x43eb00+s*32;local freeze=0x42e000+s*40
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',7);set('SourceWorldTick4086_Slot',s);set('SourceWorldTick4086_View',0x4000+s*80);set('SourceWorldTick4086_Side',0x6800+s*64);put(sy.SourceWorldTick4086_TimeLo,c.time,4)
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0);put(sy.SourceSelf4086_GlobalLow,v,4);set('SourceFreeze4086_Ready',0xb5df);set('SourceIdle4086_Ready',0xb4f3)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',58);set('SourceUpdateFrame4086_Bytes',FEBYTES)
 set('SourceFrameEffectPlan4086_Ready',0);set('SourceFrameMotion4086_Status',0);set('VmState_Status',0);set('VmSourceWorld_Level',1)
 set('SourceUpdateAnimationPrefix4086_Ready',0xb60d);set('SourceUpdateAnimationPrefix4086_Status',0);set('SourceUpdateAnimationPrefix4086_Base',0x8000);set('SourceUpdateAnimationPrefix4086_Bank',59);set('SourceUpdateAnimationPrefix4086_Bytes',UPBYTES);set('SourceUpdateAnimationPrefix4086_Models',16);set('SourceUpdateAnimationPrefix4086_SleepID',80)
 set('SourceUpdateAnimation4086_Ready',0xb60f);set('SourceUpdateAnimation4086_State',0);set('SourceUpdateAnimation4086_Base',0x8000);set('SourceUpdateAnimation4086_Bank',60);set('SourceUpdateAnimation4086_Bytes',TTBYTES)
 set('SourceAutokillState4086_Ready',0xb60e);set('SourceAttackCostState4086_Ready',0xb609);set('SourceMovementState4086_Ready',0xb60b);put(0x43d800+s*4,0,4);set('SourceRetirement4086_Ready',0)
 put(v+16,1,4);put(v+20,65536,4);put(side+6,c.frame);put(side+8,c.equal==1 and c.time or(c.time~65536),4);put(aux+16,c.direction);put(aux+12,123,4);put(flags,0,4);put(flags+4,0,4);put(flags+24,123,4)
 for _,offset in ipairs({24,28,32,36,40})do put(life+offset,0,4)end;put(life+48,0,4);put(freeze+4,0,4);put(freeze+32,0,4);put(freeze+36,0x80000002,4)
 if c.bad=='ready'then set('SourceUpdateAnimation4086_Ready',0)
 elseif c.bad=='busy'then set('SourceUpdateAnimation4086_State',1)
 elseif c.bad=='sticky'then set('SourceUpdateAnimation4086_State',3)
 elseif c.bad=='phase'then set('SourceWorldTick4086_Phase',5)
 elseif c.bad=='time'then put(sy.SourceWorldTick4086_TimeHi,0)
 elseif c.bad=='base'then set('SourceUpdateAnimation4086_Base',0x7fff)
 elseif c.bad=='bank'then set('SourceUpdateAnimation4086_Bank',64)
 elseif c.bad=='bytes'then set('SourceUpdateAnimation4086_Bytes',24)
 elseif c.bad=='frame'then put(side+6,32767)
 elseif c.bad=='direction'then put(aux+16,2)
 elseif c.bad=='autokill_lease'then set('SourceAutokillState4086_Ready',0)
 elseif c.bad=='autokill_cost'then set('SourceAttackCostState4086_Ready',0)
 elseif c.bad=='autokill_move'then set('SourceMovementState4086_Ready',0)
 elseif c.bad=='kill_low'then put(0x43d800+s*4,1,4)
 elseif c.bad=='kill_high'then put(0x43d800+s*4,65536,4)
 elseif c.bad=='textbox'then put(0x40c048+s*96,128,4);put(side+8,c.time~65536,4)end
 '''
 for key,value in dict(FEBYTES=len(fe),UPBYTES=len(up),TTBYTES=len(tt)).items():setup=setup.replace(key,str(value))
 if a.kill:
  setup+=r'''
 set('SourceRetirement4086_Ready',0xb4f8);set('SourceRetirement4086_Status',0);set('VmSourceVars_Ready',0xb4a4);set('VmSourceVars_Base',0x8800);set('VmSourceVars_Bank',0x41);set('VmSourceVars_Count',384)
 for j=0,8191 do emu.write(0x409000+j,0,mt)end;for j=0,24575 do emu.write(0x418800+j,0,mt)end;for j=0,31 do emu.write(0x43fd80+j,0,mt)end
 put(0x43fd80,1,4);put(0x43d800+s*4,c.autokill,4);put(v+32,1,4);put(v+36,88,4)
 '''
 if a.complete_frame:
  complete=FRAMEZERO_SETUP
  for key,value in dict(PROGRAMS=cb['program_count'],CALLBACKBASE=0x8000+len(fe),CALLBACKBYTES=len(callbacks),EFFECTBYTES=len(fe),PLANBASE=0x8000+len(up),PLANBYTES=len(plan),PAIREDCRC=struct.unpack_from('<I',plan,24)[0],BODYCRC=struct.unpack_from('<I',plan,28)[0],CLONEBASE=0x8000+len(fe)+len(callbacks),CLONEBYTES=len(clone)).items():complete=complete.replace(key,str(value))
  setup+=complete+'\n put(side+48,0,4);put(0x43fb00+(c.handle-1)*4,0,4)\n'
 lua=lua.replace(' before={};',setup+' before={};').replace('{{0x414000,18432}','{{0x41f500,2560},{0x43eb00,4096},{0x42e000,5120},{0x43d800,512},{0x414000,18432}')
 if a.kill:lua=lua.replace('{{0x41f500,2560}','{{0x409000,8192},{0x418800,24576},{0x43fd80,32},{0x7ffe38,4},{0x41f500,2560}')
 lua+=r'''
local lastGuard='entry'
for label,addr in pairs(sy)do
 if label:match('^SourceUpdateAnimation4086_Guard')then
  local captured=label
  emu.addMemoryCallback(function()lastGuard=captured end,emu.callbackType.exec,addr,addr,emu.cpuType.snes,mt)
 end
end
emu.addMemoryCallback(function()emu.log('ANIMFAULT|'..word(INDEX)..'|'..lastGuard..'|frame='..word(sy.SourceUpdateFrame4086_State)..'|prefix='..word(sy.SourceUpdateAnimationPrefix4086_Status)..'|count='..word(sy.SourceAnimation4086_Count)..'|handle='..word(sy.SourceUpdateAnimation4086_Handle))end,emu.callbackType.exec,sy.SourceUpdateAnimation4086_Bad,sy.SourceUpdateAnimation4086_Bad,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if cpu.sp+3~=st['cpu.sp']or(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 emu.log('ANIMFRAMEORDER|'..word(INDEX)..'|'..word(0x42e024+c.slot*40)..'|'..word(sy.SourceUpdateAnimationPrefix4086_Status)..'|'..word(0x416806+c.slot*64))
end,emu.callbackType.exec,sy.SourceUpdateFrame4086_Begin,sy.SourceUpdateFrame4086_Begin,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local function expect(addr,v,n)for j=0,n-1 do before[addr+j]=(v>>(8*j))&255 end end
 local pending=0;local state=3
 if c.fault==0 or c.resume_bad then
  expect(0x43eb18+c.slot*32,(c.time+1000)&0xffffffff,4);state=2
  if c.action==2 or c.action==3 then expect(0x41f510+c.slot*20,0,2)
   if c.action==3 then expect(0x414004+c.slot*80,0,2);expect(0x414024+c.slot*80,0,4);expect(0x43fd80,0,4)end
  elseif c.action==1 then
   state=1;pending=1;expect(0x416806+c.slot*64,c.result,2);expect(0x416808+c.slot*64,(c.time+c.delay)&0xffffffff,4);expect(0x41f50c+c.slot*20,0,4);expect(0x42e024+c.slot*40,0x80000003,4)
   if c.motion then
    state=2;pending=0
    expect(0x41f500+c.slot*20,c.motion.x*65536,4);expect(0x41f504+c.slot*20,c.motion.z*65536,4)
    local base=c.first_base>0 and c.first_base or c.motion.y
    expect(0x416830+c.slot*64,base*65536,4);expect(0x41f508+c.slot*20,c.first_base>0 and 0 or c.motion.y*65536,4)
    if c.flip then expect(0x41401c+c.slot*80,0,4)end
   end
  end
  if c.resume_bad then state=3;if c.resume_bad=='frame_pending'then pending=1 end end
 end
 local changed=0;local diag='';for addr,value in pairs(before)do if emu.read(addr,mt)~=value then changed=changed+1;if changed<8 then diag=diag..string.format('%06x:%02x/%02x,',addr,emu.read(addr,mt),value)end end end
 if changed~=0 then emu.log('ANIMDIAG|'..word(INDEX)..'|'..diag)end
 emu.log('ANIMRESULT|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceUpdateAnimation4086_State)..'|'..word(sy.SourceUpdateFrame4086_Pending)..'|'..state..'|'..pending)
 put(sy.VmSourceWorld_Ready,0);put(sy.SourceWorldTick4086_Ready,0)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 if a.resume_guards:
  lua+=r'''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local b=c.resume_bad
 if b=='world'then set('VmSourceWorld_Ready',0)
 elseif b=='tick'then set('SourceWorldTick4086_Ready',0)
 elseif b=='state'then set('SourceWorldTick4086_State',2)
 elseif b=='pending'then set('SourceWorldTick4086_Pending',0)
 elseif b=='phase'then set('SourceWorldTick4086_Phase',5)
 elseif b=='slot'then set('SourceWorldTick4086_Slot',(c.slot+1)%128)
 elseif b=='time_low'then put(sy.SourceWorldTick4086_TimeLo,c.time~1,4)
 elseif b=='time_high'then put(sy.SourceWorldTick4086_TimeLo,c.time~65536,4)
 elseif b=='frame_ready'then set('SourceUpdateFrame4086_Ready',0)
 elseif b=='frame_state'then set('SourceUpdateFrame4086_State',1)
 elseif b=='frame_pending'then set('SourceUpdateFrame4086_Pending',1)
 elseif b=='frame_slot'then set('SourceUpdateFrame4086_Slot',(c.slot+1)%128)
 elseif b=='self_active'then set('SourceSelf4086_Active',1)
 elseif b=='self_fault'then set('SourceSelf4086_Fault',1)
 elseif b=='plan_state'then set('SourceFrameEffectPlan4086_State',1)
 elseif b=='plan_service'then set('SourceFrameEffectPlan4086_Service',9)end
end,emu.callbackType.exec,TIMEDRESUMEPROBE,TIMEDRESUMEPROBE,emu.cpuType.snes,mt)
'''
 r=Reporter('M4-UPDATE-ANIMATION',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,apply,'SourceUpdateAnimation4086_Ready',0xb60f,tables,lua,r,append=append,bindings=bindings,probes=probes,batch_size=4,frame_limit=4000)
 actual=[list(map(int,line.split('ANIMRESULT|',1)[1].split('|')))for line in log.splitlines()if 'ANIMRESULT|'in line]
 order=[list(map(int,line.split('ANIMFRAMEORDER|',1)[1].split('|')))for line in log.splitlines()if 'ANIMFRAMEORDER|'in line]
 r.check('actual timed state, update mark before frame, delay wrap and explicit atomic admission failures',len(actual)==len(rows)and all(v[:3]==[i,0,0]and v[3:5]==v[5:7]for i,v in enumerate(actual)))
 r.check('prefix completes and frame mark is set before update_frame enters',order==[[i,3,2,c['frame']]for i,c in enumerate(rows)if c['action']==1 and (not c['fault']or c.get('resume_bad'))])
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_UPDATE_ANIMATION_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,frame_order=order,guards=a.guards,resume_guards=a.resume_guards,rom_sha256=hashlib.sha256(raw).hexdigest(),frame_services_pending=not a.complete_frame and not a.kill,actual_empty_callback_and_frame_effect_owner=a.complete_frame,world_ack_guard_executed=a.complete_frame,scripted_callback_body_executed=False,actual_no_event_no_minion_kill_executed=a.kill,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()

if __name__=='__main__':main()
