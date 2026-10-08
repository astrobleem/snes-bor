"""Pinned dropweapon with no attached item; weapon switching is observed."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def run(engine,folder,flag=2):
    folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=engine).decode('latin1');function=extract(raw,'dropweapon')
    rows=[dict(type=t,loss=n,player=p) for t in (0,1,3,512) for n in (-2147483648,-1,0,1,2,2147483647) for p in (0,3)]
    if flag != 2:
        rows=[dict(r,player_weapon=w)for r in rows for w in(-1,0,5)]
    c=r'''#include <stdio.h>
#include <string.h>
#define TYPE_PLAYER 1
#define TYPE_NONE 0
#define ANI_RESPAWN 104
#define ANI_SPAWN 23
#define ANI_IDLE 0
typedef struct {int typeshot,shootnum,counter,animal,type,weaploss[2];} data;
typedef struct {int platform[1][8];} anim;
typedef struct entity {data modeldata;int direction,animpos,blink,playerindex;struct {float x,z,y;} position;float base;unsigned nextthink;struct entity *weapent;anim *animation;void (*takeaction)(void),(*think)(void);} entity;
entity *self;struct {int weapnum;} player[4];struct {int setweap;struct {float height;} walls[1];} lv,*level=&lv;unsigned time;
int calls,number,mode,unexpected,numbers[2],modes[2];
entity *check_platform(float x,float z,entity *e){unexpected++;return NULL;}
int checkwall(float x,float z){unexpected++;return -1;}
int validanim(entity *e,int n){unexpected++;return 0;}
void ent_set_anim(entity *e,int n,int r){unexpected++;}
void common_lie(void){}
void runanimal(void){}
void set_weapon(entity *e,int n,int m){if(e!=self||calls>=2)unexpected++;else{numbers[calls]=n;modes[calls]=m;}calls++;number=n;mode=m;}
''' + function + '\nint cases[][4]={' + ','.join('{'+','.join(str(v) if v!=-2147483648 else '(-2147483647-1)' for v in(r['type'],r['loss'],r['player'],r.get('player_weapon',5)))+'}' for r in rows)+'};\n'
    c+=r'''int main(void){unsigned i;entity e;int *r,j;if(sizeof(int)!=4||sizeof(void*)!=4)return 2;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){r=cases[i];memset(&e,0,sizeof(e));e.modeldata.type=r[0];e.modeldata.weaploss[1]=r[1];e.playerindex=r[2];self=&e;calls=unexpected=0;number=mode=-1;lv.setweap=7;
for(j=0;j<4;j++)player[j].weapnum=r[3];for(j=0;j<2;j++)numbers[j]=modes[j]=-1;dropweapon(FLAG);printf("DROP|%u|%d,%d,%d,%d,%d,%d,%d,%d,%d\n",i,calls,number,mode,self==&e&&!e.weapent,unexpected,numbers[0],modes[0],numbers[1],modes[1]);
}return 0;}
'''
    c=c.replace('dropweapon(FLAG)',f'dropweapon({flag})')
    (folder/'drop_weapon.c').write_text(c)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT');p=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','drop_weapon.c','-fe=drop_weapon_authority.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise ValueError('DROP_WEAPON_C_AUTHORITY_BUILD')
    output=subprocess.check_output([str((folder/'drop_weapon_authority.exe').resolve())],cwd=folder,text=True);results=[]
    for line in output.splitlines():
        if not line.startswith('DROP|'):continue
        _,i,values=line.split('|');i=int(i);actual=list(map(int,values.split(',')));r=rows[i];loss=r['loss'];seq=[]
        if flag<2:seq.append(r['player_weapon']or 7 if r['type']&1 else 0)
        if loss>0:seq.append(loss)
        wanted=[len(seq),seq[-1]if seq else -1,0 if seq else -1,1,0,seq[0]if seq else -1,0 if seq else -1,seq[1]if len(seq)>1 else -1,0 if len(seq)>1 else -1]
        results.append(dict(case=rows[i],actual=actual,expected=wanted,passed=actual==wanted))
    report=dict(schema='BYOR_4086_DROP_WEAPON_AUTHORITY_V2',status='PASS' if len(results)==len(rows) and all(r['passed'] for r in results) else 'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(function.encode('latin1')).hexdigest(),flag=flag,cases=len(rows),results=results,attached_item_branch_tested=False,weapon_transition_instrumented=True,motu_gameplay_proven=False)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--flag',type=int,choices=(0,1,2),default=2);a=p.parse_args();r=run(a.engine,a.output.resolve(),a.flag);print(json.dumps({k:r[k] for k in ('status','cases','function_sha256')}))
    if r['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
