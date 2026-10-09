"""Compare the generic attack gate with unmodified pinned check_attack C."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_check_attack_4086 import decide


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'))
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1')
    body=extract(raw,'check_attack')
    values=(-2147483648,-65536,-1,0,1,65536,2147483647)
    rows=list(itertools.product(values,values,values,(-2147483648,0,65536),(False,True),(False,True),(0,1,0xffffffff)))
    code=r"""#include <stdio.h>
#include <stdlib.h>
typedef struct {void **attacks;} animation;
typedef struct {int falling,projectile,drop,animpos;unsigned attack_id;animation *animation;} entity;
entity actor,*self=&actor;animation anim;void *attack;
int freeze_value,queried,called;
int is_frozen(entity *e){queried++;return freeze_value;}
void do_attack(entity *e){called++;}
"""+body+r"""
int main(void){int f,p,d,z,table,row;unsigned id;if(sizeof(int)!=4)return 2;
while(scanf("%d %d %d %d %d %d %u",&f,&p,&d,&z,&table,&row,&id)==7){
 actor.falling=f;actor.projectile=p;actor.drop=d;actor.animpos=0;actor.attack_id=id;actor.animation=&anim;
 attack=row?&actor:NULL;anim.attacks=table?&attack:NULL;freeze_value=z;queried=called=0;
 check_attack();printf("%u %d %d\n",actor.attack_id,queried,called);
}return 0;}
"""
    (a.output/'check_attack.c').write_text(code,encoding='latin1')
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','check_attack.c','-fe=check_attack.exe'],cwd=a.output,env=env,capture_output=True,text=True)
    (a.output/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('CHECK_ATTACK_C_BUILD:'+build.stdout+build.stderr)
    input_text=''.join(' '.join(str(int(v))for v in row)+'\n'for row in rows)
    proc=subprocess.run([str((a.output/'check_attack.exe').resolve())],input=input_text,capture_output=True,text=True)
    if proc.returncode:raise ValueError('CHECK_ATTACK_C_EXECUTION')
    actual=[list(map(int,line.split()))for line in proc.stdout.splitlines()]
    expected=[]
    for row in rows:
        r=decide(*row);expected.append([r['attack_id'],int('is_frozen'in r['events']),int(r['service']=='DO_ATTACK')])
    mismatches=[dict(index=i,input=list(row),actual=actual[i]if i<len(actual)else None,expected=expected[i])for i,row in enumerate(rows)if i>=len(actual)or actual[i]!=expected[i]]
    report=dict(schema='BYOR_4086_CHECK_ATTACK_GATE_AUTHORITY_V1',status='PASS'if len(actual)==len(rows)and not mismatches else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),cases=len(rows),input_axes=dict(falling=list(values),projectile=list(values),drop=list(values),frozen=[-2147483648,0,65536],attack_table=[False,True],frame_attack=[False,True],attack_id=[0,1,0xffffffff]),matrix_sha256=hashlib.sha256(input_text.encode()).hexdigest(),actual_sha256=hashlib.sha256(proc.stdout.encode()).hexdigest(),mismatches=mismatches,do_attack_instrumented=True,freeze_query_instrumented=True,native_attack_gate_bound=False,native_combat_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(rows),'pinned check_attack cases')
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
