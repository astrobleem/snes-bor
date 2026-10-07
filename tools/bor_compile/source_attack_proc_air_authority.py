"""Pinned attack proc and diff: airborne returns before any resource service."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 source=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd='E:/gh/openbor-bcec').decode('latin1');f=extract(source,'common_attack_proc');d=extract(source,'diff')
 # Source-float-exact small coordinates include fractional threshold neighbours.
 inputs=[dict(y=b+delta,base=b)for b,delta in itertools.product((-8*65536,0,8*65536),(-8*65536,-4*65536-1,-4*65536,4*65536,4*65536+1,8*65536))]
 # Integer wide/extreme cases preserve classification under both representations.
 inputs.extend(dict(y=y,base=b)for y,b in itertools.product((-2147483648,-65536,0,65536,2147418112,2147483647),repeat=2)if abs(y-b)>=4*65536)
 code=r'''#include <stdio.h>
#include <string.h>
#define COST_CHECK_MP 1
typedef struct animation {struct {int cost;}energycost;}animation;
typedef struct entity {int animating,tocost,mp,health,animnum,reactive,attacking;struct{float y;}position;float base;struct{int smartbomb;}modeldata;animation*animation;}entity;
entity ent,*self=&ent,*smartbomber=NULL;animation anim;int calls;
int check_energy(int a,int n){calls++;return 0;}
void smart_bomb(entity*e,int n){calls++;}
void subtract_shot(void){calls++;}
void common_attack_finish(void){calls++;}
'''+d+'\n'+f+'\nint cases[][2]={'+','.join('{'+str(c['y'])+','+str(c['base'])+'}'for c in inputs)+r'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){entity before;memset(self,0,sizeof(*self));self->position.y=(float)cases[i][0]/65536.0f;self->base=(float)cases[i][1]/65536.0f;self->tocost=99;self->reactive=1;self->attacking=66;self->mp=77;self->health=88;self->animation=&anim;smartbomber=self;before=*self;calls=0;common_attack_proc();printf("%d,%d,%d\n",calls,memcmp(&before,self,sizeof(before))!=0,smartbomber==self);}return 0;}
'''
 (a.output/'air.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-ei','-bt=nt','air.c','-fe=air.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(b.stdout+b.stderr);assert b.returncode==0
 log=subprocess.check_output([str(a.output/'air.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,l.split(',')))for l in log.splitlines()];expected=[[0,0,1]for c in inputs];ok=actual==expected
 r=dict(schema='BYOR_4086_ATTACK_PROC_AIR_AUTHORITY_V1',status='PASS'if ok else'FAIL',cases=len(inputs),engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(f.encode()).hexdigest(),diff_sha256=hashlib.sha256(d.encode()).hexdigest(),source_function_unmodified=True,source_diff_unmodified=True,resource_callees_instrumented=True,inputs=inputs,actual=actual,expected=expected,numeric_policy='ACCEPTED_COMPAT_Q16_16; sampled classifications match literal engine floats; not universal float storage equivalence',finished_attack_bound=False,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(inputs),'literal airborne cases');assert ok

if __name__=='__main__':main()
