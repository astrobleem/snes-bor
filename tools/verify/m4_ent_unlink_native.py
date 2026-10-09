"""Native literal ent_unlink with complete neighboring actor/CPU observation."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_ent_unlink_native import emit
from source_foreign_water_retirement import emit as water,transform as retire_water
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_animation_init_native import luav


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);sy=symbols(Path('src/main.sym'))
 rows=[dict(slot=s,link=l,exists=e,fault=0,bad='')for s,l,e in itertools.product((0,1,2,63,126,127),(-1,0,1,63,127),(0,-1))if l!=s]
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');body=extract(raw,'ent_unlink')
 code='#include <stdio.h>\ntypedef struct entity{struct entity *link,*grabbing;int exists,dead;}entity;entity es[128];\n'+body+"""
int main(void){int i,j,l;int rows[][3]={
"""+',\n'.join('{'+','.join(str(c[k])for k in ('slot','link','exists'))+'}'for c in rows)+"""};
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
for(j=0;j<128;j++){es[j].link=0;es[j].grabbing=es+(j+7)%128;es[j].exists=rows[i][2];es[j].dead=1;}
l=rows[i][1]==128?rows[i][0]:rows[i][1];es[rows[i][0]].link=l<0?0:es+l;
if(l>=0&&l!=rows[i][0])es[l].link=es+(l+3)%128;
ent_unlink(es+rows[i][0]);for(j=0;j<128;j++)printf("%s%d,%d",j?",":"",es[j].link?(int)(es[j].link-es):-1,es[j].grabbing?(int)(es[j].grabbing-es):-1);puts("");}
return 0;}
"""
 (a.output/'unlink.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');run=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','unlink.c','-fe=unlink.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build-authority.log').write_text(run.stdout+run.stderr);assert run.returncode==0,run.stdout+run.stderr
 log=subprocess.check_output([str(a.output/'unlink.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log)
 for c,l in zip(rows,log.splitlines()):c['expected']=list(map(int,l.split(',')))
 assert len(log.splitlines())==len(rows)
 nominal=len(rows);seed=next(c for c in rows if c['slot']==0 and c['link']==63)
 rows.extend(dict(seed,fault=1,bad=b)for b in ('ready','base','count','slot','token','linkbank','linkalign','linkfrontier','linktoken','generation','selflink'))
 lua='local extra='+luav({k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'})+'\nfor k,v in pairs(extra)do sy[k]=v end\n'
 lua+=r'''
local mt=emu.memType.snesMemory;local before,cpu,ctx={},{},0
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n)end
local function token(i)return i<0 and 0 or 0x414000+80*i end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000)
 set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4);put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do set(n,0)end;for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 for i=0,127 do put(0x414000+80*i,token(i),4);put(0x414004+80*i,c.exists,4);put(0x439014+80*i,1,4);put(0x40901c+64*i,0,4);put(0x40c050+96*i,token((i+7)%128),4)end
 local link=c.link==128 and c.slot or c.link
 put(0x40901c+64*c.slot,token(link),4)
 if link>=0 and link~=c.slot then put(0x40901c+64*link,token((link+3)%128),4)end
 put(SLOT,c.bad=='slot'and 128 or c.slot)
 if c.bad=='ready'then set('VmSourceWorld_Ready',0)elseif c.bad=='base'then set('VmSourceWorld_PoolBase',0)elseif c.bad=='count'then set('VmSourceWorld_Count',129)elseif c.bad=='token'then put(0x414000+80*c.slot,token(c.slot)+1,4)elseif c.bad=='linkbank'then put(0x40901c+64*c.slot,0x424000,4)elseif c.bad=='linkalign'then put(0x40901c+64*c.slot,token(link)+1,4)elseif c.bad=='linkfrontier'then set('VmSourceWorld_Count',link)elseif c.bad=='linktoken'then put(0x414000+80*link,token(link)+1,4)elseif c.bad=='selflink'then put(0x40901c+64*c.slot,token(c.slot),4)end
 put(GEN,c.bad=='generation'and 2 or 1,4)
 before={};for _,r in ipairs({{0x414000,18432},{0x40c000,12288},{0x409000,8192},{0x439000,10240}})do for j=0,r[2]-1 do before[r[1]+j]=emu.read(r[1]+j,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1]
 if c.fault==0 then for i=0,127 do for _,f in ipairs({{0x40901c+64*i,token(c.expected[2*i+1])},{0x40c050+96*i,token(c.expected[2*i+2])}})do for j=0,3 do before[f[1]+j]=(f[2]>>(8*j))&255 end end end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end;emu.log('UNLINKRESULT|'..word(INDEX)..'|'..ctx..'|'..n)
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 slot,gen=0x7ffd90,0x7ffd92;lua=lua.replace('SLOT',str(slot)).replace('GEN',str(gen))
 wrapper=f'''UnlinkProbe:
.a16
.i16
 php
 rep #$39
 phx
 phy
 lda.l {gen}
 tax
 lda.l {gen}+2
 tay
 lda.l {slot}
 jsl EntUnlink_Run
 bcs UnlinkProbe_Bad
 ply
 plx
 plp
 clc
 rtl
UnlinkProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
 r=Reporter('M4-ENT-UNLINK',kind='GATE');raw,log=run_fixture(a.rom,a.output,rows,'UnlinkProbe','VmSourceWorld_Ready',0xb4a3,[],lua,r,append=wrapper+emit(sy)+water(sy),rom_transform=retire_water,link_pcm=False,batch_size=4,frame_limit=10000)
 results=[list(map(int,l.split('UNLINKRESULT|')[1].split('|')))for l in log.splitlines()if'UNLINKRESULT|'in l];ok=results==[[i,0,0]for i in range(len(rows))];r.check('literal source linked/target clearing with inactive and dead actors; self-link source NULL-dereference domain rejected; all malformed pointers reject before writes; complete neighbor and CPU state',ok)
 report=dict(schema='BYOR_ENT_UNLINK_NATIVE_V1',status='PASS'if ok else'FAIL',cases=len(rows),source_C_cases=nominal,inputs=rows,results=results,source_function_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),rom_sha256=hashlib.sha256(raw).hexdigest(),self_link_domain_rejected=True,common_damage_tail_bound=False,pain_fall_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True);(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()


if __name__=='__main__':main()
