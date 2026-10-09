"""Source checkdamage arithmetic versus native health publication and guards."""
import argparse,hashlib,itertools,json,os,re,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from compiler import Source
from source_combat_health_native import derive,emit
from source_foreign_state_layout import layout
from actor_s5_entity_fixture import symbols
from script_nested_authority import extract
from m4_animation_init_native import luav
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from source_foreign_water_retirement import emit as water,transform as retire_water


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
 for k in('rom','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);req=derive(Source(a.source));sy=symbols(Path('src/main.sym'));work=next(r['address']for r in layout(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'])['regions']if r['name']=='attack_chain_controls')
 base=dict(slot=0,other=127,health=100,force=7,maxhp=300,inv=0,alt=0,life=0,nokill=0,fault=0,bad='')
 rows=[dict(base,slot=slot,other=(slot+1)%128,health=hp,force=f,inv=inv,nokill=nk)for slot,hp,f,inv,nk in itertools.product((0,1,127),(-300,0,1,100,300),(-8388608,-300,-1,0,1,7,300,8388607),(0,2,3),(0,1))]
 rows.extend(dict(base,slot=slot,other=(slot+1)%128,health=1,force=7,inv=inv,alt=alt,life=life)for slot,inv,alt,life in itertools.product((0,1,127),(2,3),(-251*65536,-250*65536-1,-250*65536,-250*65536+1,-249*65536),(-1,0)))
 rows.extend(dict(base,health=hp,force=f)for hp,f in((-2147483648+8388608,8388607),(2147483647-8388608,-8388608),(2147483647,0),(-2147483648,0)))
 raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',req['engine_commit']+':engine/openbor.c']).decode('latin1');body=extract(raw,'checkdamage')
 c='''#include <stdio.h>
#include <string.h>
#define PIT_DEPTH -250
typedef struct {int attack_force,attack_type,no_kill,attack_drop,no_block,guardcost,jugglecost,pause_add;}s_attack;
typedef struct entity {int health,invincible,lifespancountdown;struct {struct {int max,current;}guardpoints;int health;}modeldata;struct {float factor;}defense[20];float offense_factors[20];struct {float y;}position;}entity;
entity victim,opponent,*self=&victim;int max_attack_types=20,damage_calls,death_calls;
void execute_takedamage_script(entity*a,entity*b,int c,int d,int e,int f,int g,int h,int i){damage_calls++;}
void execute_ondeath_script(entity*a,entity*b,int c,int d,int e,int f,int g,int h,int i){death_calls++;}
'''+body+'''\nint main(void){s_attack a;unsigned i,j;int rows[][7]={\n'''+',\n'.join('{'+','.join(str(c[k])for k in('health','force','maxhp','inv','alt','life','nokill'))+'}'for c in rows)+'''};
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){memset(&victim,0,sizeof(victim));memset(&opponent,0,sizeof(opponent));memset(&a,0,sizeof(a));for(j=0;j<20;j++){victim.defense[j].factor=1;opponent.offense_factors[j]=1;}victim.health=rows[i][0];a.attack_force=rows[i][1];victim.modeldata.health=rows[i][2];victim.invincible=rows[i][3];victim.position.y=rows[i][4]/65536.0f;victim.lifespancountdown=rows[i][5];a.no_kill=rows[i][6];damage_calls=death_calls=0;checkdamage(&opponent,&a);printf("%d,%d,%d\\n",victim.health,damage_calls,death_calls);}return 0;}
'''
 authority_c=c;(a.output/'health.c').write_text(authority_c);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','-op','-fpc','health.c','-fe=health.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build-authority.log').write_text(b.stdout+b.stderr);assert b.returncode==0,b.stdout+b.stderr
 actual=subprocess.check_output([str(a.output/'health.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(actual);values=[list(map(int,l.split(',')))for l in actual.splitlines()];assert len(values)==len(rows)
 for c,v in zip(rows,values):c['expected']=v[0]
 seed=rows[0]
 for bad in('ready','generation','self','phase','time','count','slot','other','token','health_tag','max_tag','alt_tag','factor_marker','factor_model','factor_defense','factor_offense','script_ready','script_mask','script_clear','script_onkill','life_marker','life_model','force_high','subtract_overflow'):
  c=dict(seed,bad=bad,fault=1,expected=seed['health'])
  if bad=='subtract_overflow':c.update(health=-2147483648,force=1,expected=-2147483648)
  rows.append(c)
 lua='local extra='+luav({k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'})+'\nfor k,v in pairs(extra)do sy[k]=v end\n'
 lua+=r'''
local mt=emu.memType.snesMemory;local before,cpu,ctx={}, {},0
local ranges={{0x414000,18432},{0x432800,4096},{0x43b900,512},{0x439000,10240},{0x409000,8192}}
local function word(a)return emu.read(a,mt)|(emu.read(a+1,mt)<<8)end
local function put(a,v,n)for j=0,(n or 2)-1 do emu.write(a+j,(v>>(8*j))&255,mt)end end
local function set(k,v,n)put(sy[k],v,n)end
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];put(EXPECTFAULT,c.fault)
 for _,r in ipairs(ranges)do for i=0,r[2]-1 do put(r[1]+i,165,1)end end
 for i=0,127 do
  local v=0x414000+80*i;put(v,v,4);put(v+8,2,4);put(v+12,0,4);put(v+32,1,4);put(v+36,100,4);put(v+64,1,4);put(v+68,300,4)
  put(0x416800+64*i,0);put(0x416810+64*i,0,4);put(0x43b900+4*i,0);put(0x43b902+4*i,0xb5f1)
  put(0x432800+32*i,0x3f800000,4);put(0x43281c+32*i,0x3f800000,4);put(0x439018+80*i,0,4);put(0x439048+80*i,0);put(0x43904a+80*i,0xb4fb)
  for j=44,55 do put(0x409000+64*i+j,0,1)end;put(0x40902c+64*i,1)
 end
 local v=0x414000+80*c.slot;put(v+36,c.health,4);put(v+68,c.maxhp,4);put(v+12,c.alt,4);put(0x416810+64*c.slot,c.life,4);put(0x439018+80*c.slot,c.inv,4)
 put(W,0xb6b0);put(W+2,0);put(W+4,c.slot);put(W+6,c.other);put(W+8,1,4);put(W+12,c.force,4);put(W+16,c.nokill,4)
 set('VmSourceWorld_Ready',0xb4a3);set('VmSourceWorld_Count',128);set('VmSourceWorld_PoolBase',0x4000);set('VmSourceWorld_SideBase',0x6800);put(sy.VmSourceWorld_Time,48,4)
 set('SourceWorldTick4086_Ready',0xb4d5);set('SourceWorldTick4086_State',1);set('SourceWorldTick4086_Pending',1);set('SourceWorldTick4086_Phase',8);set('SourceWorldTick4086_Fault',0);put(sy.SourceWorldTick4086_TimeLo,48,4)
 set('SourceSelf4086_Ready',0xb4f6);set('SourceSelf4086_Fault',0);put(sy.SourceSelf4086_GlobalLow,v,4);set('SourceFactors4086_Ready',0xb5f1);set('SourceFactors4086_Models',MODELS);set('SourceScriptClone4086_Ready',0xb5c1);set('SourceLifecycle4086_Ready',0xb4fb)
 set('SourceForeignWork_Ready',0xb671);put(sy.SourceForeignWork_Generation,1,4)
 put(0x7ff840,0xb4b0);put(0x7ff862,0xb4b1);put(0x7ff856,0);put(0x7ff866,0xb672);put(0x7ff846,0x30)
 for _,n in ipairs({'StageFp_BG2Loaded','StageFp_BG2Active','StageFp_BG2DmaPending','StageFp_BG2Booting','StreamScrollFp_ColPending','StreamScrollFp_Enabled'})do set(n,0)end
 for i=0,7 do put(sy.DmaQueue+8*i+7,0,1)end
 if c.bad=='ready'then put(W,0)
 elseif c.bad=='generation'then put(W+8,2,4)
 elseif c.bad=='self'then put(sy.SourceSelf4086_GlobalLow,0,4)
 elseif c.bad=='phase'then set('SourceWorldTick4086_Phase',7)
 elseif c.bad=='time'then put(sy.SourceWorldTick4086_TimeLo,49,4)
 elseif c.bad=='count'then set('VmSourceWorld_Count',129)
 elseif c.bad=='slot'then put(W+4,128)
 elseif c.bad=='other'then put(W+6,128)
 elseif c.bad=='token'then put(v,0,4)
 elseif c.bad=='health_tag'then put(v+32,2)
 elseif c.bad=='max_tag'then put(v+64,2)
 elseif c.bad=='alt_tag'then put(v+8,1)
 elseif c.bad=='factor_marker'then put(0x43b902+4*c.slot,0)
 elseif c.bad=='factor_model'then put(0x43b900+4*c.slot,1)
 elseif c.bad=='factor_defense'then put(0x432800+32*c.slot,0,4)
 elseif c.bad=='factor_offense'then put(0x43281c+32*c.other,0,4)
 elseif c.bad=='script_ready'then set('SourceScriptClone4086_Ready',0)
 elseif c.bad=='script_mask'then put(0x40902c+64*c.slot,2)
 elseif c.bad=='script_clear'then put(0x409030+64*c.slot,1)
 elseif c.bad=='script_onkill'then put(0x409034+64*c.slot,1)
 elseif c.bad=='life_marker'then put(0x43904a+80*c.slot,0)
 elseif c.bad=='life_model'then put(0x439048+80*c.slot,1)
 elseif c.bad=='force_high'then put(W+12,8388608,4)end
 before={};for _,r in ipairs(ranges)do for i=0,r[2]-1 do before[r[1]+i]=emu.read(r[1]+i,mt)end end
end,emu.callbackType.exec,INIT,INIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();cpu={};for _,k in ipairs({'x','y','d','dbr','sp','ps'})do cpu[k]=s['cpu.'..k]end;cpu.sp=cpu.sp+3 end,emu.callbackType.exec,APPLY,APPLY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local s=emu.getState();ctx=0;for _,k in ipairs({'x','y','d','dbr','sp'})do if cpu[k]~=s['cpu.'..k]then ctx=ctx+1 end end;if(cpu.ps&254)~=(s['cpu.ps']&254)then ctx=ctx+1 end end,emu.callbackType.exec,AFTER,AFTER,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 local c=rows[word(INDEX)+1];if c.fault==0 then for i=0,3 do before[0x414024+80*c.slot+i]=(c.expected>>(8*i))&255 end end
 local n=0;for a,v in pairs(before)do if emu.read(a,mt)~=v then n=n+1;if n<4 then emu.log('HEALTHDIFF|'..word(INDEX)..'|'..a..'|'..emu.read(a,mt)..'|'..v)end end end
 emu.log('HEALTHRESULT|'..word(INDEX)..'|'..n..'|'..ctx..'|'..word(W+2))
end,emu.callbackType.exec,RESULT,RESULT,emu.cpuType.snes,mt)
'''
 lua=re.sub(r'\bW\b',str(work),lua).replace('MODELS',str(len(req['models'])))
 wrapper='''HealthProbe:
.a16
.i16
 php
 rep #$38
 phx
 phy
 ldx #1
 ldy #0
 jsl CombatHealth_Run
 bcs HealthProbe_Bad
 ply
 plx
 plp
 clc
 rtl
HealthProbe_Bad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
'''
 assembly=wrapper+emit(req,work,sy)+water(sy);probes={}
 for n in re.findall(r'^CombatHealth_Guard(\d+):',assembly,re.M):
  probes['HG'+n]='CombatHealth_Guard'+n
  lua+=f'\nemu.addMemoryCallback(function()if word(INDEX)==0 then emu.log("HEALTHGUARD|{n}|"..emu.getState()["cpu.a"])end end,emu.callbackType.exec,HG{n},HG{n},emu.cpuType.snes,mt)\n'
 probes['HBAD']='CombatHealth_Bad'
 lua+='\nemu.addMemoryCallback(function()emu.log("HEALTHFAULT|"..word(INDEX).."|"..emu.getState()["cpu.a"])end,emu.callbackType.exec,HBAD,HBAD,emu.cpuType.snes,mt)\n'
 r=Reporter('M4-COMBAT-HEALTH',kind='GATE');rom,log=run_fixture(a.rom,a.output,rows,'HealthProbe','SourceWorldTick4086_Ready',0xb4d5,[],lua,r,batch_size=4,append=assembly,probes=probes,rom_transform=retire_water,link_pcm=False,frame_limit=10000)
 results=[list(map(int,l.split('HEALTHRESULT|',1)[1].split('|')))for l in log.splitlines()if'HEALTHRESULT|'in l];expected=[[i,0,0,3 if c['fault']else 2]for i,c in enumerate(rows)];r.check('actual pinned checkdamage health, caps and invincibility; typed ownership/factor/script/overflow guards; retained neighboring rows and CPU',results==expected)
 report=dict(schema='BYOR_COMBAT_HEALTH_NATIVE_V1',status='PASS'if results==expected else'FAIL',cases=len(rows),inputs=rows,results=results,expected=expected,requirements=req,rom_sha256=hashlib.sha256(rom).hexdigest(),authority_c_sha256=hashlib.sha256(authority_c.encode()).hexdigest(),unmodified_source_checkdamage=True,damage_script_calls_instrumented_as_absent=True,full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_pcm_copies=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');r.finish()


if __name__=='__main__':main()
