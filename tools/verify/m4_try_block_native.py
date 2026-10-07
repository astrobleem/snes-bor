"""Native common_try_block early gates with real engine RNG and VM preservation."""
import argparse, hashlib, json
from pathlib import Path
from m4_ai_owner_native import LUA
from _source_leaf_fixture import run_fixture
from _harness import Reporter

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 au=json.loads(a.authority.read_text());assert au['status']=='PASS'
 base=dict(time=48,nextthink=48,endgame=0,takeaction=0,think=6,noaicontrol=0,reactive=1,update_mark=0x12340001,animation=5,spawn=3,respawn=4,animating=1,exists=1,bad='',mutation=0)
 rows=[];seen=set()
 for c in au['inputs']:
  key=tuple(c[k]for k in ('nopassiveblock','blockodds','random_index','animation'))
  if key in seen:continue
  seen.add(key);seed=au['random_rows'][c['random_index']]
  rows.append(dict(base,**c,slot=(0,1,63,127)[len(rows)%4],model=len(rows)%16,calls=(0,65535,0xffffffff)[len(rows)%3],seed_before=seed[0],seed_after=seed[1],random_result=seed[2],fault=c['requires_target_service'],advance=int(bool(c['nopassiveblock']))))
 good=next(c for c in rows if c['nopassiveblock']and not c['fault'])
 for bad in ('ready','busy','commonready','commonphase','commonslot','normalready','normalphase','normalslot','world','pool','side','count','slot','tick','phase','state','pending','time','self_lease','self_active','self_fault','self_pointer','life','freeze','cache','cache_models','cache_max','cache_bytes','spawn_id','respawn_id','token','model','policyready','core','entities','policymodels','randready','randbusy'):
  rows.append(dict(good,bad=bad,fault=1,advance=0))
 lua=LUA.replace("set('SourceAI4086_State',0)","set('SourceAI4086_State',2);set('SourceAI4086_Slot',s)")
 setup="""
 put(side,c.model);cache=0x43c000+c.model*256;put(cache+26,c.animation)
 set('SourceTryBlock4086_Ready',0xb5f1);set('SourceTryBlock4086_Status',0);set('SourceTryBlock4086_Mask',55,4)
 set('SourceNormalAttack4086_Ready',0xb5eb);set('SourceNormalAttack4086_State',3);set('SourceNormalAttack4086_Slot',s);set('SourceNormalAttack4086_Response',55,4)
 set('SourceCommonThink4086_Ready',0xb5e7);set('SourceCommonThink4086_State',7);set('SourceCommonThink4086_Slot',s)
 set('SourceModelAttackPolicy4086_Ready',0xb5f0);set('SourceModelAttackPolicy4086_Models',16)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Models',16);set('SourceModelEntityCopy4086_Entities',128)
 put(0x42f408+s*24,c.nopassiveblock,4);put(0x42f40c+s*24,c.blockodds,4)
 -- A conflicting cache row proves entity shallow-copy values are used.
 put(0x40bc00+c.model*16,0x12345678,4);put(0x40bc04+c.model*16,0x76543210,4)
 set('SourceRandom4086_Ready',0xb4d4);set('SourceRandom4086_Busy',0);set('SourceRandom4086_SeedLo',c.seed_before,4);set('SourceRandom4086_CallsLo',c.calls,4)
 for j=0,7 do put(sy.VmNativeVariant_Result+j,0x5a,1)end
 for j=0,17 do put(sy.SourceCRandom4086_Ready+j,0xa5,1)end
 local extra={ready={'SourceTryBlock4086_Ready',0},busy={'SourceTryBlock4086_Status',2},commonready={'SourceCommonThink4086_Ready',0},commonphase={'SourceCommonThink4086_State',6},commonslot={'SourceCommonThink4086_Slot',(s+1)%128},normalready={'SourceNormalAttack4086_Ready',0},normalphase={'SourceNormalAttack4086_State',4},normalslot={'SourceNormalAttack4086_Slot',(s+1)%128},policyready={'SourceModelAttackPolicy4086_Ready',0},core={'SourceModelEntityCopy4086_Ready',0},entities={'SourceModelEntityCopy4086_Entities',127},policymodels={'SourceModelAttackPolicy4086_Models',15},randready={'SourceRandom4086_Ready',0},randbusy={'SourceRandom4086_Busy',1}}
 if extra[c.bad]then local f=extra[c.bad];set(f[1],f[2])end
"""
 lua=lua.replace(' local faults=',setup+' local faults=').replace("ready={'SourceAI4086_Ready',0},busy={'SourceAI4086_State',1},",'')
 lua=lua.replace("end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)"," for j=0,7 do before[sy.VmNativeVariant_Result+j]=0x5a end\n for j=0,17 do before[sy.SourceCRandom4086_Ready+j]=0xa5 end\n for j=0,11 do before[sy.SourceRandom4086_Ready+j]=emu.read(sy.SourceRandom4086_Ready+j,mt)end\n for j=0,255 do before[0x40bc00+j]=emu.read(0x40bc00+j,mt)end\nend,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)",1)
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local phase=');end=lua.index('emu.addMemoryCallback(function()',start+30);lua=lua[:start]+lua[end:]
 start=lua.index('emu.addMemoryCallback(function()\n local c=rows[word(INDEX)+1];local s=c.slot;local e=c.expected')
 lua=lua[:start]+r'''
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.advance~=0 then for _,r in ipairs({{sy.SourceRandom4086_SeedLo,c.seed_after},{sy.SourceRandom4086_CallsLo,(c.calls+1)&0xffffffff}})do for j=0,3 do before[r[1]+j]=(r[2]>>(8*j))&255 end end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('TRYBLOCK|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceTryBlock4086_Status)..'|'..dw(sy.SourceNormalAttack4086_Response))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
'''
 r=Reporter('M4-TRY-BLOCK',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceTryBlock4086_Execute','SourceTryBlock4086_Ready',0xb5f1,[],lua,r,batch_size=2)
 results=[list(map(int,l.split('TRYBLOCK|',1)[1].split('|')))for l in log.splitlines()if 'TRYBLOCK|'in l];wanted=[[i,0,0,3 if c['fault']else 2,55 if c['fault']else 0]for i,c in enumerate(rows)]
 failures=[dict(index=i,input=c,actual=v,expected=e)for i,(c,v,e)in enumerate(zip(rows,results,wanted))if v!=e]
 r.check('ordered nopassiveblock/full32 mask/cache gates; exact RNG call count/wrap and real outputs; entity values independent of cache; typed VM scratch/CRT stream/CPU/siblings retained; target bodies explicit fault',len(results)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_TRY_BLOCK_NULL_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,failures=failures[:20],authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),rand32_body_instrumented=False,target_services_bound=False,grounded_attack_integrated=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
