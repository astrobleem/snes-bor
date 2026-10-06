"""Native source player spawn heights and guard propagation, no constructor."""
import argparse,hashlib,json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''local mt=emu.memType.snesMemory
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
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Level',1);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_Count',128)
 set('SourceEnvironment4086_Ready',0xb4d1);set('SourceEnvironment4086_Stage',c.stage)
 for i=0,127 do put(0x414000+i*80,0x414000+i*80,4);put(0x414004+i*80,c.alive);put(0x414028+i*80,1,4);put(0x41402c+i*80,c.player,4)end
 set('SourcePlayerSpawnHeight4086_Ready',0xb505);set('SourcePlayerSpawnHeight4086_Stage',c.stage);set('SourcePlayerSpawnHeight4086_Status',0);set('SourcePlayerSpawnHeight4086_Slot',c.slot);set('SourcePlayerSpawnHeight4086_ValueLo',0xa5a5);set('SourcePlayerSpawnHeight4086_ValueHi',0xa5a5)
 for i=0,3 do put(sy.SourcePlayerSpawnHeight4086_Heights+i*4,c.heights[i+1]<<16,4)end
 if c.bad=='ready'then set('SourcePlayerSpawnHeight4086_Ready',0xffff)
 elseif c.bad=='sticky'then set('SourcePlayerSpawnHeight4086_Status',3)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='level'then set('VmSourceWorld_Level',0)
 elseif c.bad=='pool'then set('VmSourceWorld_PoolBase',0x4002)
 elseif c.bad=='count_zero'then set('VmSourceWorld_Count',0)
 elseif c.bad=='count'then set('VmSourceWorld_Count',129)
 elseif c.bad=='slot'then set('SourcePlayerSpawnHeight4086_Slot',128)
 elseif c.bad=='environment'then set('SourceEnvironment4086_Ready',0)
 elseif c.bad=='stage_zero'then set('SourcePlayerSpawnHeight4086_Stage',0)
 elseif c.bad=='stage'then set('SourceEnvironment4086_Stage',0)
 elseif c.bad=='token'then put(0x414000+c.slot*80,0)
 elseif c.bad=='token_high'then put(0x414002+c.slot*80,0)
 elseif c.bad=='tag'then put(0x414028+c.slot*80,2)
 elseif c.bad=='reserved'then put(0x41402a+c.slot*80,1)
 elseif c.bad=='player_high'then put(0x41402e+c.slot*80,1)
 elseif c.bad=='player_negative'then put(0x41402c+c.slot*80,0xffffffff,4)
 elseif c.bad=='player_bound'then put(0x41402c+c.slot*80,4,4)
 elseif c.bad=='fraction'then put(sy.SourcePlayerSpawnHeight4086_Heights+c.player*4,1)
 elseif c.bad=='negative_height'then put(sy.SourcePlayerSpawnHeight4086_Heights+c.player*4+2,0xffff)
 elseif c.bad=='large_height'then put(sy.SourcePlayerSpawnHeight4086_Heights+c.player*4+2,0x8000)end
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
 emu.log('EMPTYRESULT|'..word(INDEX)..'|'..mismatch..'|'..ctx..'|'..word(sy.SourcePlayerSpawnHeight4086_Status)..'|'..word(sy.SourcePlayerSpawnHeight4086_ValueLo)..'|'..word(sy.SourcePlayerSpawnHeight4086_ValueHi))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('EMPTYCLOCK|'..word(INDEX)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault))end,emu.callbackType.exec,POSTRESULT,POSTRESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--source-report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());source=json.loads(a.source_report.read_text());assert authority['status']=='PASS'and all(s['heights']==[300]*4 for s in source['stages']);values=[0,300,32767,4]
 rows=[dict(stage=stage,slot=slot,player=player,heights=values[shift:]+values[:shift],alive=alive,fault=0,bad='')for stage in (1,2)for slot in (0,1,127)for player in range(4)for shift in range(4)for alive in (0,1)]
 for bad in ('ready','sticky','world','level','pool','count_zero','count','slot','environment','stage_zero','stage','token','token_high','tag','reserved','player_high','player_negative','player_bound','fraction','negative_height','large_height'):
  for slot in (0,127):rows.append(dict(stage=1,slot=slot,player=1,heights=values,alive=1,fault=1,bad=bad))
 reporter=Reporter('M4-PLAYER-SPAWN-HEIGHT',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourcePlayerSpawnHeight4086_Query','SourcePlayerSpawnHeight4086_Ready',0xb505,[],LUA,reporter,post='SourceClock4086_Commit');results=[];costs=[];clocks=[]
 for line in log.splitlines():
  for marker,target in [('EMPTYRESULT|',results),('EMPTYCOST|',costs),('EMPTYCLOCK|',clocks)]:
   if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
 reporter.check('exact source-integer height by player index, including dead entity; no physical mutations',len(results)==len(rows)and all(r==[i,0,0,3 if c['fault']else 2,*([0xa5a5]*2 if c['fault']else[0,c['heights'][c['player']]])]for i,(r,c)in enumerate(zip(results,rows))))
 reporter.check('spawn height faults block source clock retirement',len(clocks)==len(rows)and all(r==([i,1,48,1]if c['fault']else[i,0,49,0])for i,(r,c)in enumerate(zip(clocks,rows))))
 r=dict(schema='BYOR_4086_PLAYER_SPAWN_HEIGHT_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),source_report_sha256=hashlib.sha256(a.source_report.read_bytes()).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),cases=len(rows),inputs=rows,results=results,costs=costs,clocks=clocks,stage_descriptor_installation_instrumented=True,native_world_publication_bound=False,drop_jump_bound=False,full_default_init_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
