"""Unchanged pinned post-collision prefix and empty ondoattack dispatchers."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_hit_prelude_4086 import prelude


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine', type=Path, default=Path('E:/gh/openbor-bcec'))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); a.output = a.output.resolve(); a.output.mkdir(parents=True, exist_ok=True)
    def read(n):
        return subprocess.check_output(['git', 'show', ENGINE_COMMIT + ':engine/' + n], cwd=a.engine).decode('latin1')
    raw = read('openbor.c'); body = extract(raw, 'do_attack')
    start = body.index('            temp = self;')
    end = body.index('                //if #05,', start)
    prefix = body[start:end]
    dispatch = extract(raw, 'execute_ondoattack_script')
    initialized = extract(read('openborscript.c'), 'Script_IsInitialized')
    rows = list(itertools.product(range(6), (0, 1, -1), (0, 1), (0, 1, 0xffffffff), (None, 0, 3)))
    code = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define VOID void
#define LONG int
#define VT_PTR 2
#define VT_INTEGER 1
typedef struct {int initialized;} Script;
typedef struct {void *ptrVal;int lVal;} ScriptVariant;
typedef struct {Script *ondoattack_script;} Scripts;
typedef struct entity {struct entity *owner;struct {int ground;} modeldata;Scripts *scripts;} entity;
typedef struct {int attack_drop,attack_type,no_block,guardcost,jugglecost,pause_add;} s_attack;
entity pool[4],*e,*self,*temp,*topowner,*otherowner,*ent_list[1];int i=0;
Script empty;Scripts scripts={&empty};s_attack data,*attack=&data;
struct {int confirm;} lasthit;int force,current_attack_id,didhit,air,air_calls;
void unexpected(void){exit(9);}
void ScriptVariant_Init(ScriptVariant *v){unexpected();}
void ScriptVariant_ChangeType(ScriptVariant *v,int t){unexpected();}
void Script_Set_Local_Variant(Script *s,char *n,ScriptVariant *v){unexpected();}
void Script_Execute(Script *s){unexpected();}
void ScriptVariant_Clear(ScriptVariant *v){unexpected();}
int inair(entity *e){air_calls++;return air;}
''' + initialized + '\n' + dispatch + '\nint run(void){\n' + prefix + r'''
 if(didhit)return 1;self=temp;}
 return 0;}
int main(void){int mode,ground,yes,c,old,i,result;unsigned confirm;
while(scanf("%d %d %d %u %d",&mode,&ground,&yes,&confirm,&old)==5){
 memset(pool,0,sizeof(pool));for(i=0;i<4;i++)pool[i].scripts=&scripts;
 if(mode==1)pool[1].owner=pool;
 if(mode==2){pool[0].owner=pool+2;pool[1].owner=pool+2;}
 if(mode==3){pool[0].owner=pool+2;pool[1].owner=pool+3;}
 if(mode==4)pool[1].owner=pool+2;
 if(mode==5){pool[0].owner=pool+2;pool[2].owner=pool+3;pool[1].owner=pool+3;}
 e=pool;ent_list[0]=pool+1;self=old<0?NULL:pool+old;topowner=e;while(topowner->owner)topowner=topowner->owner;
 e->modeldata.ground=ground;memcpy(&lasthit.confirm,&confirm,4);air=yes;air_calls=0;didhit=7;result=run();
 printf("%d %d %d %d\n",result,didhit,self?(int)(self-pool):-1,air_calls);
 }return 0;}
'''
    (a.output/'prelude.c').write_text(code, encoding='latin1')
    env = dict(os.environ, WATCOM='C:/WATCOM', INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    b = subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','prelude.c','-fe=prelude.exe'],cwd=a.output,env=env,capture_output=True,text=True)
    (a.output/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode: raise ValueError('HIT_PRELUDE_C_BUILD:'+b.stdout+b.stderr)
    inputs=''.join(f'{mode} {ground} {air} {confirm} {old if old is not None else -1}\n' for mode,ground,air,confirm,old in rows)
    q=subprocess.run([str(a.output/'prelude.exe')],input=inputs,capture_output=True,text=True)
    actual=[list(map(int,l.split())) for l in q.stdout.splitlines()]; expected=[]
    for mode,ground,air,confirm,old in rows:
        pool=[dict(owner=None,ground=0) for _ in range(4)]; pool[0]['ground']=ground
        for i,o in ({}, {1:0}, {0:2,1:2}, {0:2,1:3}, {1:2}, {0:2,2:3,1:3})[mode].items(): pool[i]['owner']=o
        calls=[];events=[]
        r=prelude(pool,0,1,old,dict(confirm=confirm),{},2,lambda *args:events.append(args[:2]+args[3:6]),lambda i:calls.append(i) or air)
        if [v[:3] for v in events] != [(1,0,0),(0,1,1)]: raise ValueError('HIT_PRELUDE_EVENT_ORDER')
        expected.append([int(r['required']),r['didhit'] if r['didhit'] is not None else 7,r['source_self'] if r['source_self'] is not None else -1,len(calls)])
    failures=[dict(index=i,actual=x,expected=y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y]
    report=dict(schema='BYOR_HIT_PRELUDE_AUTHORITY_V1',status='PASS' if q.returncode==0 and actual==expected else 'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),
        prefix_sha256=hashlib.sha256(prefix.encode('latin1')).hexdigest(),empty_dispatch_sha256=hashlib.sha256(dispatch.encode('latin1')).hexdigest(),
        script_initialized_sha256=hashlib.sha256(initialized.encode('latin1')).hexdigest(),results=actual,failures=failures,
        prefix_and_script_bodies_unmodified=True,inair_service_instrumented=True,confirm_zero_retains_target_self=True,
        item_blocking_damage_body_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(rows),'pinned post-collision prefix cases')
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
