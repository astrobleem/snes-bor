"""Verify model physics defaults/type ordering and loader bodies in pinned C."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document,discover
from script_nested_authority import extract
from source_model_core_4086 import TYPE_NAMES
from source_model_physics_4086 import load


def run(engine,source,folder):
    folder.mkdir(parents=True,exist_ok=True)
    def git(path):return subprocess.check_output(['git','-C',str(engine),'show',ENGINE_COMMIT+':'+path]).decode('latin1')
    raw=git('engine/openbor.c');header=git('engine/openbor.h');body=extract(raw,'lcmHandleCommandType')
    init=raw[raw.index('s_model *init_model('):raw.index('void update_model_loadflag(')]
    assert 's_model *newchar = calloc(1, sizeof(*newchar));' in init
    assert not re.search(r'newchar->(?:antigravity|bounce|size\.y)\s*=',init)
    enums='\n'.join(re.search(r'typedef enum\s*\{[^}]*\}\s*'+name+r'\s*;',header,re.S)[0]
        for name in ('e_entity_type','e_aimove_1','e_aiattack_1'))
    bodies={}
    for name in ('antigravity','height','bounce'):
        start=raw.index('case CMD_MODEL_'+name.upper()+':');end=raw.index('case CMD_MODEL_',start+5)
        bodies[name]=raw[start:end]
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    cases=[dict(identity=m['declaration'],rows=docs[key(m['source_path'])]['directives'])for m in discover(source,docs)['models']]
    def row(name,*values):return dict(directive=name,values=list(values))
    for kind in TYPE_NAMES:
        cases.append(dict(identity='synthetic-type',rows=[row('type',kind)]))
        for before in (False,True):
            for percent in ('-25','0','33.33333','100','150'):
                ops=[row('antigravity',percent),row('bounce','-2'),row('height','43')]
                cases.append(dict(identity='synthetic-ordered',rows=ops+[row('type',kind)]if before else[row('type',kind)]+ops))
    code=r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define MAX_ATCHAIN 12
typedef struct {char *args[4];} ArgList;
#define GET_ARGP(i) (arglist->args[i])
#define GET_ARG(i) (arglist->args[i])
#define GET_INT_ARG(i) atoi(GET_ARG(i))
int stricmp(const char *a,const char *b){unsigned x,y;do{x=(unsigned char)*a++;y=(unsigned char)*b++;if(x>=65&&x<=90)x+=32;if(y>=65&&y<=90)y+=32;if(x!=y)return (int)x-(int)y;}while(x);return 0;}
void shutdown(int n,char *s,...){exit(9);}
'''+enums+r'''
typedef struct {int type,nopassiveblock,atchain[12],chainlength,bounce,
subject_to_wall,subject_to_platform,subject_to_obstacle,subject_to_hole,
subject_to_gravity,subject_to_screen,subject_to_minz,subject_to_maxz,
no_adjust_base,aimove,aiattack,offscreenkill;float antigravity;struct{int y;}size;}s_model;
'''+body+'\n'
    for index,name in enumerate(bodies,1):code+='#define CMD_MODEL_'+name.upper()+' '+str(index)+'\n'
    code+='void command(ArgList *arglist,s_model *newchar,int n){char *value;switch(n){\n'+'\n'.join(bodies.values())+'\n}}\n'
    code+='int main(void){s_model model,*newchar=&model;ArgList args,*arglist=&args;unsigned bits;\nif(sizeof(float)!=4||sizeof(int)!=4)return 2;\n'
    expected=[]
    for case in cases:
        fields=load(case['rows']);expected.append([struct.unpack('<I',struct.pack('<f',fields['antigravity']))[0],fields['height'],fields['bounce']])
        code+='memset(newchar,0,sizeof(model));newchar->aimove=newchar->aiattack=-1;\n'
        for row in case['rows']:
            name,values=row['directive'],row['values']
            if name not in ('type',*bodies):continue
            for n in range(1,4):code+='args.args[%d]=%s;\n'%(n,json.dumps(values[n-1]if n<=len(values)else''))
            code+='lcmHandleCommandType(arglist,newchar,"fixture");\n'if name=='type'else'command(arglist,newchar,CMD_MODEL_'+name.upper()+');\n'
        code+='memcpy(&bits,&newchar->antigravity,4);printf("%u,%d,%d\\n",bits,newchar->size.y,newchar->bounce);\n'
    code+='return 0;}\n';(folder/'model_physics.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-op','-fpc','-bt=nt','model_physics.c','-fe=model_physics.exe'],cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('MODEL_PHYSICS_AUTHORITY_BUILD:'+build.stdout+build.stderr)
    log=subprocess.check_output([str(folder/'model_physics.exe')],cwd=folder,text=True,timeout=30)
    (folder/'authority.log').write_text(log);actual=[list(map(int,line.split(',')))for line in log.splitlines()]
    report=dict(schema='BYOR_4086_MODEL_PHYSICS_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',
        engine_commit=ENGINE_COMMIT,cases=len(cases),actual=actual,expected=expected,
        source_type_body_sha256=hashlib.sha256(body.encode('latin1')).hexdigest(),
        source_case_body_sha256={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},
        source_case_bodies_unmodified=True,consistent_floating_point_compiler_options=['-op','-fpc'],calloc_defaults_verified=True,native_instance_physics_bound=False,
        motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(cases),'model physics cases');assert actual==expected


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.engine,Source(a.source),a.output.resolve())


if __name__=='__main__':main()
