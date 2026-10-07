"""Real engine RNG + unsigned modulo, compiler-proven probability cutoff."""
import argparse,hashlib,json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from source_actor_numeric import random32_step

LUA=r'''
local mt=emu.memType.snesMemory
local before,cpu={},{}
local ctx=0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 put(sy.SourceNormalChance4086_Ready,c.bad=='ready'and 0 or 0xb600);put(sy.SourceNormalChance4086_Status,c.bad=='busy'and 1 or 0);put(sy.SourceNormalChance4086_Cutoff,c.cutoff);put(sy.SourceNormalChance4086_AI,c.ai,4);put(sy.SourceNormalChance4086_Result,55,4)
 put(sy.SourceRandom4086_Ready,c.bad=='rng_ready'and 0 or 0xb4d4);put(sy.SourceRandom4086_SeedLo,c.seed,4);put(sy.SourceRandom4086_CallsLo,0xffffffff,4);put(sy.SourceRandom4086_Busy,c.bad=='rng_busy'and 1 or 0)
 for j=0,7 do emu.write(sy.VmNativeVariant_Result+j,0xa5,mt)end
 put(sy.SourceModelEntityCopy4086_Lo,0x12345678,4)
 before={};for _,r in ipairs({{sy.VmNativeVariant_Result,8},{sy.SourceModelEntityCopy4086_Lo,4},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18},{0x414000,18432},{0x40c000,12288},{0x42f400,3072},{0x437e00,2560},{0x439000,10240},{0x43eb00,4096}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 for _,r in ipairs({{sy.SourceRandom4086_SeedLo,c.seed_after},{sy.SourceRandom4086_CallsLo,(0xffffffff+c.calls)&0xffffffff}})do for j=0,3 do before[r[1]+j]=(r[2]>>(8*j))&255 end end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('CHANCEKERNEL|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceNormalChance4086_Status)..'|'..dw(sy.SourceNormalChance4086_Result)..'|'..dw(sy.SourceRandom4086_SeedLo)..'|'..dw(sy.SourceRandom4086_CallsLo))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
 cutoffs=sorted({v[0]for v in authority['actual']});rows=[]
 for cutoff in cutoffs:
  for ai in (0,8,65536,0xffffffff):
   for seed in (0,1,2,65535,65536,0x7fffffff,0x80000000,0xffffffff):
    after,value=random32_step(seed);calls=int(not(ai&8));expected=1 if ai&8 else int(value%10000<=cutoff)
    rows.append(dict(cutoff=cutoff&65535,ai=ai,seed=seed,seed_after=after if calls else seed,calls=calls,expected=expected,bad='',fault=0))
 for bad in ('ready','busy','rng_ready','rng_busy','cutoff'):
  rows.append(dict(rows[0],bad=bad,cutoff=10000 if bad=='cutoff'else rows[0]['cutoff'],expected=55,seed_after=rows[0]['seed'],calls=0,fault=1))
 # The literal ALWAYS branch does not inspect the cutoff or RNG lease.
 for bad in ('rng_ready','rng_busy','cutoff'):
  rows.append(dict(rows[0],ai=8,bad=bad,cutoff=10000,expected=1,seed_after=rows[0]['seed'],calls=0,fault=0))
 reporter=Reporter('M4-NORMAL-CHANCE',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceNormalChance4086_Execute','SourceNormalChance4086_Ready',0xb600,[],LUA,reporter,batch_size=1,frame_limit=6000)
 actual=[list(map(int,l.split('CHANCEKERNEL|',1)[1].split('|')))for l in log.splitlines()if 'CHANCEKERNEL|'in l]
 expected=[[i,0,0,3 if c['fault']else 2,c['expected'],c['seed_after'],(0xffffffff+c['calls'])&0xffffffff]for i,c in enumerate(rows)]
 failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 reporter.check('exact C cutoff decision, source RNG consumption, full unsigned modulo, ALWAYS bypass, CPU/VM/model scratch/CRT/entity retention and guards',len(actual)==len(rows)and not failures)
 report=dict(schema='BYOR_4086_NORMAL_CHANCE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:20],cutoffs=cutoffs,authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),actual_entity_model_cutoff_selection_bound=False,normal_attack_caller_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
