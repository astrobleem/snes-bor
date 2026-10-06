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
from source_frame_effects_4086 import derive,pack,unpack,loader_frames
from compiler import Source
from actor_s5_entity_fixture import symbols
from m4_input_controller_native import offset
from _harness import McpSession,MESEN_EXE,_free_tcp_port,Reporter,run_frames_exact,exact_input_edge
import game_bor_startup_select as startup

REQUEST,INDEX,ERROR=0x7ffb80,0x7ffb82,0x7ffb84


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--motion',action='store_true',help='Execute the native movement/base/facing effect prefix; other effects remain instrumented.')
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    report=derive(Source(a.source));sy=symbols(Path('src/main.sym'))
    rows=[]
    for an in report['animations']:
        for f in an['frames']:
            for animating in (-1,0,1):
                rows.append(dict(handle=an['handle'],f=f['index'],count=len(an['frames']),delay=f['delay_ticks'],
                    animating=animating,mode=0,slot=(0,1,127)[len(rows)%3],time=0xffffffff if len(rows)%17==0 else 48))
    sample=next(c for c in rows if c['count']>2 and c['f']==1 and c['animating']==1)
    rows += [dict(sample,mode=mode) for mode in (1,2,3)]
    rows += [dict(sample,f=sample['count'],mode=0),dict(sample,f=sample['count']+1,mode=0)]
    for i,c in enumerate(rows):
        c.update(direction=(0,1,-1)[i%3],level=(i//3)%2,base=(-2,0,3.5)[(i//6)%3])
    authority_cases={}
    if a.motion:
        authority=json.loads(Path('out/byor-motu-update-frame-authority/report.json').read_text())
        if authority['status']!='PASS' or authority['functions_sha256']!='72d75ee216c7c00ceb01f6f811b77184dda3a8f22f0174b7f0be6e35205183d7':
            raise ValueError('MOTION_PINNED_C_AUTHORITY_REQUIRED')
        synthetic_handles={}
        for firstbase in (-1,0,7):
            handle=len(report['animations'])+1;synthetic_handles[firstbase]=handle
            events=loader_frames([dict(directive='anim',values=['idle'],line=1)])[0]['events'];events['flipframe']=1
            report['animations'].append(dict(handle=handle,events=events,frames=[
                dict(index=0,move=dict(base=firstbase,x=3,y=2,z=-1),sound=None,delay_ticks=6),
                dict(index=1,move=dict(base=22,x=5,y=0,z=4),sound=None,delay_ticks=8)]))
        for ar in authority['results']:
            c=ar['case']
            if c['mode'] or c['f']>=2 or c['jumping'] or c['success'] or c['subdamage']:continue
            i=len(rows);authority_cases[i]=ar['actual']['state']
            rows.append(dict(handle=synthetic_handles[c['base']],f=c['f'],count=2,delay=6 if not c['f'] else 8,
                animating=c['animating'],mode=0,slot=(0,1,127)[i%3],time=c['time'],direction=c['direction'],
                level=c['level'],base=-2,mx=10,mz=20,alt=3))
        bad_handle=len(report['animations'])+1
        report['animations'].append(dict(handle=bad_handle,events=events,frames=[
            dict(index=0,move=dict(base=-1,x=65536,y=0,z=0),sound=None,delay_ticks=6),
            dict(index=1,move=dict(base=-1,x=-32768,y=0,z=0),sound=None,delay_ticks=6)]))
        basecase=dict(handle=synthetic_handles[-1],f=0,count=2,delay=6,animating=0,mode=0,slot=127,
            time=48,direction=1,level=1,base=-2,mx=10,mz=20,alt=3,fault=1)
        rows.extend([dict(basecase,mx=32767.5),dict(basecase,mz=-32768),dict(basecase,base=32767.5),
            dict(basecase,alt=32767.5),dict(basecase,handle=bad_handle),
            dict(basecase,handle=bad_handle,f=1,direction=0),dict(basecase,reapply=1)])
    table=pack(report);unpack(table)
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
    if a.motion:
        asm=asm.replace(' lda.l PENDING\n jsl ACK',''' lda.l PENDING
 cmp #2
 bne PrefixFixture_MotionSkip
 jsl MOTION
PrefixFixture_MotionReturned:
.a16
.i16
 bcs PrefixFixture_MotionCarry
 lda.l REPEAT
 beq PrefixFixture_MotionNoRepeat
 jsl MOTION
PrefixFixture_MotionRepeated:
.a16
.i16
 bcs PrefixFixture_MotionCarry
 jmp PrefixFixture_Bad
PrefixFixture_MotionNoRepeat:
.a16
.i16
 lda.l EXPECTEDFAULT
 bne PrefixFixture_Bad
PrefixFixture_MotionSkip:
.a16
.i16
 lda.l PENDING
 jsl ACK''')
        asm=asm.replace('PrefixFixture_Result:\n',''' jmp PrefixFixture_Result
PrefixFixture_MotionCarry:
.a16
.i16
 lda.l EXPECTEDFAULT
 beq PrefixFixture_Bad
 jsl CHECKIDLE
 bcc PrefixFixture_Bad
 jsl CLOCKCOMMIT
 bcc PrefixFixture_Bad
 jmp PrefixFixture_Committed
PrefixFixture_Result:
''')
        replacements['MOTION']=sy['SourceFrameMotion4086_Apply']
        replacements.update(EXPECTEDFAULT=REQUEST+6,REPEAT=REQUEST+8)
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
    lua+='local sy={'+','.join(k+'='+str(v) for k,v in sy.items() if k.startswith(('SourceUpdateFrame4086_','SourceFrameMotion4086_','VmSourceWorld_','SourceClock4086_','SourceWorldTick4086_','VmState_')))+'}\n'
    lua+=r'''
local mt=emu.memType.snesMemory
local motion_cpu={};local motion_start=0;local motion_faults=0
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
 motion_faults=0
 local neighbor=(c.slot+1)%128
 for i=0,19 do emu.write(0x41f500+neighbor*20+i,0xa5,mt)end
 for i=0,63 do emu.write(0x416800+neighbor*64+i,0x5a,mt)end
 for i=0,79 do emu.write(0x414000+neighbor*80+i,0xc3,mt)end
 put(EXPECTEDFAULT,c.fault or 0,2);put(REPEAT,c.reapply or 0,2)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0)
 set('SourceUpdateFrame4086_Slot',c.slot);set('SourceUpdateFrame4086_Request',c.f)
 set('SourceUpdateFrame4086_Base',0x8000);set('SourceUpdateFrame4086_Bank',60);set('SourceUpdateFrame4086_Bytes',TABLEBYTES)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800)
 set('VmSourceWorld_Count',128);set('VmSourceWorld_Time',c.time,4);set('SourceWorldTick4086_Ready',0)
 set('SourceClock4086_Ready',0xb4c5);set('SourceClock4086_TimeLo',c.time,4);set('SourceClock4086_Due',1);set('SourceClock4086_Fault',0)
 set('VmState_Status',0,1);set('VmState_Error',0)
 set('SourceFrameMotion4086_Ready',MOTIONLEASE);set('SourceFrameMotion4086_Status',0)
 set('VmSourceWorld_Level',c.level)
 put(view()+24,1,4);put(view()+28,c.direction,4)
 put(side()+48,c.base*65536,4)
 put(aux(),(c.mx or 10.5)*65536,4);put(aux()+4,(c.mz or 20.25)*65536,4);put(aux()+8,(c.alt or 3.25)*65536,4)
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
 if MOTIONLEASE~=0 then
  local c=row();local neighbor=(c.slot+1)%128;local guard_faults=0
  for i=0,19 do if emu.read(0x41f500+neighbor*20+i,mt)~=0xa5 then guard_faults=guard_faults+1 end end
  for i=0,63 do if emu.read(0x416800+neighbor*64+i,mt)~=0x5a then guard_faults=guard_faults+1 end end
  for i=0,79 do if emu.read(0x414000+neighbor*80+i,mt)~=0xc3 then guard_faults=guard_faults+1 end end
  emu.log('MOTIONGUARD|'..word(INDEX)..'|'..guard_faults..'|'..motion_faults)
 end
 if MOTIONLEASE~=0 then emu.log('MOTIONRESULT|'..word(INDEX)..'|'..dw(aux())..'|'..dw(aux()+4)..'|'..dw(side()+48)..'|'..dw(aux()+8)..'|'..dw(view()+28)..'|'..word(sy.SourceFrameMotion4086_Status))end
 emu.log('PREFIXRESULT|'..word(INDEX)..'|'..word(sy.SourceUpdateFrame4086_State)..'|'..word(sy.SourceUpdateFrame4086_Pending)..'|'..word(side()+6)..'|'..dw(side()+8)..'|'..dw(aux()+12)..'|'..word(side()+4)..'|'..word(view()+4)..'|'..dw(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Due))
end,emu.callbackType.exec,COMMITTED,COMMITTED,emu.cpuType.snes,mt)
'''
    for k,v in dict(INDEX=INDEX,EXPECTEDFAULT=REQUEST+6,REPEAT=REQUEST+8,TABLEBYTES=len(table),MOTIONLEASE=0xb4e8 if a.motion else 0,INIT=fs['PrefixFixture_Init'],
        OBSERVE=fs['PrefixFixture_Observe'],COMMITTED=fs['PrefixFixture_Committed']).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    if a.motion:
        lua+=f'''emu.addMemoryCallback(function()
 local state=emu.getState();motion_start=state.masterClock;motion_cpu={{}}
 for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do motion_cpu[k]=state['cpu.'..k]end
end,emu.callbackType.exec,{sy['SourceFrameMotion4086_Apply']},{sy['SourceFrameMotion4086_Apply']},emu.cpuType.snes,mt)
'''
        for label in ('PrefixFixture_MotionReturned','PrefixFixture_MotionRepeated'):
            lua+=f'''emu.addMemoryCallback(function()
 local state=emu.getState()
 for _,k in ipairs({{'x','y','d','dbr'}})do if motion_cpu[k]~=state['cpu.'..k]then motion_faults=motion_faults+1 end end
 if motion_cpu.sp+3~=state['cpu.sp'] or (motion_cpu.ps&254)~=(state['cpu.ps']&254)then motion_faults=motion_faults+1 end
 emu.log('MOTIONCOST|'..word({INDEX})..'|'..(state.masterClock-motion_start))
end,emu.callbackType.exec,{fs[label]},{fs[label]},emu.cpuType.snes,mt)
'''
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
    results=[];pending=[];motions=[];motion_costs=[];motion_guards=[]
    for line in (folder/'mesen.log').read_text().splitlines():
        if 'PREFIXRESULT|' in line:results.append(list(map(int,line.split('PREFIXRESULT|',1)[1].split('|'))))
        if 'PREFIXPENDING|' in line:pending.append(list(map(int,line.split('PREFIXPENDING|',1)[1].split('|'))))
        if 'MOTIONRESULT|' in line:motions.append(list(map(int,line.split('MOTIONRESULT|',1)[1].split('|'))))
        if 'MOTIONCOST|' in line:motion_costs.append(list(map(int,line.split('MOTIONCOST|',1)[1].split('|'))))
        if 'MOTIONGUARD|' in line:motion_guards.append(list(map(int,line.split('MOTIONGUARD|',1)[1].split('|'))))
    mismatches=[]
    for i,c in enumerate(rows):
        no_op=c['f']>=c['count'];script=c['animating']!=0 and not no_op
        expected=[i,2,0,99 if no_op else 0 if c['mode']==1 else c['f'],
            (c['time']+c['delay'])&0xffffffff if script else 0x12345678,
            0 if script else 0x87654321,c['handle']+(c['mode']==2),int(c['mode']!=3),
            (c['time']+1)&0xffffffff,0]
        if c.get('fault'):expected[1:3]=[1,2];expected[-2:]=[c['time'],1]
        if i>=len(results) or results[i]!=expected:mismatches.append(dict(case=c,expected=expected,actual=results[i] if i<len(results) else None))
        wanted=[] if no_op else ([1] if c['mode'] in (1,2) else [1,2]) if script else [2]
        actual=[p[1] for p in pending if p[0]==i]
        if actual!=wanted:mismatches.append(dict(case=c,pending_expected=wanted,pending_actual=actual))
    reporter.check('source prefix, interruption and captured identities preserved',len(results)==len(rows) and not mismatches)
    reporter.check('every pending service blocks early clock commit',bool(pending) and all(p[2:]==[rows[p[0]]['time'],1,1] for p in pending))
    motion_mismatches=[]
    if a.motion:
        animations={an['handle']:an for an in report['animations']}
        for i,c in enumerate(rows):
            active=c['f']<c['count'] and not(c['animating'] and c['mode'] in (1,2)) and (not c.get('fault') or c.get('reapply'))
            mx,mz,base,alt,direction=c.get('mx',10.5),c.get('mz',20.25),c['base'],c.get('alt',3.25),c['direction']
            if active:
                an=animations[c['handle']];move=an['frames'][c['f']]['move']
                if c['level']:mx+=move['x'] if direction else -move['x'];mz+=move['z']
                firstbase=an['frames'][0]['move']['base']
                if firstbase>0:
                    if base<=0:base=firstbase
                else:
                    base+=move['y'];alt=alt+move['y'] if move['y'] else 0
                if an['events']['flipframe']==c['f']:direction=int(not direction)
            expected=[i,*[int(v*65536)&0xffffffff for v in (mx,mz,base,alt)],direction&0xffffffff,2 if c.get('fault') else int(active)]
            if i>=len(motions) or motions[i]!=expected:
                motion_mismatches.append(dict(case=c,expected=expected,actual=motions[i] if i<len(motions) else None))
            if i in authority_cases:
                state=authority_cases[i]
                pinned=[i,*[int(v*65536)&0xffffffff for v in state[4:8]],int(state[3])&0xffffffff,1]
                if i>=len(motions) or motions[i]!=pinned:
                    motion_mismatches.append(dict(case=c,pinned_c_expected=pinned,actual=motions[i] if i<len(motions) else None))
        reporter.check('native movement, first-frame base and full direction truth match source',len(motions)==len(rows) and not motion_mismatches)
        reporter.check('motion preserves CPU context and adjacent source records',len(motion_guards)==len(rows) and all(r[1:]==[0,0] for r in motion_guards))
    r=dict(schema='BYOR_4086_UPDATE_FRAME_PREFIX_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',
        rom_sha256=hashlib.sha256(raw).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),
        cases=len(rows),source_frames=836,source_animations=80,pending_services=len(pending),
        mismatches=mismatches,results=results,pending=pending,script_services_instrumented=True,effect_services_instrumented=True,
        scope='Native frame mutation, signed animating gate, delay/time wrap, pause reset, callback interruption and unfinished-frame commit rejection',
        live_callback_owner_bound=False,remaining_effects_bound=False,motu_gameplay_proven=False,no_pcm_copies=True)
    r.update(motion_backend_executed=a.motion,motion_mismatches=motion_mismatches,motion_results=motions if a.motion else [],
        pinned_c_motion_cases=len(authority_cases),motion_cpu_costs=motion_costs,motion_guards=motion_guards)
    (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
