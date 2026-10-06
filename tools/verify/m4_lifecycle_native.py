"""Native current-model scalar installation; callbacks and full init unbound."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_lifecycle_inputs import unpack,HEADER,STRIDE
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function romput(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,emu.memType.snesPrgRom)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function set(k,v)put(sy[k],v)end
local ranges={{0x438fc0,64},{0x439000,10240},{0x43b800,64},{0x414000,10240},{0x40c000,12288},{0x430000,24064},{0x43c000,8192}}
local before,cpu,start,ctx={},{},0,0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,prefix in ipairs({'SourceUpdateFrame','SourceAnimationInit','SourceModelAnimation','SourceModelTransition','SourceFrameStack','SourceFrameEffectPlan','SourceSelf','SourceWorldTick'})do set(prefix..'4086_Ready',0)end
 set('SourceClock4086_Ready',0xb4c5);set('SourceClock4086_Due',1);set('SourceClock4086_TimeLo',48);set('SourceClock4086_TimeHi',0);set('SourceClock4086_Fault',0)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,165,mt)end end
 for i,n in ipairs(tablebytes)do emu.write(0x1e0000+i-1,n,emu.memType.snesPrgRom)end
 for i=0,127 do put(0x414000+i*80,0x414000+i*80,4);put(0x43904a+i*80,0xb4fb)end
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_Count',128)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',128);set('SourceModelEntityCopy4086_Models',16)
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceLifecycle4086_Status',0);set('SourceLifecycle4086_Slot',c.slot);set('SourceLifecycle4086_Model',c.model);set('SourceLifecycle4086_Base',0x8000);set('SourceLifecycle4086_Bank',60);set('SourceLifecycle4086_Bytes',TABLEBYTES);set('SourceLifecycle4086_Models',16);set('SourceLifecycle4086_Reset',c.reset)
 if c.bad=='ready'then set('SourceLifecycle4086_Ready',0xffff)
 elseif c.bad=='sticky'then set('SourceLifecycle4086_Status',3)
 elseif c.bad=='reset'then set('SourceLifecycle4086_Reset',2)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='pool'then set('VmSourceWorld_PoolBase',0x4002)
 elseif c.bad=='count_zero'then set('VmSourceWorld_Count',0)
 elseif c.bad=='count'then set('VmSourceWorld_Count',129)
 elseif c.bad=='slot'then set('SourceLifecycle4086_Slot',128)
 elseif c.bad=='core'then set('SourceModelEntityCopy4086_Ready',0)
 elseif c.bad=='paired_entities'then set('SourceModelEntityCopy4086_Entities',127)
 elseif c.bad=='models_zero'then set('SourceLifecycle4086_Models',0)
 elseif c.bad=='models'then set('SourceLifecycle4086_Models',17)
 elseif c.bad=='paired_models'then set('SourceModelEntityCopy4086_Models',15)
 elseif c.bad=='model'then set('SourceLifecycle4086_Model',16)
 elseif c.bad=='base'then set('SourceLifecycle4086_Base',0x7fff)
 elseif c.bad=='bank'then set('SourceLifecycle4086_Bank',0x40)
 elseif c.bad=='bytes'then set('SourceLifecycle4086_Bytes',TABLEBYTES-2)
 elseif c.bad=='token'then put(0x414000+c.slot*80,0)
 elseif c.bad=='token_high'then put(0x414002+c.slot*80,0)
 elseif c.bad=='uninitialized'then set('SourceLifecycle4086_Reset',0);put(0x43904a+c.slot*80,0)
 elseif c.bad=='magic'then romput(0x1e0000,0)
 elseif c.bad=='version'then romput(0x1e0004,0)
 elseif c.bad=='stride'then romput(0x1e0006,30)
 elseif c.bad=='header_models'then romput(0x1e0008,15)
 elseif c.bad=='row_id'then romput(0x1e0000+24+c.model*32,16)
 elseif c.bad=='row_reserved'then romput(0x1e0000+26+c.model*32,1)
 elseif c.bad=='subtype'then romput(0x1e0000+28+c.model*32,12)
 elseif c.bad=='subtype_high'then romput(0x1e0000+30+c.model*32,1)
 elseif c.bad=='makeinv_min'then romput(0x1e0000+36+c.model*32,0x80000000,4)
 elseif c.bad=='knock_inf'then romput(0x1e0000+44+c.model*32,0x7f800000,4)
 elseif c.bad=='knock_nan'then romput(0x1e0000+44+c.model*32,0x7fc00000,4)
 elseif c.bad=='reserved'then romput(0x1e0000+48+c.model*32,1)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 local s=emu.getState();start=s.masterClock;cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if cpu.sp~=s['cpu.sp'] or(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('LIFECOST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.fault==0 then
  if c.reset==1 then for i=0,79 do before[0x439000+c.slot*80+i]=0 end end
  for i=0,19 do before[0x439030+c.slot*80+i]=tablebytes[24+c.model*32+4+i+1]end
  local function expect(a,v)before[a]=v&255;before[a+1]=(v>>8)&255 end
  expect(0x439048+c.slot*80,c.model);expect(0x43904a+c.slot*80,0xb4fb)
 end
 local mismatch=0;for a,n in pairs(before)do if emu.read(a,mt)~=n then mismatch=mismatch+1 end end
 emu.log('LIFERESULT|'..word(INDEX)..'|'..mismatch..'|'..ctx..'|'..word(sy.SourceLifecycle4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log('LIFECLOCK|'..word(INDEX)..'|'..word(sy.SourceClock4086_Due)..'|'..word(sy.SourceClock4086_TimeLo)..'|'..word(sy.SourceClock4086_Fault))end,emu.callbackType.exec,POSTRESULT,POSTRESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--table',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);table=a.table.read_bytes();assert len(unpack(table))==16
 rows=[dict(model=m,slot=s,reset=r,fault=0,bad='')for m in range(16)for s in (0,1,127)for r in (0,1)]
 for bad in ('ready','sticky','reset','world','pool','count_zero','count','slot','core','paired_entities','models_zero','models','paired_models','model','base','bank','bytes','token','token_high','uninitialized','magic','version','stride','header_models','row_id','row_reserved','subtype','subtype_high','makeinv_min','knock_inf','knock_nan','reserved'):
  for slot in (0,127):rows.append(dict(model=3,slot=slot,reset=1,fault=1,bad=bad))
 reporter=Reporter('M4-LIFECYCLE',kind='GATE');lua='local tablebytes={'+','.join(map(str,table))+'}\n'+LUA.replace('TABLEBYTES',str(len(table)));raw,log=run_fixture(a.rom,a.output,rows,'SourceLifecycle4086_Apply','SourceLifecycle4086_Ready',0xb4fb,[(60,0,table)],lua,reporter,post='SourceClock4086_Commit');results=[];costs=[];clocks=[]
 for line in log.splitlines():
  for marker,target in [('LIFERESULT|',results),('LIFECOST|',costs),('LIFECLOCK|',clocks)]:
   if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
 reporter.check('current model scalar reset/preserve, full physical rows/guards and CPU context',len(results)==len(rows) and all(r==[i,0,0,3 if c['fault'] else 2]for i,(r,c)in enumerate(zip(results,rows))))
 reporter.check('lifecycle fault cannot retire source clock',len(clocks)==len(rows)and all(r==([i,1,48,1]if c['fault']else[i,0,49,0])for i,(r,c)in enumerate(zip(clocks,rows))))
 report=dict(schema='BYOR_4086_CURRENT_LIFECYCLE_SCALAR_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),table_sha256=hashlib.sha256(table).hexdigest(),cases=len(rows),inputs=rows,results=results,costs=costs,clocks=clocks,peak_master_clocks=max((c[1]for c in costs),default=0),physical_range=['439000','43B7FF'],held_palette_binding_workspace_max_end='435E00',callback_execution_bound=False,full_default_init_bound=False,birth_model_transition_installation_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
