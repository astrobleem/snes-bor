"""Real JOY1/JOY2 to owned BOR masks after the original source bootstrap.

The private wrapper calls the real banked bridge once per physical NMI epoch.
It does not install controller masks through debugger writes. Its timestamp
is the hardware field counter; this fixture is not the 200-Hz world owner.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_input_controller import BINDING,convert,refresh
from source_script_input import ADDRESS,MAGIC
from actor_s5_entity_fixture import symbols
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,exact_input_edge,run_frames_exact
import game_bor_startup_select as startup

REQUEST=0x7ff8f2
COUNT=0x7ff8f8
PORT_COUNT=0x7ff8fa


def offset(address):return (address>>16)*32768+(address&65535)-32768


def build(original,sy,folder):
    rom=bytearray(original);target=sy.get('SourceClock4086_NmiGate',sy['StageTimer_NmiField'])
    needle=bytes([0x22,target&255,target>>8&255,target>>16])
    entry=rom.find(needle)
    if entry<0 or rom.find(needle,entry+1)>=0:raise ValueError('SOURCE_INPUT_NMI_HOOK_CHANGED')
    start=39*32768
    if rom[start:start+32768] not in (bytes(32768),bytes([255])*32768):
        raise ValueError('SOURCE_INPUT_FIXTURE_BANK_OCCUPIED')
    asm='''.snes
.bank 39
.org $8000
SourceInputFixture_Gate:
.a16
.i16
    php
    rep #$31
    pha
    phx
    phy
    lda.l $7FF8F2
    cmp #$B4C4
    bne SourceInputFixture_Return
    lda.l $7FF8F8
    inc a
    sta.l $7FF8F8
    tax
    ldy #0
    lda.l $7FF8FA
    jsl $%(bridge)06X
SourceInputFixture_Return:
.a16
.i16
    ply
    plx
    pla
    plp
    jml $%(resume)06X
SourceInputFixture_End:
.a16
.i16
'''%dict(bridge=sy['SourceInputController_Refresh'],resume=target)
    path=folder/'input.pasm';path.write_text(asm)
    cmd=['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(path),
         '--output',str(folder/'input.bin'),'--symbols',str(folder/'input.sym'),'--no-pansy']
    p=subprocess.run(cmd,capture_output=True,text=True);(folder/'poppy.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise ValueError('SOURCE_INPUT_FIXTURE_ASSEMBLY')
    gates=symbols(folder/'input.sym');end=offset(gates['SourceInputFixture_End'])
    rom[start:end]=(folder/'input.bin').read_bytes()[start:end]
    rom[entry:entry+4]=bytes.fromhex('22 00 80 27')
    return rom


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('rom','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[2];folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    sy=symbols(root/'src/main.sym');rom=build(a.rom.read_bytes(),sy,folder);path=folder/'bor.sfc';path.write_bytes(rom)
    for src in a.rom.parent.glob('bor*.pcm'):
        dest=folder/src.name
        if not dest.exists():os.link(src,dest)
    src=a.rom.parent/'bor.msu';dest=folder/'bor.msu'
    if not dest.exists():os.link(src,dest)
    lua=folder/'input.lua'
    lua.write_text('''local count=0;local start=0;local mt=emu.memType.snesMemory
local function word(a) return emu.read(a,mt)+256*emu.read(a+1,mt) end
emu.addMemoryCallback(function() if word(REQUEST)==0xb4c4 then start=emu.getState().masterClock end end,
 emu.callbackType.exec,START,START,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 if count>=240 or word(REQUEST)~=0xb4c4 then return end
 count=count+1;local data={}
 for i=0,31 do data[#data+1]=string.format('%02x',emu.read(SNAPSHOT+i,mt)) end
 emu.log('SOURCEINPUT|'..word(RAW1)..'|'..word(RAW2)..'|'..table.concat(data)..'|'..(emu.getState().masterClock-start))
end,emu.callbackType.exec,DONE,DONE,emu.cpuType.snes,mt)
'''.replace('REQUEST',str(REQUEST)).replace('SNAPSHOT',str(ADDRESS))
    .replace('RAW1',str(sy['SourceInputController_Raw1'])).replace('RAW2',str(sy['SourceInputController_Raw2']))
    .replace('START',str(sy['SourceInputController_Refresh'])).replace('DONE',str(sy['SourceInputController_Refresh__done'])))
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--Snes.Port2.Type=SnesController',
                '--Snes.AllowInvalidInput=true','--donotsavesettings',str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    reporter=Reporter('M4-CONTROLLER-SOURCE',kind='GATE')
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        # Cold-disable the fixture request before any script dispatch. Source
        # snapshot itself is cleared by the production native boot.
        m.write_u16(REQUEST,0)
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('SOURCE_INPUT_BOOTSTRAP_REQUIRED')
        run_frames_exact(m,12);reporter.check('native lease cold-disabled',m.read_memory('snesMemory',ADDRESS,32)[:2]==bytes(2))
        m.write_u16(COUNT,0);m.write_u16(PORT_COUNT,2);m.write_u16(REQUEST,0xb4c4)
        run_frames_exact(m,4)
        physical_to_mcp={0x4000:m.BTN_Y,0x8000:m.BTN_B,0x0080:m.BTN_A,0x0040:m.BTN_X,
                         0x0020:m.BTN_L,0x0010:m.BTN_R,0x2000:m.BTN_SELECT,0x1000:m.BTN_START,
                         0x0800:m.BTN_UP,0x0400:m.BTN_DOWN,0x0200:m.BTN_LEFT,0x0100:m.BTN_RIGHT}
        for port in (0,1):
            for bit,_ in BINDING:
                exact_input_edge(m,physical_to_mcp[bit],4,port=port);run_frames_exact(m,3)
        exact_input_edge(m,0xfff,4,port=1);run_frames_exact(m,4)
        for count in (0,3):
            before=m.read_memory('snesMemory',ADDRESS,32)
            m.write_u16(PORT_COUNT,count);run_frames_exact(m,3)
            reporter.check('unsupported physical port count '+str(count)+' preserves snapshot',
                           m.read_memory('snesMemory',ADDRESS,32)==before)
        m.write_u16(REQUEST,0)
    events=[];old=[0,0];observed=set();new=set();released=set()
    for line in (folder/'mesen.log').read_text().splitlines():
        if 'SOURCEINPUT|' not in line:continue
        s1,s2,data,cost=line.split('SOURCEINPUT|',1)[1].split('|');raw=[int(s1),int(s2)];data=bytes.fromhex(data)
        ready,count,tick=struct.unpack_from('<HHI',data);rows=[struct.unpack_from('<III',data,8+12*i) for i in range(2)]
        expected=refresh(old,raw);exact=ready==MAGIC and count==2 and rows==expected
        events.append(dict(raw=raw,tick=tick,rows=rows,exact=exact,master_clocks=int(cost)))
        for port in range(2):
            for bit,name in BINDING:
                mask=convert(bit)
                if rows[port][0]&mask:observed.add((port,name))
                if rows[port][1]&mask:new.add((port,name))
                if rows[port][2]&mask:released.add((port,name))
        old=[r[0] for r in rows]
    required={(port,name) for port in range(2) for _,name in BINDING}
    reporter.check('every native snapshot equals actual latched controller masks',bool(events) and all(e['exact'] for e in events))
    reporter.check('both physical ports cover every held binding',required<=observed)
    reporter.check('both physical ports cover every pressed binding',required<=new)
    reporter.check('both physical ports cover every released binding',required<=released)
    report=dict(schema='BYOR_SOURCE_CONTROLLER_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
                rom_sha256=hashlib.sha256(rom).hexdigest(),events=events,control_binding=BINDING,
                peak_refresh_master_clocks=max(e['master_clocks'] for e in events),
                scope='Real physical controller latches and native outer-refresh snapshots after original BOR bootstrap. Field-counter timestamps are fixture data, not a 200-Hz live MOTU world.',bank0_growth=0)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
