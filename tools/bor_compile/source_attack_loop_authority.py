"""Pinned ordered do_attack loop header and predicate, before hit services."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    def read(n):return subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/'+n],cwd=a.engine).decode('latin1')
    body=extract(read('openbor.c'),'do_attack');header=read('openbor.h')
    start=body.index('for(i = 0;');end=body.index('{',start);loop=body[start:end].strip()
    start=body.index('if( ent_list[i]->exists');end=body.index('{',start);predicate=body[start+2:end].strip()
    if loop!='for(i = 0; i < ent_max && !followed; i++)':raise ValueError('ATTACK_LOOP_ORDER_AUTHORITY')
    def enum(n):
        end=header.index('} '+n+';')+len('} '+n+';');start=header.rfind('typedef enum',0,end);return header[start:end]
    code='''#include <stdio.h>
#include <string.h>
'''+enum('e_attack_types')+'\n'+enum('e_otg')+r'''
typedef struct {int current;} metric;
typedef struct {int type;metric jugglepoints;} model;
typedef struct {int attackone;} anim;
typedef struct {int attack_type,otg,jugglecost,counterattack;} attack_t;
typedef struct entity {int exists,dead,invincible,falling;unsigned pain_time;int hit_by_attack_id;void *takedamage,*takeaction;model modeldata;struct entity *lasthit;anim *animation;} entity;
entity actor,targets[128],*e=&actor,*ent_list[128];anim animation,followanimation,*current_anim=&animation;attack_t attack_data,*attack=&attack_data;
int them,current_attack_id,ent_max,lie_token;unsigned time;void *common_lie=&lie_token;
int normal_result,counter_result,visits[128],nvisits,firsthit,collision_calls;
int checkhit(entity *a,entity *b,int mode){collision_calls++;return a==b?0:mode?counter_result:normal_result;}
void run(void){int i;
#define followed (current_anim!=e->animation)
'''+loop+'\n{visits[nvisits++]=i;\nif '+predicate+r'''
 {firsthit=i;e->animation=&followanimation;}}
#undef followed
}
int main(void){int count,slot,mode,i;for(count=1;count<=128;count++)for(slot=0;slot<2;slot++)for(mode=0;mode<3;mode++){
 int selfslot=slot?count-1:0;
 memset(&actor,0,sizeof(actor));memset(targets,0,sizeof(targets));memset(&attack_data,0,sizeof(attack_data));
 actor.exists=1;actor.modeldata.type=1;actor.animation=&animation;animation.attackone=-1;ent_max=count;them=2;time=48;current_attack_id=2;
 normal_result=mode==2;counter_result=0;firsthit=-1;nvisits=collision_calls=0;
 for(i=0;i<count;i++){ent_list[i]=i==selfslot?&actor:targets+i;targets[i].exists=mode!=0;targets[i].modeldata.type=2;targets[i].takedamage=&actor;}
 run();printf("%d %d %d %d %d %d",count,selfslot,mode,firsthit,nvisits,collision_calls);for(i=0;i<nvisits;i++)printf(" %d",visits[i]);printf("\n");}return 0;}
'''
    (a.output/'attack_loop.c').write_text(code,encoding='latin1')
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','attack_loop.c','-fe=attack_loop.exe'],cwd=a.output,env=env,capture_output=True,text=True)
    (a.output/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode:raise ValueError('ATTACK_LOOP_C_BUILD:'+b.stdout+b.stderr)
    log=subprocess.check_output([str(a.output/'attack_loop.exe')],text=True);actual=[list(map(int,l.split())) for l in log.splitlines()];expected=[]
    for count in range(1,129):
        for slot in (0,count-1):
            for mode in range(3):
                first=next((i for i in range(count) if i!=slot),-1) if mode==2 else -1
                n=first+1 if first>=0 else count
                calls=sum(i!=slot for i in range(n)) if mode else 0
                expected.append([count,slot,mode,first,n,calls,*range(n)])
    mismatches=[dict(index=i,actual=x,expected=y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y]
    report=dict(schema='BYOR_4086_ORDERED_ATTACK_LOOP_AUTHORITY_V1',status='PASS' if actual==expected else 'FAIL',engine_commit=ENGINE_COMMIT,cases=len(expected),
        loop_header_unmodified=True,outer_predicate_unmodified=True,loop_header_sha256=hashlib.sha256(loop.encode('latin1')).hexdigest(),predicate_sha256=hashlib.sha256(predicate.encode('latin1')).hexdigest(),
        results=actual,mismatches=mismatches,collision_results_instrumented=True,hit_body_instrumented=True,followed_stop_simulated_by_animation_pointer_change=True,
        ondoattack_and_damage_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(expected),'ordered source scan prefixes;',len(mismatches),'mismatches')
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
