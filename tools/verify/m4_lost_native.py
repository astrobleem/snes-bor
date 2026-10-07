"""Native check_lost planner paired with literal pinned C; deaths unexecuted."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function set(k,v,n)put(sy[k],v,n)end
local before={};local cpu={};local ctx=0;local returned=0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 set('SourceLost4086_Ready',0xb5e0);set('SourceLost4086_Status',0)
 set('SourceLost4086_OffscreenKill',c.offscreenkill,4);set('SourceLost4086_DefaultOffscreenKill',c.default_offscreenkill,4);set('SourceLost4086_Direction',c.direction,4);set('SourceLost4086_HRes',c.hres);set('SourceLost4086_VRes',c.vres)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Level',1);set('VmSourceWorld_Time',c.time,4);set('VmSourceWorld_AdvanceX',c.advancex*65536,4);set('VmSourceWorld_AdvanceY',c.advancey*65536,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',2);set('SourceWorldTick4086_Slot',c.slot);set('SourceWorldTick4086_TimeLo',c.time,4);set('SourceWorldTick4086_Frozen',55)
 set('SourceFreeze4086_Ready',0xb5df);set('SourceFreeze4086_Status',2);put(LIFEREADY,0xb4fb)
 local v=0x414000+c.slot*80;local s=0x416800+c.slot*64;local f=0x42e000+c.slot*40
 put(v,v,4);put(v+8,2,4);put(v+12,c.y*65536,4);put(v+48,2,4);put(v+52,c.x*65536,4);put(v+56,c.z==100000 and 1 or 2,4);put(v+60,c.z==100000 and 100000 or c.z*65536,4);put(v+32,1,4);put(v+36,c.health,4)
 put(s+16,c.lifespan,4);put(0x40c048+c.slot*96,c.type,4);put(0x439004+c.slot*80,c.takedamage,4);put(f,c.frozen,4);put(f+4,c.freezetime,4)
 put(0x43fd98,c.textbox==1 and 0x414000 or 0,4);put(0x43fd94,c.bomber==1 and v or c.bomber==2 and (v==0x414000 and 0x414050 or 0x414000) or 0,4)
 if c.bad=='ready'then set('SourceLost4086_Ready',0)
 elseif c.bad=='repeat'then set('SourceLost4086_Status',2)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='pool'then set('VmSourceWorld_PoolBase',0x4002)
 elseif c.bad=='side'then set('VmSourceWorld_SideBase',0x6802)
 elseif c.bad=='tick'then set('SourceWorldTick4086_Ready',0)
 elseif c.bad=='pending'then set('SourceWorldTick4086_Pending',0)
 elseif c.bad=='state'then set('SourceWorldTick4086_State',4)
 elseif c.bad=='phase'then set('SourceWorldTick4086_Phase',3)
 elseif c.bad=='time'then set('SourceWorldTick4086_TimeLo',(c.time+1)&0xffffffff,4)
 elseif c.bad=='level'then set('VmSourceWorld_Level',0)
 elseif c.bad=='count'then set('VmSourceWorld_Count',0)
 elseif c.bad=='count_high'then set('VmSourceWorld_Count',129)
 elseif c.bad=='slot'then set('SourceWorldTick4086_Slot',128)
 elseif c.bad=='life'then put(LIFEREADY,0)
 elseif c.bad=='freeze'then set('SourceFreeze4086_Ready',0)
 elseif c.bad=='hres'then set('SourceLost4086_HRes',0)
 elseif c.bad=='vres'then set('SourceLost4086_VRes',32768)
 elseif c.bad=='x_tag'then put(v+48,1,4)
 elseif c.bad=='y_tag'then put(v+8,0,4)
 elseif c.bad=='z_tag'then put(v+56,3,4)
 elseif c.bad=='park_low'then put(v+56,1,4);put(v+60,100001,4)
 elseif c.bad=='park_high'then put(v+56,1,4);put(v+60,0x286a0,4)
 elseif c.bad=='health_tag'then put(v+32,2,4)end
 before={};for _,r in ipairs({{0x414000,10240},{0x416800,8192},{0x40c000,12288},{0x439000,10240},{0x42e000,5120},{sy.SourceWorldTick4086_Ready,52},{0x43fd94,8},{sy.SourceFreeze4086_Ready,4}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 if c.fault==0 then for i=0,3 do before[s+16+i]=(c.expected.lifespan>>(8*i))&255 end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();returned=s['cpu.a'];ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local changed=0;for address,value in pairs(before)do if emu.read(address,mt)~=value then changed=changed+1 end end
 emu.log('LOST|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceLost4086_Status)..'|'..returned..'|'..dw(sy.SourceLost4086_Force)..'|'..word(sy.SourceLost4086_AttackType))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS';rows=[]
    indices=list(range(0,2550,5))+list(range(2550,len(authority['inputs'])))
    for i,n in enumerate(indices):rows.append(dict(authority['inputs'][n],expected=authority['actual'][n],slot=(0,1,63,127)[i%4],fault=0,bad=''))
    base=next(c for c in rows if c['expected']['action']==3)
    for bad in ('ready','repeat','world','pool','side','tick','pending','state','phase','time','level','count','count_high','slot','life','freeze','hres','vres','x_tag','y_tag','z_tag','park_low','park_high','health_tag'):
        rows.append(dict(base,fault=1,bad=bad))
    sy=symbols(Path('src/main.sym'));entry=sy['SourceLost4086_Begin']
    lua=LUA.replace('LIFEREADY',str(sy['SourceLifecycle4086_Ready']))+f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-LOST',kind='GATE');rom,log=run_fixture(a.rom,a.output,rows,'SourceLost4086_Begin','SourceLost4086_Ready',0xb5e0,[],lua,r,batch_size=2)
    results=[list(map(int,line.split('LOST|',1)[1].split('|')))for line in log.splitlines()if 'LOST|'in line];failures=[]
    for i,(c,v)in enumerate(zip(rows,results)):
        e=c['expected'];want=[i,0,0,1 if e['action']else 2,e['action'],e.get('attack_force',0)&0xffffffff,e.get('attack_type',0)]
        if (v[:4]!=[i,0,0,3] if c['fault'] else v!=want):failures.append(dict(index=i,input=c,result=v,expected=want))
    r.check('literal C decisions, signed wide comparisons, sentinel, countdown, CPU and full actor/role state',len(results)==len(rows)and not failures)
    report=dict(schema='BYOR_4086_LOST_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],rom_sha256=hashlib.sha256(rom).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),numeric_policy='ACCEPTED_COMPAT Q16 coordinates; signed 64-bit comparisons and exact signed integer offscreenkill; parked Z integer sentinel',death_damage_backend_bound=False,attack_drop_vector_bound=False,world_owner_integration_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()


if __name__=='__main__':main()
