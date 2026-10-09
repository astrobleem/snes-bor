"""Pinned player dropweapon selection with exact set_weapon bookkeeping."""
import argparse,hashlib,itertools,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract

LISTS=(None,[],[2,0],[0,1])


def selected(owner,number,default):
    w=LISTS[owner]
    return w[number-1]if w and 0<number<=len(w)and w[number-1]else default


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1');bodies={n:extract(raw,n)for n in ('set_weapon','dropweapon')}
    rows=[dict(type=typ,model=model,owner=owner,loss=loss,loss0=loss0,number=number,level=level,player=player)for typ,model,owner,loss,loss0,number,level,player in itertools.product((1,3),(0,3),range(4),(-1,0,1,2,3),(-1,0,3),(-2147483648,-1,0,1,2,3,2147483647),(-1,0,1,2,5),(0,3))]
    pre=r'''
#include <stdio.h>
#include <string.h>
#define TYPE_PLAYER 1
#define TYPE_NONE 0
#define WEAPLOSS_TYPE_CHANGE 3
#define ANI_RESPAWN 104
#define ANI_SPAWN 23
#define ANI_IDLE 0
typedef struct {int id;}s_model;
typedef struct {int typeshot,shootnum,counter,animal,type,weaploss[2],*weapon,numweapons;}data;
typedef struct {int platform[1][8];}anim;
typedef struct entity {data modeldata;int direction,animpos,blink,playerindex;s_model *defaultmodel;struct{float x,z,y;}position;float base;unsigned nextthink;struct entity *weapent;anim *animation;void(*takeaction)(void),(*think)(void);}entity;
entity *self;struct{int weapnum;}player[4];struct{int setweap;struct{float height;}walls[1];}lv,*level=&lv;unsigned time;
int calls,target[2],syncvalue[2],unexpected;
entity *check_platform(float x,float z,entity *e){unexpected++;return NULL;}
int checkwall(float x,float z){unexpected++;return -1;}
int validanim(entity *e,int a){unexpected++;return 0;}
void ent_set_anim(entity *e,int a,int r){unexpected++;}
void common_lie(void){}
void runanimal(void){}
void set_model_ex(entity *e,char *name,int index,s_model *m,int sync){if(e!=self||calls>=2)unexpected++;else{target[calls]=m?m->id:index;syncvalue[calls]=sync;}calls++;}
'''
    code=pre+'\n'.join(bodies.values())+r'''
int main(void){int typ,model,owner,loss,loss0,number,lev,pi,j;entity e;s_model def;int lists[][2]={{0,0},{2,0},{0,1}};
while(scanf("%d %d %d %d %d %d %d %d",&typ,&model,&owner,&loss,&loss0,&number,&lev,&pi)==8){memset(&e,0,sizeof(e));self=&e;def.id=model;e.defaultmodel=&def;e.modeldata.type=typ;e.modeldata.weaploss[0]=loss0;e.modeldata.weaploss[1]=loss;e.modeldata.weapon=owner?lists[owner-1]:NULL;e.modeldata.numweapons=owner>1?2:0;e.playerindex=pi;for(j=0;j<4;j++)player[j].weapnum=77;player[pi].weapnum=number;lv.setweap=lev;calls=unexpected=0;for(j=0;j<2;j++)target[j]=syncvalue[j]=-777;dropweapon(1);printf("%d %d %d %d %d %d %d %d %d %d\n",calls,target[0],syncvalue[0],target[1],syncvalue[1],unexpected,player[0].weapnum,player[1].weapnum,player[2].weapnum,player[3].weapnum);}return 0;}
'''
    (a.output/'player_drop.c').write_text(code,encoding='latin1');env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');q=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','player_drop.c','-fe=player_drop.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(q.stdout+q.stderr)
    if q.returncode:raise ValueError('PLAYER_DROP_C_BUILD:'+q.stdout+q.stderr)
    q=subprocess.run([str(a.output/'player_drop.exe')],input=''.join(' '.join(str(v)for v in r.values())+'\n'for r in rows),capture_output=True,text=True);actual=[list(map(int,l.split()))for l in q.stdout.splitlines()];results=[]
    for i,r in enumerate(rows):
        n=r['number']or r['level'];first=selected(r['owner'],n,r['model']);second=selected(r['owner'],r['loss'],r['model'])if r['loss']>0 else-777;finalnumber=r['loss']if r['loss']>0 else n;players=[77]*4;players[r['player']]=finalnumber if r['loss0']==3 else r['level'];expected=[2 if r['loss']>0 else 1,first,1,second,1 if r['loss']>0 else-777,0,*players];got=actual[i]if i<len(actual)else None
        results.append(dict(case=r,actual=got,expected=expected,passed=got==expected,first_model_change_required=first!=r['model'],second_model_change_required=second!=-777 and second!=r['model']))
    ok=q.returncode==0 and len(actual)==len(rows)and all(r['passed']for r in results);report=dict(schema='BYOR_PLAYER_DROP_WEAPON_AUTHORITY_V1',status='PASS'if ok else'FAIL',cases=len(rows),engine_commit=ENGINE_COMMIT,functions={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},source_functions_unmodified=True,model_transition_instrumented=True,second_call_on_changed_model_not_proven=True,results=results,full_damage_callback_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'source player selection/bookkeeping cases')
    if not ok:raise SystemExit(1)


if __name__=='__main__':main()
