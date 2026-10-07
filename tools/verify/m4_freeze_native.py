"""Native frozen predicate, unsigned timer expansion and update_mark reset."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_freeze_4086 import TIMERS, frozen, expand
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function set(k,v,n)put(sy[k],v,n)end
local addresses={};local before={};local cpu={};local ctx=0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 set('SourceFreeze4086_Ready',0xb5df);set('SourceFreeze4086_Status',0)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Time',c.time,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',c.phase);set('SourceWorldTick4086_Slot',c.slot);set('SourceWorldTick4086_TimeLo',c.time,4);set('SourceWorldTick4086_Frozen',55)
 set('SourceToss4086_Ready',0xb4e2);put(LIFEREADY,0xb4fb)
 local f=0x42e000+c.slot*40;local s=0x416800+c.slot*64;local v=0x414000+c.slot*80
 addresses={f+8,f+12,s+8,s+20,s+24,f+16,f+20,0x41f300+c.slot*4,f+4,f+24,0x439000+c.slot*80+32,f+28,f+32}
 put(v,v,4);put(0x40c048+c.slot*96,c.type,4);put(f,c.frozen,4);put(f+36,0x87654321,4)
 for i,address in ipairs(addresses)do put(address,c.timers[i],4)end
 put(0x43fd98,c.textbox==1 and 0x414000 or 0,4);put(0x43fd94,c.bomber==1 and v or c.bomber==2 and (v==0x414000 and 0x414050 or 0x414000) or 0,4)
 if c.bad=='ready'then set('SourceFreeze4086_Ready',0)
 elseif c.bad=='repeat'then set('SourceFreeze4086_Status',2)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='pool'then set('VmSourceWorld_PoolBase',0x4002)
 elseif c.bad=='side'then set('VmSourceWorld_SideBase',0x6802)
 elseif c.bad=='tick'then set('SourceWorldTick4086_Ready',0)
 elseif c.bad=='pending'then set('SourceWorldTick4086_Pending',0)
 elseif c.bad=='state'then set('SourceWorldTick4086_State',4)
 elseif c.bad=='phase'then set('SourceWorldTick4086_Phase',2)
 elseif c.bad=='time'then set('SourceWorldTick4086_TimeLo',(c.time+1)&0xffffffff,4)
 elseif c.bad=='count'then set('VmSourceWorld_Count',0)
 elseif c.bad=='count_high'then set('VmSourceWorld_Count',129)
 elseif c.bad=='slot'then set('SourceWorldTick4086_Slot',128)
 elseif c.bad=='life'then put(LIFEREADY,0)
 elseif c.bad=='toss'then set('SourceToss4086_Ready',0)end
 before={};for _,r in ipairs({{0x42e000,5120},{0x416800,8192},{0x439000,10240},{0x41f300,512},{sy.SourceWorldTick4086_Ready,52},{0x43fd94,8}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 if c.fault==0 then
  if c.phase==3 then put(0x7ffd8a,c.expected_frozen);for i=0,1 do before[sy.SourceWorldTick4086_Frozen+i]=(c.expected_frozen>>(8*i))&255 end
  elseif c.phase==1 then for i=0,3 do before[f+36+i]=0 end
  else for j,address in ipairs(addresses)do for i=0,3 do before[address+i]=(c.expected_timers[j]>>(8*i))&255 end end end
 end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local changed=0;for address,value in pairs(before)do if emu.read(address,mt)~=value then changed=changed+1 end end
 emu.log('FREEZE|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceFreeze4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
    inputs=[r for r in authority['inputs']if not r['self_other']];rows=[]
    for i,r in enumerate(inputs):
        for phase in (1,3,4):
            c=dict(r,phase=phase,slot=(0,1,63,127)[i%4],fault=0,bad='')
            ent=dict(token=1,type=r['type'],frozen=r['frozen'],**dict(zip(TIMERS,r['timers'])))
            c['expected_frozen']=int(frozen(ent,ent,textbox=r['textbox'],smartbomber=r['bomber'],time=r['time']))
            expand(ent,textbox=r['textbox'],smartbomber=r['bomber']);c['expected_timers']=[ent[n]for n in TIMERS];rows.append(c)
    for bad in ('ready','repeat','world','pool','side','tick','pending','state','phase','time','count','count_high','slot','life','toss'):
        rows.append(dict(rows[-1],fault=1,bad=bad))
    sy=symbols(Path('src/main.sym'));entry=sy['SourceFreeze4086_Execute']
    lua=LUA.replace('LIFEREADY',str(sy['SourceLifecycle4086_Ready']))+f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-FREEZE',kind='GATE');rom,log=run_fixture(a.rom,a.output,rows,'SourceFreeze4086_Execute','SourceFreeze4086_Ready',0xb5df,[],lua,r,batch_size=2)
    results=[list(map(int,line.split('FREEZE|',1)[1].split('|')))for line in log.splitlines()if 'FREEZE|'in line]
    failures=[dict(index=i,input=c,result=v)for i,(c,v)in enumerate(zip(rows,results))if v != [i,0,0,3 if c['fault']else 2]]
    r.check('literal frozen predicate, 13 unsigned timers, mark reset, full physical state and CPU preservation',len(results)==len(rows)and not failures)
    report=dict(schema='BYOR_4086_FREEZE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],rom_sha256=hashlib.sha256(rom).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),new_entity_state_bytes=5120,world_owner_integration_bound=False,constructor_initialization_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()


if __name__=='__main__':main()
