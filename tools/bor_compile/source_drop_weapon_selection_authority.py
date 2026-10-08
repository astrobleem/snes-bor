"""Coupled pinned dropweapon(1)/set_weapon; model transitions observed."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    bodies={n:extract(raw,n)for n in('set_weapon','dropweapon')}
    lists=(None,[],[2,0],[0,1],[-1,2])
    rows=[dict(type=t,model=m,owner=o,loss=loss)for t,m,o,loss in itertools.product((0,2,512),(0,3),range(5),(-2147483648,-1,0,1,2,2147483647))]
    code=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define TYPE_PLAYER 1
#define TYPE_NONE 0
#define WEAPLOSS_TYPE_CHANGE 3
#define ANI_RESPAWN 104
#define ANI_SPAWN 23
#define ANI_IDLE 0
typedef struct{int id;}s_model;
typedef struct{int typeshot,shootnum,counter,animal,type,weaploss[2],*weapon,numweapons;}data;
typedef struct{int platform[1][8];}anim;
typedef struct entity{data modeldata;int direction,animpos,blink,playerindex;s_model *defaultmodel;struct{float x,z,y;}position;float base;unsigned nextthink;struct entity *weapent;anim *animation;void(*takeaction)(void),(*think)(void);}entity;
entity *self;struct{int weapnum;}player[4];struct{int setweap;struct{float height;}walls[1];}lv,*level=&lv;unsigned time;
int calls,target[2],syncvalue[2],unexpected;
entity *check_platform(float x,float z,entity *e){unexpected++;return NULL;}
int checkwall(float x,float z){unexpected++;return -1;}
int validanim(entity *e,int n){unexpected++;return 0;}
void ent_set_anim(entity *e,int n,int r){unexpected++;}
void common_lie(void){}
void runanimal(void){}
void set_model_ex(entity *e,char *name,int index,s_model *m,int sync){if(e!=self||calls>=2)unexpected++;else{target[calls]=m?m->id:index;syncvalue[calls]=sync;}calls++;}
'''+ '\n'.join(bodies.values())+'\nstruct Case{int type,model,owner,loss;}cases[]={\n'
    code+=',\n'.join('{'+','.join('(-2147483647-1)'if v==-2147483648 else str(v)for v in r.values())+'}'for r in rows)+'\n};\n'
    code+=r'''
int main(void){entity e;s_model def;unsigned i;int j;int weapons[][2]={{0,0},{2,0},{0,1},{-1,2}};struct Case *c;
if(sizeof(int)!=4||sizeof(void*)!=4)return 2;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
c=cases+i;memset(&e,0,sizeof(e));self=&e;def.id=c->model;e.defaultmodel=&def;e.modeldata.type=c->type;e.modeldata.weaploss[1]=c->loss;e.modeldata.weapon=c->owner?weapons[c->owner-1]:NULL;e.modeldata.numweapons=c->owner>1?2:0;
calls=unexpected=0;for(j=0;j<2;j++)target[j]=syncvalue[j]=-777;for(j=0;j<4;j++)player[j].weapnum=5;lv.setweap=7;
dropweapon(1);printf("COUPLED|%u|%d,%d,%d,%d,%d,%d,%d\n",i,calls,target[0],syncvalue[0],target[1],syncvalue[1],unexpected,self==&e&&!e.weapent);
}return 0;}
'''
    (folder/'drop_selection.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','drop_selection.c','-fe=drop_selection.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('DROP_SELECTION_C_BUILD:'+build.stdout+build.stderr)
    log=subprocess.check_output([str(folder/'drop_selection.exe')],cwd=folder,text=True);results=[]
    for line in log.splitlines():
        if not line.startswith('COUPLED|'):continue
        _,index,values=line.split('|');r=rows[int(index)];actual=list(map(int,values.split(',')));target=r['model']
        if r['loss']>0:
            w=lists[r['owner']]
            if w and r['loss']<=len(w)and w[r['loss']-1]:target=w[r['loss']-1]
        expected=[2 if r['loss']>0 else 1,r['model'],1,target if r['loss']>0 else -777,1 if r['loss']>0 else -777,0,1]
        results.append(dict(case=r,actual=actual,expected=expected,passed=actual==expected,model_transition_required=target!=r['model'],source_invalid_model_selection=target<0))
    ok=len(results)==len(rows)and all(r['passed']for r in results)
    report=dict(schema='BYOR_4086_DROP_WEAPON_SELECTION_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,functions={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},cases=len(rows),results=results,
                domain='no attached item; nonplayer; default model equals current; includes second weapon-loss override',model_transition_service_instrumented=True,full_source_model_transition_body_proven=False,native_drop_weapon_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'coupled source drop/selection cases')
    if not ok:raise SystemExit(1)


if __name__=='__main__':main()
