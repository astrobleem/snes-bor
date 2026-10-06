"""Native current-model tail under the closed empty environment capability."""
import argparse, hashlib, itertools, json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function set(k,v)put(sy[k],v)end
local ranges={{0x40c000,12288},{0x414000,18432},{0x439000,10240}}
local before,cpu,ctx={}, {},0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do emu.write(r[1]+i,165,mt)end end
 local v=0x414000+c.slot*80;put(v,v,4);put(v+4,c.alive)
 put(0x416804+c.slot*64,1)
 local b=0x40c000+c.slot*96;put(b,c.multiple,4);put(b+4,c.wall,4);put(b+8,c.platform,4)
 set('SourceDefaultPlayer4086_Ready',0xb503);set('SourceDefaultPlayer4086_Status',0);set('SourceDefaultPlayer4086_Slot',c.slot)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Level',c.level);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Count',128);set('VmSourceWorld_TemplateCount',16)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Entities',128);set('SourceModelEntityCopy4086_Models',16)
 set('SourceAnimationInit4086_Ready',0);set('SourceAnimationInit4086_State',0)
 set('SourceEnvironment4086_Ready',0xb4d1);set('SourceEnvironment4086_Stage',1);set('SourceEnvironment4086_WallCount',0)
 set('SourceEmptyInitEnvironment4086_Ready',0xb504);set('SourceEmptyInitEnvironment4086_Models',16);set('SourceEmptyInitEnvironment4086_Stage',1);set('SourceEmptyInitEnvironment4086_Status',0)
 if c.bad=='ready'then set('SourceDefaultPlayer4086_Ready',0)
 elseif c.bad=='sticky'then set('SourceDefaultPlayer4086_Status',3)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='pool'then set('VmSourceWorld_PoolBase',0x4002)
 elseif c.bad=='side'then set('VmSourceWorld_SideBase',0x6802)
 elseif c.bad=='count'then set('VmSourceWorld_Count',129)
 elseif c.bad=='slot'then set('SourceDefaultPlayer4086_Slot',128)
 elseif c.bad=='core'then set('SourceModelEntityCopy4086_Ready',0)
 elseif c.bad=='entities'then set('SourceModelEntityCopy4086_Entities',127)
 elseif c.bad=='token'then put(v,0)
 elseif c.bad=='token_high'then put(v+2,0)
 elseif c.bad=='animation'then put(0x416804+c.slot*64,0)
 elseif c.bad=='pending'then set('SourceAnimationInit4086_Ready',0xb4ec);set('SourceAnimationInit4086_State',1)
 elseif c.bad=='empty'then set('SourceEmptyInitEnvironment4086_Ready',0)
 elseif c.bad=='walls'then set('SourceEnvironment4086_WallCount',1)
 elseif c.bad=='stage'then set('SourceEnvironment4086_Stage',2)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 local s=emu.getState();cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.fault==0 and c.level~=0 and c.multiple<0 then for i=0,3 do before[0x40c000+c.slot*96+i]=0 end end
 local s=emu.getState();for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('TAILRESULT|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(sy.SourceDefaultPlayer4086_Status)..'|'..word(sy.SourceEmptyInitEnvironment4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 rows=[dict(slot=s,level=l,alive=alive,multiple=m,platform=x,wall=y,bad='',fault=0)for s,l,alive,m,(x,y)in itertools.product((0,127),(0,1),(0,1),(-2147483648,-1,0,2147483647),((0,0),(-1,-1),(1,0),(0,1),(65536,-2147483648),(-2147483648,65536)))]
 base=dict(slot=0,level=1,alive=1,multiple=-1,platform=1,wall=1)
 for bad in ('ready','sticky','world','pool','side','count','slot','core','entities','token','token_high','animation','pending','empty','walls','stage'):
  for s in (0,127):rows.append(dict(base,slot=s,bad=bad,fault=1))
 # Invalid environment is irrelevant when both query flags are nonpositive.
 for l in (0,1):rows.append(dict(base,level=l,platform=0,wall=-1,bad='empty',fault=0))
 r=Reporter('M4-DEFAULT-INIT-TAIL',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceDefaultInit4086_FinalizeEmpty','SourceDefaultPlayer4086_Ready',0xb503,[],LUA,r)
 results=[list(map(int,line.split('TAILRESULT|',1)[1].split('|')))for line in log.splitlines()if 'TAILRESULT|'in line]
 r.check('current multiple clamp, empty environment, dead pointers and untouched physical/context state',len(results)==len(rows)and all(v[:4]==[i,0,0,3 if c['fault']else 2]for i,(v,c)in enumerate(zip(results,rows))))
 r.check('query only for positive current model flags in an active level',len(results)==len(rows)and all(c['fault']or v[4]==(2 if c['level']and(c['platform']>0 or c['wall']>0)else 0)for v,c in zip(results,rows)))
 report=dict(schema='BYOR_4086_DEFAULT_INIT_EMPTY_TAIL_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,lease_installation_instrumented=True,set_idle_branch_bound=False,full_default_init_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
