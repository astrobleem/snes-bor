"""Prevent retiring a source world tick with unfinished stage queue services."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function set(k,v,n)put(sy[k],v,n)end
local cpu={};local ctx=0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,name in ipairs({'SourceWorldTick4086_Ready','SourceUpdateFrame4086_Ready','SourceAnimationInit4086_Ready','SourceFrameStack4086_Ready','SourceModelAnimation4086_Ready','SourceModelTransition4086_Ready','SourceFrameEffectPlan4086_Ready','SourceSelf4086_Ready','SourceRetirement4086_Ready','SourceBirthCore4086_Ready','SourceLifecycle4086_Ready','SourceEmptyInitEnvironment4086_Ready','SourcePlayerSpawnHeight4086_Ready'})do set(name,0)end
 set('SourceClock4086_Ready',0xb4c5);set('SourceClock4086_Due',1);set('SourceClock4086_TimeLo',c.time,4);set('SourceClock4086_Fault',0)
 set('SourceStageProducer4086_Ready',c.ready);set('SourceStageProducer4086_State',c.state);set('SourceCtorOwner4086_Phase',c.ctor);set('SourceDefaultInit4086_Phase',c.default);set('SourceSmartSpawn4086_Status',c.properties)
 set('SourceWait4086_Ready',c.wait_ready);set('SourceWait4086_Status',c.wait_status)
 set('SourceCameraMotion4086_Ready',c.camera_ready);set('SourceCameraMotion4086_Status',c.camera_status)
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 emu.log('QUEUECLOCK|'..word(INDEX)..'|'..ctx..'|'..word(sy.SourceClock4086_Due)..'|'..dw(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for ready,state,time in itertools.product((0,0xb5d6,65535),(0,1,2,3,4,65535),(48,0xffffffff)):
        rows.append(dict(ready=ready,state=state,ctor=2,default=6,properties=2,time=time,fault=int(ready!=0 and(ready!=0xb5d6 or state!=4))))
    for ctor,default,properties in itertools.product((0,1,2,3,65535),(0,1,6,7,65535),(0,1,2,3,65535)):
        rows.append(dict(ready=0xb5d6,state=4,ctor=ctor,default=default,properties=properties,time=48,fault=int(ctor not in (0,2)or default not in (0,6)or properties not in (0,2))))
    for row in rows:row.update(wait_ready=0,wait_status=0)
    for ready,status,time in itertools.product((0,0xb5d9,65535),(0,1,2,3,65535),(48,0xffffffff)):
        rows.append(dict(ready=0xb5d6,state=4,ctor=2,default=6,properties=2,time=time,wait_ready=ready,wait_status=status,fault=int(ready!=0 and(ready!=0xb5d9 or status!=2))))
    for row in rows:row.update(camera_ready=0,camera_status=0)
    for ready,status,time in itertools.product((0,0xb5db,65535),(0,1,2,3,65535),(48,0xffffffff)):
        rows.append(dict(ready=0xb5d6,state=4,ctor=2,default=6,properties=2,time=time,wait_ready=0xb5d9,wait_status=2,camera_ready=ready,camera_status=status,fault=int(ready!=0 and(ready!=0xb5db or status!=2))))
    for wait_ready,camera_ready,status in itertools.product((0xb5d9,65535),(0xb5db,65535),(0,1,2,3,65535)):
        rows.append(dict(ready=0,state=65535,ctor=65535,default=65535,properties=65535,time=48,wait_ready=wait_ready,wait_status=status,camera_ready=camera_ready,camera_status=status,fault=0))
    sy=symbols(Path('src/main.sym'));entry=sy['SourceClock4086_Commit'];lua=LUA+f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-STAGE-CLOCK-GATE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceClock4086_Commit','SourceClock4086_Ready',0xb4c5,[],lua,r,batch_size=2)
    results=[list(map(int,line.split('QUEUECLOCK|',1)[1].split('|')))for line in log.splitlines()if 'QUEUECLOCK|'in line]
    r.check('disabled queue preserves clock; live queue/constructor/default/properties/music must complete before tick retirement',len(results)==len(rows)and all(v==[i,0,1 if c['fault']else 0,c['time']if c['fault']else(c['time']+1)&0xffffffff,c['fault']]for i,(v,c)in enumerate(zip(results,rows))))
    d=dict(schema='BYOR_4086_STAGE_CLOCK_GATE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,rom_sha256=hashlib.sha256(raw).hexdigest(),owner_completion_controls_instrumented=True,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
