"""Native source-derived spawn-row preparation; live dispatch is unbound."""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_stage_queue_4086 import derive,pack,unpack
from source_model_registry import derive as registry
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function set(k,v)put(sy[k],v)end
local ranges={{0x414000,18432},{0x409000,24576},{0x432800,12288},{0x439000,10240}}
local outputs={sy.SourceSpawnSlot4086_Model,sy.SourceCtorState4086_X,sy.SourceCtorState4086_Z,sy.SourceCtorState4086_A,sy.SourceCtorState4086_Direction,sy.SourceCtorState4086_Time,sy.SourceDefaultChoice4086_TimeLo,sy.SourceDefaultPlayer4086_TimeLo,sy.SourceDefaultChoice4086_Select}
local before,cpu,ctx={}, {},0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,(i*37+131)&255,mt)end end
 for _,a in ipairs(outputs)do put(a,0x5a5a,4)end
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Level',1);set('VmSourceWorld_TemplateCount',MODELS)
 put(sy.VmSourceWorld_AdvanceX,c.advancex,4);put(sy.VmSourceWorld_AdvanceY,c.advancey,4);put(sy.VmSourceWorld_Time,c.time,4);set('VmSourceWorld_ScrollAxis',c.axis)
 set('SourceEnvironment4086_Ready',0xb4d1);set('SourceEnvironment4086_Stage',c.stage)
 set('SourceStageQueue4086_Ready',0xb5d2);set('SourceStageQueue4086_Status',c.status)
 set('SourceStageQueue4086_Base',c.base);set('SourceStageQueue4086_Bank',c.bank);set('SourceStageQueue4086_Bytes',TABLEBYTES);set('SourceStageQueue4086_Records',RECORDS);set('SourceStageQueue4086_Stages',STAGES);set('SourceStageQueue4086_Index',c.index);set('SourceStageQueue4086_Stage',c.stage)
 if c.bad=='ready'then set('SourceStageQueue4086_Ready',0)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='level'then set('VmSourceWorld_Level',c.value)
 elseif c.bad=='base'then set('SourceStageQueue4086_Base',c.value)
 elseif c.bad=='bank'then set('SourceStageQueue4086_Bank',c.value)
 elseif c.bad=='bytes'then set('SourceStageQueue4086_Bytes',c.value)
 elseif c.bad=='records'then set('SourceStageQueue4086_Records',c.value)
 elseif c.bad=='stages'then set('SourceStageQueue4086_Stages',c.value)
 elseif c.bad=='stage'then set('SourceStageQueue4086_Stage',c.value)
 elseif c.bad=='index'then set('SourceStageQueue4086_Index',c.value)
 elseif c.bad=='environment'then set('SourceEnvironment4086_Ready',0)
 elseif c.bad=='stage_pair'then set('SourceEnvironment4086_Stage',c.stage+1)
 elseif c.bad=='model_count'then set('VmSourceWorld_TemplateCount',0)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 for _,a in ipairs(outputs)do for i=0,3 do before[a+i]=emu.read(a+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 local function expect(a,v,n)for i=0,(n or 4)-1 do before[a+i]=(v>>(8*i))&255 end end
 if c.fault==0 then
  expect(sy.SourceSpawnSlot4086_Model,c.model,2);expect(sy.SourceCtorState4086_X,c.x);expect(sy.SourceCtorState4086_Z,c.z);expect(sy.SourceCtorState4086_A,c.a);expect(sy.SourceCtorState4086_Direction,c.direction);expect(sy.SourceCtorState4086_Time,c.time);expect(sy.SourceDefaultChoice4086_TimeLo,c.time);expect(sy.SourceDefaultPlayer4086_TimeLo,c.time);expect(sy.SourceDefaultChoice4086_Select,0,2)
 end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('STAGEQUEUE|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(sy.SourceStageQueue4086_Status)..'|'..word(sy.SourceSpawnSlot4086_Model)..'|'..dw(sy.SourceCtorState4086_X)..'|'..dw(sy.SourceCtorState4086_Z)..'|'..dw(sy.SourceCtorState4086_A)..'|'..dw(sy.SourceCtorState4086_Direction)..'|'..dw(sy.SourceCtorState4086_Time))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--validate-only',action='store_true');p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    source=Source(a.source);model_count=len(registry(source)['models']);report=derive(source);table=pack(report);records=unpack(table,model_count);rows=[]
    def case(index,axis=0,advance=0,time=0,**extra):
        r=records[index];x,z,height=r['coords_q16'];advancex=advance if axis==0 else 0;advancey=advance if axis==1 else 0
        return dict(index=index,stage=r['stage_id'],axis=axis,advancex=advancex,advancey=advancey,time=time,base=0x8000,bank=59,status=0,bad='',value=0,fault=0,model=r['model'],x=(x+advancex)&0xffffffff,z=(z+advancey)&0xffffffff,a=height&0xffffffff,direction=r['flip']&0xffffffff,**extra)
    for index,r in enumerate(records):
        if r['kind']=='spawn':
            for axis,advance,time in ((0,0,0),(0,15*65536,0xffffffff),(1,-17*65536,48),(0,7*65536+16384,49)):rows.append(case(index,axis,advance,time))
        else:
            c=case(index);c['fault']=1;rows.append(c)
    first=next(i for i,r in enumerate(records)if r['kind']=='spawn')
    for bad,values in {'ready':[0],'world':[0],'level':[0,2],'base':[0x7fff,0xffff],'bank':[0,64],'bytes':[23,len(table)+1],'records':[0,256,len(records)-1],'stages':[0,3],'stage':[0,3],'index':[len(records),65535],'environment':[0],'stage_pair':[0],'model_count':[0]}.items():
        for value in values:
            c=case(first);c.update(bad=bad,value=value,fault=1);rows.append(c)
    for status in (1,3,4,65535):
        c=case(first);c.update(status=status,fault=1);rows.append(c)
    for axis in (0,1):
        c=case(first,axis,0x7fffffff);c['fault']=1;rows.append(c)
    last_negative=next(i for i,r in enumerate(records)if r['kind']=='spawn'and r['coords'][0]<0)
    c=case(last_negative,0,-2147483648);c['fault']=1;rows.append(c)
    if a.validate_only:
        for c in rows:
            if c['bad']==''and c['status']==0:c['fault']=0
    tables=[(59,0,table)]
    # Corrupt distinct immutable headers/body identities in reserved private ROM.
    for i,(at,value)in enumerate(((0,0),(4,2),(6,64),(8,len(records)-1),(14,1),(20,1),(24+first*128+4,model_count))):
        data=bytearray(table);struct.pack_into('<H',data,at,value);start=i*len(table);tables.append((60,start,bytes(data)))
        c=case(first);c.update(base=0x8000+start,bank=60,fault=1);rows.append(c)
    sy=symbols(Path('src/main.sym'));lua=LUA.replace('if c.fault==0 then','if false then')if a.validate_only else LUA
    for k,v in dict(MODELS=model_count,TABLEBYTES=len(table),RECORDS=len(records),STAGES=len(report['stages'])).items():lua=lua.replace(k,str(v))
    apply='SourceStageQueue4086_ValidateCurrentRow'if a.validate_only else'SourceStageQueue4086_PrepareSpawn'
    entry=sy[apply];lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-STAGE-QUEUE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,apply,'SourceStageQueue4086_Ready',0xb5d2,tables,lua,r,batch_size=2)
    results=[list(map(int,line.split('STAGEQUEUE|',1)[1].split('|')))for line in log.splitlines()if 'STAGEQUEUE|'in line]
    r.check('all source spawns, paired stages/time/coordinates, signed advances/overflow, immutable headers and admission guards preserve entities and CPU context',len(results)==len(rows)and all(v[:4]==[i,0,0,3 if c['fault']else 2]for i,(v,c)in enumerate(zip(results,rows))))
    d=dict(schema='BYOR_4086_STAGE_QUEUE_PREPARE_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),cases=len(rows),validate_only=a.validate_only,inputs=rows,results=results,source_spawn_records=sum(r['kind']=='spawn'for r in records),constructor_execution_bound=False,live_queue_dispatch_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
