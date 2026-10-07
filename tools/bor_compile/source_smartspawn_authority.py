"""Pinned smartspawn/colourmap C with constructor and events instrumented."""
import argparse
import hashlib
import itertools
import json
import os
import re
import subprocess
from pathlib import Path
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_stage_queue_4086 import derive
from source_smartspawn_4086 import post

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1')
    adjusted=re.sub(r'(entity \*smartspawn\([^\n]*?\))[^\n]*',r'\1',raw)
    smartspawn=extract(adjusted,'smartspawn');colourmap=extract(raw,'ent_set_colourmap')
    inputs=[]
    for stage in derive(Source(a.source))['stages']:
        for row in stage['records']:
            if row['kind']=='spawn':
                for players,current_map,music in itertools.product(range(1,5),(0,1),(0,1)):
                    inputs.append(dict(row=row,players=players,current_map=current_map,maps_loaded=2,music=music))
    for wanted,loaded,oldmap,players,music in itertools.product((-2147483648,-1,0,1,2,3,2147483647),(0,1,2),(0,1),range(1,5),(0,1)):
        row=dict(alias='Alias',health=[0,-1,2147483647,-2147483648],map=wanted,boss=1)
        inputs.append(dict(row=row,players=players,current_map=oldmap,maps_loaded=loaded,music=music))
    expected=[];cases=[]
    for c in inputs:
        r=c['row'];e=dict(name='fresh',health=111,model_health=222,map=c['current_map'],palette=c['current_map'],boss=-9,spawntype=0)
        trace=post(e,r,c['players'],c['maps_loaded'],c['music'])
        expected.append(dict(trace=[1]+[dict(COLOURMAP=2,BOSS_MUSIC=3,ONSPAWN=4,STAGE_SPAWN_SCRIPT=5)[x]for x in trace],state=[e['health'],e['model_health'],e['map'],e['palette'],e['boss'],e['spawntype'],e['name']]))
        cases.append('{'+','.join(map(str,[c['players'],c['current_map'],c['maps_loaded'],c['music'],r['map'],r['boss']]))+',{'+','.join(map(str,r['health']))+'},'+json.dumps(r['alias'])+'}')
    code=r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define TYPE_PLAYER 1
#define SCROLL_INWARD 1
#define SCROLL_OUTWARD 2
#define MAX(a,b) ((a)>(b)?(a):(b))
#define MAX_NAME_LEN 47
typedef struct Model {int health,mp,score,multiple,aggression,alpha,nolife,weapnum,maps_loaded;void *palette,*colourmap[2];} Model;
typedef struct {float x,z,y;} Position;
typedef struct entity {Model modeldata;Position position;unsigned map;void *colourmap;char name[48],itemalias[48];int health,mp,item,itemmap,itemhealth,itemplayer_count,spawntype,itemtrans,dying,per1,per2,boss;struct entity *weapent;} entity;
typedef struct {int spawnplayer_count,boss,flip,index,itemindex,itemmap,itemhealth,itemplayer_count,spawntype,mp,score,multiple,colourmap,aggression,itemtrans,alpha,dying,per1,per2,nolife,weaponindex,health[4];char *name,*item,*weapon;char alias[48],itemalias[48];Model *model,*weaponmodel;Position position;} s_spawn_entry;
typedef struct {int scrolldir,bosses,bossmusic_offset;char bossmusic[48];} Level;
Level lev,*level=&lev;entity ent;int players,trace[16],nt;float advancex,advancey;
void event(int n){trace[nt++]=n;}
int count_ents(int type){return players;}
entity *spawn(float x,float z,float y,int dir,char *name,int index,Model *model){event(1);ent.position.x=x;ent.position.z=z;ent.position.y=y;return &ent;}
void music(char *name,int loop,int offset){event(3);}
void set_weapon(entity *e,int n,int flag){}
void execute_onspawn_script(entity *e){event(4);}
void execute_spawn_script(s_spawn_entry *p,entity *e){event(5);}
'''+colourmap+'\n'+smartspawn+'\nstruct {int players,map,loaded,music,wanted,boss,health[4];char *alias;} cases[]={'+','.join(cases)+r'''};
int main(void){unsigned i;int j,pi;entity *e;s_spawn_entry p;
if(sizeof(int)!=4||sizeof(void*)!=4)return 2;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){memset(&ent,0,sizeof(ent));memset(&p,0,sizeof(p));memset(&lev,0,sizeof(lev));nt=0;players=cases[i].players;
strcpy(ent.name,"fresh");ent.health=111;ent.modeldata.health=222;ent.map=cases[i].map;ent.boss=-9;ent.modeldata.maps_loaded=cases[i].loaded;ent.modeldata.palette=(void*)100;ent.modeldata.colourmap[0]=(void*)101;ent.modeldata.colourmap[1]=(void*)102;ent.colourmap=(void*)(100+ent.map);
strcpy(p.alias,cases[i].alias);p.spawntype=1;p.colourmap=cases[i].wanted;p.boss=cases[i].boss;for(j=0;j<4;j++)p.health[j]=cases[i].health[j];if(cases[i].music)strcpy(lev.bossmusic,"music");
e=smartspawn(&p);printf("SMART|%u|",i);for(j=0;j<nt;j++)printf("%s%d",j?",":"",trace[j]);pi=(int)e->colourmap-100;printf("|%d,%d,%u,%d,%d,%d|%s\n",e->health,e->modeldata.health,e->map,pi,e->boss,e->spawntype,e->name);}return 0;}
'''
    # Observe the real function's palette call without replacing its body.
    code=code.replace('void ent_set_colourmap(entity *ent, unsigned int which)\n{','void ent_set_colourmap(entity *ent, unsigned int which)\n{\n event(2);')
    (a.output/'smartspawn.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','smartspawn.c','-fe=smartspawn.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('SMARTSPAWN_AUTHORITY_C_BUILD')
    log=subprocess.check_output([str(a.output/'smartspawn.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[]
    for line in log.splitlines():
        if line.startswith('SMART|'):
            _,i,trace,state,name=line.split('|');actual.append(dict(trace=[int(x)for x in trace.split(',')],state=[*map(int,state.split(',')),name]))
    ok=actual==expected;d=dict(schema='BYOR_4086_SMARTSPAWN_STAGE_PROPERTIES_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,functions_sha256=hashlib.sha256((smartspawn+colourmap).encode()).hexdigest(),cases=len(inputs),inputs=inputs,actual=actual,expected=expected,constructor_instrumented=True,spawn_scripts_instrumented=True,music_instrumented=True,native_properties_bound=False,live_queue_dispatch_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');print(d['status'],len(inputs),'smartspawn property cases')
    if not ok:raise SystemExit(1)

if __name__=='__main__':main()
