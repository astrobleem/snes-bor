"""Bounded native air predicate under the explicit Q16 coordinate policy."""
import argparse,hashlib,itertools,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from source_binary32_q16 import project
from _source_leaf_fixture import run_fixture
from _harness import Reporter

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local saved,writes,active,result={},0,false,0
for _,r in ipairs({{0x409000,0x40efff},{0x414000,0x41ffff},{0x439000,0x43ffff}})do
 emu.addMemoryCallback(function()if active then writes=writes+1 end end,emu.callbackType.write,r[1],r[2],emu.cpuType.snes,mt)
end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,0)
 put(sy.SourceModelEntityCopy4086_Lo,c.y,4);put(sy.SourceDefaultPlayer4086_InvLo,c.base,4)
 saved=emu.getState();writes=0;active=true
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 active=false;local s=emu.getState();local context=0
 for _,k in ipairs({'x','y','d','dbr','sp'})do if s['cpu.'..k]~=saved['cpu.'..k]then context=context+1 end end
 if (s['cpu.ps']&254)~=(saved['cpu.ps']&254)then context=context+1 end
 local c=rows[word(INDEX)+1];local wrong=0
 if(word(sy.SourceModelEntityCopy4086_Lo)|(word(sy.SourceModelEntityCopy4086_Hi)<<16))~=(c.y&0xffffffff)then wrong=wrong+1 end
 if(word(sy.SourceDefaultPlayer4086_InvLo)|(word(sy.SourceDefaultPlayer4086_InvHi)<<16))~=(c.base&0xffffffff)then wrong=wrong+1 end
 emu.log('INAIRRESULT|'..word(INDEX)..'|'..s['cpu.a']..'|'..writes..'|'..context..'|'..wrong)
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'
 values=(-2147483648,-65536,-6555,-6554,-6553,-1,0,1,6553,6554,6555,65536,2147483647)
 rows=[dict(y=y,base=b,expected=int(abs(y-b)>=6554))for y,b in itertools.product(values,repeat=2)]
 source_rows=[]
 for i,((y,b),r)in enumerate(zip(authority['air_inputs'],authority['air_results'])):
  yq,bq=project(y),project(b);row=dict(y=yq,base=bq,expected=int(abs(yq-bq)>=6554),source_air=r[1],source_case=i);rows.append(row);source_rows.append(row)
 r=Reporter('M4-INAIR-Q16',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'SourceInAir4086_Q16Compatibility','SourceModelEntityCopy4086_Ready',0xb50a,[],LUA,r,batch_size=32)
 results=[list(map(int,line.split('INAIRRESULT|',1)[1].split('|')))for line in log.splitlines()if 'INAIRRESULT|'in line]
 r.check('absolute difference threshold, both signed extremes, source probes and context/no writes',results==[[i,c['expected'],0,0,0]for i,c in enumerate(rows)])
 deviations=[c for c in source_rows if c['source_air']!=c['expected']]
 report=dict(schema='BYOR_4086_INAIR_Q16_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',rom_sha256=hashlib.sha256(raw).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),cases=len(rows),inputs=rows,results=results,numeric_policy='ACCEPTED_COMPAT_Q16_16',threshold_q16=6554,source_binary32_boundary_deviations=deviations,arbitrary_binary32_predicate_equivalence=False,drop_native_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
