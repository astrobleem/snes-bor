"""Ranged target queries from actual player-think ownership over canonical rows."""
import argparse, hashlib, json
from dataclasses import asdict
from pathlib import Path
from m4_target_metadata_native import LUA
from actor_s5_entity_fixture import symbols
from source_normal_target_native import emit
from source_target_4086 import Target, normal_find
from source_frame_state_4086 import derive as frames_derive, pack as frames_pack
from source_animation_range_4086 import derive as ranges_derive, pack as ranges_pack
from compiler import Source
from _source_leaf_fixture import run_fixture
from _harness import Reporter

ASM='''
NormalTargetProbe:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl AIBEGIN
 bcs NormalTargetProbe_Bad
 cmp #2
 bne NormalTargetProbe_Bad
NormalTargetProbe_Query:
.a16
.i16
 nop
 lda.l QUERYADJUST
 tax
 lda.l QUERYADJUST+2
 tay
 lda.l QUERYROLE
 jsl NormalTarget_Begin
 bcs NormalTargetProbe_Bad
 ply
 plx
 plp
 clc
 rtl
NormalTargetProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''

SETUP=r'''
 set('SourceAITarget4086_Ready',0xb5f3);set('SourceAITarget4086_Status',0);put(sy.SourceAITarget4086_Result,55,4);set('SourceAITarget4086_Selected',55)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',6);set('SourceWorldTick4086_Slot',0);put(sy.SourceWorldTick4086_TimeLo,48,4)
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0);put(sy.SourceSelf4086_GlobalLow,0x414000,4)
 set('SourceAI4086_Ready',0xb5e2);set('SourceAI4086_State',0);put(sy.SourceAI4086_Endgame,0,4);set('SourceAI4086_SpawnID',23);set('SourceAI4086_RespawnID',104)
 set('SourceFreeze4086_Ready',0xb5df);set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0)
 put(0x439000,2,4);put(0x43900c,0,4);put(0x416814,0,4)
 set('SourceModelAnimationCopy4086_Ready',0xb4e9);set('SourceModelAnimationCopy4086_Models',16);set('SourceModelAnimationCopy4086_Maximum',128);set('SourceModelAnimationCopy4086_Bytes',4096)
 for j=0,4095 do emu.write(0x43c000+j,0,mt)end
 put(0x43c000+256*c.entities[1].model+2*c.role,c.handle)
 set('VmSourceEntity_Ready',0xb5ef);set('VmSourceEntity_Base',0x4000);set('VmSourceEntity_Bank',0x41);set('VmSourceEntity_Count',3)
 set('SourceEntityRange4086_Ready',0xb5f9);set('SourceEntityRange4086_Status',0)
 set('SourceAnimationRange4086_Ready',0xb5f8);set('SourceAnimationRange4086_Status',0);set('SourceAnimationRange4086_Bank',58);set('SourceAnimationRange4086_Bytes',RANGEBYTES)
 set('SourceCheckRange4086_Ready',0xb5f7);set('SourceCheckRange4086_Status',0)
 -- No common_think state is borrowed for this player-think query.
 set('SourceCommonThink4086_Ready',0);set('SourceCommonThink4086_State',0);set('SourceCommonThink4086_Slot',65535)
 for j=0,7 do emu.write(sy.VmNativeVariant_Result+j,0xa5,mt)end
 for j,v in ipairs(c.order)do put(0x41f200+2*(j-1),v)end
 put(QUERYROLE,c.role);put(QUERYADJUST,c.adjustment,4)
 for _,e in ipairs(c.entities)do local v=0x414000+80*e.slot;put(v+8,2,4);put(v+12,e.y,4);put(0x416830+64*e.slot,e.base,4)end
'''

QUERY=r'''
emu.addMemoryCallback(function()
 emu.log('NORMALTARGETFAULT|'..word(INDEX)..'|'..word(sy.SourceAITarget4086_Status)..'|'..word(sy.SourceTargetMeta4086_Status)..'|'..word(sy.SourceEntityRange4086_Status)..'|'..word(sy.SourceAnimationRange4086_Status)..'|'..word(sy.SourceAI4086_State)..'|'..word(sy.SourceAI4086_Callback))
end,emu.callbackType.exec,QUERYFAULT,QUERYFAULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.retired then put(0x414004,0,4)end
 local faults={query_ready={'SourceAITarget4086_Ready',0},query_busy={'SourceAITarget4086_Status',1},ai_state={'SourceAI4086_State',1},callback={'SourceAI4086_Callback',6},callback_high={'SourceAI4086_Callback+2',1},owner_pending={'SourceWorldTick4086_Pending',0},range_ready={'SourceEntityRange4086_Ready',0},range_busy={'SourceEntityRange4086_Status',1},table_ready={'SourceAnimationRange4086_Ready',0},numeric_ready={'SourceCheckRange4086_Ready',0}}
 if faults[c.bad]then local f=faults[c.bad];if f[1]=='SourceAI4086_Callback+2'then put(sy.SourceAI4086_Callback+2,f[2])else set(f[1],f[2])end end
 if c.bad=='role'then put(QUERYROLE,128)elseif c.bad=='handle'then put(0x43c000+256*c.entities[1].model+2*c.role,0)elseif c.bad=='self_y'then put(0x414008,1)end
 before={};for _,r in ipairs({{0x414000,18432},{0x40c000,12288},{0x42f400,3072},{0x439000,10240},{0x41f200,256},{0x43c000,4096},{sy.VmNativeVariant_Result,8}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,QUERY,QUERY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('NORMALTARGET|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceAITarget4086_Status)..'|'..(word(sy.SourceAITarget4086_Result)|(word(sy.SourceAITarget4086_Result+2)<<16))..'|'..word(sy.SourceAITarget4086_Selected)..'|'..word(sy.SourceAI4086_State)..'|'..word(sy.SourceAI4086_Callback))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def cases(frame_ir, range_ir):
    models=json.loads(Path('out/byor-motu-model-attack-policy/report.json').read_text())['models']
    ids={m['identity']:m['index']for m in models}
    frames={}
    for an in frame_ir['animations']:
        for i,f in enumerate(an['frames']):frames.setdefault(bool(f['vulnerable']),(ids[an['model']],an['handle'],i))
    rows=[]
    for i,an in enumerate(range_ir['animations']):
        for direction in (0,1):
            for variant in range(4):
                r=an['ranges'];center=[(r[2*k]+r[2*k+1])//2*65536 for k in range(4)]
                coords=center.copy();coords[0]*=1 if direction==1 else -1
                outside=coords.copy();outside[0]=(r[1]+1)*65536*(1 if direction==1 else -1)
                targets=[Target(0x414000,direction=direction,hostile=2),Target(0x414050,x=coords[0],z=coords[1],y=coords[2],base=coords[3],type=2),Target(0x4140a0,x=outside[0],z=outside[1],y=outside[2],base=outside[3],type=2)]
                if variant==1:targets[1]=Target(**(asdict(targets[1])|dict(dead=True)))
                if variant==2:targets[1]=Target(**(asdict(targets[1])|dict(hide=1)))
                if variant==3:targets[2]=Target(**(asdict(targets[1])|dict(token=0x4140a0,invincible=2)))
                entities=[]
                for slot,t in enumerate(targets):
                    model,handle,frame=frames[t.vulnerable]
                    if slot==0:model=i%16
                    entities.append(asdict(t)|dict(slot=slot,model=model,handle=handle,frame=frame,exists=int(t.alive),dead=int(t.dead)))
                retired=variant==3
                if retired:targets[0]=Target(**(asdict(targets[0])|dict(alive=False)))
                order=[0,2,1]if variant==3 else[0,1,2]
                adjustment=1 if variant==2 else 0
                expected=normal_find(targets,targets[0].token,r,adjustment,order)or 0
                rows.append(dict(name=f'range_{an["handle"]}_{direction}_{variant}',count=3,time=48,entities=entities,order=order,bad='',fault=0,expected=expected,role=(0,12,15,38,49,104)[i%6],handle=an['handle'],ranges=r,adjustment=adjustment,retired=retired))
    base=rows[0]
    for bad in ('query_ready','query_busy','ai_state','callback','callback_high','owner_pending','range_ready','range_busy','table_ready','numeric_ready','role','handle','self_y'):
        rows.append(dict(base,name=bad,bad=bad,fault=1,expected=55))
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('rom','source','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    source=Source(a.source);fi=frames_derive(source);ri=ranges_derive(source);ft=frames_pack(fi);rt=ranges_pack(ri);rows=cases(fi,ri)
    lua=LUA[:LUA.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local n=0;')]
    lua=lua.replace('TABLESIZE',str(len(ft))).replace('put(v+28,1,4)','put(v+28,e.direction,4)').replace('put(v+52,65536*e.slot,4)','put(v+52,e.x,4)').replace('put(v+60,220*65536,4)','put(v+60,e.z,4)')
    lua=lua.replace(' before={};',SETUP.replace('RANGEBYTES',str(len(rt)))+' before={};')+QUERY
    sy=symbols(Path('src/main.sym'));assembly=ASM+emit(sy)+'\nNormalTargetProbe_End:\n'
    for k,v in dict(AIBEGIN=sy['SourceAI4086_Begin'],QUERYROLE=0x7ffd8a,QUERYADJUST=0x7ffd8c).items():
        import re
        assembly=re.sub(r'\b'+k+r'\b',str(v),assembly);lua=re.sub(r'\b'+k+r'\b',str(v),lua)
    reporter=Reporter('M4-NORMAL-TARGET',kind='GATE')
    def boundary(raw,all_symbols):
        if all_symbols['NormalTargetProbe_End']>>16!=39:raise ValueError('NORMAL_TARGET_FIXTURE_BANK_OVERFLOW')
    raw,log=run_fixture(a.rom,a.output,rows,'NormalTargetProbe','SourceAITarget4086_Ready',0xb5f3,[(59,0,ft),(58,0,rt)],lua,reporter,append=assembly,probes=dict(QUERY='NormalTargetProbe_Query',QUERYFAULT='NormalTargetProbe_Bad'),batch_size=4,link_pcm=False,rom_transform=boundary)
    actual=[list(map(int,l.split('NORMALTARGET|',1)[1].split('|')))for l in log.splitlines()if'NORMALTARGET|'in l]
    failures=[]
    for i,v in enumerate(actual):
        c=rows[i];expected=[i,0,0,3 if c['fault'] else 2,c['expected'],55 if c['fault'] else (c['expected']-0x414000)//80 if c['expected'] else 65535,1 if c['bad']=='ai_state' else 2,6 if c['bad']=='callback' else 2]
        # A query that faults after publishing its detection adjustment retains
        # that scratch, rather than pretending to publish a target result.
        if c['fault']and c['bad']not in('query_ready','query_busy','ai_state','callback','callback_high','owner_pending'):expected[4]=c['adjustment']
        if v!=expected:failures.append(dict(input=c,actual=v,expected=expected))
    reporter.check('all authored ranges, current role cache, retired self, real player owner, preserved CPU/entities/VM result and guards',len(actual)==len(rows)and not failures)
    report=dict(schema='BYOR_4086_NORMAL_TARGET_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),authored_ranges=len(ri['animations']),inputs=rows,actual=actual,failures=failures[:20],rom_sha256=hashlib.sha256(raw).hexdigest(),range_table_sha256=hashlib.sha256(rt).hexdigest(),frame_table_sha256=hashlib.sha256(ft).hexdigest(),actual_player_think_owner=True,current_mutable_role_cache_read=True,new_state_bytes=0,numeric_policy='ACCEPTED_COMPAT_Q16_16',combat_attack_chain_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
