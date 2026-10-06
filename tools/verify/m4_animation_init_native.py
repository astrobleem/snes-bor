"""Native ent_set_anim service-boundary proof against verbatim pinned C."""
import argparse,hashlib,json,os,re,struct,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_animation_init_4086 import derive,pack
from source_frame_effects_4086 import ANIMATION_FIELDS,pack as pack_effects
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

REQUEST,INDEX,ERROR=0x7ffb80,0x7ffb82,0x7ffb84


def luav(v):
    if isinstance(v,str):return json.dumps(v)
    if isinstance(v,list):return '{'+','.join(luav(x) for x in v)+'}'
    if isinstance(v,dict):return '{'+','.join(k+'='+luav(x) for k,x in v.items())+'}'
    return str(v)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--authority',type=Path,required=True)
    p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text())
    if authority['status']!='PASS' or authority['initialization_function_sha256']!='30132883eeb233e8caef25a4bafce45128b35778e5c93edcbe74bc7e02127828':raise ValueError('ANIMATION_INIT_PINNED_C_AUTHORITY')
    authored=derive(Source(a.source));authored_data=pack(authored);(folder/'authored.b4ai').write_bytes(authored_data)
    synthetic=[];lookup={};rows=[]
    def handle(identity,count,sync):
        key=(identity,count,sync)
        if key not in lookup:
            h=len(synthetic)+1;lookup[key]=h
            synthetic.append(dict(handle=h,numframes=count,sync=sync,engine_animation_id=identity))
        return lookup[key]
    for i,r in enumerate(authority['results']):
        c=r['case'];old0=handle(0,4,c['oldsync']);new=handle(1,c['count'],c['newSync']);empty=handle(3,0,1)
        old=0 if c['old']<0 else old0 if c['old']==0 else new
        wanted=list(r['actual']);wanted[1]=0 if wanted[1]<0 else old0 if wanted[1]==0 else new
        rows.append(dict(slot=(0,1,127)[i%3],old=old,old0=old0,new=new,empty=empty,target=c['target']&65535,
            reset=c['reset']&65535,frame=c['frame'],wanted=wanted,fault=0,bad=''))
    for bad in ('ready','world','base','count','slot','cache_ready','cache_size','models','maximum','table_bank','table_size','table_magic','handle','old_handle','tag','reserved','pending','ack_stale'):
        rows.append(dict(rows[0],target=1,reset=1,fault=1,bad=bad))
    ai=pack(dict(maximum_animations=4,animations=synthetic))
    effects=dict(models=[],animations=[],media=[])
    for an in synthetic:
        effects['animations'].append(dict(handle=an['handle'],events=dict.fromkeys(ANIMATION_FIELDS,0),
            frames=[dict(move=dict(base=-1,x=0,y=0,z=0),sound=None,delay_ticks=6) for _ in range(an['numframes'])]))
    fe=pack_effects(effects)
    sy=symbols(Path('src/main.sym'));entry=sy['Vm_SourceFrameGate'];raw=bytearray(a.rom.read_bytes());first=39*32768
    if raw[first:first+32768]!=bytes(32768) or raw[59*32768:61*32768]!=bytes(65536) or raw[0x7fd8]!=8:raise ValueError('ANIMATION_INIT_PRIVATE_RESERVATION')
    asm='''.snes
.bank 39
.org $8000
AnimationInitFixture_Gate:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l REQUEST
 cmp #$B4ED
 bne AnimationInitFixture_Return
AnimationInitFixture_Init:
.a16
.i16
 nop
 lda.l MODE
 beq AnimationInitFixture_Begin
 jsl ACK
 bra AnimationInitFixture_After
AnimationInitFixture_Begin:
.a16
.i16
 jsl APPLY
AnimationInitFixture_After:
.a16
.i16
 nop
 bcc AnimationInitFixture_Success
 lda.l EXPECTFAULT
 beq AnimationInitFixture_Bad
 bra AnimationInitFixture_Result
AnimationInitFixture_Success:
.a16
.i16
 lda.l EXPECTFAULT
 bne AnimationInitFixture_Bad
AnimationInitFixture_Result:
.a16
.i16
 nop
 jsl CLOCK
AnimationInitFixture_ClockResult:
.a16
.i16
 nop
 lda.l INDEX
 inc a
 sta.l INDEX
 cmp #CASES
 bcs AnimationInitFixture_Done
 and #7
 bne AnimationInitFixture_Init
 bra AnimationInitFixture_Return
AnimationInitFixture_Bad:
.a16
.i16
 lda #1
 sta.l ERROR
AnimationInitFixture_Done:
.a16
.i16
 lda #0
 sta.l REQUEST
 sta.l READY
 sta.l WORLDREADY
AnimationInitFixture_Return:
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
    values=dict(REQUEST=REQUEST,INDEX=INDEX,ERROR=ERROR,APPLY=sy['SourceAnimationInit4086_Begin'],
        EXPECTFAULT=REQUEST+6,MODE=REQUEST+8,CLOCK=sy['SourceClock4086_Commit'],ACK=sy['SourceAnimationInit4086_Ack'],CASES=len(rows),READY=sy['SourceAnimationInit4086_Ready'],WORLDREADY=sy['VmSourceWorld_Ready'],RESUME=entry+5)
    for k,v in values.items():asm=re.sub(r'\b'+k+r'\b',str(v),asm)
    pasm=folder/'fixture.pasm';pasm.write_text(asm)
    proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(pasm),'--output',str(folder/'fixture.bin'),'--symbols',str(folder/'fixture.sym')],capture_output=True,text=True)
    (folder/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('ANIMATION_INIT_FIXTURE_ASSEMBLY')
    fs=symbols(folder/'fixture.sym');code=(folder/'fixture.bin').read_bytes()[first:]
    if raw[offset(entry):offset(entry)+5]!=bytes.fromhex('08 c2 31 da 5a'):raise ValueError('ANIMATION_INIT_PRIVATE_GATE')
    raw[first:first+len(code)]=code;raw[59*32768:59*32768+len(ai)]=ai;raw[60*32768:60*32768+len(fe)]=fe
    raw[offset(entry):offset(entry)+5]=b'\x5c'+struct.pack('<I',fs['AnimationInitFixture_Gate'])[:3]+b'\xea'
    rom=folder/'bor.sfc';rom.write_bytes(raw)
    for media in [a.rom.with_suffix('.msu'),*a.rom.parent.glob('bor-*.pcm')]:
        target=folder/media.name
        if not target.exists():os.link(media.resolve(),target)
    lua='local rows='+luav(rows)+'\nlocal sy='+luav({k:v for k,v in sy.items() if k.startswith(('SourceAnimationInit4086_','SourceModelAnimationCopy4086_','SourceModelEntityCopy4086_','SourceUpdateFrame4086_','SourceClock4086_','SourceWorldTick4086_','VmSourceWorld_'))})+'\n'
    lua+=r'''
local mt=emu.memType.snesMemory;local before={};local cpu={};local start=0;local context_faults=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v)emu.write(a,v&255,mt);emu.write(a+1,(v>>8)&255,mt)end
local function set(k,v)put(sy['SourceAnimationInit4086_'..k],v)end
local ranges={{0x414000,10240},{0x416800,8192},{0x40c000,12288},{0x41f500,2560},{0x43c000,8192},{0x43e000,512}}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local v=0x414000+80*c.slot;local s=0x416800+64*c.slot;local e=0x40c000+96*c.slot;local aux=0x41f500+20*c.slot
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0xa5,mt)end end
 put(v+16,1);put(v+18,0);put(v+20,99);put(v+22,0)
 put(s,0);put(s+4,c.old);put(s+6,c.frame);put(s+8,456);put(s+10,0)
 put(e+80,123);put(e+82,0);put(e+84,77);put(e+86,0)
 put(aux+8,0);put(aux+10,13);put(aux+16,65535)
 put(0x43e000+4*(c.old0-1),17);put(0x43e002+4*(c.old0-1),0)
 put(0x43e000+4*(c.new-1),18);put(0x43e002+4*(c.new-1),0)
 put(0x43c000,c.old0);put(0x43c002,c.new);put(0x43c004,0);put(0x43c006,c.empty)
 set('Ready',0xb4ec);set('State',0);set('Slot',c.slot);set('Number',c.target);set('Reset',c.reset)
 set('Base',0x8000);set('Bank',59);set('Bytes',AIBYTES);set('Issued',0)
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_Count,128)
 put(sy.SourceModelEntityCopy4086_Ready,0xb4eb)
 put(sy.SourceModelAnimationCopy4086_Ready,0xb4e9);put(sy.SourceModelAnimationCopy4086_Models,1);put(sy.SourceModelAnimationCopy4086_Maximum,4);put(sy.SourceModelAnimationCopy4086_Bytes,8)
 put(sy.SourceUpdateFrame4086_Ready,0xb4e3);put(sy.SourceUpdateFrame4086_Base,0x8000);put(sy.SourceUpdateFrame4086_Bank,60);put(sy.SourceUpdateFrame4086_Bytes,FEBYTES);put(sy.SourceUpdateFrame4086_Animations,HANDLES)
 put(sy.SourceUpdateFrame4086_State,0);put(sy.SourceUpdateFrame4086_Pending,0)
 put(sy.SourceClock4086_Ready,0xb4c5);put(sy.SourceClock4086_Due,1);put(sy.SourceClock4086_TimeLo,48);put(sy.SourceClock4086_TimeHi,0);put(sy.SourceClock4086_Fault,0);put(sy.SourceWorldTick4086_Ready,0)
 put(EXPECTFAULT,c.fault);put(MODE,0)
 if c.bad=='ready'then set('Ready',0)
 elseif c.bad=='world'then put(sy.VmSourceWorld_Ready,0)
 elseif c.bad=='base'then put(sy.VmSourceWorld_PoolBase,0x4002)
 elseif c.bad=='count'then put(sy.VmSourceWorld_Count,129)
 elseif c.bad=='slot'then set('Slot',128)
 elseif c.bad=='cache_ready'then put(sy.SourceModelAnimationCopy4086_Ready,0)
 elseif c.bad=='cache_size'then put(sy.SourceModelAnimationCopy4086_Bytes,10)
 elseif c.bad=='models'then put(sy.SourceModelAnimationCopy4086_Models,129)
 elseif c.bad=='maximum'then put(sy.SourceModelAnimationCopy4086_Maximum,0)
 elseif c.bad=='table_bank'then set('Bank',64)
 elseif c.bad=='table_size'then set('Bytes',AIBYTES-2)
 elseif c.bad=='table_magic'then set('Base',0x8002)
 elseif c.bad=='handle'then put(0x43c002,HANDLES+1)
 elseif c.bad=='old_handle'then put(s+4,HANDLES+1)
 elseif c.bad=='tag'then put(v+16,2)
 elseif c.bad=='reserved'then put(v+18,1)
 elseif c.bad=='pending'then set('State',1)
 elseif c.bad=='ack_stale'then
  set('State',1);put(MODE,1);put(sy.SourceUpdateFrame4086_State,2);put(sy.SourceUpdateFrame4086_Slot,c.slot);put(sy.SourceUpdateFrame4086_Request,0)
 end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
local function capture()
 local state=emu.getState();start=state.masterClock;context_faults=0;cpu={}
 for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=state['cpu.'..k]end
end
emu.addMemoryCallback(capture,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(capture,emu.callbackType.exec,ACK,ACK,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local state=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=state['cpu.'..k]then context_faults=context_faults+1 end end
 if cpu.sp+3~=state['cpu.sp'] or (cpu.ps&254)~=(state['cpu.ps']&254)then context_faults=context_faults+1 end
 emu.log('ANIMINITCOST|'..word(INDEX)..'|'..(state.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local w=c.wanted;local v=0x414000+80*c.slot;local s=0x416800+64*c.slot;local e=0x40c000+96*c.slot;local aux=0x41f500+20*c.slot
 local function expect(a,n)before[a]=n&255;before[a+1]=(n>>8)&255 end
 if c.fault==0 then
  expect(v+20,w[1]);expect(s+4,w[2]);expect(s+6,w[3]);expect(aux+16,w[4]);expect(e+84,w[5]);expect(aux+10,w[6]);expect(s+8,w[7])
  expect(0x43e000+4*(c.old0-1),w[8]);expect(0x43e000+4*(c.new-1),w[9])
 end
 local mismatch=0;for addr,value in pairs(before)do if emu.read(addr,mt)~=value then mismatch=mismatch+1 end end
 emu.log('ANIMINITRESULT|'..word(INDEX)..'|'..word(sy.SourceAnimationInit4086_State)..'|'..mismatch..'|'..context_faults)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 emu.log('ANIMINITCLOCK|'..word(INDEX)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault))
end,emu.callbackType.exec,CLOCKRESULT,CLOCKRESULT,emu.cpuType.snes,mt)
'''
    for k,v in dict(INDEX=INDEX,MODE=REQUEST+8,ACK=sy['SourceAnimationInit4086_Ack'],CLOCKRESULT=fs['AnimationInitFixture_ClockResult'],EXPECTFAULT=REQUEST+6,INIT=fs['AnimationInitFixture_Init'],APPLY=sy['SourceAnimationInit4086_Begin'],AFTER=fs['AnimationInitFixture_After'],RESULT=fs['AnimationInitFixture_Result'],AIBYTES=len(ai),FEBYTES=len(fe),HANDLES=len(synthetic)).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    script=folder/'observer.lua';script.write_text(lua)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(script)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    reporter=Reporter('M4-ANIMATION-INIT',kind='GATE')
    with Observed(rom=rom,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        with patch.object(m,'reset_emulator',return_value=None):startup.cold_to_title(m,reporter)
        reporter.check('cold animation initialization disabled',startup.u16(m,sy['SourceAnimationInit4086_Ready'])==0)
        startup.title_to_charselect(m);exact_input_edge(m,m.BTN_START,1,port=0)
        if not startup.wait_state(m,startup.PLAYING,300):raise ValueError('ANIMATION_INIT_BOOTSTRAP')
        run_frames_exact(m,12);m.write_u16(INDEX,0);m.write_u16(ERROR,0);m.write_u16(REQUEST,0xb4ed)
        for _ in range(1500):
            run_frames_exact(m,1)
            if startup.u16(m,INDEX)==len(rows) or startup.u16(m,ERROR):break
        reporter.check('native initialization batch completed',startup.u16(m,INDEX)==len(rows) and startup.u16(m,ERROR)==0)
    results=[];costs=[];clocks=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        for marker,target in [('ANIMINITRESULT|',results),('ANIMINITCOST|',costs),('ANIMINITCLOCK|',clocks)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    reporter.check('C-derived initialization preserves all unrelated entity/cache bytes and CPU context',len(results)==len(rows) and all(r==[i,3 if c['fault'] else 1 if c['wanted'][-1] else 2,0,0] for i,(r,c) in enumerate(zip(results,rows))))
    reporter.check('direct clock commit cannot retire pending or faulty initialization',len(clocks)==len(rows) and all(r==[i,1,48,1] if c['wanted'][-1] or c['fault'] and c['bad']!='ready' else r==[i,0,49,0] for i,(r,c) in enumerate(zip(clocks,rows))))
    report=dict(schema='BYOR_4086_ANIMATION_INIT_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),authority_report_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),
        authored_table_sha256=hashlib.sha256(authored_data).hexdigest(),authored_animations=len(authored['animations']),cases=len(rows),results=results,cpu_costs=costs,clock_results=clocks,
        frame_zero_service_instrumented=True,frame_zero_effects_bound=False,nested_owner_bound=False,live_presentation_contention_proven=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
