"""Execute authored Knightbot FRAME6 until its real projectile native yield."""
import argparse,hashlib,json,struct
from pathlib import Path
from compiler import Source
from script_callback_owner import derive,pack,validate_pair
from source_model_registry import derive as registry,pack as pack_registry
from source_frame_effects_4086 import derive as effects,pack as pack_effects
from source_native_continuation import derive as continuations,pack as pack_continuations,validate_pair as pair_native
from source_world_pool import empty_pool
from source_script_variables import descriptor
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_animation_init_native import luav

ASM=r'''
ScriptedProjectileFixture:
.a16
.i16
 php
 rep #$38
 jsl FRAMEBEGIN
 bcs ScriptedProjectileFixtureBad
 cmp #1
 bne ScriptedProjectileFixtureBad
 jsl CALLBACKBEGIN
 bcs ScriptedProjectileFixtureBad
ScriptedProjectileFixtureRun:
.a16
.i16
 jsl CALLBACKRUN
 bcs ScriptedProjectileFixtureBad
 cmp #3
 bne ScriptedProjectileFixtureBad
 lda.l NATIVEPOSTED
 cmp #$B613
 bne ScriptedProjectileFixtureRun
 jsl NATIVEMATCH
 bcs ScriptedProjectileFixtureBad
ScriptedProjectileWaitProbe:
.a16
.i16
 nop
 jsl CALLBACKRUN
 bcs ScriptedProjectileFixtureBad
 cmp #3
 bne ScriptedProjectileFixtureBad
 plp
 clc
 rtl
ScriptedProjectileFixtureBad:
.a16
.i16
 plp
 sec
 rtl
'''

LUA=r'''
local waiting={}
local mt=emu.memType.snesMemory
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(j*8))&255,mt)end end
local function set(k,v,n)put(assert(sy[k],k),v,n)end
local function copy(a,t)for i,v in ipairs(t)do emu.write(a+i-1,v,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,0)
 copy(sy.VmCode_Wram,metadata);copy(0x414000,pool);copy(sy.VmSourceVars_Ready,vars)
 for j=0,8191 do emu.write(sy.VmSlots_Wram+j,0,mt)end
 for j=0,24575 do emu.write(0x418800+j,0,mt)end
 for j=0,8191 do emu.write(0x416800+j,0,mt)end
 for j=0,2815 do emu.write(0x41f500+j,0,mt)end
 local v=0x414000+c.slot*80;local side=0x416800+c.slot*64
 put(v+4,1,4);for n,tag in ipairs({2,1,1,1,1,2,2,1})do put(v+n*8,tag,4)end
 put(v+12,0,4);put(v+20,8,4);put(v+28,c.direction,4);put(v+36,100,4);put(v+52,80*65536,4);put(v+60,220*65536,4);put(v+68,100,4)
 put(side,MODEL);put(side+2,MODEL);put(side+4,HANDLE);put(side+6,5);put(0x41f510+c.slot*20,1)
 set('SourceAnimationCallback4086_Ready',0xb4e6);set('SourceAnimationCallback4086_State',0);set('SourceAnimationCallback4086_Base',CALLBACKBASE);set('SourceAnimationCallback4086_Bank',38);set('SourceAnimationCallback4086_Bytes',CALLBACKBYTES)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0);set('SourceUpdateFrame4086_Slot',c.slot);set('SourceUpdateFrame4086_Request',6);set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',58);set('SourceUpdateFrame4086_Bytes',FRAMEBYTES)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Count',128);set('VmSourceWorld_Level',1);set('VmSourceWorld_Time',48,4);set('VmSourceWorld_TemplateCount',16)
 set('VmSourceModels_Ready',0xb4a1);set('VmSourceModels_Base',MODELBASE);set('VmSourceModels_Bank',38);set('VmSourceModels_Count',16);set('VmSourceModels_Bytes',MODELBYTES);for j=0,63 do put(sy.VmSourceModels_Loaded+j,j<2 and 255 or 0,1)end
 set('VmSourceEntity_Ready',0xb48b);set('VmSourceEntity_Base',0x4000);set('VmSourceEntity_Bank',0x41);set('VmSourceEntity_Count',128);set('VmSourceMutation_Ready',0xb4a2)
 set('SourceVMRun4086_Ready',0xb4d7);set('SourceVMRun4086_Busy',0);set('VmSourceCallback_Ready',0xb4a5);set('VmSourceCallback_Active',0);set('VmSourceCallback_Request',0)
 set('VmSourceFrame_Ready',0xb4fd);set('VmSourceFrame_Base',DISPATCHBASE);set('VmSourceFrame_Bank',38);set('VmSourceFrame_Bytes',DISPATCHBYTES);set('VmSourceFrame_Programs',PROGRAMS);set('VmSourceFrame_Handles',80);set('VmSourceFrame_Pending',0)
 set('VmSourceInstr_Ready',0xb48e);set('VmSourceInstr_Base',0x8000);set('VmSourceInstr_Bank',38);set('VmPriv_InstrOff',0);set('VmCall_CallsitesOff',CALLSITES);set('VmCall_ArgSlotsOff',ARGS);set('VmStr_StringsOff',STRINGS);set('VmState_InstrCount',INSTRUCTIONS);set('VmState_SlotCount',SLOTCOUNT);set('VmState_FrameTop',0);set('VmState_Error',0);set('VmState_Status',0,1);set('VmNativeVariant_ContextValid',0)
 for _,k in ipairs({'SourceWorldTick4086_Ready','SourceClock4086_Ready','SourceFrameEffectPlan4086_Ready','SourceSelf4086_Ready','SourceFrameMotion4086_Ready','SourceAnimationInit4086_Ready','SourceModelAnimation4086_Ready','SourceModelTransition4086_Ready','SourceRetirement4086_Ready','SourceBirthCore4086_Ready','SourceLifecycle4086_Ready','SourceScriptClone4086_Ready'})do set(k,0)end
 set('SourceFrameStack4086_Ready',0xb4ed);set('SourceFrameStack4086_Depth',0);set('SourceFrameStack4086_Fault',0)
 set('SourceNativeContinuation4086_Ready',0xb612);set('SourceNativeContinuation4086_State',0);set('SourceNativeContinuation4086_Request',0);set('SourceNativeContinuation4086_Base',NATIVEBASE);set('SourceNativeContinuation4086_Bank',38);set('SourceNativeContinuation4086_Bytes',NATIVEBYTES);set('SourceNativeContinuation4086_Count',NATIVECOUNT)
 set('SourceNativeSnapshot4086_Ready',0xb614);set('SourceNativeRequest4086_Ready',0xb615);set('SourceNamedKnife4086_Ready',0xb611);set('SourceCtorState4086_Ready',0xb5c2);set('SourceSpawnSlot4086_Ready',0xb5a1)
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local wait_changes=0;for addr,value in pairs(waiting)do if emu.read(addr,mt)~=value then wait_changes=wait_changes+1 end end;emu.log('SCRIPTWAIT|'..word(INDEX)..'|'..wait_changes)
 local c=rows[word(INDEX)+1];emu.log('SCRIPTSTATE|'..word(sy.SourceAnimationCallback4086_Fault)..'|'..word(sy.VmState_Error)..'|'..word(sy.SourceVMRun4086_Ready)..'|'..word(sy.SourceVMRun4086_Status)..'|'..word(sy.SourceVMRun4086_Error)..'|'..word(sy.VmSourceFrame_Ready)..'|'..word(sy.SourceAnimationCallback4086_Program));local live=0;for j=0,127 do live=live+word(0x414004+j*80)end
 emu.log('SCRIPTEDPROJECTILE|'..word(INDEX)..'|'..word(sy.SourceNativeContinuation4086_State)..'|'..word(sy.SourceNativeContinuation4086_Record)..'|'..word(sy.SourceNativeContinuation4086_Request)..'|'..word(sy.SourceSpawnSlot4086_Model)..'|'..dw(sy.SourceCtorState4086_X)..'|'..dw(sy.SourceCtorState4086_Z)..'|'..dw(sy.SourceCtorState4086_A)..'|'..dw(sy.SourceCtorState4086_Direction)..'|'..word(sy.VmState_Ip)..'|'..word(sy.VmState_FrameTop)..'|'..word(sy.SourceUpdateFrame4086_Pending)..'|'..live)
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()set('VmState_Status',4,1);set('VmSourceCallback_Active',0);set('SourceUpdateFrame4086_Ready',0);set('SourceAnimationCallback4086_Ready',0)end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()waiting={};for _,range in ipairs({{0x7fc000,8192},{0x7fe090,20},{0x7fe100,768}})do for j=0,range[2]-1 do waiting[range[1]+j]=emu.read(range[1]+j,mt)end end end,emu.callbackType.exec,WAITPROBE,WAITPROBE,emu.cpuType.snes,mt)
local ctor_guard='none'
for k,v in pairs(sy)do if k:match('^SourceCtorState4086_Guard')or k:match('^SourceFrameStack4086_')or k:match('^SourceNativeSnapshot4086_')then local name=k;emu.addMemoryCallback(function()ctor_guard=name end,emu.callbackType.exec,v,v,emu.cpuType.snes,mt)end end
for k,v in pairs(sy)do if k=='Vm_FetchSourceInit'or k=='SourceAnimationCallback4086_CloseFault'or k=='SourceAnimationCallback4086_Bad'or k=='SourceFrameStack4086_Bad'or k=='SourceCtorOwner4086_Bad'or k=='SourceCtorOwner4086_BeginBad'or k=='SourceCtorState4086_Bad'or k=='SourceNativeResult4086_Bad'or k=='SourceNativeContinuation4086_Bad'or k=='SourceNativeSnapshot4086_Bad'then emu.addMemoryCallback(function()emu.log('SCRIPTTRACE|'..k..'|'..word(sy.SourceVMRun4086_Ready)..'|'..ctor_guard..'|clone='..word(sy.SourceScriptClone4086_Status)..'|model='..word(sy.SourceCtorModel4086_Status)..'|offscreen='..word(sy.SourceOffscreenState4086_Ready)..'|cost='..word(sy.SourceAttackCostState4086_Ready))end,emu.callbackType.exec,v,v,emu.cpuType.snes,mt)end end
'''


CTOR_OBSERVER=r'''
emu.addMemoryCallback(function()
 local i=word(INDEX);local cs=word(sy.SourceNamedKnife4086_Child);local side=0x416800+cs*64;local v=0x414000+cs*80;local core=0x40c000+cs*96;local life=0x439000+cs*80;local dest=sy.VmSlots_Wram+8*word(sy.SourceNativeContinuation4086_ResultSlot)
 emu.log('ACTUALPROJECTILECTOR|'..i..'|'..word(sy.SourceFrameStack4086_Depth)..'|'..word(sy.SourceFrameStack4086_Fault)..'|'..cs..'|'..word(dest)..'|'..word(dest+2)..'|'..dw(dest+4)..'|'..dw(core+72)..'|'..dw(v+52)..'|'..dw(v+60)..'|'..dw(v+12)..'|'..word(v+4)..'|'..dw(0x409008+cs*64)..'|'..dw(0x43d600+cs*4)..'|'..dw(0x43d800+cs*4))
end,emu.callbackType.exec,AFTERCHILD,AFTERCHILD,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','source','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--constructor',action='store_true');p.add_argument('--from-frame-zero',action='store_true');p.add_argument('--audio-source',type=Path);p.add_argument('--isolate-audio',action='store_true');p.add_argument('--idle-audio-pump',action='store_true');p.add_argument('--spc-driver',type=Path);p.add_argument('--prefill-audio',action='store_true');p.add_argument('--audio-arm-guard',action='store_true');a=p.parse_args();assert not a.from_frame_zero or a.constructor;assert not a.audio_source or a.from_frame_zero;assert not(a.isolate_audio or a.idle_audio_pump or a.spc_driver or a.prefill_audio or a.audio_arm_guard)or a.audio_source;a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);source=Source(a.source)
 owner,code,meta,dispatch=derive(source);callbacks=pack(owner);reg=registry(source);models=pack_registry(reg);validate_pair(callbacks,models,code,meta,dispatch)
 nr,ncode,nmeta=continuations(source);assert(code,meta)==(ncode,nmeta);native=pack_continuations(nr);pair_native(native,code,meta)
 er=effects(source);fe=pack_effects(er);an=next(x for x in er['animations']if x['model']=='Knightbot'and x['role']=='attack1');model=next(x['id']for x in reg['models']if x['identity']=='Knightbot');child=next(x['id']for x in reg['models']if x['identity']=='ShockBall')
 bundle=bytearray(code);locations={}
 for name,data in [('dispatch',dispatch),('models',models),('callbacks',callbacks),('native',native)]:locations[name]=0x8000+len(bundle);bundle.extend(data)
 ctorprefix=ctorsetup='';ctorplan=b'';walkid=0
 if a.constructor:
  from m4_projectile_ctor_fixture import resources
  ctorplan,ctorprefix,ctorsetup,walkid=resources(source,er,bundle,locations)
 assert len(bundle)<=32768
 rows=[dict(slot=s,direction=d,fault=0)for s in (0,1,95,96,127)for d in (0,1)]
 if a.audio_source:rows=rows[:1]
 values=dict(MODEL=model,HANDLE=an['handle'],FRAMEBYTES=len(fe),CALLBACKBASE=locations['callbacks'],CALLBACKBYTES=len(callbacks),MODELBASE=locations['models'],MODELBYTES=len(models),DISPATCHBASE=locations['dispatch'],DISPATCHBYTES=len(dispatch),PROGRAMS=owner['program_count'],NATIVEBASE=locations['native'],NATIVEBYTES=len(native),NATIVECOUNT=len(nr['records']),CALLSITES=struct.unpack_from('<I',meta,32)[0],ARGS=struct.unpack_from('<I',meta,36)[0],STRINGS=struct.unpack_from('<I',meta,40)[0],INSTRUCTIONS=len(code)//8,SLOTCOUNT=struct.unpack_from('<H',meta,10)[0])
 lua='local metadata='+luav(list(meta))+'\nlocal pool='+luav(list(empty_pool()[0]))+'\nlocal vars='+luav(list(descriptor(0x414000,count=384)))+'\n'+LUA
 if a.constructor:
  from source_animation_energy_4086 import derive as energy
  assert next(x for x in energy(source)['animations']if x['model']=='Knightbot'and x['role']=='attack1')['fields']['cost']==0
  lua=ctorprefix+lua
  lua=lua.replace("set('SourceSpawnSlot4086_Ready',0xb5a1)\nend","set('SourceSpawnSlot4086_Ready',0xb5a1)\n"+ctorsetup+'\nend')
 import re
 for key,value in values.items():lua=re.sub(r'\b'+key+r'\b',str(value),lua)
 asm=ASM;tables=[(38,0,bytes(bundle)),(58,0,fe)];bindings=dict(FRAMEBEGIN='SourceUpdateFrame4086_Begin',CALLBACKBEGIN='SourceAnimationCallback4086_Begin',CALLBACKRUN='SourceAnimationCallback4086_Run',NATIVEPOSTED='SourceNativeContinuation4086_Request',NATIVEMATCH='SourceNativeContinuation4086_Match');probes={'WAITPROBE':'ScriptedProjectileWaitProbe'};fixture_hooks={}
 if a.constructor:
  from m4_projectile_ctor_fixture import CONSTRUCT,BINDINGS
  asm=asm.replace(' plp\n clc\n rtl',CONSTRUCT.replace('WALKID',str(walkid))+' plp\n clc\n rtl',1);bindings.update(BINDINGS);tables.append((59,0,ctorplan));probes['AFTERCHILD']='ScriptedProjectileAfterChild';probes['WAITOBSERVED']='ScriptedProjectileWaitObserved'
  asm=asm.replace(' lda.l PARENTSLOT','ScriptedProjectileWaitObserved:\n.a16\n.i16\n nop\n lda.l PARENTSLOT')
  if a.from_frame_zero:
   from m4_projectile_timed_fixture import resources as timed_resources, PRELUDE, BINDINGS as TIMED_BINDINGS
   timed_setup,timed_observer,timed_table=timed_resources(source,fe)
   init_end='end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)'
   assert lua.count(init_end)==1
   lua=lua.replace(init_end,timed_setup+'\n'+init_end);lua+=timed_observer
   asm=asm.replace('ScriptedProjectileFixtureRun:',PRELUDE+'ScriptedProjectileFixtureRun:',1)
   bindings.update(TIMED_BINDINGS);tables.append(timed_table);probes['NATURALTICK']='ScriptedProjectileNaturalTick'
  if a.audio_source:
   from m4_projectile_audio_fixture import configure, SERVICE, NEAR, BINDINGS as AUDIO_BINDINGS, OBSERVER
   from actor_s5_entity_fixture import symbols
   sy=symbols(Path('src/main.sym'))
   sound=an['frames'][6]['sound'];audio_row,transform,before,closeout=configure(a.output,a.audio_source.resolve(),sound,a.isolate_audio,a.idle_audio_pump,a.spc_driver,a.prefill_audio,a.audio_arm_guard)
   audio_asm=SERVICE.replace('SOUNDINDEX',str(audio_row['sound_index']))
   asm=asm.replace('ScriptedProjectileConstructorDone:\n.a16\n.i16\n','ScriptedProjectileConstructorDone:\n.a16\n.i16\n'+audio_asm)
   asm+=NEAR.replace('NEARRELAY',str((sy['Tad_ProcessMaybeStream__return']&65535)-1)).replace('NEARBANK',str(sy['AudioSemantic_StreamBackendPolicy']>>16)).replace('NEARTARGET',str((sy['AudioSemantic_StreamBackendPolicy']&65535)-1))
   bindings.update(AUDIO_BINDINGS);probes['AFTERAUDIO']='ScriptedProjectileAfterAudio';lua+=OBSERVER
   if not a.idle_audio_pump and 'Tad_StreamWaitFrame' in sy:
    from m4_projectile_audio_fixture import WAIT_CONTEXT_BINDINGS, WAIT_CONTEXT_OBSERVER
    bindings.update(WAIT_CONTEXT_BINDINGS);lua+=WAIT_CONTEXT_OBSERVER
   if a.idle_audio_pump:
    from m4_projectile_audio_fixture import IDLE, IDLE_BINDINGS
    asm+=IDLE.replace('WAITRETURN',str(sy['Core_Nmi_WaitFrame__loop']+6));bindings.update(IDLE_BINDINGS)
   if a.audio_arm_guard:
    from m4_projectile_audio_fixture import ARM_GUARD, ARM_BINDINGS
    asm+=ARM_GUARD;bindings.update(ARM_BINDINGS)
   fixture_hooks=dict(rom_transform=transform,before_start=before,closeout=closeout,emulator_env={'MESEN_VOICE_CAPTURE_PATH':str(a.output/'voice0.raw'),'MESEN_VOICE_CAPTURE_VOICE':'0','MESEN_VOICE_CAPTURE_ARM_FILE':str(a.output/'voice0.raw.arm')})
  # Relax distant fixture rejection branches with explicit-width trampolines.
  counter=[0]
  def relax(m):
   counter[0]+=1;label='ScriptedProjectileRelax'+str(counter[0]);op={'bcs':'bcc','bcc':'bcs','beq':'bne','bne':'beq'}[m[1]]
   return ' '+op+' '+label+'\n jmp '+m[2]+'\n'+label+':\n.a16\n.i16'
  asm=re.sub(r'^ (bcs|bcc|beq|bne) (ScriptedProjectileFixtureBad(?:Stack)?)$',relax,asm,flags=re.M)
  lua=lua.replace("emu.log('SCRIPTWAIT|'..word(INDEX)..'|'..wait_changes)",'')
  lua+=CTOR_OBSERVER
  lua+=r'''
emu.addMemoryCallback(function()local changed=0;for addr,value in pairs(waiting)do if emu.read(addr,mt)~=value then changed=changed+1 end end;emu.log('SCRIPTWAIT|'..word(INDEX)..'|'..changed)end,emu.callbackType.exec,WAITOBSERVED,WAITOBSERVED,emu.cpuType.snes,mt)
'''
 audio_verification=None
 r=Reporter('M4-SCRIPTED-PROJECTILE-CONSTRUCTOR'if a.constructor else'M4-SCRIPTED-PROJECTILE-REQUEST',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'ScriptedProjectileFixture','SourceNativeRequest4086_Ready',0xb615,tables,lua,r,append=asm,bindings=bindings,batch_size=1,probes=probes,frame_limit=200,**fixture_hooks)
 actual=[list(map(int,l.split('SCRIPTEDPROJECTILE|',1)[1].split('|')))for l in log.splitlines()if'SCRIPTEDPROJECTILE|'in l]
 if a.constructor:
  actual_ctor=[list(map(int,l.split('ACTUALPROJECTILECTOR|',1)[1].split('|')))for l in log.splitlines()if'ACTUALPROJECTILECTOR|'in l]
  expected_ctor=[]
  for i,c in enumerate(rows):
   cs=1 if c['slot']==0 else 0;token=0x414000+cs*80;expected_ctor.append([i,0,0,cs,5,0,token,2,80*65536,221*65536,34*65536,1,0x414000+c['slot']*80,30,0])
  r.check('actual named ShockBall allocation/model/script/default frame services/knife post; paired VM restoration and complete PTR; parent self retained',actual_ctor==expected_ctor)
 else:actual_ctor=expected_ctor=[]
 waits=[list(map(int,l.split('SCRIPTWAIT|',1)[1].split('|')))for l in log.splitlines()if'SCRIPTWAIT|'in l]
 natural=[list(map(int,l.split('NATURALFRAME|',1)[1].split('|')))for l in log.splitlines()if'NATURALFRAME|'in l]
 if a.from_frame_zero:r.check('authored frame zero seta sets BASE40 without altitude mutation; actual timed frames 1 through 6, sixteen-tick delays; no pending effects before next tick',natural==[[i,f,48+16*f,64+16*f,0,40*65536,0]for i in range(len(rows))for f in range(6)])
 r.check('posted native prevents early VM resume; IP, budget, call frames and all slots unchanged on repeated callback Run',waits==[[i,0]for i in range(len(rows))])
 expected=[]
 for i,c in enumerate(rows):
  match=next((j,n)for j,n in enumerate(nr['records'])if n['model']=='Knightbot'and n['native_name']=='projectile')
  j,n=match;expected.append([i,2,j,0xb613,child,80*65536,221*65536,34*65536,c['direction'],n['resume_ip'],len(n['frame_callsites']),1,1])
 if a.constructor:
  actual_final=[v for v in actual];r.check('authored caller resumes and closes callback after constructor; parent effects completion matches requested service scope',all(v[-2:]==[0 if a.audio_source else 2,2]for v in actual_final)and len(actual_final)==len(rows))
  if a.audio_source:
   requests=[list(map(int,l.split('SOURCEAUDIOREQUEST|',1)[1].split('|')))for l in log.splitlines()if'SOURCEAUDIOREQUEST|'in l]
   r.check('source sound namespace -> real TAD stream request, exact compiled payload length/chunk count',requests==[[1,audio_row['brr_bytes'],(audio_row['brr_bytes']+143)//144]])
   if a.isolate_audio and a.prefill_audio:
    from m4_source_audio_native_verify import verify
    audio_verification=verify(a.output,a.audio_source.resolve(),require_dsp_trace=True)
    if not a.idle_audio_pump and 'Tad_StreamWaitFrame' in sy:
     contexts=[list(map(int,l.split('SOURCEAUDIOWAITCTX|',1)[1].split('|')))for l in log.splitlines()if'SOURCEAUDIOWAITCTX|'in l]
     r.check('shared foreground wait preserves A/X/Y/D/DBR/SP and original REP/CMP flags across real NMI and active stream',len(contexts)>=40 and all(v[1]==0 for v in contexts))
     audio_verification['shared_wait_context_observations']=len(contexts);audio_verification['shared_wait_context_faults']=sum(v[1]for v in contexts)
    r.check('private stream: all BRR bytes, padding, voice0 pitch/gain, continuous full-duration envelope and END; no observed producer underrun',audio_verification['status']=='PASS')
 else:r.check('actual source FRAME6, real bytecode/script CALL frame, typed model/coordinate/direction request, cooperative yield and exact native continuation identity; no child allocated',actual==expected)
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_SCRIPTED_PROJECTILE_REQUEST_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),wait_observations=waits,natural_frame_observations=natural,from_authored_frame_zero=a.from_frame_zero,actual=actual,expected=expected,rom_sha256=hashlib.sha256(raw).hexdigest(),source_model='Knightbot',source_frame=6,compiled_source_sha256=hashlib.sha256(code+meta+dispatch).hexdigest(),source_stage_context_instrumented=True,source_self_global_lease_disabled=not a.constructor,constructor_executed=a.constructor,constructor_observations=actual_ctor,constructor_expected=expected_ctor,source_frame_audio_request_executed=bool(a.audio_source),source_frame_audio_executed=audio_verification is not None,audio_verification=audio_verification,motu_gameplay_proven=False,no_color_reduction=True),indent=2)+'\n');r.finish()

if __name__=='__main__':main()
