"""Owned 4086 clock against native fields, source caps and tick commits.

Private opt-in after original bootstrap; no live foreign world or combat.
Elapsed fields are real: bounded foreground waits exercise backlog policies.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_clock_4086 import Clock,ADDRESS
from actor_s5_entity_fixture import symbols
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,exact_input_edge,run_frames_exact
import game_bor_startup_select as startup
from m4_input_controller_native import offset

REQUEST=0x7ff8f2
MODE=0x7ff8f8
DELAY=0x7ff8fa


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('rom','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[2];folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    sy=symbols(root/'src/main.sym');rom=bytearray(a.rom.read_bytes());entry=sy['Vm_SourceFrameGate'];start=39*32768
    if rom[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a') or rom[start:start+32768]!=bytes(32768):
        raise ValueError('SOURCE_CLOCK_PRIVATE_HOOK_RESERVATION')
    asm='''.snes
.bank 39
.org $8000
SourceClockFixture_Gate:
.a16
.i16
    php
    rep #$31
    pha
    phx
    phy
    lda.l $7FF8F2
    cmp #$B4C7
    bne SourceClockFixture_Return
    lda.l $7FFA00
    cmp #$B4C5
    beq SourceClockFixture_Ready
    jsl $%(init)06X
SourceClockFixture_Ready:
.a16
.i16
    lda.l $7FFA20
    cmp #$B4C6
    bne SourceClockFixture_Return
    lda.l $7FF8FA
    beq SourceClockFixture_Observe
    sta.l $7FF8FC
    lda #0
    sta.l $7FF8FA
    lda.l $7FFA02
    sta.l $7FF8FE
SourceClockFixture_Wait:
.a16
.i16
    lda.l $7FFA02
    sec
    sbc.l $7FF8FE
    cmp.l $7FF8FC
    bcc SourceClockFixture_Wait
SourceClockFixture_Observe:
.a16
.i16
    lda.l $7FF8F8
    jsl $%(observe)06X
    bcs SourceClockFixture_Return
SourceClockFixture_Drain:
.a16
.i16
    lda.l $7FFA16
    beq SourceClockFixture_After
    jsl $%(commit)06X
    bcs SourceClockFixture_Return
    bra SourceClockFixture_Drain
SourceClockFixture_After:
.a16
.i16
    nop
SourceClockFixture_Return:
.a16
.i16
    ply
    plx
    pla
    plp
    php
    rep #$31
    phx
    phy
    jml $%(resume)06X
SourceClockFixture_End:
.a16
.i16
'''%dict(init=sy['SourceClock4086_Start'],observe=sy['SourceClock4086_Observe'],commit=sy['SourceClock4086_Commit'],resume=entry+5)
    pasm=folder/'clock.pasm';pasm.write_text(asm)
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(pasm),
         '--output',str(folder/'clock.bin'),'--symbols',str(folder/'clock.sym'),'--no-pansy'],capture_output=True,text=True)
    (folder/'poppy.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('SOURCE_CLOCK_FIXTURE_ASSEMBLY')
    gates=symbols(folder/'clock.sym');end=offset(gates['SourceClockFixture_End'])
    rom[start:end]=(folder/'clock.bin').read_bytes()[start:end];rom[offset(entry):offset(entry)+5]=bytes.fromhex('5c 00 80 27 ea')
    path=folder/'bor.sfc';path.write_bytes(rom)
    for src in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor*.pcm')]:
        dest=folder/src.name
        if not dest.exists():os.link(src,dest)
    lua=folder/'clock.lua'
    lua.write_text('''local fields=0;local observations=0;local start=0;local mt=emu.memType.snesMemory
local function word(a) return emu.read(a,mt)+256*emu.read(a+1,mt) end
local function long(a) return word(a)+65536*word(a+2) end
emu.addMemoryCallback(function()
 if word(READY)~=0xb4c5 or fields>=256 then return end
 fields=fields+1;local s=emu.getState()
 local f=long(FIELDS);local odd=word(PREVIOUS)>0 and 1 or 0
 emu.log('SOURCECLOCKFIELD|'..f..'|'..math.floor((f+odd)/2)..'|'..s['ppu.frameCount']..'|'..odd)
end,emu.callbackType.exec,NMIDONE,NMIDONE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function() if word(REQUEST)==0xb4c7 then start=emu.getState().masterClock end end,
 emu.callbackType.exec,OBSERVEPOS,OBSERVEPOS,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 if word(REQUEST)~=0xb4c7 or observations>=256 then return end
 observations=observations+1
 emu.log('SOURCECLOCKOBSERVE|'..long(SNAPSHOT)..'|'..long(SNAPSHOT+4)..'|'..long(PHASE)..'|'..long(RAW)..'|'..word(DUE)..'|'..long(TIME)..'|'..word(RUNNING)..'|'..word(FAULT)..'|'..(emu.getState().masterClock-start))
end,emu.callbackType.exec,DONE,DONE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 if word(REQUEST)==0xb4c7 and observations<=256 then emu.log('SOURCECLOCKCOMMIT|'..long(TIME)..'|'..word(DUE)..'|'..word(FAULT)) end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
'''.replace('REQUEST',str(REQUEST)).replace('READY',str(ADDRESS))
      .replace('NMIDONE',str(sy['SourceClock4086_NmiGate__owned_done']))
      .replace('FIELDS',str(sy['SourceClock4086_FieldsLo'])).replace('SHORTS',str(sy['SourceClock4086_ShortsLo']))
      .replace('PREVIOUS',str(sy['SourceClock4086_PreviousShort']))
      .replace('OBSERVEPOS',str(sy['SourceClock4086_Observe'])).replace('DONE',str(sy['SourceClock4086_Observe__due']+4))
      .replace('SNAPSHOT',str(sy['SourceClock4086_Snapshot'])).replace('PHASE',str(sy['SourceClock4086_PhaseLo']))
      .replace('RAW',str(sy['SourceClock4086_RawLo'])).replace('DUE',str(sy['SourceClock4086_Due']))
      .replace('TIME',str(sy['SourceClock4086_TimeLo'])).replace('RUNNING',str(sy['SourceClock4086_Running']))
      .replace('FAULT',str(sy['SourceClock4086_Fault'])).replace('AFTER',str(gates['SourceClockFixture_After'])))
    with lua.open('a') as diagnostic:
        diagnostic.write("\nemu.addMemoryCallback(function()emu.log('SOURCECLOCKOWNERS|'..word("+str(sy['SourceStageProducer4086_Ready'])+")..'|'..word("+str(sy['SourceWait4086_Ready'])+")..'|'..word("+str(sy['SourceCameraMotion4086_Ready'])+")..'|'..word("+str(sy['SourceCameraMotion4086_Status'])+"))end,emu.callbackType.exec,"+str(sy['SourceClock4086_Commit__bad'])+","+str(sy['SourceClock4086_Commit__bad'])+",emu.cpuType.snes,mt)\n")
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    reporter=Reporter('M4-SOURCE-CLOCK',kind='GATE')
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        m.write_u16(REQUEST,0)
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('SOURCE_CLOCK_BOOTSTRAP_REQUIRED')
        run_frames_exact(m,12);reporter.check('native clock cold-disabled',m.read_memory('snesMemory',ADDRESS,80)[:2]==bytes(2))
        m.write_u16(MODE,1);m.write_u16(DELAY,0);m.write_u16(REQUEST,0xb4c7)
        run_frames_exact(m,30)
        for delay in (20,61):
            m.write_u16(DELAY,delay)
            for attempt in range(1500):
                m.tool('run_frames',{'count':1})
                if m.read_memory('snesMemory',DELAY,32)[:2]==bytes(2):break
            else:raise ValueError('SOURCE_CLOCK_DELAY_NOT_CONSUMED')
            run_frames_exact(m,delay+20)
        m.write_u16(MODE,0);run_frames_exact(m,24)
        m.write_u16(MODE,1);run_frames_exact(m,16);m.write_u16(REQUEST,0)
    clock=Clock();field_events=[];observed=[];commits=[];expected_time=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        if 'SOURCECLOCKFIELD|' in line:field_events.append(list(map(int,line.split('SOURCECLOCKFIELD|',1)[1].split('|'))))
        if 'SOURCECLOCKOBSERVE|' in line:
            f,s,phase,raw,due,time,running,fault,cost=map(int,line.split('SOURCECLOCKOBSERVE|',1)[1].split('|'))
            expected_due=clock.observe(f,s,bool(running));exact=phase==clock.phase and due==expected_due and time==clock.time and fault==0
            observed.append(dict(fields=f,shorts=s,phase=phase,raw_ticks=raw,due=due,time_before=time,running=running,fault=fault,exact=exact,master_clocks=cost))
            while clock.due:clock.commit()
            expected_time.append(clock.time)
        if 'SOURCECLOCKCOMMIT|' in line:commits.append(list(map(int,line.split('SOURCECLOCKCOMMIT|',1)[1].split('|'))))
    physical=bool(field_events);short=0
    for i,(fields,shorts,ppu,odd) in enumerate(field_events):
        physical=physical and fields==i and shorts==short and ppu==field_events[0][2]+i
        if (field_events[0][3]+i)%2:short+=1
    reporter.check('physical field and prior short-field counters',physical)
    reporter.check('every source interval and phase matches independent arithmetic',bool(observed) and all(e['exact'] for e in observed))
    reporter.check('logical time commits only the admitted interval',len(commits)==len(expected_time) and all(c==[t,0,0] for c,t in zip(commits,expected_time)))
    reporter.check('real bounded backlog caps to fifty',any(e['raw_ticks']>50 and e['raw_ticks']<=200 and e['due']==50 for e in observed))
    reporter.check('real excessive backlog resets to one',any(e['raw_ticks']>200 and e['due']==1 for e in observed))
    reporter.check('paused intervals consumed without logical ticks',any(not e['running'] and e['raw_ticks']>0 and e['due']==0 for e in observed))
    r=dict(schema='BYOR_SOURCE_CLOCK_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
           rom_sha256=hashlib.sha256(rom).hexdigest(),fields=field_events,observations=observed,commits=commits,
           scope='Native NTSC field clock, pinned 4086 backlog/pause policy and empty tick commits after original bootstrap. No live MOTU world update or gameplay.',
           bank0_growth=0,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
