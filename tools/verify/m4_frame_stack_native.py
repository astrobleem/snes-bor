"""Bounded native frame-effect snapshots; no recursive VM or gameplay claim."""
import argparse,hashlib,json,os,re,struct,subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_animation_init_native import luav
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

REQUEST,INDEX,ERROR,MODE=0x7ffd80,0x7ffd82,0x7ffd84,0x7ffd86


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    rows=[dict(mode=mode,depth=d,seed=seed,bad='',fault=0) for mode in (0,1) for d in (range(8) if mode==0 else range(1,9)) for seed in (0,17,131,255)]
    for seed in (0,17,131,255):
        rows.extend(dict(mode=0,depth=d,seed=(seed+13*d)&255,bad='',fault=0,chain=1,step=d) for d in range(8))
        rows.extend(dict(mode=1,depth=d,seed=(seed+7*d)&255,bad='',fault=0,chain=1,step=16-d) for d in range(8,0,-1))
    for mode in (0,1):
        for bad in ('ready','sticky','depth','busy','active','running','yielded','vmfault','callback','callback_fault','frame_ready','frame_state','frame_pending','motion','init','model','transition'):
            rows.append(dict(mode=mode,depth=1 if mode else 0,seed=31,bad=bad,fault=1))
    sy=symbols(Path('src/main.sym'));entry=sy['Vm_SourceFrameGate'];raw=bytearray(a.rom.read_bytes());first=39*32768
    if raw[first:first+32768]!=bytes(32768) or raw[0x7fd8]!=8:raise ValueError('FRAME_STACK_PROOF_RESERVATION')
    asm='''.snes
.bank 39
.org $8000
FrameStackFixture_Gate:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l REQUEST
 cmp #$B4EE
 bne FrameStackFixture_Return
FrameStackFixture_Init:
.a16
.i16
 nop
 lda.l MODE
 bne FrameStackFixture_Pop
 jsl PUSH
 bra FrameStackFixture_After
FrameStackFixture_Pop:
.a16
.i16
 jsl POP
FrameStackFixture_After:
.a16
.i16
 nop
 bcc FrameStackFixture_Success
 lda.l EXPECTFAULT
 beq FrameStackFixture_Bad
 bra FrameStackFixture_Result
FrameStackFixture_Success:
.a16
.i16
 lda.l EXPECTFAULT
 bne FrameStackFixture_Bad
FrameStackFixture_Result:
.a16
.i16
 nop
 jsl CHECKIDLE
FrameStackFixture_IdleResult:
.a16
.i16
 nop
 jsl CLOCK
FrameStackFixture_ClockResult:
.a16
.i16
 nop
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #CASES
 bcs FrameStackFixture_Done
 and #3
 bne FrameStackFixture_Init
 bra FrameStackFixture_Return
FrameStackFixture_Bad:
.a16
.i16
 lda #1
 sta.l ERROR
FrameStackFixture_Done:
.a16
.i16
 lda #0
 sta.l REQUEST
 sta.l READY
FrameStackFixture_Return:
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
    values=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,MODE=MODE,EXPECTFAULT=MODE+2,PUSH=sy['SourceFrameStack4086_Push'],POP=sy['SourceFrameStack4086_Pop'],CHECKIDLE=sy['SourceFrameStack4086_CheckIdle'],CLOCK=sy['SourceClock4086_Commit'],CASES=len(rows),READY=sy['SourceFrameStack4086_Ready'],RESUME=entry+5)
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm)
    pasm=folder/'fixture.pasm';pasm.write_text(asm)
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(pasm),'--output',str(folder/'fixture.bin'),'--symbols',str(folder/'fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('FRAME_STACK_FIXTURE_ASSEMBLY')
    fs=symbols(folder/'fixture.sym');code=(folder/'fixture.bin').read_bytes()[first:]
    if raw[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a'):raise ValueError('FRAME_STACK_PRIVATE_GATE')
    raw[first:first+len(code)]=code;raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['FrameStackFixture_Gate'])[:3]+b'\xea'
    rom=folder/'bor.sfc';rom.write_bytes(raw)
    for media in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor-*.pcm')]:
        target=folder/media.name
        if not target.exists():os.link(media.resolve(),target)
    lua='local rows='+luav(rows)+'\nlocal sy='+luav({k:v for k,v in sy.items() if k.startswith(('SourceFrameStack4086_','SourceUpdateFrame4086_','SourceFrameMotion4086_','SourceAnimationCallback4086_','SourceAnimationInit4086_','SourceModelAnimation4086_','SourceModelTransition4086_','SourceVMRun4086_','VmSourceCallback_','VmState_','SourceClock4086_','SourceWorldTick4086_'))})+'\n'
    lua+=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local start=0;local ctx=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function set(k,v)put(sy['SourceFrameStack4086_'..k],v)end
local ranges={{0x7ffb50,496},{0x40efc0,64},{0x40f000,4096},{0x414000,10240},{0x43c000,8192}}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 for _,r in ipairs(ranges)do
  if not(c.chain==1 and c.step>0 and r[1]==0x40f000)then
   for i=0,r[2]-1 do emu.write(r[1]+i,(i*37+c.seed)&255,mt)end
  end
 end
 set('Ready',0xb4ed);if c.chain~=1 or c.step==0 then set('Depth',c.depth)end
 set('Fault',0);put(MODE,c.mode);put(EXPECTFAULT,c.fault)
 put(sy.SourceVMRun4086_Busy,0);put(sy.VmSourceCallback_Active,0);put(sy.VmState_Status,4)
 put(sy.SourceAnimationCallback4086_Ready,0xb4e6);put(sy.SourceAnimationCallback4086_State,3)
 put(sy.SourceUpdateFrame4086_Ready,0xb4e3);put(sy.SourceUpdateFrame4086_State,c.mode==0 and 1 or 2);put(sy.SourceUpdateFrame4086_Pending,c.mode==0 and 2 or 0)
 put(sy.SourceFrameMotion4086_Ready,0xb4e8);put(sy.SourceFrameMotion4086_Status,1)
 put(sy.SourceAnimationInit4086_Ready,0xb4ec);put(sy.SourceAnimationInit4086_State,c.mode==0 and 1 or 2);put(sy.SourceAnimationInit4086_Issued,1)
 put(sy.SourceModelAnimation4086_Ready,0xb4ef);put(sy.SourceModelAnimation4086_State,c.mode==0 and 1 or 2)
 put(sy.SourceModelTransition4086_Ready,0xb4f0);put(sy.SourceModelTransition4086_State,c.mode==0 and 1 or 2);put(sy.SourceModelTransition4086_Service,c.mode==0 and 4 or 0);put(sy.SourceModelTransition4086_Acknowledged,0)
 if c.bad=='ready'then set('Ready',0)
 elseif c.bad=='sticky'then set('Fault',1)
 elseif c.bad=='depth'then set('Depth',c.mode==0 and 8 or 0)
 elseif c.bad=='busy'then put(sy.SourceVMRun4086_Busy,0xb4d8)
 elseif c.bad=='active'then put(sy.VmSourceCallback_Active,1)
 elseif c.bad=='running'then put(sy.VmState_Status,2)
 elseif c.bad=='yielded'then put(sy.VmState_Status,3)
 elseif c.bad=='vmfault'then put(sy.VmState_Status,5)
 elseif c.bad=='callback'then put(sy.SourceAnimationCallback4086_State,1)
 elseif c.bad=='callback_fault'then put(sy.SourceAnimationCallback4086_State,4)
 elseif c.bad=='frame_ready'then put(sy.SourceUpdateFrame4086_Ready,0)
 elseif c.bad=='frame_state'then put(sy.SourceUpdateFrame4086_State,3)
 elseif c.bad=='frame_pending'then put(sy.SourceUpdateFrame4086_Pending,1)
 elseif c.bad=='motion'then
  if c.mode==0 then put(sy.SourceFrameMotion4086_Status,0)else put(sy.SourceAnimationInit4086_State,1)end
 elseif c.bad=='init'then put(sy.SourceAnimationInit4086_State,3)
 elseif c.bad=='model'then put(sy.SourceModelAnimation4086_State,3)
 elseif c.bad=='transition'then put(sy.SourceModelTransition4086_State,3)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
local function capture()
 local s=emu.getState();start=s.masterClock;ctx=0;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end
emu.addMemoryCallback(capture,emu.callbackType.exec,PUSH,PUSH,emu.cpuType.snes,mt)
emu.addMemoryCallback(capture,emu.callbackType.exec,POP,POP,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp'] or (cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('FRAMESTACKCOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 local function expect(a,v)before[a]=v&255;before[a+1]=(v>>8)&255 end
 if c.fault==0 then
  local row=0x40f000+512*(c.mode==0 and c.depth or c.depth-1)
  if c.mode==0 then
   for i=0,495 do before[row+i]=before[0x7ffb50+i]end
   for _,k in ipairs({'SourceUpdateFrame4086_State','SourceUpdateFrame4086_Pending','SourceFrameMotion4086_Status','SourceAnimationCallback4086_State','SourceAnimationInit4086_State','SourceAnimationInit4086_Issued','SourceModelAnimation4086_State','SourceModelTransition4086_State','SourceModelTransition4086_Service','SourceModelTransition4086_Acknowledged'})do expect(sy[k],0)end
  else for i=0,495 do before[0x7ffb50+i]=before[row+i]end end
 end
 local mismatch=0;for addr,v in pairs(before)do if emu.read(addr,mt)~=v then mismatch=mismatch+1 end end
 emu.log('FRAMESTACKRESULT|'..word(INDEX)..'|'..word(sy.SourceFrameStack4086_Depth)..'|'..word(sy.SourceFrameStack4086_Fault)..'|'..mismatch..'|'..ctx)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 emu.log('FRAMESTACKIDLE|'..word(INDEX)..'|'..(emu.getState()['cpu.ps']&1))
 -- Isolate direct stack guard from frame/init owners already byte-verified.
 put(sy.SourceUpdateFrame4086_Ready,0);put(sy.SourceAnimationInit4086_Ready,0);put(sy.SourceModelAnimation4086_Ready,0);put(sy.SourceWorldTick4086_Ready,0);put(sy.SourceModelTransition4086_Ready,0)
 put(sy.SourceClock4086_Ready,0xb4c5);put(sy.SourceClock4086_Due,1);put(sy.SourceClock4086_TimeLo,48);put(sy.SourceClock4086_TimeHi,0);put(sy.SourceClock4086_Fault,0)
end,emu.callbackType.exec,IDLERESULT,IDLERESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('FRAMESTACKCLOCK|'..word(INDEX)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault))end,emu.callbackType.exec,CLOCKRESULT,CLOCKRESULT,emu.cpuType.snes,mt)
'''
    values.update(INIT=fs['FrameStackFixture_Init'],AFTER=fs['FrameStackFixture_After'],RESULT=fs['FrameStackFixture_Result'],IDLERESULT=fs['FrameStackFixture_IdleResult'],CLOCKRESULT=fs['FrameStackFixture_ClockResult'])
    for k,v in values.items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    script=folder/'observer.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    reporter=Reporter('M4-FRAME-STACK',kind='GATE')
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        reporter.check('cold frame stack disabled',startup.u16(m,sy['SourceFrameStack4086_Ready'])==0)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('FRAME_STACK_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(INDEX,0);m.write_u16(ERROR,0);m.write_u16(REQUEST,0xb4ee)
        for _ in range(1500):
            run_frames_exact(m,1)
            if startup.u16(m,INDEX)==len(rows) or startup.u16(m,ERROR):break
        reporter.check('native stack batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,ERROR)==0)
    results=[];costs=[];idle=[];clocks=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        for marker,target in [('FRAMESTACKRESULT|',results),('FRAMESTACKCOST|',costs),('FRAMESTACKIDLE|',idle),('FRAMESTACKCLOCK|',clocks)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    def wanted(c):
        d=c['depth']
        if c['fault']:return (8 if c['mode']==0 else 0) if c['bad']=='depth' else d
        return d+1 if c['mode']==0 else d-1
    reporter.check('all snapshot bytes, untouched live entities/cache, guards and CPU context match',len(results)==len(rows) and all(r==[i,wanted(c),c['fault'],0,0] for i,(r,c) in enumerate(zip(results,rows))))
    reporter.check('outstanding stack or sticky fault blocks idle',len(idle)==len(rows) and all(r==[i,int(c['bad']!='ready' and (wanted(c)!=0 or c['fault']))] for i,(r,c) in enumerate(zip(idle,rows))))
    reporter.check('direct clock cannot commit outstanding frame continuations',len(clocks)==len(rows) and all(r==[i,1,48,1] if c['bad']!='ready' and (wanted(c)!=0 or c['fault']) else r==[i,0,49,0] for i,(r,c) in enumerate(zip(clocks,rows))))
    report=dict(schema='BYOR_4086_FRAME_EFFECT_STACK_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),results=results,cpu_costs=costs,idle_results=idle,clock_results=clocks,
        stack_range='40F000..40FFFF',snapshot_range='7FFB50..7FFD3F',maximum_depth=8,bytes_per_snapshot=496,row_stride=512,lifo_chains=4,lifo_chain_cases=64,
        child_services_instrumented=True,recursive_interpreter_bound=False,weapon_frame_execution_bound=False,live_presentation_contention_proven=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
