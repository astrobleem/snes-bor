"""Pinned player wrapper force copy, with physical type and captured globals."""
import argparse,hashlib,itertools,json,os,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_player_damage_force_native import emit
from source_foreign_state_layout import layout
from source_foreign_water_retirement import emit as water,transform as retire_water
from actor_s5_entity_fixture import symbols
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--reuse-proof',action='store_true',help='Reparse retained native evidence when the emitted assembly is identical.')
 for k in('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);sy=symbols(Path('src/main.sym'));work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='attack_chain_controls')
 rows=[dict(slot=s,other=(s+1)%128,force=f,cheat=hc,nohurt=nh,type=t,fault=0,bad='')for s,f,hc,nh,t in itertools.product((0,127),(-2147483648,-1,0,14,2147483647),(0,1,-1,2147483647,-2147483648),(0,1,-1),(0,1,2,3,4,6,-2147483648))]
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');body=extract(raw,'player_takedamage')
 code='''#include <stdio.h>
#include <stdlib.h>
#define TYPE_ENEMY 2
typedef struct {int attack_force,other_field;}s_attack;
typedef struct {struct {int type;}modeldata;}entity;
struct {int nohurt;}lev,*level=&lev;int healthcheat;
int common_takedamage(entity*other,s_attack*a){if(a->other_field!=17)exit(7);return a->attack_force;}
'''+body+'\nint main(void){entity other;s_attack a;int i,r;int rows[][4]={\n'+',\n'.join('{'+','.join('(-2147483647-1)'if c[k]==-2147483648 else str(c[k])for k in('force','cheat','nohurt','type'))+'}'for c in rows)+'''};
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){a.attack_force=rows[i][0];a.other_field=17;healthcheat=rows[i][1];level->nohurt=rows[i][2];other.modeldata.type=rows[i][3];r=player_takedamage(&other,&a);if(a.attack_force!=rows[i][0]||a.other_field!=17)return 8;printf("%d\\n",r);}return 0;}
'''
 (a.output/'player_force.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','-op','-fpc','player_force.c','-fe=player_force.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build-authority.log').write_text(b.stdout+b.stderr);assert b.returncode==0,b.stdout+b.stderr
 authority=subprocess.check_output([str(a.output/'player_force.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(authority);values=[int(v)for v in authority.splitlines()];assert len(values)==len(rows)
 for c,v in zip(rows,values):c['expected']=v
 rows.extend(dict(rows[0],bad=bad,fault=1,expected=165*0x1010101)for bad in('ready','generation','self','phase','time','count','slot','other','token','player_type'))
 lua='local extra='+luav({k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'})+'\nfor k,v in pairs(extra)do sy[k]=v end\n'
 lua+=r'''
local mt=emu.memType.snesMemory;local before,cpu,ctx={}, {},0
local ranges={{0x414000,18432},{0x40c000,12288},{W,96}}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for i=0,(n or 2)-1 do emu.write(a+i,(v>>(8*i))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do put(r[1]+i,165,1)end end
 for _,i in ipairs({c.slot,c.other})do put(0x414000+80*i,0x414000+80*i,4)end
 put(0x40c048+96*c.slot,1,4);put(0x40c048+96*c.other,c.type,4)
 put(W+4,c.slot);put(W+6,c.other);put(W+8,1,4);put(W+64,0xb6b2);put(W+66,0);put(W+68,c.force,4);put(W+72,c.cheat,4);put(W+76,c.nohurt,4)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);put(sy.VmSourceWorld_Time,48,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',8);set('SourceWorldTick4086_Fault',0);put(sy.SourceWorldTick4086_TimeLo,48,4)
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Fault',0);put(sy.SourceSelf4086_GlobalLow,0x414000+80*c.slot,4)
 set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4);put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do set(n,0)end;for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 if c.bad=='ready'then put(W+64,0)
 elseif c.bad=='generation'then put(W+8,2,4)
 elseif c.bad=='self'then put(sy.SourceSelf4086_GlobalLow,0,4)
 elseif c.bad=='phase'then set('SourceWorldTick4086_Phase',7)
 elseif c.bad=='time'then put(sy.SourceWorldTick4086_TimeLo,49,4)
 elseif c.bad=='count'then set('VmSourceWorld_Count',129)
 elseif c.bad=='slot'then put(W+4,128)
 elseif c.bad=='other'then put(W+6,128)
 elseif c.bad=='token'then put(0x414000+80*c.other,0,4)
 elseif c.bad=='player_type'then put(0x40c048+96*c.slot,2,4)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];before[W+66]=c.fault==1 and 3 or 2;before[W+67]=0
 if c.fault==0 then for i=0,3 do before[W+80+i]=(c.expected>>(8*i))&255 end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1 end end
 emu.log('PLAYERFORCE|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(W+66))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''.replace('{W,96}','{'+str(work)+',96}')
 import re
 lua=re.sub(r'\bW\b',str(work),lua)
 wrapper='''PlayerForceProbe:
.a16
.i16
 php
 rep #$38
 phx
 phy
 ldx #1
 ldy #0
 jsl PlayerDamageForce_Run
 bcs PlayerForceProbe_Bad
 ply
 plx
 plp
 clc
 rtl
PlayerForceProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
 assembly=wrapper+emit(work,sy)+water(sy);r=Reporter('M4-PLAYER-DAMAGE-FORCE',kind='GATE')
 if a.reuse_proof:
  if assembly not in (a.output/'fixture.pasm').read_text():raise ValueError('PLAYER_FORCE_REUSE_ASSEMBLY_CHANGED')
  rom=(a.output/'bor.sfc').read_bytes();log=(a.output/'mesen.log').read_text()
  r.check('retained native proof has identical emitted assembly and unchanged bank zero',rom[:32768]==a.rom.read_bytes()[:32768])
 else:rom,log=run_fixture(a.rom,a.output,rows,'PlayerForceProbe','SourceWorldTick4086_Ready',0xb4d5,[],lua,r,append=assembly,rom_transform=retire_water,link_pcm=False,frame_limit=10000,batch_size=4)
 results=[list(map(int,line.split('PLAYERFORCE|')[1].split('|')))for line in log.splitlines()if'PLAYERFORCE|'in line];wanted=[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)];r.check('actual source copied force and physical enemy bit; arbitrary signed flags; input/actor/CPU preservation and stale snapshot rejection',results==wanted)
 report=dict(schema='BYOR_PLAYER_DAMAGE_FORCE_NATIVE_V1',status='PASS'if results==wanted else'FAIL',retained_native_evidence_reparsed=a.reuse_proof,engine_commit=ENGINE_COMMIT,source_function_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),rom_sha256=hashlib.sha256(rom).hexdigest(),cases=len(rows),inputs=rows,results=results,expected=wanted,source_player_takedamage_unmodified=True,common_callback_instrumented=True,world_globals_snapshot_installed_by_fixture=True,production_globals_capture_bound=False,full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()


if __name__=='__main__':main()
