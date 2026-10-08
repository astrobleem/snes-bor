"""Pinned full damage callbacks for positive self-inflicted landing attacks.

Damage/drop/death and MP/score helpers execute verbatim. Effect, weapon,
script, score/audio and controller services are explicitly instrumented;
this proves callback ordering and scalar behavior, not those service bodies.
"""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

PREAMBLE=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define TYPE_PLAYER 1
#define TYPE_ENEMY 2
#define ATK_NORMAL 0
#define ATK_LAND 16
#define DIRECTION_RIGHT 1
#define DIRECTION_LEFT 0
#define DIRECTION_ADJUST_NONE 0
#define DIRECTION_ADJUST_SAME 1
#define DIRECTION_ADJUST_OPPOSITE 2
#define DIRECTION_ADJUST_RIGHT 3
#define DIRECTION_ADJUST_LEFT 4
#define WEAPLOSS_TYPE_ANY 0
#define WEAPLOSS_TYPE_KNOCKDOWN 1
#define WEAPLOSS_TYPE_DEATH 2
#define PIT_DEPTH -250
#define GAME_SPEED 200
#define GRAB_STALL 160
typedef struct entity entity;
typedef struct {float x,z,y;} Vec;
typedef struct {int attack_force,attack_type,attack_drop,no_pain,no_kill,no_block,guardcost,jugglecost,pause_add,grab,damage_on_landing,force_direction;float grab_distance;Vec dropv;} s_attack;
typedef struct {int type,health,mp,mprate,nopain,noflip,animal,escapehits,falldie,diesound,score,multiple,weaploss[3];float knockdowncount;struct{int max,current;}guardpoints;int subject_to_wall,subject_to_platform,subject_to_hole,subject_to_gravity,no_adjust_base;} Model;
struct entity {Model modeldata;Vec position,velocity;float offense_factors[20];struct{float factor,knockdown,pain;}defense[20];int exists,dead,toexplode,drop,frozen,damagetype,health,mp,damage_on_landing,direction,invincible,playerindex,nograb,idling,boss,itemplayer_count,multiple,escapecount,lifespancountdown;float knockdowncount;unsigned knockdowntime,stalltime,releasetime;entity *opponent,*grabbing,*item;void(*takeaction)(void);};
entity victim,opponent,*self;struct{int nohurt,bosses;}lev,*level=&lev;
int healthcheat,max_attack_types=20,magic_type=0,level_completed;
unsigned time=48;struct{int effectvol;}savedata;
int events[256],ne,script_force,script_type,score_total,rumble_last;void event(int n){events[ne++]=n;}
void unexpected(void){fprintf(stderr,"UNEXPECTED_NONLANDING_CALLBACK_BRANCH\n");exit(9);}
int common_takedamage(entity*,s_attack*);
int cangrab(entity *e,entity *o){unexpected();return 0;}
int adjust_grabposition(entity *e,entity *o,float distance,int grab){unexpected();return 0;}
void ents_link(entity *e,entity *o){unexpected();}
void set_opponent(entity *e,entity *o){unexpected();}
void dropweapon(int n){event(2);}
void checkdamageeffects(s_attack *a){event(3);}
void execute_takedamage_script(entity *e,entity *o,int f,int d,int t,int b,int g,int j,int p){if(t!=ATK_LAND||d||b||g||j||p)unexpected();script_force=f;script_type=t;event(5);}
void execute_ondeath_script(entity *e,entity *o,int f,int d,int t,int b,int g,int j,int p){event(6);}
void addscore(int player,int score){score_total+=score;event(7);}
void control_rumble(int player,int force){rumble_last=force;event(8);}
void sound_play_sample(int sample,int loop,int l,int r,int speed){event(9);}
int count_ents(int t){unexpected();return 0;}
void drop_item(entity *e){unexpected();}
void kill_all_enemies(void){unexpected();}
void kill(entity *e){unexpected();}
void player_die(void){unexpected();}
void ent_unlink(entity *e){unexpected();}
void common_fall(void){unexpected();}
void common_pain(void){unexpected();}
void common_grabattack(void){unexpected();}
void set_death(entity *e,int t,int r){unexpected();}
void toss(entity *e,float f){unexpected();}
int set_fall(entity *e,int t,int r,entity *o,int f,int d,int b,int g,int j,int p){unexpected();return 0;}
void set_pain(entity *e,int t,int r){unexpected();}
'''


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'))
 p.add_argument('--output',type=Path,required=True)
 p.add_argument('--empty-damage-scripts',action='store_true',help='Execute both actual script dispatchers with uninitialized source script instances.')
 p.add_argument('--weaploss',type=int,choices=(0,1,2,3),default=0)
 p.add_argument('--score-body',action='store_true',help='Couple actual addscore and pinned SDL rumble with zero initialized scores and no score scripts.')
 p.add_argument('--model-multiple',type=int,choices=(0,1,2,5),default=2)
 p.add_argument('--model-score',type=int,default=0)
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 if not 0<=a.model_score<=1000:raise ValueError('CALLBACK_SCORE_FIXTURE_BELOW_EXTRA_LIFE_DOMAIN')
 if a.score_body and not a.empty_damage_scripts:raise ValueError('SCORE_BODY_REQUIRES_ACTUAL_EMPTY_SCRIPT_DISPATCHERS')
 raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
 names=('checkgrab','checkdamageflip','checkdamagedrop','checkmpadd','checkhitscore','checkdamage','checkdeath','common_takedamage','player_takedamage','arrow_takedamage')
 bodies={n:extract(raw,n)for n in names};pre=PREAMBLE
 if a.empty_damage_scripts:
  script_raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openborscript.c']).decode('latin1')
  bodies['Script_IsInitialized']=extract(script_raw,'Script_IsInitialized')
  for n in ('execute_takedamage_script','execute_ondeath_script'):bodies[n]=extract(raw,n)
  pre=pre.replace('typedef struct entity entity;',r'''
#define VOID void
#define LONG long
#define VT_PTR 2
#define VT_INTEGER 1
typedef struct {int initialized;} Script;
typedef struct {void *ptrVal;long lVal;} ScriptVariant;
typedef struct {Script *takedamage_script,*ondeath_script;} ScriptSet;
Script damage_script,death_script;ScriptSet script_set={&damage_script,&death_script};
typedef struct entity entity;
''').replace('struct entity {Model modeldata;','struct entity {ScriptSet *scripts;Model modeldata;')
  pre='\n'.join(line for line in pre.splitlines()if not line.startswith(('void execute_takedamage_script(','void execute_ondeath_script(')))+'\n'
  pre+=r'''
void ScriptVariant_Init(ScriptVariant *v){unexpected();}
void ScriptVariant_ChangeType(ScriptVariant *v,int t){unexpected();}
void Script_Set_Local_Variant(Script *s,char *n,ScriptVariant *v){unexpected();}
void Script_Execute(Script *s){unexpected();}
void ScriptVariant_Clear(ScriptVariant *v){unexpected();}
int Script_IsInitialized(Script *s);
void execute_takedamage_script(entity*,entity*,int,int,int,int,int,int,int);
void execute_ondeath_script(entity*,entity*,int,int,int,int,int,int,int);
'''
 if a.score_body:
  bodies['addscore']=extract(raw,'addscore')
  controller=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/sdl/control.c']).decode('latin1')
  bodies['control_rumble']=extract(controller,'control_rumble')
  pre='\n'.join(line for line in pre.splitlines()if not line.startswith(('void addscore(','void control_rumble(')))+'\n'
  pre+='struct{unsigned score;int lives;}player[4];Script score_script[4];unsigned lifescore=50000;int SAMPLE_1UP=27;\nvoid addscore(int,int);void control_rumble(int,int);\n'
 code=pre+'\n'.join(bodies.values())
 rows=[dict(zip(('callback','health','force','guardbreak','invincible','cheat','opponent'),v))for v in itertools.product(range(3),(1,100,300),(1,7,150),(0,1),(0,2,3),(0,1),range(4))]
 code+='\nstruct Case{int callback,health,force,guardbreak,invincible,cheat,opponent;}cases[]={\n'
 code+=',\n'.join('{'+','.join(str(v)for v in r.values())+'}'for r in rows)
 code+=r'''};
int main(void){unsigned i;int j,ret;struct Case *c;s_attack attack;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
c=cases+i;memset(&victim,0,sizeof(victim));memset(&opponent,0,sizeof(opponent));memset(&attack,0,sizeof(attack));memset(&lev,0,sizeof(lev));ne=script_force=script_type=score_total=rumble_last=0;self=&victim;
victim.exists=1;victim.health=c->health;victim.modeldata.health=300;victim.modeldata.diesound=-1;victim.modeldata.type=c->callback==1?TYPE_PLAYER:TYPE_ENEMY;
victim.modeldata.no_adjust_base=1;victim.modeldata.guardpoints.max=c->guardbreak;victim.modeldata.guardpoints.current=0;
victim.invincible=c->invincible;victim.idling=1;victim.damage_on_landing=c->force;victim.knockdowncount=3;victim.modeldata.knockdowncount=3;victim.knockdowntime=47;victim.modeldata.multiple=2;
victim.defense[ATK_LAND].factor=1;victim.defense[ATK_LAND].knockdown=1;victim.offense_factors[ATK_LAND]=1;
opponent.modeldata.type=c->opponent==2?TYPE_PLAYER:TYPE_ENEMY;
victim.opponent=c->opponent==0?NULL:c->opponent==1?self:&opponent;
healthcheat=c->cheat;attack.attack_force=c->force;attack.attack_type=ATK_LAND;
ret=c->callback==0?common_takedamage(self,&attack):c->callback==1?player_takedamage(self,&attack):arrow_takedamage(self,&attack);
printf("CALLBACK|%u|%d,%d,%d,%d,%d,%d,%d,%u,%d,%d,%d,%d,%d|",i,ret,victim.health,victim.dead,victim.nograb,victim.idling,victim.damage_on_landing,(int)victim.knockdowncount,victim.knockdowntime,victim.damagetype,victim.modeldata.no_adjust_base,victim.modeldata.subject_to_gravity,victim.modeldata.subject_to_platform,victim.modeldata.subject_to_hole);
printf("%d,%d,%d,%d|",script_force,script_type,score_total,rumble_last);
for(j=0;j<ne;j++)printf("%s%d",j?",":"",events[j]);puts("");
 }return 0;}'''
 if a.empty_damage_scripts:code=code.replace('victim.exists=1;','victim.scripts=&script_set;victim.exists=1;')
 code=code.replace('victim.exists=1;','victim.modeldata.weaploss[0]='+str(a.weaploss)+';victim.exists=1;')
 if a.score_body:
  code=code.replace('self=&victim;','self=&victim;memset(player,0,sizeof(player));')
  code=code.replace('printf("CALLBACK|','score_total=player[0].score;printf("CALLBACK|')
 code=code.replace('victim.modeldata.multiple=2;','victim.modeldata.multiple='+str(a.model_multiple)+';victim.modeldata.score='+str(a.model_score)+';')
 (a.output/'callback.c').write_text(code+'\n')
 env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','-op','-fpc','callback.c','-fe=callback.exe'],cwd=a.output,env=env,capture_output=True,text=True)
 (a.output/'build.log').write_text(build.stdout+build.stderr)
 if build.returncode:raise ValueError('LANDING_CALLBACK_C_BUILD:'+build.stdout+build.stderr)
 log=subprocess.check_output([str(a.output/'callback.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log)
 actual=[];expected=[]
 for line,r in zip(log.splitlines(),rows):
  _,index,state,parameters,events=line.split('|');assert int(index)==len(actual)
  actual.append(dict(state=list(map(int,state.split(','))),parameters=list(map(int,parameters.split(','))),events=list(map(int,events.split(',')))if events else []))
  force=0 if r['guardbreak']or(r['callback']==1 and r['cheat'])else r['force'];health=r['health']-force
  death_script=health<=0
  if death_script and r['invincible']==2:health=1
  if death_script and r['invincible']==3:health=300
  dead=int(health<=0);arrow=r['callback']==2
  trace=([2]if a.weaploss==0 else [])+([]if r['guardbreak']else[3])
  if r['opponent']==2:trace.extend([7,8])
  elif r['opponent']in(1,3):trace.append(7)
  if not a.empty_damage_scripts:
   trace.append(5)
   if death_script:trace.append(6)
  if dead and (r['opponent']==2 or(r['opponent']==1 and r['callback']==1)):trace.append(7)
  if r['callback']==1:trace.append(8)
  if a.score_body:trace=[e for e in trace if e not in(7,8)]
  attack_force=0 if r['callback']==1 and r['cheat']else r['force']
  score=attack_force*(a.model_multiple if r['opponent']==2 else 1 if r['opponent']in(1,3)else 0)
  if dead and(r['opponent']==2 or(r['opponent']==1 and r['callback']==1)):score+=a.model_score
  rumble=attack_force*(3 if r['callback']==1 else 2 if r['opponent']==2 else 0)
  if a.score_body:rumble=0
  expected.append(dict(state=[int(not arrow or dead),health,dead,dead,1-dead,0,3,248,16,int(not arrow),int(arrow),int(arrow),int(arrow)],parameters=[0 if a.empty_damage_scripts else force,0 if a.empty_damage_scripts else 16,score,rumble],events=trace))
 ok=actual==expected and len(actual)==len(rows)
 report=dict(schema='BYOR_4086_LANDING_CALLBACK_AUTHORITY_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,
  engine_commit=ENGINE_COMMIT,source_functions_unmodified=True,source_function_hashes={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},
  source_attack_type_land=16,source_positive_self_landing_early_return=True,
  source_checkgrab_self_no_op_proven=True,source_checkdamageflip_self_no_op_proven=True,
  actual_empty_damage_script_dispatchers_proven=a.empty_damage_scripts,
  source_weaploss=a.weaploss,
  source_model_multiple=a.model_multiple,source_model_score=a.model_score,
  actual_addscore_and_SDL_rumble_bodies_proven=a.score_body,
  source_score_domain='initial score0, lifescore50000, no score scripts, increments below threshold'if a.score_body else None,
  damage_script_execution_service_instrumented=not a.empty_damage_scripts,
  effect_weapon_script_score_rumble_services_instrumented=True,native_handler_backend_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(report['status'],len(actual),'full pinned landing callbacks',[(i,x,y)for i,(x,y)in enumerate(zip(actual,expected))if x!=y][:2]);assert ok


if __name__=='__main__':main()
