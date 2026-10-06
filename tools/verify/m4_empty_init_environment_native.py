"""Native closed no-platform/empty-wall initialization query and clock guard."""
import argparse,hashlib,json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function set(k,v)put(sy[k],v)end
local ranges={{0x409000,24576},{0x414000,18432},{0x439000,16384}}
local before,cpu,start,ctx={},{},0,0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,165,mt)end end
 for _,p in ipairs({'SourceUpdateFrame','SourceAnimationInit','SourceFrameStack','SourceModelAnimation','SourceModelTransition','SourceFrameEffectPlan','SourceSelf','SourceWorldTick'})do set(p..'4086_Ready',0)end
 set('SourceClock4086_Ready',0xb4c5);set('SourceClock4086_Due',1);set('SourceClock4086_TimeLo',48);set('SourceClock4086_TimeHi',0);set('SourceClock4086_Fault',0)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Level',1);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_Count',c.count);set('VmSourceWorld_TemplateCount',c.models)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',c.count);set('SourceModelEntityCopy4086_Models',c.models)
 set('SourceEnvironment4086_Ready',0xb4d1);set('SourceEnvironment4086_WallCount',0);set('SourceEnvironment4086_Stage',c.stage)
 for k,v in pairs({Ready=0xb504,Models=c.models,Stage=c.stage,Status=0,PlatformLo=0xa5a5,PlatformHi=0xa5a5,WallIndex=0xa5a5})do set('SourceEmptyInitEnvironment4086_'..k,v)end
 if c.bad=='ready'then set('SourceEmptyInitEnvironment4086_Ready',0xffff)
 elseif c.bad=='sticky'then set('SourceEmptyInitEnvironment4086_Status',3)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='level'then set('VmSourceWorld_Level',0)
 elseif c.bad=='count_zero'then set('VmSourceWorld_Count',0)
 elseif c.bad=='count'then set('VmSourceWorld_Count',129)
 elseif c.bad=='pool'then set('VmSourceWorld_PoolBase',0x4002)
 elseif c.bad=='core'then set('SourceModelEntityCopy4086_Ready',0)
 elseif c.bad=='entities'then set('SourceModelEntityCopy4086_Entities',0)
 elseif c.bad=='models_zero'then set('SourceEmptyInitEnvironment4086_Models',0)
 elseif c.bad=='models'then set('SourceEmptyInitEnvironment4086_Models',17)
 elseif c.bad=='paired_core'then set('SourceModelEntityCopy4086_Models',0)
 elseif c.bad=='paired_world'then set('VmSourceWorld_TemplateCount',0)
 elseif c.bad=='environment'then set('SourceEnvironment4086_Ready',0)
 elseif c.bad=='walls'then set('SourceEnvironment4086_WallCount',1)
 elseif c.bad=='stage_zero'then set('SourceEmptyInitEnvironment4086_Stage',0)
 elseif c.bad=='stage'then set('SourceEnvironment4086_Stage',0)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 local state=emu.getState();start=state.masterClock;cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=state['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local state=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=state['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp~=state['cpu.sp']or(cpu.ps&254)~=(state['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('EMPTYCOST|'..word(INDEX)..'|'..(state.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local mismatch=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then mismatch=mismatch+1 end end
 emu.log('EMPTYRESULT|'..word(INDEX)..'|'..mismatch..'|'..ctx..'|'..word(sy.SourceEmptyInitEnvironment4086_Status)..'|'..word(sy.SourceEmptyInitEnvironment4086_PlatformLo)..'|'..word(sy.SourceEmptyInitEnvironment4086_PlatformHi)..'|'..word(sy.SourceEmptyInitEnvironment4086_WallIndex))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('EMPTYCLOCK|'..word(INDEX)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault))end,emu.callbackType.exec,POSTRESULT,POSTRESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--source-report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());source=json.loads(a.source_report.read_text());assert authority['status']=='PASS'and source['platform_query_admitted']and all(s['admitted']for s in source['stages'])
 rows=[dict(count=c,models=m,stage=s,fault=0,bad='')for c in (1,128)for m in (1,16)for s in (1,2)]
 for bad in ('ready','sticky','world','level','count_zero','count','pool','core','entities','models_zero','models','paired_core','paired_world','environment','walls','stage_zero','stage'):
  for count in (1,128):rows.append(dict(count=count,models=16,stage=1,fault=1,bad=bad))
 reporter=Reporter('M4-EMPTY-INIT-ENVIRONMENT',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceEmptyInitEnvironment4086_Query','SourceEmptyInitEnvironment4086_Ready',0xb504,[],LUA,reporter,post='SourceClock4086_Commit');results=[];costs=[];clocks=[]
 for line in log.splitlines():
  for marker,target in [('EMPTYRESULT|',results),('EMPTYCOST|',costs),('EMPTYCLOCK|',clocks)]:
   if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
 reporter.check('NULL platform and -1 wall index, or reject before output/physical writes; preserved CPU',len(results)==len(rows)and all(r==[i,0,0,3 if c['fault']else 2,*([0xa5a5]*3 if c['fault']else[0,0,65535])]for i,(r,c)in enumerate(zip(results,rows))))
 reporter.check('empty environment faults block source clock retirement',len(clocks)==len(rows)and all(r==([i,1,48,1]if c['fault']else[i,0,49,0])for i,(r,c)in enumerate(zip(clocks,rows))))
 r=dict(schema='BYOR_4086_EMPTY_INIT_ENVIRONMENT_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),source_report_sha256=hashlib.sha256(a.source_report.read_bytes()).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),cases=len(rows),inputs=rows,results=results,costs=costs,clocks=clocks,lease_installation_instrumented=True,closed_registry_native_world_publication_bound=False,full_default_init_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
