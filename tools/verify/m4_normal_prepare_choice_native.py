"""Actual normal_prepare weighted choices over source-derived range descriptors."""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source
from source_frame_state_4086 import derive as frame_profile,pack as pack_frames
from source_frame_effects_4086 import derive as effect_profile,pack as pack_effects
from source_animation_init_4086 import derive as init_profile,pack as pack_init
from source_animation_range_4086 import derive as range_profile,pack as pack_ranges
from source_attack_choice_4086 import derive as choice_profile,pack as pack_choice
from source_attack_body_profile import derive as body_profile,pack_runtime
from m4_normal_prepare_native import ASM,SETUP
from m4_target_metadata_native import LUA as BASE_LUA
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--changed-animation',action='store_true');p.add_argument('--script-framezero',action='store_true');p.add_argument('--complete-framezero',action='store_true');p.add_argument('--ai-dispatch',action='store_true');p.add_argument('--resume-guards',action='store_true');p.add_argument('--self-model',type=int,choices=range(16),default=14)
 a=p.parse_args();a.complete_framezero=a.complete_framezero or a.script_framezero;a.changed_animation=a.changed_animation or a.complete_framezero;a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);au=json.loads(a.authority.read_text());assert au['status']=='PASS';source=Source(a.source)
 fp=frame_profile(source);ft=pack_frames(fp);effects=pack_effects(effect_profile(source));init=pack_init(init_profile(source));rt=pack_ranges(range_profile(source));profile=choice_profile(source);pt=pack_choice(profile);body=pack_runtime(body_profile(source));assert profile['normal_roles']==[8,9,10,11]
 sample=next(an for an in fp['animations']if an['model']=='He_Man'and an['role']=='idle')if a.script_framezero else next(an for an in fp['animations']if any(f['vulnerable']for f in an['frames']));frame=next(i for i,f in enumerate(sample['frames'])if f['vulnerable']);ids={m['identity']:m['index']for m in body_profile(source)['models']};rows=[]
 for c,e in zip(au['inputs'],au['actual']):
  if not(c['present']==c['ranges']or c['ranges']==0 and c['seed']==1):continue
  i=len(rows);slot=(0,1,95,96,127)[i%5];target=(slot+1)%128
  def entity(s,m,h,x,t):return dict(slot=s,model=m,handle=h,frame=frame if h==sample['handle']else 0,exists=1,type=t,hostile=int(t==2),dead=0,invincible=0,detect=-1,hide=-1,x=x,z=220*65536,direction=0 if t==2 else 1)
  options=[r for j,r in enumerate(profile['normal_roles'])if c['present']&c['ranges']&(1<<j)]
  rows.append(dict(c,expected=e,slot=slot,count=128,time=50,stalltime=0,noflip=0,found=1,entities=[entity(slot,a.self_model,1,0,2),entity(target,ids[sample['model']],sample['handle'],65536,1)],bad='',fault=0,options=options))
 if a.changed_animation:rows=[c for c in rows if c['total']]
 if a.script_framezero:
  assert not a.resume_guards
  model_identity=body_profile(source)['models'][a.self_model]['identity']
  authored=next(an for an in fp['animations']if an['model']==model_identity and an['role']=='attack1');old=next(an for an in fp['animations']if an['model']==model_identity and an['role']=='idle')
  rows=[c for c in rows if c['present']==1 and c['ranges']==1]
  for c in rows:c['entities'][0]['handle']=old['handle']
 if a.resume_guards:
  assert a.complete_framezero and not a.ai_dispatch
  seed=rows[0];rows=[]
  for slot in (0,1,95,96,127):
   for bad in ('low','high'):
    ents=[dict(seed['entities'][0],slot=slot),dict(seed['entities'][1],slot=(slot+1)%128)]
    rows.append(dict(seed,slot=slot,entities=ents,resume_bad=bad,fault=1))
 lua=BASE_LUA[:BASE_LUA.index('emu.addMemoryCallback(function()local s=emu.getState();cpu=')]
 lua=lua.replace('TABLESIZE',str(len(ft))).replace('put(v+28,1,4)','put(v+28,e.direction,4)').replace('put(v+52,65536*e.slot,4)','put(v+52,e.x,4)').replace('put(v+60,220*65536,4)','put(v+60,e.z,4)')
 setup=SETUP.replace('14*9',str(a.self_model)+'*9').replace('BODYBASE',str(0x8000+len(rt)+len(pt))).replace('BODYOFFSET',str(len(rt)+len(pt))).replace('CHOICEBYTES',str(len(pt))).replace("set('SourceAttackChoiceProfile4086_Base',0x8000)","set('SourceAttackChoiceProfile4086_Base',"+str(0x8000+len(rt))+")")
 setup+=r'''
 put(sy.SourceRandom4086_SeedLo,c.seed,4)
 for _,e in ipairs(c.entities)do put(0x414008+e.slot*80,2,4);put(0x41400c+e.slot*80,0,4);put(0x416830+e.slot*64,0,4)end
 set('SourceEntityRange4086_Ready',0xb5f9);set('SourceEntityRange4086_Status',0);set('SourceCheckRange4086_Ready',0xb5f7);set('SourceCheckRange4086_Status',0);set('SourceAnimationRange4086_Ready',0xb5f8);set('SourceAnimationRange4086_Status',0);set('SourceAnimationRange4086_Bank',60);set('SourceAnimationRange4086_Bytes',RANGEBYTES)
 for j=0,3 do if(c.present&(1<<j))~=0 then put(0x43c000+SELFMODEL*336+2*(8+j),(c.ranges&(1<<j))~=0 and NEARHANDLE or 18)end end
 for j=0,255 do emu.write(0x435800+j,0xa5,mt)end
 put(v+16,1,4);put(v+20,0,4)
 set('SourceAnimationInit4086_Ready',0xb4ec);set('SourceAnimationInit4086_State',0);set('SourceAnimationInit4086_Number',55);set('SourceAnimationInit4086_Base',INITBASE);set('SourceAnimationInit4086_Bank',59);set('SourceAnimationInit4086_Bytes',INITBYTES)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_Animations',80);set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',58)
 '''
 for token,value in dict(NEARHANDLE=2 if a.changed_animation else 1,RANGEBYTES=len(rt),INITBASE=0x8000+len(ft),INITBYTES=len(init),SELFMODEL=a.self_model).items():setup=setup.replace(token,str(value))
 tables=[(58,0,effects),(59,0,ft+init),(60,0,rt+pt+body)];append=ASM;bindings=dict(PROFILELOAD='SourceAttackChoiceProfile4086_Load',PREPARE='SourceNormalPrepare4086_Execute')
 if a.complete_framezero:
  from script_callback_owner import derive as callback_profile,pack as pack_callback
  from source_script_clone import derive as clone_profile,pack as pack_clone
  from source_frame_effect_plan import derive as plan_profile,pack as pack_plan
  cb,code,metadata,dispatch=callback_profile(source);callbacks=pack_callback(cb);
  if a.script_framezero:
   from script_callback_owner import validate_pair
   from source_model_registry import derive as model_registry,pack as pack_registry
   validate_pair(callbacks,pack_registry(model_registry(source)),code,metadata,dispatch)
  clone=pack_clone(clone_profile(source));plan=pack_plan(plan_profile(effect_profile(source)))
  if not a.script_framezero and cb['models'][a.self_model]['program']!=65535:raise ValueError('PRESENT_SCRIPT_REQUIRES_ACTUAL_VM_PROGRAM_FIXTURE')
  tables=[(58,0,effects+callbacks+clone),(59,0,ft+init+plan),(60,0,rt+pt+body)]
  complete_setup="\n put(0x416802+c.slot*64,SELFMODEL);put(0x41f500+c.slot*20,0,4);put(0x41f504+c.slot*20,0,4);put(0x41f50c+c.slot*20,0,4);put(0x43fb00,0,4);put(sy.VmSourceWorld_Level,1)\n set('VmSourceFrame_Ready',0xb4fd);set('VmSourceFrame_Programs',PROGRAMS);set('VmSourceInstr_Ready',0xb48e);set('SourceVMRun4086_Ready',0xb4d7);set('SourceVMRun4086_Busy',0);set('VmSourceModels_Count',16);set('VmSourceCallback_Active',0)\n set('SourceAnimationCallback4086_Ready',0xb4e6);set('SourceAnimationCallback4086_State',0);set('SourceAnimationCallback4086_Base',CALLBACKBASE);set('SourceAnimationCallback4086_Bank',58);set('SourceAnimationCallback4086_Bytes',CALLBACKBYTES)\n set('SourceUpdateFrame4086_Bytes',EFFECTBYTES);set('SourceFrameMotion4086_Ready',0xb4e8);set('SourceFrameMotion4086_Status',0);set('SourceFrameEffectLeaf4086_Ready',0xb4f4)\n set('SourceFrameEffectPlan4086_Ready',0xb4f2);set('SourceFrameEffectPlan4086_State',0);set('SourceFrameEffectPlan4086_Base',PLANBASE);set('SourceFrameEffectPlan4086_Bank',59);set('SourceFrameEffectPlan4086_Bytes',PLANBYTES);set('SourceFrameEffectPlan4086_Animations',80)\n put(sy.SourceFrameEffectPlan4086_PairedCrcLo,PAIREDCRC,4);put(sy.SourceFrameEffectPlan4086_BodyCrcLo,BODYCRC,4)\n set('VmSourceWorld_TemplateCount',16);set('VmSourceVars_Ready',0xb4a4);set('VmSourceVars_Base',0x8800);set('VmSourceVars_Bank',0x41);set('VmSourceVars_Count',384)\n put(0x410000+c.slot*64,0x414000+c.slot*80,4);put(0x40902c+c.slot*64,0,4)\n set('SourceScriptClone4086_Ready',0xb5c1);set('SourceScriptClone4086_Status',0);set('SourceScriptClone4086_Base',CLONEBASE);set('SourceScriptClone4086_Bank',58);set('SourceScriptClone4086_Bytes',CLONEBYTES);set('SourceScriptClone4086_Models',16)\n"
  for token,value in dict(SELFMODEL=a.self_model,PROGRAMS=cb['program_count'],CALLBACKBASE=0x8000+len(effects),CALLBACKBYTES=len(callbacks),EFFECTBYTES=len(effects),PLANBASE=0x8000+len(ft)+len(init),PLANBYTES=len(plan),PAIREDCRC=struct.unpack_from('<I',plan,24)[0],BODYCRC=struct.unpack_from('<I',plan,28)[0],CLONEBASE=0x8000+len(effects)+len(callbacks),CLONEBYTES=len(clone)).items():complete_setup=complete_setup.replace(token,str(value))
  setup+=complete_setup
  if a.script_framezero:
   from source_script_variables import descriptor
   offsets=struct.unpack_from('<6I',metadata,24)
   tables.append((38,0,code+dispatch))
   setup+="for i,vv in ipairs(metadata)do emu.write(sy.VmCode_Wram+i-1,vv,mt)end;for j=0,24575 do emu.write(0x418800+j,0,mt)end;for i,vv in ipairs(varsdescriptor)do emu.write(sy.VmSourceVars_Ready+i-1,vv,mt)end;put(sy.VmSourceVars_Owner,0x414000+c.slot*80,4)\n"
   setup+="set('SourceAnimationCallback4086_Models',16);set('SourceAnimationCallback4086_Programs',"+str(cb['program_count'])+");set('SourceScriptClone4086_Slot',c.slot);set('SourceScriptClone4086_Model',"+str(a.self_model)+");set('VmSourceCallback_Ready',0xb4a5);set('VmSourceCallback_Request',0);set('VmState_Status',0);set('VmState_Error',0);set('VmState_FrameTop',0)\n"
   for k,vv in dict(VmSourceFrame_Base=0x8000+len(code),VmSourceFrame_Bank=38,VmSourceFrame_Bytes=len(dispatch),VmSourceFrame_Handles=80,VmSourceFrame_Pending=0,VmSourceInstr_Base=0x8000,VmSourceInstr_Bank=38,VmPriv_InstrOff=0,VmCall_CallsitesOff=offsets[2],VmCall_ArgSlotsOff=offsets[3],VmStr_StringsOff=offsets[4],VmState_InstrCount=len(code)//8,VmState_SlotCount=struct.unpack_from('<H',metadata,10)[0]).items():setup+="set('"+k+"',"+str(vv)+")\n"
   setup=setup.replace('and 2 or 18','and '+str(authored['handle'])+' or 18')
   # Canonical idle pointer and original frame number for the actual model.
   setup+="put(0x43c000+"+str(a.self_model*336)+","+str(old['handle'])+");put(0x43c000+"+str(a.self_model*336+16)+","+str(authored['handle'])+");put(0x41f510+c.slot*20,1)\n"
 if a.ai_dispatch:
  assert a.complete_framezero
  setup+="set('SourceAIRun4086_Ready',0xb5e6);set('SourceAIRun4086_State',0);set('SourceAI4086_State',0);put(sy.SourceAI4086_Endgame,0,4);put(side+20,c.time,4);put(0x42e024+c.slot*40,0,4);put(0x40902c+c.slot*64,0,4)\n"
  bindings['PREPARE']='SourceAIRun4086_Begin'
 if a.script_framezero:lua='local metadata='+luav(list(metadata))+'\nlocal varsdescriptor='+luav(list(descriptor(0x414000,count=384)))+'\n'+lua
 lua='local choicebytes='+luav(list(pt))+'\nlocal bodybytes='+luav(list(body))+'\n'+lua.replace(' before={};',setup+' before={};')
 lua=lua.replace('{{0x414000,18432}', '{{0x43e000,512},{0x41f500,2560},{0x435800,1536},{0x40bdcc,352},{0x42e000,5120},{0x416800,8192},{0x43eb00,4096},{sy.VmNativeVariant_Result,8},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18},{0x414000,18432}')
 lua+=r'''
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,PREPARE,PREPARE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()if word(sy.SourceNormalPrepare4086_Status)~=(CHANGED and 1 or 2) then emu.log('PREPFAULT|'..word(INDEX)..'|'..word(sy.SourceNormalPrepare4086_Status)..'|'..word(sy.SourceEntityRange4086_Status)..'|'..word(sy.SourceAnimationRange4086_Status)..'|'..word(sy.SourceCheckRange4086_Status)..'|'..word(sy.SourceAnimationInit4086_State))end;local st=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,PREPAREAFTER,PREPAREAFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local e=c.expected;local function expect(a,v,n)for j=0,n-1 do before[a+j]=(v>>(8*j))&255 end end
 expect(0x416824+c.slot*64,0,8);expect(0x43eb00+c.slot*32,e[3],4);expect(0x41401c+c.slot*80,e[6],4);expect(0x43900c+c.slot*80,e[5],4);expect(0x40c058+c.slot*96,e[4],4)
 if CHANGED then expect(0x416804+c.slot*64,2,2);expect(0x414014+c.slot*80,c.chosen,4);expect(0x41f508+c.slot*20,0,4);expect(0x41f510+c.slot*20,1,2);expect(0x43e004,0,4);expect(0x40c054+c.slot*96,0,4)end
 expect(sy.SourceRandom4086_SeedLo,c.seed_after,4);expect(sy.SourceRandom4086_CallsLo,(0xffffffff+c.calls)&0xffffffff,4)
 for j=17,#choicebytes do before[0x435900+j-17]=choicebytes[j]end
 for j,role in ipairs(c.options)do expect(0x435800+(j-1)*4,role,2);expect(0x435802+(j-1)*4,14-role,2)end
 local changed=0;local details='';for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1;if changed<=12 then details=details..string.format('%06x:%02x/%02x,',a,emu.read(a,mt),v)end end end
 if changed~=0 then emu.log('CHOICEDIAG|'..word(INDEX)..'|'..details)end
 emu.log('PREPCHOICE|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceNormalPrepare4086_Status)..'|'..word(sy.SourceAnimationInit4086_Number))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 if a.complete_framezero:
  append=ASM[:ASM.index('PrepareProbe_After:')]+' bcs PrepareProbe_Fail\n jsl STARTFRAME\n bcs PrepareProbe_Fail\n jsl CALLBACKBEGIN\n bcs PrepareProbe_Fail\n jsl CALLBACKRUN\n bcs PrepareProbe_Fail\n cmp #4\n bne PrepareProbe_Fail\n lda #1\n jsl FRAMEACK\n bcs PrepareProbe_Fail\n jsl EFFECTRUN\n bcs PrepareProbe_Fail\n cmp #0\n bne PrepareProbe_Fail\n jsl PREPARECONTINUE\nPrepareProbe_After:\n.a16\n.i16\n nop\n rtl\nPrepareProbe_Fail:\n.a16\n.i16\n sec\n rtl\n'
  bindings.update(STARTFRAME='SourceAnimationInit4086_StartFrame',CALLBACKBEGIN='SourceAnimationCallback4086_Begin',CALLBACKRUN='SourceAnimationCallback4086_Run',FRAMEACK='SourceUpdateFrame4086_Ack',EFFECTRUN='SourceFrameEffects4086_Run',PREPARECONTINUE='SourceNormalPrepare4086_Continue')
  lua=lua.replace('(CHANGED and 1 or 2)','2').replace('local changed=0;local details=', 'expect(0x416806+c.slot*64,0,2);expect(0x416808+c.slot*64,c.time+8,4)\n local changed=0;local details=')
 if a.script_framezero:
  append=append.replace(' jsl PROFILELOAD',' jsl SCRIPTBIND\n bcs PrepareProbe_Fail\n jsl PROFILELOAD');bindings['SCRIPTBIND']='SourceScriptClone4086_Bind'
  source_frame=next(an for an in effect_profile(source)['animations']if an['handle']==authored['handle'])['frames'][0]
  lua=lua.replace('local changed=0;local details=', 'expect(0x416830+c.slot*64,'+str(source_frame['move']['base']*65536)+',4)\n local changed=0;local details=')
  lua=lua.replace('expect(0x416804+c.slot*64,2,2)','expect(0x416804+c.slot*64,'+str(authored['handle'])+',2)').replace('c.time+8,4','c.time+'+str(authored['frames'][0]['delay_ticks'])+',4')
  # Interpreter scratch may change; source actor/VM ownership is verified below.
  lua=lua.replace('{sy.VmNativeVariant_Result,8},','')
  lua='local scriptspans=0\n'+lua.replace(' local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)',' local c=rows[word(INDEX)+1];scriptspans=0;put(EXPECTFAULT,c.fault)')
  lua+=r"""
for _,name in ipairs({'SourceScriptClone4086_Bad','SourceNormalPrepare4086_Bad','SourceAnimationCallback4086_Bad','Vm_SourceVarsValidate__bad','Vm_SourceCallbackPoll__bad','Vm_SourceFrameGate__fault','SourceVMRun4086_Rejected'})do emu.addMemoryCallback(function()
 local st=emu.getState();emu.log('AUTHOREDBAD|'..name..'|actor '..word(INDEX)..'|P '..word(sy.SourceNormalPrepare4086_Status)..'|CB '..word(sy.SourceAnimationCallback4086_State)..'|init '..word(sy.SourceAnimationInit4086_State)..'|active '..word(sy.VmSourceCallback_Active)..'|ctx '..word(sy.VmNativeVariant_ContextValid)..'|vars '..word(sy.VmSourceVars_Ready)..','..word(sy.VmSourceVars_Scope)..','..word(sy.VmSourceVars_Owner)..','..word(sy.VmSourceVars_Owner+2)..'|self '..word(sy.VmNativeVariant_Self)..','..word(sy.VmNativeVariant_Self+4)..','..word(sy.VmNativeVariant_Self+6)..'|err '..word(sy.VmState_Error)..'|busy '..word(sy.SourceVMRun4086_Busy)..'|acc '..(st['cpu.a']or -1))
end,emu.callbackType.exec,sy[name],sy[name],emu.cpuType.snes,mt)end
"""
  lua+=r"""
for _,name in ipairs({'SourceScriptClone4086_Bind','SourceNormalPrepare4086_Execute','SourceAnimationInit4086_StartFrame','SourceAnimationCallback4086_Begin','SourceAnimationCallback4086_Run','SourceVMRun4086_Call','SourceVMRun4086_Return'})do emu.addMemoryCallback(function()emu.log('AUTHOREDSTEP|'..name..'|busy '..word(sy.SourceVMRun4086_Busy)..'|status '..word(sy.VmState_Status)..'|entry '..word(sy.VmSourceFrame_Entry))end,emu.callbackType.exec,sy[name],sy[name],emu.cpuType.snes,mt)end
"""
  lua+="emu.addMemoryCallback(function()scriptspans=scriptspans+1 end,emu.callbackType.exec,sy.SourceVMRun4086_Call,sy.SourceVMRun4086_Call,emu.cpuType.snes,mt)\n"
  lua+="emu.addMemoryCallback(function()local n=0;for i,v in ipairs(metadata)do if emu.read(sy.VmCode_Wram+i-1,mt)~=v then n=n+1 end end;emu.log('PREPSCRIPT|'..word(INDEX)..'|'..scriptspans..'|'..n..'|'..word(sy.VmSourceCallback_Active)..'|'..word(sy.VmNativeVariant_ContextValid)..'|'..word(sy.SourceAnimationInit4086_State)..'|'..word(sy.VmSourceFrame_Entry))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
 if a.ai_dispatch:
  bindings['PREPARECONTINUE']='SourceAIRun4086_Continue'
  lua=lua.replace('local changed=0;local details=', 'expect(0x416814+c.slot*64,c.time,4);expect(0x42e024+c.slot*40,2,4)\n local changed=0;local details=')
  lua+="emu.addMemoryCallback(function()emu.log('PREPAICLOSE|'..word(INDEX)..'|'..word(sy.SourceAIRun4086_State)..'|'..word(sy.SourceAI4086_State)..'|'..word(sy.SourceAIRun4086_PendingKind))end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)\n"
 if a.resume_guards:
  lua+="emu.addMemoryCallback(function()local c=rows[word(INDEX)+1];put(sy.SourceAI4086_Callback,c.resume_bad=='low'and 15 or 16,4);if c.resume_bad=='high'then put(sy.SourceAI4086_Callback+2,1)end end,emu.callbackType.exec,sy.SourceNormalPrepare4086_Continue,sy.SourceNormalPrepare4086_Continue,emu.cpuType.snes,mt)\n"
  lua=lua.replace('word(sy.SourceNormalPrepare4086_Status)~=2','word(sy.SourceNormalPrepare4086_Status)~=3')
 if a.ai_dispatch:
  lua+="emu.addMemoryCallback(function()emu.log('PREPAIYIELD|'..word(INDEX)..'|'..word(sy.SourceAIRun4086_State)..'|'..word(sy.SourceAI4086_State)..'|'..word(sy.SourceAIRun4086_PendingKind))end,emu.callbackType.exec,sy.SourceAnimationInit4086_StartFrame,sy.SourceAnimationInit4086_StartFrame,emu.cpuType.snes,mt)\n"
 lua=lua.replace('CHANGED','true'if a.changed_animation else'false')
 reporter=Reporter('M4-NORMAL-PREPARE-CHOICE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'PrepareProbe','SourceNormalPrepare4086_Ready',0xb606,tables,lua,reporter,append=append,bindings=bindings,probes=dict(PREPAREAFTER='PrepareProbe_After'),batch_size=1,frame_limit=300 if a.script_framezero else 3000)
 actual=[list(map(int,l.split('PREPCHOICE|',1)[1].split('|')))for l in log.splitlines()if 'PREPCHOICE|'in l];expected=[[i,0,0,3 if c['fault']else 1 if a.changed_animation and not a.complete_framezero else 2,c['chosen']if c['chosen']>=0 else 55]for i,c in enumerate(rows)];failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 reporter.check('literal C weighted role, one unconditional RNG plus selection RNG only with choices, actual source range masks, attack flags/action, CPU/VM/CRT/siblings',len(actual)==len(rows)and not failures)
 if a.ai_dispatch:
  owners=[list(map(int,l.split('PREPAICLOSE|',1)[1].split('|')))for l in log.splitlines()if 'PREPAICLOSE|'in l];reporter.check('actual AI callback 16 pending frame-zero resumed once and closed before world tick returns',owners==[[i,2,5,0]for i in range(len(rows))]);yields=[list(map(int,l.split('PREPAIYIELD|',1)[1].split('|')))for l in log.splitlines()if 'PREPAIYIELD|'in l];reporter.check('actual action owner holds callback 16 and animation request while frame zero runs',yields==[[i,1,1,16]for i in range(len(rows))])
 if a.script_framezero:
  scripts=[list(map(int,l.split('PREPSCRIPT|',1)[1].split('|')))for l in log.splitlines()if 'PREPSCRIPT|'in l];reporter.check('actual authored attack frame-zero script binding and empty command route, immutable metadata, callback/context retired and real initializer acknowledgement',scripts==[[i,1,0,0,0,2,65535]for i in range(len(rows))])
 r=dict(schema='BYOR_4086_NORMAL_PREPARE_CHOICE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:10],authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),domain='Mutable normal-role cache maps eligible roles to actual current handle 1 and ineligible present roles to source range handle 18; special roles absent, NULL weapon, chainlength 1',normal_weights=[6,5,4,3],changed_attack_animation_yield_bound=a.changed_animation,changed_attack_frame_zero_proven=a.complete_framezero,self_model=a.self_model,actual_ai_dispatch=a.ai_dispatch,resume_callback_guards=a.resume_guards,authored_script_framezero=a.script_framezero,authored_frame_zero_empty_command_route=a.script_framezero,script_program=cb['models'][a.self_model]['program']if a.script_framezero else None,authored_attack_handle=authored['handle']if a.script_framezero else None,source_script_code_sha256=hashlib.sha256(code).hexdigest()if a.script_framezero else None,source_script_metadata_sha256=hashlib.sha256(metadata).hexdigest()if a.script_framezero else None,source_script_dispatch_sha256=hashlib.sha256(dispatch).hexdigest()if a.script_framezero else None,authored_source_frame_base=source_frame['move']['base']if a.script_framezero else None,authored_source_frame_delay=source_frame['delay_ticks']if a.script_framezero else None,common_attack_proc_executed=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
