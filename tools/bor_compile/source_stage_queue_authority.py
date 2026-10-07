"""Compile pinned queue loader cases with real C memset/copy/float stores."""
import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_model_registry import derive as registry
from source_stage_queue_4086 import load,KINDS,derive,pack,unpack
from dialect_4086 import ENGINE_COMMIT

COMMANDS={'spawn':'SPAWN','wait':'WAIT','group':'GROUP','at':'AT','coords':'COORDS','alias':'ALIAS','health':'HEALTH','2phealth':'2PHEALTH','3phealth':'3PHEALTH','4phealth':'4PHEALTH','map':'MAP','flip':'FLIP','boss':'BOSS'}

def normalized(r):
    return [KINDS[r['kind']],r['model'],r['at'],*[struct.unpack('<I',struct.pack('<f',x))[0]for x in r['coords']],r['flip'],*r['health'],r['map'],r['boss'],*r['group'],r['alias']]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1')
    header=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.h'],cwd=a.engine).decode('latin1');name_limit=int(re.search(r'#define\s+MAX_NAME_LEN\s+(\d+)',header)[1])
    bodies=[]
    for n in COMMANDS.values():
        start=raw.index('        case CMD_LEVEL_'+n+':');end=raw.index('            break;',start)+len('            break;');bodies.append(raw[start:end])
    source=Source(a.source);models=registry(source)['models'];ids={key(m['identity']):m['id']for m in models}
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')};shape=discover(source,docs);tests=[];seen=set()
    for s in shape['sets']:
        for e in s['entries']:
            k=key(e['source_path'])
            if e['kind']=='STAGE'and k not in seen:
                seen.add(k);tests.append([r for r in docs[k]['directives']if r['directive']in COMMANDS])
    def rows(commands):return [dict(directive=n,values=v,line=i+1)for i,(n,v)in enumerate(commands)]
    identity=models[0]['identity']
    for health in ('0','-1','2147483647','-2147483648','4.9','abc'):
        tests.append(rows([('spawn',[identity]),('health',[health]),('2phealth',['77']),('3phealth',['-2']),('4phealth',['0']),('coords',['1.005','-0.1','300']),('alias',['Alias']),('map',['2']),('flip',['-1']),('boss',['1']),('at',['123']),('at',['124'])]))
    for minimum in ('-1','0','1','3','100'):
        for maximum in ('-1','0','1','100'):
            tests.append(rows([('spawn',[identity]),('health',['50']),('group',[minimum,maximum]),('at',['0']),('wait',[]),('at',['2']),('at',['3'])]))
    expected=[normalized(r)for test in tests for r in load(test,ids)]
    commands=[]
    for test in tests:
        commands.append('{-1,{"","",""}}')
        for r in test:
            args=(r['values']+['']*3)[:3]
            commands.append('{'+str(list(COMMANDS).index(r['directive']))+',{'+','.join(json.dumps(x)for x in args)+'}}')
    defines='\n'.join('#define CMD_LEVEL_'+n+' '+str(i)for i,n in enumerate(COMMANDS.values()))
    code=r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define GET_ARG(n) args[n-1]
#define GET_INT_ARG(n) atoi(GET_ARG(n))
#define GET_FLOAT_ARG(n) atof(GET_ARG(n))
#define __realloc(a,b) ((void)0)
typedef struct {char *name;} Model;
typedef struct {float x,z,y;} Position;
typedef struct {Position position;char *name;int index,itemindex,weaponindex,spawnplayer_count,spawntype,wait,at,health[4],colourmap,flip,boss,groupmin,groupmax;char alias[48];int spawnscript;} Entry;
typedef struct {Entry spawnpoints[256];int numspawns,bosses;} Level;
int Script_IsInitialized(int *p){return 0;}void Script_Compile(int *p){}
'''+defines+'\n#define MAX_NAME_LEN '+str(name_limit)+'\nModel models[]={'+','.join('{'+json.dumps(m['identity'])+'}'for m in models)+r'''};
int model_count=sizeof(models)/sizeof(models[0]);
Model *findmodel(char *name){int i;for(i=0;i<model_count;i++)if(!stricmp(name,models[i].name))return models+i;return NULL;}
Model *load_cached_model(char *name,char *file,int flags){return findmodel(name);}
int get_cached_model_index(char *name){return (int)(findmodel(name)-models);}
struct {int cmd;char *args[3];} commands[]={'''+','.join(commands)+r'''};
int main(void){Entry next,*e;Level lev,*level=&lev;Model *cached_model,*tempmodel;char *args[3],*filename="fixture";int n,j,cmd,crlf=0,id=0,kind;unsigned bits[3];memset(&lev,0,sizeof(lev));memset(&next,0,sizeof(next));
for(n=0;n<sizeof(commands)/sizeof(commands[0]);n++){cmd=commands[n].cmd;if(cmd<0){memset(&next,0,sizeof(next));continue;}for(j=0;j<3;j++)args[j]=commands[n].args[j];switch(cmd){'''+ '\n'.join(bodies)+r'''}
if(cmd==CMD_LEVEL_AT){e=level->spawnpoints+level->numspawns-1;kind=e->name?1:e->wait?2:(e->groupmin||e->groupmax)?3:0;memcpy(bits,&e->position,12);
printf("QUEUE|%d|%d|%d|%d|%u|%u|%u|%d",id++,kind,e->name?e->index:65535,e->at,bits[0],bits[1],bits[2],e->flip);for(j=0;j<4;j++)printf("|%d",e->health[j]);printf("|%d|%d|%d|%d|%s\n",e->colourmap,e->boss,e->groupmin,e->groupmax,e->alias);}}
return 0;}
'''
    (a.output/'queue.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','queue.c','-fe=queue.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('STAGE_QUEUE_AUTHORITY_C_BUILD')
    log=subprocess.check_output([str(a.output/'queue.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log)
    results=[]
    for line in log.splitlines():
        if line.startswith('QUEUE|'):
            values=line.split('|')[2:];results.append([*map(int,values[:-1]),values[-1]])
    table=pack(derive(source));decoded=unpack(table,len(models));binary_match=[normalized(r)for r in decoded]==results[:len(decoded)]
    ok=results==expected and binary_match;d=dict(schema='BYOR_4086_STAGE_QUEUE_LOADER_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,loader_cases_sha256=hashlib.sha256('\n'.join(bodies).encode()).hexdigest(),name_limit=name_limit,cases=len(expected),tests=len(tests),actual=results,expected=expected,binary_rows_match_actual_c=binary_match,binary_source_records=len(decoded),table_sha256=hashlib.sha256(table).hexdigest(),external_model_lookup_instrumented=True,live_producer_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');print(d['status'],len(expected),'queue entries',len(tests),'loader streams')
    if not ok:raise SystemExit(1)

if __name__=='__main__':main()
