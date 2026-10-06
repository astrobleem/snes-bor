"""Native owner traversal against pinned C; gameplay services instrumented.

The native CPU owns requests, acknowledgments, compaction and clock commit.
Lua supplies controlled external service outcomes, not gameplay certification.
"""
import argparse
import hashlib
import json
import os
import re
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
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    authority=json.loads((a.authority/'report.json').read_text());rows=cases()
    if authority['status']!='PASS' or [r['case'] for r in authority['results']]!=rows:
        raise ValueError('WORLD_TICK_PINNED_AUTHORITY_REQUIRED')
    sy=symbols(Path('src/main.sym'));rom=bytearray(a.rom.read_bytes());entry=sy['Vm_SourceFrameGate'];start=39*32768
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
    replacements=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,CASES=len(rows),RESUME=entry+5,
        BEGIN=sy['SourceWorldTick4086_Begin'],POLL=sy['SourceWorldTick4086_Poll'],
        ACK=sy['SourceWorldTick4086_Ack'],COMMIT=sy['SourceWorldTick4086_Commit'],
        PHASE=sy['SourceWorldTick4086_Phase'],WORLDREADY=sy['VmSourceWorld_Ready'],
        TICKREADY=sy['SourceWorldTick4086_Ready'],CLOCKREADY=sy['SourceClock4086_Ready'])
    replacements.update(CLOCKCOMMIT=sy['SourceClock4086_Commit'],CLOCKFAULT=sy['SourceClock4086_Fault'],
                        FAULTINDEX=FAULT_INDEX,VMSTATUS=sy['VmState_Status'])
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
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local index=word(INDEX);local c=fixtures[index+1]
 local service=word(sy.SourceWorldTick4086_Phase);local slot=word(sy.SourceWorldTick4086_Slot)
 emu.log('WORLDTICKEVENT|'..index..'|'..service..'|'..slot..'|'..dw(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Due))
 if service==3 then put(sy.SourceWorldTick4086_Frozen,bit(c.frozen,slot),2) end
 if service==c.kill_stage and slot==c.kill_slot then put(0x414004+80*slot,0,2) end
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
'''.replace('FIXTURES',fixture).replace('SYMBOLS','{'+','.join(k+'='+str(v) for k,v in sy.items() if k.startswith(('SourceWorldTick4086_','SourceClock4086_','VmSourceWorld_','VmState_')))+'}')
    for key,value in dict(INDEX=INDEX,INIT=fs['WorldTickFixture_Init'],OBSERVE=fs['WorldTickFixture_Observe'],RESULT=fs['WorldTickFixture_Result'],
        FAULTINDEX=FAULT_INDEX,FAULTINIT=fs['WorldTickFixture_FaultInit'],FAULTOBSERVE=fs['WorldTickFixture_FaultObserved']).items():
        lua=re.sub(r'\b'+key+r'\b',str(value),lua)
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
        for _ in range(12):
            run_frames_exact(m,60)
            if (startup.u16(m,INDEX)==len(rows) and startup.u16(m,FAULT_INDEX)==10) or startup.u16(m,ERROR):break
        reporter.check('native traversal batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,FAULT_INDEX)==10 and startup.u16(m,ERROR)==0)
    actual=[dict(events=[]) for _ in rows];clock_checks=[];faults=[]
    for line in (folder/'mesen.log').read_text().splitlines():
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
    report=dict(schema='BYOR_4086_WORLD_TICK_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(rom).hexdigest(),authority_functions_sha256=authority['functions_sha256'],
        cases=len(rows),events=sum(len(r['events']) for r in actual),comparisons=comparisons,
        rejections=faults,early_direct_clock_commit_rejections=len(rows),
        bank0_growth=0,live_gameplay_handlers_bound=False,motu_gameplay_proven=False)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
