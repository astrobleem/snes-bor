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
#define WEAPLOSS_TYPE_ANY 0
#define WEAPLOSS_TYPE_KNOCKDOWN 1
#define WEAPLOSS_TYPE_DEATH 2
#define PIT_DEPTH -1000
#define GAME_SPEED 200
#define GRAB_STALL 160
typedef struct entity entity;
typedef struct {float x,z,y;} Vec;
typedef struct {int attack_force,attack_type,attack_drop,no_pain,no_kill,no_block,guardcost,jugglecost,pause_add,grab,damage_on_landing;Vec dropv;} s_attack;
typedef struct {int type,health,mp,mprate,nopain,animal,escapehits,falldie,diesound,score,multiple,weaploss[3];float knockdowncount;struct{int max,current;}guardpoints;int subject_to_wall,subject_to_platform,subject_to_hole,subject_to_gravity,no_adjust_base;} Model;
struct entity {Model modeldata;Vec position,velocity;float offense_factors[20];struct{float factor,knockdown,pain;}defense[20];int exists,dead,toexplode,drop,frozen,damagetype,health,mp,damage_on_landing,direction,invincible,playerindex,nograb,idling,boss,itemplayer_count,multiple,escapecount;float knockdowncount,lifespancountdown;unsigned knockdowntime,stalltime,releasetime;entity *opponent,*grabbing,*item;void(*takeaction)(void);};
entity victim,opponent,*self;struct{int nohurt,bosses;}lev,*level=&lev;
int healthcheat,max_attack_types=20,magic_type=0,level_completed;
unsigned time=48;struct{int effectvol;}savedata;
int events[256],ne,script_force,script_type,score_total,rumble_last;void event(int n){events[ne++]=n;}
void unexpected(void){fprintf(stderr,"UNEXPECTED_NONLANDING_CALLBACK_BRANCH\n");exit(9);}
int common_takedamage(entity*,s_attack*);
int checkgrab(entity *e,s_attack *a){if(e!=self||a->grab)unexpected();event(1);return 1;}
void set_opponent(entity *e,entity *o){unexpected();}
void dropweapon(int n){event(2);}
void checkdamageeffects(s_attack *a){event(3);}
void checkdamageflip(entity *o,s_attack *a){if(o!=self)unexpected();event(4);}
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
 p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
 names=('checkdamagedrop','checkmpadd','checkhitscore','checkdamage','checkdeath','common_takedamage','player_takedamage','arrow_takedamage')
 bodies={n:extract(raw,n)for n in names};code=PREAMBLE+'\n'.join(bodies.values())
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
  trace=[1,2]+([]if r['guardbreak']else[3])+[4]
  if r['opponent']==2:trace.extend([7,8])
  elif r['opponent']in(1,3):trace.append(7)
  trace.append(5)
  if death_script:trace.append(6)
  if dead and (r['opponent']==2 or(r['opponent']==1 and r['callback']==1)):trace.append(7)
  if r['callback']==1:trace.append(8)
  attack_force=0 if r['callback']==1 and r['cheat']else r['force']
  score=attack_force*(2 if r['opponent']==2 else 1 if r['opponent']in(1,3)else 0)
  rumble=attack_force*(3 if r['callback']==1 else 2 if r['opponent']==2 else 0)
  expected.append(dict(state=[int(not arrow or dead),health,dead,dead,1-dead,0,3,248,16,int(not arrow),int(arrow),int(arrow),int(arrow)],parameters=[force,16,score,rumble],events=trace))
 ok=actual==expected and len(actual)==len(rows)
 report=dict(schema='BYOR_4086_LANDING_CALLBACK_AUTHORITY_V1',status='PASS'if ok else'FAIL',cases=len(rows),inputs=rows,actual=actual,expected=expected,
  engine_commit=ENGINE_COMMIT,source_functions_unmodified=True,source_function_hashes={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},
  source_attack_type_land=16,source_positive_self_landing_early_return=True,
  effect_weapon_script_score_rumble_services_instrumented=True,native_handler_backend_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(report['status'],len(actual),'full pinned landing callbacks',[(i,x,y)for i,(x,y)in enumerate(zip(actual,expected))if x!=y][:2]);assert ok


if __name__=='__main__':main()
