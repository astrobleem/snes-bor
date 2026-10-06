"""Native ent_set_model animation transitions against pinned C service boundaries."""
import argparse,hashlib,json,os,re,struct,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_model_animation_authority import IDS,COUNTS
from source_animation_init_4086 import pack
from source_frame_effects_4086 import ANIMATION_FIELDS,pack as pack_effects
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from m4_animation_init_native import luav
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

REQUEST,INDEX,ERROR=0x7ffd80,0x7ffd82,0x7ffd84


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--authority',type=Path,required=True)
    p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text())
    if authority['status']!='PASS' or authority['functions_sha256']!='b8aa5981df840a7e7a07526ed2a79ddd9d09539ec73b1e6606c42a7756821362':raise ValueError('MODEL_ANIMATION_C_AUTHORITY')
    synthetic=[dict(handle=1,numframes=8,sync=1,engine_animation_id=0,identity=1)]
    handles=[]
    for variant,counts in enumerate(COUNTS):
        group=[]
        for identity,(number,count) in enumerate(zip(IDS,counts),2):
            h=len(synthetic)+1;group.append(h);synthetic.append(dict(handle=h,numframes=count,sync=1 if variant==1 else -1,engine_animation_id=number,identity=identity))
        handles.append(group)
    rows=[]
    for i,ar in enumerate(authority['results']):
        c=ar['case'];hs=handles[c['variant']];unsafe=ar['expected']['unsafe']
        wanted=list(ar['actual']) if not unsafe else [0,1 if c['old'] else 0,c['frame'],-1,77,13,456,1,17,18,19,20,0,0]
        if wanted[1]>=2:wanted[1]=hs[wanted[1]-2]
        rows.append(dict(c,slot=(0,1,127)[i%3],handles=hs,wanted=wanted,fault=int(unsafe),bad='empty_sync' if unsafe else ''))
    base=next(r for r in rows if r['sync'] and r['mask']==15 and not r['fault'])
    for bad in ('ready','delay_policy','slot','pending','role','table','cache','ack_stale'):
        original=[0,1 if base['old'] else 0,base['frame'],-1,77,13,456,1,17,18,19,20,0,0]
        rows.append(dict(base,wanted=original,fault=1,bad=bad))
    ai=pack(dict(maximum_animations=168,animations=synthetic));effects=dict(models=[],animations=[])
    for an in synthetic:
        frames=[dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=j if an['identity']==1 else 6+2*(an['identity']-2)+j) for j in range(an['numframes'])]
        effects['animations'].append(dict(handle=an['handle'],events=dict.fromkeys(ANIMATION_FIELDS,0),frames=frames))
    fe=pack_effects(effects);sy=symbols(Path('src/main.sym'));entry=sy['Vm_SourceFrameGate'];first=39*32768;raw=bytearray(a.rom.read_bytes())
    if raw[first:first+32768]!=bytes(32768) or raw[59*32768:61*32768]!=bytes(65536) or raw[0x7fd8]!=8:raise ValueError('MODEL_ANIMATION_PRIVATE_RESERVATION')
    asm='''.snes
.bank 39
.org $8000
ModelAnimationFixture_Gate:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l REQUEST
 cmp #$B4ED
 bne ModelAnimationFixture_Return
ModelAnimationFixture_Init:
.a16
.i16
 nop
 lda.l MODE
 beq ModelAnimationFixture_Begin
 jsl ACK
 bra ModelAnimationFixture_After
ModelAnimationFixture_Begin:
.a16
.i16
 jsl APPLY
ModelAnimationFixture_After:
.a16
.i16
 nop
 bcc ModelAnimationFixture_Success
 lda.l EXPECTFAULT
 beq ModelAnimationFixture_Bad
 bra ModelAnimationFixture_Result
ModelAnimationFixture_Success:
.a16
.i16
 lda.l EXPECTFAULT
 bne ModelAnimationFixture_Bad
ModelAnimationFixture_Result:
.a16
.i16
 nop
 jsl CLOCK
ModelAnimationFixture_ClockResult:
.a16
.i16
 nop
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #CASES
 bcs ModelAnimationFixture_Done
 and #7
 bne ModelAnimationFixture_Init
 bra ModelAnimationFixture_Return
ModelAnimationFixture_Bad:
.a16
.i16
 lda #1
 sta.l ERROR
ModelAnimationFixture_Done:
.a16
.i16
 lda #0
 sta.l REQUEST
 sta.l READY
 sta.l WORLDREADY
ModelAnimationFixture_Return:
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
    values=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,APPLY=sy['SourceModelAnimation4086_Begin'],
        EXPECTFAULT=REQUEST+6,MODE=REQUEST+8,CLOCK=sy['SourceClock4086_Commit'],ACK=sy['SourceModelAnimation4086_Ack'],CASES=len(rows),READY=sy['SourceModelAnimation4086_Ready'],WORLDREADY=sy['VmSourceWorld_Ready'],RESUME=entry+5)
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm)
    pasm=folder/'fixture.pasm';pasm.write_text(asm)
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(pasm),'--output',str(folder/'fixture.bin'),'--symbols',str(folder/'fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('ANIMATION_INIT_FIXTURE_ASSEMBLY')
    fs=symbols(folder/'fixture.sym');code=(folder/'fixture.bin').read_bytes()[first:]
    if raw[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a'):raise ValueError('ANIMATION_INIT_PRIVATE_GATE')
    raw[first:first+len(code)]=code;raw[59*32768:59*32768+len(ai)]=ai;raw[60*32768:60*32768+len(fe)]=fe
    raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['ModelAnimationFixture_Gate'])[:3]+b'\xea'
    rom=folder/'bor.sfc';rom.write_bytes(raw)
    for media in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor-*.pcm')]:
        target=folder/media.name
        if not target.exists():os.link(media.resolve(),target)
    lua='local rows='+luav(rows)+'\nlocal sy='+luav({k:v for k,v in sy.items() if k.startswith(('SourceModelAnimation4086_','SourceAnimationInit4086_','SourceModelAnimationCopy4086_','SourceModelEntityCopy4086_','SourceUpdateFrame4086_','SourceClock4086_','SourceWorldTick4086_','SourceFrameStack4086_'))})+'\n'
    lua+=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local start=0;local ctx=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function set(k,v)put(sy['SourceModelAnimation4086_'..k],v)end
local ranges={{0x414000,10240},{0x416800,8192},{0x40c000,12288},{0x41f500,2560},{0x43c000,8192},{0x43e000,512}}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local v=0x414000+80*c.slot;local s=0x416800+64*c.slot;local e=0x40c000+96*c.slot;local aux=0x41f500+20*c.slot
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0xa5,mt)end end
 put(v+16,1);put(v+18,0);put(v+20,0);put(v+22,0);put(s,0);put(s+4,c.old==1 and 1 or 0);put(s+6,c.frame);put(s+8,456);put(s+10,0)
 put(e+72,c.type);put(e+74,0);put(e+80,123);put(e+82,0);put(e+84,77);put(e+86,0);put(e+88,1);put(e+90,0)
 put(aux+8,0);put(aux+10,13);put(aux+16,65535)
 for j,h in ipairs(c.handles)do put(0x43e000+4*(h-1),16+j);put(0x43e002+4*(h-1),0)end
 for i=0,167 do put(0x43c000+2*i,0)end
 local ids={0,23,104,59};for j,id in ipairs(ids)do put(0x43c000+2*id,(c.mask&(1<<(j-1)))~=0 and c.handles[j] or 0)end
 set('Ready',0xb4ef);set('State',0);set('Slot',c.slot);set('Sync',c.sync);set('TimeLo',c.time&65535);set('TimeHi',(c.time>>16)&65535)
 set('Select',c.select);set('Idle',0);set('Spawn',23);set('Respawn',104);set('SelectAnimation',59);set('DelayPolicy',1)
 put(sy.SourceAnimationInit4086_Ready,0xb4ec);put(sy.SourceAnimationInit4086_State,0);put(sy.SourceAnimationInit4086_Base,0x8000);put(sy.SourceAnimationInit4086_Bank,59);put(sy.SourceAnimationInit4086_Bytes,AIBYTES);put(sy.SourceAnimationInit4086_Issued,0)
 put(WORLDREADY,0xb4a3);put(WORLDBASE,0x4000);put(WORLDCOUNT,128)
 put(sy.SourceModelEntityCopy4086_Ready,0xb4eb)
 put(sy.SourceModelAnimationCopy4086_Ready,0xb4e9);put(sy.SourceModelAnimationCopy4086_Models,1);put(sy.SourceModelAnimationCopy4086_Maximum,168);put(sy.SourceModelAnimationCopy4086_Bytes,336)
 put(sy.SourceUpdateFrame4086_Ready,0xb4e3);put(sy.SourceUpdateFrame4086_State,0);put(sy.SourceUpdateFrame4086_Pending,0)
 put(sy.SourceUpdateFrame4086_Base,0x8000);put(sy.SourceUpdateFrame4086_Bank,60);put(sy.SourceUpdateFrame4086_Bytes,FEBYTES);put(sy.SourceUpdateFrame4086_Animations,HANDLES)
 put(sy.SourceFrameStack4086_Ready,0);put(sy.SourceWorldTick4086_Ready,0)
 put(sy.SourceClock4086_Ready,0xb4c5);put(sy.SourceClock4086_Due,1);put(sy.SourceClock4086_TimeLo,48);put(sy.SourceClock4086_TimeHi,0);put(sy.SourceClock4086_Fault,0)
 put(EXPECTFAULT,c.fault);put(MODE,0)
 if c.bad=='ready'then set('Ready',0)
 elseif c.bad=='delay_policy'then set('DelayPolicy',0)
 elseif c.bad=='slot'then set('Slot',128)
 elseif c.bad=='pending'then set('State',1)
 elseif c.bad=='role'then set('Sync',0);set('Idle',168)
 elseif c.bad=='table'then put(sy.SourceAnimationInit4086_Bytes,AIBYTES-2)
 elseif c.bad=='cache'then put(sy.SourceModelAnimationCopy4086_Bytes,338)
 elseif c.bad=='ack_stale'then set('State',1);put(MODE,1);put(sy.SourceAnimationInit4086_State,1)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
local function capture()
 local state=emu.getState();start=state.masterClock;ctx=0;cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=state['cpu.'..k]end
end
emu.addMemoryCallback(capture,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(capture,emu.callbackType.exec,ACK,ACK,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp'] or (cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('MODELTRANSITIONCOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local w=c.wanted;local v=0x414000+80*c.slot;local s=0x416800+64*c.slot;local e=0x40c000+96*c.slot;local aux=0x41f500+20*c.slot
 local function expect(a,n)before[a]=n&255;before[a+1]=(n>>8)&255 end
 if c.fault==0 then
  expect(v+20,w[1]);expect(s+4,w[2]);expect(s+6,w[3]);expect(aux+16,w[4]);expect(e+84,w[5]);expect(aux+10,w[6]);expect(s+8,w[7]&65535);expect(s+10,(w[7]>>16)&65535);expect(e+88,w[8])
  for j,h in ipairs(c.handles)do expect(0x43e000+4*(h-1),w[8+j])end
 end
 local mismatch=0;for addr,value in pairs(before)do if emu.read(addr,mt)~=value then mismatch=mismatch+1 end end
 emu.log('MODELTRANSITIONRESULT|'..word(INDEX)..'|'..word(sy.SourceModelAnimation4086_State)..'|'..mismatch..'|'..ctx)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('MODELTRANSITIONCLOCK|'..word(INDEX)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault))end,emu.callbackType.exec,CLOCKRESULT,CLOCKRESULT,emu.cpuType.snes,mt)
'''
    values=dict(INDEX=INDEX,MODE=REQUEST+8,EXPECTFAULT=REQUEST+6,APPLY=sy['SourceModelAnimation4086_Begin'],ACK=sy['SourceModelAnimation4086_Ack'],INIT=fs['ModelAnimationFixture_Init'],AFTER=fs['ModelAnimationFixture_After'],RESULT=fs['ModelAnimationFixture_Result'],CLOCKRESULT=fs['ModelAnimationFixture_ClockResult'],AIBYTES=len(ai),FEBYTES=len(fe),HANDLES=len(synthetic),WORLDREADY=sy['VmSourceWorld_Ready'],WORLDBASE=sy['VmSourceWorld_PoolBase'],WORLDCOUNT=sy['VmSourceWorld_Count'])
    for k,v in values.items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    script=folder/'observer.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    reporter=Reporter('M4-MODEL-ANIMATION',kind='GATE')
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        reporter.check('cold model animation owner disabled',startup.u16(m,sy['SourceModelAnimation4086_Ready'])==0)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('MODEL_ANIMATION_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(INDEX,0);m.write_u16(ERROR,0);m.write_u16(REQUEST,0xb4ed)
        for _ in range(2500):
            run_frames_exact(m,1)
            if startup.u16(m,INDEX)==len(rows) or startup.u16(m,ERROR):break
        reporter.check('native model transition batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,ERROR)==0)
    results=[];costs=[];clocks=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        for marker,target in [('MODELTRANSITIONRESULT|',results),('MODELTRANSITIONCOST|',costs),('MODELTRANSITIONCLOCK|',clocks)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    reporter.check('C-derived transitions preserve every unrelated entity/cache byte and CPU context',len(results)==len(rows) and all(r==[i,3 if c['fault'] else 1 if c['wanted'][-2] else 2,0,0] for i,(r,c) in enumerate(zip(results,rows))))
    reporter.check('direct clock cannot retire pending/faulty model transition',len(clocks)==len(rows) and all(r==[i,1,48,1] if c['wanted'][-2] or c['fault'] and c['bad']!='ready' else r==[i,0,49,0] for i,(r,c) in enumerate(zip(clocks,rows))))
    report=dict(schema='BYOR_4086_MODEL_ANIMATION_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),authority_report_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),cases=len(rows),source_undefined_rejections=sum(r['bad']=='empty_sync' for r in rows),results=results,cpu_costs=costs,clock_results=clocks,
        frame_zero_service_instrumented=True,full_model_switch_bound=False,frame_zero_effects_bound=False,source_default_edelay_required=True,live_presentation_contention_proven=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
