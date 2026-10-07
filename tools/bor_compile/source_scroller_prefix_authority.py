"""Pinned unmodified update_scroller prefix, before queue/camera services."""
import argparse
import hashlib
import itertools
import json
import os
import subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from source_scroller_prefix_4086 import begin


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1')
    start=raw.index('void update_scroller()');end=raw.index('    if(current_spawn >= level->numspawns',start);prefix=raw[start:end]
    # Add only an end-of-prefix reachability observer and closing brace.
    function=prefix+' reached=1;\n}\n'
    inputs=[];expected=[];rows=[]
    for time,advance,freeze,completed in itertools.product((0,1,48,0x7fffffff,0x80000000,0xfffffffe,0xffffffff),(0,49,0x80000000,0xffffffff),(-2147483648,-1,0,1,65536),(0,1,-1,65536)):
        s=dict(time=time,advancetime=advance,freezeall=freeze,completed=completed,scrolldx=123,scrolldy=-77)
        reached=begin(s);inputs.append(dict(time=time,advancetime=advance,freezeall=freeze,completed=completed));expected.append([int(reached),s['advancetime'],s['scrolldx'],s['scrolldy']]);rows.append('{'+','.join(map(str,(time,advance,freeze,completed)))+'}')
    code=r'''#include <stdio.h>
typedef unsigned int u32;struct {u32 advancetime;} lev,*level=&lev;
u32 time;int freezeall,level_completed,reached;float advancex,advancey,scrolldx,scrolldy;
'''+function+'\nstruct {u32 time,advance;int freeze,completed;} cases[]={'+','.join(rows)+r'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){time=cases[i].time;level->advancetime=cases[i].advance;freezeall=cases[i].freeze;level_completed=cases[i].completed;scrolldx=123;scrolldy=-77;reached=0;update_scroller();printf("%d,%u,%d,%d\n",reached,level->advancetime,(int)scrolldx,(int)scrolldy);}return 0;}
'''
    (a.output/'prefix.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','prefix.c','-fe=prefix.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('SCROLLER_PREFIX_AUTHORITY_BUILD')
    log=subprocess.check_output([str(a.output/'prefix.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,line.split(',')))for line in log.splitlines()]
    ok=actual==expected;d=dict(schema='BYOR_4086_SCROLLER_PREFIX_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,prefix_sha256=hashlib.sha256(prefix.encode()).hexdigest(),cases=len(inputs),inputs=inputs,expected=expected,actual=actual,native_prefix_bound=False,camera_queue_completion_bound=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');print(d['status'],len(inputs),'scroller prefix cases')
    if not ok:raise SystemExit(1)

if __name__=='__main__':main()
