"""Compile literal pinned scroller camera block, including WAIT and role bounds."""
import argparse
import copy
import hashlib
import itertools
import json
import os
import subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_camera_4086 import move,bits

FIELDS=('x','y','dx','dy','pos','waiting','timeleft','go_time')
def normalized(s):return [bits(s[k])if k in ('x','y','dx','dy')else s[k]for k in FIELDS]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1');full=extract(raw,'update_scroller')
    start=full.index('    for(i = 0;');block=full[start:]
    cases=[];expected=[]
    role_sets=[[],[dict(x=80.,z=220.,a=0.)],[dict(x=800.,z=240.,a=93.)],[dict(x=80.,z=220.,a=0.),None,dict(x=900.,z=100.,a=50.)],[None,None,None,dict(x=400.,z=270.,a=100.)],[dict(x=2239.5,z=220.5,a=12.25),dict(x=2240.25,z=221.25,a=0.)]]
    for direction,width,height,x,speed,waiting,enemies,cameratype,roles in itertools.product((2,3,8,9),(320,768,2544),(245,256),(0.,40.5,448.,2224.),(.5,1.),(0,1),(0,1),(0,1),role_sets):
        s=dict(direction=direction,width=width,height=height,x=x,y=6.25,dx=0.,dy=0.,speed=speed,waiting=waiting,enemies=enemies,cameratype=cameratype,players=roles+[None]*(4-len(roles)),maxplayers=4,offsetx=0.,offsetz=0.,minx=0.,maxx=float(width-320),minz=0.,maxz=float(height),blockade=25.,rocking=0,hres=320,vres=240,pos=77,noreset=0,settime=100,time=48,timeleft=-77,go_time=123)
        cases.append(s);v=copy.deepcopy(s);move(v);expected.append(normalized(v))
    # Sequential endpoint progress and asymmetric source clamp/control cases.
    for maxplayers,noreset,time,rocking,offsetx,offsetz in itertools.product((1,2,4),(0,2),(0,0xfffffff0),(0,1),(-50.,100.),(-25.,40.)):
        s=dict(cases[-1],maxplayers=maxplayers,noreset=noreset,time=time,rocking=rocking,offsetx=offsetx,offsetz=offsetz,waiting=1,enemies=0)
        cases.append(s);v=copy.deepcopy(s);move(v);expected.append(normalized(v))
    crows=[]
    for s in cases:
        values=[s[k]for k in ('direction','width','height','x','y','speed','waiting','enemies','cameratype','maxplayers','offsetx','offsetz','minx','maxx','minz','maxz','blockade','rocking','hres','vres','pos','noreset','settime','time','timeleft','go_time')]
        roles=['{'+','.join(map(str,([1,p['x'],p['z'],p['a']]if p else[0,0,0,0])))+'}'for p in s['players']]
        crows.append('{'+','.join(map(str,values))+',{'+','.join(roles)+'}}')
    code=r'''#include <stdio.h>
#include <string.h>
#define TYPE_ENEMY 2
#define GAME_SPEED 200
#define COUNTER_SPEED (GAME_SPEED*2)
#define SCROLL_RIGHT 2
#define SCROLL_LEFT 8
#define SCROLL_BACK 1
#define SCROLL_INWARD 32
#define SCROLL_OUTWARD 64
#define SCROLL_UP 16
#define SCROLL_DOWN 4
typedef struct {float x,z,y;} Position;
typedef struct {Position position;} Entity;
typedef struct {Entity *ent;} Player;
struct {int scrolldir,width,waiting,noreset,settime,pos,rocking;float cameraxoffset,camerazoffset,scrollspeed;} lev,*level=&lev;
struct {int maxplayers;} levelsets[1];int current_set=0;
struct {int hRes,vRes;} videomodes;
Player player[4];Entity ents[4];int panel_height,cameratype,enemies,timeleft;unsigned int time,go_time;
float advancex,advancey,scrolldx,scrolldy,scrollminx,scrollmaxx,scrollminz,scrollmaxz,blockade;
void *findent(int mask){return enemies?&lev:0;}
void camera(void){float to=0;int i,againstend=0,numplay=0;float tx=advancex,ty=advancey;float rm=-9999,lm=999999,bm=-9999,tm=999999;static int scrolladd=0;
'''+block+r'''
struct {int direction,width,height;float x,y,speed;int waiting,enemies,cameratype,maxplayers;float offsetx,offsetz,minx,maxx,minz,maxz,blockade;int rocking,hres,vres,pos,noreset,settime;unsigned int time;int timeleft;unsigned int go_time;struct {int live;float x,z,a;} roles[4];} cases[]={'''+','.join(crows)+r'''};
unsigned int fb(float f){unsigned int v;memcpy(&v,&f,4);return v;}
int main(void){unsigned i;int j;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
level->scrolldir=cases[i].direction;level->width=cases[i].width;panel_height=cases[i].height;advancex=cases[i].x;advancey=cases[i].y;level->scrollspeed=cases[i].speed;level->waiting=cases[i].waiting;enemies=cases[i].enemies;cameratype=cases[i].cameratype;levelsets[0].maxplayers=cases[i].maxplayers;level->cameraxoffset=cases[i].offsetx;level->camerazoffset=cases[i].offsetz;scrollminx=cases[i].minx;scrollmaxx=cases[i].maxx;scrollminz=cases[i].minz;scrollmaxz=cases[i].maxz;blockade=cases[i].blockade;level->rocking=cases[i].rocking;videomodes.hRes=cases[i].hres;videomodes.vRes=cases[i].vres;level->pos=cases[i].pos;level->noreset=cases[i].noreset;level->settime=cases[i].settime;time=cases[i].time;timeleft=cases[i].timeleft;go_time=cases[i].go_time;scrolldx=scrolldy=0;
for(j=0;j<4;j++){player[j].ent=cases[i].roles[j].live?ents+j:0;ents[j].position.x=cases[i].roles[j].x;ents[j].position.z=cases[i].roles[j].z;ents[j].position.y=cases[i].roles[j].a;}
camera();printf("%u,%u,%u,%u,%d,%d,%d,%u\n",fb(advancex),fb(advancey),fb(scrolldx),fb(scrolldy),level->pos,level->waiting,timeleft,go_time);
}return 0;}
'''
    (a.output/'camera.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','camera.c','-fe=camera.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('CAMERA_AUTHORITY_BUILD')
    log=subprocess.check_output([str(a.output/'camera.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,line.split(',')))for line in log.splitlines()]
    failures=[dict(index=i,input=cases[i],expected=e,actual=v)for i,(e,v)in enumerate(zip(expected,actual))if e!=v]
    ok=not failures and len(actual)==len(expected);d=dict(schema='BYOR_4086_HORIZONTAL_CAMERA_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,block_sha256=hashlib.sha256(block.encode()).hexdigest(),cases=len(cases),inputs=cases,expected=expected,actual=actual,failures=failures[:20],supported_directions=[2,3,8,9],native_camera_bound=False,moving_rendering_bound=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');print(d['status'],len(cases),'horizontal camera cases',len(failures),'failures')
    if not ok:raise SystemExit(1)
if __name__=='__main__':main()
