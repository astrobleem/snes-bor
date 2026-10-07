"""Pinned C stage-completion condition on actual native entity and role data."""
import argparse
import hashlib
import itertools
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

LUA=r'''
local mt=emu.memType.snesMemory
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function dw(a)return word(a)|(word(a+2)<<16)end
local function set(k,v,n)put(sy[k],v,n)end
local before={};local cpu={};local ctx=0;local returned=0
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for i=0,127 do put(0x414000+i*80,0x414000+i*80,4);put(0x414004+i*80,0,4);put(0x40c048+i*96,0,4);put(0x439014+i*80,c.dead,4)end
 put(0x414004+10*80,c.exists,4);put(0x40c048+10*96,c.mask,4)
 for i=0,3 do put(0x43fd84+i*4,(c.roles&(1<<i))~=0 and(0x414000+c.slot*80)or 0,4)end
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Level',1);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_Count',128)
 set('SourceStageCompletion4086_Ready',0xb5d8);set('SourceStageCompletion4086_Status',0);set('SourceStageCompletion4086_LevelType',c.leveltype,4)
 set('SourceScrollerPrefix4086_Ready',0xb5d7);set('SourceScrollerPrefix4086_State',2);set('SourceScrollerPrefix4086_Completed',0,4)
 set('SourceStageProducer4086_Ready',0xb5d6);set('SourceStageProducer4086_State',0);set('SourceStageProducer4086_Limit',34);set('SourceStageProducer4086_Completed',0);set('SourceStageQueue4086_Index',c.index)
 if c.bad=='ready'then set('SourceStageCompletion4086_Ready',0)
 elseif c.bad=='prefix'then set('SourceScrollerPrefix4086_State',4)
 elseif c.bad=='producer'then set('SourceStageProducer4086_State',1)
 elseif c.bad=='world'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='role_high'then put(0x43fd86,0x42)
 elseif c.bad=='role_low'then put(0x43fd84,0x4001)
 elseif c.bad=='role_count'then set('VmSourceWorld_Count',1)
 elseif c.bad=='token'then put(0x414000+c.slot*80,0,4)end
 before={};for _,r in ipairs({{0x414000,10240},{0x40c000,12288},{0x439000,10240},{0x43fd84,16}})do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local s=emu.getState();returned=s['cpu.a'];ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end
 if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end
end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('STAGECOMPLETE|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(sy.SourceStageCompletion4086_Status)..'|'..dw(sy.SourceScrollerPrefix4086_Completed)..'|'..word(sy.SourceStageProducer4086_Completed)..'|'..returned)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for index,leveltype,mask,roles in itertools.product((33,34),(-1,0,1,2),(0,2,4,8,12,256),(0,1,2,4,8)):
        rows.append(dict(index=index,leveltype=leveltype,mask=mask,roles=roles,slot=0 if roles%2 else 127,dead=0,exists=1,bad='',fault=0))
    for dead,exists,roles in itertools.product((-1,1,65536,0),(0,1,65536),(1,15)):
        rows.append(dict(index=34,leveltype=0,mask=0,roles=roles,slot=127,dead=dead,exists=exists,bad='',fault=0))
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');find=extract(raw,'findent')
    start=raw.index('    if(current_spawn >= level->numspawns',raw.index('void update_scroller()'));end=raw.index('    else if(count_ents(TYPE_ENEMY)',start);block=raw[start:end]
    entries=['{'+','.join(map(str,[c[k]for k in ('index','leveltype','mask','roles','dead','exists')]))+'}'for c in rows]
    code=r'''#include <stdio.h>
#include <string.h>
#define TYPE_NONE 0
#define TYPE_ENEMY 2
#define TYPE_ITEM 4
#define TYPE_OBSTACLE 8
#define TYPE_ENDLEVEL 256
typedef struct entity {int exists;struct {int type;} modeldata;int dead;} entity;
entity pool[128],*ent_list[128];int ent_max=128,current_spawn,level_completed;
struct {entity *ent;} player[4];struct {int numspawns,type;} lev,*level=&lev;
'''+find+'\nvoid check(void){\n'+block+'\n}\nstruct {int index,type,mask,roles,dead,exists;} cases[]={'+','.join(entries)+r'''};
int main(void){unsigned i;int j;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){memset(pool,0,sizeof(pool));for(j=0;j<128;j++)ent_list[j]=&pool[j];pool[0].dead=cases[i].dead;pool[10].exists=cases[i].exists;pool[10].modeldata.type=cases[i].mask;for(j=0;j<4;j++)player[j].ent=(cases[i].roles&(1<<j))?&pool[0]:0;current_spawn=cases[i].index;lev.numspawns=34;lev.type=cases[i].type;level_completed=0;check();printf("%d\n",level_completed);}return 0;}
'''
    (a.output/'completion.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','completion.c','-fe=completion.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'authority-build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('STAGE_COMPLETION_AUTHORITY_BUILD')
    actual=list(map(int,subprocess.check_output([str(a.output/'completion.exe')],cwd=a.output,text=True).splitlines()))
    for c,v in zip(rows,actual):c['expected']=v
    base=dict(index=34,leveltype=0,mask=0,roles=1,slot=127,dead=0,exists=1,bad='',fault=0,expected=1)
    for bad in ('ready','prefix','producer','world','role_high','role_low','role_count','token'):rows.append(dict(base,bad=bad,fault=1))
    sy=symbols(Path('src/main.sym'));entry=sy['SourceStageCompletion4086_Check'];lua=LUA+f"emu.addMemoryCallback(function()local s=emu.getState();cpu={{}};for _,k in ipairs({{'x','y','d','dbr','sp','ps'}})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,{entry},{entry},emu.cpuType.snes,mt)\n"
    r=Reporter('M4-STAGE-COMPLETION',kind='GATE');rom,log=run_fixture(a.rom,a.output,rows,'SourceStageCompletion4086_Check','SourceStageCompletion4086_Ready',0xb5d8,[],lua,r,batch_size=2)
    results=[list(map(int,line.split('STAGECOMPLETE|',1)[1].split('|')))for line in log.splitlines()if 'STAGECOMPLETE|'in line]
    r.check('pinned C completion with all player roles, full-width dead/existence, level/mask conditions, canonical guards and readonly CPU/entity state',len(results)==len(rows)and all(v[:3]==[i,0,0]and(v[3:6]==[3,0,0]if c['fault']else v[3:]==[2,c['expected'],c['expected'],c['expected']])for i,(v,c)in enumerate(zip(results,rows))))
    d=dict(schema='BYOR_4086_STAGE_COMPLETION_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',engine_commit=ENGINE_COMMIT,completion_block_sha256=hashlib.sha256(block.encode()).hexdigest(),cases=len(rows),inputs=rows,results=results,rom_sha256=hashlib.sha256(rom).hexdigest(),combat_and_queue_exhaustion_instrumented=True,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');r.finish()

if __name__=='__main__':main()
