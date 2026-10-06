"""Native pure source movement compatibility projection against 32-bit C."""
import argparse,hashlib,json
from pathlib import Path
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local ranges={{0x40b000,16384},{0x414000,18432},{0x439000,10240}}
local cpu,start,ctx,writes,active={},0,0,0,false
emu.addMemoryCallback(function(a,v)
 if not active then return end
 for _,r in ipairs(ranges)do if a>=r[1]and a<r[1]+r[2]then writes=writes+1;return end end
end,emu.callbackType.write,0x40b000,0x43b7ff,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(sy.SourceModelEntityCopy4086_Lo,c.bits,4)
 local s=emu.getState();start=s.masterClock;cpu={};ctx=0;for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end
 writes=0;active=true
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 active=false;local s=emu.getState();for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
 emu.log('Q16COST|'..word(INDEX)..'|'..(s.masterClock-start))
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 emu.log('Q16RESULT|'..word(INDEX)..'|'..writes..'|'..ctx..'|'..(word(sy.SourceModelEntityCopy4086_Lo)|(word(sy.SourceModelEntityCopy4086_Hi)<<16)))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
 rows=[dict(bits=r['bits'],fault=1-r['actual'][0],expected=(r['actual'][1]if r['actual'][0]else r['bits'])&0xffffffff)for r in authority['results']]
 r=Reporter('M4-BINARY32-Q16',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceModelSpeed4086_ProjectQ16','SourceModelEntityCopy4086_Ready',0xb4eb,[],LUA,r)
 results=[];costs=[]
 for line in log.splitlines():
  for marker,target in [('Q16RESULT|',results),('Q16COST|',costs)]:
   if marker in line:target.append(list(map(int,line.split(marker,1)[1].split('|'))))
 r.check('C-exact compatibility projection or rejection with original input retained; physical/context state untouched',len(results)==len(rows)and all(v==[i,0,0,c['expected']]for i,(v,c)in enumerate(zip(results,rows))))
 report=dict(schema='BYOR_BINARY32_Q16_COMPAT_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),cases=len(rows),inputs=rows,results=results,costs=costs,numeric_policy='ACCEPTED_COMPAT_Q16_16',source_float_equivalence=False,entity_speed_installation_bound=False,full_default_init_bound=False,foreign_profile_admitted=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
