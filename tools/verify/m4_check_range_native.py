"""Native extended range arithmetic; staging primitive, not gameplay binding."""
import argparse
import hashlib
import json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from source_check_range_4086 import check

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local before,cpu={},{}
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 put(sy.SourceCheckRange4086_Ready,c.bad=='ready'and 0 or 0xb5f7)
 put(sy.SourceCheckRange4086_Status,c.bad=='busy'and 1 or c.bad=='fault'and 3 or c.bad=='wide_status'and 0x10000 or 0)
 put(sy.SourceCheckRange4086_Present,c.target and 1 or 0)
 put(sy.SourceCheckRange4086_Direction,c.direction,4)
 for i=1,4 do put(sy.SourceCheckRange4086_Source+4*(i-1),c.source[i],4);put(sy.SourceCheckRange4086_Target+4*(i-1),(c.target or {0,0,0,0})[i],4)end
 for i=1,8 do put(sy.SourceCheckRange4086_Ranges+4*(i-1),c.ranges[i],4)end
 put(sy.SourceCheckRange4086_Result,55,4);before={}
 for _,block in ipairs({{sy.SourceCheckRange4086_Present,70},{sy.VmNativeVariant_Result,8},{sy.SourceRandom4086_Ready,12},{sy.SourceCRandom4086_Ready,18}})do
  for j=0,block[2]-1 do local a=block[1]+j;before[a]=emu.read(a,mt)end
 end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=st['cpu.'..k]end;cpu.sp=cpu.sp+3
end,emu.callbackType.exec,sy.SourceCheckRange4086_Execute,sy.SourceCheckRange4086_Execute,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local st=emu.getState();local context=0
 for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=st['cpu.'..k]then context=context+1 end end
 if(cpu.ps&254)~=(st['cpu.ps']&254)then context=context+1 end
 local changed=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then changed=changed+1 end end
 emu.log('RANGEPROOF|'..word(INDEX)..'|'..context..'|'..changed..'|'..word(sy.SourceCheckRange4086_Status)..'|'..(word(sy.SourceCheckRange4086_Result)|(word(sy.SourceCheckRange4086_Result+2)<<16)))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('rom','authority','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    au=json.loads(a.authority.read_text());assert au['status']=='PASS'
    indices=sorted(set(range(0,len(au['inputs']),37))|{d['index']for d in au['accepted_compat_differences']})
    rows=[dict(au['inputs'][i],authority_index=i,bad='',fault=0)for i in indices]
    # Native operands can span the entire signed Q16 coordinate domain.
    # Deliberately exercise 33-bit differences and 48-bit range endpoints.
    for axis in range(4):
        for lo,hi in ((-2147483648,2147483647),(-32768,32768),(0,0)):
            for source,target in ((-2147483648,2147483647),(2147483647,-2147483648),(-1,0),(0,-1)):
                for direction in (0,1,65536):
                    s=[0]*4;t=[0]*4;r=[-1,1]*4;s[axis]=source;t[axis]=target;r[2*axis:2*axis+2]=[lo,hi]
                    rows.append(dict(source=s,target=t,ranges=r,direction=direction,bad='',fault=0))
    for bad in ('ready','busy','fault'):
        rows.append(dict(rows[0],bad=bad,fault=1))
    reporter=Reporter('M4-CHECK-RANGE',kind='GATE')
    raw,log=run_fixture(a.rom,a.output,rows,'SourceCheckRange4086_Execute','SourceCheckRange4086_Ready',0xb5f7,[],LUA,reporter,batch_size=8)
    actual=[list(map(int,line.split('RANGEPROOF|',1)[1].split('|')))for line in log.splitlines()if 'RANGEPROOF|'in line]
    expected=[[i,0,0,3 if c['fault']else 2,55 if c['fault']else int(check(c['ranges'],c['source'],c['target'],c['direction']))]for i,c in enumerate(rows)]
    failures=[dict(input=c,actual=v,expected=e)for c,v,e in zip(rows,actual,expected)if v!=e]
    reporter.check('extended native numeric predicate, CPU and immutable input/VM/RNG retention; guards',len(actual)==len(rows)and not failures)
    report=dict(schema='BYOR_4086_CHECK_RANGE_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,failures=failures[:20],
                rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),numeric_policy='ACCEPTED_COMPAT_Q16_16',
                arithmetic_width_bits=48,actual_entity_binding=False,animation_table_query_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()


if __name__=='__main__':main()
