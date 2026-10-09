"""Compile unchanged ordered do_attack blocking/counter predicates."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_hit_block_4086 import choose


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');b=extract(raw,'do_attack')
    starts=[b.index('                    if( !self->modeldata.nopassiveblock'),b.index('                    else if((self->modeldata.nopassiveblock'),b.index('                    else if((self->animpos')]
    predicates=[b[i:b.index('{',i)].strip() for i in starts]
    base=dict(nopassiveblock=0,valid=1,guardmax=0,guardcurrent=0,link=0,air=0,frozen=0,direction=0,attacker_direction=1,blockback=0,idling=1,attacking=0,
              no_block=0,blockpower=0,blockodds=1,random=1,thold=0,force=7,initial_blockthreshold=0,type=2,blocking=0,blockthreshold=0,counter_min=1,counter_max=0,animpos=0)
    rows=[]
    knobs=('nopassiveblock','valid','link','air','frozen','direction','idling','blocking','type','counter_min','guardmax','guardcurrent')
    for mask in range(4096):
        row=dict(base)
        for i,n in enumerate(knobs):row[n]=int(bool(mask&(1<<i)))
        row['counter_max']=1
        for random in (0,1,2,0xffffffff):rows.append(dict(row,random=random))
    for name in ('nopassiveblock','guardmax','guardcurrent','frozen','idling','attacking','blockback','no_block','blockpower','blockodds','thold','force','initial_blockthreshold','type','blocking','blockthreshold','counter_min','counter_max','animpos'):
        for value in (-2147483648,-16777217,-1,0,1,7,8,16777217,2147483647):
            for mode in range(3):
                row=dict(base)
                if mode==1:row.update(nopassiveblock=1,blocking=1,type=1)
                if mode==2:row.update(valid=0,counter_min=0,counter_max=1)
                row[name]=value;rows.append(row)
    fields=list(base)
    code=r'''
#include <stdio.h>
#include <string.h>
#define TYPE_PLAYER 1
#define ANI_BLOCK 1
typedef struct {int nopassiveblock,blockback,blockodds,thold,type;struct {int max,current;} guardpoints;} Model;
typedef struct {struct {struct {int min,max;}frame;} counterrange;} Anim;
typedef struct {Model modeldata;void *link;int frozen,direction,idling,attacking,blocking,animpos;struct {float blockpower,blockthreshold;} defense[1];Anim *animation;} entity;
typedef struct {int no_block,attack_type;} Attack;
entity defender,attacker,*self=&defender,*e=&attacker;Anim anim;Attack attack_data,*attack=&attack_data;
int force,fdefense_blockthreshold,valid,air,validcalls,aircalls,randcalls,trace;unsigned random_value;
int validanim(entity *e,int n){validcalls++;trace=trace*10+1;return valid;}
int inair(entity *e){aircalls++;trace=trace*10+2;return air;}
unsigned rand32(void){randcalls++;trace=trace*10+3;return random_value;}
int choose(void){
''' + predicates[0]+'\n{return 1;}\n'+predicates[1]+'\n{return 2;}\n'+predicates[2]+'\n{return 3;}\nreturn 0;}\n'
    code+='int main(void){int v[25],i,r;while(scanf("'+' '.join('%u'if n=='random'else'%d' for n in fields)+'",'+','.join('&v['+str(i)+']'for i in range(len(fields)))+')==25){\n'
    mappings=dict(nopassiveblock='self->modeldata.nopassiveblock',valid='valid',guardmax='self->modeldata.guardpoints.max',guardcurrent='self->modeldata.guardpoints.current',link='self->link',air='air',frozen='self->frozen',direction='self->direction',attacker_direction='e->direction',blockback='self->modeldata.blockback',idling='self->idling',attacking='self->attacking',no_block='attack->no_block',blockpower='self->defense[0].blockpower',blockodds='self->modeldata.blockodds',random='random_value',thold='self->modeldata.thold',force='force',initial_blockthreshold='fdefense_blockthreshold',type='self->modeldata.type',blocking='self->blocking',blockthreshold='self->defense[0].blockthreshold',counter_min='anim.counterrange.frame.min',counter_max='anim.counterrange.frame.max',animpos='self->animpos')
    code+='self->animation=&anim;\n'+'\n'.join(mappings[n]+'='+('(void *)' if n=='link' else '')+f'v[{i}];'for i,n in enumerate(fields))
    code+='\nvalidcalls=aircalls=randcalls=trace=0;r=choose();printf("%d %d %d %d %d\\n",r,validcalls,aircalls,randcalls,trace);}return 0;}\n'
    (a.output/'block.c').write_text(code,encoding='latin1');env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    q=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','block.c','-fe=block.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(q.stdout+q.stderr)
    if q.returncode:raise ValueError('HIT_BLOCK_C_BUILD:'+q.stdout+q.stderr)
    inputs=''.join(' '.join(str(row[n])for n in fields)+'\n'for row in rows)
    q=subprocess.run([str(a.output/'block.exe')],input=inputs,capture_output=True,text=True);actual=[list(map(int,l.split()))for l in q.stdout.splitlines()];expected=[]
    branches=['DAMAGE','PASSIVE_BLOCK','ACTIVE_BLOCK','COUNTER']
    from source_hit_block_4086 import f32
    for row in rows:
        counts=[0,0,0];trace=[]
        def service(i,value):counts[i]+=1;trace.append(str(i+1));return value
        d=dict(row,blockpower=f32(row['blockpower']),blockthreshold=f32(row['blockthreshold']))
        result=choose(d,dict(direction=row['attacker_direction']),dict(no_block=row['no_block']),row['force'],row['initial_blockthreshold'],lambda:service(0,row['valid']),lambda:service(1,row['air']),lambda:service(2,row['random']))
        expected.append([branches.index(result),*counts,int(''.join(trace)or'0')])
    failures=[dict(index=i,input=rows[i],actual=x,expected=y)for i,(x,y)in enumerate(zip(actual,expected))if x!=y]
    r=dict(schema='BYOR_HIT_BLOCK_AUTHORITY_V1',status='PASS'if q.returncode==0 and actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,cases=len(rows),
        predicate_sha256=[hashlib.sha256(v.encode('latin1')).hexdigest()for v in predicates],unchanged_source_predicates=True,
        actual_validanim_inair_random_bodies_instrumented=True,service_call_order_counts_proven=True,blocking_damage_bodies_proven=False,
        failures=failures,output_sha256=hashlib.sha256(q.stdout.encode()).hexdigest(),motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(rows),'ordered source blocking choices;',len(failures),'mismatches')
    if r['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
