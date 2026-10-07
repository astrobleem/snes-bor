"""Literal normal attack body: instrument callees and observe mutation order."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');f=extract(raw,'common_try_normalattack')
 rows=[dict(step=s,combo=t,time=now,pick=pick,chance=chance)for s,t,now,pick,chance in itertools.product((0,1,65536,-1),(0,49,50,51,0xffffffff),(0,50,0xffffffff),(-1,0,167),(0,1))]
 code='''#include <stdio.h>
#include <stddef.h>
#define MAX(a,b) ((a)>(b)?(a):(b))
#define GAME_SPEED 200
typedef struct animation {int vulnerable[1];} animation;
typedef struct entity {int combostep[1],idling,attacking,drop,animpos;unsigned combotime,stalltime,nextattack;void(*takeaction)(void);struct {float x,z;}velocity;struct {float attackthrottletime;int aggression;}modeldata;animation*animation;} entity;
entity ent,victim,*self=&ent;animation anim;unsigned time;float min_noatk_chance=0;int pick,chance,trace,idle_observation;
void mark(int n){trace=trace*10+n;}
void common_rise(void){}
void normal_prepare(void){}
entity*normal_find_target(int a,int b){mark(1);return &victim;}
unsigned recheck_nextattack(entity*e){mark(2);return 0;}
int pick_random_attack(entity*e,int n){mark(3);return pick;}
int check_attack_chance(entity*e,float a,float b){mark(4);return chance;}
float randf(float f){mark(5);return 7;}
void set_idle(entity*e){mark(6);idle_observation=(e->takeaction==normal_prepare&&e->velocity.x==0&&e->velocity.z==0&&e->idling==55&&e->attacking==66);e->idling=2;e->attacking=0;}
'''+f+'\nint cases[][5]={'+','.join('{'+str(c['step'])+','+str(c['combo'])+'u,'+str(c['time'])+'u,'+str(c['pick'])+','+str(c['chance'])+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){int r;self->combostep[0]=cases[i][0];self->combotime=cases[i][1];time=cases[i][2];pick=cases[i][3];chance=cases[i][4];self->stalltime=111;self->nextattack=222;self->idling=55;self->attacking=66;self->velocity.x=3;self->velocity.z=4;self->takeaction=NULL;self->modeldata.attackthrottletime=150;self->modeldata.aggression=0;anim.vulnerable[0]=1;victim.animation=&anim;victim.animpos=0;trace=idle_observation=0;r=common_try_normalattack(&victim);printf("%d,%d,%u,%u,%d,%d,%d,%d,%d\\n",r,trace,self->stalltime,self->nextattack,self->idling,self->attacking,self->takeaction==normal_prepare,self->velocity.x==0&&self->velocity.z==0,idle_observation);}return 0;}
'''
 (a.output/'normal_body.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','normal_body.c','-fe=normal_body.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'normal_body.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[]
 for c in rows:
  combo=bool(c['step']and c['combo']>c['time'])
  if c['pick']<0:expected.append([0,1223,111,222,55,66,0,0,0])
  elif combo:expected.append([1,12236,(c['time']+1)&0xffffffff,222,0,-1,1,1,1])
  elif not c['chance']:expected.append([0,122345,111,(c['time']+7)&0xffffffff,55,66,0,0,0])
  else:expected.append([1,1223456,(c['time']+7)&0xffffffff,222,0,-1,1,1,1])
 ok=actual==expected
 report=dict(schema='BYOR_4086_NORMAL_ATTACK_BODY_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(f.encode()).hexdigest(),cases=len(rows),inputs=rows,actual=actual,expected=expected,callees_instrumented=True,source_function_unmodified=True,trace_symbols=dict(query=1,recheck=2,pick=3,chance=4,randf=5,idle=6),native_body_bound=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'literal normal attack body cases');assert ok

if __name__=='__main__':main()
