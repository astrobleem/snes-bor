"""Native speed truth metadata; guarded setter helper and exact float truth."""
import argparse,hashlib,json,sys
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from actor_s5_entity_fixture import symbols

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local before,cpu={},{ }
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for i=0,10239 do emu.write(0x439000+i,165,mt)end
 for i=0,8191 do emu.write(0x416800+i,165,mt)end
 put(sy.SourceLifecycle4086_Ready,c.enabled and 0xb4fb or 0);put(sy.SourceLifecycle4086_Status,2)
 put(sy.SourceModelEntityCopy4086_Ready,0xb4eb);put(sy.SourceModelEntityCopy4086_Entities,128);put(sy.VmSourceWorld_Count,128)
 put(ENTITYINDEX,c.slot);put(MOTIONSIDE,c.slot*64);put(ARGLO,c.value,4)
 put(0x416800+c.slot*64,3);put(0x439048+c.slot*80,3);put(0x43904a+c.slot*80,0xb4fb)
 if c.bad=='life'then put(sy.SourceLifecycle4086_Ready,0xffff)
 elseif c.bad=='sticky'then put(sy.SourceLifecycle4086_Status,3)
 elseif c.bad=='core'then put(sy.SourceModelEntityCopy4086_Ready,0)
 elseif c.bad=='count'then put(sy.SourceModelEntityCopy4086_Entities,127)
 elseif c.bad=='marker'then put(0x43904a+c.slot*80,0)
 elseif c.bad=='model'then put(0x439048+c.slot*80,4)end
 before={};for _,r in ipairs({{0x439000,10240},{0x416800,8192}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
 cpu=emu.getState()
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];local n,ctx=0,0
 if c.enabled and c.fault==0 then
  local b=0x439000+c.slot*80
  for i=0,3 do before[b+68+i]=i==0 and(c.value~=0 and 1 or 0)or 0 end
  before[b+76]=8;before[b+77]=0xb5
 end
 for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 local s=emu.getState();for _,k in ipairs({'a','x','y','d','dbr','sp'})do if cpu['cpu.'..k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu['cpu.ps']&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('SPEEDIDENTITY|'..word(INDEX)..'|'..n..'|'..ctx)
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 rows=[dict(slot=s,value=v,enabled=e,bad='',fault=0)for s in(0,1,127)for v in(0,1,-1,65536,-2147483648,2147483647)for e in(0,1)]
 rows.extend(dict(slot=s,value=1,enabled=1,bad=b,fault=1)for s in(0,127)for b in('life','sticky','core','count','marker','model'))
 sy=symbols(Path('src/main.sym'));lua=LUA
 for k,v in dict(ENTITYINDEX=sy['VmSourceEntity_Index'],MOTIONSIDE=sy['SourceMotionProperty_Side'],ARGLO=sy['VmSourceMutation_Lo']).items():lua=lua.replace(k,str(v))
 wrapper='''
SpeedIdentityFixture_Apply:
.a16
.i16
 jsl PREFLIGHT
 bcs SpeedIdentityFixture_Return
 jsl MUTATE
SpeedIdentityFixture_Return:
.a16
.i16
 rtl
'''
 r=Reporter('M4-SPEED-IDENTITY',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SpeedIdentityFixture_Apply','SourceLifecycle4086_Ready',0xb508,[],lua,r,append=wrapper,bindings=dict(PREFLIGHT='SourceSpeedIdentity4086_PreflightProperty',MUTATE='SourceSpeedIdentity4086_ApplyProperty'))
 results=[list(map(int,line.split('SPEEDIDENTITY|',1)[1].split('|')))for line in log.splitlines()if 'SPEEDIDENTITY|'in line]
 r.check('zero/nonzero metadata only; rejection has no physical writes; original lease opt-out and CPU context',results==[[i,0,0]for i in range(len(rows))])
 report=dict(schema='BYOR_4086_SPEED_IDENTITY_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),cases=len(rows),inputs=rows,results=results,caller_checks_world_pool_slot=True,script_input_policy='ACCEPTED_COMPAT_Q16_16',binary32_truth_separately_proven_by_model_copy=True,full_default_init_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
