"""Check animation physics IR against verbatim pinned loader case bodies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document,discover
from source_animation_physics_4086 import loader_frames,derive,pack,unpack

COMMANDS=('dive','dive1','dive2','landframe','dropframe','seta','move','movea','movez')


def run(engine,source,folder):
    folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C',str(engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    header=subprocess.check_output(['git','-C',str(engine),'show',ENGINE_COMMIT+':engine/openbor.h']).decode('latin1')
    bodies={}
    for name in COMMANDS:
        start=raw.index('case CMD_MODEL_'+name.upper()+':')
        end=raw.index('case CMD_MODEL_',start+5)
        bodies[name]=raw[start:end]
    defaults=[]
    for assignment in ('newanim->antigrav = 0;', 'newanim->landframe.frame = -1;',
                       'newanim->dropframe.frame = -1;', 'move.base = -1;'):
        assert assignment in raw,assignment
        defaults.append(assignment)
    frame_macro=re.search(r'^#define GET_FRAME_ARG\(z\).*$',header,re.M).group()
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    structure=discover(source,docs);model_names=[m['declaration']for m in structure['models']]
    fixtures=[]
    for model in structure['models']:
        rows=docs[key(model['source_path'])]['directives'];current=None
        for row in rows:
            if row['directive']=='anim':
                current=[row];fixtures.append(current)
            elif current is not None and row['directive'] in (*COMMANDS,'frame'):
                current.append(row)
    def row(name,*values):return dict(directive=name,values=list(values),line=0)
    for command in ('dive','dive1','dive2'):
        fixtures.append([row('anim','idle'),row('frame','a'),row(command,'1.5','2.25'),
            row('seta','40'),row('movea','-2'),row('frame','b'),row('landframe','this'),
            row('dropframe','this'),row('frame','c'),row('landframe','1',model_names[0])])
    fixtures.append([row('anim','idle'),row('frame','a'),row('landframe','this'),row('dropframe','-1')])
    expected=[]
    for rows in fixtures:
        animation=loader_frames(rows)[0];entity=animation['land_entity']
        ei=-1 if entity is None else model_names.index(entity)if isinstance(entity,str)else entity
        expected.append([animation['antigrav'],animation['landframe'],ei,animation['dropframe'],
            len(animation['frames']),*[f['movement'][k]for f in animation['frames']for k in ('base','x','y','z')]])
    code=r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct {int x,y,z,base;} Move;
typedef struct {int frame,ent;struct {float x,y,z;}velocity;} Event;
typedef struct {int antigrav,numframes;Event landframe,dropframe,jumpframe;} Animation;
typedef struct {int command;char *args[3];} Command;
char **args;int stricmp(const char *a,const char *b){unsigned x,y;do{x=(unsigned char)*a++;y=(unsigned char)*b++;if(x>=65&&x<=90)x+=32;if(y>=65&&y<=90)y+=32;if(x!=y)return (int)x-(int)y;}while(x);return 0;}
#define GET_ARG(z) args[(z)-1]
#define GET_INT_ARG(z) atoi(GET_ARG(z))
#define GET_FLOAT_ARG(z) ((float)atof(GET_ARG(z)))
'''+frame_macro+'\nchar *models[]={'+','.join(json.dumps(n)for n in model_names)+'};\n'
    code+='int get_cached_model_index(char *s){unsigned i;for(i=0;i<sizeof(models)/sizeof(models[0]);i++)if(!stricmp(models[i],s))return i;exit(9);return -1;}\n'
    for i,name in enumerate(COMMANDS,1):code+='#define CMD_MODEL_'+name.upper()+' '+str(i)+'\n'
    for i,rows in enumerate(fixtures):
        code+='Command c%d[]={\n'%i
        for r in rows[1:]:
            values=(r['values']+['','',''])[:3]
            code+='{%d,{%s}},\n'%(0 if r['directive']=='frame'else COMMANDS.index(r['directive'])+1,','.join(json.dumps(v)for v in values))
        code+='};\n'
    code+='void probe(Command *commands,int count){Animation anim,*newanim=&anim;Move move,frames[1024];char *value;int i,j;memset(&anim,0,sizeof(anim));memset(&move,0,sizeof(move));\n'+'\n'.join(defaults)+'\n'
    code+='for(i=0;i<count;i++){args=commands[i].args;if(!commands[i].command){if(newanim->numframes>=1024)exit(10);frames[newanim->numframes++]=move;continue;}switch(commands[i].command){\n'+'\n'.join(bodies.values())+'\n}}\n'
    code+='printf("%d,%d,%d,%d,%d",anim.antigrav,anim.landframe.frame,anim.landframe.ent,anim.dropframe.frame,anim.numframes);for(j=0;j<anim.numframes;j++)printf(",%d,%d,%d,%d",frames[j].base,frames[j].x,frames[j].y,frames[j].z);puts("");}\nint main(void){\n'
    for i in range(len(fixtures)):code+='probe(c%d,sizeof(c%d)/sizeof(c%d[0]));\n'%(i,i,i)
    code+='return 0;}\n';(folder/'physics_loader.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','physics_loader.c','-fe=physics_loader.exe'],cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('ANIMATION_PHYSICS_AUTHORITY_BUILD:'+build.stdout+build.stderr)
    log=subprocess.check_output([str(folder/'physics_loader.exe')],cwd=folder,text=True)
    (folder/'authority.log').write_text(log);actual=[list(map(int,line.split(',')))for line in log.splitlines()]
    inputs=derive(source);binary=pack(inputs);decoded=unpack(binary)
    compiled_expected=[]
    for animation in decoded:
        compiled_expected.append([animation['antigrav'],animation['landframe'],animation['land_entity_index'],
            animation['dropframe'],len(animation['frames']),
            *[value for f in animation['frames']for value in (f['base'],f['y'])]])
    compiled_actual=[]
    for values in actual[:len(decoded)]:
        compiled_actual.append(values[:5]+[value for i in range(values[4])for value in (values[5+i*4],values[7+i*4])])
    (folder/'physics.b4ph').write_bytes(binary)
    report=dict(schema='BYOR_4086_ANIMATION_PHYSICS_LOADER_AUTHORITY_V1',status='PASS'if actual==expected and compiled_actual==compiled_expected else'FAIL',
        engine_commit=ENGINE_COMMIT,cases=len(fixtures),actual=actual,expected=expected,
        case_body_sha256={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},
        source_case_bodies_unmodified=True,frame_macro_sha256=hashlib.sha256(frame_macro.encode()).hexdigest(),
        compiled_sha256=hashlib.sha256(binary).hexdigest(),compiled_bytes=len(binary),
        compiled_records_match_independent_c_authority=compiled_actual==compiled_expected,
        cached_model_lookup_instrumented=True,full_model_loader_proven=False,
        native_active_gravity_or_landing_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(fixtures),'animation physics loader cases',len(binary),'compiled bytes')
    assert actual==expected and compiled_actual==compiled_expected


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'))
    p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.engine,Source(a.source),a.output.resolve())


if __name__=='__main__':main()
