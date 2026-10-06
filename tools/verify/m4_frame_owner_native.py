"""Combined captured-frame owners against pinned C; callback body instrumented."""
import argparse, hashlib, json, struct, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_frame_effects_4086 import pack as pack_fe
from source_frame_effect_plan import derive, pack as pack_plan, unpack
from source_update_frame_authority import events
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM='''
FrameOwnerFixture_Run:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl FRAMEBEGIN
 bcs FrameOwnerFixture_Bad
FrameOwnerFixture_Script:
.a16
.i16
 nop
 lda.l PENDING
 cmp #1
 bne FrameOwnerFixture_Effects
 lda #1
 jsl FRAMEACK
 bcs FrameOwnerFixture_Bad
FrameOwnerFixture_Effects:
.a16
.i16
 lda.l PENDING
 beq FrameOwnerFixture_Done
 jsl MOTION
 bcs FrameOwnerFixture_Bad
 jsl PLANBEGIN
 bcs FrameOwnerFixture_Bad
 jsl LEAF
 bcs FrameOwnerFixture_Bad
 jsl RESTORE
 bcs FrameOwnerFixture_Bad
 lda #2
 jsl FRAMEACK
 bcs FrameOwnerFixture_Bad
FrameOwnerFixture_Done:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
FrameOwnerFixture_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''

LUA=r'''
local mt=emu.memType.snesMemory;local before={};local ctx=0;local cpu={};local start=0;local lease=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function set(p,k,v,n)put(sy[p..'4086_'..k],v,n)end
local ranges={{0x414000,10240},{0x416800,8192},{0x41f500,2560},{0x43fb00,512},{0x7ffe30,4},{0x7ffe38,4},{0x7ff610,32}}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local v=0x414000+80*c.slot;local s=0x416800+64*c.slot;local a=0x41f500+20*c.slot
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,0xa5,mt)end end
 -- Disable unrelated owners explicitly; all admitted owners below are real.
 for _,p in ipairs({'SourceAnimationInit','SourceModelAnimation','SourceModelTransition','SourceWorldTick','SourceFrameStack'})do set(p,'Ready',0)end
 set('SourceUpdateFrame','Ready',0xb4e3);set('SourceUpdateFrame','State',0);set('SourceUpdateFrame','Pending',0);set('SourceUpdateFrame','Fault',0)
 set('SourceUpdateFrame','Slot',c.slot);set('SourceUpdateFrame','Request',0);set('SourceUpdateFrame','Base',0x8000);set('SourceUpdateFrame','Bank',60);set('SourceUpdateFrame','Bytes',FEBYTES)
 set('SourceFrameMotion','Ready',0xb4e8);set('SourceFrameMotion','Status',0)
 set('SourceFrameEffectPlan','Ready',0xb4f2);set('SourceFrameEffectPlan','State',0);set('SourceFrameEffectPlan','Service',0)
 set('SourceFrameEffectPlan','Base',0x8000);set('SourceFrameEffectPlan','Bank',59);set('SourceFrameEffectPlan','Bytes',PLANBYTES);set('SourceFrameEffectPlan','Animations',2)
 set('SourceFrameEffectPlan','PairedCrcLo',PAIRLO);set('SourceFrameEffectPlan','PairedCrcHi',PAIRHI);set('SourceFrameEffectPlan','BodyCrcLo',BODYLO);set('SourceFrameEffectPlan','BodyCrcHi',BODYHI)
 set('SourceFrameEffectLeaf','Ready',0xb4f4);set('SourceSelf','Ready',0xb4f6);set('SourceSelf','Active',0);set('SourceSelf','Fault',0)
 set('SourceSelf','GlobalLow',c.old);set('SourceSelf','GlobalHigh',c.old==0 and 0 or 0x41)
 put(sy.VmSourceWorld_Ready,0xb4a3);put(sy.VmSourceWorld_PoolBase,0x4000);put(sy.VmSourceWorld_SideBase,0x6800);put(sy.VmSourceWorld_Count,128);put(sy.VmSourceWorld_Level,c.level);put(sy.VmSourceWorld_Time,c.time,4)
 put(sy.VmState_Status,0,1);put(sy.VmState_Error,0);put(EXPECTFAULT,c.bad and 1 or 0)
 put(v+4,1);put(v+16,1,4);put(v+20,0,4);put(v+24,1,4);put(v+28,c.direction,4)
 put(s+4,1);put(s+6,0);put(s+8,0,4);put(s+48,-2*65536,4)
 put(a,10*65536,4);put(a+4,20*65536,4);put(a+8,3*65536,4);put(a+12,123,4);put(a+16,c.animating)
 put(0x43fb00,0,4);put(0x7ffe30,99,4)
 set('SourceClock','Ready',0xb4c5);set('SourceClock','Due',1);set('SourceClock','TimeLo',c.time,4);set('SourceClock','Fault',0)
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 lease=0
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;start=s.masterClock;ctx=0
end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local v=0x414000+80*c.slot;local s=0x416800+64*c.slot
 if word(sy.SourceSelf4086_GlobalLow)~=0x4000+80*c.slot or word(sy.SourceSelf4086_GlobalHigh)~=0x41 or word(sy.SourceSelf4086_Active)~=1 then lease=lease+1 end
 if word(sy.SourceUpdateFrame4086_Pending)==1 then
  if c.mode==1 then put(s+6,1)elseif c.mode==2 then put(s+4,2)elseif c.mode==3 then put(v+4,0)end
  put(sy.VmState_Status,4,1)
 end
end,emu.callbackType.exec,SCRIPTPROBE,SCRIPTPROBE,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp+3~=s['cpu.sp'] or (cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('OWNERCOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local e=c.wanted;local v=0x414000+80*c.slot;local s=0x416800+64*c.slot;local a=0x41f500+20*c.slot
 local function expect(at,n,size)for i=0,(size or 2)-1 do before[at+i]=(n>>(8*i))&255 end end
 expect(v+4,e[21]);expect(s+4,e[22]==1 and 1 or 2);expect(s+6,e[1]);expect(s+8,e[2],4);expect(a+12,e[3],4)
 expect(v+28,e[4],4);expect(a,e[5]*65536,4);expect(a+4,e[6]*65536,4);expect(s+48,e[7]*65536,4);expect(a+8,e[8]*65536,4)
 expect(0x7ffe30,e[9],4);expect(0x43fb00,e[10],4)
 if c.bad then expect(0x7ffe38,0x4000+80*c.slot);expect(0x7ffe3a,0x41)end
 local mismatch=0;for addr,n in pairs(before)do if emu.read(addr,mt)~=n then mismatch=mismatch+1 end end
 local retirement=0
 for _,check in ipairs({{'SourceUpdateFrame4086_State',c.bad and 3 or 2},{'SourceUpdateFrame4086_Pending',c.bad and 2 or 0},{'SourceSelf4086_Active',c.bad and 1 or 0},{'SourceSelf4086_Fault',c.bad=='self_fault' and 1 or 0}})do if word(sy[check[1]])~=check[2]then retirement=retirement+1 end end
 emu.log('OWNERRESULT|'..word(INDEX)..'|'..mismatch..'|'..ctx..'|'..lease..'|'..retirement)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('OWNERCLOCK|'..word(INDEX)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_TimeHi)..'|'..word(sy.SourceClock4086_Fault))end,emu.callbackType.exec,POSTRESULT,POSTRESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--native-runner',action='store_true');p.add_argument('--external-yield',action='store_true');p.add_argument('--runner-guards',action='store_true');a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    if a.external_yield and not a.native_runner:raise ValueError('EXTERNAL_YIELD_REQUIRES_NATIVE_RUNNER')
    if a.runner_guards and not a.external_yield:raise ValueError('RUNNER_GUARDS_REQUIRE_EXTERNAL_YIELD')
    authority=json.loads(Path('out/byor-motu-update-frame-authority/report.json').read_text())
    if authority['status']!='PASS' or authority['functions_sha256']!='72d75ee216c7c00ceb01f6f811b77184dda3a8f22f0174b7f0be6e35205183d7':raise ValueError('PINNED_C_REQUIRED')
    frames=[dict(move=dict(base=-1,x=3,y=2,z=-1),sound=None,delay_ticks=6),dict(move=dict(base=22,x=5,y=0,z=4),sound=None,delay_ticks=8)]
    if a.external_yield:frames[0]['sound']='fixture.wav'
    effects=dict(models=['dust','effect'],animations=[dict(handle=i,events=events(),frames=frames) for i in (1,2)])
    fe=pack_fe(effects);plan=pack_plan(derive(effects));unpack(plan,fe);h=struct.unpack_from('<4s6H4I',plan)
    rows=[]
    for ar in authority['results']:
        c=ar['case']
        if c['mode']>3 or c['f'] or c['base']!=-1 or c['jumping'] or c['success'] or c['subdamage']:continue
        for slot in (0,1,127):
            for old in (0,0x4000,0x4000+80*127):rows.append(dict(c,slot=slot,old=old,wanted=ar['actual']['state']))
    if a.runner_guards:
        base=[c for c in rows if c['mode']==0 and c['animating']==1 and c['direction']==1 and c['level']==1 and c['old']==0]
        rows=[dict(c,bad=bad) for c in base for bad in ('motion_ready','self_ready','self_fault','plan_ready','plan_state','slot','handle','frame','count','index','bank','base','span','opcode')]
    bindings=dict(FRAMEBEGIN='SourceUpdateFrame4086_Begin',FRAMEACK='SourceUpdateFrame4086_Ack',PENDING='SourceUpdateFrame4086_Pending',MOTION='SourceFrameMotion4086_Apply',PLANBEGIN='SourceFrameEffectPlan4086_Begin',LEAF='SourceFrameEffectLeaf4086_Apply',RESTORE='SourceSelf4086_RestoreEffect')
    values=dict(FEBYTES=len(fe),PLANBYTES=len(plan),PAIRLO=h[-2]&65535,PAIRHI=h[-2]>>16,BODYLO=h[-1]&65535,BODYHI=h[-1]>>16)
    lua=LUA
    for k,v in values.items():lua=lua.replace(k,str(v))
    reporter=Reporter('M4-COMBINED-FRAME-OWNER',kind='GATE')
    asm=ASM
    if a.native_runner:
        start=asm.index(' jsl MOTION');end=asm.index('FrameOwnerFixture_Done:')
        asm=asm[:start]+' jsl RUNNER\n bcs FrameOwnerFixture_Bad\n cmp #0\n bne FrameOwnerFixture_Bad\n'+asm[end:]
        bindings['RUNNER']='SourceFrameEffects4086_Run'
        if a.external_yield:
            asm=asm.replace(' cmp #0\n bne FrameOwnerFixture_Bad', ''' cmp #9
 bne FrameOwnerFixture_Bad
 jsl CLOCK
 bcc FrameOwnerFixture_Bad
FrameOwnerFixture_YieldClock:
.a16
.i16
 nop
 jsl RUNNER
 bcs FrameOwnerFixture_Bad
 cmp #9
 bne FrameOwnerFixture_Bad
 lda #9
 sta.l ACKWORD
 jsl CURSORACK
 bcs FrameOwnerFixture_Bad
 jsl RUNNER
 bcs FrameOwnerFixture_Bad
 cmp #0
 bne FrameOwnerFixture_Bad''')
            bindings.update(CLOCK='SourceClock4086_Commit',CURSORACK='SourceFrameEffectPlan4086_Ack',ACKWORD='SourceFrameEffectPlan4086_Acknowledged')
            if a.runner_guards:
                begin=asm.index(' jsl RUNNER',asm.index('FrameOwnerFixture_YieldClock:'))
                asm=asm[:begin]+''' jsl RUNNER
 bcs FrameOwnerFixture_Bad
 lda #1
 sta.l ERROR
 jmp FrameOwnerFixture_Bad
'''+asm[asm.index('FrameOwnerFixture_Done:'):]
                # Require real C=1 as well as the observed diagnostic state.
            lua+=r'''
emu.addMemoryCallback(function()
 emu.log('OWNERYIELD|'..word(INDEX)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault)..'|'..word(sy.SourceFrameEffectPlan4086_Service)..'|'..word(sy.SourceSelf4086_Active))
 set('SourceClock','Fault',0)
 local c=rows[word(INDEX)+1]
 if c.bad=='motion_ready'then set('SourceFrameMotion','Ready',0)
 elseif c.bad=='self_ready'then set('SourceSelf','Ready',0)
 elseif c.bad=='self_fault'then set('SourceSelf','Fault',1)
 elseif c.bad=='plan_ready'then set('SourceFrameEffectPlan','Ready',0)
 elseif c.bad=='plan_state'then set('SourceFrameEffectPlan','State',3)
 elseif c.bad=='slot'then set('SourceFrameEffectPlan','Slot',c.slot+1)
 elseif c.bad=='handle'then set('SourceFrameEffectPlan','Handle',2)
 elseif c.bad=='frame'then set('SourceFrameEffectPlan','Frame',1)
 elseif c.bad=='count'then set('SourceFrameEffectPlan','Count',33)
 elseif c.bad=='index'then set('SourceFrameEffectPlan','Index',32)
 elseif c.bad=='bank'then set('SourceFrameEffectPlan','Bank',64)
 elseif c.bad=='base'then set('SourceFrameEffectPlan','Base',0x7ffe)
 elseif c.bad=='span'then set('SourceFrameEffectPlan','Bytes',0)
 elseif c.bad=='opcode'then set('SourceFrameEffectPlan','Service',7)end
end,emu.callbackType.exec,YIELDPROBE,YIELDPROBE,emu.cpuType.snes,mt)
'''
    probes=dict(SCRIPTPROBE='FrameOwnerFixture_Script')
    if a.external_yield:probes['YIELDPROBE']='FrameOwnerFixture_YieldClock'
    raw,log=run_fixture(a.rom,folder,rows,'FrameOwnerFixture_Run','SourceUpdateFrame4086_Ready',0xb4f7,[(60,0,fe),(59,0,plan)],lua,reporter,post='SourceClock4086_Commit',append=asm,bindings=bindings,probes=probes)
    results=[];costs=[];clocks=[];yields=[]
    for line in log.splitlines():
        for marker,target in [('OWNERRESULT|',results),('OWNERCOST|',costs),('OWNERCLOCK|',clocks),('OWNERYIELD|',yields)]:
            if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
    reporter.check('C state, all guarded live bytes, CPU context and self identity',len(results)==len(rows) and all(r==[i,0,0,0,0] for i,r in enumerate(results)))
    reporter.check('clock retires only after combined owners complete',len(clocks)==len(rows) and all(r==([i,1,c['time']&65535,c['time']>>16,1] if c.get('bad') else [i,0,(c['time']+1)&65535,((c['time']+1)&0xffffffff)>>16,0]) for i,(r,c) in enumerate(zip(clocks,rows))))
    if a.external_yield:
        expected=[[i,1,c['time']&65535,1,9,1] for i,c in enumerate(rows) if not c['animating'] or c['mode'] not in (1,2)]
        reporter.check('external service retains self/cursor and blocks clock before explicit Ack',yields==expected)
    report=dict(schema='BYOR_4086_COMBINED_FRAME_OWNER_NATIVE_V1',status='PASS' if all(ok for _,ok in reporter.results) else 'FAIL',cases=len(rows),case_inputs=rows,results=results,costs=costs,clocks=clocks,yields=yields,rom_sha256=hashlib.sha256(raw).hexdigest(),frame_effects_sha256=hashlib.sha256(fe).hexdigest(),plan_sha256=hashlib.sha256(plan).hexdigest(),native_effect_runner=a.native_runner,runner_guards=a.runner_guards,callback_body_instrumented=True,sound_service_instrumented=a.external_yield,native_motion_quake_cursor_self_retirement=True,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'frame-effects.b4fe').write_bytes(fe);(folder/'frame-effects.b4ep').write_bytes(plan);(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
