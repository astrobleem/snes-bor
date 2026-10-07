"""Actual pinned update_scroller queue block with spawn/count services measured separately."""
import argparse
import copy
import hashlib
import itertools
import json
import os
import subprocess
from pathlib import Path
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from source_stage_queue_4086 import derive
from source_stage_dispatch_4086 import dispatch


FIELDS=('index','groupmin','groupmax','waiting','go_time','completed','advancetime')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);a.output=a.output.resolve()
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1')
    start=raw.index('    if(current_spawn >= level->numspawns',raw.index('void update_scroller()'))
    end=raw.index('\n    for(i = 0;',start)
    block=raw[start:end]
    source=derive(Source(a.source));tests=[];expected=[];cinputs=[]
    for stage in source['stages']:
        records=stage['records']
        for index in range(len(records)+1):
            at=records[index]['at'] if index<len(records)else 0
            for enemies,(minimum,maximum),offset in itertools.product(range(4),((1,1),(2,3),(100,100)),(-1,0,1)):
                state=dict(index=index,groupmin=minimum,groupmax=maximum,waiting=0,go_time=77,completed=0,time=48,advancetime=47,freezeall=0,pos=at+offset,players=[dict(dead=0),None,None,None],leveltype=0)
                tests.append((stage['stage_id']-1,state,enemies,0,0))
        for live,leveltype,mask,completed,frozen,timing in itertools.product((0,1),range(3),(0,4,8,256),(0,1),(0,1),(0,1)):
            state=dict(index=len(records),groupmin=100,groupmax=100,waiting=0,go_time=77,completed=completed,time=48,advancetime=49 if timing else 47,freezeall=frozen,pos=0,players=[dict(dead=not live),None,None,None],leveltype=leveltype)
            tests.append((stage['stage_id']-1,state,0,mask,live))
    for sid,state,enemies,mask,live in tests:
        s=copy.deepcopy(state);entities=[dict(exists=1,type=2,dead=0)for _ in range(enemies)]
        if mask:entities.append(dict(exists=1,type=mask,dead=0))
        def spawn(row,pool):
            if row['kind']=='spawn':pool.append(dict(exists=1,type=2,dead=0))
        trace=dispatch(s,source['stages'][sid]['records'],entities,spawn)
        expected.append([*[s[k] for k in FIELDS],sum(e['type']==2 for e in entities),len(trace)])
        cinputs.append('{'+','.join(map(str,[sid,state['index'],state['groupmin'],state['groupmax'],state['pos'],enemies,mask,int(not state['players'][0]['dead']),state['leveltype'],state['completed'],state['freezeall'],state['advancetime']]))+'}')
    stage_arrays=[]
    for stage in source['stages']:
        rows=[]
        for r in stage['records']:
            rows.append('{'+','.join(map(str,[r['at'],int(r['kind']=='wait'),*r['group'],int(r['kind']=='spawn')]))+'}')
        stage_arrays.append('{'+str(len(rows))+',{'+','.join(rows)+'}}')
    code=r'''#include <stdio.h>
#include <string.h>
#define TYPE_ENEMY 2
#define TYPE_ITEM 4
#define TYPE_OBSTACLE 8
#define TYPE_ENDLEVEL 256
typedef struct {int dead;} Entity;
typedef struct {Entity *ent;} Player;
typedef struct {int x,y;} XY;
typedef struct {int at,wait,groupmin,groupmax,spawn;int musicfade,nojoin,scrollminz,scrollmaxz,scrollminx,scrollmaxx,blockade,palette,shadowcolor,shadowalpha,musicoffset;char music[128];XY light;} Row;
typedef struct {int numspawns;Row spawnpoints[128];int pos,type,waiting;} Level;
struct {int numspawns;Row spawnpoints[128];} stages[]={'''+','.join(stage_arrays)+r'''};
struct {int stage,index,minimum,maximum,pos,enemies,mask,live,type,completed,frozen,advancetime;} cases[]={'''+','.join(cinputs)+r'''};
Level lev,*level=&lev;Player player[4];Entity entity;
int current_spawn,groupmin,groupmax,level_completed,go_time,time,advancey,scrollminz,scrollmaxz,scrollminx,scrollmaxx,nojoin,blockade,shadowcolor,shadowalpha,musicoffset,musicloop,enemy_count,othermask,spawn_calls;char musicname[128];float musicfade[2];struct {int musicvol;} savedata;XY light;
int count_ents(int mask){return mask==TYPE_ENEMY?enemy_count:0;}
Entity *findent(int mask){return ((mask&TYPE_ENEMY)&&enemy_count)||(mask&othermask)?&entity:0;}
void change_system_palette(int palette){}
void smartspawn(Row *r){spawn_calls++;if(r->spawn)enemy_count++;}
int main(void){unsigned i;int adv;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
memset(&lev,0,sizeof(lev));lev.numspawns=stages[cases[i].stage].numspawns;memcpy(lev.spawnpoints,stages[cases[i].stage].spawnpoints,sizeof(lev.spawnpoints));lev.pos=cases[i].pos;lev.type=cases[i].type;
memset(player,0,sizeof(player));entity.dead=!cases[i].live;player[0].ent=&entity;
current_spawn=cases[i].index;groupmin=cases[i].minimum;groupmax=cases[i].maximum;enemy_count=cases[i].enemies;othermask=cases[i].mask;level_completed=cases[i].completed;go_time=77;spawn_calls=0;time=48;adv=cases[i].advancetime;
if(time>=adv&&!cases[i].frozen){adv=time;if(!level_completed){
'''+block+r'''
}}
printf("QUEUE|%u|%d,%d,%d,%d,%d,%d,%d,%d,%d\n",i,current_spawn,groupmin,groupmax,level->waiting,go_time,level_completed,adv,enemy_count,current_spawn-cases[i].index);
}return 0;}
'''
    (a.output/'queue.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','queue.c','-fe=queue.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('STAGE_DISPATCH_AUTHORITY_BUILD')
    log=subprocess.check_output([str(a.output/'queue.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log)
    actual=[list(map(int,line.split('|')[2].split(',')))for line in log.splitlines()if line.startswith('QUEUE|')]
    ok=actual==expected;d=dict(schema='BYOR_4086_STAGE_DISPATCH_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,queue_block_sha256=hashlib.sha256(block.encode()).hexdigest(),cases=len(tests),actual=actual,expected=expected,spawn_and_entity_services_instrumented=True,camera_movement_bound=False,native_dispatch_bound=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');print(d['status'],len(tests),'queue dispatch cases')
    if not ok:raise SystemExit(1)

if __name__=='__main__':main()
