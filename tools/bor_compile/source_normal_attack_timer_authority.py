"""Literal normal attack with real source timer helper and bounded body stubs."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pairs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 pairs=json.loads(a.pairs.read_text());assert pairs['status']=='PASS'
 s=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');normal=extract(s,'common_try_normalattack');recheck=extract(s,'recheck_nextattack');rows=[]
 for i,(c,e)in enumerate(zip(pairs['inputs'],pairs['actual'])):
  for time in (0,50,0xffffffff,e[1]):
   found=int(i%3!=0);vulnerable=int(i%2==0);after=e[1]if found else c['timer'];delay=int(bool(found and after>time));rows.append(dict(c,time=time,found=found,vulnerable=vulnerable,after=after,delay=delay,requires_body=int(bool(found and not delay and(vulnerable or not c['attacking'])))))
 code='''#include <stdio.h>
#include <stddef.h>
#define MAX(a,b) ((a)>(b)?(a):(b))
#define GAME_SPEED 200
typedef unsigned int u32;
typedef struct animation {int vulnerable[1];} animation;
typedef struct entity {int combostep[1],idling,attacking,blocking,jumping,drop,animpos;u32 combotime,stalltime,nextattack;void(*takeaction)(void);struct {float x,z;}velocity;struct {float attackthrottletime;int aggression;}modeldata;animation*animation;} entity;
entity ent,victim,*self=&ent;animation anim;u32 time;float min_noatk_chance=.05f;int found,findcalls,rechecks,picks,mutations,randomcalls;
entity*normal_find_target(int a,int b){findcalls++;return found?&victim:NULL;}
int pick_random_attack(entity*e,int n){picks++;return -1;}
int check_attack_chance(entity*e,float a,float b){mutations++;return 0;}
float randf(float f){randomcalls++;return 0;}
void common_rise(void){}
void normal_prepare(void){}
void set_idle(entity*e){mutations++;}
'''+recheck.replace('recheck_nextattack(', 'recheck_nextattack_body(',1)+'''
u32 recheck_nextattack(entity*e){rechecks++;return recheck_nextattack_body(e);}
'''+normal+'\nunsigned cases[][7]={'+','.join('{'+','.join(str(c[k]&0xffffffff)+'u'for k in ('blocking','attacking','jumping','timer','time','found','vulnerable'))+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){int r;victim.blocking=cases[i][0];victim.attacking=cases[i][1];victim.jumping=cases[i][2];ent.nextattack=cases[i][3];time=cases[i][4];found=cases[i][5];victim.animation=&anim;anim.vulnerable[0]=cases[i][6];findcalls=rechecks=picks=mutations=randomcalls=0;r=common_try_normalattack(NULL);printf("%d,%u,%d,%d,%d,%d,%d\\n",r,ent.nextattack,findcalls,rechecks,picks,mutations,randomcalls);}return 0;}
'''
 (a.output/'normal_timer.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','normal_timer.c','-fe=normal_timer.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'normal_timer.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[[0,c['after'],1,2*c['found'],c['requires_body'],0,0]for c in rows];ok=actual==expected
 (a.output/'report.json').write_text(json.dumps(dict(schema='BYOR_4086_NORMAL_ATTACK_TIMER_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,source_sha256=dict(normal=hashlib.sha256(normal.encode()).hexdigest(),recheck=hashlib.sha256(recheck.encode()).hexdigest()),cases=len(rows),inputs=rows,actual=actual,expected=expected,target_lookup_and_later_body_instrumented=True,timer_body_instrumented=False,motu_gameplay_proven=False),indent=2)+'\n');print('PASS'if ok else'FAIL',len(rows),'literal normal attack timer cases');assert ok
if __name__=='__main__':main()
