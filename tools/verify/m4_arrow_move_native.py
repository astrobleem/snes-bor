"""Native ordinary arrow velocity on real source rows, with owner guard faults."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
from m4_ai_owner_native import LUA as AI_LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True)
    p.add_argument('--dispatcher',action='store_true',help='Exercise production common_move dispatch and priority')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    au=json.loads(a.authority.read_text());assert au['status']=='PASS' and au['source_function_unmodified']
    # Select source-authority cases admitted by the native immutable empty-wall lease.
    rows=[]
    base=dict(time=48,nextthink=48,endgame=0,takeaction=0,think=6,noaicontrol=0,
              update_mark=0x12340001,animation=5,spawn=3,respawn=4,animating=1,exists=1,
              mutation=0,bad='',fault=0)
    seen=set()
    for index,(c,result) in enumerate(zip(au['inputs'],au['actual'])):
        if not c['level_present'] or c['hit']!=-1:continue
        key=(c['direction'],float(c['speed']).hex(),c['subject_to_wall'])
        if key in seen:continue
        seen.add(key);speed=int(c['speed']*65536);want=int((-c['speed'] if c['direction']==0 else c['speed'] if c['direction']==1 else 3.25)*65536)&0xffffffff
        rows.append(dict(base,slot=(0,1,63,127)[len(rows)%4],direction=c['direction'],speed=speed&0xffffffff,want=want,authority_case=index,subject=c['subject_to_wall'],subtype=0))
    if a.dispatcher:
        rows=[dict(rows[0],mask=mask,air=air,fault=int(bool(mask&128)),want=212992 if mask&128 else rows[0]['want'],arrow_status=0 if mask&128 else 2)
              for mask,air in itertools.product((256,256|512,256|1024,256|2048,128|256),(0,1))]
    else:
        for bad in ('ready','status','commonready','commonphase','commonslot','owner','modelcore','lifelease','speedlease','chase','walls','wallready','stage','stagezero','directiontype','directionreserved','minspeed'):
            rows.append(dict(rows[0],bad=bad,fault=1,want=212992))
    lua=AI_LUA[:AI_LUA.index(' local faults=')]
    lua=lua.replace("set('SourceAI4086_State',0)","set('SourceAI4086_State',2);set('SourceAI4086_Slot',s)")
    lua+=r'''
 set('VmSourceWorld_Level',1);set('SourceEnvironment4086_Ready',0xb4d1);set('SourceEnvironment4086_WallCount',0);set('SourceEnvironment4086_Stage',1)
 set('SourceCommonThink4086_Ready',0xb5e7);set('SourceCommonThink4086_State',8);set('SourceCommonThink4086_Slot',s)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceArrowMove4086_Ready',0xb616);set('SourceArrowMove4086_Status',0)
 put(life+48,c.subtype,4);put(life+74,0xb4fb);put(life+76,0xb508)
 put(v+24,1);put(v+26,0);put(v+28,c.direction,4);put(side+60,c.speed,4);put(side+36,212992,4);put(side+40,0xfffb8000,4)
 put(0x43d800+s*4,0x80000002,4)
 local faults={ready={'SourceArrowMove4086_Ready',0},status={'SourceArrowMove4086_Status',3},commonready={'SourceCommonThink4086_Ready',0},commonphase={'SourceCommonThink4086_State',7},commonslot={'SourceCommonThink4086_Slot',(s+1)%128},owner={'SourceSelf4086_GlobalLow',0},modelcore={'SourceModelEntityCopy4086_Ready',0},walls={'SourceEnvironment4086_WallCount',1},wallready={'SourceEnvironment4086_Ready',0},stage={'SourceEnvironment4086_Stage',2},stagezero={'SourceEnvironment4086_Stage',0}}
 if faults[c.bad]then local f=faults[c.bad];set(f[1],f[2])end
 if c.bad=='lifelease'then put(life+74,0)elseif c.bad=='speedlease'then put(life+76,0)elseif c.bad=='chase'then put(life+48,11,4)elseif c.bad=='directiontype'then put(v+24,2)elseif c.bad=='directionreserved'then put(v+26,1)elseif c.bad=='minspeed'then put(v+28,0,4);put(side+60,0x80000000,4)end
 before={};for _,r in ipairs({{0x414000,18432},{0x41f500,2560},{0x42e000,5120},{0x42f400,3072},{0x439000,10240},{0x43eb00,4096},{0x43c000,8192},{0x43d800,512},{sy.SourceWorldTick4086_Ready,52},{sy.SourceSelf4086_GlobalLow,4}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local state=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=state['cpu.'..k]end;cpu.sp=cpu.sp+3
end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local state=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=state['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(state['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local side=0x416800+c.slot*64
 if c.fault==0 then for i=0,3 do before[side+36+i]=(c.want>>(i*8))&255 end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('ARROW|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceArrowMove4086_Status)..'|'..dw(side+36)..'|'..dw(side+40)..'|'..dw(0x43d800+c.slot*4))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
    if a.dispatcher:
        lua=lua.replace(" set('VmSourceWorld_Level',1)"," set('SourceAIReadonly4086_Ready',0xb5e8);set('SourceAIReadonly4086_Status',0);set('SourceRetirement4086_Ready',0xb4f8);put(v+8,2);put(v+10,0);put(v+12,c.air*65536,4);put(side+48,0,4);put(0x40c034+s*96,c.mask,4)\n set('VmSourceWorld_Level',1)")
    reporter=Reporter('M4-ARROW-MOVE',kind='GATE')
    apply='SourceAIReadonly4086_Execute'if a.dispatcher else'SourceArrowMove4086_Execute'
    raw,log=run_fixture(a.rom,a.output,rows,apply,'SourceArrowMove4086_Ready',0xb616,[],lua,reporter,batch_size=2)
    results=[list(map(int,line.split('ARROW|',1)[1].split('|')))for line in log.splitlines()if 'ARROW|'in line]
    expected=[[i,0,0,c.get('arrow_status',3 if c['fault']else 2),c['want'],0xfffb8000,0x80000002]for i,c in enumerate(rows)]
    failed=[dict(index=i,input=rows[i],actual=v,expected=w)for i,(v,w)in enumerate(zip(results,expected))if v!=w]
    reporter.check('source-authority velocity, untouched Z/autokill, physical rows/CPU state, explicit admission faults',len(results)==len(rows)and not failed)
    report=dict(schema='BYOR_4086_ARROW_MOVE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',
                cases=len(rows),inputs=rows,results=results,failures=failed,rom_sha256=hashlib.sha256(raw).hexdigest(),
                authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),ptype=0,wall_count=0,
                coordinate_policy='ACCEPTED_COMPAT_Q16_16',position_integration_proven=False,
                common_move_dispatcher_exercised=a.dispatcher,live_projectile_owner_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
