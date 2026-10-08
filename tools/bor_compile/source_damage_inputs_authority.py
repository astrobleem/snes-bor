"""Actual pinned model loader cases for damage inputs, including order."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from dialect_4086 import ENGINE_COMMIT
from source_damage_inputs_4086 import load


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    names=('ANIMAL','NODROP','GUARDPOINTS','NOMOVE');bodies=[]
    for name in names:
        start=re.search(r'case CMD_MODEL_'+name+r'\s*:',raw).start();end=raw.index('\n            case ',start+1);bodies.append(raw[start:end])
    rows=[[dict(directive=name.lower(),values=[v])]for name in names for v in('-2147483648','-1','0','1','2147483647','1suffix','nonsense')]
    for first in('nomove','nodrop'):
        second='nodrop'if first=='nomove'else'nomove'
        for x in('-1','0','1'):
            for y in('-1','0','1'):
                rows.append([dict(directive=first,values=[x]),dict(directive=second,values=[y])])
    code=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define GET_ARG(n) args[n-1]
#define GET_INT_ARG(n) atoi(args[n-1])
#define CMD_MODEL_ANIMAL 0
#define CMD_MODEL_NODROP 1
#define CMD_MODEL_GUARDPOINTS 2
#define CMD_MODEL_NOMOVE 3
typedef struct{int animal,nodrop,nomove,noflip;struct{int max,current;}guardpoints;}Model;
void command(Model *newchar,int op,char *text){char *args[2],*value;args[0]=text;args[1]="0";switch(op){
'''+ '\n'.join(bodies)+'\n}}\nint main(void){Model m;if(sizeof(int)!=4)return 2;\n'
    for i,rs in enumerate(rows):
        code+='memset(&m,0,sizeof(m));\n'
        for r in rs:code+=f'command(&m,{names.index(r["directive"].upper())},"{r["values"][0]}");\n'
        code+=f'printf("INPUT|{i}|%d,%d,%d,%d\\n",m.animal,m.nodrop,m.guardpoints.max,m.guardpoints.current);\n'
    code+='return 0;}\n';(folder/'damage_inputs.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','damage_inputs.c','-fe=damage_inputs.exe'],cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('DAMAGE_INPUT_C_BUILD:'+build.stdout+build.stderr)
    output=subprocess.check_output([str(folder/'damage_inputs.exe')],cwd=folder,text=True);results=[]
    for line in output.splitlines():
        if not line.startswith('INPUT|'):continue
        _,index,values=line.split('|');i=int(index);d=load(rows[i]);expected=[d['animal'],d['nodrop'],d['guardpoints'],d['guardpoints']];actual=list(map(int,values.split(',')))
        results.append(dict(case=rows[i],actual=actual,expected=expected,passed=actual==expected))
    ok=len(results)==len(rows)and all(r['passed']for r in results)
    report=dict(schema='BYOR_4086_DAMAGE_INPUT_LOADER_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,
                loader_fragments={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in zip(names,bodies)},cases=len(rows),results=results,
                defaults_authority='zeroed allocation; init_model explicitly initializes guardpoints.current=max=0',native_damage_callback_proven=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(results),'damage input loader cases')
    if not ok:raise SystemExit(1)


if __name__=='__main__':main()
