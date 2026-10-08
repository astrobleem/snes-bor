"""Verbatim pinned animation-role loader plus BOUNCEFACTOR authority."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document,discover
from source_animation_ids import configure
from source_animation_bounce_4086 import initial_bounce,load
from script_nested_authority import extract


def run(engine,source,folder):
    folder.mkdir(parents=True,exist_ok=True)
    def git(path):return subprocess.check_output(['git','-C',str(engine),'show',ENGINE_COMMIT+':'+path]).decode('latin1')
    raw=git('engine/openbor.c');header=git('engine/openbor.h')
    loader='static '+extract(raw.replace('static int translate_ani_id','int translate_ani_id'),'translate_ani_id')
    macros=header[header.index('#define strclen'):header.index('#define lut_mul')]
    start=raw.index('case CMD_MODEL_BOUNCEFACTOR:');end=raw.index('case CMD_MODEL_',start+5);case=raw[start:end]
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    structure=discover(source,docs);config=configure(docs[key(structure['models_path'])]['directives'])
    roles=set(config['authority']['direct_loader_aliases'])
    for model in structure['models']:roles.update(a['role']for a in model['animations'])
    roles=sorted(roles);cases=[]
    for role in roles:
        for value in (None,'-2','0','1.5','4','33.33333'):
            cases.append((role,value))
    code='#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n'+macros+'\n'
    for name,value in config['authority']['enum'].items():code+='#define '+name+' '+str(value)+'\n'
    code+='#define MAX_ATKS 20\n#define STA_ATKS 10\n'
    aliases=dict(deaths='dies',normal_attacks='attacks',freespecials='specials')
    for name,values in config['arrays'].items():code+='int anim'+aliases.get(name,name)+'[]={'+','.join(map(str,values))+'};\n'
    code+='''typedef struct {int attackone,sync;float bounce;struct{int cost;}energycost;struct{struct{int x;}min,max;}range;}s_anim;
typedef struct {float jumpheight;}s_model;typedef struct {int counterattack;}s_attack;
'''+loader+'\n#define CMD_MODEL_BOUNCEFACTOR 1\n#define GET_FLOAT_ARG(i) ((float)atof(value))\n'
    code+='void command(s_anim *newanim,char *value){switch(1){\n'+case+'\n}}\n'
    code+='int main(void){s_anim anim,*newanim=&anim;unsigned bits;\n'
    expected=[]
    for role,value in cases:
        rows=[dict(directive='anim',values=[role])]
        if value is not None:rows.append(dict(directive='bouncefactor',values=[value]))
        expected.append(struct.unpack('<I',struct.pack('<f',load(rows)[0]['bounce']))[0])
        code+='memset(newanim,0,sizeof(anim));translate_ani_id('+json.dumps(role)+',NULL,newanim,NULL);\n'
        if value is not None:code+='command(newanim,'+json.dumps(value)+');\n'
        code+='memcpy(&bits,&anim.bounce,4);printf("%u\\n",bits);\n'
    code+='return 0;}\n';(folder/'bounce.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-op','-fpc','-bt=nt','bounce.c','-fe=bounce.exe'],cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('ANIMATION_BOUNCE_AUTHORITY_BUILD:'+build.stdout+build.stderr)
    log=subprocess.check_output([str(folder/'bounce.exe')],cwd=folder,text=True,timeout=30)
    (folder/'authority.log').write_text(log);actual=list(map(int,log.splitlines()))
    report=dict(schema='BYOR_4086_ANIMATION_BOUNCE_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',
        engine_commit=ENGINE_COMMIT,cases=len(cases),inputs=cases,actual=actual,expected=expected,
        source_loader_sha256=hashlib.sha256(loader.encode('latin1')).hexdigest(),
        source_case_body_sha256=hashlib.sha256(case.encode('latin1')).hexdigest(),source_bodies_unmodified=True,
        compiler_float_modes=['-op','-fpc'],native_bounce_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],len(cases),'animation bounce cases');assert actual==expected


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True)
    p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.engine,Source(a.source),a.output.resolve())


if __name__=='__main__':main()
