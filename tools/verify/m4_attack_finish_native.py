"""Literal attack finish through actual idle, over actual per-entity modeldata type."""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source
from source_frame_state_4086 import derive as frames,pack as pack_frames
from source_frame_effects_4086 import derive as effects,pack as pack_effects
from source_animation_init_4086 import derive as init,pack as pack_init
from m4_target_metadata_native import LUA as BASE
from _source_leaf_fixture import run_fixture
from _harness import Reporter

FINISH_SETUP=r'''
 local s=c.slot;local v=0x414000+s*80;local side=0x416800+s*64;local life=0x439000+s*80;local flags=0x43eb00+s*32
 set('SourceAI4086_SpawnID',23);set('SourceAI4086_RespawnID',104);set('SourceAI4086_Ready',0xb5e2);set('SourceAI4086_State',c.bad=='ai_state'and 2 or 1);set('SourceAI4086_Slot',s);put(sy.SourceAI4086_Callback,c.bad=='callback_low'and 16 or 17,4);if c.bad=='callback_high'then put(sy.SourceAI4086_Callback+2,1)end
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',6);set('SourceWorldTick4086_Slot',s);put(sy.SourceWorldTick4086_TimeLo,c.time,4)
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0);put(sy.SourceSelf4086_GlobalLow,v,4);set('SourceFreeze4086_Ready',0xb5df)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Maximum',168);set('SourceModelAnimationCopy4086_Bytes',5376);set('SourceModelAnimationCopy4086_Frames',80)
 for j=0,5375 do emu.write(0x43c000+j,0,mt)end;put(0x43c000+c.model*336,1);put(0x40b09c+c.model*160,c.type~1,4);put(v+16,1,4);put(v+20,0,4)
 set('SourceAnimationInit4086_Ready',0xb4ec);set('SourceAnimationInit4086_State',0);set('SourceAnimationInit4086_Base',INITBASE);set('SourceAnimationInit4086_Bank',59);set('SourceAnimationInit4086_Bytes',INITBYTES)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);set('SourceUpdateFrame4086_Animations',80);set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',58);set('SourceIdle4086_Ready',0xb4f3);set('SourceIdle4086_Status',0)
 put(life+12,c.bad=='action_low'and 16 or 17,4);if c.bad=='action_high'then put(life+14,1)end
 put(flags,55,4);put(flags+4,66,4);put(flags+8,77,4);put(flags+12,88,4);put(flags+20,0,4);put(0x40c058+s*96,99,4);put(side+36,3*65536,4);put(side+40,4*65536,4);put(0x42e008+s*40,111,4)
 put(0x40900c+s*64,c.bad=='opponent_low'and 1 or c.bad=='opponent_high'and 65536 or 0,4)
 set('SourceAttackTiming4086_Status',c.bad=='timing_busy'and 1 or 2);set('SourceAttackTiming4086_Models',c.bad=='timing_models'and 15 or 16);if c.bad=='core_models'then set('SourceModelEntityCopy4086_Models',17)elseif c.bad=='core_zero'then set('SourceModelEntityCopy4086_Models',0)end
 set('SourceAttackTiming4086_Ready',c.bad=='timing_ready'and 0 or 0xb603);put(0x438800+s*14,c.aggression,4);put(0x43880c+s*14,c.bad=='timing_marker'and 0 or 0xb603)
 set('SourceCommonAttackFinish4086_Ready',c.bad=='finish_ready'and 0 or 0xb608);set('SourceCommonAttackFinish4086_Status',c.bad=='finish_busy'and 1 or c.bad=='finish_sticky'and 3 or 0)
 '''

FRAMEZERO_SETUP="\n put(0x416802+s*64,c.model);put(0x41f500+s*20,0,4);put(0x41f504+s*20,0,4);put(0x41f50c+s*20,0,4);put(0x43fb00,0,4);put(sy.VmSourceWorld_Level,1)\n set('VmSourceFrame_Ready',0xb4fd);set('VmSourceFrame_Programs',PROGRAMS);set('VmSourceInstr_Ready',0xb48e);set('SourceVMRun4086_Ready',0xb4d7);set('SourceVMRun4086_Busy',0);set('VmSourceModels_Count',16);set('VmSourceCallback_Active',0)\n set('SourceAnimationCallback4086_Ready',0xb4e6);set('SourceAnimationCallback4086_State',0);set('SourceAnimationCallback4086_Base',CALLBACKBASE);set('SourceAnimationCallback4086_Bank',58);set('SourceAnimationCallback4086_Bytes',CALLBACKBYTES)\n set('SourceUpdateFrame4086_Bytes',EFFECTBYTES);set('SourceFrameMotion4086_Ready',0xb4e8);set('SourceFrameMotion4086_Status',0);set('SourceFrameEffectLeaf4086_Ready',0xb4f4)\n set('SourceFrameEffectPlan4086_Ready',0xb4f2);set('SourceFrameEffectPlan4086_State',0);set('SourceFrameEffectPlan4086_Base',PLANBASE);set('SourceFrameEffectPlan4086_Bank',59);set('SourceFrameEffectPlan4086_Bytes',PLANBYTES);set('SourceFrameEffectPlan4086_Animations',80)\n put(sy.SourceFrameEffectPlan4086_PairedCrcLo,PAIREDCRC,4);put(sy.SourceFrameEffectPlan4086_BodyCrcLo,BODYCRC,4)\n set('VmSourceWorld_TemplateCount',16);set('VmSourceVars_Ready',0xb4a4);set('VmSourceVars_Base',0x8800);set('VmSourceVars_Bank',0x41);set('VmSourceVars_Count',384)\n put(0x410000+s*64,0x414000+s*80,4);put(0x40902c+s*64,0,4)\n set('SourceScriptClone4086_Ready',0xb5c1);set('SourceScriptClone4086_Status',0);set('SourceScriptClone4086_Base',CLONEBASE);set('SourceScriptClone4086_Bank',58);set('SourceScriptClone4086_Bytes',CLONEBYTES);set('SourceScriptClone4086_Models',16)\n"

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--proc-guards',action='store_true');p.add_argument('--cost-payment',action='store_true');p.add_argument('--ai-dispatch',action='store_true');p.add_argument('--attack-proc',action='store_true');p.add_argument('--resume-guards',action='store_true');p.add_argument('--complete-idle',action='store_true');p.add_argument('--pending',action='store_true');p.add_argument('--premature-continue',action='store_true')
 a=p.parse_args();a.pending=a.pending or a.complete_idle;a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);au=json.loads(a.authority.read_text());assert au['status']=='PASS';source=Source(a.source);ft=pack_frames(frames(source));fe=pack_effects(effects(source));it=pack_init(init(source));rows=[]
 for i,(c,e)in enumerate(zip(au['inputs'],au['actual'])):
  s=(0,1,95,96,127)[i%5];m=(0,1,15)[i%3]
  ent=dict(slot=s,model=m,handle=2 if a.pending else 1,frame=0,exists=1,type=c['type'],hostile=1,dead=0,invincible=0,detect=-1,hide=-1)
  rows.append(dict(c,slot=s,model=m,count=128,entities=[ent],bad='',fault=int(a.premature_continue),expected=e))
 if a.pending:rows=[c for c in rows if c['time']==50]
 if not a.pending:
  for s in (0,127):
   for bad in ('finish_ready','finish_busy','finish_sticky','ai_state','callback_low','callback_high','action_low','action_high','opponent_low','opponent_high','timing_ready','timing_marker','timing_busy','timing_models','core_models','core_zero'):
    rows.append(dict(rows[0],slot=s,type=0,bad=bad,fault=1,entities=[dict(rows[0]['entities'][0],slot=s)]))
 tables=[(58,0,fe),(59,0,ft+it)]
 if a.complete_idle:
  from script_callback_owner import derive as callbacks_profile,pack as pack_callbacks
  from source_script_clone import derive as clone_profile,pack as pack_clone
  from source_frame_effect_plan import derive as plan_profile,pack as pack_plan
  cb,*_=callbacks_profile(source);callbacks=pack_callbacks(cb);clone=pack_clone(clone_profile(source));plan=pack_plan(plan_profile(effects(source)))
  rows=[c for c in rows if cb['models'][c['model']]['program']==65535]
  tables=[(58,0,fe+callbacks+clone),(59,0,ft+it+plan)]
 if a.resume_guards:
  assert a.complete_idle and not a.premature_continue
  seed=rows[0];rows=[]
  for slot in (0,1,95,96,127):
   for bad in ('low','high'):
    rows.append(dict(seed,slot=slot,entities=[dict(seed['entities'][0],slot=slot)],resume_bad=bad,fault=1,expected=[111,*seed['expected'][1:]]))
 if a.proc_guards:
  assert a.attack_proc and not a.complete_idle and not a.pending and not a.ai_dispatch
  seed=rows[0];rows=[]
  for slot in (0,1,95,96,127):
   for bad in ('proc_ready','proc_busy','proc_sticky','roles_ready','smart_self','flags_ready','shot_low','shot_high','cost_ready','pay_ready'):
    rows.append(dict(seed,slot=slot,entities=[dict(seed['entities'][0],slot=slot)],bad=bad,fault=1))
   for smart in (0,1):
    for reactive in (0,1,65536,65537,0xffffffff):rows.append(dict(seed,slot=slot,entities=[dict(seed['entities'][0],slot=slot)],bad='',fault=0,smart_other=smart,reactive=reactive))
 if a.attack_proc:
  for i,c in enumerate(rows):c.setdefault('reactive',(0,1,65536,65537,0xffffffff)[i%5])
 lua=BASE[:BASE.index('emu.addMemoryCallback(function()local s=emu.getState();cpu=')].replace('TABLESIZE',str(len(ft)))
 setup=FINISH_SETUP
 setup=setup.replace('INITBASE',str(0x8000+len(ft))).replace('INITBYTES',str(len(it)))
 if a.complete_idle:
  complete_setup=FRAMEZERO_SETUP
  for token,value in dict(PROGRAMS=cb['program_count'],CALLBACKBASE=0x8000+len(fe),CALLBACKBYTES=len(callbacks),EFFECTBYTES=len(fe),PLANBASE=0x8000+len(ft)+len(it),PLANBYTES=len(plan),PAIREDCRC=struct.unpack_from('<I',plan,24)[0],BODYCRC=struct.unpack_from('<I',plan,28)[0],CLONEBASE=0x8000+len(fe)+len(callbacks),CLONEBYTES=len(clone)).items():complete_setup=complete_setup.replace(token,str(value))
  setup+=complete_setup
 if a.attack_proc:
  setup+="\n set('SourceCommonAttackProc4086_Ready',0xb607);set('SourceCommonAttackProc4086_Status',0);set('SourceRetirement4086_Ready',0xb4f8);put(0x43fd94,0,4);put(flags+16,c.reactive,4);put(flags+28,0,4);put(v+8,2,4);put(v+12,0,4);put(side+48,0,4);put(0x41f510+s*20,0)\n set('SourceAttackCostState4086_Ready',0xb609);set('SourceAttackCostPay4086_Ready',0xb60a);set('SourceAttackCostPay4086_Status',0);put(0x43de00+s*4,0,4)\n"
 if a.proc_guards:
  setup+="\n if c.bad=='proc_ready'then set('SourceCommonAttackProc4086_Ready',0)elseif c.bad=='proc_busy'then set('SourceCommonAttackProc4086_Status',1)elseif c.bad=='proc_sticky'then set('SourceCommonAttackProc4086_Status',3)elseif c.bad=='roles_ready'then set('SourceRetirement4086_Ready',0)elseif c.bad=='smart_self'then put(0x43fd94,v,4)elseif c.bad=='flags_ready'then set('SourceIdle4086_Ready',0)elseif c.bad=='shot_low'then put(flags+16,1,4);put(flags+28,1,4)elseif c.bad=='shot_high'then put(flags+16,1,4);put(flags+28,65536,4)elseif c.bad=='cost_ready'then set('SourceAttackCostState4086_Ready',0)elseif c.bad=='pay_ready'then set('SourceAttackCostPay4086_Ready',0)end\n if c.smart_other==1 then put(0x43fd94,0x414000+((s+1)%128)*80,4)end\n"
 if a.cost_payment:
  assert a.attack_proc and a.complete_idle
  from source_animation_energy_4086 import derive as energies,pack as pack_energy
  energy=energies(source);et=pack_energy(energy);live=next(an for an in energy['animations']if an['fields']['cost']==10);tables.append((60,0,et))
  for i,c in enumerate(rows):c['tocost']=(1,65536,0xffffffff)[i%3];c['debit_mp']=int(c['type']!=0)
  setup+="\n set('SourceEntityEnergy4086_Ready',0xb5fd);set('SourceEntityEnergy4086_Status',0);set('VmSourceEntity_Ready',0xb5ef);set('VmSourceEntity_Base',0x4000);set('VmSourceEntity_Bank',0x41);set('VmSourceEntity_Count',128)\n set('SourceCheckEnergy4086_Ready',0xb5fa);set('SourceCheckEnergy4086_Status',0);set('SourceAnimationEnergy4086_Ready',0xb5fc);set('SourceAnimationEnergy4086_Status',0);set('SourceAnimationEnergy4086_Bank',60);set('SourceAnimationEnergy4086_Bytes',"+str(len(et))+");put(side+4,"+str(live['handle'])+");put(v+32,1,4);put(v+36,88,4);put(0x40c04c+s*96,77,4);put(0x437e04+s*20,0,4);put(0x437e10+s*20,0xb5fb);put(0x437e12+s*20,0);put(0x43de00+s*4,c.tocost,4)\n"
 if a.ai_dispatch:
  assert a.attack_proc and a.complete_idle and not a.resume_guards
  setup+="\n set('SourceAIRun4086_Ready',0xb5e6);set('SourceAIRun4086_State',0);set('SourceAIRun4086_PendingKind',0);set('SourceAI4086_State',0);put(sy.SourceAI4086_Endgame,0,4);put(side+20,0,4);put(0x42e024+s*40,17,4)\n"
 lua=lua.replace(' before={};',setup+' before={};').replace('{{0x414000,18432}','{{0x43eb00,4096},{0x42e000,5120},{0x416800,8192},{0x41f500,2560},{0x43e000,512},{0x409000,8192},{0x438800,1792},{0x40b000,2560},{0x43c000,8192},{sy.VmNativeVariant_Result,8},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18},{0x414000,18432}')
 lua+=r'''
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local function expect(a,v,n)for j=0,n-1 do before[a+j]=(v>>(8*j))&255 end end
 if c.bad==''then
 expect(0x43900c+c.slot*80,0,4);expect(0x43eb00+c.slot*32,0,16);expect(0x43eb00+c.slot*32,3,4);expect(0x40c058+c.slot*96,0,4);expect(0x416824+c.slot*64,0,8);expect(0x42e008+c.slot*40,PENDING and 111 or c.expected[1],4)
 if PENDING then expect(0x416804+c.slot*64,1,2);expect(0x41f510+c.slot*20,1,2);expect(0x41f508+c.slot*20,0,4);expect(0x43e004,0,4);expect(0x40c054+c.slot*96,0,4)end
 end
 local changed=0;local details='';for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1;if changed<=12 then details=details..string.format('%06x:%02x/%02x,',a,emu.read(a,mt),v)end end end
 if changed~=0 then emu.log('FINISHDIAG|'..word(INDEX)..'|'..details)end
 emu.log('FINISHRESULT|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceCommonAttackFinish4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 lua+=r'''
emu.addMemoryCallback(function()emu.log('FINISHGUARD|actor '..word(sy.SourceAI4086_Slot)..' idle '..word(sy.SourceIdle4086_Status)..' init '..word(sy.SourceAnimationInit4086_State)..' callback '..word(sy.SourceAI4086_Callback)..' status '..word(sy.SourceCommonAttackFinish4086_Status))end,emu.callbackType.exec,sy.SourceCommonAttackFinish4086_Bad,sy.SourceCommonAttackFinish4086_Bad,emu.cpuType.snes,mt)
for _,name in ipairs({'SourceAI4086_PreflightBad','SourceSetIdle4086_Bad','SourceIdle4086_Bad','SourceAnimationInit4086_ResolveBad'})do emu.addMemoryCallback(function()emu.log('FINISHCHILD|'..name)end,emu.callbackType.exec,sy[name],sy[name],emu.cpuType.snes,mt)end
'''
 if a.complete_idle:
  lua=lua.replace('PENDING and 111 or c.expected[1]','c.expected[1]')
  lua=lua.replace('local changed=0;local details=', 'if PENDING then expect(0x416806+c.slot*64,0,2);expect(0x416808+c.slot*64,c.time+8,4)end\n local changed=0;local details=')
 lua='local finishorder,orderfaults={},0\n'+lua.replace(' local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)',' local c=rows[word(INDEX)+1];finishorder={};orderfaults=0;put(EXPECTFAULT,c.fault)')
 lua+=r'''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];finishorder[#finishorder+1]=1
 local life=0x439000+c.slot*80;local side=0x416800+c.slot*64
 if word(life+12)~=0 or word(life+14)~=0 or word(side+36)~=0 or word(side+38)~=0 or word(side+40)~=0 or word(side+42)~=0 or word(0x42e008+c.slot*40)~=111 or word(0x42e00a+c.slot*40)~=0 then orderfaults=orderfaults+1 end
end,emu.callbackType.exec,sy.SourceSetIdle4086_Begin,sy.SourceSetIdle4086_Begin,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()finishorder[#finishorder+1]=2;local c=rows[word(INDEX)+1];if word(0x42e008+c.slot*40)~=111 or word(0x42e00a+c.slot*40)~=0 or word(0x43eb00+c.slot*32)~=3 then orderfaults=orderfaults+1 end end,emu.callbackType.exec,sy.SourceCommonAttackFinish4086_PostIdle,sy.SourceCommonAttackFinish4086_PostIdle,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('FINISHORDER|'..word(INDEX)..'|'..orderfaults..'|'..table.concat(finishorder,','))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 if a.resume_guards:
  lua+="emu.addMemoryCallback(function()local c=rows[word(INDEX)+1];put(sy.SourceAI4086_Callback,c.resume_bad=='low'and 16 or 17,4);if c.resume_bad=='high'then put(sy.SourceAI4086_Callback+2,1)end end,emu.callbackType.exec,sy.SourceCommonAttackFinish4086_Continue,sy.SourceCommonAttackFinish4086_Continue,emu.cpuType.snes,mt)\n"
 if a.attack_proc:
  lua=lua.replace("if c.bad==''then\n","if c.bad==''then\n if c.reactive==1 then expect(0x43eb10+c.slot*32,0,4)end\n",1).replace("word(sy.SourceCommonAttackFinish4086_Status))","word(sy.SourceCommonAttackProc4086_Status))")
 if a.cost_payment:
  lua=lua.replace("if c.bad==''then\n","if c.bad==''then\n expect(0x40c04c+c.slot*96,c.debit_mp==1 and 67 or 77,4);expect(0x414024+c.slot*80,c.debit_mp==1 and 88 or 78,4);expect(0x43de00+c.slot*4,0,4)\n",1)
  lua="local cost_calls=0\n"+lua.replace('finishorder={};orderfaults=0;','finishorder={};orderfaults=0;cost_calls=0;')
  lua+="emu.addMemoryCallback(function()cost_calls=cost_calls+1 end,emu.callbackType.exec,sy.SourceAttackCostPay4086_Execute,sy.SourceAttackCostPay4086_Execute,emu.cpuType.snes,mt)\n"
  lua+="emu.addMemoryCallback(function()emu.log('PROCCOSTCALLS|'..word(INDEX)..'|'..cost_calls)end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
 if a.ai_dispatch:
  lua=lua.replace("if c.bad==''then\n","if c.bad==''then\n expect(0x416814+c.slot*64,0,4);expect(0x42e024+c.slot*40,19,4)\n",1)
  lua+="emu.addMemoryCallback(function()emu.log('PROCINITIALAI|'..word(INDEX)..'|'..word(sy.SourceAIRun4086_State)..'|'..word(sy.SourceAI4086_State)..'|'..word(sy.SourceAIRun4086_PendingKind))end,emu.callbackType.exec,sy.SourceAnimationInit4086_StartFrame,sy.SourceAnimationInit4086_StartFrame,emu.cpuType.snes,mt)\n"
  lua+="emu.addMemoryCallback(function()emu.log('PROCFINALAI|'..word(INDEX)..'|'..word(sy.SourceAIRun4086_State)..'|'..word(sy.SourceAI4086_State)..'|'..word(sy.SourceAIRun4086_PendingKind))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
 lua=lua.replace('PENDING','true'if a.pending else'false');append='';bindings={};apply='SourceCommonAttackFinish4086_Execute'
 if a.premature_continue:
  assert a.pending;apply='FinishProbe';append='FinishProbe:\n.a16\n.i16\n jsl FINISH\n bcs FinishProbe_Return\n jsl CONTINUE\nFinishProbe_Return:\n.a16\n.i16\n rtl\n';bindings=dict(FINISH='SourceCommonAttackFinish4086_Execute',CONTINUE='SourceCommonAttackFinish4086_Continue')
 if a.complete_idle:
  assert not a.premature_continue;apply='FinishCompleteProbe';append='FinishCompleteProbe:\n.a16\n.i16\n jsl FINISH\n bcs FinishCompleteProbe_Fail\n cmp #1\n bne FinishCompleteProbe_Fail\n jsl STARTFRAME\n bcs FinishCompleteProbe_Fail\n jsl CALLBACKBEGIN\n bcs FinishCompleteProbe_Fail\n jsl CALLBACKRUN\n bcs FinishCompleteProbe_Fail\n cmp #4\n bne FinishCompleteProbe_Fail\n lda #1\n jsl FRAMEACK\n bcs FinishCompleteProbe_Fail\n jsl EFFECTRUN\n bcs FinishCompleteProbe_Fail\n cmp #0\n bne FinishCompleteProbe_Fail\n jsl CONTINUE\n rtl\nFinishCompleteProbe_Fail:\n.a16\n.i16\n sec\n rtl\n';bindings=dict(FINISH='SourceCommonAttackFinish4086_Execute',STARTFRAME='SourceAnimationInit4086_StartFrame',CALLBACKBEGIN='SourceAnimationCallback4086_Begin',CALLBACKRUN='SourceAnimationCallback4086_Run',FRAMEACK='SourceUpdateFrame4086_Ack',EFFECTRUN='SourceFrameEffects4086_Run',CONTINUE='SourceCommonAttackFinish4086_Continue')
 if a.attack_proc:
  if apply=='SourceCommonAttackFinish4086_Execute':apply='SourceCommonAttackProc4086_Execute'
  else:bindings.update(FINISH='SourceCommonAttackProc4086_Execute',CONTINUE='SourceCommonAttackProc4086_Continue')
 if a.ai_dispatch:bindings.update(FINISH='SourceAIRun4086_Begin',CONTINUE='SourceAIRun4086_Continue')
 r=Reporter('M4-ATTACK-FINISH',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,apply,'SourceCommonAttackFinish4086_Ready',0xb608,tables,lua,r,append=append,bindings=bindings,batch_size=1,frame_limit=4000)
 actual=[list(map(int,l.split('FINISHRESULT|',1)[1].split('|')))for l in log.splitlines()if 'FINISHRESULT|'in l];expected=[[i,0,0,3 if c['fault']else 1 if a.pending and not a.complete_idle else 2]for i,c in enumerate(rows)];failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 r.check('literal finish through actual idle, per-entity type with contradictory shared model template, signed aggression, wrapped stall, owner guards, unchanged siblings/VM/RNG/CPU',len(actual)==len(rows)and not failures)
 order=[l.split('FINISHORDER|',1)[1].split('|')for l in log.splitlines()if 'FINISHORDER|'in l];wanted_order=[[str(i),'0',''if c['bad']else '1'if a.resume_guards or a.pending and not a.complete_idle else '1,2']for i,c in enumerate(rows)];r.check('literal call order: action/velocity clear then idle, completed idle before stall write',order==wanted_order)
 cost_calls=[list(map(int,l.split('PROCCOSTCALLS|',1)[1].split('|')))for l in log.splitlines()if 'PROCCOSTCALLS|'in l]
 if a.cost_payment:r.check('actual cost paid once before yielded idle; no cost helper on continuation',cost_calls==[[i,1]for i in range(len(rows))])
 ai_initial=[list(map(int,l.split('PROCINITIALAI|',1)[1].split('|')))for l in log.splitlines()if 'PROCINITIALAI|'in l];ai_final=[list(map(int,l.split('PROCFINALAI|',1)[1].split('|')))for l in log.splitlines()if 'PROCFINALAI|'in l]
 if a.ai_dispatch:r.check('actual AI callback17 pending then retirement after real idle frame zero',ai_initial==[[i,1,1,17]for i in range(len(rows))]and ai_final==[[i,2,5,0]for i in range(len(rows))])
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_ATTACK_FINISH_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:10],rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),execution_order=order,changed_idle_pending=a.pending,premature_continue=a.premature_continue,actual_frame_zero_executed=a.complete_idle,resume_callback_guards=a.resume_guards,proc_guards=a.proc_guards,cost_payment=a.cost_payment,cost_helper_calls=cost_calls,actual_ai_dispatch=a.ai_dispatch,ai_initial=ai_initial,ai_final=ai_final,finished_proc_bound=a.attack_proc,finished_proc_domain='nonself smartbomber and NULL weapent; player or NULL opponent' if a.attack_proc else None,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()

if __name__=='__main__':main()
