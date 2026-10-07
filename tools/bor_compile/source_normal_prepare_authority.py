"""Literal normal_prepare prefix/absence proof with body callees observed."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');f=extract(raw,'normal_prepare')
 rows=[dict(found=found,noflip=noflip,direction=d,target_x=x,turn=turn,time=time,stalltime=stall)for found,noflip,d,x,turn,time,stall in itertools.product((0,1),(0,1,65536,-1),(0,1),(-1,0,1),(0,1),(0,50,0xffffffff),(0,50,51,0xffffffff))]
 code='''#include <stdio.h>
#include <stddef.h>
#define ANI_TURN 13
#define ANI_THROWATTACK 63
#define SUBTYPE_PROJECTILE 9
#define COST_CHECK_MP 0
#define COST_CHECK_HP 1
typedef struct entity {int idling,direction;void(*takeaction)(void);struct {float x,z;}velocity;struct {float x;}position;struct {int noflip,subtype,chainlength;}modeldata;unsigned stalltime;struct entity*weapent;} entity;
entity ent,victim,*self=&ent;unsigned time;int found,turn,trace,turn_seen,turn_animation;
int max_freespecials=8,max_attacks=4,animspecials[8]={22,26,28,44,45,46,47,48},animattacks[4]={8,9,10,11},atkchoices[64];
void mark(int n){trace=trace*10+n;}
void common_turn(void){}
void common_attack_proc(void){}
void normal_prepare(void);
entity*normal_find_target(int a,int b){mark(1);return found?&victim:NULL;}
int validanim(entity*e,int n){if(n==ANI_TURN){mark(2);return turn;}return 0;}
int check_energy(int a,int n){mark(7);return 0;}
int check_range(entity*a,entity*b,int n){mark(7);return 0;}
int check_costmove(int n,int a,int b){mark(7);return 0;}
int perform_atchain(void){mark(7);return 0;}
unsigned int rand32(void){mark(5);return 7;}
void set_turning(entity*e){mark(3);turn_seen=(e->takeaction==common_turn&&e->velocity.x==0&&e->velocity.z==0);}
void set_attacking(entity*e){mark(7);}
void ent_set_anim(entity*e,int n,int r){mark(4);turn_animation=n;}
'''+f+'\nunsigned cases[][7]={'+','.join('{'+','.join(str(c[k])+'u'for k in ('found','noflip','direction','target_x','turn','time','stalltime'))+'}'for c in rows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){found=cases[i][0];self->modeldata.noflip=cases[i][1];self->direction=cases[i][2];victim.position.x=(int)cases[i][3];turn=cases[i][4];time=cases[i][5];self->stalltime=cases[i][6];self->position.x=0;self->velocity.x=3;self->velocity.z=4;self->idling=55;self->takeaction=normal_prepare;self->weapent=NULL;self->modeldata.chainlength=1;trace=turn_seen=0;turn_animation=-1;normal_prepare();printf("%d,%d,%d,%d,%d,%d,%d,%d\\n",trace,self->idling,self->direction,self->takeaction==NULL?0:self->takeaction==common_turn?1:2,self->velocity.x==0&&self->velocity.z==0,turn_seen,turn_animation,self->takeaction==common_attack_proc);}return 0;}
'''
 (a.output/'prepare.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','prepare.c','-fe=prepare.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'prepare.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[]
 for c in rows:
  d=c['direction']if c['noflip']else int(0<c['target_x']);changed=d!=c['direction'];trace=12 if changed else 1
  if not c['found']:expected.append([1,1,c['direction'],0,1,0,-1,0])
  elif changed and c['turn']:expected.append([1234,55,c['direction'],1,1,1,13,0])
  elif c['time']<c['stalltime']:expected.append([trace,55,d,2,1,0,-1,0])
  else:expected.append([trace*10+5,1,d,0,1,0,-1,0])
 ok=actual==expected;report=dict(schema='BYOR_4086_NORMAL_PREPARE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(f.encode()).hexdigest(),source_function_unmodified=True,callees_instrumented=True,domain='no held projectile, no normal/special animations, chainlength 1; TURN availability varied',cases=len(rows),inputs=rows,actual=actual,expected=expected,native_bound=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'literal normal_prepare cases');assert ok

if __name__=='__main__':main()
