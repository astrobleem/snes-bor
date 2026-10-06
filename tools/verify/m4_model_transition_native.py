"""Ordered native model transition; external model/script/frame services observed."""
import argparse,hashlib,json,os,re,struct,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_model_switch_4086 import CACHED_FIELDS,ENTITY_CORE_FIELDS
from source_animation_init_4086 import pack as pack_init
from source_frame_effects_4086 import pack as pack_effects,ANIMATION_FIELDS
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_animation_init_native import luav
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

REQUEST,INDEX,ERROR=0x7ffd80,0x7ffd82,0x7ffd84
FLOATS={'speed','runspeed','runjumpheight','runjumpdist'}


def inputs(c):
    old=dict(zip(CACHED_FIELDS,range(10,49)));new=dict(zip(CACHED_FIELDS,range(110,149)))
    for i,f in enumerate(CACHED_FIELDS):
        if not c['variant'] or i%3:new[f]=0 if f in ('speed','runspeed','health','mp') else -1
    b=c['boundary']
    if b==3:new.update(health=-1,mp=-1)
    elif b==4:new.update(health=2147483647,mp=2147483647)
    elif b==5:new.update(health=-2147483648,mp=-2147483648)
    elif b==6:
        for f in ('aimove','aiattack','risetime.rise'):new[f]=-2
    elif b==7:new.update(speed=-0.,runspeed=-0.)
    elif b==8:new.update(speed=1.1754943508222875e-38,runspeed=1.1754943508222875e-38)
    cache=b''.join(struct.pack('<f' if f in FLOATS else '<i',d[f]) for d in (old,new) for f in CACHED_FIELDS)
    cache=cache[:156]+struct.pack('<i',c['oldtype'])+cache[156:]+struct.pack('<i',c['newtype'])
    hp=-2147483648 if b==1 else 2147483647 if b==2 else 500
    core=struct.pack('<20i',*[old[f]+60 for f in ENTITY_CORE_FIELDS],c['oldtype'],hp)+struct.pack('<4i',123,77,1,0x25252525)
    return list(cache),list(core),hp


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--authority',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--weapon-metadata',action='store_true');p.add_argument('--nested-frame-zero',action='store_true')
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text())
    if authority['status']!='PASS' or authority['functions_sha256']!='b986f6344bb027ff9bbc61f30375b49503941b5088906fd09aa7dc564b3d0c35':raise ValueError('MODEL_TRANSITION_AUTHORITY')
    rows=[]
    for ar in authority['results']:
        c=ar['case']
        if c['number']!=1:continue
        cache,core,hp=inputs(c);s=ar['actual']['state'];wanted_cache=bytearray()
        for f,v in zip(CACHED_FIELDS,s[17:56]):wanted_cache.extend(struct.pack('<f' if f in FLOATS else '<i',float(v) if f in FLOATS else int(v)))
        wanted_cache.extend(struct.pack('<i',c['newtype']))
        wanted_core=struct.pack('<20i',*[int(v) for v in s[82:100]],c['oldtype'],int(s[3]))+struct.pack('<4i',123,77,int(s[8]),0x25252525)
        rows.append(dict(c,slot=(0,1,127)[len(rows)%3],cache=cache,core=core,hp=hp,wanted=s,wanted_cache=list(wanted_cache),wanted_core=list(wanted_core),trace=ar['actual']['trace']))
    base=next(r for r in rows if r['flags']==1 and r['anim_flag']==1 and r['variant']==0)
    rows.extend(dict(base,bad_ack=n) for n in range(1,8))
    rows.extend(dict(base,same_model=1,slot=slot) for slot in (0,1,127))
    if a.nested_frame_zero:
        rows.extend(dict(base,nested_bad=n) for n in ('issued','busy','depth','request','child_slot','ticket_ready','ticket_state','ticket_issued','ticket_slot','child_pending'))
        rows.extend(dict(base,nested_depth=n) for n in range(1,8))
    animations=[dict(handle=i+1,numframes=n,sync=-1,engine_animation_id=i) for i,n in enumerate((4,2,0,1))]
    ai=pack_init(dict(maximum_animations=168,animations=animations));fe=pack_effects(dict(models=[],animations=[dict(handle=an['handle'],events=dict.fromkeys(ANIMATION_FIELDS,0),frames=[dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=d) for d in delays]) for an,delays in zip(animations,([6,8,10,12],[14,16],[],[18]))]))
    sy=symbols(Path('src/main.sym'));entry=sy['Vm_SourceFrameGate'];first=39*32768;raw=bytearray(a.rom.read_bytes())
    if raw[first:first+32768]!=bytes(32768) or raw[59*32768:61*32768]!=bytes(65536) or raw[0x7fd8]!=8:raise ValueError('MODEL_TRANSITION_PRIVATE_RESERVATION')
    asm='''.snes
.bank 39
.org $8000
TransitionFixture_Gate:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l REQUEST
 cmp #$B4F0
 beq TransitionFixture_Init
 jmp TransitionFixture_Return
TransitionFixture_Init:
.a16
.i16
 nop
 jsl BEGIN
TransitionFixture_After:
.a16
.i16
 nop
 bcc TransitionFixture_AfterGood
 lda.l EXPECTFAULT
 bne TransitionFixture_Result
 jmp TransitionFixture_Bad
TransitionFixture_AfterGood:
.a16
.i16
 lda.l STATE
 cmp #2
 beq TransitionFixture_Result
TransitionFixture_Service:
.a16
.i16
 nop
 NESTEDCALL
 jsl CLOCK
TransitionFixture_PendingClock:
.a16
.i16
 nop
 jsl ACK
 bra TransitionFixture_After
TransitionFixture_Result:
.a16
.i16
 nop
 PARENTACK
 jsl CLOCK
TransitionFixture_Clock:
.a16
.i16
 nop
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #CASES
 bcs TransitionFixture_Done
 and #3
 bne TransitionFixture_Init
 bra TransitionFixture_Return
TransitionFixture_Bad:
.a16
.i16
 lda #1
 sta.l ERROR
TransitionFixture_Done:
.a16
.i16
 lda #0
 sta.l REQUEST
 sta.l READY
 sta.l WORLDREADY
TransitionFixture_Return:
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
    nested=''' lda.l NESTED
 beq TransitionFixture_NestedDone
 jsl NESTEDSTART
TransitionFixture_AfterNestedStart:
.a16
.i16
 nop
 bcc TransitionFixture_ChildScript
 lda.l EXPECTFAULT
 bne TransitionFixture_NestedRejectedStart
 jmp TransitionFixture_Bad
TransitionFixture_NestedRejectedStart:
.a16
.i16
 jmp TransitionFixture_Result
TransitionFixture_ChildScript:
.a16
.i16
 lda #1
 jsl FRAMEACK
 bcc TransitionFixture_ChildEffects
 jmp TransitionFixture_Bad
TransitionFixture_ChildEffects:
.a16
.i16
 nop
 lda #2
 jsl FRAMEACK
 bcc TransitionFixture_ChildFinish
 jmp TransitionFixture_Bad
TransitionFixture_ChildFinish:
.a16
.i16
 jsl NESTEDFINISH
TransitionFixture_AfterNestedFinish:
.a16
.i16
 nop
 bcc TransitionFixture_NestedDone
 lda.l EXPECTFAULT
 bne TransitionFixture_NestedRejectedFinish
 jmp TransitionFixture_Bad
TransitionFixture_NestedRejectedFinish:
.a16
.i16
 jmp TransitionFixture_Result
TransitionFixture_NestedDone:
.a16
.i16
 nop'''
    asm=asm.replace(' NESTEDCALL',nested if a.nested_frame_zero else '').replace(' PARENTACK',' lda #2\n jsl FRAMEACK' if a.nested_frame_zero else '')
    # Extra child calls increase the private fixture's backward branch span.
    asm=asm.replace(' bra TransitionFixture_After',' jmp TransitionFixture_After').replace(' bne TransitionFixture_Init',' beq TransitionFixture_Yield\n jmp TransitionFixture_Init\nTransitionFixture_Yield:\n.a16\n.i16')
    values=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,EXPECTFAULT=REQUEST+6,NESTED=REQUEST+8,NESTEDSTART=sy['SourceAnimationInit4086_StartNestedFrame'],NESTEDFINISH=sy['SourceAnimationInit4086_FinishNestedFrame'],FRAMEACK=sy['SourceUpdateFrame4086_Ack'],STATE=sy['SourceModelTransition4086_State'],READY=sy['SourceModelTransition4086_Ready'],WORLDREADY=sy['VmSourceWorld_Ready'],BEGIN=sy['SourceModelTransition4086_Begin'],ACK=sy['SourceModelTransition4086_Ack'],CLOCK=sy['SourceClock4086_Commit'],CASES=len(rows),RESUME=entry+5)
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm)
    pasm=folder/'fixture.pasm';pasm.write_text(asm)
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(pasm),'--output',str(folder/'fixture.bin'),'--symbols',str(folder/'fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('MODEL_TRANSITION_FIXTURE_ASSEMBLY')
    fs=symbols(folder/'fixture.sym');code=(folder/'fixture.bin').read_bytes()[first:];raw[first:first+len(code)]=code;raw[59*32768:59*32768+len(ai)]=ai;raw[60*32768:60*32768+len(fe)]=fe
    if raw[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a'):raise ValueError('MODEL_TRANSITION_GATE')
    raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['TransitionFixture_Gate'])[:3]+b'\xea'
    rom=folder/'bor.sfc';rom.write_bytes(raw)
    for media in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor-*.pcm')]:
        target=folder/media.name
        if not target.exists():os.link(media.resolve(),target)
    lua='local nested_frame_zero='+str(a.nested_frame_zero).lower()+'\nlocal weapon_metadata='+str(a.weapon_metadata).lower()+'\nlocal rows='+luav(rows)+'\nlocal sy='+luav({k:v for k,v in sy.items() if k.startswith(('SourceModel','SourceWeapon4086_','SourceAnimationInit4086_','SourceAnimationCallback4086_','SourceFrameMotion4086_','SourceFrameEffectPlan4086_','SourceVMRun4086_','VmSourceCallback_','VmState_','SourceUpdateFrame4086_','SourceClock4086_','SourceWorldTick4086_','SourceFrameStack4086_','VmSourceWorld_'))})+'\n'
    lua+=r'''
local mt=emu.memType.snesMemory;local before={};local failure_before={};local trace={};local ctx=0;local cpu={};local start=0;local services={};local faults=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function long(a,v)put(a,v&65535);put(a+2,(v>>16)&65535)end
local function set(prefix,k,v)put(sy[prefix..'4086_'..k],v)end
local function bytes(a,b)for i,v in ipairs(b)do emu.write(a+i-1,v,mt)end end
local ranges={{0x414000,10240},{0x416800,8192},{0x40b000,3072},{0x40c000,12288},{0x41f500,2560},{0x43c000,8192},{0x43e000,512}}
if weapon_metadata then ranges[#ranges+1]={0x43e200,2048}end
emu.addMemoryCallback(function()
 if word(sy.SourceClock4086_Due)~=1 or word(sy.SourceClock4086_TimeLo)~=48 or word(sy.SourceClock4086_Fault)~=1 then faults=faults+1 end
 set('SourceClock','Fault',0)
end,emu.callbackType.exec,PENDINGCLOCK,PENDINGCLOCK,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];trace={};services={};ctx=0;faults=0
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0xa5,mt)end end
 bytes(0x40b000,c.cache);bytes(0x40c000+96*c.slot,c.core)
 local v=0x414000+80*c.slot;local s=0x416800+64*c.slot;local aux=0x41f500+20*c.slot
 long(v,v);put(v+4,1);put(v+6,0)
 for _,at in ipairs({16,32,64})do put(v+at,1);put(v+at+2,0)end
 long(v+20,0);long(v+36,c.hp);long(v+68,777)
 put(s,0);put(s+2,0);put(s+4,1);put(s+6,3);long(s+8,123);long(aux+8,0);put(aux+16,1)
 for i=0,335 do put(0x43c000+2*i,0)end
 put(0x43c000,1);put(0x43c002,2);put(0x43c004,3)
 put(0x43c000+336+2,2);put(0x43c000+336+6,4)
 for i=0,3 do long(0x43e000+4*i,17+i)end
 bytes(0x40ba00,{0,0,2,0,0,0,0,0,3,0,0,0,255,255,255,255,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0})
 bytes(0x40ba20,{255,255,0,0,c.flags,0,0,0,3,0,0,0,255,255,255,255,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0})
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_Count,128)
 set('SourceModelEntityCopy','Ready',0xb4eb);set('SourceModelEntityCopy','Models',2);set('SourceModelEntityCopy','Entities',128)
 set('SourceModelCachedCopy','Ready',0xb4ee);set('SourceModelCachedCopy','Models',2)
 set('SourceModelAnimationCopy','Ready',0xb4e9);set('SourceModelAnimationCopy','Models',2);set('SourceModelAnimationCopy','Maximum',168);set('SourceModelAnimationCopy','Bytes',672)
 set('SourceModelAnimation','Ready',0xb4ef);set('SourceModelAnimation','State',0);set('SourceModelAnimation','Sync',c.anim_flag==0 and 1 or 0)
 set('SourceModelAnimation','TimeLo',c.time);set('SourceModelAnimation','TimeHi',0);set('SourceModelAnimation','Select',c.select)
 set('SourceModelAnimation','Idle',1);set('SourceModelAnimation','Spawn',3);set('SourceModelAnimation','Respawn',2);set('SourceModelAnimation','SelectAnimation',3);set('SourceModelAnimation','DelayPolicy',1)
 set('SourceAnimationInit','Ready',0xb4ec);set('SourceAnimationInit','State',0);set('SourceAnimationInit','Base',0x8000);set('SourceAnimationInit','Bank',59);set('SourceAnimationInit','Bytes',AIBYTES);set('SourceAnimationInit','Issued',0)
 set('SourceUpdateFrame','Ready',0xb4e3);set('SourceUpdateFrame','State',0);set('SourceUpdateFrame','Pending',0);set('SourceUpdateFrame','Base',0x8000);set('SourceUpdateFrame','Bank',60);set('SourceUpdateFrame','Bytes',FEBYTES);set('SourceUpdateFrame','Animations',4)
 set('SourceFrameStack','Ready',0);set('SourceWorldTick','Ready',0);set('SourceFrameEffectPlan','Ready',0)
 if nested_frame_zero then
  set('SourceFrameStack','Ready',0xb4ed);set('SourceFrameStack','Depth',c.nested_depth or 0);set('SourceFrameStack','Fault',0)
  set('SourceUpdateFrame','State',1);set('SourceUpdateFrame','Pending',2);set('SourceUpdateFrame','Slot',c.slot);set('SourceUpdateFrame','Request',3)
  set('SourceFrameMotion','Ready',0);set('SourceAnimationCallback','Ready',0);set('SourceVMRun','Busy',0)
  put(sy.VmSourceCallback_Active,0);put(sy.VmState_Status,4);long(sy.VmSourceWorld_Time,c.time)
  put(sy.VmSourceWorld_SideBase,0x6800)
 end
 set('SourceModelTransition','Ready',0xb4f0);set('SourceModelTransition','State',0);set('SourceModelTransition','Service',0);set('SourceModelTransition','Slot',c.slot);set('SourceModelTransition','New',1)
 set('SourceWeapon','Ready',weapon_metadata and 0xb4f1 or 0);set('SourceWeapon','Models',2);set('SourceWeapon','Entities',128)
 put(EXPECTFAULT,(c.bad_ack or c.nested_bad) and 1 or 0)
 if c.same_model==1 then set('SourceModelTransition','New',0);set('SourceModelCachedCopy','Ready',0);set('SourceModelAnimationCopy','Ready',0);set('SourceModelAnimation','Ready',0)end
 set('SourceClock','Ready',0xb4c5);set('SourceClock','Due',1);set('SourceClock','TimeLo',48);set('SourceClock','TimeHi',0);set('SourceClock','Fault',0)
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
local function capture()
 local s=emu.getState();start=s.masterClock;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
 local c=rows[word(INDEX)+1]
 if c.bad_ack and word(sy.SourceModelTransition4086_Service)==c.bad_ack then
  before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 end
 if c.nested_bad then failure_before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do failure_before[r[1]+i]=emu.read(r[1]+i,mt)end end end
end
emu.addMemoryCallback(capture,emu.callbackType.exec,BEGIN,BEGIN,emu.cpuType.snes,mt)
emu.addMemoryCallback(capture,emu.callbackType.exec,ACK,ACK,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp'] or (cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('MODELOWNERCOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local service=word(sy.SourceModelTransition4086_Service);services[#services+1]=service
 put(NESTED,nested_frame_zero and service==4 and c.bad_ack~=4 and 1 or 0)
 local v=0x414000+80*c.slot;local s=0x416800+64*c.slot;local e=0x40c000+96*c.slot
 if service==1 then
  if word(s)~=0 or word(e+72)~=c.oldtype then faults=faults+1 end
 elseif service==2 or service==3 then
  if word(s)~=1 or word(e+72)~=c.newtype then faults=faults+1 end
 elseif service==4 then
  if word(e+72)~=c.newtype then faults=faults+1 end
  local n=word(v+20);trace[#trace+1]=10+n
  if not nested_frame_zero or c.bad_ack==4 then put(s+6,0);long(s+8,c.wanted[8]);set('SourceAnimationInit','State',2)end
 elseif service==5 then
  if word(e+72)~=c.oldtype then faults=faults+1 end
  if(c.flags&4)~=0 then trace[#trace+1]=20 end
  trace[#trace+1]=21;trace[#trace+1]=22
 elseif service==7 and c.variant~=0 then trace[#trace+1]=24 end
 if service==4 then
  if c.nested_bad=='issued'then set('SourceAnimationInit','Issued',1)
  elseif c.nested_bad=='busy'then set('SourceVMRun','Busy',1)
  elseif c.nested_bad=='depth'then set('SourceFrameStack','Depth',8)end
 end
 set('SourceModelTransition','Acknowledged',c.bad_ack==service and 0 or service)
end,emu.callbackType.exec,SERVICE,SERVICE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local w=c.wanted;local v=0x414000+80*c.slot;local s=0x416800+64*c.slot;local aux=0x41f500+20*c.slot
 local function expect(a,v)before[a]=v&255;before[a+1]=(v>>8)&255 end
 local function expectlong(a,v)expect(a,v&65535);expect(a+2,(v>>16)&65535)end
 local function expectbytes(a,b)for i,v in ipairs(b)do before[a+i-1]=v end end
 if c.nested_bad then before=failure_before end
 if not c.bad_ack and not c.nested_bad and c.same_model~=1 then
 expectbytes(0x40b0a0,c.wanted_cache);expectbytes(0x40c000+96*c.slot,c.wanted_core)
 expectlong(v+36,w[3]);expectlong(v+68,w[98]);expectlong(v+20,w[5]);expect(s,1);expect(s+4,w[6]);expect(s+6,w[7]);expectlong(s+8,w[8])
 if c.anim_flag~=0 or (c.flags&1)~=0 then
  expectlong(0x40c000+96*c.slot+84,123);expectlong(aux+8,0);expect(aux+16,1);expectlong(0x43e000+4*(w[6]-1),0)
  if nested_frame_zero then expectlong(aux+12,0)end
 end
 for i=0,3 do expect(0x43c000+336+2*i,w[57+i])end
 if(c.flags&3)==0 then expect(0x40ba20,0);expect(0x40ba22,2)end
 if weapon_metadata then
  local at=0x43e200+16*c.slot
  expect(at,(c.flags&3)==0 and 0 or 65535);expect(at+2,(c.flags&3)==0 and 2 or 0);expectlong(at+4,3);expectlong(at+8,-1);expectlong(at+12,0)
 end
 end
 local mismatch=0;for addr,value in pairs(before)do if emu.read(addr,mt)~=value then mismatch=mismatch+1;if mismatch<5 then emu.log('MODELOWNERDIFF|'..word(INDEX)..'|'..addr..'|'..emu.read(addr,mt)..'|'..value)end end end
 if not c.bad_ack and not c.nested_bad and c.same_model~=1 then
  if #trace~=#c.trace then faults=faults+1 else for i,n in ipairs(trace)do if n~=c.trace[i]then faults=faults+1 end end end
 elseif c.same_model==1 and #services~=0 then faults=faults+1 end
 if nested_frame_zero and not c.nested_bad then
  if word(sy.SourceFrameStack4086_Depth)~=(c.nested_depth or 0) or word(sy.SourceFrameStack4086_Fault)~=0 or word(sy.SourceUpdateFrame4086_State)~=1 or word(sy.SourceUpdateFrame4086_Pending)~=2 or word(sy.SourceUpdateFrame4086_Request)~=3 then faults=faults+1 end
 end
 emu.log('MODELOWNERRESULT|'..word(INDEX)..'|'..word(sy.SourceModelTransition4086_State)..'|'..mismatch..'|'..ctx..'|'..faults)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('MODELOWNERCLOCK|'..word(INDEX)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault))end,emu.callbackType.exec,CLOCKRESULT,CLOCKRESULT,emu.cpuType.snes,mt)
'''
    if a.nested_frame_zero:
        lua+=r'''
emu.addMemoryCallback(capture,emu.callbackType.exec,NESTEDSTART,NESTEDSTART,emu.cpuType.snes,mt)
emu.addMemoryCallback(capture,emu.callbackType.exec,NESTEDFINISH,NESTEDFINISH,emu.cpuType.snes,mt)
local function nestedContext()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp'] or (cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('MODELOWNERCOST|'..word(INDEX)..'|'..(s.masterClock-start))
end
emu.addMemoryCallback(nestedContext,emu.callbackType.exec,AFTERNESTEDSTART,AFTERNESTEDSTART,emu.cpuType.snes,mt)
emu.addMemoryCallback(nestedContext,emu.callbackType.exec,AFTERNESTEDFINISH,AFTERNESTEDFINISH,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local b=c.nested_bad;local row=0x40f000+512*(word(sy.SourceFrameStack4086_Depth)-1)
 if b=='request'then set('SourceUpdateFrame','Request',1)
 elseif b=='child_slot'then set('SourceUpdateFrame','Slot',(c.slot+1)%128)
 elseif b=='ticket_ready'then put(row+0x140,0)
 elseif b=='ticket_state'then put(row+0x142,2)
 elseif b=='ticket_issued'then put(row+0x168,0)
 elseif b=='ticket_slot'then put(row+0x144,(c.slot+1)%128)
 elseif b=='child_pending'then set('SourceUpdateFrame','Pending',1)end
end,emu.callbackType.exec,FINISHPREFLIGHT,FINISHPREFLIGHT,emu.cpuType.snes,mt)
'''
        values.update(AFTERNESTEDSTART=fs['TransitionFixture_AfterNestedStart'],AFTERNESTEDFINISH=fs['TransitionFixture_AfterNestedFinish'],FINISHPREFLIGHT=fs['TransitionFixture_ChildFinish'])
    values.update(INIT=fs['TransitionFixture_Init'],SERVICE=fs['TransitionFixture_Service'],PENDINGCLOCK=fs['TransitionFixture_PendingClock'],AFTER=fs['TransitionFixture_After'],RESULT=fs['TransitionFixture_Result'],CLOCKRESULT=fs['TransitionFixture_Clock'],AIBYTES=len(ai),FEBYTES=len(fe))
    for k,v in values.items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    script=folder/'observer.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    reporter=Reporter('M4-MODEL-TRANSITION',kind='GATE')
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('MODEL_TRANSITION_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(INDEX,0);m.write_u16(ERROR,0);m.write_u16(REQUEST,0xb4f0)
        for _ in range(1500):
            run_frames_exact(m,1)
            if startup.u16(m,INDEX)==len(rows) or startup.u16(m,ERROR):break
        reporter.check('native ordered transition batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,ERROR)==0)
    results=[];costs=[];clocks=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        for marker,target in [('MODELOWNERRESULT|',results),('MODELOWNERCOST|',costs),('MODELOWNERCLOCK|',clocks)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    def wanted_state(c):
        if c.get('nested_bad'):return 1 if c['nested_bad'] in ('issued','busy','depth') else 0
        return 3 if c.get('bad_ack') else 2
    reporter.check('all source transitions preserve bytes/context and service order',len(results)==len(rows) and all(r==[i,wanted_state(c),0,0,0] for i,(r,c) in enumerate(zip(results,rows))))
    reporter.check('completed transitions retire clock; stale acknowledgements cannot',len(clocks)==len(rows) and all(r==([i,1,48,1] if c.get('bad_ack') or c.get('nested_bad') or c.get('nested_depth') else [i,0,49,0]) for i,(r,c) in enumerate(zip(clocks,rows))))
    report=dict(schema='BYOR_4086_MODEL_TRANSITION_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),results=results,cpu_costs=costs,clock_results=clocks,authority_report_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),entity_weapon_metadata_install_bound=a.weapon_metadata,native_nested_frame_prefix_bound=a.nested_frame_zero,external_services_instrumented=True,full_model_switch_bound=False,frame_zero_effects_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
