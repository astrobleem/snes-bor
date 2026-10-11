"""Execute the pinned spawn model-resolution prefix, before allocation.

This bounded authority probe does not certify constructor execution or residency.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine', type=Path, default=Path('E:/gh/openbor-bcec'))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); a.output = a.output.resolve(); a.output.mkdir(parents=True, exist_ok=True)
    raw = subprocess.check_output(['git', 'show', ENGINE_COMMIT + ':engine/openbor.c'], cwd=a.engine).decode('latin1')
    function = extract(raw, 'spawn')
    start = function.index('    if(!model)')
    end = function.index('    if(ent_count >=', start)
    prefix = function[start:end]
    code = r'''#include <stdio.h>
#include <stddef.h>
typedef struct {int identity;} Model;
typedef struct {Model *model;} Cache;
Model models[]={{11},{22},{33}};
Cache model_cache[2];
int lookups;
Model *findmodel(char *name){lookups++;return &models[2];}
Model *resolve(char *name,int index,Model *model){
''' + prefix + r'''return model;}
int main(void){int resident,explicit_model,named,index;Model *m;
for(resident=0;resident<2;resident++)for(explicit_model=0;explicit_model<2;explicit_model++)
for(named=0;named<2;named++)for(index=-1;index<2;index++){
model_cache[0].model=resident?&models[0]:NULL;model_cache[1].model=&models[1];lookups=0;
m=resolve(named?"named":NULL,index,explicit_model?&models[1]:NULL);
printf("%d|%d|%d|%d|%d|%d\n",resident,explicit_model,named,index,m?m->identity:-1,lookups);
}return 0;}
'''
    (a.output/'resolution.c').write_text(code)
    env = dict(os.environ, WATCOM='C:/WATCOM', INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc = subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','resolution.c','-fe=resolution.exe'], cwd=a.output, env=env, capture_output=True, text=True)
    (a.output/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode: raise ValueError('SPAWN_RESOLUTION_AUTHORITY_BUILD')
    log = subprocess.check_output([str(a.output/'resolution.exe')], cwd=a.output, text=True)
    actual = [list(map(int,line.split('|'))) for line in log.splitlines()]
    expected = []
    for resident in range(2):
        for explicit in range(2):
            for named in range(2):
                for index in range(-1,2):
                    identity = 22 if explicit else (11 if resident else -1) if index==0 else 22 if index==1 else 33 if named else -1
                    expected.append([resident,explicit,named,index,identity,int(not explicit and index<0 and named)])
    report = dict(schema='BYOR_4086_SPAWN_RESOLUTION_AUTHORITY_V1', status='PASS' if actual==expected else 'FAIL',
        engine_commit=ENGINE_COMMIT, resolution_prefix_sha256=hashlib.sha256(prefix.encode()).hexdigest(),
        cases=len(actual), actual=actual, expected=expected,
        zero_initialized_entry_cache_index=0, unloaded_cache_returns_null=True,
        constructor_allocation_instrumented=False, actual_model_residency_proven=False,
        live_queue_dispatch_bound=False, motu_gameplay_proven=False, no_color_reduction=True)
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'], len(actual), 'pinned model-resolution cases')
    if actual!=expected: raise SystemExit(1)


if __name__=='__main__': main()
