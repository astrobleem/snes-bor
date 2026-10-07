"""Native source-order first-slot/priority selection under a fixed pool lease."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_spawn_slot_authority import fixtures,choose
from source_lifecycle_inputs import pack as pack_life
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols
LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function set(k,v)put(sy[k],v)end
local ranges={{0x414000,576},{0x439000,320},{0x40c000,384},{0x43fd80,32}}
local before,cpu,ctx={}, {},0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,165,mt)end end
 for i=0,3 do local v=0x414000+i*80;put(v,v,4);put(v+4,c.exists[i+1],4);local l=0x439000+i*80;put(l+60,c.old,4);put(l+72,0);put(l+74,0xb4fb)end
 put(0x43fd80,c.count,4)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Count',4);set('VmSourceWorld_TemplateCount',8)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Models',8);set('SourceModelEntityCopy4086_Entities',4)
 set('SourceLifecycle4086_Ready',0xb4fb);set('SourceLifecycle4086_Status',0);set('SourceLifecycle4086_Base',0x8000);set('SourceLifecycle4086_Bank',59);set('SourceLifecycle4086_Bytes',LIFEBYTES);set('SourceLifecycle4086_Models',8)
 set('SourceSpawnSlot4086_Ready',0xb5a1);set('SourceSpawnSlot4086_Status',0);set('SourceSpawnSlot4086_Model',c.model);put(sy.SourceSpawnSlot4086_OverrideLo,c.override,4)
 if c.bad=='ready'then set('SourceSpawnSlot4086_Ready',0)
 elseif c.bad=='sticky'then set('SourceSpawnSlot4086_Status',3)
 elseif c.bad=='limit_sticky'then set('SourceSpawnSlot4086_Status',4)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='base'then set('VmSourceWorld_PoolBase',0x4002)
 elseif c.bad=='side'then set('VmSourceWorld_SideBase',0x6802)
 elseif c.bad=='count'then set('VmSourceWorld_Count',129)
 elseif c.bad=='model'then set('SourceSpawnSlot4086_Model',8)
 elseif c.bad=='models'then set('SourceLifecycle4086_Models',7)
 elseif c.bad=='core'then set('SourceModelEntityCopy4086_Ready',0)
 elseif c.bad=='entities'then set('SourceModelEntityCopy4086_Entities',3)
 elseif c.bad=='life'then set('SourceLifecycle4086_Ready',0)
 elseif c.bad=='life_sticky'then set('SourceLifecycle4086_Status',3)
 elseif c.bad=='life_table'then set('SourceLifecycle4086_Base',0x8002)
 elseif c.bad=='roles'then put(0x43fd80,c.count+1,4)
 elseif c.bad=='role_high'then put(0x43fd82,1)
 elseif c.bad=='token'then put(0x414000+3*80,0,4)
 elseif c.bad=='token_high'then put(0x414002+3*80,0)
 elseif c.bad=='exists'then put(0x414004+3*80,2,4)
 elseif c.bad=='exists_high'then put(0x414006+3*80,1)
 elseif c.bad=='current_marker'then put(0x43904a,0)
 elseif c.bad=='current_model'then put(0x439048,8)
 end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('SLOTRESULT|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(sy.SourceSpawnSlot4086_Status)..'|'..word(sy.SourceSpawnSlot4086_Slot)..'|'..word(sy.SourceSpawnSlot4086_NeedKill))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 priorities=(-2147483648,-65537,-65536,-2,-1,0,1,2147483647);models=[dict(id=i,fields=dict(subtype=0,nomove=0,makeinv=0,priority=v,knockdowncount=0.0))for i,v in enumerate(priorities)];table=pack_life(dict(models=models));rows=[]
 for c in fixtures():
  want=choose(c);rows.append(dict(c,model=priorities.index(c['priority']),bad='',fault=want['limit'],status=4 if want['limit']else 2,wantslot=want['slot']&65535,wantkill=want['needkill']))
 base=dict(rows[3],override=0,old=-1,count=3,exists=[1,1,1,0],fault=1,status=3,wantslot=65535,wantkill=0)
 for bad in('ready','sticky','limit_sticky','world','base','side','count','model','models','core','entities','life','life_sticky','life_table','roles','role_high','token','token_high','exists','exists_high','current_marker','current_model'):rows.append(dict(base,bad=bad))
 rows.extend([dict(rows[0],model=65535,bad=bad,fault=0,status=2,wantslot=65535,wantkill=0)for bad in('','world','life')])
 # Ready rejection precedes deterministic output reset; seed output sentinels
 # so guard rows still have an explicit expected result.
 lua=LUA.replace("set('SourceSpawnSlot4086_Status',0)","set('SourceSpawnSlot4086_Slot',65535);set('SourceSpawnSlot4086_NeedKill',0);set('SourceSpawnSlot4086_Status',0)").replace('LIFEBYTES',str(len(table)))
 sy=symbols(Path('src/main.sym'));entry=sy['SourceSpawnSlot4086_Select'];lua+=f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
 r=Reporter('M4-SPAWN-SLOT',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceSpawnSlot4086_Select','SourceSpawnSlot4086_Ready',0xb5a1,[(59,0,table)],lua,r,batch_size=8)
 results=[list(map(int,line.split('SLOTRESULT|',1)[1].split('|')))for line in log.splitlines()if 'SLOTRESULT|'in line];r.check('source first-slot order, signed priority/override boundaries, nullable model, explicit capacity limit, guards and read-only physical/context state',results==[[i,0,0,c['status'],c['wantslot'],c['wantkill']]for i,c in enumerate(rows)])
 d=dict(schema='BYOR_4086_FIXED_SPAWN_SLOT_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,heap_growth_bound=False,priority_kill_bound=False,full_constructor_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True);(a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
