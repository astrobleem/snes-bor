"""Pinned NOQUAKE loader case including ordered OR semantics; joined plan proof."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import struct
from compiler import Source,key
from dialect_4086 import ENGINE_COMMIT
from source_profile import document,discover
from source_landing_plan_4086 import derive,pack,noquake


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C',str(a.engine),'show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    start=raw.index('case CMD_MODEL_NOQUAKE:');end=raw.index('case CMD_MODEL_',start+5);case=raw[start:end]
    source=Source(a.source);docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    rows=[[r for r in docs[key(m['source_path'])]['directives']if r['directive']=='noquake']for m in discover(source,docs)['models']]
    authored_models=len(rows)
    choices=list(itertools.product(('', '0','1','-1','2'),repeat=2))
    rows.extend([[dict(directive='noquake',values=list(first)),dict(directive='noquake',values=list(second))]
                for first,second in itertools.product(choices,repeat=2)])
    code='#include <stdio.h>\n#include <stdlib.h>\n#define CMD_MODEL_NOQUAKE 1\n#define NO_QUAKE 1\n#define NO_QUAKEN 2\n#define GET_INT_ARG(i) atoi(args[(i)-1])\ntypedef struct{int noquake;}Model;void command(Model *newchar,char **args){switch(1){\n'+case+'\n}}\nint main(void){Model model;char *args[2];\n'
    for sequence in rows:
        code+='model.noquake=0;\n'
        for row in sequence:
            values=row['values']+['',''];code+='args[0]='+json.dumps(values[0])+';args[1]='+json.dumps(values[1])+';command(&model,args);\n'
        code+='printf("%d\\n",model.noquake);\n'
    code+='return 0;}\n';(folder/'noquake.c').write_text(code)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','noquake.c','-fe=noquake.exe'],cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('LANDING_PLAN_NOQUAKE_BUILD:'+build.stdout+build.stderr)
    log=subprocess.check_output([str(folder/'noquake.exe')],cwd=folder,text=True,timeout=30);(folder/'authority.log').write_text(log)
    actual=list(map(int,log.splitlines()));expected=[noquake(sequence)for sequence in rows]
    plans=derive(source);table=pack(plans)
    report=dict(schema='BYOR_4086_LANDING_PLAN_AUTHORITY_V1',status='PASS'if actual==expected else'FAIL',engine_commit=ENGINE_COMMIT,
                noquake_loader_cases=len(rows),authored_models=authored_models,inputs=rows,actual=actual,expected=expected,
                source_noquake_case_sha256=hashlib.sha256(case.encode('latin1')).hexdigest(),source_case_unmodified=True,
                landing_plan_count=len(plans['plans']),landing_plan_sha256=hashlib.sha256(table).hexdigest(),
                model_bounce_authority='out/byor-motu-model-physics-authority/report.json',
                animation_bounce_authority='out/byor-motu-animation-bounce-authority/report.json',
                native_landing_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    # Every packed row preserves the source-derived join, not an actor-name selector.
    for i,plan in enumerate(sorted(plans['plans'],key=lambda x:x['handle'])):
        values=struct.unpack_from('<HHfiI',table,16+i*16)
        assert values==(plan['handle'],plan['model_index'],plan['animation_bounce'],plan['model_bounce'],plan['noquake'])
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'NOQUAKE loader cases and',len(plans['plans']),'plan joins');assert actual==expected


if __name__=='__main__':main()
