"""Native full signed product and checked source movement accumulator backend."""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_velocity_4086 import native
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA = r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function set(k,v,n)put(sy[k],v,n)end
local before={};local cpu={};local ctx=0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 set('SourceVelocity4086_Ready',0xb5de);set('SourceVelocity4086_Status',0)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',10);set('SourceWorldTick4086_Slot',c.slot)
 set('SourceUpdateFrame4086_Ready',0xb4e3)
 local a=0x41f500+c.slot*20;local s=0x416800+c.slot*64
 put(a,c.values[1],4);put(a+4,c.values[2],4);put(s+36,c.values[3],4);put(s+40,c.values[4],4);put(s+32,c.values[5],4)
 if c.bad=='ready'then set('SourceVelocity4086_Ready',0)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='tick'then set('SourceWorldTick4086_Ready',0)
 elseif c.bad=='pending'then set('SourceWorldTick4086_Pending',0)
 elseif c.bad=='phase'then set('SourceWorldTick4086_Phase',9)
 elseif c.bad=='repeat'then set('SourceVelocity4086_Status',2)
 elseif c.bad=='state'then set('SourceWorldTick4086_State',4)
 elseif c.bad=='pool'then set('VmSourceWorld_PoolBase',0x4002)
 elseif c.bad=='side'then set('VmSourceWorld_SideBase',0x6802)
 elseif c.bad=='aux'then set('SourceUpdateFrame4086_Ready',0)
 elseif c.bad=='count'then set('VmSourceWorld_Count',0)
 elseif c.bad=='count_high'then set('VmSourceWorld_Count',129)
 elseif c.bad=='slot'then set('SourceWorldTick4086_Slot',128)end
 before={};for _,r in ipairs({{0x416800,8192},{0x41f500,2560},{sy.SourceWorldTick4086_Ready,52}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local a=0x41f500+c.slot*20;local changed=0
 for address,value in pairs(before)do if (c.fault==1 or address<a or address>=a+8)and emu.read(address,mt)~=value then changed=changed+1 end end
 emu.log('VELOCITY|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceVelocity4086_Status)..'|'..dw(a)..'|'..dw(a+4))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
    inputs=authority['inputs'][::7];rng=random.Random(408611)
    inputs += [[rng.randint(-0x80000000,0x7fffffff) for _ in range(5)] for _ in range(128)]
    inputs += [[0x7fffffff,0,65536,0,65536],[-0x80000000,0,-65536,0,65536],
               [0,-0x80000000,0,-65536,65536],[0,0,-0x80000000,-0x80000000,-0x80000000],
               [-0x80000000,0,0x7fffffff,0,131073]]
    rows=[]
    for i,v in enumerate(inputs):
        try: expected=native(*v);fault=0
        except ValueError: expected=v[:2];fault=1
        rows.append(dict(values=v,expected=[n&0xffffffff for n in expected],fault=fault,bad='',slot=(0,1,63,127)[i%4]))
    for bad in ('ready','world','tick','pending','phase','repeat','state','pool','side','aux','count','count_high','slot'):
        rows.append(dict(values=[123,-456,65536,-65536,65536],expected=[123,(-456)&0xffffffff],fault=1,bad=bad,slot=127))
    sy=symbols(Path('src/main.sym'));entry=sy['SourceVelocity4086_Apply']
    lua=LUA+f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-VELOCITY',kind='GATE')
    rom,log=run_fixture(a.rom,a.output,rows,'SourceVelocity4086_Apply','SourceVelocity4086_Ready',0xb5de,[],lua,r,batch_size=2)
    results=[list(map(int,line.split('VELOCITY|',1)[1].split('|')))for line in log.splitlines()if 'VELOCITY|'in line]
    failures=[dict(index=i,input=c,actual=v)for i,(c,v)in enumerate(zip(rows,results))if v != [i,0,0,3 if c['fault']else 2,*c['expected']]]
    r.check('signed full product, cancellation, both-axis overflow guards, readonly siblings/tick state and CPU',len(results)==len(rows)and not failures)
    d=dict(schema='BYOR_4086_VELOCITY_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],
           rom_sha256=hashlib.sha256(rom).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),
           numeric_policy=authority['numeric_policy'],world_service_acknowledged=False,collision_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()


if __name__=='__main__':main()
