"""Compare jump fields against unchanged pinned model-loader assignments."""
import argparse,hashlib,json,os,re,struct,subprocess
from pathlib import Path
from compiler import Source,key
from source_profile import document,discover
from source_model_core_4086 import load as load_core
from source_player_jump_entry_profile import load
from dialect_4086 import ENGINE_COMMIT


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    tags=('JUMPSPEED','JUMPSPEEDF','JUMPHEIGHT','JUMPMOVE','RUNNING')
    blocks=[]
    for block in re.findall(r'((?:            case CMD_MODEL_[^\n]*\n)+.*?                break;)',raw,re.S):
        if any(t in tags for t in re.findall(r'case CMD_MODEL_(\w+):',block)):blocks.append(block)
    selected='\n'.join(blocks)
    init=raw[raw.index('s_model *init_model('):raw.index('void update_model_loadflag(')]
    defaults='\n'.join(line for line in init.splitlines()if re.match(r'\s*newchar->(?:jumpspeed|jumpheight|runjumpheight|runjumpdist)\s*=',line))
    start=raw.index('    if(newchar->jumpspeed < 0)',raw.index('s_model *load_cached_model('));post=raw[start:raw.index('    if(blendfx_is_set == 0)',start)]
    docs={k:document(Source(a.source),n)for k,(n,_)in Source(a.source).index.items()if k.endswith('.txt')};structure=discover(Source(a.source),docs)
    cases=[dict(identity=m['declaration'],rows=docs[key(m['source_path'])]['directives'],height=4.0,speed=-1.0)for m in structure['models']]
    def row(n,*v):return dict(directive=n,values=list(map(str,v)))
    for name in('jumpspeed','jumpspeedf'):
        for value in('-100','-0','0','0.7','1.17549435e-38','10.1234567','300'):
            for speed in(0.0,1.2):cases.append(dict(identity='synthetic-units',rows=[row(name,value)],height=4.5,speed=-1.0,core_speed=speed))
    for values in((20,5.25,1.3),(10,4.5,2),(-10,-1,0)):
        cases.append(dict(identity='synthetic-running',rows=[row('running',*values),row('jumpmove',2,-3),row('jumpheight',6.75)],height=4.0,speed=.7))
    fields=('jumpheight','jumpspeed','jumpmovez','runjumpheight','runjumpdist')
    code='''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define MAX(a,b) ((a)>(b)?(a):(b))
typedef struct {char *args[8];} ArgList;
#define GET_ARG(i) (arglist->args[i])
#define GET_INT_ARG(i) atoi(GET_ARG(i))
#define GET_FLOAT_ARG(i) ((float)atof(GET_ARG(i)))
typedef struct {float jumpheight,jumpspeed,runjumpheight,runjumpdist,runspeed,speed;int jumpmovez,jumpmovex,runupdown,runhold;} Model;
float default_model_jumpheight,default_model_jumpspeed;
'''
    code+='enum {'+','.join('CMD_MODEL_'+t+'='+str(i+1)for i,t in enumerate(tags))+'};\nvoid init(Model *newchar){\n'+defaults+'\n}\nvoid finish(Model *newchar){\n'+post+'}\nvoid command(Model *newchar,ArgList *arglist,int cmd){char *value;switch(cmd){\n'+selected+'\n}}\nint main(void){Model m;ArgList args;unsigned int v;\n'
    expected=bytearray()
    for c in cases:
        core,_=load_core(c['rows'],c['height']);core['speed']=c.get('core_speed',core['speed'])
        result=load(c['rows'],c['height'],c['speed'],core)
        code+='memset(&m,0,sizeof(m));default_model_jumpheight='+str(c['height'])+'f;default_model_jumpspeed='+str(c['speed'])+'f;m.speed='+str(core['speed'])+'f;init(&m);\n'
        for r in c['rows']:
            tag=r['directive'].upper()
            if tag not in tags:continue
            values=([r['directive']]+r['values']+['0']*8)[:8]
            code+=''.join('args.args['+str(i)+']='+json.dumps(v)+';'for i,v in enumerate(values))+'command(&m,&args,CMD_MODEL_'+tag+');\n'
        code+='finish(&m);\n'
        for f in fields:
            code+=('v=(unsigned int)m.'+f+';'if f=='jumpmovez'else'memcpy(&v,&m.'+f+',4);')+'printf("%08x\\n",v);\n'
            expected.extend(struct.pack('<i',result[f])if f=='jumpmovez'else struct.pack('<f',result[f]))
    code+='return 0;}\n';code=re.sub(r'(?<![\w.])(-?\d+)f(?=[;,])',r'\1.0f',code);(out/'jump_model.c').write_text(code)
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','jump_model.c','-fe=jump_model.exe'],cwd=out,env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT'),capture_output=True,text=True);(out/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('PLAYER_JUMP_MODEL_AUTHORITY_BUILD')
    actual=b''.join(struct.pack('<I',int(v,16))for v in subprocess.check_output([str(out/'jump_model.exe')],cwd=out,text=True).splitlines())
    report=dict(schema='BYOR_4086_PLAYER_JUMP_MODEL_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,literal_defaults_sha256=hashlib.sha256(defaults.encode()).hexdigest(),literal_commands_sha256=hashlib.sha256(selected.encode()).hexdigest(),literal_postload_sha256=hashlib.sha256(post.encode()).hexdigest(),literal_blocks_unmodified=True,cases=len(cases),compared_bytes=len(expected),actual_sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),native_model_fields_bound=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(cases),'jump model authority cases');assert actual==expected


if __name__=='__main__':main()
