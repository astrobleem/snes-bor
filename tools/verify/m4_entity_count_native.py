"""Pinned count_ents predicate on the real native pool; readonly ownership proof."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter

MASK=0x7ffd8a
LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local before={};local cpu={};local ctx=0;local returned=0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);put(0x7ffd8a,c.mask)
 put(sy.VmSourceWorld_Ready,c.ready);put(sy.VmSourceWorld_Count,c.count);put(sy.VmSourceWorld_PoolBase,c.pool)
 for i=0,127 do put(0x414004+i*80,c.entities[i+1].exists,4);put(0x40c048+i*96,c.entities[i+1].type,4)end
 before={};for _,r in ipairs({{0x414000,10240},{0x40c000,12288}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();returned=s['cpu.a'];ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('SOURCECOUNT|'..word(INDEX)..'|'..n..'|'..ctx..'|'..returned)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for count in (1,2,7,128):
        for mask in (0,1,2,4,8,12,256,65535):
            for pattern in range(3):
                entities=[dict(exists=(0,1,-1,65536)[(i+pattern)%4],type=(0,1,2,4,8,256,3,12)[(i*3+pattern)%8])for i in range(128)]
                rows.append(dict(count=count,mask=mask,entities=entities,ready=0xb4a3,pool=0x4000,fault=0))
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');function=extract(raw,'count_ents')
    crows=[]
    for r in rows:
        crows.append('{'+str(r['count'])+','+str(r['mask'])+',{'+','.join('{'+str(e['exists'])+','+str(e['type'])+'}'for e in r['entities'])+'}}')
    code='#include <stdio.h>\ntypedef struct {int exists;struct {int type;} modeldata;} Entity; Entity ents[128],*ent_list[128];int ent_max;\n'+function+'\nstruct {int count,mask;struct {int exists,type;} entities[128];} cases[]={'+','.join(crows)+'};\nint main(void){unsigned i;int j;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){ent_max=cases[i].count;for(j=0;j<128;j++){ents[j].exists=cases[i].entities[j].exists;ents[j].modeldata.type=cases[i].entities[j].type;ent_list[j]=&ents[j];}printf("%d\\n",count_ents(cases[i].mask));}return 0;}\n'
    (a.output/'count.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','count.c','-fe=count.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('ENTITY_COUNT_AUTHORITY_BUILD')
    values=list(map(int,subprocess.check_output([str(a.output/'count.exe')],cwd=a.output,text=True).splitlines()))
    for row,value in zip(rows,values):row['expected']=value
    for bad,value in (('ready',0),('pool',0x4002),('count',0),('count',129)):
        c=dict(rows[-1]);c[bad]=value;c['fault']=1;rows.append(c)
    sy=symbols(Path('src/main.sym'));entry=sy['SourceCountEntities4086_Count'];lua=LUA+f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+6 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    append='\nSourceCountFixture_Apply:\n.a16\n.i16\n lda.l $7FFD8A\n jsl COUNTENTRY\n rtl\n'
    r=Reporter('M4-ENTITY-COUNT',kind='GATE');rom,log=run_fixture(a.rom,a.output,rows,'SourceCountFixture_Apply','VmSourceWorld_Ready',0xb4a3,[],lua,r,batch_size=2,append=append,bindings=dict(COUNTENTRY='SourceCountEntities4086_Count'))
    results=[list(map(int,line.split('SOURCECOUNT|',1)[1].split('|')))for line in log.splitlines()if 'SOURCECOUNT|'in line]
    r.check('literal C count over mixed types, full-width existence, pool spans and readonly CPU/entity guards',len(results)==len(rows)and all(v[:3]==[i,0,0]and(c['fault']or v[3]==c['expected'])for i,(v,c)in enumerate(zip(results,rows))))
    d=dict(schema='BYOR_4086_ENTITY_COUNT_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=len(rows),inputs=rows,results=results,engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(function.encode()).hexdigest(),rom_sha256=hashlib.sha256(rom).hexdigest(),low16_mask_domain=True,native_queue_dispatch_bound=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
