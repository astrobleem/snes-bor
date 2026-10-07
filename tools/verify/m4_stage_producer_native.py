"""Native queue loop up to its constructor request; no simulated combat claim."""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_stage_queue_4086 import derive,pack,unpack
from source_model_registry import derive as registry
from source_stage_dispatch_4086 import dispatch
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

class Request(Exception):pass

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function set(k,v,n)put(sy[k],v,n)end
local before={};local cpu={};local ctx=0;local returned=0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for i=0,127 do put(0x414004+i*80,i<c.enemies and 1 or 0,4);put(0x40c048+i*96,i<c.enemies and 2 or 0,4)end
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Level',1);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_TemplateCount',MODELS);set('VmSourceWorld_Time',48,4);set('VmSourceWorld_AdvanceX',0,4);set('VmSourceWorld_AdvanceY',0,4);set('VmSourceWorld_ScrollAxis',0)
 set('SourceEnvironment4086_Ready',0xb4d1);set('SourceEnvironment4086_Stage',c.stage)
 set('SourceStageQueue4086_Ready',0xb5d2);set('SourceStageQueue4086_Status',0);set('SourceStageQueue4086_Base',0x8000);set('SourceStageQueue4086_Bank',59);set('SourceStageQueue4086_Records',RECORDS);set('SourceStageQueue4086_Stages',STAGES);set('SourceStageQueue4086_Bytes',TABLEBYTES);set('SourceStageQueue4086_Stage',c.stage);set('SourceStageQueue4086_Index',c.index)
 set('SourceStageProducer4086_Ready',0xb5d6);set('SourceStageProducer4086_State',c.state);set('SourceStageProducer4086_First',c.first);set('SourceStageProducer4086_Limit',c.limit);set('SourceStageProducer4086_GroupMin',c.minimum,4);set('SourceStageProducer4086_GroupMax',c.maximum,4);set('SourceStageProducer4086_Position',c.pos,4);set('SourceStageProducer4086_Completed',c.completed);set('SourceStageProducer4086_Waiting',0);set('SourceStageProducer4086_GoTime',77,4);set('SourceStageProducer4086_Time',48,4)
 set('SourceCtorOwner4086_Phase',2);set('SourceSmartSpawn4086_Status',2)
 if c.bad=='ready'then set('SourceStageProducer4086_Ready',0)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='queue'then set('SourceStageQueue4086_Ready',0)
 elseif c.bad=='stage'then set('SourceEnvironment4086_Stage',0)
 elseif c.bad=='ctor'then set('SourceCtorOwner4086_Phase',1)
 elseif c.bad=='music'then set('SourceSmartSpawn4086_Status',1)
 elseif c.bad=='time'then set('SourceStageProducer4086_Time',47,4)end
 before={};for _,r in ipairs({{0x414000,10240},{0x40c000,12288}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();returned=s['cpu.a'];ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('PRODUCER|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(sy.SourceStageProducer4086_State)..'|'..word(sy.SourceStageQueue4086_Index)..'|'..dw(sy.SourceStageProducer4086_GroupMin)..'|'..dw(sy.SourceStageProducer4086_GroupMax)..'|'..word(sy.SourceStageProducer4086_Waiting)..'|'..dw(sy.SourceStageProducer4086_GoTime)..'|'..returned)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    source=Source(a.source);models=len(registry(source)['models']);report=derive(source);table=pack(report);unpack(table,models);rows=[];first=0
    for stage in report['stages']:
        records=stage['records'];limit=first+len(records)
        for localindex in range(len(records)+1):
            at=records[localindex]['at']if localindex<len(records)else 0
            for enemies in (0,3):
                for offset in (-1,0):
                    c=dict(stage=stage['stage_id'],first=first,limit=limit,index=first+localindex,pos=at+offset,enemies=enemies,minimum=100,maximum=100,state=0,completed=0,bad='',fault=0)
                    s=dict(index=localindex,groupmin=100,groupmax=100,pos=c['pos'],waiting=0,go_time=77,completed=0,time=48,advancetime=47,freezeall=0,players=[None]*4,leveltype=0)
                    requested=False
                    def spawn(row,pool):raise Request()
                    try:dispatch(s,records,[dict(exists=1,type=2,dead=0)]*enemies,spawn)
                    except Request:requested=True
                    c['expected']=[1 if requested else 4,first+s['index'],s['groupmin'],s['groupmax'],s['waiting'],s['go_time'],int(requested)]
                    rows.append(c)
        first=limit
    base=copy.deepcopy(rows[1])
    for bad in ('ready','world','queue','stage','ctor','music'):
        c=dict(base,bad=bad,fault=1);rows.append(c)
    for state in (1,3,5,65535):rows.append(dict(base,state=state,fault=1))
    rows.append(dict(base,state=2,bad='time',fault=1))
    for field,value in (('first',base['limit']),('limit',len(unpack(table,models))+1),('index',65535),('minimum',0),('minimum',-1),('maximum',0),('maximum',-1),('completed',2)):
        c=dict(base,fault=1);c[field]=value;rows.append(c)
    sy=symbols(Path('src/main.sym'));lua=LUA
    for k,v in dict(MODELS=models,RECORDS=sum(len(s['records'])for s in report['stages']),STAGES=len(report['stages']),TABLEBYTES=len(table)).items():lua=lua.replace(k,str(v))
    entry=sy['SourceStageProducer4086_Next'];lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-STAGE-PRODUCER',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceStageProducer4086_Next','SourceStageProducer4086_Ready',0xb5d6,[(59,0,table)],lua,r,batch_size=2)
    results=[list(map(int,line.split('PRODUCER|',1)[1].split('|')))for line in log.splitlines()if 'PRODUCER|'in line]
    r.check('source queue branch, wait/group semantics, signed positions, pool counts, constructor handoff and CPU/entity guards',len(results)==len(rows)and all(v[:3]==[i,0,0]and(v[3]==3 if c['fault']else v[3:]==c['expected'])for i,(v,c)in enumerate(zip(results,rows))))
    d=dict(schema='BYOR_4086_STAGE_PRODUCER_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,rom_sha256=hashlib.sha256(raw).hexdigest(),constructor_handoff_only=True,constructor_ack_bound=False,time_freeze_prefix_bound=False,camera_completion_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
