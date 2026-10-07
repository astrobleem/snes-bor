"""Literal pinned update_scroller WAIT block with only findent instrumented."""
import argparse
import hashlib
import itertools
import json
import os
import subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from source_wait_4086 import release

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,default=Path('E:/gh/openbor-bcec'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.c'],cwd=a.engine).decode('latin1')
    start=raw.index('    if(level->waiting)',raw.index('void update_scroller()'));end=raw.index('    if(numplay == 0)',start);block=raw[start:end]
    header=subprocess.check_output(['git','show',ENGINE_COMMIT+':engine/openbor.h'],cwd=a.engine).decode('latin1')
    import re
    assert re.search(r'#define\s+GAME_SPEED\s+200',header) and re.search(r'#define\s+COUNTER_SPEED\s+\(GAME_SPEED\*2\)',header)
    inputs=[];expected=[];crows=[]
    for waiting,enemies,noreset,settime,time in itertools.product((0,1),(0,1),(-2147483648,-1,0,1,2,65536),(-5368709,0,100,5368709),(0,48,0xfffffff0)):
        s=dict(waiting=waiting,enemies=enemies,noreset=noreset,settime=settime,time=time,timeleft=-77,go_time=123)
        inputs.append(dict(s));done=release(s,enemies);expected.append([s['waiting'],s['timeleft'],s['go_time'],int(done)])
        crows.append('{'+','.join(map(str,(waiting,enemies,noreset,settime,time)))+'}')
    code='''#include <stdio.h>
#define TYPE_ENEMY 2
#define GAME_SPEED 200
#define COUNTER_SPEED (GAME_SPEED*2)
struct {int waiting,noreset,settime;} lev,*level=&lev;
unsigned int time,go_time;int timeleft,enemies;
void *findent(int mask){return enemies?&lev:0;}
void run(void){
'''+block+'''}
struct {int waiting,enemies,noreset,settime;unsigned int time;} cases[]={'''+','.join(crows)+'''};
int main(void){unsigned i;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){level->waiting=cases[i].waiting;enemies=cases[i].enemies;level->noreset=cases[i].noreset;level->settime=cases[i].settime;time=cases[i].time;timeleft=-77;go_time=123;run();printf("%d,%d,%u,%d\\n",level->waiting,timeleft,go_time,cases[i].waiting&&!enemies);}return 0;}
'''
    (a.output/'wait.c').write_text(code);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    proc=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-bt=nt','wait.c','-fe=wait.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'build.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('WAIT_AUTHORITY_BUILD')
    log=subprocess.check_output([str(a.output/'wait.exe')],cwd=a.output,text=True);(a.output/'authority.log').write_text(log);actual=[list(map(int,line.split(',')))for line in log.splitlines()]
    ok=actual==expected;d=dict(schema='BYOR_4086_WAIT_AUTHORITY_V1',status='PASS'if ok else'FAIL',engine_commit=ENGINE_COMMIT,block_sha256=hashlib.sha256(block.encode()).hexdigest(),cases=len(inputs),inputs=inputs,expected=expected,actual=actual,enemy_service_instrumented=True,camera_bound=False,motu_gameplay_proven=False)
    (a.output/'report.json').write_text(json.dumps(d,indent=2)+'\n');print(d['status'],len(inputs),'WAIT cases')
    if not ok:raise SystemExit(1)
if __name__=='__main__':main()
