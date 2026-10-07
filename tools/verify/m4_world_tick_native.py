"""Native owner traversal against pinned C; gameplay services instrumented.

The native CPU owns requests, acknowledgments, compaction and clock commit.
Lua supplies controlled external service outcomes, not gameplay certification.
"""
import argparse
import hashlib
import json
import os
import re
import struct
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_world_tick_authority import cases,expected
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

REQUEST=0x7ffb20
INDEX=0x7ffb22
ERROR=0x7ffb24
FAULT_INDEX=0x7ffb26


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--script-source',type=Path)
    p.add_argument('--script-library',default='DATA/SCRIPTS/SCRIPT.C')
    p.add_argument('--script-expression',default='dasher(1.5,0.25,-0.75);'*9)
    p.add_argument('--expected-velocity',nargs=3,type=float,default=[-1.5,-0.75,0.25],metavar=('X','Z','Y'))
    p.add_argument('--script-toss-count',type=int,default=0)
    p.add_argument('--ai-backend',action='store_true',help='actual AI dispatcher, closed no-action/no-think fixture; requires update-method-source')
    p.add_argument('--update-method-source',type=Path,help='validate and execute metadata-derived uninitialized update methods; requires lost backend')
    p.add_argument('--lost-backend',action='store_true',help='execute actual lost decision and no-event retirement; other death/damage handlers remain unbound')
    p.add_argument('--freeze-backend',action='store_true',help='execute actual source mark/freeze/timer services; other gameplay handlers remain instrumented')
    p.add_argument('--velocity-backend',action='store_true',help='execute actual native service 10; other gameplay handlers remain instrumented')
    a=p.parse_args();
    if a.lost_backend and (not a.freeze_backend or a.script_source):raise ValueError('LOST_FIXTURE_REQUIRES_FREEZE_BACKEND_AND_CLOSED_NO_SCRIPT_SCOPE')
    if a.update_method_source and not a.lost_backend:raise ValueError('UPDATE_METHOD_FIXTURE_REQUIRES_LOST_BACKEND')
    if a.ai_backend and not a.update_method_source:raise ValueError('AI_FIXTURE_REQUIRES_UPDATE_METHOD_SOURCE')
    folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    authority=json.loads((a.authority/'report.json').read_text());rows=cases()
    if authority['status']!='PASS' or [r['case'] for r in authority['results']]!=rows:
        raise ValueError('WORLD_TICK_PINNED_AUTHORITY_REQUIRED')
    if a.update_method_source:rows=[r for r in rows if r['kill_stage']!=5]
    if a.ai_backend:rows=[r for r in rows if r['kill_stage']!=6]
    sy=symbols(Path('src/main.sym'));rom=bytearray(a.rom.read_bytes());entry=sy['Vm_SourceFrameGate'];start=39*32768
    callback=None;callback_blob=None
    if a.script_source:
        from compiler import Source
        from script_ir_4086 import parse_script
        from script_bytecode import compile_library
        from script_native_module import lower,POLICY
        from script_native_api import SIGNATURES
        raw=Source(a.script_source).read(a.script_library)
        callback_blob,detail=lower(compile_library(parse_script(raw.decode('latin1')+'\nvoid main(){'+a.script_expression+'}',
            a.script_library+'#owner-probe'),sorted({name for name,_ in SIGNATURES})),numeric_policy=POLICY)
        callback=dict(source_library=a.script_library,source_sha256=hashlib.sha256(raw).hexdigest(),
            wrapper_expression=a.script_expression,module_sha256=hashlib.sha256(callback_blob).hexdigest(),
            numeric_policy=POLICY)
    if rom[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a') or rom[start:start+32768]!=bytes(32768):
        raise ValueError('WORLD_TICK_NATIVE_GATE_RESERVATION')
    asm='''.snes
.bank 39
.org $8000
WorldTickFixture_Gate:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l REQUEST
    cmp #$B4D6
    beq WorldTickFixture_Start
    jmp WorldTickFixture_Return
WorldTickFixture_Start:
.a16
.i16
    lda #0
    sta.l REQUEST
    sta.l INDEX
    sta.l ERROR
WorldTickFixture_Init:
.a16
.i16
    nop
    jsl BEGIN
    bcs WorldTickFixture_Fault
    ; A direct clock call must not bypass an outstanding world traversal.
    jsl CLOCKCOMMIT
    bcs WorldTickFixture_EarlyCommitRejected
    bra WorldTickFixture_Fault
WorldTickFixture_EarlyCommitRejected:
.a16
.i16
    lda.l CLOCKFAULT
    cmp #1
    bne WorldTickFixture_Fault
    lda #0
    sta.l CLOCKFAULT
WorldTickFixture_Poll:
.a16
.i16
    jsl POLL
    bcs WorldTickFixture_Fault
    cmp #0
    beq WorldTickFixture_Commit
    pha
    jsl POLL
    bcs WorldTickFixture_PendingFault
    cmp.l PHASE
    bne WorldTickFixture_PendingFault
WorldTickFixture_Observe:
.a16
.i16
    nop
    lda #SCRIPTENABLED
    beq WorldTickFixture_Ack
    lda.l PHASE
    cmp #5
    bne WorldTickFixture_Ack
WorldTickFixture_ScriptCall:
.a16
.i16
    jsl SCRIPTCALL
    bcs WorldTickFixture_PendingFault
WorldTickFixture_ScriptReturn:
.a16
.i16
    cmp #3
    beq WorldTickFixture_ScriptCall
    cmp #4
    bne WorldTickFixture_PendingFault
WorldTickFixture_ScriptComplete:
.a16
.i16
    nop
WorldTickFixture_Ack:
.a16
.i16
    pla
    jsl ACK
    bcs WorldTickFixture_Fault
    bra WorldTickFixture_Poll
WorldTickFixture_Commit:
.a16
.i16
    jsl COMMIT
    bcs WorldTickFixture_Fault
WorldTickFixture_Result:
.a16
.i16
    nop
    lda.l INDEX
    inc a
    sta.l INDEX
    cmp #CASES
    bcc WorldTickFixture_Init
    lda #0
    sta.l FAULTINDEX
WorldTickFixture_FaultInit:
.a16
.i16
    nop
    jsl BEGIN
    php
    lda.l FAULTINDEX
    cmp #6
    bcs WorldTickFixture_FaultService
    plp
    bcs WorldTickFixture_FaultObserved
    bra WorldTickFixture_Fault
WorldTickFixture_FaultService:
.a16
.i16
    plp
    bcs WorldTickFixture_Fault
    jsl POLL
    bcs WorldTickFixture_Fault
    lda.l FAULTINDEX
    cmp #8
    beq WorldTickFixture_EarlyOwnerCommit
    cmp #9
    bne WorldTickFixture_AckFault
    lda #3
    sta.l VMSTATUS
WorldTickFixture_AckFault:
.a16
.i16
    lda.l FAULTINDEX
    cmp #7
    bne WorldTickFixture_AckFaultLast
    lda #1
    jsl ACK
    bcs WorldTickFixture_Fault
WorldTickFixture_AckFaultLast:
.a16
.i16
    lda #1
    ldx.l FAULTINDEX
    cpx #6
    bne WorldTickFixture_AckFaultCall
    lda #2
WorldTickFixture_AckFaultCall:
.a16
.i16
    jsl ACK
    bra WorldTickFixture_ExpectFault
WorldTickFixture_EarlyOwnerCommit:
.a16
.i16
    jsl COMMIT
WorldTickFixture_ExpectFault:
.a16
.i16
    bcc WorldTickFixture_Fault
WorldTickFixture_FaultObserved:
.a16
.i16
    nop
    lda.l FAULTINDEX
    inc a
    sta.l FAULTINDEX
    cmp #10
    bcc WorldTickFixture_FaultInit
    bra WorldTickFixture_Done
WorldTickFixture_PendingFault:
.a16
.i16
    pla
WorldTickFixture_Fault:
.a16
.i16
    lda #1
    sta.l ERROR
WorldTickFixture_Done:
.a16
.i16
    lda #0
    sta.l WORLDREADY
    sta.l TICKREADY
    sta.l CLOCKREADY
    sta.l SCRIPTREADY
WorldTickFixture_Return:
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
WorldTickFixture_End:
.a16
.i16
'''
    if a.velocity_backend:
        asm=asm.replace('WorldTickFixture_Ack:\n.a16\n.i16\n    pla', '''WorldTickFixture_Ack:
.a16
.i16
    lda.l PHASE
    cmp #10
    beq WorldTickFixture_VelocityRequest
    cmp #12
    beq WorldTickFixture_ClearRequest
    jmp WorldTickFixture_VelocityDone
WorldTickFixture_ClearRequest:
.a16
.i16
    jsl CLEARVELOCITY
    bcs WorldTickFixture_PendingFault
WorldTickFixture_ClearObserved:
.a16
.i16
    nop
    jmp WorldTickFixture_VelocityDone
WorldTickFixture_VelocityRequest:
.a16
.i16
    lda #10
    jsl ACK
    bcs WorldTickFixture_VelocityEarlyAckRejected
    jmp WorldTickFixture_PendingFault
WorldTickFixture_VelocityEarlyAckRejected:
.a16
.i16
    lda #0
    sta.l OWNERFAULT
    jsl VELOCITY
    bcs WorldTickFixture_PendingFault
WorldTickFixture_VelocityObserved:
.a16
.i16
    nop
WorldTickFixture_VelocityDone:
.a16
.i16
    pla''')
    if a.freeze_backend:
        asm=asm.replace('WorldTickFixture_Ack:\n.a16\n.i16\n', 'WorldTickFixture_Ack:\n.a16\n.i16\n    lda.l PHASE\n    cmp #1\n    beq WorldTickFixture_FreezeRequest\n    cmp #3\n    beq WorldTickFixture_FreezeRequest\n    cmp #4\n    bne WorldTickFixture_FreezeDone\nWorldTickFixture_FreezeRequest:\n.a16\n.i16\n    jsl ACK\n    bcs WorldTickFixture_FreezeEarlyAckRejected\n    jmp WorldTickFixture_PendingFault\nWorldTickFixture_FreezeEarlyAckRejected:\n.a16\n.i16\n    lda #0\n    sta.l FREEZEOWNERFAULT\n    jsl FREEZEBACKEND\n    bcs WorldTickFixture_PendingFault\nWorldTickFixture_FreezeObserved:\n.a16\n.i16\n    nop\nWorldTickFixture_FreezeDone:\n.a16\n.i16\n')
    if a.lost_backend:
        asm=asm.replace('WorldTickFixture_Ack:\n.a16\n.i16\n', 'WorldTickFixture_Ack:\n.a16\n.i16\n    lda.l PHASE\n    cmp #2\n    bne WorldTickFixture_LostDone\n    jsl ACK\n    bcs WorldTickFixture_LostEarlyAckRejected\n    jmp WorldTickFixture_PendingFault\nWorldTickFixture_LostEarlyAckRejected:\n.a16\n.i16\n    lda #0\n    sta.l LOSTOWNERFAULT\n    jsl LOSTBEGIN\n    bcs WorldTickFixture_PendingFault\n    cmp #0\n    beq WorldTickFixture_LostObserved\n    cmp #1\n    bne WorldTickFixture_PendingFault\n    jsl LOSTKILL\n    bcs WorldTickFixture_PendingFault\nWorldTickFixture_LostObserved:\n.a16\n.i16\n    nop\nWorldTickFixture_LostDone:\n.a16\n.i16\n')
    update_descriptor=None;update_table=None;update_callbacks=None
    if a.update_method_source:
        from compiler import Source
        from source_script_clone import derive as derive_clone,pack as pack_clone
        from script_callback_owner import derive as derive_callbacks,pack as pack_callbacks
        source=Source(a.update_method_source);update_descriptor=derive_clone(source);update_table=pack_clone(update_descriptor);cb,*_=derive_callbacks(source);update_callbacks=pack_callbacks(cb)
        rom[59*32768:59*32768+len(update_table)]=update_table;rom[60*32768:60*32768+len(update_callbacks)]=update_callbacks
        asm=asm.replace('WorldTickFixture_Ack:\n.a16\n.i16\n', 'WorldTickFixture_Ack:\n.a16\n.i16\n    lda.l PHASE\n    cmp #5\n    bne WorldTickFixture_UpdateMethodDone\n    jsl ACK\n    bcs WorldTickFixture_UpdateMethodEarlyAckRejected\n    jmp WorldTickFixture_PendingFault\nWorldTickFixture_UpdateMethodEarlyAckRejected:\n.a16\n.i16\n    lda #0\n    sta.l UPDATEMETHODOWNERFAULT\n    jsl UPDATEMETHOD\n    bcs WorldTickFixture_PendingFault\nWorldTickFixture_UpdateMethodObserved:\n.a16\n.i16\n    nop\nWorldTickFixture_UpdateMethodDone:\n.a16\n.i16\n')
    if a.ai_backend:
        asm=asm.replace('WorldTickFixture_Ack:\n.a16\n.i16\n', 'WorldTickFixture_Ack:\n.a16\n.i16\n    lda.l PHASE\n    cmp #6\n    bne WorldTickFixture_AIDone\n    jsl ACK\n    bcs WorldTickFixture_AIEarlyAckRejected\n    jmp WorldTickFixture_PendingFault\nWorldTickFixture_AIEarlyAckRejected:\n.a16\n.i16\n    lda #0\n    sta.l AIOWNERFAULT\n    jsl AIBACKEND\n    bcs WorldTickFixture_PendingFault\n    cmp #0\n    bne WorldTickFixture_PendingFault\nWorldTickFixture_AIObserved:\n.a16\n.i16\n    nop\nWorldTickFixture_AIDone:\n.a16\n.i16\n')
    replacements=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,CASES=len(rows),RESUME=entry+5,
        BEGIN=sy['SourceWorldTick4086_Begin'],POLL=sy['SourceWorldTick4086_Poll'],
        ACK=sy['SourceWorldTick4086_Ack'],COMMIT=sy['SourceWorldTick4086_Commit'],
        PHASE=sy['SourceWorldTick4086_Phase'],WORLDREADY=sy['VmSourceWorld_Ready'],
        TICKREADY=sy['SourceWorldTick4086_Ready'],CLOCKREADY=sy['SourceClock4086_Ready'])
    replacements.update(CLOCKCOMMIT=sy['SourceClock4086_Commit'],CLOCKFAULT=sy['SourceClock4086_Fault'],
                        FAULTINDEX=FAULT_INDEX,VMSTATUS=sy['VmState_Status'],SCRIPTENABLED=int(callback is not None),
                        SCRIPTCALL=sy['SourceVMRun4086_Call'],SCRIPTREADY=sy['SourceVMRun4086_Ready'])
    if a.ai_backend:replacements.update(AIBACKEND=sy['SourceAIRun4086_Begin'],AIOWNERFAULT=sy['SourceWorldTick4086_Fault'])
    if a.update_method_source:
        replacements.update(UPDATEMETHOD=sy['SourceUpdateScript4086_Execute'],UPDATEMETHODOWNERFAULT=sy['SourceWorldTick4086_Fault'])
    if a.velocity_backend:
        replacements['VELOCITY']=sy['SourceVelocity4086_Apply']
        replacements['CLEARVELOCITY']=sy['SourceVelocity4086_Clear']
        replacements['OWNERFAULT']=sy['SourceWorldTick4086_Fault']
    if a.freeze_backend:
        replacements.update(FREEZEBACKEND=sy['SourceFreeze4086_Execute'],FREEZEOWNERFAULT=sy['SourceWorldTick4086_Fault'])
    if a.lost_backend:
        replacements.update(LOSTBEGIN=sy['SourceLost4086_Begin'],LOSTKILL=sy['SourceLost4086_ApplyNoEventKill'],LOSTOWNERFAULT=sy['SourceWorldTick4086_Fault'])
    asm=asm.replace('    ldx.l FAULTINDEX','    lda.l FAULTINDEX\n    tax\n    lda #1')
    for name,value in replacements.items():
        asm=re.sub(r'\b'+name+r'\b',('$%06X'%value) if name!='CASES' else str(value),asm)
    branch_number=[0]
    def relax(match):
        branch_number[0]+=1
        label='WorldTickFixture_Branch_'+str(branch_number[0])
        inverse={'bne':'beq','beq':'bne','bcs':'bcc','bcc':'bcs'}
        return '    '+inverse[match[1]]+' '+label+'\n    jmp '+match[2]+'\n'+label+':\n.a16\n.i16'
    asm=re.sub(r'^    (bne|beq|bcs|bcc) (WorldTickFixture_\w+)$',relax,asm,flags=re.M)
    asm=re.sub(r'^    bra (WorldTickFixture_\w+)$',r'    jmp \1',asm,flags=re.M)
    pasm=folder/'world_tick.pasm';pasm.write_text(asm)
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',
        str(pasm),'--output',str(folder/'world_tick.bin'),'--symbols',str(folder/'world_tick.sym'),'--no-pansy'],capture_output=True,text=True)
    (folder/'poppy.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('WORLD_TICK_NATIVE_ASSEMBLY')
    fs=symbols(folder/'world_tick.sym');end=offset(fs['WorldTickFixture_End'])
    rom[start:end]=(folder/'world_tick.bin').read_bytes()[start:end]
    rom[offset(entry):offset(entry)+5]=bytes.fromhex('5c 00 80 27 ea')
    path=folder/'bor.sfc';path.write_bytes(rom)
    for src in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor*.pcm')]:
        dest=folder/src.name
        if not dest.exists():os.link(src,dest)
    fixture='{' + ','.join('{'+','.join('%s=%s'%(k,('{'+','.join(map(str,v))+'}' if isinstance(v,list) else str(int(v)))) for k,v in c.items())+'}' for c in rows)+'}'
    lua=r'''local mt=emu.memType.snesMemory
local fixtures=FIXTURES;local sy=SYMBOLS;local spawned=false
SCRIPTDEFINITIONS
local function word(a) return emu.read(a,mt)+256*emu.read(a+1,mt) end
local function put(a,v,n) for i=0,n-1 do emu.write(a+i,math.floor(v/256^i)%256,mt) end end
local function dw(a) return word(a)+65536*word(a+2) end
local function bit(mask,s) return math.floor(mask/2^s)%2 end
local function live(c) local n=0;for s=0,c.n-1 do n=n+word(0x414004+80*s) end;return n end
emu.addMemoryCallback(function()
 local c=fixtures[word(INDEX)+1];spawned=false
 put(sy.SourceWorldTick4086_Ready,0xb4d5,2)
 put(sy.SourceWorldTick4086_State,0,2);put(sy.SourceWorldTick4086_Fault,0,2)
 put(sy.SourceWorldTick4086_Pending,0,2);put(sy.SourceWorldTick4086_Maximum,c.maximum,2)
 put(sy.VmSourceWorld_Ready,0xb4a3,2);put(sy.VmSourceWorld_Count,c.n,2)
 put(sy.VmSourceWorld_PoolBase,0x4000,2);put(sy.VmSourceWorld_SideBase,0x6800,2)
 put(sy.VmSourceWorld_Level,c.level,2);put(sy.VmSourceWorld_Time,c.time,4)
 put(sy.SourceClock4086_Ready,0xb4c5,2);put(sy.SourceClock4086_Due,1,2)
 put(sy.SourceClock4086_TimeLo,c.time,4);put(sy.VmState_Status,4,1)
 for s=0,c.n-1 do
  put(0x41f200+2*s,c.order[s+1],2);put(0x414004+80*s,bit(c.alive,s),2)
  put(0x41680c+64*s,bit(c.fresh,s)==1 and c.time or (c.time-1)%4294967296,4)
 end
 SCRIPTINIT
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local index=word(INDEX);local c=fixtures[index+1]
 local service=word(sy.SourceWorldTick4086_Phase);local slot=word(sy.SourceWorldTick4086_Slot)
 emu.log('WORLDTICKEVENT|'..index..'|'..service..'|'..slot..'|'..dw(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Due))
 if service==3 then put(sy.SourceWorldTick4086_Frozen,bit(c.frozen,slot),2) end
 SCRIPTPREPARE
 if service==c.kill_stage and slot==c.kill_slot and (service~=5 or not callback_enabled) then put(0x414004+80*slot,0,2) end
 if service==c.spawn_stage and not spawned then
  spawned=true
  for i=0,c.n-1 do
   local s=word(0x41f200+2*i)
   if word(0x414004+80*s)==0 then
    put(0x414004+80*s,1,2);put(0x41680c+64*s,c.time,4)
    put(sy.SourceWorldTick4086_Maximum,math.max(live(c),word(sy.SourceWorldTick4086_Maximum)),2)
    break
   end
  end
 end
end,emu.callbackType.exec,OBSERVE,OBSERVE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local index=word(INDEX);local c=fixtures[index+1];local mask=0;local order={}
 for s=0,c.n-1 do mask=mask+2^s*word(0x414004+80*s);order[#order+1]=word(0x41f200+2*s) end
 emu.log('WORLDTICKRESULT|'..index..'|'..word(sy.SourceWorldTick4086_Maximum)..'|'..mask..'|'..table.concat(order,',')..'|'..dw(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceWorldTick4086_Fault))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local i=word(FAULTINDEX)
 put(sy.SourceWorldTick4086_Ready,0xb4d5,2);put(sy.SourceWorldTick4086_State,0,2)
 put(sy.SourceWorldTick4086_Fault,0,2);put(sy.SourceWorldTick4086_Pending,0,2)
 put(sy.SourceWorldTick4086_Maximum,2,2);put(sy.VmSourceWorld_Ready,0xb4a3,2)
 put(sy.VmSourceWorld_Count,2,2);put(sy.VmSourceWorld_PoolBase,0x4000,2)
 put(sy.VmSourceWorld_SideBase,0x6800,2);put(sy.VmSourceWorld_Level,1,2)
 put(sy.VmSourceWorld_Time,48,4);put(sy.SourceClock4086_Ready,0xb4c5,2)
 put(sy.SourceClock4086_Due,1,2);put(sy.SourceClock4086_TimeLo,48,4)
 put(sy.SourceClock4086_Fault,0,2);put(sy.VmState_Status,4,1)
 put(0x41f200,0,2);put(0x41f202,1,2)
 for s=0,1 do put(0x414004+80*s,1,2);put(0x41680c+64*s,47,4) end
 if i==0 then put(sy.SourceWorldTick4086_Ready,0,2)
 elseif i==1 then put(sy.VmSourceWorld_Count,0,2)
 elseif i==2 then put(0x41f202,0,2)
 elseif i==3 then put(sy.SourceWorldTick4086_Maximum,1,2)
 elseif i==4 then put(sy.VmSourceWorld_PoolBase,0x4001,2)
 elseif i==5 then put(sy.SourceClock4086_TimeLo,49,4) end
end,emu.callbackType.exec,FAULTINIT,FAULTINIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local i=word(FAULTINDEX)
 emu.log('WORLDTICKFAULT|'..i..'|'..word(sy.SourceWorldTick4086_Fault)..'|'..dw(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Due))
end,emu.callbackType.exec,FAULTOBSERVE,FAULTOBSERVE,emu.cpuType.snes,mt)
'''.replace('FIXTURES',fixture).replace('SYMBOLS','{'+','.join(k+'='+str(v) for k,v in sy.items() if k.startswith(('SourceWorldTick4086_','SourceClock4086_','VmSourceWorld_','VmState_','SourceVelocity4086_','SourceFreeze4086_','SourceLost4086_','SourceSelf4086_','SourceUpdateScript4086_','SourceAI4086_','SourceAIRun4086_')))+'}')
    script_definitions=script_init=script_prepare=''
    if callback:
        count,slots=struct.unpack_from('<2H',callback_blob,8);offsets=struct.unpack_from('<6I',callback_blob,24)
        slot_data=callback_blob[offsets[1]:offsets[1]+slots*8]
        script_definitions='''local callback_enabled=true;local context_faults=0;local script_calls=0;local script_yields=0;local before_call=nil
local function hex(a,h) for i=1,#h,2 do emu.write(a+(i-1)/2,tonumber(h:sub(i,i+1),16),mt) end end
'''
        script_init='\n'.join([
            f'hex({sy["VmCode_Wram"]},"{callback_blob.hex()}")',f'hex({sy["VmSlots_Wram"]},"{slot_data.hex()}")',
            f'put({sy["VmPriv_InstrOff"]},{offsets[0]},2)',f'put({sy["VmCall_CallsitesOff"]},{offsets[2]},2)',
            f'put({sy["VmCall_ArgSlotsOff"]},{offsets[3]},2)',f'put({sy["VmStr_StringsOff"]},{offsets[4]},2)',
            f'put({sy["VmState_InstrCount"]},{count},2)',f'put({sy["VmState_SlotCount"]},{slots},2)',
            f'put({sy["VmSourceEntity_Base"]},0x4000,2)',f'put({sy["VmSourceEntity_Bank"]},0x41,2)',
            f'put({sy["VmSourceEntity_Count"]},c.n,2)',f'put({sy["VmSourceEntity_Ready"]},0xb48b,2)',
            f'put({sy["VmSourceMutation_Ready"]},0xb4a2,2)',f'put({sy["VmSourceVars_Ready"]},0,2)',
            f'put({sy["VmSourceInstr_Ready"]},0,2)',f'put({sy["SourceVMRun4086_Ready"]},0xb4d7,2)',
            f'put({sy["SourceVMRun4086_Busy"]},0,2)',
            f'put({sy["SourceToss4086_Ready"]},0xb4e2,2)',
            '''for s=0,c.n-1 do
 local base=0x414000+80*s;put(base,base,4);put(base+6,0,2)
 for n,tag in ipairs({2,1,1,1,1,2,2,1}) do
  put(base+8*n,tag,2);put(base+8*n+2,0,2);put(base+8*n+4,(n==4 or n==8) and 150 or 0,4)
 end
 for j=72,79 do put(base+j,0,1) end
 put(0x41f300+4*s,0,4)
end'''])
        script_prepare='\n'.join([
            'if service==5 then',
            f' put({sy["VmNativeVariant_ContextValid"]},0xb48f,2)',
            f' put({sy["VmNativeVariant_Self"]},5,4)',f' put({sy["VmNativeVariant_Self"]+4},0x414000+80*slot,4)',
            f' put({sy["VmState_Ip"]},{struct.unpack_from("<H",callback_blob,16)[0]},2)',
            f' put({sy["VmState_FrameTop"]},0,2)',f' put({sy["VmState_Error"]},0,2)',f' put({sy["VmState_Status"]},1,1)',
            'end'])
        lua += r'''
emu.addMemoryCallback(function()
 local s=emu.getState();before_call={}
 for _,k in ipairs({'x','y','d','dbr','sp','ps'}) do before_call[k]=s['cpu.'..k] end
end,emu.callbackType.exec,CALLENTRY,CALLENTRY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();script_calls=script_calls+1
 for _,k in ipairs({'x','y','d','dbr'}) do if before_call[k]~=s['cpu.'..k] then context_faults=context_faults+1 end end
 if before_call.sp+3~=s['cpu.sp'] or (before_call.ps & 0xfe)~=(s['cpu.ps'] & 0xfe) then context_faults=context_faults+1 end
 if word(STATUSADDRESS)==3 then script_yields=script_yields+1 end
end,emu.callbackType.exec,SCRIPTRETURN,SCRIPTRETURN,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local slot=word(sy.SourceWorldTick4086_Slot);local base=0x416800+64*slot
 emu.log('WORLDTICKSCRIPT|'..word(INDEX)..'|'..slot..'|'..dw(base+36)..'|'..dw(base+40)..'|'..dw(base+44)..'|'..context_faults..'|'..script_calls..'|'..script_yields..'|'..dw(0x41400c+80*slot)..'|'..dw(0x41f300+4*slot))
 local c=fixtures[word(INDEX)+1]
 if c.kill_stage==5 and slot==c.kill_slot then put(0x414004+80*slot,0,2) end
end,emu.callbackType.exec,SCRIPTCOMPLETE,SCRIPTCOMPLETE,emu.cpuType.snes,mt)
'''
        for key,value in dict(CALLENTRY=sy['SourceVMRun4086_Call'],SCRIPTRETURN=fs['WorldTickFixture_ScriptReturn'],
            SCRIPTCOMPLETE=fs['WorldTickFixture_ScriptComplete'],STATUSADDRESS=sy['SourceVMRun4086_Status']).items():
            lua=re.sub(r'\b'+key+r'\b',str(value),lua)
    # Scope this independently of retained battery-backed fixture controls.
    velocity_init=f'put({sy["SourceLost4086_Ready"]},{0xb5e0 if a.lost_backend else 0},2)\nput({sy["SourceRetirement4086_Ready"]},{0xb4f8 if a.lost_backend else 0},2)\nput({sy["SourceSelf4086_Ready"]},{0xb4f6 if a.lost_backend else 0},2)\nput({sy["SourceFreeze4086_Ready"]},{0xb5df if a.freeze_backend else 0},2)\nput({sy["SourceStageProducer4086_Ready"]},0,2)\nput({sy["SourceUpdateFrame4086_State"]},0,2)\nput({sy["SourceUpdateFrame4086_Pending"]},0,2)\nput({sy["SourceVelocity4086_Ready"]},{0xb5de if a.velocity_backend else 0},2)\n'
    velocity_init+=f'put({sy["SourceUpdateScript4086_Ready"]},{0xb5e1 if a.update_method_source else 0},2)\n'
    velocity_init+=f'put({sy["SourceAIRun4086_Ready"]},{0xb5e6 if a.ai_backend else 0},2)\n'
    if a.velocity_backend:
        velocity_init+=f'put({sy["SourceUpdateFrame4086_Ready"]},0xb4e3,2)\n'
        velocity_init+='for s=0,c.n-1 do put(0x41f500+s*20,0,4);put(0x41f504+s*20,0,4);put(0x416820+s*64,65536,4);put(0x416824+s*64,(s+1)*65536,4);put(0x416828+s*64,-(s+1)*65536,4) end\n'
        lua+=f'''emu.addMemoryCallback(function()
 local s=word(sy.SourceWorldTick4086_Slot)
 emu.log('WORLDTICKCLEAR|'..word(INDEX)..'|'..s..'|'..dw(0x41f500+s*20)..'|'..dw(0x41f504+s*20)..'|'..word({sy['SourceVelocity4086_Status']}))
end,emu.callbackType.exec,{fs['WorldTickFixture_ClearObserved']},{fs['WorldTickFixture_ClearObserved']},emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=word(sy.SourceWorldTick4086_Slot)
 emu.log('WORLDTICKVELOCITY|'..word(INDEX)..'|'..s..'|'..dw(0x41f500+s*20)..'|'..dw(0x41f504+s*20)..'|'..word({sy['SourceVelocity4086_Status']}))
end,emu.callbackType.exec,{fs['WorldTickFixture_VelocityObserved']},{fs['WorldTickFixture_VelocityObserved']},emu.cpuType.snes,mt)
'''
    if a.freeze_backend:
        velocity_init+=f'put({sy["SourceToss4086_Ready"]},0xb4e2,2)\nput({sy["SourceLifecycle4086_Ready"]},0xb4fb,2)\nput(0x43fd94,0,4)\nput(0x43fd98,0,4)\n'
        velocity_init+='for s=0,c.n-1 do for j=0,39 do put(0x42e000+s*40+j,0,1)end;put(0x42e000+s*40,bit(c.frozen,s),4);put(0x42e004+s*40,(c.time+1)%4294967296,4);put(0x42e024+s*40,0xabcdef01,4);put(0x40c048+s*96,2,4) end\n'
        lua=lua.replace('if service==3 then put(sy.SourceWorldTick4086_Frozen,bit(c.frozen,slot),2) end','')
        lua+=f"emu.addMemoryCallback(function()local s=word(sy.SourceWorldTick4086_Slot);emu.log('WORLDTICKFREEZE|'..word(INDEX)..'|'..word(sy.SourceWorldTick4086_Phase)..'|'..s..'|'..word(sy.SourceWorldTick4086_Frozen)..'|'..dw(0x42e024+s*40)..'|'..word(sy.SourceFreeze4086_Status))end,emu.callbackType.exec,{fs['WorldTickFixture_FreezeObserved']},{fs['WorldTickFixture_FreezeObserved']},emu.cpuType.snes,mt)\n"
    if a.lost_backend:
        settings=dict(SourceLost4086_Status=0,SourceLost4086_OffscreenKill=0,SourceLost4086_DefaultOffscreenKill=3000,SourceLost4086_Direction=2,SourceLost4086_HRes=320,SourceLost4086_VRes=240,SourceRetirement4086_Status=0,SourceSelf4086_Active=0,SourceSelf4086_Fault=0,SourceModelEntityCopy4086_Ready=0xb4eb,SourceIdle4086_Ready=0xb4f3,VmSourceVars_Ready=0xb4a4,VmSourceVars_Base=0x8800,VmSourceVars_Bank=0x41,VmSourceVars_Count=1)
        velocity_init+='\n'.join(f'put({sy[k]},{v},2)'for k,v in settings.items())+'\n'
        velocity_init+=f'put({sy["SourceModelEntityCopy4086_Entities"]},c.n,2)\nput({sy["VmSourceWorld_AdvanceX"]},0,4)\nput({sy["VmSourceWorld_AdvanceY"]},0,4)\nput({sy["SourceSelf4086_GlobalLow"]},0,4)\n'
        velocity_init+='for j=0,31 do put(0x43fd80+j,0,1)end;put(0x43fd80,live(c),4);for j=0,63 do put(0x418800+j,0,1)end\n'
        velocity_init+='for s=0,c.n-1 do put(0x414004+s*80,bit(c.alive,s),4);put(0x40c050+s*96,0,4);put(0x40c054+s*96,0,4);for j=0,63 do put(0x409000+s*64+j,0,1)end;for j=0,31 do put(0x43eb00+s*32+j,0,1)end;put(0x414000+s*80,0x414000+s*80,4);put(0x414008+s*80,2,4);put(0x41400c+s*80,0,4);put(0x414030+s*80,2,4);put(0x414034+s*80,80*65536,4);put(0x414038+s*80,2,4);put(0x41403c+s*80,220*65536,4);put(0x416810+s*64,(c.kill_stage==2 and c.kill_slot==s) and 0xffffffff or 300,4);put(0x439004+s*80,0,4)end\n'
        old='if service==c.kill_stage and slot==c.kill_slot and (service~=5 or not callback_enabled) then put(0x414004+80*slot,0,2) end'
        lua=lua.replace(old,'if service==c.kill_stage and slot==c.kill_slot and service~=2 and (service~=5 or not callback_enabled) then put(0x414004+80*slot,0,2);put(0x43fd80,live(c),4) end')
        lua=lua.replace('put(0x414004+80*s,1,2);put(0x41680c+64*s,c.time,4)','put(0x414004+80*s,1,2);put(0x41680c+64*s,c.time,4);put(0x43fd80,live(c),4)')
        lua+=f"emu.addMemoryCallback(function()local s=word(sy.SourceWorldTick4086_Slot);emu.log('WORLDTICKLOST|'..word(INDEX)..'|'..s..'|'..word(sy.SourceLost4086_Request)..'|'..word(sy.SourceLost4086_Status)..'|'..dw(0x414004+s*80)..'|'..dw(0x43fd80)..'|'..dw(sy.SourceSelf4086_GlobalLow))end,emu.callbackType.exec,{fs['WorldTickFixture_LostObserved']},{fs['WorldTickFixture_LostObserved']},emu.cpuType.snes,mt)\n"
    if a.update_method_source:
        settings=dict(SourceUpdateScript4086_Status=0,VmSourceWorld_TemplateCount=16,SourceScriptClone4086_Ready=0xb5c1,SourceScriptClone4086_Status=0,SourceScriptClone4086_Base=0x8000,SourceScriptClone4086_Bank=59,SourceScriptClone4086_Bytes=len(update_table),SourceScriptClone4086_Models=16,SourceAnimationCallback4086_Ready=0xb4e6,SourceAnimationCallback4086_Base=0x8000,SourceAnimationCallback4086_Bank=60,SourceAnimationCallback4086_Models=16,SourceAnimationCallback4086_Programs=cb['program_count'])
        velocity_init+='\n'.join(f'put({sy[k]},{v},2)'for k,v in settings.items())+'\n'
        masks='{'+','.join(str(m['initialized_mask'])for m in update_descriptor['models'])+'}'
        velocity_init+='local masks='+masks+';for s=0,c.n-1 do put(0x416800+s*64,s%16,2);put(0x40902c+s*64,masks[s%16+1],4)end\n'
        lua+=f"emu.addMemoryCallback(function()local s=word(sy.SourceWorldTick4086_Slot);emu.log('WORLDTICKUPDATEABSENT|'..word(INDEX)..'|'..s..'|'..word(sy.SourceUpdateScript4086_Status))end,emu.callbackType.exec,{fs['WorldTickFixture_UpdateMethodObserved']},{fs['WorldTickFixture_UpdateMethodObserved']},emu.cpuType.snes,mt)\n"
    if a.ai_backend:
        settings=dict(SourceAI4086_Ready=0xb5e2,SourceAI4086_State=0,SourceAI4086_Endgame=0,SourceAI4086_SpawnID=23,SourceAI4086_RespawnID=104,SourceModelAnimationCopy4086_Ready=0xb4e9,SourceModelAnimationCopy4086_Models=16,SourceModelAnimationCopy4086_Maximum=128,SourceModelAnimationCopy4086_Bytes=4096)
        velocity_init+='\n'.join(f'put({sy[k]},{v},2)'for k,v in settings.items())+'\n'
        velocity_init+='for j=0,4095 do put(0x43c000+j,0,1)end;for s=0,c.n-1 do put(0x416804+s*64,1,2);put(0x439000+s*80,0,4);put(0x43900c+s*80,0,4);put(0x43eb10+s*32,0,4);put(0x416814+s*64,c.time,4);put(0x41f510+s*20,1,2)end\n'
        lua+=f"emu.addMemoryCallback(function()local s=word(sy.SourceWorldTick4086_Slot);emu.log('WORLDTICKAI|'..word(INDEX)..'|'..s..'|'..word(sy.SourceAIRun4086_State)..'|'..word(sy.SourceAI4086_State)..'|'..dw(0x42e024+s*40))end,emu.callbackType.exec,{fs['WorldTickFixture_AIObserved']},{fs['WorldTickFixture_AIObserved']},emu.cpuType.snes,mt)\n"
    lua=lua.replace('SCRIPTDEFINITIONS',script_definitions).replace('SCRIPTINIT',velocity_init+script_init).replace('SCRIPTPREPARE',script_prepare)
    for key,value in dict(INDEX=INDEX,INIT=fs['WorldTickFixture_Init'],OBSERVE=fs['WorldTickFixture_Observe'],RESULT=fs['WorldTickFixture_Result'],
        FAULTINDEX=FAULT_INDEX,FAULTINIT=fs['WorldTickFixture_FaultInit'],FAULTOBSERVE=fs['WorldTickFixture_FaultObserved']).items():
        lua=re.sub(r'\b'+key+r'\b',str(value),lua)
    lua+=f"emu.addMemoryCallback(function()emu.log('WORLDTICKOWNERFAULT|'..word(INDEX)..'|'..word(sy.SourceWorldTick4086_Phase)..'|'..word(sy.SourceWorldTick4086_Fault)..'|'..word(sy.SourceClock4086_Fault))end,emu.callbackType.exec,{fs['WorldTickFixture_Fault']},{fs['WorldTickFixture_Fault']},emu.cpuType.snes,mt)\n"
    lua+=f"emu.addMemoryCallback(function()put({sy['SourceAIRun4086_Ready']},0,2);put({sy['SourceUpdateScript4086_Ready']},0,2);put({sy['SourceFreeze4086_Ready']},0,2);put({sy['SourceLost4086_Ready']},0,2);put({sy['SourceSelf4086_Ready']},0,2)end,emu.callbackType.exec,{fs['WorldTickFixture_FaultInit']},{fs['WorldTickFixture_FaultInit']},emu.cpuType.snes,mt)\n"
    script=folder/'world_tick.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    reporter=Reporter('M4-WORLD-TICK-OWNER',kind='GATE')
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        m.write_u16(REQUEST,0)
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        reporter.check('cold world owner disabled',startup.u16(m,sy['SourceWorldTick4086_Ready'])==0)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('WORLD_TICK_NATIVE_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(REQUEST,0xb4d6)
        for _ in range(128 if callback else 12):
            run_frames_exact(m,60)
            if (startup.u16(m,INDEX)==len(rows) and startup.u16(m,FAULT_INDEX)==10) or startup.u16(m,ERROR):break
        reporter.check('native traversal batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,FAULT_INDEX)==10 and startup.u16(m,ERROR)==0)
    actual=[dict(events=[]) for _ in rows];clock_checks=[];faults=[];script_results=[];velocity_results=[];clear_results=[];freeze_results=[];lost_results=[];update_method_results=[];ai_results=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        if 'WORLDTICKAI|'in line:ai_results.append(list(map(int,line.split('WORLDTICKAI|',1)[1].split('|'))))
        if 'WORLDTICKUPDATEABSENT|'in line:update_method_results.append(list(map(int,line.split('WORLDTICKUPDATEABSENT|',1)[1].split('|'))))
        if 'WORLDTICKLOST|' in line:
            lost_results.append(list(map(int,line.split('WORLDTICKLOST|',1)[1].split('|'))))
        if 'WORLDTICKFREEZE|' in line:
            freeze_results.append(list(map(int,line.split('WORLDTICKFREEZE|',1)[1].split('|'))))
        if 'WORLDTICKCLEAR|' in line:
            clear_results.append(list(map(int,line.split('WORLDTICKCLEAR|',1)[1].split('|'))))
        if 'WORLDTICKVELOCITY|' in line:
            velocity_results.append(list(map(int,line.split('WORLDTICKVELOCITY|',1)[1].split('|'))))
        if 'WORLDTICKSCRIPT|' in line:
            script_results.append(list(map(int,line.split('WORLDTICKSCRIPT|',1)[1].split('|'))))
        if 'WORLDTICKFAULT|' in line:
            faults.append(list(map(int,line.split('WORLDTICKFAULT|',1)[1].split('|'))))
        if 'WORLDTICKEVENT|' in line:
            i,stage,slot,time,due=map(int,line.split('WORLDTICKEVENT|',1)[1].split('|'))
            actual[i]['events'].append([stage,slot]);clock_checks.append(time==rows[i]['time'] and due==1)
        if 'WORLDTICKRESULT|' in line:
            words=line.split('WORLDTICKRESULT|',1)[1].split('|');i=int(words[0])
            actual[i].update(maximum=int(words[1]),alive=int(float(words[2])),order=list(map(int,words[3].split(','))))
            clock_checks.append(int(words[4])==(rows[i]['time']+1)&0xffffffff and int(words[5])==0 and int(words[6])==0)
    comparisons=[]
    for c,got in zip(rows,actual):
        wanted=expected(c);wanted.pop('completed')
        comparisons.append(dict(case=c,expected=wanted,actual=got,passed=got==wanted))
    reporter.check('all native requests and compaction match pinned C',all(r['passed'] for r in comparisons))
    reporter.check('time commits only after the completed traversal',bool(clock_checks) and all(clock_checks))
    reporter.check('invalid ownership and incomplete services reject without clock mutation',
                   faults==[[i,1,49 if i==5 else 48,1] for i in range(10)])
    if a.ai_backend:
        reporter.check('actual no-callback AI dispatch completes and marks source update before owner acknowledgement',ai_results==[[i,slot,2,5,2]for i,r in enumerate(actual)for phase,slot in r['events']if phase==6] and bool(ai_results))
    if a.update_method_source:
        reporter.check('metadata-derived uninitialized update methods complete before acknowledgement',update_method_results==[[i,slot,2]for i,r in enumerate(actual)for phase,slot in r['events']if phase==5] and bool(update_method_results))
    if a.lost_backend:
        wanted_lost=[[i,s]for i,r in enumerate(actual)for phase,s in r['events']if phase==2]
        reporter.check('actual lost decisions/no-event retirement complete before acknowledgement with source global self retained',len(lost_results)==len(wanted_lost) and all(v[:2]==e and v[2:5]==[int(rows[v[0]]['kill_stage']==2 and rows[v[0]]['kill_slot']==v[1]),2,int(not(rows[v[0]]['kill_stage']==2 and rows[v[0]]['kill_slot']==v[1]))] and v[6]==0x414000+v[1]*80 for v,e in zip(lost_results,wanted_lost)))
    if a.freeze_backend:
        wanted_freeze=[[i,phase,s] for i,r in enumerate(actual) for phase,s in r['events'] if phase in (1,3,4)]
        reporter.check('actual mark/freeze/expand services reject early acknowledgement and preserve source decisions',len(freeze_results)==len(wanted_freeze) and all(v[:3]==e and v[4:]==[0,2] and (v[1]!=3 or v[3]==((rows[v[0]]['frozen']>>v[2])&1)) for v,e in zip(freeze_results,wanted_freeze)))
    if a.velocity_backend:
        reporter.check('actual arrange_ents tail clears each admitted movement accumulator',clear_results==[[i,s,0,0,2] for i,r in enumerate(actual) for phase,s in r['events'] if phase==12] and bool(clear_results))
        expected_velocity=[[i,s,((s+1)*32768)&0xffffffff,(-(s+1)*32768)&0xffffffff,2] for i,r in enumerate(actual) for phase,s in r['events'] if phase==10]
        reporter.check('actual service 10 rejects early acknowledgement and publishes exactly once before the owner acknowledgement',velocity_results==expected_velocity and bool(velocity_results))
    if callback:
        invocations=sum(sum(e[0]==5 for e in r['events']) for r in actual)
        velocity=[int(v*65536)&0xffffffff for v in a.expected_velocity]
        reporter.check('source-authored function executes inside native owner services',
            len(script_results)==invocations and all(r[2:5]==velocity for r in script_results))
        reporter.check('VM portal preserves owner context across cooperative yields',
            bool(script_results) and all(r[5]==0 for r in script_results) and script_results[-1][7]>0)
        reporter.check('toss altitude and tick timestamp are source-derived',
            all(r[8]==a.script_toss_count*32768 and r[9]==(((rows[r[0]]['time']+1)&0xffffffff) if a.script_toss_count else 0) for r in script_results))
    report=dict(schema='BYOR_4086_WORLD_TICK_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(rom).hexdigest(),authority_functions_sha256=authority['functions_sha256'],
        cases=len(rows),events=sum(len(r['events']) for r in actual),comparisons=comparisons,
        rejections=faults,early_direct_clock_commit_rejections=len(rows),
        ai_backend=a.ai_backend,ai_results=ai_results,update_method_descriptor=update_descriptor,update_method_results=update_method_results,callback=callback,script_results=script_results,velocity_backend=a.velocity_backend,velocity_results=velocity_results,clear_results=clear_results,freeze_backend=a.freeze_backend,freeze_results=freeze_results,lost_backend=a.lost_backend,lost_results=lost_results,
        bank0_growth=0,live_gameplay_handlers_bound=False,motu_gameplay_proven=False)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
