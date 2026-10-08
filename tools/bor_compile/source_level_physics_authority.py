"""Compile pinned physics loader cases and stage default assignments."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import struct
import subprocess
from dialect_4086 import ENGINE_COMMIT
from source_level_physics_4086 import FIELDS,global_physics,stage_physics


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    bodies={}
    for name in ('LEVELORDER_GRAVITY','LEVEL_GRAVITY','LEVEL_MAXFALLSPEED','LEVEL_MAXTOSSSPEED'):
        bodies[name]=re.search(r'case CMD_'+name+r':\s*(.*?)\s*break;',raw,re.S)[1]
    defaults={k:re.search(r'float default_level_'+k+r' = ([^;]+);',raw)[1]for k in FIELDS}
    initialization='\n'.join(re.search(r'level->'+k+r' = default_level_'+k+r';',raw)[0]for k in FIELDS)
    code='#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#define GET_FLOAT_ARG(n) atof(args[n-1])\n'
    code+='typedef struct {float gravity,maxfallspeed,maxtossspeed;} Level;\n'
    code+='unsigned bits(float f){unsigned v;memcpy(&v,&f,4);return v;}\nint main(void){Level lev,*level=&lev;char *args[3];\n'
    code+=''.join('float default_level_'+k+'='+v+';'for k,v in defaults.items())
    expected=[];inputs=[]
    for global_args,gravity,fall,toss in itertools.product((None,[],['-.3','-9','80'],['-.2']),(None,[],['-10'],['-12.5']),(None,[],['-60'],['-25']),(None,[],['1000'],['123.75'])):
        rows=[]if global_args is None else[dict(directive='gravity',values=global_args)]
        stage=[dict(directive=k,values=v)for k,v in zip(FIELDS,(gravity,fall,toss))if v is not None]
        values=stage_physics(stage,global_physics(rows))
        inputs.append(dict(global_args=global_args,stage=stage))
        expected.append([struct.unpack('<I',struct.pack('<f',values[k]))[0]for k in FIELDS])
        code+=''.join('default_level_'+k+'='+v+';'for k,v in defaults.items())
        def arguments(v):return ''.join('args[%d]=%s;'%(i,json.dumps(x))for i,x in enumerate((v+['']*3)[:3]))
        if global_args is not None:code+=arguments(global_args)+bodies['LEVELORDER_GRAVITY']
        code+=initialization
        for k,v in zip(FIELDS,(gravity,fall,toss)):
            if v is not None:code+=arguments(v)+bodies[dict(gravity='LEVEL_GRAVITY',maxfallspeed='LEVEL_MAXFALLSPEED',maxtossspeed='LEVEL_MAXTOSSSPEED')[k]]
        code+='printf("%u,%u,%u\\n",bits(level->gravity),bits(level->maxfallspeed),bits(level->maxtossspeed));\n'
    code+='return 0;}\n';(folder/'physics.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    b=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','physics.c','-fe=physics.exe'],cwd=folder,env=env,capture_output=True,text=True);(folder/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode:raise ValueError('LEVEL_PHYSICS_AUTHORITY_BUILD:'+b.stdout+b.stderr)
    log=subprocess.check_output([str(folder/'physics.exe')],cwd=folder,text=True);(folder/'authority.log').write_text(log)
    actual=[list(map(int,line.split(',')))for line in log.splitlines()]
    r=dict(schema='BYOR_4086_LEVEL_PHYSICS_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,source_case_hashes={k:hashlib.sha256(v.encode('latin1')).hexdigest()for k,v in bodies.items()},source_default_literals=defaults,source_cases_unmodified=True,cases=len(inputs),inputs=inputs,actual=actual,expected=expected,native_physics_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(inputs),'physics loader cases');assert actual==expected


if __name__=='__main__':main()
