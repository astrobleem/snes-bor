"""Native exact model policy copy into independent entity modeldata fields."""
import argparse, hashlib, json
from pathlib import Path
from m4_ai_owner_native import LUA as _IMPORT_PATH
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local before,cpu,ctx={}, {},0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 set('SourceModelAttackPolicy4086_Ready',0xb5f0);set('SourceModelAttackPolicy4086_Models',16);set('SourceModelAttackPolicy4086_Slot',c.slot);set('SourceModelAttackPolicy4086_Model',c.model);set('SourceModelAttackPolicy4086_Status',0)
 set('SourceModelEntityCopy4086_Ready',0xb4eb);set('SourceModelEntityCopy4086_Models',16);set('SourceModelEntityCopy4086_Entities',128)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);set('VmSourceWorld_Count',128)
 for j=0,3071 do put(0x42f400+j,0x5a,1)end
 for j=0,255 do put(0x40bc00+j,0xa5,1)end
 for j,v in ipairs(c.values)do put(0x40bc00+c.model*16+(j-1)*4,v,4)end
 local guards={ready={'SourceModelAttackPolicy4086_Ready',0},core={'SourceModelEntityCopy4086_Ready',0},world={'VmSourceWorld_Ready',0},pool={'VmSourceWorld_PoolBase',0x4002},side={'VmSourceWorld_SideBase',0x6802},count_zero={'VmSourceWorld_Count',0},count_large={'VmSourceWorld_Count',129},count_pair={'SourceModelEntityCopy4086_Entities',127},slot={'SourceModelAttackPolicy4086_Slot',128},models_zero={'SourceModelAttackPolicy4086_Models',0},models_large={'SourceModelAttackPolicy4086_Models',17},models_pair={'SourceModelEntityCopy4086_Models',15},model={'SourceModelAttackPolicy4086_Model',16}}
 if guards[c.bad]then local f=guards[c.bad];set(f[1],f[2])end
 before={};for _,r in ipairs({{0x40bc00,256},{0x40c000,12288},{0x414000,18432},{0x41f500,2560},{0x42e000,8192},{0x439000,10240},{0x43eb00,4096},{0x43c000,8192}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.fault==0 then for j,v in ipairs(c.values)do for k=0,3 do before[0x42f408+c.slot*24+(j-1)*4+k]=(v>>(8*k))&255 end end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('MODELATTACKPOLICY|'..word(INDEX)..'|'..ctx..'|'..n..'|'..word(sy.SourceModelAttackPolicy4086_Status))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 au=json.loads(a.authority.read_text());assert au['status']=='PASS';rows=[]
 for i,(c,v)in enumerate(zip(au['inputs'],au['actual'])):
  for slot in ((0,1,63,127)if i<16 else((0,1,63,127)[i%4],)):
   rows.append(dict(slot=slot,model=i%16,values=[n&0xffffffff for n in v],bad='',fault=0,identity=c['identity']))
 for bad in ('ready','core','world','pool','side','count_zero','count_large','count_pair','slot','models_zero','models_large','models_pair','model'):rows.append(dict(rows[0],bad=bad,fault=1))
 r=Reporter('M4-MODEL-ATTACK-POLICY',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceModelAttackPolicy4086_Apply','SourceModelAttackPolicy4086_Ready',0xb5f0,[],LUA,r,batch_size=2)
 results=[list(map(int,l.split('MODELATTACKPOLICY|',1)[1].split('|')))for l in log.splitlines()if 'MODELATTACKPOLICY|'in l];wanted=[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)]
 failures=[dict(index=i,input=c,actual=v,expected=e)for i,(c,v,e)in enumerate(zip(rows,results,wanted))if v!=e]
 r.check('all4 full32 fields copied without inheritance; current mutable cache/all16 models and 4 slots; controls guard before writes; running/noAI/siblings/core/CPU retained',len(results)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_MODEL_ATTACK_POLICY_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),inputs=rows,results=results,failures=failures[:20],constructor_and_model_switch_integrated=False,target_metadata_producer_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()
if __name__=='__main__':main()
