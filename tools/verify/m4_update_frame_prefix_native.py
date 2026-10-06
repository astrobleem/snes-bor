"""Native update_frame prefix/ownership gate; effect and script services mocked."""
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
from source_frame_effects_4086 import derive,pack,unpack
from compiler import Source
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

REQUEST,INDEX,ERROR=0x7ffb80,0x7ffb82,0x7ffb84


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    report=derive(Source(a.source));table=pack(report);unpack(table);sy=symbols(Path('src/main.sym'))
    rows=[]
    for an in report['animations']:
        for f in an['frames']:
            for animating in (-1,0,1):
                rows.append(dict(handle=an['handle'],f=f['index'],count=len(an['frames']),delay=f['delay_ticks'],
                    animating=animating,mode=0,slot=(0,1,127)[len(rows)%3],time=0xffffffff if len(rows)%17==0 else 48))
    sample=next(c for c in rows if c['count']>2 and c['f']==1 and c['animating']==1)
    rows += [dict(sample,mode=mode) for mode in (1,2,3)]
    rows += [dict(sample,f=sample['count'],mode=0),dict(sample,f=sample['count']+1,mode=0)]
    asm='''.snes
.bank 39
.org $8000
PrefixFixture_Gate:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l REQUEST
 cmp #$B4E4
 bne PrefixFixture_Return
 lda #0
 sta.l REQUEST
 sta.l INDEX
 sta.l ERROR
PrefixFixture_Init:
.a16
.i16
 nop
 jsl BEGIN
 bcs PrefixFixture_Bad
 cmp #0
 beq PrefixFixture_Result
PrefixFixture_Pending:
.a16
.i16
 nop
 jsl CHECKIDLE
 bcc PrefixFixture_Bad
 jsl CLOCKCOMMIT
 bcc PrefixFixture_Bad
PrefixFixture_Observe:
.a16
.i16
 nop
 lda.l PENDING
 jsl ACK
 bcs PrefixFixture_Bad
 cmp #0
 bne PrefixFixture_Pending
PrefixFixture_Result:
.a16
.i16
 nop
 jsl CHECKIDLE
 bcs PrefixFixture_Bad
 jsl CLOCKCOMMIT
 bcs PrefixFixture_Bad
PrefixFixture_Committed:
.a16
.i16
 nop
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #CASES
 bcc PrefixFixture_Init
 bra PrefixFixture_Done
PrefixFixture_Bad:
.a16
.i16
 lda #1
 sta.l ERROR
PrefixFixture_Done:
.a16
.i16
 lda #0
 sta.l OWNERREADY
 sta.l CLOCKREADY
 sta.l WORLDREADY
PrefixFixture_Return:
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
    replacements=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,BEGIN=sy['SourceUpdateFrame4086_Begin'],
        ACK=sy['SourceUpdateFrame4086_Ack'],CHECKIDLE=sy['SourceUpdateFrame4086_CheckIdle'],
        CLOCKCOMMIT=sy['SourceClock4086_Commit'],PENDING=sy['SourceUpdateFrame4086_Pending'],
        OWNERREADY=sy['SourceUpdateFrame4086_Ready'],CLOCKREADY=sy['SourceClock4086_Ready'],
        WORLDREADY=sy['VmSourceWorld_Ready'],RESUME=sy['Vm_SourceFrameGate']+5,CASES=len(rows))
    for key,value in replacements.items():asm=re.sub(r'\b'+key+r'\b',str(value),asm)
    branch=[0]
    def relax(m):
        branch[0]+=1;label='PrefixFixture_Branch_'+str(branch[0])
        return ' '+dict(bcc='bcs',bcs='bcc',beq='bne',bne='beq')[m[1]]+' '+label+'\n jmp '+m[2]+'\n'+label+':\n.a16\n.i16'
    asm=re.sub(r'^ (bcc|bcs|beq|bne) (PrefixFixture_\w+)$',relax,asm,flags=re.M)
    pasm=folder/'prefix_fixture.pasm';pasm.write_text(asm)
    built=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',
        str(pasm),'--output',str(folder/'prefix_fixture.bin'),'--symbols',str(folder/'prefix_fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(built.stdout+built.stderr)
    if built.returncode:raise ValueError('PREFIX_FIXTURE_ASSEMBLY')
    fs=symbols(folder/'prefix_fixture.sym');raw=bytearray(a.rom.read_bytes());entry=sy['Vm_SourceFrameGate']
    first=39*32768;fixture=(folder/'prefix_fixture.bin').read_bytes()[first:]
    if raw[first:first+32768]!=bytes(32768) or raw[60*32768:61*32768]!=bytes(32768):raise ValueError('PREFIX_FIXTURE_RESERVED_ROM')
    if raw[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a') or len(fixture)>32768:raise ValueError('PREFIX_FIXTURE_GATE')
    raw[first:first+len(fixture)]=fixture;raw[60*32768:60*32768+len(table)]=table
    raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['PrefixFixture_Gate'])[:3]+b'\xea'
    path=folder/'bor.sfc';path.write_bytes(raw)
    for media in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor-*.pcm')]:
        target=folder/media.name
        if not target.exists():os.link(media.resolve(),target)
    lua='local rows={'+','.join('{'+','.join(k+'='+str(v) for k,v in c.items())+'}' for c in rows)+'}\n'
    lua+='local sy={'+','.join(k+'='+str(v) for k,v in sy.items() if k.startswith(('SourceUpdateFrame4086_','VmSourceWorld_','SourceClock4086_','SourceWorldTick4086_','VmState_')))+'}\n'
    lua+=r'''
local mt=emu.memType.snesMemory
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for j=0,n-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n or 2)end
local function row()return rows[word(INDEX)+1]end
local function side()return 0x416800+row().slot*64 end
local function view()return 0x414000+row().slot*80 end
local function aux()return 0x41f500+row().slot*20 end
emu.addMemoryCallback(function()
 local state=emu.getState()
 emu.log('PREFIXBAD|'..word(INDEX)..'|'..state['cpu.a']..'|'..state['cpu.x']..'|'..word(sy.SourceUpdateFrame4086_Handle)..'|'..word(sy.SourceUpdateFrame4086_Count)..'|'..word(sy.SourceUpdateFrame4086_AnimationData)..'|'..word(sy.SourceUpdateFrame4086_FirstFrame)..'|'..word(sy.SourceUpdateFrame4086_TableEnd))
end,emu.callbackType.exec,sy.SourceUpdateFrame4086_Bad,sy.SourceUpdateFrame4086_Bad,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=row()
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0)
 set('SourceUpdateFrame4086_Slot',c.slot);set('SourceUpdateFrame4086_Request',c.f)
 set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',60);set('SourceUpdateFrame4086_Bytes',TABLEBYTES)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800)
 set('VmSourceWorld_Count',128);set('VmSourceWorld_Time',c.time,4);set('SourceWorldTick4086_Ready',0)
 set('SourceClock4086_Ready',0xb4c5);set('SourceClock4086_TimeLo',c.time,4);set('SourceClock4086_Due',1);set('SourceClock4086_Fault',0)
 set('VmState_Status',0,1);set('VmState_Error',0)
 put(view()+4,1,2);put(view()+16,1,4);put(view()+20,44,4)
 put(side()+4,c.handle,2);put(side()+6,99,2);put(side()+8,0x12345678,4)
 put(aux()+12,0x87654321,4);put(aux()+16,c.animating&65535,2)
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=row();local pending=word(sy.SourceUpdateFrame4086_Pending)
 emu.log('PREFIXPENDING|'..word(INDEX)..'|'..pending..'|'..dw(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceClock4086_Fault))
 set('SourceClock4086_Fault',0)
 if pending==1 then
  if c.mode==1 then put(side()+6,0,2)elseif c.mode==2 then put(side()+4,c.handle+1,2)elseif c.mode==3 then put(view()+4,0,2)end
 end
 set('VmState_Status',4,1)
end,emu.callbackType.exec,OBSERVE,OBSERVE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 emu.log('PREFIXRESULT|'..word(INDEX)..'|'..word(sy.SourceUpdateFrame4086_State)..'|'..word(sy.SourceUpdateFrame4086_Pending)..'|'..word(side()+6)..'|'..dw(side()+8)..'|'..dw(aux()+12)..'|'..word(side()+4)..'|'..word(view()+4)..'|'..dw(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Due))
end,emu.callbackType.exec,COMMITTED,COMMITTED,emu.cpuType.snes,mt)
'''
    for k,v in dict(INDEX=INDEX,TABLEBYTES=len(table),INIT=fs['PrefixFixture_Init'],
        OBSERVE=fs['PrefixFixture_Observe'],COMMITTED=fs['PrefixFixture_Committed']).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    script=folder/'prefix.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):
                return super().__enter__()
    reporter=Reporter('M4-UPDATE-FRAME-PREFIX',kind='GATE')
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        reporter.check('cold frame owner disabled',startup.u16(m,sy['SourceUpdateFrame4086_Ready'])==0)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('PREFIX_NATIVE_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(REQUEST,0xb4e4)
        for _ in range(24):
            run_frames_exact(m,60)
            if startup.u16(m,INDEX)==len(rows) or startup.u16(m,ERROR):break
        reporter.check('native prefix batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,ERROR)==0)
    results=[];pending=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        if 'PREFIXRESULT|' in line:results.append(list(map(int,line.split('PREFIXRESULT|',1)[1].split('|'))))
        if 'PREFIXPENDING|' in line:pending.append(list(map(int,line.split('PREFIXPENDING|',1)[1].split('|'))))
    mismatches=[]
    for i,c in enumerate(rows):
        no_op=c['f']>=c['count'];script=c['animating']!=0 and not no_op
        expected=[i,2,0,99 if no_op else 0 if c['mode']==1 else c['f'],
            (c['time']+c['delay'])&0xffffffff if script else 0x12345678,
            0 if script else 0x87654321,c['handle']+(c['mode']==2),int(c['mode']!=3),
            (c['time']+1)&0xffffffff,0]
        if i>=len(results) or results[i]!=expected:mismatches.append(dict(case=c,expected=expected,actual=results[i] if i<len(results) else None))
        wanted=[] if no_op else ([1] if c['mode'] in (1,2) else [1,2]) if script else [2]
        actual=[p[1] for p in pending if p[0]==i]
        if actual!=wanted:mismatches.append(dict(case=c,pending_expected=wanted,pending_actual=actual))
    reporter.check('source prefix, interruption and captured identities preserved',len(results)==len(rows) and not mismatches)
    reporter.check('every pending service blocks early clock commit',bool(pending) and all(p[2:]==[rows[p[0]]['time'],1,1] for p in pending))
    r=dict(schema='BYOR_4086_UPDATE_FRAME_PREFIX_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(raw).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),
        cases=len(rows),source_frames=836,source_animations=80,pending_services=len(pending),
        mismatches=mismatches,results=results,pending=pending,script_services_instrumented=True,effect_services_instrumented=True,
        scope='Native frame mutation, signed animating gate, delay/time wrap, pause reset, callback interruption and unfinished-frame commit rejection',
        live_callback_owner_bound=False,remaining_effects_bound=False,motu_gameplay_proven=False,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
