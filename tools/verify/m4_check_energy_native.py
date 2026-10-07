"""Native staged check_energy predicate and signed32 boundary proof."""
import argparse,hashlib,json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from source_animation_energy_4086 import check

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local before,cpu={},{}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 put(sy.SourceCheckEnergy4086_Ready,c.bad=='ready'and 0 or 0xb5fa);put(sy.SourceCheckEnergy4086_Status,c.bad=='busy'and 1 or c.bad=='fault'and 3 or 0)
 for _,field in ipairs({{'Which',c.which},{'Cost',c.fields.cost},{'Only',c.fields.mponly},{'Disable',c.fields.disable},{'Type',c.type},{'Seal',c.seal},{'MP',c.mp},{'Health',c.health}})do put(sy['SourceCheckEnergy4086_'..field[1]],field[2],4)end
 put(sy.SourceCheckEnergy4086_Present,c.present and 1 or 0);put(sy.SourceCheckEnergy4086_Result,55,4)
 before={};for _,r in ipairs({{sy.SourceCheckEnergy4086_Which,34},{sy.VmNativeVariant_Result,8},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();local ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(st['cpu.ps']&254)then ctx=ctx+1 end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('ENERGYPREDICATE|'..word(INDEX)..'|'..ctx..'|'..changed..'|'..word(sy.SourceCheckEnergy4086_Status)..'|'..(word(sy.SourceCheckEnergy4086_Result)|(word(sy.SourceCheckEnergy4086_Result+2)<<16)))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','authority','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 au=json.loads(a.authority.read_text());assert au['status']=='PASS';rows=[]
 for i in range(0,len(au['inputs']),41):rows.append(dict(au['inputs'][i],authority_index=i,present=True,fault=0,bad='',expected=au['actual'][i]))
 for cost in (-2147483648,-65536,-1,0,1,65536,2147483647):
  for mp in (-2147483648,-1,0,1,2147483647):
   for which in (0,1):
    c=dict(which=which,type=2,seal=0,mp=mp,health=mp,fields=dict(cost=cost,mponly=0,disable=0),present=True,fault=0,bad='')
    c['expected']=int(check(which,c['fields'],c['type'],c['seal'],mp,mp));rows.append(c)
 for c in rows[:12]:rows.append(dict(c,present=False,expected=0))
 for bad in ('ready','busy','fault'):rows.append(dict(rows[0],bad=bad,fault=1,expected=55))
 reporter=Reporter('M4-CHECK-ENERGY',kind='GATE')
 raw,log=run_fixture(a.rom,a.output,rows,'SourceCheckEnergy4086_Execute','SourceCheckEnergy4086_Ready',0xb5fa,[],LUA,reporter,batch_size=8)
 actual=[list(map(int,l.split('ENERGYPREDICATE|',1)[1].split('|')))for l in log.splitlines()if 'ENERGYPREDICATE|'in l]
 expected=[[i,0,0,3 if c['fault']else 2,c['expected']]for i,c in enumerate(rows)]
 failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
 reporter.check('real integer energy predicate, signed32 bounds, CPU/input/VM/RNG retention and lease guards',len(actual)==len(rows)and not failures)
 r=dict(schema='BYOR_4086_CHECK_ENERGY_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:20],authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),actual_entity_binding=False,mutable_animation_energy_binding=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');reporter.finish()

if __name__=='__main__':main()
