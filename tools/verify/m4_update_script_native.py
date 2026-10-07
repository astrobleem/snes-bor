"""Closed, metadata-derived uninitialized entity update method native proof."""
import argparse,hashlib,itertools,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_script_clone import derive,pack
from script_callback_owner import derive as callbacks,pack as pack_callbacks
from script_nested_authority import extract
from dialect_4086 import ENGINE_COMMIT
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function set(k,v,n)put(sy[k],v,n)end
local before,cpu,ctx={}, {},0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 local v=0x414000+c.slot*80;local rel=0x409000+c.slot*64
 put(v,v,4);put(v+4,1,4);put(0x416800+c.slot*64,c.model);put(rel+44,c.mask,4)
 set('SourceUpdateScript4086_Ready',0xb5e1);set('SourceUpdateScript4086_Status',0)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',5);set('SourceWorldTick4086_Slot',c.slot);set('SourceWorldTick4086_TimeLo',48,4)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_TemplateCount',16);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Time',48,4)
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Active',0);set('SourceSelf4086_Fault',0);set('SourceSelf4086_GlobalLow',v,4)
 set('SourceUpdateFrame4086_State',0);set('SourceUpdateFrame4086_Pending',0)
 set('SourceScriptClone4086_Ready',0xb5c1);set('SourceScriptClone4086_Status',0);set('SourceScriptClone4086_Base',0x8000);set('SourceScriptClone4086_Bank',59);set('SourceScriptClone4086_Bytes',CLONEBYTES);set('SourceScriptClone4086_Models',16)
 set('SourceAnimationCallback4086_Ready',0xb4e6);set('SourceAnimationCallback4086_Base',0x8000);set('SourceAnimationCallback4086_Bank',60);set('SourceAnimationCallback4086_Models',16);set('SourceAnimationCallback4086_Programs',PROGRAMS)
 set('VmSourceVars_Ready',0xb4a4);set('VmSourceVars_Base',0x8800);set('VmSourceVars_Bank',0x41);set('VmSourceVars_Count',384)
 local faults={ready={'SourceUpdateScript4086_Ready',0},repeat_call={'SourceUpdateScript4086_Status',2},world={'VmSourceWorld_Ready',0},pool={'VmSourceWorld_PoolBase',0x4002},side={'VmSourceWorld_SideBase',0x6802},count={'VmSourceWorld_Count',129},slot={'SourceWorldTick4086_Slot',128},tick={'SourceWorldTick4086_Ready',0},phase={'SourceWorldTick4086_Phase',4},state={'SourceWorldTick4086_State',3},pending={'SourceWorldTick4086_Pending',0},time={'SourceWorldTick4086_TimeLo',49},self_lease={'SourceSelf4086_Ready',0},self_active={'SourceSelf4086_Active',1},self_fault={'SourceSelf4086_Fault',1},self_pointer={'SourceSelf4086_GlobalLow',0},clone={'SourceScriptClone4086_Ready',0},table={'SourceScriptClone4086_Base',0x8002},callback={'SourceAnimationCallback4086_Ready',0},vars={'VmSourceVars_Ready',0}}
 if faults[c.bad]then local f=faults[c.bad];set(f[1],f[2])end
 if c.bad=='mask'then put(rel+44,c.mask~1,4)
 elseif c.bad=='mask_wide'then put(rel+46,1)
 elseif c.bad=='update_initialized'then put(rel+44,c.mask|2,4)
 elseif c.bad=='model'then put(0x416800+c.slot*64,16)
 elseif c.bad=='token'then put(v,0,4)
 elseif c.bad=='exists'then put(v+4,0,4)
 elseif c.bad=='exists_wide'then put(v+6,1)end
 before={};for _,r in ipairs({{0x409000,8192},{0x40c000,12288},{0x414000,18432},{0x418800,24576},{0x439000,10240},{sy.SourceWorldTick4086_Ready,52},{sy.SourceSelf4086_GlobalLow,4}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('UPDATEABSENT|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(sy.SourceUpdateScript4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 src=Source(a.source);cr=derive(src);ct=pack(cr);cb,*_=callbacks(src);bt=pack_callbacks(cb)
 assert all(not m['update_method_initialized']for m in cr['models'])
 text=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');function=extract(text,'execute_updateentity_script');(a.output/'execute_updateentity_script.c').write_text(function)
 assert 'if(Script_IsInitialized(cs))'in function and 'ent->scripts->update_script' in function
 rows=[dict(slot=s,model=m['id'],mask=m['initialized_mask'],bad='',fault=0)for s,m in itertools.product((0,1,63,127),cr['models'])]
 for slot in (0,127):
  for bad in ('ready','repeat_call','world','pool','side','count','slot','tick','phase','state','pending','time','self_lease','self_active','self_fault','self_pointer','clone','table','callback','vars','mask','mask_wide','update_initialized','model','token','exists','exists_wide'):
   rows.append(dict(rows[slot//127],slot=slot,bad=bad,fault=1))
 sy=symbols(Path('src/main.sym'));entry=sy['SourceUpdateScript4086_Execute'];lua=LUA.replace('CLONEBYTES',str(len(ct))).replace('PROGRAMS',str(cb['program_count']))
 lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
 r=Reporter('M4-UPDATE-ABSENT',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceUpdateScript4086_Execute','SourceUpdateScript4086_Ready',0xb5e1,[(59,0,ct),(60,0,bt)],lua,r,batch_size=2)
 results=[list(map(int,line.split('UPDATEABSENT|',1)[1].split('|')))for line in log.splitlines()if 'UPDATEABSENT|'in line]
 r.check('all source model descriptors, full instance mask, owner and epoch guards; no live mutations and CPU preservation',results==[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)])
 d=dict(schema='BYOR_4086_UPDATE_UNINITIALIZED_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,engine_commit=ENGINE_COMMIT,authority_function_sha256=hashlib.sha256(function.encode()).hexdigest(),metadata=cr,rom_sha256=hashlib.sha256(raw).hexdigest(),script_table_sha256=hashlib.sha256(ct).hexdigest(),callback_table_sha256=hashlib.sha256(bt).hexdigest(),initialized_update_methods_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
