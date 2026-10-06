"""Native captured-frame B4EP cursor; effect handlers explicitly instrumented."""
import argparse,hashlib,json,os,re,struct,subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_animation_init_native import luav
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

REQUEST,INDEX,ERROR=0x7ffd80,0x7ffd82,0x7ffd84


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True);report=json.loads((a.plan/'report.json').read_text());table=(a.plan/'frame-effects.b4ep').read_bytes()
    if hashlib.sha256(table).hexdigest()!=report['sha256']:raise ValueError('FRAME_EFFECT_PLAN_IDENTITY')
    rows=[]
    for animation in report['animations']:
        for r in animation['frames']:rows.append(dict(handle=animation['handle'],count=len(animation['frames']),frame=r['index'],ops=r['ops'],slot=(0,1,127)[len(rows)%3],bad='',fault=0))
    for bad in ('ready','pending','prefix_ready','prefix_state','prefix_pending','animations','handle_zero','handle_bound','frame','bank','base','bytes','pair','body','directory_count','ack_stale','unissued','stale_slot','stale_handle','stale_frame'):
        rows.append(dict(rows[0],bad=bad,fault=1))
    header=struct.unpack_from('<4s6H4I',table);sy=symbols(Path('src/main.sym'));entry=sy['Vm_SourceFrameGate'];first=39*32768;raw=bytearray(a.rom.read_bytes())
    if raw[first:first+32768]!=bytes(32768) or raw[59*32768:60*32768]!=bytes(32768) or raw[0x7fd8]!=8:raise ValueError('FRAME_EFFECT_PLAN_PRIVATE_RESERVATION')
    asm='''.snes
.bank 39
.org $8000
EffectPlanFixture_Gate:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l REQUEST
 cmp #$B4F2
 beq EffectPlanFixture_Init
 jmp EffectPlanFixture_Return
EffectPlanFixture_Init:
.a16
.i16
 nop
 lda.l SKIP
 beq EffectPlanFixture_Begin
 jmp EffectPlanFixture_Result
EffectPlanFixture_Begin:
.a16
.i16
 jsl BEGIN
EffectPlanFixture_After:
.a16
.i16
 nop
 bcc EffectPlanFixture_Good
 lda.l EXPECTFAULT
 beq EffectPlanFixture_Bad
 bra EffectPlanFixture_Result
EffectPlanFixture_Good:
.a16
.i16
 lda.l STATE
 cmp #2
 beq EffectPlanFixture_Result
EffectPlanFixture_Service:
.a16
.i16
 nop
 jsl CLOCK
EffectPlanFixture_PendingClock:
.a16
.i16
 nop
 jsl ACK
 bra EffectPlanFixture_After
EffectPlanFixture_Result:
.a16
.i16
 nop
 jsl CHECK
EffectPlanFixture_Idle:
.a16
.i16
 nop
 lda #2
 jsl FRAMEACK
 jsl CLOCK
EffectPlanFixture_Clock:
.a16
.i16
 nop
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #CASES
 bcs EffectPlanFixture_Done
 and #7
 beq EffectPlanFixture_Return
 jmp EffectPlanFixture_Init
EffectPlanFixture_Bad:
.a16
.i16
 lda #1
 sta.l ERROR
EffectPlanFixture_Done:
.a16
.i16
 lda #0
 sta.l REQUEST
 sta.l READY
EffectPlanFixture_Return:
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
    values=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,EXPECTFAULT=REQUEST+6,SKIP=REQUEST+8,STATE=sy['SourceFrameEffectPlan4086_State'],READY=sy['SourceFrameEffectPlan4086_Ready'],BEGIN=sy['SourceFrameEffectPlan4086_Begin'],ACK=sy['SourceFrameEffectPlan4086_Ack'],CHECK=sy['SourceFrameEffectPlan4086_CheckIdle'],FRAMEACK=sy['SourceUpdateFrame4086_Ack'],CLOCK=sy['SourceClock4086_Commit'],CASES=len(rows),RESUME=entry+5)
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm)
    pasm=folder/'fixture.pasm';pasm.write_text(asm);proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(pasm),'--output',str(folder/'fixture.bin'),'--symbols',str(folder/'fixture.sym')],capture_output=True,text=True);(folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('FRAME_EFFECT_PLAN_FIXTURE_ASSEMBLY')
    fs=symbols(folder/'fixture.sym');code=(folder/'fixture.bin').read_bytes()[first:];raw[first:first+len(code)]=code;raw[59*32768:59*32768+len(table)]=table
    if raw[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a'):raise ValueError('FRAME_EFFECT_PLAN_GATE')
    raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['EffectPlanFixture_Gate'])[:3]+b'\xea';rom=folder/'bor.sfc';rom.write_bytes(raw)
    for media in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor-*.pcm')]:
        target=folder/media.name
        if not target.exists():os.link(media.resolve(),target)
    lua='local rows='+luav(rows)+'\nlocal sy='+luav({k:v for k,v in sy.items() if k.startswith(('SourceFrameEffectPlan4086_','SourceUpdateFrame4086_','SourceSelf4086_','SourceClock4086_','SourceWorldTick4086_','SourceFrameStack4086_','SourceFrameMotion4086_','SourceAnimationInit4086_','SourceModelAnimation4086_','SourceModelTransition4086_','VmState_'))})+'\n'
    lua+=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local ctx=0;local start=0;local faults=0;local trace={}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function set(k,v)put(sy['SourceFrameEffectPlan4086_'..k],v)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];trace={};ctx=0;faults=0
 for i=0,47 do emu.write(0x7ffb50+i,(i*37)&255,mt)end
 set('Ready',0xb4f2);set('State',0);set('Service',0);set('Acknowledged',0);set('Base',0x8000);set('Bank',59);set('Bytes',TABLEBYTES);set('Animations',ANIMATIONS)
 set('PairedCrcLo',PAIR&65535);set('PairedCrcHi',(PAIR>>16)&65535);set('BodyCrcLo',BODY&65535);set('BodyCrcHi',(BODY>>16)&65535)
 put(sy.SourceUpdateFrame4086_Ready,0xb4e3);put(sy.SourceUpdateFrame4086_State,1);put(sy.SourceUpdateFrame4086_Pending,2);put(sy.SourceUpdateFrame4086_Slot,c.slot);put(sy.SourceUpdateFrame4086_Handle,c.handle);put(sy.SourceUpdateFrame4086_Request,c.frame);put(sy.SourceUpdateFrame4086_Count,c.count);put(sy.SourceUpdateFrame4086_Animations,ANIMATIONS)
 put(sy.SourceFrameMotion4086_Ready,0);put(sy.SourceFrameStack4086_Ready,0);put(sy.SourceWorldTick4086_Ready,0);put(sy.SourceAnimationInit4086_Ready,0);put(sy.SourceModelAnimation4086_Ready,0);put(sy.SourceModelTransition4086_Ready,0);put(sy.VmState_Status,4)
 put(sy.SourceSelf4086_Ready,0)
 put(sy.SourceClock4086_Ready,0xb4c5);put(sy.SourceClock4086_Due,1);put(sy.SourceClock4086_TimeLo,48);put(sy.SourceClock4086_TimeHi,0);put(sy.SourceClock4086_Fault,0);put(EXPECTFAULT,c.fault)
 put(SKIP,c.bad=='unissued' and 1 or 0)
 if c.bad=='ready'then set('Ready',0)
 elseif c.bad=='pending'then set('State',1)
 elseif c.bad=='prefix_ready'then put(sy.SourceUpdateFrame4086_Ready,0)
 elseif c.bad=='prefix_state'then put(sy.SourceUpdateFrame4086_State,2)
 elseif c.bad=='prefix_pending'then put(sy.SourceUpdateFrame4086_Pending,1)
 elseif c.bad=='animations'then set('Animations',0)
 elseif c.bad=='handle_zero'then put(sy.SourceUpdateFrame4086_Handle,0)
 elseif c.bad=='handle_bound'then put(sy.SourceUpdateFrame4086_Handle,ANIMATIONS+1)
 elseif c.bad=='frame'then put(sy.SourceUpdateFrame4086_Request,c.count)
 elseif c.bad=='bank'then set('Bank',64)
 elseif c.bad=='base'then set('Base',0x7ffe)
 elseif c.bad=='bytes'then set('Bytes',39)
 elseif c.bad=='pair'then set('PairedCrcLo',(PAIR&65535)~1)
 elseif c.bad=='body'then set('BodyCrcLo',(BODY&65535)~1)
 elseif c.bad=='directory_count'then put(sy.SourceUpdateFrame4086_Count,c.count+1)end
 before={};for i=0,47 do before[0x7ffb50+i]=emu.read(0x7ffb50+i,mt)end
 for i=0,15 do before[sy.SourceFrameEffectPlan4086_Base+i]=emu.read(sy.SourceFrameEffectPlan4086_Base+i,mt)end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
local function capture()local s=emu.getState();start=s.masterClock;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end end
emu.addMemoryCallback(capture,emu.callbackType.exec,BEGIN,BEGIN,emu.cpuType.snes,mt)
emu.addMemoryCallback(capture,emu.callbackType.exec,ACK,ACK,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp'] or (cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('EFFECTPLANCOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local op=word(sy.SourceFrameEffectPlan4086_Service);trace[#trace+1]=op
 if op~=c.ops[#trace]then faults=faults+1 end
 set('Acknowledged',c.bad=='ack_stale' and 0 or op)
 -- Isolate the cursor's direct clock guard from its parent prefix.
 put(sy.SourceUpdateFrame4086_Ready,0)
end,emu.callbackType.exec,SERVICE,SERVICE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 if word(sy.SourceClock4086_Due)~=1 or word(sy.SourceClock4086_TimeLo)~=48 or word(sy.SourceClock4086_Fault)~=1 then faults=faults+1 end
 put(sy.SourceClock4086_Fault,0);put(sy.SourceUpdateFrame4086_Ready,0xb4e3)
end,emu.callbackType.exec,PENDINGCLOCK,PENDINGCLOCK,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local mismatch=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then mismatch=mismatch+1 end end
 if c.fault==0 and #trace~=#c.ops then faults=faults+1 end
 emu.log('EFFECTPLANRESULT|'..word(INDEX)..'|'..word(sy.SourceFrameEffectPlan4086_State)..'|'..mismatch..'|'..ctx..'|'..faults)
 if c.bad=='stale_slot'then set('Slot',(c.slot+1)%128)
 elseif c.bad=='stale_handle'then set('Handle',c.handle+1)
 elseif c.bad=='stale_frame'then set('Frame',c.frame+1)end
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('EFFECTPLANIDLE|'..word(INDEX)..'|'..(emu.getState()['cpu.ps']&1))end,emu.callbackType.exec,IDLE,IDLE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('EFFECTPLANCLOCK|'..word(INDEX)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault))end,emu.callbackType.exec,CLOCKRESULT,CLOCKRESULT,emu.cpuType.snes,mt)
'''
    values.update(INIT=fs['EffectPlanFixture_Init'],AFTER=fs['EffectPlanFixture_After'],SERVICE=fs['EffectPlanFixture_Service'],PENDINGCLOCK=fs['EffectPlanFixture_PendingClock'],RESULT=fs['EffectPlanFixture_Result'],IDLE=fs['EffectPlanFixture_Idle'],CLOCKRESULT=fs['EffectPlanFixture_Clock'],TABLEBYTES=len(table),ANIMATIONS=len(report['animations']),PAIR=header[-2],BODY=header[-1])
    for k,v in values.items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    script=folder/'observer.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    reporter=Reporter('M4-FRAME-EFFECT-PLAN',kind='GATE')
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('FRAME_EFFECT_PLAN_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(INDEX,0);m.write_u16(ERROR,0);m.write_u16(REQUEST,0xb4f2)
        for _ in range(2000):
            run_frames_exact(m,1)
            if startup.u16(m,INDEX)==len(rows) or startup.u16(m,ERROR):break
        reporter.check('native effect plan batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,ERROR)==0)
    results=[];costs=[];clocks=[];idle=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        for marker,target in [('EFFECTPLANRESULT|',results),('EFFECTPLANCOST|',costs),('EFFECTPLANCLOCK|',clocks),('EFFECTPLANIDLE|',idle)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    def expected_state(c):
        if c['bad']=='unissued':return 0
        if c['bad'].startswith('stale_'):return 2
        return 3 if c['fault'] else 2
    reporter.check('every authored plan operation preserves captured prefix and CPU context',len(results)==len(rows) and all(r==[i,expected_state(c),0,0,0] for i,(r,c) in enumerate(zip(results,rows))))
    reporter.check('admitted pending/faulty cursor blocks clock and parent effect acknowledgement',len(clocks)==len(rows) and all(r==([i,1,48,1] if c['fault'] and c['bad']!='ready' else [i,0,49,0]) for i,(r,c) in enumerate(zip(clocks,rows))))
    reporter.check('cursor idle guard accepts idle/completion or disabled lease',len(idle)==len(rows) and all(r==[i,0 if not c['fault'] or c['bad'] in ('ready','unissued') or c['bad'].startswith('stale_') else 1] for i,(r,c) in enumerate(zip(idle,rows))))
    r=dict(schema='BYOR_4086_FRAME_EFFECT_PLAN_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),source_frames=836,results=results,cpu_costs=costs,clock_results=clocks,idle_results=idle,plan_sha256=report['sha256'],disabled_lease_uses_existing_static_path=True,foreign_profile_admitted=False,effect_handlers_instrumented=True,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
