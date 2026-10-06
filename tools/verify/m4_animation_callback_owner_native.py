"""Execute authored He_ManB frame callbacks through the native world owner.

Exclusive source pool after ordinary bootstrap; subsequent effect/audio service
is instrumented. This certifies callback ownership and source birth, not MOTU
player initialization, effect presentation, combat or Demo completion.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from script_callback_owner import derive,pack,validate_pair
from source_frame_effects_4086 import derive as frame_effects,pack as pack_effects
from source_model_registry import derive as model_registry,pack as pack_registry
from source_birth_templates import derive as birth_templates,pack as pack_birth
from source_birth_core import derive as birth_core,pack as pack_core,STRIDE as CORE_STRIDE
from source_world_pool import empty_pool
from source_script_variables import descriptor
from script_dispatch_4086 import compile_source
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

REQUEST,INDEX,ERROR=0x7ffb80,0x7ffb82,0x7ffb84


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--effects-runner',action='store_true',help='Use real paired B4EP/motion/quake/self retirement; sound service instrumented.')
    p.add_argument('--birth-core',action='store_true',help='Execute actual B4BI core/flags/relation birth augmentation.')
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);source=Source(a.source)
    owners,code,metadata,dispatch=derive(source);callbacks=pack(owners)
    registry=model_registry(source);models=pack_registry(registry);births=pack_birth(birth_templates(source))
    coretable=pack_core(birth_core(source)) if a.birth_core else b''
    if a.birth_core and not a.effects_runner:raise ValueError('BIRTH_CORE_REQUIRES_REAL_SELF_OWNER')
    validate_pair(callbacks,models,code,metadata,dispatch)
    effects=frame_effects(source);frames=pack_effects(effects)
    if a.effects_runner:
        from source_frame_effect_plan import derive as derive_plan,pack as pack_plan,unpack as unpack_plan
        plan=pack_plan(derive_plan(effects));unpack_plan(plan,frames)
    actor=next(m['id'] for m in registry['models'] if m['identity']=='He_ManB')
    default=next(m['id'] for m in registry['models'] if m['identity']=='He_Man')
    breath=next(m['id'] for m in registry['models'] if m['identity']=='HBreath')
    animation=next(h for h in compile_source(source)['animation_handles'] if h['model']=='He_ManB' and h['role']=='freespecial4')
    rows=[dict(f=f,direction=d,default=default,fault=0) for f in (3,4) for d in (0,1)]
    rows += [dict(f=4,direction=1,default=actor,fault=0),dict(f=4,direction=1,default=default,fault=1)]
    rows.insert(1,dict(f=3,direction=0,default=default,fault=0,warm=1))
    rows.insert(5,dict(f=4,direction=1,default=default,fault=0,warm=1))
    sy=symbols(Path('src/main.sym'));raw=bytearray(a.rom.read_bytes());entry=sy['Vm_SourceFrameGate']
    first=39*32768
    if raw[first:first+32768]!=bytes(32768) or raw[60*32768:61*32768]!=bytes(32768):raise ValueError('CALLBACK_NATIVE_RESERVED_ROM')
    base=sy['SourceVM_InstructionReservation'];at=offset(base)
    if raw[at:at+32768]!=b'\xff'*32768:raise ValueError('CALLBACK_NATIVE_SCRIPT_RESERVATION')
    cursor=0;locations={}
    for name,data in [('code',code),('dispatch',dispatch),('models',models),('births',births),('callbacks',callbacks)]:
        locations[name]=base+cursor;raw[at+cursor:at+cursor+len(data)]=data;cursor+=len(data)
    if coretable:
        locations['birthcore']=base+cursor;raw[at+cursor:at+cursor+len(coretable)]=coretable;cursor+=len(coretable)
    if cursor>32768:raise ValueError('CALLBACK_NATIVE_IMMUTABLE_BANK_CAPACITY')
    raw[60*32768:60*32768+len(frames)]=frames
    if a.effects_runner:
        if raw[59*32768:60*32768]!=bytes(32768):raise ValueError('CALLBACK_PLAN_PRIVATE_BANK')
        raw[59*32768:59*32768+len(plan)]=plan
    asm='''.snes
.bank 39
.org $8000
CallbackFixture_Gate:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l REQUEST
 cmp #$B4E7
 bne CallbackFixture_Return
 lda #0
 sta.l REQUEST
 sta.l INDEX
 sta.l ERROR
CallbackFixture_Init:
.a16
.i16
 nop
 jsl FRAMEBEGIN
 bcs CallbackFixture_Bad
 cmp #1
 bne CallbackFixture_Bad
CallbackFixture_BeforeOwner:
.a16
.i16
 nop
 jsl CALLBACKBEGIN
 bcs CallbackFixture_Bad
CallbackFixture_Run:
.a16
.i16
 jsl CALLBACKRUN
 bcs CallbackFixture_ExpectedFault
 cmp #3
 beq CallbackFixture_Run
 cmp #4
 bne CallbackFixture_Bad
 lda #1
 jsl FRAMEACK
 bcs CallbackFixture_Bad
 cmp #2
 bne CallbackFixture_Bad
CallbackFixture_AfterScript:
.a16
.i16
 nop
 ; Subsequent audio/effect service remains instrumented in this proof.
 lda #2
 jsl FRAMEACK
 bcs CallbackFixture_Bad
 jmp CallbackFixture_Result
CallbackFixture_ExpectedFault:
.a16
.i16
 lda.l EXPECTFAULT
 beq CallbackFixture_Bad
 jsl CHECKIDLE
 bcc CallbackFixture_Bad
 jsl CLOCKCOMMIT
 bcc CallbackFixture_Bad
CallbackFixture_Result:
.a16
.i16
 nop
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #CASES
 bcc CallbackFixture_Init
 bra CallbackFixture_Done
CallbackFixture_Bad:
.a16
.i16
 lda #1
 sta.l ERROR
CallbackFixture_Done:
.a16
.i16
 lda #0
 sta.l CALLBACKREADY
 sta.l FRAMEREADY
 sta.l WORLDREADY
 sta.l CONTEXTVALID
CallbackFixture_Return:
.a16
.i16
 ply
 plx
 plp
 php
 rep #$31
 phx
 phy
 jml RESUME
'''
    if a.effects_runner:
        begin=asm.index(' ; Subsequent audio/effect service');end=asm.index(' jmp CallbackFixture_Result',begin)
        asm=asm[:begin]+'''CallbackFixture_Effects:
.a16
.i16
 jsl EFFECTRUN
 bcs CallbackFixture_Bad
 cmp #0
 beq CallbackFixture_EffectsDone
 cmp #9
 bne CallbackFixture_Bad
CallbackFixture_AudioService:
.a16
.i16
 nop
 lda #9
 sta.l EFFECTACKWORD
 jsl EFFECTACK
 bcs CallbackFixture_Bad
 jmp CallbackFixture_Effects
CallbackFixture_EffectsDone:
.a16
.i16
 jsl CLOCKCOMMIT
 bcs CallbackFixture_Bad
'''+asm[end:]
    values=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,FRAMEBEGIN=sy['SourceUpdateFrame4086_Begin'],
        FRAMEACK=sy['SourceUpdateFrame4086_Ack'],CALLBACKBEGIN=sy['SourceAnimationCallback4086_Begin'],
        CALLBACKRUN=sy['SourceAnimationCallback4086_Run'],CALLBACKREADY=sy['SourceAnimationCallback4086_Ready'],
        FRAMEREADY=sy['SourceUpdateFrame4086_Ready'],WORLDREADY=sy['VmSourceWorld_Ready'],
        CONTEXTVALID=sy['VmNativeVariant_ContextValid'],RESUME=entry+5,CASES=len(rows))
    values.update(EXPECTFAULT=0x7ffb86,CHECKIDLE=sy['SourceUpdateFrame4086_CheckIdle'],CLOCKCOMMIT=sy['SourceClock4086_Commit'])
    if a.effects_runner:values.update(EFFECTRUN=sy['SourceFrameEffects4086_Run'],EFFECTACK=sy['SourceFrameEffectPlan4086_Ack'],EFFECTACKWORD=sy['SourceFrameEffectPlan4086_Acknowledged'])
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm)
    branch=[0]
    def relax(m):
        branch[0]+=1;label='CallbackFixture_Branch_'+str(branch[0])
        return ' '+dict(bcc='bcs',bcs='bcc',beq='bne',bne='beq')[m[1]]+' '+label+'\n jmp '+m[2]+'\n'+label+':\n.a16\n.i16'
    asm=re.sub(r'^ (bcc|bcs|beq|bne) (CallbackFixture_\w+)$',relax,asm,flags=re.M)
    pasm=folder/'callback_fixture.pasm';pasm.write_text(asm)
    built=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',
        str(pasm),'--output',str(folder/'callback_fixture.bin'),'--symbols',str(folder/'callback_fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(built.stdout+built.stderr)
    if built.returncode:raise ValueError('CALLBACK_FIXTURE_ASSEMBLY')
    fs=symbols(folder/'callback_fixture.sym');fixture=(folder/'callback_fixture.bin').read_bytes()[first:]
    if raw[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a') or len(fixture)>32768:raise ValueError('CALLBACK_FIXTURE_GATE')
    raw[first:first+len(fixture)]=fixture
    raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['CallbackFixture_Gate'])[:3]+b'\xea'
    path=folder/'bor.sfc';path.write_bytes(raw)
    for media in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor-*.pcm')]:
        target=folder/media.name
        if not target.exists():os.link(media.resolve(),target)
    pool,sides=empty_pool(128)
    initial_meta=metadata
    lua='local rows={'+','.join('{'+','.join(k+'='+str(v) for k,v in c.items())+'}' for c in rows)+'}\n'
    lua+='local sy={'+','.join(k+'='+str(v) for k,v in sy.items() if k.startswith(('Source','Vm'))) +'}\n'
    lua+='local metadata={'+','.join(map(str,initial_meta))+'}\n'
    lua+='local pool={'+','.join(map(str,pool))+'}\n'
    lua+='local vars_descriptor={'+','.join(map(str,descriptor(0x414000,count=384)))+'}\n'
    if coretable:lua+='local birthcore={'+','.join(map(str,coretable[24+breath*CORE_STRIDE+16:24+(breath+1)*CORE_STRIDE]))+'}\n'
    lua+=r'''
local mt=emu.memType.snesMemory;local spans=0;local context_faults=0;local before_call={};local owner_start=0;local owner_field=0
local init_faults=0;local copy_checks=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for j=0,n-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n or 2)end
local function copy(a,data)for i,v in ipairs(data)do emu.write(a+i-1,v,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];spans=0;context_faults=0;init_faults=0;copy_checks=0
 put(0x7ffb86,c.fault,2)
 copy(sy.VmCode_Wram,metadata);copy(0x414000,pool)
 for j=0,8191 do emu.write(0x416800+j,0,mt)end
 if not c.warm then for j=0,24575 do emu.write(0x418800+j,0,mt)end end
 for j=0,2815 do emu.write(0x41f500+j,0,mt)end
 copy(sy.VmSourceVars_Ready,vars_descriptor)
 set('SourceAnimationCallback4086_Ready',0xb4e6);set('SourceAnimationCallback4086_State',0)
 set('SourceAnimationCallback4086_Base',CALLBACKBASE);set('SourceAnimationCallback4086_Bank',CODEBANK)
 set('SourceAnimationCallback4086_Bytes',CALLBACKBYTES)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0)
 set('SourceUpdateFrame4086_Slot',0);set('SourceUpdateFrame4086_Request',c.f)
 set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',60);set('SourceUpdateFrame4086_Bytes',FRAMEBYTES)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800)
 set('VmSourceWorld_Count',128);set('VmSourceWorld_Level',1);set('VmSourceWorld_Time',48,4)
 set('VmSourceWorld_TemplateBase',BIRTHBASE);set('VmSourceWorld_TemplateBank',CODEBANK)
 set('VmSourceWorld_TemplateCount',MODELCOUNT);set('VmSourceWorld_TemplateBytes',BIRTHBYTES)
 set('VmSourceWorld_Players',1);set('VmSourceWorld_AdvanceX',0,4);set('VmSourceWorld_AdvanceY',0,4);set('VmSourceWorld_ScrollAxis',0)
 set('VmSourceModels_Ready',0xb4a1);set('VmSourceModels_Base',MODELBASE);set('VmSourceModels_Bank',CODEBANK)
 set('VmSourceModels_Count',MODELCOUNT);set('VmSourceModels_Bytes',MODELBYTES)
 for j=0,63 do emu.write(sy.VmSourceModels_Loaded+j,j<2 and 255 or 0,mt)end
 set('VmSourceEntity_Ready',0xb48b);set('VmSourceEntity_Base',0x4000);set('VmSourceEntity_Bank',0x41);set('VmSourceEntity_Count',128)
 set('VmSourceMutation_Ready',0xb4a2);set('SourceToss4086_Ready',0xb4e2)
 set('SourceVMRun4086_Ready',0xb4d7);set('SourceVMRun4086_Busy',0)
 set('VmSourceCallback_Ready',0xb4a5);set('VmSourceCallback_Active',0);set('VmSourceCallback_Request',0)
 set('VmSourceFrame_Ready',0xb4fd);set('VmSourceFrame_Base',DISPATCHBASE);set('VmSourceFrame_Bank',CODEBANK)
 set('VmSourceFrame_Bytes',DISPATCHBYTES);set('VmSourceFrame_Programs',PROGRAMCOUNT);set('VmSourceFrame_Handles',80);set('VmSourceFrame_Pending',0)
 set('VmSourceInstr_Ready',0xb48e);set('VmSourceInstr_Base',0x8000);set('VmSourceInstr_Bank',CODEBANK)
 set('VmPriv_InstrOff',0);set('VmCall_CallsitesOff',CALLSITES);set('VmCall_ArgSlotsOff',ARGS);set('VmStr_StringsOff',STRINGS)
 set('VmState_InstrCount',INSTRUCTIONS);set('VmState_SlotCount',SLOTS);set('VmState_FrameTop',0);set('VmState_Error',0);set('VmState_Status',0,1)
 set('VmNativeVariant_ContextValid',0);set('SourceWorldTick4086_Ready',0);set('SourceClock4086_Ready',0)
 set('SourceFrameEffectPlan4086_Ready',0);set('SourceSelf4086_Ready',0);set('SourceFrameMotion4086_Ready',0)
 set('SourceAnimationInit4086_Ready',0);set('SourceModelAnimation4086_Ready',0);set('SourceModelTransition4086_Ready',0);set('SourceFrameStack4086_Ready',0)
 set('SourceRetirement4086_Ready',0)
 set('SourceBirthCore4086_Ready',0)
 INSTALL_EFFECT_RUNNER
 INSTALL_BIRTH_CORE
 put(0x414004,1,2)
 for n,tag in ipairs({2,1,1,1,1,2,2,1})do put(0x414000+8*n,tag,4)end
 put(0x414014,ANIMATIONID,4);put(0x41401c,c.direction,4);put(0x414024,150,4)
 put(0x414034,80*65536,4);put(0x41403c,220*65536,4);put(0x414044,150,4)
 put(0x416800,ACTORID,2);put(0x416802,c.default,2);put(0x416804,HANDLE,2)
 put(0x41f510,1,2)
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 local state=emu.getState();owner_start=state.masterClock;owner_field=state['ppu.frameCount']
 if c.fault==1 then
  set('VmSourceWorld_TemplateBase',BIRTHBASE+2)
  set('SourceClock4086_Ready',0xb4c5);set('SourceClock4086_Due',1);set('SourceClock4086_TimeLo',48,4)
 end
end,emu.callbackType.exec,BEFOREOWNER,BEFOREOWNER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();before_call={}
 if emu.read(sy.VmState_Status,mt)==1 then
  local source=sy.VmCode_Wram+word(sy.SourceAnimationCallback4086_Initializers)
  local target=sy.VmSlots_Wram+8*word(sy.SourceAnimationCallback4086_SlotBase)
  local bytes=8*word(sy.SourceAnimationCallback4086_Slots)
  for i=0,bytes-1 do if emu.read(source+i,mt)~=emu.read(target+i,mt)then init_faults=init_faults+1 end end
  copy_checks=copy_checks+1
 end
 for _,k in ipairs({'x','y','d','dbr','sp','ps'})do before_call[k]=s['cpu.'..k]end
end,emu.callbackType.exec,RUNENTRY,RUNENTRY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();spans=spans+1
 for _,k in ipairs({'x','y','d','dbr'})do if before_call[k]~=s['cpu.'..k]then context_faults=context_faults+1 end end
 if before_call.sp+3~=s['cpu.sp'] or (before_call.ps&254)~=(s['cpu.ps']&254)then context_faults=context_faults+1 end
end,emu.callbackType.exec,RUNRETURN,RUNRETURN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local live=0;local local_faults=0
 for j=0,127 do live=live+word(0x414004+80*j)end
 for j=0,3 do for k=0,7 do if emu.read(0x418808+64*j+k,mt)~=0 then local_faults=local_faults+1 end end end
 emu.log('CALLBACKOWNER|'..word(INDEX)..'|'..word(sy.SourceAnimationCallback4086_State)..'|'..word(sy.SourceAnimationCallback4086_Status)..'|'..word(sy.VmSourceCallback_Active)..'|'..word(sy.VmNativeVariant_ContextValid)..'|'..word(sy.SourceUpdateFrame4086_Pending)..'|'..live..'|'..dw(0x414050+12)..'|'..dw(0x414050+52)..'|'..dw(0x414050+60)..'|'..spans..'|'..context_faults..'|'..local_faults..'|'..word(0x416840)..'|'..dw(0x41684c))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local state=emu.getState()
 emu.log('CALLBACKCOST|'..word(INDEX)..'|'..(state.masterClock-owner_start)..'|'..owner_field..'|'..state['ppu.frameCount'])
 for i,v in ipairs(metadata)do if emu.read(sy.VmCode_Wram+i-1,mt)~=v then init_faults=init_faults+1 end end
 emu.log('CALLBACKINIT|'..word(INDEX)..'|'..init_faults..'|'..copy_checks)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState()
 emu.log('CALLBACKBAD|'..word(INDEX)..'|'..s['cpu.a']..'|'..word(sy.SourceAnimationCallback4086_State)..'|'..word(sy.SourceAnimationCallback4086_Fault)..'|'..emu.read(sy.VmState_Status,mt)..'|'..word(sy.VmState_Error)..'|'..word(sy.VmCall_TargetId))
end,emu.callbackType.exec,BAD,BAD,emu.cpuType.snes,mt)
'''
    offs=struct.unpack_from('<6I',metadata,24)
    values=dict(INDEX=INDEX,CODEBANK=base>>16,CALLBACKBASE=locations['callbacks']&65535,CALLBACKBYTES=len(callbacks),
        FRAMEBYTES=len(frames),BIRTHBASE=locations['births']&65535,BIRTHBYTES=len(births),MODELCOUNT=len(registry['models']),
        MODELBASE=locations['models']&65535,MODELBYTES=len(models),DISPATCHBASE=locations['dispatch']&65535,DISPATCHBYTES=len(dispatch),
        PROGRAMCOUNT=owners['program_count'],CALLSITES=offs[2],ARGS=offs[3],STRINGS=offs[4],INSTRUCTIONS=len(code)//8,
        SLOTS=struct.unpack_from('<H',metadata,10)[0],ANIMATIONID=animation['engine_animation_id'],ACTORID=actor,HANDLE=animation['handle'],
        INIT=fs['CallbackFixture_Init'],RUNENTRY=sy['SourceAnimationCallback4086_Run'],RUNRETURN=fs['CallbackFixture_Run']+4,
        RESULT=fs['CallbackFixture_Result'],BAD=fs['CallbackFixture_Bad'],BEFOREOWNER=fs['CallbackFixture_BeforeOwner'])
    install=''
    if a.effects_runner:
        h=struct.unpack_from('<4s6H4I',plan)
        install="\n".join(" set('"+name+"',"+str(value)+")" for name,value in dict(SourceFrameMotion4086_Ready=0xb4e8,SourceFrameMotion4086_Status=0,SourceFrameEffectLeaf4086_Ready=0xb4f4,SourceSelf4086_Ready=0xb4f6,SourceSelf4086_GlobalLow=0,SourceSelf4086_GlobalHigh=0,SourceSelf4086_Active=0,SourceSelf4086_Fault=0,SourceFrameEffectPlan4086_Ready=0xb4f2,SourceFrameEffectPlan4086_State=0,SourceFrameEffectPlan4086_Service=0,SourceFrameEffectPlan4086_Base=0x8000,SourceFrameEffectPlan4086_Bank=59,SourceFrameEffectPlan4086_Bytes=len(plan),SourceFrameEffectPlan4086_Animations=80,SourceFrameEffectPlan4086_PairedCrcLo=h[-2]&65535,SourceFrameEffectPlan4086_PairedCrcHi=h[-2]>>16,SourceFrameEffectPlan4086_BodyCrcLo=h[-1]&65535,SourceFrameEffectPlan4086_BodyCrcHi=h[-1]>>16,SourceClock4086_Ready=0xb4c5,SourceClock4086_Due=1,SourceClock4086_TimeLo=48,SourceClock4086_TimeHi=0,SourceClock4086_Fault=0).items())
        install+='\n for j=0,511 do emu.write(0x43fb00+j,0,mt)end\n'
        lua+=r'''
emu.addMemoryCallback(function()
 emu.log('CALLBACKFRAME|'..word(INDEX)..'|'..word(sy.SourceUpdateFrame4086_State)..'|'..word(sy.SourceFrameEffectPlan4086_State)..'|'..word(sy.SourceSelf4086_Active)..'|'..word(sy.SourceSelf4086_GlobalLow)..'|'..word(sy.SourceSelf4086_GlobalHigh)..'|'..word(sy.SourceClock4086_Due)..'|'..dw(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    lua=lua.replace('INSTALL_EFFECT_RUNNER',install)
    coreinstall=''
    if coretable:
        coreinstall="\n".join(" set('"+name+"',"+str(value)+")" for name,value in dict(SourceModelEntityCopy4086_Ready=0xb4eb,SourceModelEntityCopy4086_Entities=128,SourceModelEntityCopy4086_Models=16,SourceIdle4086_Ready=0xb4f3,SourceRetirement4086_Ready=0xb4f8,SourceRetirement4086_Status=0,SourceBirthCore4086_Ready=0xb4f9,SourceBirthCore4086_Status=0,SourceBirthCore4086_Base=locations['birthcore']&65535,SourceBirthCore4086_Bank=base>>16,SourceBirthCore4086_Bytes=len(coretable),SourceBirthCore4086_Models=16).items())
        coreinstall+='\n for _,r in ipairs({{0x409000,8192,0},{0x40c000,12288,165},{0x43eb00,4096,165},{0x43fd80,32,0}})do for j=0,r[2]-1 do emu.write(r[1]+j,r[3],mt)end end\n put(0x40c048,1,4);put(0x43fd80,1,4);put(0x43fd84,0x414000,4)\n'
        lua+=r'''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local born=c.f==4 and c.fault==0;local bad=0
 for n,r in ipairs({{0x40c060,96},{0x43eb20,32},{0x409040,64}})do
  local base=n==1 and 0 or n==2 and 96 or 128
  for j=0,r[2]-1 do local expected=born and birthcore[base+j+1] or n==3 and 0 or 165;if emu.read(r[1]+j,mt)~=expected then bad=bad+1 end end
 end
 if dw(0x43fd80)~=(born and 2 or 1) or dw(0x43fd84)~=0x414000 or dw(0x40c048)~=1 then bad=bad+1 end
 emu.log('CALLBACKBIRTHCORE|'..word(INDEX)..'|'..bad)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    lua=lua.replace('INSTALL_BIRTH_CORE',coreinstall)
    for k,v in values.items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    for label in ('Vm_SourceCallbackScan','Vm_SourceCallbackPoll__save','Vm_SourceCallbackPoll__ok',
                  'SourceAnimationCallback4086_Prepare','SourceAnimationCallback4086_Prepare__copy',
                  'Vm_SourceFrameGate','SourceAnimationCallback4086_Run__span',
                  'SourceAnimationCallback4086_Close'):
        if label.endswith('__copy'):continue
        lua+=f'''emu.addMemoryCallback(function()
 local state=emu.getState()
 emu.log('CALLBACKSEGMENT|{label}|'..word({INDEX})..'|'..(state.masterClock-owner_start))
end,emu.callbackType.exec,{sy[label]},{sy[label]},emu.cpuType.snes,mt)
'''
    script=folder/'callback_owner.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    reporter=Reporter('M4-ANIMATION-CALLBACK-OWNER',kind='GATE')
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        reporter.check('cold callback owner disabled',startup.u16(m,sy['SourceAnimationCallback4086_Ready'])==0)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('CALLBACK_OWNER_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(REQUEST,0xb4e7)
        for _ in range(24):
            run_frames_exact(m,60)
            if startup.u16(m,INDEX)==len(rows) or startup.u16(m,ERROR):break
        reporter.check('native authored callback batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,ERROR)==0)
    results=[];faults=[];costs=[];initializers=[];frame_results=[];core_results=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        for marker,target in [('CALLBACKOWNER|',results),('CALLBACKBAD|',faults),('CALLBACKCOST|',costs),('CALLBACKINIT|',initializers),('CALLBACKFRAME|',frame_results),('CALLBACKBIRTHCORE|',core_results)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    expected=[]
    for i,c in enumerate(rows):
        born=c['f']==4 and not c['fault']
        expected.append([i,4 if c['fault'] else 3,5 if c['fault'] else 4,0,0,1 if c['fault'] else 0,2 if born else 1,93*65536 if born else 0,
            (80+(18 if c['direction'] else -18))*65536 if born else 0,220*65536 if born else 0,
            None,0,0,breath if born else 0,48 if born else 0])
    reporter.check('source birth position and cleared shared callback boundary',len(results)==len(expected) and
        all(all(e is None or g==e for g,e in zip(got,want)) and len(got)==len(want) for got,want in zip(results,expected)))
    reporter.check('foreground callback entry preserves CPU context',bool(results) and all(r[10]>=1 and r[11]==0 for r in results))
    reporter.check('nonempty initializer copy is exact and metadata stays immutable',len(initializers)==len(rows) and
        all(r[1]==0 for r in initializers) and sum(r[2] for r in initializers)>=4)
    if a.effects_runner:
        expected_frame=[[i,1,0,1,0x4000,0x41,1,48,1] if c['fault'] else [i,2,2,0,0,0,0,49,0] for i,c in enumerate(rows)]
        reporter.check('actual callback birth followed by native captured effect retirement and clock',frame_results==expected_frame)
    if coretable:reporter.check('authored callback publishes exact native birth core and preserves parent role/type',core_results==[[i,0] for i in range(len(rows))])
    r=dict(schema='BYOR_NATIVE_ANIMATION_CALLBACK_OWNER_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(raw).hexdigest(),source_pak_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
        owner_table_sha256=hashlib.sha256(callbacks).hexdigest(),cases=rows,results=results,expected=expected,faults=faults,
        source_frame_handle=animation['handle'],script_programs=owners['program_count'],
        callback_cpu_costs=costs,cost_scope='Before native callback Begin through callback completion/fault and instrumented frame-service acknowledgement; includes intervening NMI/runtime, excludes debugger initialization',
        initializer_copy_checks=initializers,
        remaining_effect_service_instrumented=not a.effects_runner,native_effect_runner=a.effects_runner,sound_service_instrumented=a.effects_runner,frame_results=frame_results,player_initialization_bound=False,source_effect_presentation_proven=False,
        combat_proven=False,motu_gameplay_proven=False,no_pcm_copies=True,no_color_reduction=True)
    r.update(native_birth_core=a.birth_core,birth_core_results=core_results)
    (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
