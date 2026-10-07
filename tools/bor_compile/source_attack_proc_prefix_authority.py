"""Literal common_attack_proc animating short circuit, with callees observed."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 f=extract(subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1'),'common_attack_proc')
 code=r'''#include <stdio.h>
#include <string.h>
#define COST_CHECK_MP 1
typedef struct animation {struct {int cost;}energycost;}animation;
typedef struct entity {int animating,tocost,mp,health,animnum,reactive,attacking;struct{float y;}position;float base;struct{int smartbomb;}modeldata;animation*animation;}entity;
entity ent,*self=&ent,*smartbomber=NULL;animation anim;int calls;
float diff(float a,float b){calls++;return a>b?a-b:b-a;}
int check_energy(int a,int n){calls++;return 0;}
void smart_bomb(entity*e,int n){calls++;}
void subtract_shot(void){calls++;}
void common_attack_finish(void){calls++;}
'''+f+r'''
int main(void){int values[]={-32768,-1,1,32767};unsigned i;for(i=0;i<4;i++){entity before;memset(self,0,sizeof(*self));self->animating=values[i];self->tocost=99;self->reactive=1;self->attacking=66;self->mp=77;self->health=88;self->animation=&anim;before=*self;calls=0;common_attack_proc();printf("%d,%d,%d\n",values[i],calls,memcmp(&before,self,sizeof(before))!=0);}return 0;}
'''
 (a.output/'attack.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','attack.c','-fe=attack.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'attack.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[[v,0,0]for v in (-32768,-1,1,32767)];ok=actual==expected;r=dict(schema='BYOR_4086_ATTACK_PROC_PREFIX_AUTHORITY_V1',status='PASS'if ok else'FAIL',cases=4,engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(f.encode()).hexdigest(),source_function_unmodified=True,callees_instrumented=True,actual=actual,expected=expected,domain='nonzero animating within signed16 native auxiliary domain',finished_attack_bound=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],'literal common_attack_proc animating short circuit');assert ok

if __name__=='__main__':main()
