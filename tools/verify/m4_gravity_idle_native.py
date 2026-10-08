"""Native inactive-air gravity using actual source rows and CPU observations."""
import argparse
import hashlib
import json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function set(k,v,n)put(assert(sy[k],k),v,n)end
local before,cpu,ctx={},{},0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 local s=c.slot;local v=0x414000+s*80;local side=0x416800+s*64;local aux=0x41f500+s*20;local freeze=0x42e000+s*40;local life=0x439000+s*80
 set('SourceGravityIdle4086_Ready',0xb618);set('SourceGravityIdle4086_Status',0);set('SourceFreeze4086_Ready',0xb5df)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Level',1);set('VmSourceWorld_TemplateCount',1);set('VmSourceWorld_Time',c.time,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',11);set('SourceWorldTick4086_Slot',s);set('SourceWorldTick4086_Fault',0);set('SourceWorldTick4086_TimeLo',c.time,4)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceLifecycle4086_Ready',0xb4fb);set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0);set('SourceSelf4086_GlobalLow',v,4)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',128);set('SourceModelEntityCopy4086_Models',1)
 set('SourceEmptyInitEnvironment4086_Ready',0xb504);set('SourceEmptyInitEnvironment4086_Status',0);set('SourceEmptyInitEnvironment4086_Models',1);set('SourceEmptyInitEnvironment4086_Stage',1)
 set('SourceEnvironment4086_Ready',0xb4d1);set('SourceEnvironment4086_Stage',1);set('SourceEnvironment4086_WallCount',0)
 put(v,v,4);put(v+4,1,4);put(v+48,2);put(v+50,0);put(v+52,c.x,4);put(v+56,2);put(v+58,0);put(v+60,c.z,4)
 set('SourceToss4086_Ready',0xb4e2)
 put(v+8,2);put(v+10,0);put(v+12,c.altitude*65536,4)
 put(side+44,0,4);put(side+48,c.altitude*65536,4)
 put(0x40c024+s*96,1,4);put(0x41f300+s*4,c.toss_time,4)
 put(side,0);put(side+24,c.nextmove,4);put(aux,c.mx,4);put(aux+4,c.mz,4);put(life+4,0,4);put(life+72,0);put(life+74,0xb4fb)
 put(freeze,c.freeze,4);put(freeze+4,c.freeze==1 and c.time<0xffffffff and (c.time+1) or 0,4);put(freeze+36,c.mark,4)
 put(0x40c048+s*96,32,4);put(0x43fd94,0,4);put(0x43fd98,c.freeze==1 and c.time==0xffffffff and 1 or 0,4)
 local faults={ready={'SourceGravityIdle4086_Ready',0},status={'SourceGravityIdle4086_Status',3},world={'VmSourceWorld_Ready',0},tick={'SourceWorldTick4086_Ready',0},state={'SourceWorldTick4086_State',3},phase={'SourceWorldTick4086_Phase',10},pending={'SourceWorldTick4086_Pending',0},tickfault={'SourceWorldTick4086_Fault',1},count={'VmSourceWorld_Count',0},slot={'SourceWorldTick4086_Slot',128},time={'SourceWorldTick4086_TimeLo',(c.time+1)&0xffff},self={'SourceSelf4086_GlobalLow',0},selffault={'SourceSelf4086_Fault',1},selfactive={'SourceSelf4086_Active',1},freeze={'SourceFreeze4086_Ready',0},aux={'SourceUpdateFrame4086_Ready',0},platform={'SourceEmptyInitEnvironment4086_Ready',0},walls={'SourceEnvironment4086_WallCount',1},stage={'SourceEnvironment4086_Stage',2}}
 if faults[c.bad]then local f=faults[c.bad];set(f[1],f[2])end
 if c.bad=='noadjust'then put(0x40c024+s*96,0,4)elseif c.bad=='vertical'then put(side+44,65536,4)elseif c.bad=='altitude'then put(v+12,(c.altitude+1)*65536,4)elseif c.bad=='tosslease'then set('SourceToss4086_Ready',0)elseif c.bad=='corelease'then set('SourceModelEntityCopy4086_Ready',0)elseif c.bad=='corecount'then set('SourceModelEntityCopy4086_Entities',127)elseif c.bad=='atag'then put(v+8,1)elseif c.bad=='areserved'then put(v+10,1)elseif c.bad=='trymove'then put(life+4,1,4)elseif c.bad=='lifelease'then put(life+74,0)elseif c.bad=='modelrange'then put(side,1)elseif c.bad=='modelidentity'then put(life+72,1)elseif c.bad=='xtag'then put(v+48,1)elseif c.bad=='zreserved'then put(v+58,1)elseif c.bad=='token'then put(v,0,4)elseif c.bad=='exists'then put(v+4,0,4)end
 before={};for _,r in ipairs({{0x41f300,512},{0x414000,18432},{0x41f500,2560},{0x42e000,5120},{0x439000,10240},{0x40c000,12288},{sy.SourceWorldTick4086_Ready,52},{sy.SourceSelf4086_GlobalLow,4}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local state=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=state['cpu.'..k]end;cpu.sp=cpu.sp+3
end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local state=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=state['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(state['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local s=c.slot;local v=0x414000+s*80;local side=0x416800+s*64;local aux=0x41f500+s*20;local freeze=0x42e000+s*40
 if c.fault==0 then for _,r in ipairs({{0x41f300+s*4,c.expected[1]},{freeze+36,c.expected[2]}})do for i=0,3 do before[r[1]+i]=(r[2]>>(8*i))&255 end end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('GRAVITYIDLE|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceGravityIdle4086_Status)..'|'..dw(0x41f300+s*4)..'|'..dw(freeze+36))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    au=json.loads(a.authority.read_text());assert au['status']=='PASS' and au['adjust_base_body_proven']
    selected=[(i,c)for i,c in enumerate(au['inputs'])if c['falling']==0 and c['subject_to_platform']==1]
    rows=[]
    for i,c in selected:
        et=c['toss'];em=c['mark']
        if not em&8:
            if not c['freeze'] and et<=c['time']:et=(c['time']+1)&0xffffffff
            em|=8
        rows.append(dict(authority_case=i,slot=(0,1,63,127)[len(rows)%4],time=c['time'],freeze=c['freeze'],mark=c['mark'],altitude=c['altitude'],toss_time=c['toss'],nextmove=0,x=5242880,z=14417920,mx=98304,mz=0,bad='',fault=0,expected=[et,em]))
    base=dict(rows[0],mark=0,time=48,toss_time=0,altitude=34,freeze=0)
    for bad in ('ready','status','world','tick','state','phase','pending','tickfault','count','slot','time','self','selffault','selfactive','freeze','aux','platform','walls','stage','lifelease','modelrange','modelidentity','token','exists','noadjust','vertical','altitude','tosslease','corelease','corecount','atag','areserved'):
        rows.append(dict(base,bad=bad,fault=1,expected=[0,0]))
    reporter=Reporter('M4-GRAVITY-IDLE',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceGravityIdle4086_Execute','SourceGravityIdle4086_Ready',0xb618,[],LUA,reporter,batch_size=2)
    actual=[list(map(int,line.split('GRAVITYIDLE|',1)[1].split('|')))for line in log.splitlines()if 'GRAVITYIDLE|'in line]
    expected=[[i,0,0,3 if c['fault']else 2,*c['expected']]for i,c in enumerate(rows)]
    failures=[dict(index=i,input=rows[i],actual=v,expected=w)for i,(v,w)in enumerate(zip(actual,expected))if v!=w]
    reporter.check('inactive-air gravity clocks/marks, actual freeze, physical siblings, CPU and explicit guards',len(actual)==len(rows)and not failures)
    r=dict(schema='BYOR_4086_GRAVITY_IDLE_NATIVE_V1',status='PASS'if not failures and len(actual)==len(rows)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures,rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),zero_falling_and_binding_compiler_contract=True,sticky_base_empty_platform_policy=True,active_airborne_or_landing_proven=False,world_post_update_owner_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
