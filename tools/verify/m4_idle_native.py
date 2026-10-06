"""DEFAULT_IDLE_ONLY native leaf against pinned C; nested initializer separate."""
import argparse, hashlib, itertools, json, os, re, struct, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_animation_init_4086 import pack
from source_frame_effects_4086 import ANIMATION_FIELDS, pack as pack_effects
from source_idle_4086 import default_idle_capability
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_animation_init_native import luav
from _harness import McpSession, MESEN_EXE, _free_tcp_port, Reporter, run_frames_exact, exact_input_edge
import game_bor_startup_select as startup

REQUEST, INDEX, ERROR = 0x7ffd80, 0x7ffd82, 0x7ffd84


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--authority',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text())
    if authority['status']!='PASS' or authority['functions_sha256']!='caab8b9618e615c01d0f7d528b96d6c5496c36a88dc822b21f7fd4064677a0bc':raise ValueError('IDLE_C_AUTHORITY')
    cap=default_idle_capability(json.loads(Path('out/byor-motu-animation-identities.json').read_text()),json.loads(Path('out/byor-motu-model-core-inputs.json').read_text()))
    rows=[]
    for type_,mode,handle,slot in itertools.product((0,1,2,65536),(0,1),(0,1,2),(0,1,127)):
        ar=next(r for r in authority['results'] if not r['direct'] and r['case']==dict(type=type_,subtype=0,idling=-2,mask=4 if handle==1 else 0,health=26,time=48,force=mode,target=0))
        rows.append(dict(type=type_,mode=mode,handle=handle,slot=slot,wanted=ar['actual'],fault=0,bad=''))
    for bad in ('ready','world','pool','side','core','entities','slot','models','model','mode_high','mode_low','init','pending'):
        rows.append(dict(rows[0],fault=1,bad=bad))
    ai=pack(dict(maximum_animations=4,animations=[dict(handle=1,numframes=1,sync=-1,engine_animation_id=0),dict(handle=2,numframes=0,sync=-1,engine_animation_id=0)]))
    fe=pack_effects(dict(models=[],animations=[dict(handle=1,events=dict.fromkeys(ANIMATION_FIELDS,0),frames=[dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=6)]),dict(handle=2,events=dict.fromkeys(ANIMATION_FIELDS,0),frames=[])]))
    sy=symbols(Path('src/main.sym'));entry=sy['Vm_SourceFrameGate'];first=39*32768;raw=bytearray(a.rom.read_bytes())
    if raw[first:first+32768]!=bytes(32768) or raw[59*32768:61*32768]!=bytes(65536) or raw[0x7fd8]!=8:raise ValueError('IDLE_PRIVATE_RESERVATION')
    asm='''.snes
.bank 39
.org $8000
IdleFixture_Gate:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l REQUEST
 cmp #$B4F3
 bne IdleFixture_Return
IdleFixture_Init:
.a16
.i16
 nop
 jsl APPLY
IdleFixture_After:
.a16
.i16
 nop
 bcc IdleFixture_Success
 lda.l EXPECTFAULT
 beq IdleFixture_Bad
 bra IdleFixture_Result
IdleFixture_Success:
.a16
.i16
 lda.l EXPECTFAULT
 bne IdleFixture_Bad
IdleFixture_Result:
.a16
.i16
 nop
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #CASES
 bcs IdleFixture_Done
 and #7
 bne IdleFixture_Init
 bra IdleFixture_Return
IdleFixture_Bad:
.a16
.i16
 lda #1
 sta.l ERROR
IdleFixture_Done:
.a16
.i16
 lda #0
 sta.l REQUEST
 sta.l READY
 sta.l WORLDREADY
IdleFixture_Return:
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
    values=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,EXPECTFAULT=REQUEST+6,READY=sy['SourceIdle4086_Ready'],WORLDREADY=sy['VmSourceWorld_Ready'],APPLY=sy['SourceIdle4086_Prepare'],CASES=len(rows),RESUME=entry+5)
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm)
    pasm=folder/'fixture.pasm';pasm.write_text(asm)
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(pasm),'--output',str(folder/'fixture.bin'),'--symbols',str(folder/'fixture.sym')],capture_output=True,text=True);(folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('IDLE_FIXTURE_ASSEMBLY')
    fs=symbols(folder/'fixture.sym');code=(folder/'fixture.bin').read_bytes()[first:];raw[first:first+len(code)]=code;raw[59*32768:59*32768+len(ai)]=ai;raw[60*32768:60*32768+len(fe)]=fe
    if raw[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a'):raise ValueError('IDLE_GATE')
    raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['IdleFixture_Gate'])[:3]+b'\xea'
    rom=folder/'bor.sfc';rom.write_bytes(raw)
    for media in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor-*.pcm')]:
        target=folder/media.name
        if not target.exists():os.link(media.resolve(),target)
    lua='local rows='+luav(rows)+'\nlocal sy='+luav({k:v for k,v in sy.items() if k.startswith(('SourceIdle4086_','SourceAnimationInit4086_','SourceModelAnimationCopy4086_','SourceModelEntityCopy4086_','SourceUpdateFrame4086_','VmSourceWorld_'))})+'\n'
    lua+=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local ctx=0;local start=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function long(a,v)put(a,v&65535);put(a+2,(v>>16)&65535)end
local function set(prefix,k,v)put(sy[prefix..k],v)end
local ranges={{0x414000,10240},{0x416800,8192},{0x40b000,2560},{0x40c000,12288},{0x41f500,2560},{0x43c000,8192},{0x43e000,512},{0x43eb00,4096}}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local v=0x414000+80*c.slot;local s=0x416800+64*c.slot;local e=0x40c000+96*c.slot;local f=0x43eb00+32*c.slot
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0xa5,mt)end end
 put(v+16,1);put(v+18,0);long(v+20,99);put(s,0);put(s+4,0);put(s+6,3);long(s+36,81920);long(s+40,-163840)
 long(0x40b09c,c.type);long(e+72,c.type==0 and 1 or 0);long(e+88,7)
 long(f,-2);long(f+4,-1);long(f+8,3);long(f+12,2);long(f+16,17);long(f+20,c.mode);long(f+24,48);long(f+28,123)
 put(0x43c000,c.handle);put(0x43c002,0);put(0x43c004,0);put(0x43c006,0)
 set('SourceIdle4086_','Ready',0xb4f3);set('SourceIdle4086_','Slot',c.slot)
 set('SourceAnimationInit4086_','Ready',0xb4ec);set('SourceAnimationInit4086_','State',0);set('SourceAnimationInit4086_','Base',0x8000);set('SourceAnimationInit4086_','Bank',59);set('SourceAnimationInit4086_','Bytes',AIBYTES)
 set('SourceModelAnimationCopy4086_','Ready',0xb4e9);set('SourceModelAnimationCopy4086_','Models',1);set('SourceModelAnimationCopy4086_','Maximum',4);set('SourceModelAnimationCopy4086_','Bytes',8)
 set('SourceModelEntityCopy4086_','Ready',0xb4eb);set('SourceModelEntityCopy4086_','Entities',128);set('SourceModelEntityCopy4086_','Models',1)
 set('SourceUpdateFrame4086_','Ready',0xb4e3);set('SourceUpdateFrame4086_','Base',0x8000);set('SourceUpdateFrame4086_','Bank',60);set('SourceUpdateFrame4086_','Bytes',FEBYTES);set('SourceUpdateFrame4086_','Animations',2)
 set('VmSourceWorld_','Ready',0xb4a3);set('VmSourceWorld_','PoolBase',0x4000);set('VmSourceWorld_','SideBase',0x6800);set('VmSourceWorld_','Count',128)
 put(EXPECTFAULT,c.fault)
 if c.bad=='ready'then set('SourceIdle4086_','Ready',0)
 elseif c.bad=='world'then set('VmSourceWorld_','Ready',0)
 elseif c.bad=='pool'then set('VmSourceWorld_','PoolBase',0x4002)
 elseif c.bad=='side'then set('VmSourceWorld_','SideBase',0x6802)
 elseif c.bad=='core'then set('SourceModelEntityCopy4086_','Ready',0)
 elseif c.bad=='entities'then set('SourceModelEntityCopy4086_','Entities',127)
 elseif c.bad=='slot'then set('SourceIdle4086_','Slot',128)
 elseif c.bad=='models'then set('SourceModelEntityCopy4086_','Models',17)
 elseif c.bad=='model'then put(s,1)
 elseif c.bad=='mode_high'then long(f+20,65536)
 elseif c.bad=='mode_low'then long(f+20,2)
 elseif c.bad=='init'then set('SourceAnimationInit4086_','Ready',0)
 elseif c.bad=='pending'then set('SourceAnimationInit4086_','State',1)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();start=s.masterClock;ctx=0;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp'] or (cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('IDLECOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local w=c.wanted;local s=0x416800+64*c.slot;local e=0x40c000+96*c.slot;local f=0x43eb00+32*c.slot
 local function expectlong(a,n)for i=0,3 do before[a+i]=(n>>(8*i))&255 end end
 local admission=0
 if c.fault==0 then
  expectlong(f,w[2]);expectlong(e+88,w[3]);expectlong(f+4,w[4]);expectlong(f+8,w[5]);expectlong(f+12,w[6]);expectlong(s+36,w[7]*16384);expectlong(s+40,w[8]*16384)
  if word(sy.SourceAnimationInit4086_Number)~=0 or word(sy.SourceAnimationInit4086_Reset)~=0 or word(sy.SourceAnimationInit4086_Slot)~=c.slot or word(sy.SourceAnimationInit4086_Handle)~=c.handle or word(sy.SourceAnimationInit4086_Count)~=(c.handle==1 and 1 or 0)then admission=1 end
 end
 local mismatch=0;for addr,value in pairs(before)do if emu.read(addr,mt)~=value then mismatch=mismatch+1 end end
 emu.log('IDLERESULT|'..word(INDEX)..'|'..word(sy.SourceIdle4086_Status)..'|'..mismatch..'|'..ctx..'|'..admission)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    values.update(INIT=fs['IdleFixture_Init'],AFTER=fs['IdleFixture_After'],RESULT=fs['IdleFixture_Result'],AIBYTES=len(ai),FEBYTES=len(fe))
    for k,v in values.items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    script=folder/'observer.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    reporter=Reporter('M4-IDLE',kind='GATE')
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('IDLE_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(INDEX,0);m.write_u16(ERROR,0);m.write_u16(REQUEST,0xb4f3)
        for _ in range(1000):
            run_frames_exact(m,1)
            if startup.u16(m,INDEX)==len(rows) or startup.u16(m,ERROR):break
        reporter.check('native idle batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,ERROR)==0)
        print('idle fixture completion:',startup.u16(m,INDEX),'/',len(rows),'request',hex(startup.u16(m,REQUEST)),'error',startup.u16(m,ERROR))
    results=[];costs=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        for marker,target in [('IDLERESULT|',results),('IDLECOST|',costs)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    reporter.check('C-derived flags and cached-type movement preserve unrelated bytes/context',len(results)==len(rows) and all(r==[i,2 if c['fault'] else 1,0,0,0] for i,(r,c) in enumerate(zip(results,rows))))
    report=dict(schema='BYOR_4086_DEFAULT_IDLE_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),results=results,cpu_costs=costs,authority_report_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),capability=cap,nested_animation_initializer_execution_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
