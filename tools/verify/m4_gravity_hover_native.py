"""Native non-gravitating source hover, with exact branch boundary admission."""
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
 set('SourcePhysicsState4086_Ready',c.physics_ready or 0);put(0x42d800+s*16,c.falling or 0,4);put(0x42d804+s*16,c.hithead or 0,4);put(0x42d808+s*16,c.landed_platform or 0,4)
 set('SourceGravityIdle4086_Ready',0xb619);set('SourceGravityIdle4086_Status',0);set('SourceFreeze4086_Ready',0xb5df)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Level',1);set('VmSourceWorld_TemplateCount',1);set('VmSourceWorld_Time',c.time,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',c.world_state);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',11);set('SourceWorldTick4086_Slot',s);set('SourceWorldTick4086_Fault',0);set('SourceWorldTick4086_TimeLo',c.time,4)
 set('SourceUpdateFrame4086_Ready',0xb4e3);set('SourceLifecycle4086_Ready',0xb4fb);set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0);set('SourceSelf4086_GlobalLow',v,4)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',128);set('SourceModelEntityCopy4086_Models',1)
 set('SourceEmptyInitEnvironment4086_Ready',0xb504);set('SourceEmptyInitEnvironment4086_Status',0);set('SourceEmptyInitEnvironment4086_Models',1);set('SourceEmptyInitEnvironment4086_Stage',1)
 set('SourceEnvironment4086_Ready',0xb4d1);set('SourceEnvironment4086_Stage',1);set('SourceEnvironment4086_WallCount',0)
 put(v,v,4);put(v+4,1,4);put(v+48,2);put(v+50,0);put(v+52,c.x,4);put(v+56,2);put(v+58,0);put(v+60,c.z,4)
 set('SourceToss4086_Ready',0xb4e2)
 put(v+8,2);put(v+10,0);put(v+12,c.a,4)
 put(side+44,0,4);put(side+48,c.base,4)
 put(0x40c024+s*96,1,4);put(0x40c014+s*96,c.gravity,4);put(0x41f300+s*4,c.toss_time,4)
 put(side,0);put(side+24,c.nextmove,4);put(aux,c.mx,4);put(aux+4,c.mz,4);put(life+4,0,4);put(life+72,0);put(life+74,0xb4fb)
 put(freeze,c.freeze,4);put(freeze+4,c.freeze==1 and c.time<0xffffffff and (c.time+1) or 0,4);put(freeze+36,c.mark,4)
 put(0x40c048+s*96,32,4);put(0x43fd94,0,4);put(0x43fd98,c.freeze==1 and c.time==0xffffffff and 1 or 0,4)
 local faults={ready={'SourceGravityIdle4086_Ready',0},status={'SourceGravityIdle4086_Status',3},world={'VmSourceWorld_Ready',0},tick={'SourceWorldTick4086_Ready',0},state={'SourceWorldTick4086_State',3},phase={'SourceWorldTick4086_Phase',10},pending={'SourceWorldTick4086_Pending',0},tickfault={'SourceWorldTick4086_Fault',1},count={'VmSourceWorld_Count',0},slot={'SourceWorldTick4086_Slot',128},time={'SourceWorldTick4086_TimeLo',(c.time+1)&0xffff},self={'SourceSelf4086_GlobalLow',0},selffault={'SourceSelf4086_Fault',1},selfactive={'SourceSelf4086_Active',1},freeze={'SourceFreeze4086_Ready',0},aux={'SourceUpdateFrame4086_Ready',0},platform={'SourceEmptyInitEnvironment4086_Ready',0},walls={'SourceEnvironment4086_WallCount',1},stage={'SourceEnvironment4086_Stage',2}}
 if faults[c.bad]then local f=faults[c.bad];set(f[1],f[2])end
 if c.bad=='noadjust'then put(0x40c024+s*96,0,4)elseif c.bad=='vertical'then put(side+44,65536,4)elseif c.bad=='altitude'then put(v+12,(c.altitude+1)*65536,4)elseif c.bad=='tosslease'then set('SourceToss4086_Ready',0)elseif c.bad=='corelease'then set('SourceModelEntityCopy4086_Ready',0)elseif c.bad=='corecount'then set('SourceModelEntityCopy4086_Entities',127)elseif c.bad=='atag'then put(v+8,1)elseif c.bad=='areserved'then put(v+10,1)elseif c.bad=='trymove'then put(life+4,1,4)elseif c.bad=='lifelease'then put(life+74,0)elseif c.bad=='modelrange'then put(side,1)elseif c.bad=='modelidentity'then put(life+72,1)elseif c.bad=='xtag'then put(v+48,1)elseif c.bad=='zreserved'then put(v+58,1)elseif c.bad=='token'then put(v,0,4)elseif c.bad=='exists'then put(v+4,0,4)end
 before={};for _,r in ipairs({{0x41f300,512},{0x414000,18432},{0x41f500,2560},{0x42e000,5120},{0x42d800,2048},{0x439000,10240},{0x40c000,12288},{sy.SourceWorldTick4086_Ready,52},{sy.SourceSelf4086_GlobalLow,4}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for altitude,base in ((93*65536,0),(100*65536,34*65536),(6554,0),(0,0)):
      for mark in (0,4,8,12):
       for freeze in (0,1):
        for time,toss in ((48,0),(48,49),(0xffffffff,0xffffffff)):
         et=toss;em=mark
         if not em&8:
          if not freeze and toss<=time:et=(time+1)&0xffffffff
          em|=8
         rows.append(dict(slot=(0,1,63,127)[len(rows)%4],mark=mark,freeze=freeze,time=time,toss_time=toss,a=altitude,base=base,gravity=0,altitude=0,nextmove=0,x=5242880,z=14417920,mx=0,mz=0,bad='',fault=0,expected=[et,em]))
    seed=dict(rows[0],mark=0,freeze=0,time=48,toss_time=0,a=93*65536,base=0)
    for change in (dict(a=6553),dict(a=65536,base=131072),dict(a=0x7fffffff,base=0x80000000),dict(gravity=1),dict(bad='vertical'),dict(bad='noadjust'),dict(bad='atag'),dict(bad='areserved'),dict(bad='tosslease'),dict(bad='phase'),dict(bad='platform'),dict(bad='stage')):
        rows.append(dict(seed,**change,fault=1,expected=[0,0]))
    rows.append(dict(seed,physics_ready=0xb61c,expected=[49,8]))
    for change in (dict(falling=1),dict(falling=65536),dict(hithead=0x414000),dict(landed_platform=0x414050),dict(physics_ready=0xb61d)):
        rows.append(dict(seed,physics_ready=0xb61c,fault=1,expected=[0,0])|change)
    rows=[dict(c,world_state=state)for state in (1,2)for c in rows]
    reporter=Reporter('M4-GRAVITY-HOVER',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceGravityIdle4086_Execute','SourceGravityIdle4086_Ready',0xb619,[],LUA,reporter,batch_size=2)
    actual=[list(map(int,line.split('GRAVITYIDLE|',1)[1].split('|')))for line in log.splitlines()if 'GRAVITYIDLE|'in line]
    expected=[[i,0,0,3 if c['fault']else 2,*c['expected']]for i,c in enumerate(rows)]
    failures=[dict(index=i,input=rows[i],actual=v,expected=w)for i,(v,w)in enumerate(zip(actual,expected))if v!=w]
    reporter.check('non-gravitating hover preserves all physical source actor fields except source clocks/marks; CPU and landing/overflow/type/stage guards',len(actual)==len(rows)and not failures)
    r=dict(schema='BYOR_4086_GRAVITY_HOVER_NATIVE_V1',status='PASS'if not failures and len(actual)==len(rows)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures,rom_sha256=hashlib.sha256(raw).hexdigest(),world_installer_bound=False,source_effect_constructor_bound=False,active_gravity_or_landing_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
