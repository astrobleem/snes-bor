"""Literal source count_ents versus the readonly admitted native pool."""
import argparse,hashlib,itertools,json,os,re,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_count_entities_native import emit
from source_foreign_water_retirement import emit as water,transform as retire_water
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_animation_init_native import luav


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);sy=symbols(Path('src/main.sym'))
 rows=[dict(count=c,mask=m,pattern=pat,fault=0,bad='')for c,m,pat in itertools.product((0,1,2,63,127,128),(0,1,2,3,4,-1,-2147483648),(0,1,2,3))]
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');body=extract(raw,'count_ents')
 code='''#include <stdio.h>
#include <string.h>
typedef struct{int exists,dead;struct{int type;}modeldata;}entity;entity ents[128],*ent_list[128];int ent_max=128;
'''+body+'''
int main(void){int i,j;int rows[][3]={
'''+',\n'.join('{'+','.join('(-2147483647-1)'if c[k]==-2147483648 else str(c[k])for k in ('count','mask','pattern'))+'}'for c in rows)+'''};
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
for(j=0;j<128;j++){ent_list[j]=ents+j;ents[j].exists=j>=rows[i][0]?0:rows[i][2]==0?1:rows[i][2]==1?j%2:rows[i][2]==2?-1:1;ents[j].dead=j%2;ents[j].modeldata.type=rows[i][2]==3?(-2147483647-1):1<<(j%5);}
printf("%d\\n",count_ents(rows[i][1]));}return 0;}
'''
 (a.output/'count.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');p=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','count.c','-fe=count.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build-authority.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stdout+p.stderr
 log=subprocess.check_output([str(a.output/'count.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);values=[int(l)for l in log.splitlines()];assert len(values)==len(rows)
 for c,v in zip(rows,values):c['expected']=v
 seed=next(c for c in rows if c['count']==128 and c['mask']==1 and c['pattern']==0)
 rows.extend(dict(seed,bad=bad,fault=1)for bad in ('ready','base','count','token','frontier'))
 lua='local extra='+luav({k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'})+'\nfor k,v in pairs(extra)do sy[k]=v end\n'
 lua+=r'''
local mt=emu.memType.snesMemory;local before,cpu,ctx={},{},0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n)end
emu.addMemoryCallback(function()
 emu.log('COUNTINIT|'..word(INDEX));local ok,err=pcall(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault);emu.log('COUNTSETUPFIRST|'..word(EXPECTFAULT))
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',c.count);set('VmSourceWorld_PoolBase',0x4000)
 set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4);put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do set(n,0)end;for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 for i=0,127 do
  local exists=i>=c.count and 0 or c.pattern==0 and 1 or c.pattern==1 and i%2 or c.pattern==2 and -1 or 1
  local typ=c.pattern==3 and -2147483648 or (1<<(i%5))
  put(0x414000+80*i,0x414000+80*i,4);put(0x414004+80*i,exists,4);put(0x40c048+96*i,typ,4);put(0x439014+80*i,i%2,4)
 end
 put(MASK,c.mask,4)
 if c.bad=='ready'then set('VmSourceWorld_Ready',0)
 elseif c.bad=='base'then set('VmSourceWorld_PoolBase',0)
 elseif c.bad=='count'then set('VmSourceWorld_Count',129)
 elseif c.bad=='token'then put(0x414000,0x414001,4)
 elseif c.bad=='frontier'then set('VmSourceWorld_Count',127)end
 before={};for _,r in ipairs({{0x414000,18432},{0x40c000,12288},{0x439000,10240}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
emu.log('COUNTSETUPDONE|'..word(sy.SourceForeignWork_Generation)..'|'..word(0x7ffd90))
end);if not ok then emu.log('COUNTSETUPERROR|'..tostring(err))end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end;emu.log('COUNTRESULT|'..word(INDEX)..'|'..s['cpu.a']..'|'..ctx)end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end;emu.log('COUNTWRITES|'..word(INDEX)..'|'..n)end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 mask=0x7ffd90;lua=lua.replace('MASK',str(mask));wrapper=f'''CountProbe:
.a16
.i16
 php
 rep #$39
 phx
 phy
 lda.l {mask}+2
 tay
 lda.l {mask}
 jsl CountEntities_Run
 bcs CountProbe_Bad
 ply
 plx
 plp
 clc
 rtl
CountProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
 r=Reporter('M4-COUNT-ENTITIES',kind='GATE');assembly=wrapper+emit(sy)+water(sy);probes={}
 for n in re.findall(r'^CountEntities_Guard(\d+):',assembly,re.M):
  probes['CG'+n]='CountEntities_Guard'+n
  lua+=f'\nemu.addMemoryCallback(function()if word(INDEX)==0 then emu.log("COUNTGUARD|{n}|"..emu.getState()["cpu.a"])end end,emu.callbackType.exec,CG{n},CG{n},emu.cpuType.snes,mt)\n'
 probes['CBAD']='CountEntities_Bad'
 lua+='\nemu.addMemoryCallback(function()emu.log("COUNTFAULT|"..word(INDEX))end,emu.callbackType.exec,CBAD,CBAD,emu.cpuType.snes,mt)\n'
 raw,log=run_fixture(a.rom,a.output,rows,'CountProbe','VmSourceWorld_Ready',0xb4a3,[],lua,r,append=assembly,probes=probes,rom_transform=retire_water,link_pcm=False,batch_size=4,frame_limit=10000)
 results=[list(map(int,l.split('COUNTRESULT|')[1].split('|')))for l in log.splitlines()if'COUNTRESULT|'in l];writes=[list(map(int,l.split('COUNTWRITES|')[1].split('|')))for l in log.splitlines()if'COUNTWRITES|'in l]
 ok=len(results)==len(rows)and all(v[0]==i and v[2]==0 and (c['fault']or v[1]==c['expected'])for i,(c,v)in enumerate(zip(rows,results)))and writes==[[i,0]for i in range(len(rows))];r.check('unmodified source full signed masks, literal exists including negative truth and dead corpses; active-frontier/token guards; readonly all actors and CPU context',ok)
 report=dict(schema='BYOR_COUNT_ENTITIES_NATIVE_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,results=results,writes=writes,source_function_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),source_ent_max_domain=128,active_frontier_invariant_checked=True,rom_sha256=hashlib.sha256(raw).hexdigest(),native_item_drop_bound=False,native_boss_completion_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()


if __name__=='__main__':main()
