"""Literal normal_prepare normal-choice order; external services instrumented."""
import argparse,hashlib,itertools,json,os,re,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_actor_numeric import random32_step

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 def authority(path):return subprocess.check_output(['git','show',ENGINE_COMMIT+':'+path],cwd='E:/gh/openbor-bcec').decode('latin1')
 f=extract(authority('engine/openbor.c'),'normal_prepare');header=authority('engine/openbor.h');macro=re.search(r'^#define set_attacking\(e\)[^\n]*\\\n[^\n]*',header,re.M)[0]
 rows=[]
 for present,ranges,seed in itertools.product(range(16),range(16),(0,1,9,19,65535,65536,0x80000000,0xffffffff)):
  after,first=random32_step(seed);final,second=random32_step(after);options=[i for i in range(4)if present&ranges&(1<<i)];total=sum(6-i for i in options);chosen=-1
  if total:
   index=(second&65535)%total
   for i in options:
    if index<6-i:chosen=8+i;break
    index-=6-i
  rows.append(dict(present=present,ranges=ranges,seed=seed,draws=[first,second],seed_after=final if total else after,calls=2 if total else 1,chosen=chosen,total=total))
 code=r'''#include <stdio.h>
#include <stddef.h>
#define ANI_TURN 13
#define ANI_THROWATTACK 63
#define SUBTYPE_PROJECTILE 9
#define COST_CHECK_MP 1
#define COST_CHECK_HP 0
typedef struct entity {int idling,direction,attacking;void(*takeaction)(void);struct {float x,z;}velocity;struct {float x;}position;struct {int noflip,subtype,chainlength;}modeldata;unsigned stalltime;struct entity*weapent;} entity;
entity ent,victim,*self=&ent;unsigned time=50,draws[2];int present,ranges,calls,chosen;
int max_freespecials=8,max_attacks=4,animspecials[8]={22,26,28,44,45,46,47,48},animattacks[4]={8,9,10,11},atkchoices[64];
void common_turn(void){}
void common_attack_proc(void){}
void normal_prepare(void);
entity*normal_find_target(int a,int b){return &victim;}
int validanim(entity*e,int n){return n>=8&&n<=11&&(present&(1<<(n-8)));}
int check_energy(int a,int n){return 0;}
int check_range(entity*a,entity*b,int n){return ranges&(1<<(n-8));}
int check_costmove(int n,int a,int b){return 0;}
int perform_atchain(void){return 0;}
unsigned int rand32(void){return draws[calls++];}
void set_turning(entity*e){}
void ent_set_anim(entity*e,int n,int r){chosen=n;}
'''+macro+'\n'+f+'\nunsigned cases[][4]={'+','.join('{'+','.join(str(v)+'u'for v in (c['present'],c['ranges'],*c['draws']))+'}'for c in rows)+r'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){present=cases[i][0];ranges=cases[i][1];draws[0]=cases[i][2];draws[1]=cases[i][3];self->idling=55;self->attacking=66;self->direction=0;self->modeldata.noflip=0;self->modeldata.chainlength=1;self->weapent=NULL;self->stalltime=0;self->takeaction=normal_prepare;self->position.x=0;victim.position.x=1;self->velocity.x=3;self->velocity.z=4;calls=0;chosen=-1;normal_prepare();printf("%d,%d,%d,%d,%d,%d,%d\n",chosen,calls,self->idling,self->attacking,self->takeaction==common_attack_proc?17:self->takeaction==NULL?0:16,self->direction,self->velocity.x==0&&self->velocity.z==0);}return 0;}
'''
 (a.output/'prepare.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','prepare.c','-fe=prepare.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(build.stdout+build.stderr);assert build.returncode==0
 log=subprocess.check_output([str(a.output/'prepare.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[[c['chosen'],c['calls'],0 if c['total']else 1,1 if c['total']else 66,17 if c['total']else 0,1,1]for c in rows];ok=actual==expected
 report=dict(schema='BYOR_4086_NORMAL_PREPARE_CHOICE_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(f.encode()).hexdigest(),set_attacking_macro_sha256=hashlib.sha256(macro.encode()).hexdigest(),source_function_unmodified=True,callees_instrumented=True,normal_weights=[6,5,4,3],cases=len(rows),inputs=rows,actual=actual,expected=expected,domain='TURN absent, NULL weapon, no special roles, chainlength 1; normal presence and range masks, supplied pinned-RNG draws',native_bound=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'literal normal_prepare normal choices');assert ok

if __name__=='__main__':main()
