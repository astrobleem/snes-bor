"""Run literal check_lost with measured death/damage requests and freeze macro."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_freeze_authority import macro
from source_lost_4086 import decide


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1')
    header=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.h'],cwd=a.engine).decode('latin1')
    function=extract(raw,'check_lost');freeze=macro(header,'is_frozen');rng=random.Random(408613);rows=[]
    for direction in (2,3,4,8,16,18):
        for coords in ((0,0,0),(320,240,0),(-3000,0,0),(-3000.25,0,0),(3320,0,0),(3320.25,0,0),
                       (0,-3000,0),(0,-3000.25,0),(0,3240,0),(0,3240.25,0),(0,220,-250),
                       (0,220,-250.25),(0,220,-500),(0,220,-500.25),(-32768,100000,0),
                       (-32768,100000,-500.25),(0,220,1000)):
            for typ in (0,1,2,128,129):
                for life in (-1,0,1,300,0x7fffffff):
                    rows.append(dict(direction=direction,x=coords[0],z=coords[1],y=coords[2],type=typ,lifespan=life,
                        offscreenkill=rng.choice((0,1,3000,-1)),default_offscreenkill=3000,advancex=0,advancey=0,hres=320,vres=240,
                        takedamage=rng.choice((0,1)),health=rng.choice((-1,0,70,150)),frozen=rng.choice((0,1,-1)),
                        textbox=rng.choice((0,1)),bomber=rng.choice((0,1,2)),token=1,time=48,freezetime=rng.choice((0,47,48,49,0xffffffff)),
                        default_dropv=[1.25,-2.5,3.75]))
    # Disabled-freeze, exact zero lifespan and infinite lifetime are explicit.
    for life in (-1,0,1,0x7fffffff):
        rows.append(dict(rows[-1],x=80,z=220,y=0,offscreenkill=0,lifespan=life,frozen=0,textbox=0,bomber=0,takedamage=1))
    for osk in (-0x80000000,-32768,32767,0x7fffffff):
        for x,z,y,ax,ay in ((32767.5,-32768,0,-32768,32767.5),(-32768,32767.5,-250,32767.5,-32768),(0,100000,-500,0,0)):
            for direction in (2,4,16,18):
                rows.append(dict(rows[-1],offscreenkill=osk,x=x,z=z,y=y,advancex=ax,advancey=ay,direction=direction))
    keys=('direction','x','z','y','type','lifespan','offscreenkill','default_offscreenkill','advancex','advancey','hres','vres','takedamage','health','frozen','textbox','bomber','time','freezetime')
    crows=['{'+','.join(str(r[k])+('u'if k in ('time','freezetime')else '')for k in keys)+'}'for r in rows]
    code=r'''#include <stdio.h>
#include <string.h>
#define TYPE_PLAYER 1
#define TYPE_TEXTBOX 128
#define SCROLL_UP 16
#define SCROLL_DOWN 4
#define PIT_DEPTH -250
#define ATK_PIT 17
#define ATK_LIFESPAN 18
typedef struct {float x,z,y;} vector;
typedef struct {vector dropv;int attack_force,attack_type;} s_attack;
typedef struct entity {struct {int offscreenkill,type;} modeldata;vector position;int health,frozen,lifespancountdown;unsigned freezetime;void (*takedamage)(struct entity*,s_attack*);} entity;
entity ent,other,*self=&ent,*textbox,*smartbomber;
s_attack emptyattack;vector default_model_dropv={1.25,-2.5,3.75};
struct {int scrolldir;} lev,*level=&lev;struct {int hRes,vRes;} videomodes;
float advancex,advancey;unsigned time;int DEFAULT_OFFSCREEN_KILL,action,force,kind;
void kill(entity *e){action=1;}
void player_die(void){action=2;}
void damage(entity *e,s_attack *a){action=a->attack_type==ATK_PIT?3:4;force=a->attack_force;kind=a->attack_type;printf("D,%g,%g,%g;",a->dropv.x,a->dropv.z,a->dropv.y);}
'''+freeze+'\n'+function+r'''
struct {int direction;float x,z,y;int type,lifespan,osk,default_osk;float ax,ay;int hres,vres,damage,health,frozen,textbox,bomber;unsigned time,freezetime;} cases[]={'''+','.join(crows)+r'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
memset(&ent,0,sizeof(ent));level->scrolldir=cases[i].direction;ent.position.x=cases[i].x;ent.position.z=cases[i].z;ent.position.y=cases[i].y;ent.modeldata.type=cases[i].type;ent.lifespancountdown=cases[i].lifespan;ent.modeldata.offscreenkill=cases[i].osk;DEFAULT_OFFSCREEN_KILL=cases[i].default_osk;advancex=cases[i].ax;advancey=cases[i].ay;videomodes.hRes=cases[i].hres;videomodes.vRes=cases[i].vres;ent.takedamage=cases[i].damage?damage:0;ent.health=cases[i].health;ent.frozen=cases[i].frozen;textbox=cases[i].textbox?&other:0;smartbomber=cases[i].bomber==1?&ent:cases[i].bomber==2?&other:0;time=cases[i].time;ent.freezetime=cases[i].freezetime;action=force=kind=0;
check_lost();printf("R,%d,%d,%d,%d\n",action,ent.lifespancountdown,force,kind);
}return 0;}
'''
    (folder/'lost.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','lost.c','-fe=lost.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode:raise ValueError('SOURCE_LOST_AUTHORITY_BUILD')
    log=subprocess.check_output([str(folder/'lost.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(log)
    actual=[]
    for line in log.splitlines():
        parts=line.split(';');v=list(map(int,parts[-1].split(',')[1:]));d=dict(action=v[0],lifespan=v[1])
        if len(parts)>1:d.update(attack_force=v[2],attack_type=v[3],dropv=list(map(float,parts[0].split(',')[1:])))
        actual.append(d)
    expected=[decide(r)for r in rows];failures=[i for i,(e,v)in enumerate(zip(expected,actual))if e!=v];ok=len(actual)==len(rows)and not failures
    report=dict(schema='BYOR_4086_LOST_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,function_sha256=hashlib.sha256(function.encode()).hexdigest(),freeze_macro_sha256=hashlib.sha256(freeze.encode()).hexdigest(),cases=len(rows),inputs=rows,expected=expected,actual=actual,failures=failures[:20],death_damage_handlers_instrumented=True,native_backend_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'lost-entity cases')
    if not ok:raise SystemExit(1)


if __name__=='__main__':main()
